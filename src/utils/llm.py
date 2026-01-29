"""
LLM Wrapper with Logging and Cost Tracking

Provides a unified interface for calling various LLM providers
while logging all prompts, responses, and costs.
"""

import asyncio
import logging
import time
from typing import Optional, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime, timezone

import litellm
from litellm import acompletion

from src.bot.exceptions import LLMError

# Configure litellm
litellm.set_verbose = False

logger = logging.getLogger(__name__)


# Approximate costs per 1M tokens (as of Jan 2026)
# These are estimates - actual costs may vary
# OpenRouter pricing: https://openrouter.ai/docs/models
MODEL_COSTS = {
    # Anthropic (direct API)
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5-20251101": {"input": 5.0, "output": 25.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    # OpenAI (direct API)
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o1": {"input": 15.0, "output": 60.0},
    "o1-mini": {"input": 3.0, "output": 12.0},
    "o3": {"input": 20.0, "output": 80.0},  # Estimate
    "o3-mini": {"input": 1.10, "output": 4.40},
    # OpenRouter - Anthropic models
    "openrouter/anthropic/claude-3.5-haiku": {"input": 0.80, "output": 4.0},
    "openrouter/anthropic/claude-3.5-haiku-20241022": {"input": 0.80, "output": 4.0},
    "openrouter/anthropic/claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
    "openrouter/anthropic/claude-opus-4.5": {"input": 5.0, "output": 25.0},
    "openrouter/anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "openrouter/anthropic/claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
    "openrouter/anthropic/claude-3.5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    # OpenRouter - OpenAI models
    "openrouter/openai/gpt-5.2": {"input": 1.75, "output": 14.0},
    "openrouter/openai/gpt-4o": {"input": 2.5, "output": 10.0},
    "openrouter/openai/gpt-4o-2024-11-20": {"input": 2.5, "output": 10.0},
    "openrouter/openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openrouter/openai/gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "openrouter/openai/o1": {"input": 15.0, "output": 60.0},
    "openrouter/openai/o1-mini": {"input": 3.0, "output": 12.0},
    "openrouter/openai/o3": {"input": 2.0, "output": 8.0},
    "openrouter/openai/o3-mini": {"input": 1.10, "output": 4.40},
    "openrouter/openai/o3-mini-high": {"input": 1.10, "output": 4.40},
}


@dataclass
class LLMResponse:
    """Response from an LLM call with metadata."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: int
    timestamp: str
    raw_response: Optional[dict] = None


@dataclass
class LLMCall:
    """Record of an LLM call for logging."""
    model: str
    messages: list[dict]
    response: Optional[LLMResponse]
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CostTracker:
    """Tracks cumulative costs across LLM calls."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.calls: list[LLMCall] = []

    def add_call(self, call: LLMCall) -> None:
        """Add a call to the tracker."""
        self.calls.append(call)
        if call.response:
            self.total_input_tokens += call.response.input_tokens
            self.total_output_tokens += call.response.output_tokens
            self.total_cost += call.response.cost

    def get_summary(self) -> dict:
        """Get a summary of all costs."""
        return {
            "total_calls": len(self.calls),
            "successful_calls": len([c for c in self.calls if c.response]),
            "failed_calls": len([c for c in self.calls if c.error]),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
        }

    def reset(self) -> None:
        """Reset the tracker."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.calls = []


# Global cost tracker
_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker."""
    return _cost_tracker


def reset_cost_tracker() -> None:
    """Reset the global cost tracker."""
    _cost_tracker.reset()


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a given model and token counts."""
    costs = MODEL_COSTS.get(model, {"input": 5.0, "output": 15.0})  # Default to expensive estimate
    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]
    return input_cost + output_cost


class LLMClient:
    """
    Unified LLM client with logging, cost tracking, and retry logic.

    Usage:
        client = LLMClient()
        response = await client.complete(
            model="claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(response.content)
    """

    def __init__(
        self,
        log_calls: bool = True,
        track_costs: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.log_calls = log_calls
        self.track_costs = track_costs
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.call_history: list[LLMCall] = []

    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make a completion request to an LLM.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-5-20250929", "gpt-4o")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            system: System message (will be prepended to messages)
            **kwargs: Additional parameters passed to litellm

        Returns:
            LLMResponse with content, tokens, cost, etc.
        """
        # Prepare messages
        if system:
            messages = [{"role": "system", "content": system}] + messages

        # Retry loop
        last_error = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                # Make the API call via litellm
                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )

                latency_ms = int((time.time() - start_time) * 1000)

                # Extract response data
                content = response.choices[0].message.content
                usage = response.usage

                input_tokens = usage.prompt_tokens if usage else 0
                output_tokens = usage.completion_tokens if usage else 0
                cost = estimate_cost(model, input_tokens, output_tokens)

                llm_response = LLMResponse(
                    content=content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
                )

                # Log and track
                call = LLMCall(
                    model=model,
                    messages=messages,
                    response=llm_response,
                )
                self._log_call(call)

                return llm_response

            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        # All retries failed
        call = LLMCall(
            model=model,
            messages=messages,
            response=None,
            error=last_error,
        )
        self._log_call(call)
        raise LLMError(
            f"LLM call failed after {self.max_retries} attempts: {last_error}",
            attempts=self.max_retries,
            last_error=last_error,
        )

    def _log_call(self, call: LLMCall) -> None:
        """Log a call and update tracking."""
        self.call_history.append(call)

        if self.track_costs:
            _cost_tracker.add_call(call)

        if self.log_calls:
            if call.response:
                logger.info(
                    f"LLM call: model={call.model}, "
                    f"input_tokens={call.response.input_tokens}, "
                    f"output_tokens={call.response.output_tokens}, "
                    f"cost=${call.response.cost:.4f}, "
                    f"latency={call.response.latency_ms}ms"
                )
            else:
                logger.error(f"LLM call failed: model={call.model}, error={call.error}")

    def get_prompt_and_response(self, call_index: int = -1) -> tuple[str, str]:
        """
        Get the prompt and response from a specific call.
        Useful for saving artifacts.
        """
        if not self.call_history:
            return "", ""

        call = self.call_history[call_index]

        # Format prompt
        prompt_lines = []
        for msg in call.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt_lines.append(f"## {role.upper()}\n\n{content}")
        prompt = "\n\n".join(prompt_lines)

        # Get response
        response = call.response.content if call.response else f"ERROR: {call.error}"

        return prompt, response

    def get_all_prompts_and_responses(self) -> list[tuple[str, str]]:
        """Get all prompts and responses from this session."""
        return [self.get_prompt_and_response(i) for i in range(len(self.call_history))]

    def get_session_costs(self) -> dict:
        """Get costs for this client session only."""
        total_input = sum(c.response.input_tokens for c in self.call_history if c.response)
        total_output = sum(c.response.output_tokens for c in self.call_history if c.response)
        total_cost = sum(c.response.cost for c in self.call_history if c.response)

        return {
            "calls": len(self.call_history),
            "successful": len([c for c in self.call_history if c.response]),
            "failed": len([c for c in self.call_history if c.error]),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost": total_cost,
        }


# Convenience function for simple calls
async def complete(
    model: str,
    prompt: str,
    system: Optional[str] = None,
    **kwargs
) -> str:
    """
    Simple completion helper.

    Args:
        model: Model to use
        prompt: User prompt
        system: Optional system message
        **kwargs: Additional parameters

    Returns:
        Response content as string
    """
    client = LLMClient()
    response = await client.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        system=system,
        **kwargs
    )
    return response.content
