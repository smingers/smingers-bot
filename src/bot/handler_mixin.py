"""
Handler Mixin - Shared functionality for forecaster handlers.

Provides common methods for agent configuration, model selection,
and LLM calls that are identical across binary, numeric, and
multiple choice handlers.
"""

import logging

from ..utils.llm import LLMClient
from .exceptions import TruncationError

logger = logging.getLogger(__name__)


class ForecasterMixin:
    """
    Mixin providing shared agent/model configuration and LLM calls.

    Requires the class using this mixin to have:
    - self.config: dict with configuration
    - self.llm: LLMClient instance
    """

    config: dict
    llm: LLMClient

    def _get_agents(self) -> list[dict]:
        """
        Get agent configurations from config.

        Looks for agents in order:
        1. active_agents (set by mode application)
        2. ensemble.agents (from config file)

        Raises ValueError if no agents are configured (config.yaml is the
        single source of truth for ensemble composition).

        Returns:
            List of up to 5 agent configurations with name, model, weight.
        """
        agents = self.config.get("active_agents", [])

        if not agents:
            agents = self.config.get("ensemble", {}).get("agents", [])

        if not agents:
            raise ValueError(
                "No ensemble agents configured. "
                "Define agents in config.yaml under ensemble.fast / ensemble.quality."
            )

        return agents[:5]  # Ensure max 5 agents

    def _resolve_model(self, key: str, default: str) -> str:
        """
        Resolve which model to use from config with fallback.

        Looks for model in order:
        1. active_models[key] (set by mode application)
        2. models[key] (from config file)
        3. default parameter

        Args:
            key: Model key (e.g., "query_generator", "cheap")
            default: Fallback model if not found in config

        Returns:
            Model identifier string.
        """
        active_models = self.config.get("active_models", {})
        return active_models.get(key, self.config.get("models", {}).get(key, default))

    # Default temperatures per task type (used when config doesn't specify)
    _DEFAULT_TEMPERATURES: dict[str, float] = {
        "query_generation": 0.3,
        "article_summarization": 0.1,
        "agentic_search": 0.3,
        "forecasting": 0.5,
    }

    def _get_temperature(self, task: str) -> float:
        """
        Get the configured temperature for a given task type.

        Looks up llm.temperature.<task> in config, falling back to sensible defaults.

        Args:
            task: One of "query_generation", "article_summarization",
                  "agentic_search", "forecasting"

        Returns:
            Temperature float between 0.0 and 1.0
        """
        llm_config = self.config.get("llm", {})
        temp_config = llm_config.get("temperature", {})
        return float(temp_config.get(task, self._DEFAULT_TEMPERATURES.get(task, 0.7)))

    def _get_max_tokens(self) -> int:
        """
        Get max output tokens from config with fallback to 5000.

        Returns llm.max_output_tokens from config, defaulting to 5000.
        """
        llm_config = self.config.get("llm", {})
        return llm_config.get("max_output_tokens", 5000)

    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        Call a model via LLMClient.

        Args:
            model: Model identifier (e.g., "openrouter/anthropic/claude-sonnet-4.5")
            prompt: User prompt text
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0). If None, uses LLMClient default.

        Returns:
            Model response content as string.

        Raises:
            TruncationError: If response was truncated.
            Exception: If model call fails (logged and re-raised).
        """
        content, _ = await self._call_model_with_metadata(
            model, prompt, system_prompt, temperature=temperature
        )
        return content

    async def _call_model_with_metadata(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> tuple[str, dict]:
        """
        Call a model via LLMClient and return content + metadata.

        Args:
            model: Model identifier
            prompt: User prompt text
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0). If None, uses LLMClient default.

        Returns:
            Tuple of (content_string, metadata_dict)

        Raises:
            Exception: If model call fails
        """
        messages = [{"role": "user", "content": prompt}]

        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            max_tokens = self._get_max_tokens()
            response = await self.llm.complete(
                model=model,
                messages=messages,
                system=system_prompt,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Check for truncation - response was cut off before completion
            if response.was_truncated:
                raise TruncationError(
                    f"Response truncated after {response.output_tokens} tokens (limit: {max_tokens})",
                    output_tokens=response.output_tokens,
                    max_tokens=max_tokens,
                )

            metadata = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "reasoning_tokens": response.reasoning_tokens,
                "used_reasoning": response.used_reasoning,
                "reasoning_content": response.reasoning_content,
                "cost": response.cost,
            }
            return response.content, metadata
        except TruncationError:
            raise  # Don't wrap TruncationError
        except Exception as e:
            logger.error(f"Model call failed ({model}): {e}")
            raise
