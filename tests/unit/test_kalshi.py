"""
Unit tests for the Kalshi source.

Tests pure functions (_parse_event_ticker, _build_resolution_criteria,
_convert_event_to_question) and client response parsing.
"""

import pytest

from src.sources.kalshi.client import KalshiEvent, KalshiMarket
from src.sources.kalshi.source import KalshiSource, _build_resolution_criteria, _parse_event_ticker

# =============================================================================
# _parse_event_ticker
# =============================================================================


class TestParseEventTicker:
    """Tests for extracting event tickers from IDs and URLs."""

    def test_direct_ticker_uppercase(self):
        assert _parse_event_ticker("KXPRESNOMD-28") == "KXPRESNOMD-28"

    def test_direct_ticker_lowercase(self):
        assert _parse_event_ticker("kxpresnomd-28") == "KXPRESNOMD-28"

    def test_direct_ticker_mixed_case(self):
        assert _parse_event_ticker("KxPresNomD-28") == "KXPRESNOMD-28"

    def test_direct_ticker_with_whitespace(self):
        assert _parse_event_ticker("  KXPRESNOMD-28  ") == "KXPRESNOMD-28"

    def test_url_full(self):
        url = "https://kalshi.com/markets/kxpresnomd/democratic-primary-winner/kxpresnomd-28"
        assert _parse_event_ticker(url) == "KXPRESNOMD-28"

    def test_url_with_trailing_slash(self):
        url = "https://kalshi.com/markets/kxpresnomd/democratic-primary-winner/kxpresnomd-28/"
        assert _parse_event_ticker(url) == "KXPRESNOMD-28"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            _parse_event_ticker("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            _parse_event_ticker("   ")

    def test_none_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            _parse_event_ticker(None)

    def test_url_with_no_event_segment(self):
        """A URL like https://kalshi.com/markets/ yields 'MARKETS' — not a real ticker but not empty."""
        # This is a degenerate input; the function doesn't validate ticker format,
        # just extracts the last path segment. The API call would fail downstream.
        result = _parse_event_ticker("https://kalshi.com/markets/")
        assert result == "MARKETS"


# =============================================================================
# KalshiMarket.from_api_response
# =============================================================================


def _make_market_data(**overrides) -> dict:
    """Create minimal market API response data with optional overrides."""
    data = {
        "ticker": "KXPRESNOMD-28-GNEW",
        "event_ticker": "KXPRESNOMD-28",
        "title": "Will Gavin Newsom be the Democratic Presidential nominee?",
        "yes_sub_title": "Gavin Newsom",
        "status": "active",
        "last_price": 31,
        "yes_bid": 30,
        "yes_ask": 31,
        "volume": 100000,
        "open_interest": 50000,
        "close_time": "2028-11-07T15:00:00Z",
        "rules_primary": "If Gavin Newsom wins and accepts the nomination, the market resolves to Yes.",
        "rules_secondary": "",
    }
    data.update(overrides)
    return data


class TestKalshiMarketParsing:
    """Tests for KalshiMarket.from_api_response."""

    def test_basic_parsing(self):
        market = KalshiMarket.from_api_response(_make_market_data())
        assert market.ticker == "KXPRESNOMD-28-GNEW"
        assert market.yes_sub_title == "Gavin Newsom"
        assert market.last_price == 31
        assert market.yes_bid == 30
        assert market.yes_ask == 31

    def test_implied_probability(self):
        market = KalshiMarket.from_api_response(_make_market_data(yes_bid=30, yes_ask=32))
        assert market.implied_probability == pytest.approx(0.31)

    def test_implied_probability_zero(self):
        market = KalshiMarket.from_api_response(_make_market_data(yes_bid=0, yes_ask=0))
        assert market.implied_probability == 0.0

    def test_missing_fields_default(self):
        market = KalshiMarket.from_api_response({})
        assert market.ticker == ""
        assert market.last_price == 0
        assert market.volume == 0

    def test_raw_preserved(self):
        data = _make_market_data()
        market = KalshiMarket.from_api_response(data)
        assert market.raw == data


# =============================================================================
# KalshiEvent.from_api_response
# =============================================================================


def _make_event_data(num_markets=3, **overrides) -> dict:
    """Create minimal event API response data with nested markets."""
    markets = []
    candidates = ["Gavin Newsom", "Kamala Harris", "Josh Shapiro"]
    prices = [31, 8, 8]

    for i in range(num_markets):
        candidate = candidates[i] if i < len(candidates) else f"Candidate {i}"
        price = prices[i] if i < len(prices) else 1
        markets.append(
            _make_market_data(
                ticker=f"KXPRESNOMD-28-C{i}",
                yes_sub_title=candidate,
                last_price=price,
                yes_bid=max(price - 1, 0),
                yes_ask=price,
                rules_primary=f"If {candidate} wins and accepts the nomination, the market resolves to Yes.",
            )
        )

    data = {
        "event": {
            "event_ticker": "KXPRESNOMD-28",
            "series_ticker": "KXPRESNOMD",
            "title": "2028 Democratic nominee for President?",
            "sub_title": "In 2028",
            "category": "Politics",
            "mutually_exclusive": True,
            "collateral_return_type": "MECNET",
            "markets": markets,
        }
    }
    if overrides:
        data["event"].update(overrides)
    return data


class TestKalshiEventParsing:
    """Tests for KalshiEvent.from_api_response."""

    def test_basic_parsing(self):
        event = KalshiEvent.from_api_response(_make_event_data())
        assert event.event_ticker == "KXPRESNOMD-28"
        assert event.title == "2028 Democratic nominee for President?"
        assert event.mutually_exclusive is True
        assert len(event.markets) == 3

    def test_markets_parsed(self):
        event = KalshiEvent.from_api_response(_make_event_data())
        assert event.markets[0].yes_sub_title == "Gavin Newsom"
        assert event.markets[1].yes_sub_title == "Kamala Harris"

    def test_no_markets(self):
        data = _make_event_data()
        data["event"]["markets"] = []
        event = KalshiEvent.from_api_response(data)
        assert event.markets == []


# =============================================================================
# _build_resolution_criteria
# =============================================================================


class TestBuildResolutionCriteria:
    """Tests for building resolution criteria from event data."""

    def test_mutually_exclusive_event(self):
        event = KalshiEvent.from_api_response(_make_event_data())
        criteria = _build_resolution_criteria(event)
        assert "mutually exclusive" in criteria
        assert "exactly one option" in criteria

    def test_resolution_rule_template(self):
        event = KalshiEvent.from_api_response(_make_event_data())
        criteria = _build_resolution_criteria(event)
        # Should generalize the candidate name to [Candidate]
        assert "[Candidate]" in criteria
        assert "Gavin Newsom" not in criteria

    def test_no_markets_returns_empty(self):
        data = _make_event_data()
        data["event"]["markets"] = []
        data["event"]["mutually_exclusive"] = False
        event = KalshiEvent.from_api_response(data)
        criteria = _build_resolution_criteria(event)
        assert criteria == ""

    def test_early_close_condition(self):
        data = _make_event_data()
        data["event"]["markets"][0]["early_close_condition"] = "Closes when nominee is selected"
        event = KalshiEvent.from_api_response(data)
        criteria = _build_resolution_criteria(event)
        assert "Early close" in criteria


# =============================================================================
# KalshiSource._convert_event_to_question
# =============================================================================


class TestConvertEventToQuestion:
    """Tests for converting Kalshi events to Question objects."""

    def _make_source(self):
        return KalshiSource(config={})

    def test_basic_conversion(self):
        source = self._make_source()
        event = KalshiEvent.from_api_response(_make_event_data())
        question = source._convert_event_to_question(event)

        assert question.id == "KXPRESNOMD-28"
        assert question.source == "kalshi"
        assert question.question_type == "multiple_choice"
        assert len(question.options) == 3

    def test_options_sorted_by_ask_price(self):
        source = self._make_source()
        event = KalshiEvent.from_api_response(_make_event_data())
        question = source._convert_event_to_question(event)

        # Gavin Newsom (ask=31) should be first, then Harris/Shapiro (ask=8)
        assert question.options[0] == "Gavin Newsom"

    def test_title_includes_subtitle(self):
        source = self._make_source()
        event = KalshiEvent.from_api_response(_make_event_data())
        question = source._convert_event_to_question(event)

        assert "In 2028" in question.title

    def test_market_prices_in_raw(self):
        source = self._make_source()
        event = KalshiEvent.from_api_response(_make_event_data())
        question = source._convert_event_to_question(event)

        market_prices = question.raw["market_prices"]
        assert "Gavin Newsom" in market_prices
        assert market_prices["Gavin Newsom"]["yes_ask"] == 31

    def test_empty_markets_raises(self):
        source = self._make_source()
        data = _make_event_data()
        data["event"]["markets"] = []
        event = KalshiEvent.from_api_response(data)

        with pytest.raises(ValueError, match="no markets"):
            source._convert_event_to_question(event)

    def test_fallback_to_ticker_when_no_sub_title(self):
        source = self._make_source()
        data = _make_event_data(num_markets=1)
        data["event"]["markets"][0]["yes_sub_title"] = ""
        event = KalshiEvent.from_api_response(data)
        question = source._convert_event_to_question(event)

        # Should fall back to ticker
        assert question.options[0] == "KXPRESNOMD-28-C0"
