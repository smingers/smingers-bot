"""
Handler Mixin - Shared functionality for forecaster handlers.

Provides common methods for agent configuration, model selection,
and LLM calls that are identical across binary, numeric, and
multiple choice handlers.
"""

import logging
from typing import List, Optional

from ..utils.llm import LLMClient

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

    def _get_agents(self) -> List[dict]:
        """
        Get agent configurations from config.

        Looks for agents in order:
        1. _active_agents (set by mode application)
        2. ensemble.agents (from config file)
        3. DEFAULT_AGENTS fallback

        Returns:
            List of up to 5 agent configurations with name, model, weight.
        """
        agents = self.config.get("_active_agents", [])

        if not agents:
            agents = self.config.get("ensemble", {}).get("agents", [])

        if not agents:
            agents = DEFAULT_AGENTS.copy()

        return agents[:5]  # Ensure max 5 agents

    def _get_model(self, key: str, default: str) -> str:
        """
        Get model from config with fallback.

        Looks for model in order:
        1. _active_models[key] (set by mode application)
        2. models[key] (from config file)
        3. default parameter

        Args:
            key: Model key (e.g., "query_generator", "cheap")
            default: Fallback model if not found in config

        Returns:
            Model identifier string.
        """
        active_models = self.config.get("_active_models", {})
        return active_models.get(key, self.config.get("models", {}).get(key, default))

    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
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
                max_tokens=4000,
            )
            return response.content
        except Exception as e:
            logger.error(f"Model call failed ({model}): {e}")
            raise
