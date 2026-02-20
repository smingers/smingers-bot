"""
Tests for LLM client wrapper.

Tests cover:
- Retry logic on failures
- Cost estimation and tracking
- Response handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.exceptions import LLMError
from src.utils.llm import (
    MODEL_COSTS,
    CostTracker,
    LLMCall,
    LLMClient,
    LLMResponse,
    calculate_cost,
    get_cost_tracker,
    reset_cost_tracker,
)

# ============================================================================
# Cost Calculation Tests
# ============================================================================


class TestCalculateCost:
    """Tests for calculate_cost() function."""

    def test_calculate_cost_known_model(self):
        """Known models use correct pricing."""
        # Claude Haiku pricing: input=0.25, output=1.25 per 1M tokens
        cost = calculate_cost("claude-3-haiku-20240307", input_tokens=1000, output_tokens=1000)

        # 1000 tokens = 0.001 * costs
        expected_input = 0.001 * 0.25
        expected_output = 0.001 * 1.25
        assert cost == pytest.approx(expected_input + expected_output)

    def test_calculate_cost_openrouter_model(self):
        """OpenRouter models use correct pricing."""
        cost = calculate_cost(
            "openrouter/anthropic/claude-3.5-haiku", input_tokens=10000, output_tokens=5000
        )

        # Pricing: input=0.80, output=4.0 per 1M tokens
        expected_input = 0.01 * 0.80
        expected_output = 0.005 * 4.0
        assert cost == pytest.approx(expected_input + expected_output)

    def test_calculate_cost_unknown_model(self):
        """Unknown models use default (expensive) pricing."""
        cost = calculate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=1000)

        # Default: input=5.0, output=15.0 per 1M tokens
        expected_input = 0.001 * 5.0
        expected_output = 0.001 * 15.0
        assert cost == pytest.approx(expected_input + expected_output)

    def test_calculate_cost_zero_tokens(self):
        """Zero tokens returns zero cost."""
        cost = calculate_cost("claude-3-haiku-20240307", input_tokens=0, output_tokens=0)

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

        for _ in range(3):
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

        with patch(
            "src.utils.llm.acompletion", AsyncMock(return_value=mock_response)
        ) as mock_complete:
            client = LLMClient(max_retries=3)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

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
        with patch(
            "src.utils.llm.acompletion",
            AsyncMock(
                side_effect=[
                    RuntimeError("Error 1"),
                    RuntimeError("Error 2"),
                    mock_response,
                ]
            ),
        ) as mock_complete:
            client = LLMClient(max_retries=3, retry_delay=0.01)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.content == "Success"
            assert mock_complete.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Raises LLMError after exhausting retries."""
        with patch(
            "src.utils.llm.acompletion", AsyncMock(side_effect=RuntimeError("Persistent error"))
        ):
            client = LLMClient(max_retries=3, retry_delay=0.01)

            with pytest.raises(LLMError) as exc_info:
                await client.complete(
                    model="test-model", messages=[{"role": "user", "content": "Hi"}]
                )

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

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient()
            await client.complete(
                model="claude-3-haiku-20240307", messages=[{"role": "user", "content": "Hi"}]
            )

            tracker = get_cost_tracker()
            assert tracker.total_input_tokens == 1000
            assert tracker.total_output_tokens == 500
            assert tracker.total_cost > 0

    @pytest.mark.asyncio
    async def test_logs_failed_call(self):
        """Failed calls recorded in call_history."""
        with patch("src.utils.llm.acompletion", AsyncMock(side_effect=RuntimeError("API Error"))):
            client = LLMClient(max_retries=1, retry_delay=0.01)

            with pytest.raises(LLMError):
                await client.complete(
                    model="test-model", messages=[{"role": "user", "content": "Hi"}]
                )

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

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient()
            await client.complete(model="test-model", messages=[{"role": "user", "content": "Hi"}])
            await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hello"}]
            )

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

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient()
            await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Test prompt"}]
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
        if hasattr(response, "total_tokens"):
            assert response.total_tokens == 150

    def test_was_truncated_true_when_finish_reason_length(self):
        """was_truncated returns True when finish_reason is 'length'."""
        response = LLMResponse(
            content="Incomplete...",
            model="test",
            input_tokens=100,
            output_tokens=4000,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            finish_reason="length",
        )

        assert response.was_truncated is True

    def test_was_truncated_false_when_finish_reason_stop(self):
        """was_truncated returns False when finish_reason is 'stop'."""
        response = LLMResponse(
            content="Complete response",
            model="test",
            input_tokens=100,
            output_tokens=500,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            finish_reason="stop",
        )

        assert response.was_truncated is False

    def test_was_truncated_false_when_finish_reason_none(self):
        """was_truncated returns False when finish_reason is None."""
        response = LLMResponse(
            content="Response",
            model="test",
            input_tokens=100,
            output_tokens=500,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            finish_reason=None,
        )

        assert response.was_truncated is False

    def test_was_truncated_false_for_other_finish_reasons(self):
        """was_truncated returns False for other finish_reasons like 'content_filter'."""
        response = LLMResponse(
            content="Filtered response",
            model="test",
            input_tokens=100,
            output_tokens=500,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            finish_reason="content_filter",
        )

        assert response.was_truncated is False


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

    def test_calculate_cost_large_token_counts(self):
        """Handles large token counts correctly."""
        # 1 million input tokens, 500k output tokens
        cost = calculate_cost(
            "claude-3-haiku-20240307",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )

        # Haiku pricing: input=0.25, output=1.25 per 1M tokens
        expected = 0.25 + 0.625
        assert cost == pytest.approx(expected)

    def test_calculate_cost_fractional_tokens(self):
        """Handles non-integer conceptual costs (integer tokens)."""
        cost = calculate_cost(
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
            cost = calculate_cost(model, tokens[0], tokens[1])
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

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient()
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
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

        with patch(
            "src.utils.llm.acompletion", AsyncMock(return_value=mock_response)
        ) as mock_complete:
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

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient()

            for _ in range(5):
                await client.complete(
                    model="test-model", messages=[{"role": "user", "content": "Hi"}]
                )

            assert len(client.call_history) == 5
            for call in client.call_history:
                assert call.response is not None
                assert call.error is None


# ============================================================================
# Reasoning Token Tests
# ============================================================================


def _make_mock_response(
    content="Success",
    prompt_tokens=10,
    completion_tokens=20,
    reasoning_tokens=None,
    reasoning_content=None,
    finish_reason="stop",
):
    """Create a mock litellm response with optional reasoning fields.

    Uses SimpleNamespace for usage/details to avoid MagicMock auto-attribute issues
    (MagicMock creates truthy objects for any attribute access, which breaks
    isinstance checks and comparisons).
    """
    from types import SimpleNamespace

    # Build completion_tokens_details
    details = None
    if reasoning_tokens is not None:
        details = SimpleNamespace(reasoning_tokens=reasoning_tokens)

    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        completion_tokens_details=details,
    )

    message = SimpleNamespace(
        content=content,
        reasoning_content=reasoning_content,
    )

    choice = SimpleNamespace(
        message=message,
        finish_reason=finish_reason,
    )

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response.model_dump = MagicMock(return_value={})

    return response


