"""
Tests for ForecasterMixin shared functionality.

Tests cover:
- _get_agents() config hierarchy
- _resolve_model() config hierarchy
- _call_model() basic behavior
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.handler_mixin import DEFAULT_AGENTS, ForecasterMixin
from src.utils.llm import LLMClient, LLMResponse

# ============================================================================
# Test Helper Class
# ============================================================================


class TestableForecasterMixin(ForecasterMixin):
    """Concrete class for testing the mixin."""

    def __init__(self, config: dict, llm: LLMClient = None):
        self.config = config
        self.llm = llm or MagicMock(spec=LLMClient)


# ============================================================================
# _get_agents Tests
# ============================================================================


class TestGetAgents:
    """Tests for _get_agents() configuration hierarchy."""

    def test_get_agents_from_active_agents(self):
        """active_agents takes precedence over other sources."""
        config = {
            "active_agents": [
                {"name": "active_1", "model": "active-model", "weight": 2.0},
                {"name": "active_2", "model": "active-model", "weight": 1.0},
            ],
            "ensemble": {
                "agents": [
                    {"name": "ensemble_1", "model": "ensemble-model", "weight": 1.0},
                ]
            },
        }
        mixin = TestableForecasterMixin(config)

        agents = mixin._get_agents()

        assert len(agents) == 2
        assert agents[0]["name"] == "active_1"
        assert agents[0]["model"] == "active-model"
        assert agents[0]["weight"] == 2.0

    def test_get_agents_from_ensemble(self):
        """Falls back to ensemble.agents when active_agents is empty."""
        config = {
            "active_agents": [],
            "ensemble": {
                "agents": [
                    {"name": "ensemble_1", "model": "ensemble-model", "weight": 1.5},
                    {"name": "ensemble_2", "model": "ensemble-model", "weight": 0.5},
                ]
            },
        }
        mixin = TestableForecasterMixin(config)

        agents = mixin._get_agents()

        assert len(agents) == 2
        assert agents[0]["name"] == "ensemble_1"
        assert agents[0]["weight"] == 1.5

    def test_get_agents_default_fallback(self):
        """Falls back to DEFAULT_AGENTS when no config available."""
        config = {}
        mixin = TestableForecasterMixin(config)

        agents = mixin._get_agents()

        assert len(agents) == 5
        assert agents[0]["name"] == DEFAULT_AGENTS[0]["name"]
        assert agents[0]["model"] == DEFAULT_AGENTS[0]["model"]

    def test_get_agents_limits_to_five(self):
        """Never returns more than 5 agents."""
        config = {
            "active_agents": [
                {"name": f"agent_{i}", "model": "test", "weight": 1.0}
                for i in range(10)  # 10 agents
            ]
        }
        mixin = TestableForecasterMixin(config)

        agents = mixin._get_agents()

        assert len(agents) == 5

    def test_get_agents_missing_key_uses_default(self):
        """Missing active_agents key falls back properly."""
        config = {
            "ensemble": {}  # No agents key
        }
        mixin = TestableForecasterMixin(config)

        agents = mixin._get_agents()

        # Should fall back to DEFAULT_AGENTS
        assert len(agents) == 5

    def test_get_agents_none_active_agents_uses_ensemble(self):
        """None value for active_agents falls back to ensemble."""
        config = {
            "active_agents": None,
            "ensemble": {
                "agents": [
                    {"name": "ensemble_1", "model": "test", "weight": 1.0},
                ]
            },
        }
        mixin = TestableForecasterMixin(config)

        agents = mixin._get_agents()

        # None is falsy, so should fall back to ensemble
        assert agents[0]["name"] == "ensemble_1"


# ============================================================================
# _resolve_model Tests
# ============================================================================


class TestGetModel:
    """Tests for _resolve_model() configuration hierarchy."""

    def test_resolve_model_from_active_models(self):
        """active_models takes precedence."""
        config = {
            "active_models": {
                "query_generator": "active-query-model",
                "summarizer": "active-summary-model",
            },
            "models": {
                "query_generator": "config-query-model",
            },
        }
        mixin = TestableForecasterMixin(config)

        model = mixin._resolve_model("query_generator", "default-model")

        assert model == "active-query-model"

    def test_resolve_model_from_models(self):
        """Falls back to models when active_models doesn't have key."""
        config = {
            "active_models": {},
            "models": {
                "query_generator": "config-query-model",
            },
        }
        mixin = TestableForecasterMixin(config)

        model = mixin._resolve_model("query_generator", "default-model")

        assert model == "config-query-model"

    def test_resolve_model_default_fallback(self):
        """Falls back to default when no config available."""
        config = {}
        mixin = TestableForecasterMixin(config)

        model = mixin._resolve_model("query_generator", "my-default-model")

        assert model == "my-default-model"

    def test_resolve_model_missing_key_uses_default(self):
        """Missing key in all configs uses default."""
        config = {
            "active_models": {
                "other_model": "some-model",
            },
            "models": {
                "another_model": "another-model",
            },
        }
        mixin = TestableForecasterMixin(config)

        model = mixin._resolve_model("query_generator", "fallback-model")

        assert model == "fallback-model"


