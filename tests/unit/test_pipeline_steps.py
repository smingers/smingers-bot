"""
Tests for individual pipeline steps.

These tests exercise the decomposed step methods on BaseForecaster directly,
verifying that each step can be called independently with typed inputs/outputs.
This is the key benefit of the pipeline decomposition — each step is testable
without running the full pipeline.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.base_forecaster import (
    _FAILED_OUTPUT_PREFIX,
    BaseForecaster,
)
from src.bot.extractors import AgentResult
from src.bot.metrics import AgentMetrics, PipelineMetrics
from src.bot.pipeline_data import (
    CrossPollinatedContext,
    EnsembleResult,
    InsideViewResult,
    OutsideViewResult,
    ResearchContext,
)
from src.bot.search import QuestionDetails
from src.utils.llm import LLMClient, LLMResponse

# ============================================================================
# Concrete Test Implementation (same as test_base_forecaster.py)
# ============================================================================


class ConcreteForecaster(BaseForecaster):
    """Minimal concrete implementation for testing individual pipeline steps."""

    question_type = "binary"

    def _get_prompt_templates(self):
        return (
            "historical: {title}",
            "current: {title}",
            "outside_view: {context}",
            "inside_view: {context}",
        )

    def _get_question_details(self, **params):
        return QuestionDetails(
            title=params.get("question_title", ""),
            resolution_criteria=params.get("resolution_criteria", ""),
            fine_print=params.get("fine_print", ""),
            description=params.get("question_text", ""),
            resolution_date=params.get("scheduled_resolve_time"),
        )

    def _format_outside_view_prompt(self, template, context, **params):
        return template.format(context=context)

    def _format_inside_view_prompt(self, template, context, **params):
        return template.format(context=context)

    def _extract_prediction(self, output, **params):
        return 50.0

    def _aggregate_results(self, results, agents, log):
        valid = [r for r in results if r.probability is not None]
        if not valid:
            raise RuntimeError("No valid predictions")
        return sum(r.probability for r in valid) / len(valid)

    def _build_agent_result(
        self, agent_id, model, weight, outside_view_output, inside_view_output, prediction, error
    ):
        return AgentResult(
            agent_id=agent_id,
            model=model,
            weight=weight,
            outside_view_output=outside_view_output,
            inside_view_output=inside_view_output,
            probability=prediction,
            error=error,
        )

    def _build_result(self, final_prediction, agent_results, **params):
        return {"prediction": final_prediction}


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def agents():
    """Standard 5-agent configuration for testing."""
    return [{"name": f"forecaster_{i + 1}", "model": "test-model", "weight": 1.0} for i in range(5)]


@pytest.fixture
def metrics(agents):
    """Pipeline metrics initialized with agent entries."""
    m = PipelineMetrics.create_empty()
    for i, agent in enumerate(agents):
        m.agents[f"forecaster_{i + 1}"] = AgentMetrics(
            model=agent["model"],
            weight=agent["weight"],
        )
    return m


@pytest.fixture
def forecaster():
    """ConcreteForecaster with mocked LLM client."""
    config = {
        "active_agents": [
            {"name": f"forecaster_{i + 1}", "model": "test-model", "weight": 1.0} for i in range(5)
        ],
    }
    mock_llm = MagicMock(spec=LLMClient)
    return ConcreteForecaster(config, llm_client=mock_llm)


# ============================================================================
# _cross_pollinate Tests
# ============================================================================


class TestCrossPollinateStep:
    """Test cross-pollination as an independent step."""

    def test_returns_typed_result(self, forecaster):
        """Returns a CrossPollinatedContext with context_map."""
        outputs = [f"Output {i}" for i in range(5)]
        result = forecaster._cross_pollinate(outputs, "Current news")

        assert isinstance(result, CrossPollinatedContext)
        assert len(result.context_map) == 5

    def test_all_contexts_contain_current_context(self, forecaster):
        """Every forecaster's context includes the current context."""
        outputs = [f"Output {i}" for i in range(5)]
        result = forecaster._cross_pollinate(outputs, "Current news about topic X")

        for ctx in result.context_map.values():
            assert "Current news about topic X" in ctx

    def test_all_contexts_contain_label(self, forecaster):
        """Every forecaster's context includes the cross-pollination label."""
        outputs = [f"Output {i}" for i in range(5)]
        result = forecaster._cross_pollinate(outputs, "Current")

        for ctx in result.context_map.values():
            assert "Outside view prediction:" in ctx

    def test_failed_outputs_not_leaked(self, forecaster):
        """Failed output sentinels are never passed through to contexts."""
        outputs = [
            "Valid 0",
            f"{_FAILED_OUTPUT_PREFIX}err",
            "Valid 2",
            f"{_FAILED_OUTPUT_PREFIX}err",
            "Valid 4",
        ]
        result = forecaster._cross_pollinate(outputs, "Current")

        for ctx in result.context_map.values():
            assert _FAILED_OUTPUT_PREFIX not in ctx

    def test_all_failed_gives_empty_outside_view(self, forecaster):
        """When all 5 outside views failed, forecasters get empty context."""
        outputs = [f"{_FAILED_OUTPUT_PREFIX}err {i}" for i in range(5)]
        result = forecaster._cross_pollinate(outputs, "Current")

        for ctx in result.context_map.values():
            assert _FAILED_OUTPUT_PREFIX not in ctx
            # Context ends with label and empty string
            assert ctx.endswith("Outside view prediction: ")

    def test_self_pollination_for_edge_agents(self, forecaster):
        """Agents 1 and 5 receive their own outside view per CROSS_POLLINATION_MAP."""
        outputs = [f"UNIQUE_{i}" for i in range(5)]
        result = forecaster._cross_pollinate(outputs, "Current")

        # Agent 1 (idx 0) gets from itself (idx 0)
        assert "UNIQUE_0" in result.context_map[0]
        # Agent 5 (idx 4) gets from itself (idx 4)
        assert "UNIQUE_4" in result.context_map[4]


