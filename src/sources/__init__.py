"""
Forecast sources - pluggable implementations for different platforms.

Each source (Metaculus, Ecclesia, etc.) implements the ForecastSource protocol
to integrate with the core forecasting engine.
"""

from .base import get_source, register_source

__all__ = [
    "get_source",
    "register_source",
]
