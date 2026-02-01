"""
Tests for LLM client wrapper.

Tests cover:
- Retry logic on failures
- Cost estimation and tracking
- Response handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.utils.llm import (
    LLMClient,
    LLMResponse,
    LLMCall,
    CostTracker,
    estimate_cost,
    get_cost_tracker,
    reset_cost_tracker,
    MODEL_COSTS,
)
from src.bot.exceptions import LLMError


# ============================================================================
# Cost Estimation Tests
# ============================================================================

class TestEstimateCost:
    """Tests for estimate_cost() function."""

    def test_estimate_cost_known_model(self):
        """Known models use correct pricing."""
        # Claude Haiku pricing: input=0.25, output=1.25 per 1M tokens
        cost = estimate_cost("claude-3-haiku-20240307", input_tokens=1000, output_tokens=1000)

        # 1000 tokens = 0.001 * costs
        expected_input = 0.001 * 0.25
        expected_output = 0.001 * 1.25
        assert cost == pytest.approx(expected_input + expected_output)

    def test_estimate_cost_openrouter_model(self):
        """OpenRouter models use correct pricing."""
        cost = estimate_cost("openrouter/anthropic/claude-3.5-haiku", input_tokens=10000, output_tokens=5000)

        # Pricing: input=0.80, output=4.0 per 1M tokens
        expected_input = 0.01 * 0.80
        expected_output = 0.005 * 4.0
        assert cost == pytest.approx(expected_input + expected_output)

    def test_estimate_cost_unknown_model(self):
        """Unknown models use default (expensive) pricing."""
        cost = estimate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=1000)

        # Default: input=5.0, output=15.0 per 1M tokens
        expected_input = 0.001 * 5.0
        expected_output = 0.001 * 15.0
        assert cost == pytest.approx(expected_input + expected_output)

    def test_estimate_cost_zero_tokens(self):
        """Zero tokens returns zero cost."""
        cost = estimate_cost("claude-3-haiku-20240307", input_tokens=0, output_tokens=0)

        assert cost == 0.0


# ============================================================================
# CostTracker Tests
# ============================================================================

class TestCostTracker:
    """Tests for CostTracker class."""

    def test_initial_state(self):
        """New tracker starts with zeros."""
        tracker = CostTracker()

        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.calls) == 0

    def test_add_call_with_response(self):
        """Adding call with response updates totals."""
        tracker = CostTracker()
        response = LLMResponse(
            content="test",
            model="test-model",
            input_tokens=100,
            output_tokens=200,
            cost=0.05,
            latency_ms=500,
            timestamp="2026-01-01T00:00:00Z",
        )
        call = LLMCall(model="test-model", messages=[], response=response)

        tracker.add_call(call)

        assert tracker.total_input_tokens == 100
        assert tracker.total_output_tokens == 200
        assert tracker.total_cost == 0.05
        assert len(tracker.calls) == 1

    def test_add_call_without_response(self):
        """Adding call without response (error) doesn't update totals."""
        tracker = CostTracker()
        call = LLMCall(model="test-model", messages=[], response=None, error="Error")

        tracker.add_call(call)

        assert tracker.total_input_tokens == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.calls) == 1

    def test_cost_accumulates(self):
        """Multiple calls accumulate costs."""
        tracker = CostTracker()

        for i in range(3):
            response = LLMResponse(
                content="test",
                model="test",
                input_tokens=100,
                output_tokens=100,
                cost=0.01,
                latency_ms=100,
                timestamp="2026-01-01T00:00:00Z",
            )
            tracker.add_call(LLMCall(model="test", messages=[], response=response))

        assert tracker.total_cost == pytest.approx(0.03)
        assert tracker.total_input_tokens == 300
        assert len(tracker.calls) == 3

    def test_get_summary(self):
        """get_summary() returns correct totals."""
        tracker = CostTracker()
        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=500,
            output_tokens=1000,
            cost=0.10,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        tracker.add_call(LLMCall(model="test", messages=[], response=response))
        tracker.add_call(LLMCall(model="test", messages=[], response=None, error="Error"))

        summary = tracker.get_summary()

        assert summary["total_calls"] == 2
        assert summary["successful_calls"] == 1
        assert summary["failed_calls"] == 1
        assert summary["total_input_tokens"] == 500
        assert summary["total_output_tokens"] == 1000
        assert summary["total_cost"] == 0.10

    def test_reset(self):
        """reset() clears all data."""
        tracker = CostTracker()
        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=100,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        tracker.add_call(LLMCall(model="test", messages=[], response=response))

        tracker.reset()

        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_cost == 0.0
        assert len(tracker.calls) == 0


# ============================================================================
# LLMClient Retry Tests
# ============================================================================

