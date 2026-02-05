"""
Forecast sources - pluggable implementations for different platforms.

Each source (Metaculus, Ecclesia, etc.) implements the ForecastSource protocol
to integrate with the core forecasting engine.
"""

# Import sources to register them
from . import (
    ecclesia,  # noqa: F401 - registers @register_source("ecclesia")
    kalshi,  # noqa: F401 - registers @register_source("kalshi")
    local,  # noqa: F401 - registers @register_source("local")
    metaculus,  # noqa: F401 - registers @register_source("metaculus")
)
from .base import get_source, list_sources, register_source

__all__ = [
    "get_source",
    "register_source",
    "list_sources",
]
