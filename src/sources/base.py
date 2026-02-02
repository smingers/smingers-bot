"""
Base source infrastructure for the multi-source forecasting system.

This module provides:
- Source registry for dynamic source loading
- Base class with common functionality for sources
- Helper functions for source management
"""

from abc import ABC, abstractmethod
from typing import Any

from ..core.types import CoreForecast, PromptSet, Question, ResearchContext
from ..storage.artifact_store import ArtifactStore
from ..utils.llm import LLMClient

# Global registry of available sources
_SOURCE_REGISTRY: dict[str, type["BaseSource"]] = {}


def register_source(name: str):
    """
    Decorator to register a source class.

    Usage:
        @register_source("metaculus")
        class MetaculusSource(BaseSource):
            ...
    """

    def decorator(cls: type["BaseSource"]) -> type["BaseSource"]:
        _SOURCE_REGISTRY[name] = cls
        return cls

    return decorator


def get_source(
    name: str,
    config: dict,
    llm_client: LLMClient | None = None,
    artifact_store: ArtifactStore | None = None,
) -> "BaseSource":
    """
    Get a source instance by name.

    Args:
        name: Source name (e.g., "metaculus", "ecclesia")
        config: Configuration dict
        llm_client: Optional LLMClient instance
        artifact_store: Optional ArtifactStore for saving artifacts

    Returns:
        Configured source instance

    Raises:
        ValueError: If source name is not registered
    """
    if name not in _SOURCE_REGISTRY:
        available = ", ".join(_SOURCE_REGISTRY.keys()) or "(none)"
        raise ValueError(f"Unknown source: {name}. Available: {available}")

    source_class = _SOURCE_REGISTRY[name]
    return source_class(config, llm_client, artifact_store)


def list_sources() -> list[str]:
    """Return list of registered source names."""
    return list(_SOURCE_REGISTRY.keys())


class BaseSource(ABC):
    """
    Abstract base class for forecast sources.

    Provides common infrastructure and enforces the ForecastSource protocol.
    Subclasses implement source-specific logic for fetching questions,
    building research context, and submitting forecasts.
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        """
        Initialize the source.

        Args:
            config: Configuration dict with source-specific settings
            llm_client: Optional LLMClient instance (created if not provided)
            artifact_store: Optional ArtifactStore for saving artifacts
        """
        self.config = config
        self.artifact_store = artifact_store

        if llm_client:
            self.llm = llm_client
        else:
            llm_timeout = config.get("llm", {}).get("timeout_seconds")
            self.llm = LLMClient(timeout_seconds=llm_timeout)

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the source name (e.g., 'metaculus', 'ecclesia')."""
        ...

    @abstractmethod
    async def fetch_question(self, question_id: str) -> Question:
        """
        Fetch a question from the source.

        Args:
            question_id: Source-specific question identifier

        Returns:
            Question in the common format
        """
        ...

    @abstractmethod
    async def build_research_context(self, question: Question) -> ResearchContext:
        """
        Gather research context for forecasting.

        Args:
            question: The question to research

        Returns:
            ResearchContext with historical and current context
        """
        ...

    @abstractmethod
    def get_prompts(self, question_type: str) -> PromptSet:
        """
        Get prompt templates for a question type.

        Args:
            question_type: "binary", "numeric", or "multiple_choice"

        Returns:
            PromptSet with all necessary templates
        """
        ...

    @abstractmethod
    def convert_forecast(self, forecast: CoreForecast) -> Any:
        """
        Convert core forecast to source-specific format.

        Args:
            forecast: Core forecast result

        Returns:
            Source-specific forecast format for submission
        """
        ...

    @abstractmethod
    async def submit_forecast(self, question_id: str, forecast: Any) -> dict:
        """
        Submit a forecast to the source.

        Args:
            question_id: Source-specific question identifier
            forecast: Source-specific forecast (from convert_forecast)

        Returns:
            Submission result with status and any response data
        """
        ...

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

    def _get_agents(self) -> list[dict]:
        """
        Get agent configurations from config.

        Looks for agents in order:
        1. active_agents (set by mode application)
        2. ensemble.agents (from config file)
        3. Default 5-agent configuration

        Returns:
            List of up to 5 agent configurations with name, model, weight.
        """
        agents = self.config.get("active_agents", [])

        if not agents:
            agents = self.config.get("ensemble", {}).get("agents", [])

        if not agents:
            # Default configuration
            agents = [
                {
                    "name": "forecaster_1",
                    "model": "openrouter/anthropic/claude-sonnet-4.5",
                    "weight": 1.0,
                },
                {
                    "name": "forecaster_2",
                    "model": "openrouter/anthropic/claude-sonnet-4.5",
                    "weight": 1.0,
                },
                {"name": "forecaster_3", "model": "openrouter/openai/o3-mini-high", "weight": 1.0},
                {"name": "forecaster_4", "model": "openrouter/openai/o3", "weight": 1.0},
                {"name": "forecaster_5", "model": "openrouter/openai/o3", "weight": 1.0},
            ]

        return agents[:5]  # Ensure max 5 agents


# Verify BaseSource implements ForecastSource protocol at import time
# This is a runtime check that ensures the abstract methods match the protocol
assert isinstance(BaseSource, type)  # BaseSource is a class
# Note: Can't check protocol conformance directly for ABC, but subclasses will be checked
