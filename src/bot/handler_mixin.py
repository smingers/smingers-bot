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

# Default agent configuration (equal weights)
DEFAULT_AGENTS = [
    {"name": "forecaster_1", "model": "openrouter/anthropic/claude-sonnet-4.5", "weight": 1.0},
    {"name": "forecaster_2", "model": "openrouter/anthropic/claude-sonnet-4.5", "weight": 1.0},
    {"name": "forecaster_3", "model": "openrouter/openai/o3-mini-high", "weight": 1.0},
    {"name": "forecaster_4", "model": "openrouter/openai/o3", "weight": 1.0},
    {"name": "forecaster_5", "model": "openrouter/openai/o3", "weight": 1.0},
]


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
        3. DEFAULT_AGENTS fallback

        Returns:
            List of up to 5 agent configurations with name, model, weight.
        """
        agents = self.config.get("active_agents", [])

        if not agents:
            agents = self.config.get("ensemble", {}).get("agents", [])

        if not agents:
            agents = DEFAULT_AGENTS.copy()

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

    def _get_max_tokens(self, model: str | None = None) -> int:
        """
        Get max output tokens from config with fallback to 4000.

        Checks for model-specific overrides in llm.model_max_tokens first,
        then falls back to llm.max_output_tokens, then 4000.
        """
        llm_config = self.config.get("llm", {})
        default = llm_config.get("max_output_tokens", 4000)

        # Check for model-specific override
        if model:
            model_overrides = llm_config.get("model_max_tokens", {})
            for model_pattern, max_tokens in model_overrides.items():
                if model_pattern in model:
                    return max_tokens

        return default

    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Call a model via LLMClient.

        Args:
            model: Model identifier (e.g., "openrouter/anthropic/claude-sonnet-4.5")
            prompt: User prompt text
            system_prompt: Optional system prompt

        Returns:
            Model response content as string.

        Raises:
            Exception: If model call fails (logged and re-raised).
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.complete(
                model=model,
                messages=messages,
                system=system_prompt,
                max_tokens=self._get_max_tokens(model),
            )
            return response.content
        except Exception as e:
            logger.error(f"Model call failed ({model}): {e}")
            raise

    async def _call_model_with_metadata(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> tuple[str, dict]:
        """
        Call a model via LLMClient and return content + metadata.

        Args:
            model: Model identifier
            prompt: User prompt text
            system_prompt: Optional system prompt

        Returns:
            Tuple of (content_string, metadata_dict)

        Raises:
            Exception: If model call fails
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            max_tokens = self._get_max_tokens(model)
            response = await self.llm.complete(
                model=model,
                messages=messages,
                system=system_prompt,
                max_tokens=max_tokens,
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
                "cost": response.cost,
            }
            return response.content, metadata
        except TruncationError:
            raise  # Don't wrap TruncationError
        except Exception as e:
            logger.error(f"Model call failed ({model}): {e}")
            raise
