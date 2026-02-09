"""
Core types for the multi-source forecasting system.

These types define the interface between the core forecasting engine
and source-specific implementations (Metaculus, Ecclesia, etc.).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class Question:
    """
    Source-agnostic question representation.

    This is the common format that all sources convert their questions to.
    The core forecaster operates on this type, not source-specific types.
    """

    # Core identification
    id: str
    source: str  # "metaculus", "ecclesia", etc.

    # Question content
    title: str
    description: str
    resolution_criteria: str
    fine_print: str = ""

    # Question type: "binary", "numeric", "multiple_choice" (or "categorical" for Ecclesia)
    question_type: str = "binary"

    # Timing
    open_time: str = ""
    scheduled_resolve_time: str = ""

    # Type-specific fields
    # For numeric questions:
    lower_bound: float | None = None
    upper_bound: float | None = None
    unit_of_measure: str = ""

    # For multiple choice / categorical:
    options: list[str] = field(default_factory=list)

    # Source-specific raw data (for debugging/submission)
    raw: dict = field(default_factory=dict)


@dataclass
class ResearchContext:
    """
    Context gathered from research for forecasting.

    Different sources gather context differently:
    - Metaculus: Web search (Google, AskNews) for historical and current news
    - Ecclesia: Team history, resolved bets, internal data
    """

    # Historical context (outside view)
    historical_context: str = ""
    historical_metadata: dict = field(default_factory=dict)

    # Current context (inside view)
    current_context: str = ""
    current_metadata: dict = field(default_factory=dict)

    # Additional source-specific context
    extra_context: dict = field(default_factory=dict)


@dataclass
class PromptSet:
    """
    Set of prompt templates for a question type.

    Each source provides customized prompts while following the
    same overall structure (query generation + outside/inside view).
    """

    # Query generation prompts
    historical_query: str
    current_query: str

    # Forecasting prompts
    outside_view: str
    inside_view: str

    # System prompt (forecaster persona/context)
    system_prompt: str = ""


@dataclass
class CoreForecast:
    """
    Core forecast result from the ensemble pipeline.

    This is the source-agnostic representation that gets converted
    to source-specific formats for submission.
    """

    # Final aggregated prediction
    # For binary: float 0-1
    # For numeric: dict with percentiles and/or CDF
    # For multiple choice: list of floats summing to 1
    prediction: Any

    # Question type that determines prediction format
    question_type: str

    # Individual agent results
    agent_results: list[Any]  # List of AgentResult

    # Context used
    historical_context: str
    current_context: str

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_cost: float = 0.0


@runtime_checkable
class ForecastSource(Protocol):
    """
    Protocol defining the interface for forecast sources.

    Each source (Metaculus, Ecclesia, etc.) implements this interface
    to integrate with the core forecasting engine.
    """

    @property
    def name(self) -> str:
        """Return the source name (e.g., 'metaculus', 'ecclesia')."""
        ...

    async def fetch_question(self, question_id: str) -> Question:
        """
        Fetch a question from the source.

        Args:
            question_id: Source-specific question identifier

        Returns:
            Question in the common format
        """
        ...

    async def build_research_context(self, question: Question) -> ResearchContext:
        """
        Gather research context for forecasting.

        Args:
            question: The question to research

        Returns:
            ResearchContext with historical and current context
        """
        ...

    def get_prompts(self, question_type: str) -> PromptSet:
        """
        Get prompt templates for a question type.

        Args:
            question_type: "binary", "numeric", or "multiple_choice"

        Returns:
            PromptSet with all necessary templates
        """
        ...

    def convert_forecast(self, forecast: CoreForecast) -> Any:
        """
        Convert core forecast to source-specific format.

        Args:
            forecast: Core forecast result

        Returns:
            Source-specific forecast format for submission
        """
        ...

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
