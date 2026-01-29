"""
Abstract base classes for question sources.

Defines the contract that all question sources (Metaculus, Polymarket, etc.)
must implement to work with the forecasting pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional


# Standard question types supported by the forecasting pipeline
QuestionType = Literal["binary", "numeric", "multiple_choice", "date"]


@dataclass
class Question:
    """
    Source-agnostic question representation.

    This is the canonical format that all sources map their questions to.
    The forecasting pipeline works exclusively with this format.

    Attributes:
        id: Source-specific ID (string for flexibility across platforms)
        source: Source identifier (e.g., "metaculus", "polymarket")
        title: Question title/text
        description: Question background/context
        resolution_criteria: How the question will be resolved
        fine_print: Additional resolution details
        background_info: Extra background information
        question_type: Type of question (binary, numeric, multiple_choice, date)
        created_at: When the question was created
        open_time: When forecasting opened
        scheduled_close_time: When forecasting closes
        scheduled_resolve_time: When the question resolves
        status: Question status (open, closed, resolved, etc.)
        options: Multiple choice options (if applicable)
        unit_of_measure: Units for numeric questions
        lower_bound: Hard lower bound for numeric questions
        upper_bound: Hard upper bound for numeric questions
        open_lower_bound: Whether values below lower_bound are possible
        open_upper_bound: Whether values above upper_bound are possible
        zero_point: For log-scale numeric questions
        nominal_lower_bound: Suggested lower bound (may be tighter than hard bound)
        nominal_upper_bound: Suggested upper bound (may be tighter than hard bound)
        community_prediction: Current community/market prediction
        num_forecasters: Number of forecasters
        raw: Original source-specific data (preserved for submission)
        collection_id: Collection/tournament/category ID
    """
    # Core identification
    id: str
    source: str

    # Question content
    title: str
    description: str
    resolution_criteria: str
    fine_print: str = ""
    background_info: str = ""

    # Question type and metadata
    question_type: QuestionType = "binary"
    created_at: Optional[str] = None
    open_time: Optional[str] = None
    scheduled_close_time: Optional[str] = None
    scheduled_resolve_time: Optional[str] = None
    status: str = "open"

    # Type-specific fields
    # Multiple choice
    options: Optional[list[str]] = None

    # Numeric question bounds
    unit_of_measure: Optional[str] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    open_lower_bound: bool = False
    open_upper_bound: bool = False
    zero_point: Optional[float] = None
    nominal_lower_bound: Optional[float] = None
    nominal_upper_bound: Optional[float] = None

    # Community/market data
    community_prediction: Optional[float] = None
    num_forecasters: Optional[int] = None

    # Source-specific data (for submission formatting, etc.)
    raw: dict = field(default_factory=dict)

    # Collection/tournament info (generic)
    collection_id: Optional[str] = None


@dataclass
class Prediction:
    """
    A prediction ready for submission.

    Contains the forecast result in source-agnostic format.
    Each source's submit_prediction() method converts this to source-specific format.

    Attributes:
        question_id: ID of the question being forecasted
        question_type: Type of question
        value: Prediction value (format depends on question_type):
            - binary: float (0-1 probability)
            - numeric: list[float] (201-point CDF)
            - multiple_choice: dict[str, float] (option -> probability)
        timestamp: When the prediction was made
    """
    question_id: str
    question_type: QuestionType
    value: float | dict | list
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class QuestionSource(ABC):
    """
    Abstract base class for question sources.

    Implementations handle:
    - Fetching questions from the source
    - Converting source-specific format to generic Question
    - Submitting predictions back to the source
    - Collection/tournament management

    All methods are async to support non-blocking I/O.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the source identifier (e.g., 'metaculus', 'polymarket')."""
        pass

    @abstractmethod
    async def get_question(self, question_id: str) -> Question:
        """
        Fetch a single question by ID.

        Args:
            question_id: Source-specific question identifier

        Returns:
            Question object with all relevant fields populated
        """
        pass

    @abstractmethod
    async def get_question_by_url(self, url: str) -> Question:
        """
        Fetch a question from its URL.

        Args:
            url: Full URL to the question

        Returns:
            Question object

        Raises:
            ValueError: If URL format is not recognized
        """
        pass

    @abstractmethod
    async def get_collection_questions(
        self,
        collection_id: str,
        status: Optional[str] = "open",
        limit: int = 100,
    ) -> list[Question]:
        """
        Get questions from a collection (tournament, category, etc.).

        Args:
            collection_id: Source-specific collection identifier
            status: Filter by status (open, closed, resolved)
            limit: Maximum questions to return

        Returns:
            List of Question objects
        """
        pass

    @abstractmethod
    async def submit_prediction(
        self,
        question: Question,
        prediction: Prediction,
    ) -> dict:
        """
        Submit a prediction to the source.

        The implementation should:
        1. Convert the generic Prediction to source-specific format
        2. Apply any platform-specific constraints (e.g., probability bounds)
        3. Submit via the source's API

        Args:
            question: The question being forecasted
            prediction: The prediction to submit

        Returns:
            Source-specific response dict
        """
        pass

    @abstractmethod
    async def get_my_forecasts(
        self,
        collection_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get questions the user has already forecasted.

        Args:
            collection_id: Optional collection to filter by

        Returns:
            Dict mapping question_id to forecast info
        """
        pass

    async def close(self) -> None:
        """Clean up resources (HTTP clients, etc.)."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
