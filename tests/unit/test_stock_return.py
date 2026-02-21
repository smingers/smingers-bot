"""
Tests for programmatic stock return distribution computation.

Tests cover:
- Detection of stock close price questions
- Parsing ticker and dates from question metadata/title
- Trading day computation
- Return distribution computation (with mocked yFinance)
- Context formatting
- Pipeline integration (config toggle, async wrapper)
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.bot.stock_return import (
    StockReturnData,
    compute_stock_return_distribution,
    compute_trading_days,
    format_stock_return_context,
    is_stock_close_price_question,
    parse_stock_question,
    stock_return_data_to_dict,
)

# ============================================================================
# Detection Tests
# ============================================================================


class TestIsStockCloseQuestion:
    def test_detects_standard_metadata(self):
        desc = (
            "Some description about a stock. "
            '`{"format":"close_price_rises","info":{"ticker":"MCO"}}`'
        )
        assert is_stock_close_price_question(desc) is True

    def test_rejects_non_stock_question(self):
        desc = "Will the unemployment rate exceed 5% by June 2026?"
        assert is_stock_close_price_question(desc) is False

    def test_rejects_empty(self):
        assert is_stock_close_price_question("") is False

    def test_rejects_different_format(self):
        desc = '`{"format":"some_other_format","info":{"ticker":"AAPL"}}`'
        assert is_stock_close_price_question(desc) is False


# ============================================================================
# Parsing Tests
# ============================================================================


class TestParseStockQuestion:
    def test_parses_standard_question(self):
        desc = (
            "Universal Health Services, Inc. is a company listed on the S&P 500. "
            '`{"format":"close_price_rises","info":{"ticker":"UHS"}}`'
        )
        title = (
            "Will UHS's market close price on 2026-02-14 be higher "
            "than its market close price on 2026-02-02?"
        )
        result = parse_stock_question(desc, title)
        assert result == ("UHS", "2026-02-02", "2026-02-14")

    def test_parses_single_letter_ticker(self):
        desc = '`{"format":"close_price_rises","info":{"ticker":"F"}}`'
        title = (
            "Will F's market close price on 2026-03-01 be higher "
            "than its market close price on 2026-02-20?"
        )
        result = parse_stock_question(desc, title)
        assert result == ("F", "2026-02-20", "2026-03-01")

    def test_returns_none_without_metadata(self):
        desc = "Regular question without stock metadata"
        title = "Will something happen?"
        assert parse_stock_question(desc, title) is None

    def test_returns_none_without_dates_in_title(self):
        desc = '`{"format":"close_price_rises","info":{"ticker":"AAPL"}}`'
        title = "Will AAPL go up?"
        assert parse_stock_question(desc, title) is None


# ============================================================================
# Trading Days Tests
# ============================================================================


class TestComputeTradingDays:
    def test_one_week(self):
        # Mon Feb 17 to Mon Feb 24 = 5 business days
        assert compute_trading_days("2026-02-17", "2026-02-24") == 5

    def test_two_weeks(self):
        # Mon Feb 2 to Fri Feb 14 (inclusive of Mon-Fri each week)
        # Feb 2 (Mon) to Feb 14 (Sat predecessor is Fri Feb 13) = 10
        # Actually busday_count: Feb 2 to Feb 14 counts 10 business days
        result = compute_trading_days("2026-02-02", "2026-02-14")
        assert result == 10

    def test_same_day_is_zero(self):
        assert compute_trading_days("2026-02-17", "2026-02-17") == 0

    def test_weekend_span(self):
        # Friday to Monday = 1 business day
        assert compute_trading_days("2026-02-20", "2026-02-23") == 1


# ============================================================================
# Return Distribution Computation Tests (mocked yFinance)
# ============================================================================


def _make_mock_history(num_days=2520, base_price=100.0, daily_return_pct=0.04):
    """Create a synthetic price history DataFrame."""
    dates = pd.bdate_range(start="2016-01-04", periods=num_days)
    # Deterministic daily returns: base_price * (1 + r)^t
    prices = base_price * (1 + daily_return_pct / 100) ** np.arange(num_days)
    # Add some noise to make it realistic
    rng = np.random.RandomState(42)
    noise = 1 + rng.normal(0, 0.01, num_days)
    prices = prices * noise
    return pd.DataFrame({"Close": prices}, index=dates)


class TestComputeReturnDistribution:
    @pytest.fixture
    def mock_yf(self):
        """Mock yfinance.Ticker to return synthetic data."""
        with patch("yfinance.Ticker") as MockTicker:
            ticker_instance = MagicMock()
            ticker_instance.history.return_value = _make_mock_history()
            MockTicker.return_value = ticker_instance
            yield MockTicker, ticker_instance

    @pytest.mark.asyncio
    async def test_computes_distribution(self, mock_yf):
        config = {"research": {"stock_return_enabled": True, "stock_return_history_years": 10}}
        desc = '`{"format":"close_price_rises","info":{"ticker":"MCO"}}`'
        title = (
            "Will MCO's market close price on 2026-02-28 be higher "
            "than its market close price on 2026-02-17?"
        )
        result = await compute_stock_return_distribution(desc, title, config)
        assert result is not None
        assert result.ticker == "MCO"
        assert result.trading_days > 0
        assert 0 < result.positive_return_rate < 1
        assert result.sample_size > 100
        assert result.std_return > 0

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self):
        config = {"research": {"stock_return_enabled": False}}
        desc = '`{"format":"close_price_rises","info":{"ticker":"MCO"}}`'
        title = (
            "Will MCO's market close price on 2026-02-28 be higher "
            "than its market close price on 2026-02-17?"
        )
        result = await compute_stock_return_distribution(desc, title, config)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_non_stock(self):
        config = {"research": {"stock_return_enabled": True}}
        desc = "Will X happen?"
        title = "Will X happen?"
        result = await compute_stock_return_distribution(desc, title, config)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_insufficient_data(self):
        with patch("yfinance.Ticker") as MockTicker:
            ticker_instance = MagicMock()
            # Only 100 rows — below 252 minimum
            ticker_instance.history.return_value = _make_mock_history(num_days=100)
            MockTicker.return_value = ticker_instance

            config = {"research": {"stock_return_enabled": True}}
            desc = '`{"format":"close_price_rises","info":{"ticker":"MCO"}}`'
            title = (
                "Will MCO's market close price on 2026-02-28 be higher "
                "than its market close price on 2026-02-17?"
            )
            result = await compute_stock_return_distribution(desc, title, config)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_yfinance_error(self):
        with patch("yfinance.Ticker") as MockTicker:
            ticker_instance = MagicMock()
            ticker_instance.history.side_effect = Exception("API error")
            MockTicker.return_value = ticker_instance

            config = {"research": {"stock_return_enabled": True}}
            desc = '`{"format":"close_price_rises","info":{"ticker":"BAD"}}`'
            title = (
                "Will BAD's market close price on 2026-02-28 be higher "
                "than its market close price on 2026-02-17?"
            )
            result = await compute_stock_return_distribution(desc, title, config)
            assert result is None


class TestReturnDistributionStatistics:
    """Test that the computed statistics are mathematically correct."""

    def test_known_distribution(self):
        """With a steadily rising stock, positive return rate should be high."""
        # Create a stock that goes up 0.05% every day
        num_days = 2520
        dates = pd.bdate_range(start="2016-01-04", periods=num_days)
        prices = 100.0 * (1.0005 ** np.arange(num_days))
        hist = pd.DataFrame({"Close": prices}, index=dates)

        with patch("yfinance.Ticker") as MockTicker:
            ticker_instance = MagicMock()
            ticker_instance.history.return_value = hist
            MockTicker.return_value = ticker_instance

            from src.bot.stock_return import _compute_return_distribution

            result = _compute_return_distribution("TEST", "2026-02-17", "2026-02-28", 8, 10)

        assert result is not None
        # A monotonically rising stock should have ~100% positive returns
        assert result.positive_return_rate > 0.99
        assert result.mean_return > 0
        assert result.median_return > 0
        assert result.sample_size == num_days - 8

    def test_coin_flip_distribution(self):
        """With random walk, positive return rate should be ~50%."""
        rng = np.random.RandomState(123)
        num_days = 5000
        dates = pd.bdate_range(start="2006-01-04", periods=num_days)
        # Random walk with zero drift
        daily_returns = rng.normal(0, 0.01, num_days)
        prices = 100.0 * np.exp(np.cumsum(daily_returns))
        hist = pd.DataFrame({"Close": prices}, index=dates)

        with patch("yfinance.Ticker") as MockTicker:
            ticker_instance = MagicMock()
            ticker_instance.history.return_value = hist
            MockTicker.return_value = ticker_instance

            from src.bot.stock_return import _compute_return_distribution

            result = _compute_return_distribution("TEST", "2026-02-17", "2026-02-28", 5, 10)

        assert result is not None
        # Should be roughly 50% (+/- 5%)
        assert 0.45 < result.positive_return_rate < 0.55
        # Mean should be near zero
        assert abs(result.mean_return) < 1.0


# ============================================================================
# Formatting Tests
# ============================================================================


class TestFormatContext:
    @pytest.fixture
    def sample_data(self):
        return StockReturnData(
            ticker="MCO",
            start_date="2026-02-17",
            end_date="2026-02-28",
            trading_days=8,
            current_price=426.44,
            reference_price=435.00,
            return_so_far=-1.97,
            sample_size=2512,
            positive_return_rate=0.573,
            mean_return=0.31,
            median_return=0.22,
            std_return=3.42,
            percentile_5=-5.80,
            percentile_25=-1.40,
            percentile_75=2.10,
            percentile_95=5.90,
            recent_return_1m=-20.87,
            recent_return_3m=-12.40,
            volatility_30d=42.1,
        )

    def test_includes_header_and_footer(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "=== STOCK RETURN DISTRIBUTION" in ctx
        assert "=== END STOCK RETURN DISTRIBUTION ===" in ctx

    def test_includes_ticker(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "MCO" in ctx

    def test_includes_base_rate(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "57.3%" in ctx

    def test_includes_trading_days(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "8 trading days" in ctx

    def test_includes_return_so_far(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "-1.97%" in ctx
        assert "down from reference" in ctx

    def test_includes_percentiles(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "5th=" in ctx
        assert "95th=" in ctx

    def test_includes_recent_context(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "1-month trailing return" in ctx
        assert "30-day realized volatility" in ctx

    def test_handles_no_return_so_far(self, sample_data):
        sample_data.return_so_far = None
        sample_data.reference_price = None
        ctx = format_stock_return_context(sample_data)
        assert "Return so far" not in ctx

    def test_programmatic_anchor_note(self, sample_data):
        ctx = format_stock_return_context(sample_data)
        assert "PROGRAMMATIC" in ctx


# ============================================================================
# Serialization Tests
# ============================================================================


class TestSerialization:
    def test_to_dict(self):
        data = StockReturnData(
            ticker="AAPL",
            start_date="2026-02-17",
            end_date="2026-02-28",
            trading_days=8,
            current_price=200.0,
            reference_price=None,
            return_so_far=None,
            sample_size=2500,
            positive_return_rate=0.55,
            mean_return=0.3,
            median_return=0.2,
            std_return=2.0,
            percentile_5=-4.0,
            percentile_25=-1.0,
            percentile_75=1.5,
            percentile_95=4.5,
            recent_return_1m=5.0,
            recent_return_3m=10.0,
            volatility_30d=25.0,
        )
        d = stock_return_data_to_dict(data)
        assert d["ticker"] == "AAPL"
        assert d["positive_return_rate"] == 0.55
        assert d["reference_price"] is None
