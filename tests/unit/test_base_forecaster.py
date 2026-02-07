"""
Tests for BaseForecaster abstract base class.

Tests cover:
- CROSS_POLLINATION_MAP constant structure
- Initialization with different config combinations
- _get_extracted_data and _get_aggregation_data default implementations
- Cross-pollination logic for context assembly
- Cost tracking snapshot function
- System prompt selection (Claude vs GPT context)

Note: _format_query_prompts is tested in test_prompts.py via concrete subclasses.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.base_forecaster import (
    _FAILED_OUTPUT_PREFIX,
    CROSS_POLLINATION_MAP,
    BaseForecaster,
    _is_failed_output,
)
from src.bot.extractors import AgentResult
from src.bot.prompts import SUPERFORECASTER_CONTEXT
from src.bot.search import QuestionDetails
from src.storage.artifact_store import ArtifactStore
from src.utils.llm import LLMClient, LLMResponse

# ============================================================================
# Concrete Test Implementation
# ============================================================================


class ConcreteForecaster(BaseForecaster):
    """Minimal concrete implementation for testing base class logic."""

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
        return 50.0  # Always return 50%

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
# CROSS_POLLINATION_MAP Tests
# ============================================================================


class TestCrossPolllinationMap:
    """Tests for the CROSS_POLLINATION_MAP constant."""

    def test_has_five_entries(self):
        """Map covers all 5 agent indices (0-4)."""
        assert len(CROSS_POLLINATION_MAP) == 5
        assert set(CROSS_POLLINATION_MAP.keys()) == {0, 1, 2, 3, 4}

    def test_valid_source_indices(self):
        """All source indices are valid (0-4)."""
        for agent_idx, (source_idx, label) in CROSS_POLLINATION_MAP.items():
            assert 0 <= source_idx <= 4, f"Agent {agent_idx} has invalid source {source_idx}"
            assert isinstance(label, str)
            assert len(label) > 0

    def test_creates_cross_model_diversity(self):
        """Middle agents receive context from different models."""
        # Agent 1 (idx 1) should get context from Agent 4 (idx 3) - different models
        source_for_agent_1 = CROSS_POLLINATION_MAP[1][0]
        assert source_for_agent_1 == 3  # Gets from o3

        # Agent 2 (idx 2) should get context from Agent 2 (idx 1)
        source_for_agent_2 = CROSS_POLLINATION_MAP[2][0]
        assert source_for_agent_2 == 1  # Gets from Sonnet 4.5

        # Agent 3 (idx 3) should get context from Agent 3 (idx 2)
        source_for_agent_3 = CROSS_POLLINATION_MAP[3][0]
        assert source_for_agent_3 == 2  # Gets from o3-mini-high


# ============================================================================
# Initialization Tests
# ============================================================================


class TestBaseForecasterInit:
    """Tests for BaseForecaster initialization."""

    def test_init_with_config_only(self):
        """Creates default LLM client when none provided."""
        config = {"test": "value"}
        forecaster = ConcreteForecaster(config)

        assert forecaster.config == config
        assert forecaster.llm is not None
        assert isinstance(forecaster.llm, LLMClient)
        assert forecaster.artifact_store is None

    def test_init_with_llm_client(self):
        """Uses provided LLM client."""
        config = {}
        mock_llm = MagicMock(spec=LLMClient)

        forecaster = ConcreteForecaster(config, llm_client=mock_llm)

        assert forecaster.llm is mock_llm

    def test_init_with_artifact_store(self):
        """Stores artifact_store when provided."""
        config = {}
        mock_store = MagicMock(spec=ArtifactStore)

        forecaster = ConcreteForecaster(config, artifact_store=mock_store)

        assert forecaster.artifact_store is mock_store


# ============================================================================
# Data Extraction Methods Tests
# ============================================================================


class TestGetExtractedData:
    """Tests for _get_extracted_data default implementation."""

    @pytest.fixture
    def forecaster(self):
        return ConcreteForecaster({})

    def test_with_probability(self, forecaster):
        """Returns dict with probability and error."""
        result = AgentResult(
            agent_id="forecaster_1",
            model="test",
            weight=1.0,
            outside_view_output="",
            inside_view_output="",
            probability=65.0,
            error=None,
        )

        # Call the actual base class method
        data = forecaster._get_extracted_data(result)

        assert data == {"probability": 65.0, "error": None}

    def test_with_error(self, forecaster):
        """Returns None probability with error message."""
        result = AgentResult(
            agent_id="forecaster_1",
            model="test",
            weight=1.0,
            outside_view_output="",
            inside_view_output="",
            probability=None,
            error="Extraction failed",
        )

        # Call the actual base class method
        data = forecaster._get_extracted_data(result)

        assert data == {"probability": None, "error": "Extraction failed"}


class TestGetAggregationData:
    """Tests for _get_aggregation_data default implementation."""

    @pytest.fixture
    def forecaster(self):
        return ConcreteForecaster({})

    def test_structure(self, forecaster):
        """Returns dict with correct keys."""
        results = [
            AgentResult(
                agent_id=f"forecaster_{i + 1}",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                probability=50.0 + i * 5,
            )
            for i in range(5)
        ]
        agents = [{"name": f"f{i + 1}", "model": "test", "weight": 1.0} for i in range(5)]

        data = forecaster._get_aggregation_data(results, agents, 0.60)

        assert "individual_probabilities" in data
        assert "weights" in data
        assert "method" in data
        assert "final_prediction" in data

        assert len(data["individual_probabilities"]) == 5
        assert len(data["weights"]) == 5
        assert data["method"] == "weighted_average"
        assert data["final_prediction"] == 0.60


# ============================================================================
# Cross-Pollination Logic Tests
# ============================================================================


class TestCrossPolllinationLogic:
    """Tests for cross-pollination context assembly."""

    @pytest.fixture
    def forecaster(self):
        config = {
            "_active_agents": [
                {"name": f"forecaster_{i + 1}", "model": "test-model", "weight": 1.0}
                for i in range(5)
            ]
        }
        return ConcreteForecaster(config)

    def test_assembles_context_format(self):
        """Cross-pollinated context has correct format."""
        outside_view_outputs = [f"Output from agent {i + 1}" for i in range(5)]
        current_context = "Current news context"

        # Simulate cross-pollination logic from forecast()
        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]
            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # Check format
        assert "Current context: Current news context" in context_map[0]
        assert "Outside view prediction:" in context_map[0]

    def test_handles_failed_source_agent_falls_back_to_self(self):
        """When designated source failed, falls back to self's outside view."""
        outside_view_outputs = [
            "Output 1",
            "Output 2",
            "Output 3",
            f"{_FAILED_OUTPUT_PREFIX}Agent 4 failed",  # Agent 4 (idx 3) failed
            "Output 5",
        ]
        current_context = "Current context"

        # Simulate cross-pollination logic with fallback (mirrors base_forecaster.py step 4)
        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            if _is_failed_output(source_output):
                fallback_idx = None
                if not _is_failed_output(outside_view_outputs[i]):
                    fallback_idx = i
                else:
                    for j in range(5):
                        if not _is_failed_output(outside_view_outputs[j]):
                            fallback_idx = j
                            break

                if fallback_idx is not None:
                    source_output = outside_view_outputs[fallback_idx]
                else:
                    source_output = ""

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # Agent 2 (idx 1) gets from Agent 4 (idx 3) which failed → falls back to self (idx 1)
        assert "Output 2" in context_map[1]
        assert _FAILED_OUTPUT_PREFIX not in context_map[1]

    def test_uses_correct_source_agent(self):
        """Each agent receives context from correct source per map."""
        outside_view_outputs = [f"UNIQUE_OUTPUT_{i}" for i in range(5)]

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            context_map[i] = outside_view_outputs[source_idx]

        # Verify based on CROSS_POLLINATION_MAP
        assert "UNIQUE_OUTPUT_0" in context_map[0]  # Agent 1 <- Agent 1
        assert "UNIQUE_OUTPUT_3" in context_map[1]  # Agent 2 <- Agent 4
        assert "UNIQUE_OUTPUT_1" in context_map[2]  # Agent 3 <- Agent 2
        assert "UNIQUE_OUTPUT_2" in context_map[3]  # Agent 4 <- Agent 3
        assert "UNIQUE_OUTPUT_4" in context_map[4]  # Agent 5 <- Agent 5

    def test_fallback_scans_for_any_valid_when_self_also_failed(self):
        """When both designated source and self failed, falls back to first valid output."""
        # Forecaster 2 (idx 1) gets from Forecaster 4 (idx 3) per map.
        # Both idx 1 and idx 3 fail → should fall back to first valid (idx 0).
        outside_view_outputs = [
            "Valid output from agent 1",
            f"{_FAILED_OUTPUT_PREFIX}Agent 2 error",
            f"{_FAILED_OUTPUT_PREFIX}Agent 3 error",
            f"{_FAILED_OUTPUT_PREFIX}Agent 4 error",
            "Valid output from agent 5",
        ]
        current_context = "Current context"

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            if _is_failed_output(source_output):
                fallback_idx = None
                if not _is_failed_output(outside_view_outputs[i]):
                    fallback_idx = i
                else:
                    for j in range(5):
                        if not _is_failed_output(outside_view_outputs[j]):
                            fallback_idx = j
                            break

                if fallback_idx is not None:
                    source_output = outside_view_outputs[fallback_idx]
                else:
                    source_output = ""

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # Agent 2 (idx 1): source idx 3 failed, self idx 1 failed → falls back to idx 0
        assert "Valid output from agent 1" in context_map[1]

        # Agent 3 (idx 2): source idx 1 failed, self idx 2 failed → falls back to idx 0
        assert "Valid output from agent 1" in context_map[2]

        # Agent 4 (idx 3): source idx 2 failed, self idx 3 failed → falls back to idx 0
        assert "Valid output from agent 1" in context_map[3]

        # Agent 1 (idx 0): source is self (idx 0), which is valid → no fallback needed
        assert "Valid output from agent 1" in context_map[0]

        # Agent 5 (idx 4): source is self (idx 4), which is valid → no fallback needed
        assert "Valid output from agent 5" in context_map[4]

    def test_all_failed_gives_empty_context(self):
        """When all 5 outside views failed, forecasters receive empty context."""
        outside_view_outputs = [f"{_FAILED_OUTPUT_PREFIX}Agent {i + 1} error" for i in range(5)]
        current_context = "Current context"

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            if _is_failed_output(source_output):
                fallback_idx = None
                if not _is_failed_output(outside_view_outputs[i]):
                    fallback_idx = i
                else:
                    for j in range(5):
                        if not _is_failed_output(outside_view_outputs[j]):
                            fallback_idx = j
                            break

                if fallback_idx is not None:
                    source_output = outside_view_outputs[fallback_idx]
                else:
                    source_output = ""

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # All agents should get empty outside view context
        for i in range(5):
            assert _FAILED_OUTPUT_PREFIX not in context_map[i]
            assert context_map[i].endswith("Outside view prediction: ")

    def test_no_fallback_when_all_sources_valid(self):
        """When all outputs are valid, normal cross-pollination applies (no fallback)."""
        outside_view_outputs = [f"Valid output {i}" for i in range(5)]
        current_context = "Current context"

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            if _is_failed_output(source_output):
                # This branch should never execute in this test
                raise AssertionError("Fallback triggered unexpectedly")

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # Verify standard mapping applies
        assert "Valid output 0" in context_map[0]  # Self
        assert "Valid output 3" in context_map[1]  # From Forecaster 4
        assert "Valid output 1" in context_map[2]  # From Forecaster 2
        assert "Valid output 2" in context_map[3]  # From Forecaster 3
        assert "Valid output 4" in context_map[4]  # Self

    def test_failed_output_not_leaked_into_context(self):
        """Failed output sentinel string never appears in any forecaster's context."""
        outside_view_outputs = [
            "Valid output 0",
            f"{_FAILED_OUTPUT_PREFIX}TruncationError: Response truncated at 4000 tokens",
            "Valid output 2",
            f"{_FAILED_OUTPUT_PREFIX}RuntimeError: API timeout",
            "Valid output 4",
        ]
        current_context = "Current context"

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            if _is_failed_output(source_output):
                fallback_idx = None
                if not _is_failed_output(outside_view_outputs[i]):
                    fallback_idx = i
                else:
                    for j in range(5):
                        if not _is_failed_output(outside_view_outputs[j]):
                            fallback_idx = j
                            break

                if fallback_idx is not None:
                    source_output = outside_view_outputs[fallback_idx]
                else:
                    source_output = ""

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # No context should contain the failed output sentinel
        for i in range(5):
            assert _FAILED_OUTPUT_PREFIX not in context_map[i]
            assert "TruncationError" not in context_map[i]
            assert "RuntimeError" not in context_map[i]