# ============================================================================
# _extract_and_aggregate Tests
# ============================================================================


class TestExtractAndAggregateStep:
    """Test extraction + aggregation as an independent step."""

    def test_returns_typed_result(self, forecaster, agents):
        """Returns an EnsembleResult with agent_results and final_prediction."""
        inside_view = InsideViewResult(
            outputs=["output"] * 5,
            reasoning={},
        )
        result = forecaster._extract_and_aggregate(
            agents=agents,
            outside_view_outputs=[""] * 5,
            inside_view_result=inside_view,
            question_params={},
            log=MagicMock(),
        )

        assert isinstance(result, EnsembleResult)
        assert len(result.agent_results) == 5
        assert result.final_prediction is not None

    def test_concrete_forecaster_returns_50(self, forecaster, agents):
        """ConcreteForecaster always extracts 50.0, so average should be 50.0."""
        inside_view = InsideViewResult(
            outputs=["any output"] * 5,
            reasoning={},
        )
        result = forecaster._extract_and_aggregate(
            agents=agents,
            outside_view_outputs=[""] * 5,
            inside_view_result=inside_view,
            question_params={},
            log=MagicMock(),
        )

        assert result.final_prediction == 50.0

    def test_handles_exception_outputs(self, forecaster, agents):
        """Exception outputs result in None predictions, not crashes."""
        inside_view = InsideViewResult(
            outputs=[
                "valid output",
                RuntimeError("LLM failed"),
                "valid output",
                "valid output",
                RuntimeError("timeout"),
            ],
            reasoning={},
        )
        result = forecaster._extract_and_aggregate(
            agents=agents,
            outside_view_outputs=[""] * 5,
            inside_view_result=inside_view,
            question_params={},
            log=MagicMock(),
        )

        assert len(result.agent_results) == 5
        # Agents 2 and 5 should have errors
        assert result.agent_results[1].error is not None
        assert result.agent_results[4].error is not None
        # Valid agents should have predictions
        assert result.agent_results[0].probability == 50.0
        assert result.agent_results[2].probability == 50.0

    def test_failed_outside_views_become_empty_strings(self, forecaster, agents):
        """Failed outside view outputs are replaced with empty strings in AgentResults."""
        inside_view = InsideViewResult(
            outputs=["output"] * 5,
            reasoning={},
        )
        outside_view_outputs = [
            "valid",
            f"{_FAILED_OUTPUT_PREFIX}err",
            "valid",
            "valid",
            "valid",
        ]
        result = forecaster._extract_and_aggregate(
            agents=agents,
            outside_view_outputs=outside_view_outputs,
            inside_view_result=inside_view,
            question_params={},
            log=MagicMock(),
        )

        assert result.agent_results[0].outside_view_output == "valid"
        assert result.agent_results[1].outside_view_output == ""


# ============================================================================
# _run_outside_view Tests
# ============================================================================


