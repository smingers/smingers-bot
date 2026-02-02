"""
Core forecasting logic - source-agnostic shared components.

This module contains the shared ensemble pipeline, extraction logic,
and base types that are used across all forecast sources.
"""

from .extractors import (
    AgentResult,
    extract_binary_probability_percent,
    extract_date_percentiles_from_response,
    extract_multiple_choice_probabilities,
    extract_percentiles_from_response,
    normalize_probabilities,
)
from .types import (
    CoreForecast,
    ForecastSource,
    PromptSet,
    Question,
    ResearchContext,
)

__all__ = [
    # Types
    "Question",
    "ResearchContext",
    "CoreForecast",
    "PromptSet",
    "ForecastSource",
    # Extractors
    "AgentResult",
    "extract_binary_probability_percent",
    "extract_multiple_choice_probabilities",
    "extract_percentiles_from_response",
    "extract_date_percentiles_from_response",
    "normalize_probabilities",
]
