"""
Kalshi prediction market source.

Read-only source that fetches events from Kalshi's public API and
converts mutually exclusive market sets into multiple choice questions
for the forecasting pipeline. No trading or purchases.
"""

from .client import KalshiClient, KalshiEvent, KalshiMarket
from .source import KalshiSource

__all__ = [
    "KalshiSource",
    "KalshiClient",
    "KalshiEvent",
    "KalshiMarket",
]
