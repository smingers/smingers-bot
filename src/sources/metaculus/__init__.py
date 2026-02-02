"""
Metaculus forecast source.

This source handles forecasting on Metaculus questions using the existing
pipeline infrastructure. It wraps the existing handlers and API client.
"""

from .source import MetaculusSource

__all__ = ["MetaculusSource"]