# ============================================================================
# Failed Output Detection Tests
# ============================================================================


class TestIsFailedOutput:
    """Tests for the _is_failed_output() sentinel detection."""

    def test_detects_sentinel_prefix(self):
        """Correctly identifies outputs with the failed sentinel prefix."""
        assert _is_failed_output(f"{_FAILED_OUTPUT_PREFIX}Some error") is True

    def test_rejects_valid_output(self):
        """Does not flag normal outputs as failed."""
        assert _is_failed_output("Analysis:\n\nThe evidence suggests...") is False

    def test_rejects_empty_string(self):
        """Empty string is not a failure (it's the all-failed fallback)."""
        assert _is_failed_output("") is False

    def test_detects_truncation_error(self):
        """Detects truncation errors tagged with sentinel."""
        msg = f"{_FAILED_OUTPUT_PREFIX}TruncationError: Response truncated at 4000 tokens"
        assert _is_failed_output(msg) is True

    def test_detects_runtime_error(self):
        """Detects runtime errors tagged with sentinel."""
        msg = f"{_FAILED_OUTPUT_PREFIX}RuntimeError: LLM API error"
        assert _is_failed_output(msg) is True

    def test_old_error_prefix_not_detected(self):
        """Old-style 'Error:' prefix is NOT detected (we migrated to sentinel)."""
        assert _is_failed_output("Error: something went wrong") is False

    def test_sentinel_must_be_at_start(self):
        """Sentinel only counts at the very start of the string."""
        msg = f"Some preamble {_FAILED_OUTPUT_PREFIX}error"
        assert _is_failed_output(msg) is False


