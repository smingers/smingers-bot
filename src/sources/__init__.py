"""
Question source registry.

Provides a centralized way to register and retrieve question sources.
Sources are implementations that know how to fetch questions and submit
predictions for a specific platform (Metaculus, Polymarket, etc.).
"""

from typing import Dict, Optional, Type

from .base import Question, Prediction, QuestionSource


# Registry of available sources
_sources: Dict[str, Type[QuestionSource]] = {}


def register_source(name: str, source_class: Type[QuestionSource]) -> None:
    """
    Register a new question source.

    Args:
        name: Source identifier (e.g., 'metaculus', 'polymarket')
        source_class: Class implementing QuestionSource interface
    """
    _sources[name] = source_class


def get_source(name: str, **kwargs) -> QuestionSource:
    """
    Get an instance of a registered source.

    Args:
        name: Source identifier
        **kwargs: Arguments to pass to source constructor

    Returns:
        Configured QuestionSource instance

    Raises:
        ValueError: If source name is not registered
    """
    if name not in _sources:
        available = ", ".join(_sources.keys()) if _sources else "(none registered)"
        raise ValueError(f"Unknown source '{name}'. Available: {available}")
    return _sources[name](**kwargs)


def list_sources() -> list[str]:
    """List all registered source names."""
    return list(_sources.keys())


# Import and register the Metaculus source
# This is done at module load time so it's always available
from .metaculus import MetaculusSource
register_source("metaculus", MetaculusSource)


__all__ = [
    "Question",
    "Prediction",
    "QuestionSource",
    "MetaculusSource",
    "register_source",
    "get_source",
    "list_sources",
]