# ============================================================================
# _call_model Tests
# ============================================================================


class TestCallModel:
    """Tests for _call_model() LLM calls."""

    @pytest.mark.asyncio
    async def test_call_model_returns_content(self):
        """Returns response content on success."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_response = LLMResponse(
            content="Test response",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            cost=0.001,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        mock_llm.complete = AsyncMock(return_value=mock_response)

        mixin = TestableForecasterMixin({}, mock_llm)

        result = await mixin._call_model("test-model", "Test prompt")

        assert result == "Test response"
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_model_passes_system_prompt(self):
        """System prompt passed to LLM client."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_response = LLMResponse(
            content="Response",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            cost=0.001,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        mock_llm.complete = AsyncMock(return_value=mock_response)

        mixin = TestableForecasterMixin({}, mock_llm)

        await mixin._call_model("test-model", "Prompt", system_prompt="You are helpful")

        call_kwargs = mock_llm.complete.call_args.kwargs
        assert call_kwargs["system"] == "You are helpful"

    @pytest.mark.asyncio
    async def test_call_model_reraises_exception(self):
        """Exception from LLM client is re-raised."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("API error"))

        mixin = TestableForecasterMixin({}, mock_llm)

        with pytest.raises(RuntimeError, match="API error"):
            await mixin._call_model("test-model", "Prompt")


# ============================================================================
# _call_model_with_metadata Tests
# ============================================================================


class TestCallModelWithMetadata:
    """Tests for _call_model_with_metadata()."""

    @pytest.mark.asyncio
    async def test_returns_content_and_metadata(self):
        """Returns tuple of content and metadata."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_response = LLMResponse(
            content="Test response",
            model="test-model",
            input_tokens=100,
            output_tokens=200,
            cost=0.05,
            latency_ms=500,
            timestamp="2026-01-01T00:00:00Z",
        )
        mock_llm.complete = AsyncMock(return_value=mock_response)

        mixin = TestableForecasterMixin({}, mock_llm)

        content, metadata = await mixin._call_model_with_metadata("test-model", "Prompt")

        assert content == "Test response"
        assert metadata["input_tokens"] == 100
        assert metadata["output_tokens"] == 200
        assert metadata["cost"] == 0.05

    @pytest.mark.asyncio
    async def test_reraises_exception(self):
        """Exception from LLM client is re-raised."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("API error"))

        mixin = TestableForecasterMixin({}, mock_llm)

        with pytest.raises(RuntimeError, match="API error"):
            await mixin._call_model_with_metadata("test-model", "Prompt")


# ============================================================================
# DEFAULT_AGENTS Tests
# ============================================================================


class TestDefaultAgents:
    """Tests for DEFAULT_AGENTS constant."""

    def test_default_agents_has_five(self):
        """DEFAULT_AGENTS has exactly 5 agents."""
        assert len(DEFAULT_AGENTS) == 5

    def test_default_agents_have_required_keys(self):
        """All default agents have name, model, and weight."""
        for agent in DEFAULT_AGENTS:
            assert "name" in agent
            assert "model" in agent
            assert "weight" in agent

    def test_default_agents_equal_weights(self):
        """All default agents have weight 1.0."""
        for agent in DEFAULT_AGENTS:
            assert agent["weight"] == 1.0