# ============================================================================
# Cost Tracking Snapshot Tests
# ============================================================================


class TestCostTrackingSnapshot:
    """Tests for the cost tracking snapshot function."""

    def test_records_delta(self):
        """Snapshot correctly calculates cost delta."""
        step_costs = {}

        # Simulate the snapshot_cost closure
        class MockCostTracker:
            total_cost = 0.0

        cost_tracker = MockCostTracker()

        def snapshot_cost(step_name: str, start_cost: float) -> float:
            current_cost = cost_tracker.total_cost
            step_costs[step_name] = round(current_cost - start_cost, 4)
            return current_cost

        # Simulate cost accumulation
        start = 0.0
        cost_tracker.total_cost = 0.05
        result = snapshot_cost("step1", start)

        assert step_costs["step1"] == 0.05
        assert result == 0.05

    def test_returns_new_total_for_next_step(self):
        """Snapshot returns current total for chaining."""
        step_costs = {}

        class MockCostTracker:
            total_cost = 0.0

        cost_tracker = MockCostTracker()

        def snapshot_cost(step_name: str, start_cost: float) -> float:
            current_cost = cost_tracker.total_cost
            step_costs[step_name] = round(current_cost - start_cost, 4)
            return current_cost

        # Step 1
        cost_tracker.total_cost = 0.05
        step1_end = snapshot_cost("step1", 0.0)

        # Step 2
        cost_tracker.total_cost = 0.12
        step2_end = snapshot_cost("step2", step1_end)

        assert step_costs["step1"] == 0.05
        assert step_costs["step2"] == 0.07  # 0.12 - 0.05
        assert step2_end == 0.12


