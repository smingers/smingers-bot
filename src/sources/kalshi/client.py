"""
Kalshi API Client

Read-only client for fetching market and event data from the Kalshi
prediction market exchange. No authentication required for market data.

API docs: https://docs.kalshi.com
Base URL: https://api.elections.kalshi.com/trade-api/v2
"""

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"


@dataclass
class KalshiMarket:
    """
    A single Kalshi market (binary contract).

    In mutually exclusive events, each market represents one outcome
    (e.g., one candidate in a nomination race).
    """

    ticker: str
    event_ticker: str
    title: str
    yes_sub_title: str  # Short label (e.g., candidate name)
    status: str  # "active", "closed", "settled", etc.
    last_price: int  # In cents (0-100)
    yes_bid: int
    yes_ask: int
    volume: int
    open_interest: int
    close_time: str
    rules_primary: str
    rules_secondary: str
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api_response(cls, data: dict) -> "KalshiMarket":
        """Parse a market from the API response."""
        return cls(
            ticker=data.get("ticker", ""),
            event_ticker=data.get("event_ticker", ""),
            title=data.get("title", ""),
            yes_sub_title=data.get("yes_sub_title", ""),
            status=data.get("status", ""),
            last_price=data.get("last_price", 0),
            yes_bid=data.get("yes_bid", 0),
            yes_ask=data.get("yes_ask", 0),
            volume=data.get("volume", 0),
            open_interest=data.get("open_interest", 0),
            close_time=data.get("close_time", ""),
            rules_primary=data.get("rules_primary", ""),
            rules_secondary=data.get("rules_secondary", ""),
            raw=data,
        )

    @property
    def implied_probability(self) -> float:
        """Mid-price implied probability as a fraction (0-1)."""
        mid = (self.yes_bid + self.yes_ask) / 2
        return mid / 100


@dataclass
class KalshiEvent:
    """
    A Kalshi event containing one or more markets.

    Mutually exclusive events (collateral_return_type="MECNET") contain
    markets where exactly one resolves YES.
    """

    event_ticker: str
    series_ticker: str
    title: str
    sub_title: str
    category: str
    mutually_exclusive: bool
    collateral_return_type: str
    markets: list[KalshiMarket] = field(default_factory=list)
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api_response(cls, data: dict) -> "KalshiEvent":
        """Parse an event from the API response."""
        event_data = data.get("event", data)
        markets_data = event_data.get("markets", [])
        markets = [KalshiMarket.from_api_response(m) for m in markets_data]

        return cls(
            event_ticker=event_data.get("event_ticker", ""),
            series_ticker=event_data.get("series_ticker", ""),
            title=event_data.get("title", ""),
            sub_title=event_data.get("sub_title", ""),
            category=event_data.get("category", ""),
            mutually_exclusive=event_data.get("mutually_exclusive", False),
            collateral_return_type=event_data.get("collateral_return_type", ""),
            markets=markets,
            raw=data,
        )


class KalshiClient:
    """
    Read-only client for the Kalshi Trade API.

    All market data endpoints are public and require no authentication.
    Rate limit: 20 reads/second (Basic tier).
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or KALSHI_API_BASE
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def get_event(
        self,
        event_ticker: str,
        with_nested_markets: bool = True,
    ) -> KalshiEvent:
        """
        Fetch a single event by ticker.

        Args:
            event_ticker: Event identifier (e.g., "KXPRESNOMD-28")
            with_nested_markets: Include market data in response

        Returns:
            KalshiEvent with nested markets
        """
        params = {"with_nested_markets": str(with_nested_markets).lower()}
        response = await self.client.get(
            f"/events/{event_ticker}",
            params=params,
        )
        response.raise_for_status()
        return KalshiEvent.from_api_response(response.json())

    async def get_market(self, ticker: str) -> KalshiMarket:
        """
        Fetch a single market by ticker.

        Args:
            ticker: Market ticker (e.g., "KXPRESNOMD-28-GNEW")

        Returns:
            KalshiMarket object
        """
        response = await self.client.get(f"/markets/{ticker}")
        response.raise_for_status()
        data = response.json()
        return KalshiMarket.from_api_response(data.get("market", data))

    async def get_markets(
        self,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[KalshiMarket]:
        """
        Fetch markets with optional filters.

        Args:
            event_ticker: Filter by event
            series_ticker: Filter by series
            status: Filter by status (e.g., "active")
            limit: Max results (1-1000)

        Returns:
            List of KalshiMarket objects
        """
        params: dict = {"limit": limit}
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker
        if status:
            params["status"] = status

        response = await self.client.get("/markets", params=params)
        response.raise_for_status()
        data = response.json()
        return [KalshiMarket.from_api_response(m) for m in data.get("markets", [])]