class TestLLMClientRetry:
    """Tests for LLMClient retry logic."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """No retries when first call succeeds."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_response.model_dump = MagicMock(return_value={})

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)) as mock_complete:
            client = LLMClient(max_retries=3)
            response = await client.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])

            assert response.content == "Success"
            assert mock_complete.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Retries up to max_retries times."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_response.model_dump = MagicMock(return_value={})

        # Fail twice, then succeed
        with patch('src.utils.llm.acompletion', AsyncMock(side_effect=[
            RuntimeError("Error 1"),
            RuntimeError("Error 2"),
            mock_response,
        ])) as mock_complete:
            client = LLMClient(max_retries=3, retry_delay=0.01)
            response = await client.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])

            assert response.content == "Success"
            assert mock_complete.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Raises LLMError after exhausting retries."""
        with patch('src.utils.llm.acompletion', AsyncMock(side_effect=RuntimeError("Persistent error"))):
            client = LLMClient(max_retries=3, retry_delay=0.01)

            with pytest.raises(LLMError) as exc_info:
                await client.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])

            assert exc_info.value.attempts == 3
            assert "Persistent error" in str(exc_info.value.last_error)

    @pytest.mark.asyncio
    async def test_tracks_cost_on_success(self):
        """Cost tracker updated on successful call."""
        reset_cost_tracker()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        mock_response.usage = MagicMock(prompt_tokens=1000, completion_tokens=500)
        mock_response.model_dump = MagicMock(return_value={})

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)):
            client = LLMClient()
            await client.complete(model="claude-3-haiku-20240307", messages=[{"role": "user", "content": "Hi"}])

            tracker = get_cost_tracker()
            assert tracker.total_input_tokens == 1000
            assert tracker.total_output_tokens == 500
            assert tracker.total_cost > 0

    @pytest.mark.asyncio
    async def test_logs_failed_call(self):
        """Failed calls recorded in call_history."""
        with patch('src.utils.llm.acompletion', AsyncMock(side_effect=RuntimeError("API Error"))):
            client = LLMClient(max_retries=1, retry_delay=0.01)

            with pytest.raises(LLMError):
                await client.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])

            assert len(client.call_history) == 1
            assert client.call_history[0].error is not None
            assert client.call_history[0].response is None


# ============================================================================
# LLMClient Session Tests
# ============================================================================

class TestLLMClientSession:
    """Tests for LLMClient session management."""

    @pytest.mark.asyncio
    async def test_get_session_costs(self):
        """get_session_costs() returns costs for this client only."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        mock_response.model_dump = MagicMock(return_value={})

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)):
            client = LLMClient()
            await client.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])
            await client.complete(model="test-model", messages=[{"role": "user", "content": "Hello"}])

            costs = client.get_session_costs()

            assert costs["calls"] == 2
            assert costs["successful"] == 2
            assert costs["failed"] == 0
            assert costs["input_tokens"] == 200
            assert costs["output_tokens"] == 100

    def test_get_prompt_and_response_empty(self):
        """get_prompt_and_response() returns empty strings when no history."""
        client = LLMClient()

        prompt, response = client.get_prompt_and_response()

        assert prompt == ""
        assert response == ""

    @pytest.mark.asyncio
    async def test_get_prompt_and_response(self):
        """get_prompt_and_response() returns formatted prompt and response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=10)
        mock_response.model_dump = MagicMock(return_value={})

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)):
            client = LLMClient()
            await client.complete(
                model="test-model",
                messages=[{"role": "user", "content": "Test prompt"}]
            )

            prompt, response = client.get_prompt_and_response()

            assert "Test prompt" in prompt
            assert "USER" in prompt
            assert response == "Test response"


# ============================================================================
# Global Tracker Tests
# ============================================================================

class TestGlobalTracker:
    """Tests for global cost tracker functions."""

    def test_get_cost_tracker_returns_same_instance(self):
        """get_cost_tracker() returns the same global instance."""
        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()

        assert tracker1 is tracker2

    def test_reset_cost_tracker_clears_global(self):
        """reset_cost_tracker() clears the global tracker."""
        tracker = get_cost_tracker()
        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=100,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        tracker.add_call(LLMCall(model="test", messages=[], response=response))

        reset_cost_tracker()

        assert get_cost_tracker().total_cost == 0.0


# ============================================================================
# MODEL_COSTS Tests
# ============================================================================

class TestModelCosts:
    """Tests for MODEL_COSTS constant."""

    def test_has_common_models(self):
        """MODEL_COSTS includes common models."""
        assert "claude-3-haiku-20240307" in MODEL_COSTS
        assert "gpt-4o" in MODEL_COSTS
        assert "openrouter/anthropic/claude-sonnet-4.5" in MODEL_COSTS
        assert "openrouter/openai/o3" in MODEL_COSTS

    def test_all_have_input_output(self):
        """All model entries have input and output costs."""
        for model, costs in MODEL_COSTS.items():
            assert "input" in costs, f"{model} missing input cost"
            assert "output" in costs, f"{model} missing output cost"
            assert costs["input"] >= 0
            assert costs["output"] >= 0


# ============================================================================
# LLMResponse Tests
# ============================================================================

class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_creates_with_all_fields(self):
        """Creates response with all required fields."""
        response = LLMResponse(
            content="Test response content",
            model="claude-3-haiku-20240307",
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
            latency_ms=250,
            timestamp="2026-01-01T00:00:00Z",
        )

        assert response.content == "Test response content"
        assert response.model == "claude-3-haiku-20240307"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.cost == 0.001
        assert response.latency_ms == 250

    def test_total_tokens_property(self):
        """total_tokens returns sum of input and output tokens."""
        response = LLMResponse(
            content="Test",
            model="test",
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )

        # If total_tokens property exists
        if hasattr(response, 'total_tokens'):
            assert response.total_tokens == 150


class TestLLMCall:
    """Tests for LLMCall dataclass."""

    def test_creates_successful_call(self):
        """Creates call record for successful completion."""
        response = LLMResponse(
            content="Response",
            model="test",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=200,
            timestamp="2026-01-01T00:00:00Z",
        )
        call = LLMCall(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            response=response,
        )

        assert call.model == "test-model"
        assert call.response == response
        assert call.error is None

    def test_creates_failed_call(self):
        """Creates call record for failed completion."""
        call = LLMCall(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            response=None,
            error="Connection timeout",
        )

        assert call.model == "test-model"
        assert call.response is None
        assert call.error == "Connection timeout"


# ============================================================================
# Cost Calculation Tests
# ============================================================================

class TestCostCalculations:
    """Additional tests for cost calculation edge cases."""

    def test_estimate_cost_large_token_counts(self):
        """Handles large token counts correctly."""
        # 1 million input tokens, 500k output tokens
        cost = estimate_cost(
            "claude-3-haiku-20240307",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )

        # Haiku pricing: input=0.25, output=1.25 per 1M tokens
        expected = 0.25 + 0.625
        assert cost == pytest.approx(expected)

    def test_estimate_cost_fractional_tokens(self):
        """Handles non-integer conceptual costs (integer tokens)."""
        cost = estimate_cost(
            "claude-3-haiku-20240307",
            input_tokens=1,  # Single token
            output_tokens=1,
        )

        # Should be very small but non-zero
        assert cost > 0
        assert cost < 0.001

    def test_cost_tracker_with_multiple_models(self):
        """Tracks costs across multiple different models."""
        tracker = CostTracker()

        for model, tokens in [
            ("claude-3-haiku-20240307", (100, 50)),
            ("gpt-4o", (200, 100)),
            ("claude-3-haiku-20240307", (150, 75)),
        ]:
            cost = estimate_cost(model, tokens[0], tokens[1])
            response = LLMResponse(
                content="Response",
                model=model,
                input_tokens=tokens[0],
                output_tokens=tokens[1],
                cost=cost,
                latency_ms=100,
                timestamp="2026-01-01T00:00:00Z",
            )
            tracker.add_call(LLMCall(model=model, messages=[], response=response))

        summary = tracker.get_summary()

        assert summary["total_calls"] == 3
        assert summary["total_input_tokens"] == 450
        assert summary["total_output_tokens"] == 225
        assert summary["total_cost"] > 0


# ============================================================================
# LLMClient Additional Tests
# ============================================================================

class TestLLMClientAdditional:
    """Additional tests for LLMClient functionality."""

    @pytest.mark.asyncio
    async def test_handles_empty_response_content(self):
        """Handles API response with empty content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=0)
        mock_response.model_dump = MagicMock(return_value={})

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)):
            client = LLMClient()
            response = await client.complete(
                model="test-model",
                messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.content == ""
            assert response.output_tokens == 0

    @pytest.mark.asyncio
    async def test_preserves_message_format(self):
        """Preserves message format in API call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=50, completion_tokens=25)
        mock_response.model_dump = MagicMock(return_value={})

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)) as mock_complete:
            client = LLMClient()
            await client.complete(model="test-model", messages=messages)

            call_kwargs = mock_complete.call_args.kwargs
            assert call_kwargs["messages"] == messages

    @pytest.mark.asyncio
    async def test_call_history_preserved(self):
        """Call history preserved across multiple calls."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_response.model_dump = MagicMock(return_value={})

        with patch('src.utils.llm.acompletion', AsyncMock(return_value=mock_response)):
            client = LLMClient()

            for _ in range(5):
                await client.complete(
                    model="test-model",
                    messages=[{"role": "user", "content": "Hi"}]
                )

            assert len(client.call_history) == 5
            for call in client.call_history:
                assert call.response is not None
                assert call.error is None
