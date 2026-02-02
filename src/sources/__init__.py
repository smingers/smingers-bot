"""
Forecast sources - pluggable implementations for different platforms.

Each source (Metaculus, Ecclesia, etc.) implements the ForecastSource protocol
to integrate with the core forecasting engine.
"""

# Import sources to register them
from . import metaculus  # noqa: F401 - registers @register_source("metaculus")
from .base import get_source, list_sources, register_source

# Ecclesia source will be added in Phase 2
# from . import ecclesia  # noqa: F401

__all__ = [
    "get_source",
    "register_source",
    "list_sources",
]