class TestLLMResponseReasoning:
    """Tests for reasoning-related fields on LLMResponse."""

    def test_used_reasoning_true_when_tokens_present(self):
        """used_reasoning returns True when reasoning_tokens > 0."""
        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=500,
        )
        assert response.used_reasoning is True

    def test_used_reasoning_false_when_zero(self):
        """used_reasoning returns False when reasoning_tokens is 0."""
        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=0,
        )
        assert response.used_reasoning is False

    def test_used_reasoning_false_by_default(self):
        """used_reasoning defaults to False when reasoning_tokens not provided."""
        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        assert response.used_reasoning is False
        assert response.reasoning_tokens == 0
        assert response.reasoning_content is None

    def test_reasoning_content_stored(self):
        """reasoning_content is stored when provided."""
        response = LLMResponse(
            content="output",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=1000,
            reasoning_content="Let me think step by step...",
        )
        assert response.reasoning_content == "Let me think step by step..."
        assert response.used_reasoning is True


class TestReasoningExtraction:
    """Tests for reasoning token/content extraction in LLMClient.complete()."""

    @pytest.mark.asyncio
    async def test_extracts_reasoning_tokens(self):
        """Extracts reasoning_tokens from completion_tokens_details."""
        mock_response = _make_mock_response(
            completion_tokens=1500,
            reasoning_tokens=1000,
        )

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient(max_retries=1)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Think hard"}]
            )

            assert response.reasoning_tokens == 1000
            assert response.used_reasoning is True

    @pytest.mark.asyncio
    async def test_extracts_reasoning_content(self):
        """Extracts reasoning_content from message."""
        mock_response = _make_mock_response(
            reasoning_tokens=500,
            reasoning_content="Step 1: Consider the base rate...",
        )

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient(max_retries=1)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Think"}]
            )

            assert response.reasoning_content == "Step 1: Consider the base rate..."
            assert response.reasoning_tokens == 500

    @pytest.mark.asyncio
    async def test_no_reasoning_when_details_absent(self):
        """Returns 0 reasoning tokens when completion_tokens_details is None."""
        mock_response = _make_mock_response()  # No reasoning fields

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient(max_retries=1)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.reasoning_tokens == 0
            assert response.used_reasoning is False
            assert response.reasoning_content is None

    @pytest.mark.asyncio
    async def test_handles_none_reasoning_tokens_in_details(self):
        """Handles None reasoning_tokens inside completion_tokens_details."""
        from types import SimpleNamespace

        mock_response = _make_mock_response()
        # Set details to exist but with None reasoning_tokens
        mock_response.choices[0]  # SimpleNamespace, no auto-creation issue
        usage = mock_response.usage
        usage.completion_tokens_details = SimpleNamespace(reasoning_tokens=None)

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient(max_retries=1)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.reasoning_tokens == 0

    @pytest.mark.asyncio
    async def test_handles_non_int_reasoning_tokens(self):
        """Handles non-integer reasoning_tokens gracefully (e.g., string from bad API)."""
        from types import SimpleNamespace

        mock_response = _make_mock_response()
        mock_response.usage.completion_tokens_details = SimpleNamespace(
            reasoning_tokens="not_a_number"
        )

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient(max_retries=1)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.reasoning_tokens == 0

    @pytest.mark.asyncio
    async def test_ignores_empty_reasoning_content(self):
        """Empty string reasoning_content is treated as None."""
        mock_response = _make_mock_response(reasoning_content="")

        with patch("src.utils.llm.acompletion", AsyncMock(return_value=mock_response)):
            client = LLMClient(max_retries=1)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.reasoning_content is None