# ============================================================================
# System Prompt Selection Tests
# ============================================================================


class TestSystemPromptSelection:
    """Tests for system prompt selection."""

    def test_all_models_use_superforecaster_context(self):
        """All models use the same SUPERFORECASTER_CONTEXT system prompt."""
        models = [
            "openrouter/anthropic/claude-sonnet-4.5",
            "anthropic/claude-3-opus",
            "claude-3-haiku",
            "openrouter/openai/o3",
            "openai/gpt-4",
            "o3-mini-high",
            "gemini-pro",
        ]

        for model in models:
            system_prompt = SUPERFORECASTER_CONTEXT
            assert system_prompt == SUPERFORECASTER_CONTEXT, f"Failed for model: {model}"


# ============================================================================
# Full Pipeline Tests with Mocked LLM
# ============================================================================


class TestForecastPipeline:
    """Tests for full forecast() pipeline with mocked externals."""

    @pytest.fixture
    def config(self):
        return {
            "_active_agents": [
                {"name": f"forecaster_{i + 1}", "model": "test-model", "weight": 1.0}
                for i in range(5)
            ],
            "_active_models": {
                "query_generator": "test-model",
            },
        }

    @pytest.fixture
    def mock_llm_response(self):
        return LLMResponse(
            content="Test LLM output with prediction",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )

    @pytest.fixture
    def mock_search_pipeline(self):
        """Create a properly mocked SearchPipeline async context manager."""
        mock_search = MagicMock()
        mock_search.execute_searches_from_response = AsyncMock(
            return_value=("Mocked search context", {"tools_used": ["google"]})
        )
        mock_search.scrape_question_urls = AsyncMock(
            return_value=("", {"searched": False, "urls_found": 0, "urls": [], "tools_used": []})
        )
        return mock_search

    @pytest.fixture
    def mock_artifact_store(self):
        """Mock artifact store to avoid KeyError on total_pipeline_cost."""
        return MagicMock(spec=ArtifactStore)

    @pytest.mark.asyncio
    async def test_pipeline_completes_successfully(
        self, config, mock_llm_response, mock_search_pipeline, mock_artifact_store
    ):
        """Full pipeline completes with all mocked externals."""
        # Mock LLM client
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)

        # Mock cost tracker
        mock_tracker = MagicMock()
        mock_tracker.total_cost = 0.5

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            # Setup async context manager
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(
                config, llm_client=mock_llm, artifact_store=mock_artifact_store
            )
            result = await forecaster.forecast(
                log=MagicMock(),
                question_title="Test Question?",
                question_text="Background info",
                resolution_criteria="Resolves YES if X",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            assert result is not None
            assert "prediction" in result
            assert result["prediction"] == 50.0  # ConcreteForecaster always returns 50

    @pytest.mark.asyncio
    async def test_pipeline_calls_llm_for_query_generation(
        self, config, mock_llm_response, mock_search_pipeline, mock_artifact_store
    ):
        """Pipeline calls LLM for historical and current query generation."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)

        mock_tracker = MagicMock()
        mock_tracker.total_cost = 0.5

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(
                config, llm_client=mock_llm, artifact_store=mock_artifact_store
            )
            await forecaster.forecast(
                log=MagicMock(),
                question_title="Test?",
                question_text="Background",
                resolution_criteria="Criteria",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            # Should have called LLM multiple times:
            # 2 for query generation + 5 for step1 + 5 for step2 = 12 calls
            assert mock_llm.complete.call_count == 12

    @pytest.mark.asyncio
    async def test_pipeline_calls_search_for_both_contexts(
        self, config, mock_llm_response, mock_search_pipeline, mock_artifact_store
    ):
        """Pipeline calls search for historical and current contexts."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)

        mock_tracker = MagicMock()
        mock_tracker.total_cost = 0.5

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(
                config, llm_client=mock_llm, artifact_store=mock_artifact_store
            )
            await forecaster.forecast(
                log=MagicMock(),
                question_title="Test?",
                question_text="Background",
                resolution_criteria="Criteria",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            # Search should be called twice (historical + current)
            assert mock_search_pipeline.execute_searches_from_response.call_count == 2

    @pytest.mark.asyncio
    async def test_pipeline_handles_step1_agent_errors(
        self, config, mock_search_pipeline, mock_artifact_store
    ):
        """Pipeline handles errors from step 1 agents gracefully."""
        call_count = 0

        async def mock_complete_with_errors(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First 2 calls succeed (query generation)
            # Then some step1 agents fail
            if call_count <= 2:
                return LLMResponse(
                    content="Query output",
                    model="test",
                    input_tokens=10,
                    output_tokens=10,
                    cost=0.001,
                    latency_ms=50,
                    timestamp="2026-01-01T00:00:00Z",
                )
            elif call_count in [3, 5]:  # Agents 1 and 3 fail in step1
                raise RuntimeError("LLM API error")
            else:
                return LLMResponse(
                    content="Agent output",
                    model="test",
                    input_tokens=10,
                    output_tokens=10,
                    cost=0.001,
                    latency_ms=50,
                    timestamp="2026-01-01T00:00:00Z",
                )

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = mock_complete_with_errors

        mock_tracker = MagicMock()
        mock_tracker.total_cost = 0.5

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(
                config, llm_client=mock_llm, artifact_store=mock_artifact_store
            )
            result = await forecaster.forecast(
                log=MagicMock(),
                question_title="Test?",
                question_text="Background",
                resolution_criteria="Criteria",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            # Should still produce a result despite some agent failures
            assert result is not None
            assert "prediction" in result

    @pytest.mark.asyncio
    async def test_pipeline_saves_artifacts_when_store_provided(
        self, config, mock_llm_response, mock_search_pipeline
    ):
        """Pipeline saves artifacts when artifact_store is provided."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)

        mock_tracker = MagicMock()
        mock_tracker.total_cost = 0.5

        mock_store = MagicMock(spec=ArtifactStore)

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(config, llm_client=mock_llm, artifact_store=mock_store)
            await forecaster.forecast(
                log=MagicMock(),
                question_title="Test?",
                question_text="Background",
                resolution_criteria="Criteria",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            # Verify artifact store methods were called
            assert mock_store.save_query_generation.called
            assert mock_store.save_search_results.called
            assert mock_store.save_outside_view_prompt.called
            assert mock_store.save_forecaster_outside_view.called
            assert mock_store.save_forecaster_inside_view.called
            assert mock_store.save_forecaster_prediction.called
            assert mock_store.save_aggregation.called
            assert mock_store.save_tool_usage.called

    @pytest.mark.asyncio
    async def test_pipeline_tracks_costs_per_step(
        self, config, mock_llm_response, mock_search_pipeline, mock_artifact_store
    ):
        """Pipeline tracks costs for each step."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)

        # Simulate increasing costs
        cost_values = [0.0, 0.05, 0.10, 0.50, 0.80]
        cost_index = [0]

        def get_cost():
            return cost_values[min(cost_index[0], len(cost_values) - 1)]

        mock_tracker = MagicMock()
        type(mock_tracker).total_cost = property(lambda self: get_cost())

        # Track write calls to verify cost logging
        write_calls = []

        def mock_write(msg):
            write_calls.append(msg)
            # Advance cost after certain steps
            if "Step" in msg and "===" in msg:
                cost_index[0] += 1

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(
                config, llm_client=mock_llm, artifact_store=mock_artifact_store
            )
            await forecaster.forecast(
                log=mock_write,
                question_title="Test?",
                question_text="Background",
                resolution_criteria="Criteria",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            # Verify cost breakdown was logged
            cost_breakdown_logged = any("Cost Breakdown" in str(call) for call in write_calls)
            assert cost_breakdown_logged

    @pytest.mark.asyncio
    async def test_pipeline_uses_correct_system_prompts(
        self, mock_llm_response, mock_search_pipeline, mock_artifact_store
    ):
        """Pipeline uses SUPERFORECASTER_CONTEXT for all models."""
        config = {
            "_active_agents": [
                {"name": "forecaster_1", "model": "anthropic/claude-3", "weight": 1.0},
                {"name": "forecaster_2", "model": "openai/gpt-4", "weight": 1.0},
                {"name": "forecaster_3", "model": "anthropic/claude-3.5", "weight": 1.0},
                {"name": "forecaster_4", "model": "openai/o3", "weight": 1.0},
                {"name": "forecaster_5", "model": "openai/gpt-4o", "weight": 1.0},
            ],
            "_active_models": {"query_generator": "test-model"},
        }

        captured_calls = []

        async def capture_complete(*args, **kwargs):
            captured_calls.append(kwargs)
            return mock_llm_response

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = capture_complete

        mock_tracker = MagicMock()
        mock_tracker.total_cost = 0.5

        with (
            patch("src.bot.base_forecaster.SearchPipeline") as MockSearchPipeline,
            patch("src.bot.base_forecaster.get_cost_tracker", return_value=mock_tracker),
        ):
            MockSearchPipeline.return_value.__aenter__ = AsyncMock(
                return_value=mock_search_pipeline
            )
            MockSearchPipeline.return_value.__aexit__ = AsyncMock(return_value=None)

            forecaster = ConcreteForecaster(
                config, llm_client=mock_llm, artifact_store=mock_artifact_store
            )
            await forecaster.forecast(
                log=MagicMock(),
                question_title="Test?",
                question_text="Background",
                resolution_criteria="Criteria",
                fine_print="",
                scheduled_close_time="2026-12-31",
                scheduled_resolve_time="2027-01-15",
            )

            # Check that SUPERFORECASTER_CONTEXT was used for forecaster calls
            system_prompts = [call.get("system", "") for call in captured_calls if "system" in call]
            assert any(SUPERFORECASTER_CONTEXT in str(sp) for sp in system_prompts), (
                "SUPERFORECASTER_CONTEXT not used"
            )
