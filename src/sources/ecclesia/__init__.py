"""
Ecclesia forecast source.

Handles forecasting on Ecclesia business questions using a 5-agent ensemble.
Unlike Metaculus (which uses web search), context comes from:
- Team description and history
- Resolved bets as reference classes
- Team calibration patterns
"""

from .client import AIForecast, EcclesiaBet, EcclesiaClient, EcclesiaTeam, get_client
from .prompts import (
    BINARY_INSIDE_VIEW_PROMPT,
    BINARY_OUTSIDE_VIEW_PROMPT,
    BUSINESS_FORECASTER_CONTEXT,
    CATEGORICAL_INSIDE_VIEW_PROMPT,
    CATEGORICAL_OUTSIDE_VIEW_PROMPT,
    NUMERIC_INSIDE_VIEW_PROMPT,
    NUMERIC_OUTSIDE_VIEW_PROMPT,
)
from .research import EcclesiaContext, EcclesiaContextBuilder
from .source import EcclesiaSource

__all__ = [
    # Main source
    "EcclesiaSource",
    # Client
    "EcclesiaClient",
    "EcclesiaBet",
    "EcclesiaTeam",
    "AIForecast",
    "get_client",
    # Research/Context
    "EcclesiaContextBuilder",
    "EcclesiaContext",
    # Prompts
    "BUSINESS_FORECASTER_CONTEXT",
    "BINARY_OUTSIDE_VIEW_PROMPT",
    "BINARY_INSIDE_VIEW_PROMPT",
    "NUMERIC_OUTSIDE_VIEW_PROMPT",
    "NUMERIC_INSIDE_VIEW_PROMPT",
    "CATEGORICAL_OUTSIDE_VIEW_PROMPT",
    "CATEGORICAL_INSIDE_VIEW_PROMPT",
]