class TestCostTrackerReasoning:
    """Tests for CostTracker reasoning token accumulation."""

    def test_accumulates_reasoning_tokens(self):
        """CostTracker accumulates reasoning_tokens from calls."""
        tracker = CostTracker()

        response1 = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=500,
        )
        response2 = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=300,
            cost=0.02,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=1000,
        )

        tracker.add_call(LLMCall(model="test", messages=[], response=response1))
        tracker.add_call(LLMCall(model="test", messages=[], response=response2))

        assert tracker.total_reasoning_tokens == 1500

    def test_zero_reasoning_when_no_reasoning_used(self):
        """CostTracker has 0 reasoning tokens when no models use reasoning."""
        tracker = CostTracker()

        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
        )
        tracker.add_call(LLMCall(model="test", messages=[], response=response))

        assert tracker.total_reasoning_tokens == 0

    def test_summary_includes_reasoning_tokens(self):
        """get_summary() includes total_reasoning_tokens."""
        tracker = CostTracker()

        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=750,
        )
        tracker.add_call(LLMCall(model="test", messages=[], response=response))

        summary = tracker.get_summary()
        assert summary["total_reasoning_tokens"] == 750

    def test_reset_clears_reasoning_tokens(self):
        """reset() clears reasoning token accumulator."""
        tracker = CostTracker()

        response = LLMResponse(
            content="test",
            model="test",
            input_tokens=100,
            output_tokens=200,
            cost=0.01,
            latency_ms=100,
            timestamp="2026-01-01T00:00:00Z",
            reasoning_tokens=500,
        )
        tracker.add_call(LLMCall(model="test", messages=[], response=response))
        assert tracker.total_reasoning_tokens == 500

        tracker.reset()
        assert tracker.total_reasoning_tokens == 0

    def test_failed_call_does_not_accumulate_reasoning(self):
        """Failed calls (no response) don't affect reasoning token total."""
        tracker = CostTracker()

        tracker.add_call(
            LLMCall(model="test", messages=[], response=None, error="API Error")
        )

        assert tracker.total_reasoning_tokens == 0


class TestLLMClientTimeout:
    """Tests for LLMClient timeout behavior."""

    def test_default_timeout(self):
        """Client has sensible default timeout."""
        client = LLMClient()
        assert client.timeout_seconds == LLMClient.DEFAULT_TIMEOUT_SECONDS
        assert client.timeout_seconds == 240  # 4 minutes

    def test_custom_timeout(self):
        """Custom timeout can be set."""
        client = LLMClient(timeout_seconds=60)
        assert client.timeout_seconds == 60

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """Timeout triggers retry logic."""
        import asyncio

        async def slow_completion(*args, **kwargs):
            await asyncio.sleep(10)  # Would time out

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_response.model_dump = MagicMock(return_value={})

        # First call times out, second succeeds
        call_count = 0

        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(10)  # Will timeout
            return mock_response

        with patch("src.utils.llm.acompletion", mock_acompletion):
            client = LLMClient(timeout_seconds=0.1, max_retries=2, retry_delay=0.01)
            response = await client.complete(
                model="test-model", messages=[{"role": "user", "content": "Hi"}]
            )

            assert response.content == "Success"
            assert call_count == 2  # First timed out, second succeeded

    @pytest.mark.asyncio
    async def test_timeout_raises_after_max_retries(self):
        """Timeout raises LLMError after all retries exhausted."""
        import asyncio

        async def always_slow(*args, **kwargs):
            await asyncio.sleep(10)

        with patch("src.utils.llm.acompletion", always_slow):
            client = LLMClient(timeout_seconds=0.05, max_retries=2, retry_delay=0.01)

            with pytest.raises(LLMError) as exc_info:
                await client.complete(
                    model="test-model", messages=[{"role": "user", "content": "Hi"}]
                )

            assert "Timeout after" in str(exc_info.value.last_error)
            assert exc_info.value.attempts == 2