class TestRunOutsideViewStep:
    """Test outside view prediction as an independent step."""

    @pytest.fixture
    def mock_llm_response(self):
        return LLMResponse(
            content="Test outside view analysis",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_returns_typed_result(self, agents, metrics, mock_llm_response):
        """Returns an OutsideViewResult with outputs and prompt."""
        config = {"active_agents": agents}
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        forecaster = ConcreteForecaster(config, llm_client=mock_llm)

        result = await forecaster._run_outside_view(
            agents=agents,
            outside_view_prompt="Test prompt",
            forecast_temp=0.3,
            metrics=metrics,
            log=MagicMock(),
        )

        assert isinstance(result, OutsideViewResult)
        assert len(result.outputs) == 5
        assert result.prompt == "Test prompt"

    @pytest.mark.asyncio
    async def test_only_three_llm_calls(self, agents, metrics, mock_llm_response):
        """Only forecasters 1, 3, 5 make actual LLM calls (three-outside-view)."""
        config = {"active_agents": agents}
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        forecaster = ConcreteForecaster(config, llm_client=mock_llm)

        await forecaster._run_outside_view(
            agents=agents,
            outside_view_prompt="Test prompt",
            forecast_temp=0.3,
            metrics=metrics,
            log=MagicMock(),
        )

        # 3 calls for real indices [0, 2, 4]
        assert mock_llm.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_reused_outputs_match_source(self, agents, metrics):
        """Forecasters 2 and 4 reuse outputs from 5 and 3 respectively."""
        call_idx = [0]
        outputs = ["Output_F1", "Output_F3", "Output_F5"]

        async def mock_complete(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            return LLMResponse(
                content=outputs[idx],
                model="test",
                input_tokens=10,
                output_tokens=10,
                cost=0.001,
                latency_ms=50,
                timestamp="2026-01-01T00:00:00Z",
            )

        config = {"active_agents": agents}
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = mock_complete
        forecaster = ConcreteForecaster(config, llm_client=mock_llm)

        result = await forecaster._run_outside_view(
            agents=agents,
            outside_view_prompt="Test",
            forecast_temp=0.3,
            metrics=metrics,
            log=MagicMock(),
        )

        # F2 (idx 1) reuses F5 (idx 4) = "Output_F5"
        assert result.outputs[1] == result.outputs[4]
        # F4 (idx 3) reuses F3 (idx 2) = "Output_F3"
        assert result.outputs[3] == result.outputs[2]


# ============================================================================
# _run_inside_view Tests
# ============================================================================


class TestRunInsideViewStep:
    """Test inside view prediction as an independent step."""

    @pytest.fixture
    def mock_llm_response(self):
        return LLMResponse(
            content="Test inside view prediction: probability 50%",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_returns_typed_result(self, agents, metrics, mock_llm_response):
        """Returns an InsideViewResult with 5 outputs."""
        config = {"active_agents": agents}
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        forecaster = ConcreteForecaster(config, llm_client=mock_llm)

        context_map = {i: f"Context for agent {i}" for i in range(5)}

        result = await forecaster._run_inside_view(
            agents=agents,
            context_map=context_map,
            prompt_inside_view="inside_view: {context}",
            forecast_temp=0.3,
            question_params={},
            metrics=metrics,
            log=MagicMock(),
        )

        assert isinstance(result, InsideViewResult)
        assert len(result.outputs) == 5

    @pytest.mark.asyncio
    async def test_all_five_forecasters_called(self, agents, metrics, mock_llm_response):
        """All 5 forecasters make LLM calls for inside view."""
        config = {"active_agents": agents}
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        forecaster = ConcreteForecaster(config, llm_client=mock_llm)

        context_map = {i: f"Context for agent {i}" for i in range(5)}

        await forecaster._run_inside_view(
            agents=agents,
            context_map=context_map,
            prompt_inside_view="inside_view: {context}",
            forecast_temp=0.3,
            question_params={},
            metrics=metrics,
            log=MagicMock(),
        )

        assert mock_llm.complete.call_count == 5


# ============================================================================
# Pipeline Data Type Tests
# ============================================================================


class TestPipelineDataTypes:
    """Test that pipeline data types can be constructed and used independently."""

    def test_research_context_construction(self):
        """ResearchContext can be constructed with minimal data."""
        rc = ResearchContext(
            historical_context="Historical base rate data...",
            current_context="Recent news about...",
        )
        assert rc.historical_context.startswith("Historical")
        assert rc.current_context.startswith("Recent")
        assert rc.metrics == {}

    def test_outside_view_result_construction(self):
        """OutsideViewResult can be constructed with outputs list."""
        ovr = OutsideViewResult(
            outputs=["Analysis 1", "Analysis 2", "Analysis 3", "Analysis 4", "Analysis 5"],
            reasoning={0: "Thinking..."},
            prompt="The prompt used",
        )
        assert len(ovr.outputs) == 5
        assert ovr.reasoning[0] == "Thinking..."
        assert ovr.prompt == "The prompt used"

    def test_inside_view_result_with_exceptions(self):
        """InsideViewResult can hold both strings and Exceptions."""
        ivr = InsideViewResult(
            outputs=[
                "Valid output",
                RuntimeError("API error"),
                "Another valid output",
                "Third valid",
                TimeoutError("timeout"),
            ],
        )
        assert isinstance(ivr.outputs[0], str)
        assert isinstance(ivr.outputs[1], RuntimeError)
        assert len(ivr.outputs) == 5

    def test_ensemble_result_construction(self):
        """EnsembleResult holds agent results and final prediction."""
        agent_result = AgentResult(
            agent_id="forecaster_1",
            model="test",
            weight=1.0,
            outside_view_output="",
            inside_view_output="output",
            probability=65.0,
        )
        er = EnsembleResult(
            agent_results=[agent_result],
            final_prediction=0.65,
        )
        assert len(er.agent_results) == 1
        assert er.final_prediction == 0.65

    def test_cross_pollinated_context_construction(self):
        """CrossPollinatedContext maps indices to context strings."""
        cpc = CrossPollinatedContext(
            context_map={
                0: "Context for agent 1",
                1: "Context for agent 2",
            }
        )
        assert len(cpc.context_map) == 2
        assert "agent 1" in cpc.context_map[0]
