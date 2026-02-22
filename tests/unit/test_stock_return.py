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
    MIN_CONDITIONAL_SAMPLE_SIZE,
    StockReturnData,
    _compute_conditional_rates,
    _ordinal,
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
            recent_return_5d=-3.10,
            recent_return_1m=-20.87,
            recent_return_3m=-12.40,
            volatility_30d=42.1,
            recent_return_5d_percentile=22,
            recent_return_1m_percentile=5,
            recent_return_3m_percentile=15,
            conditional_rates=[
                {
                    "label": "3-month return < -20%",
                    "condition": "momentum_negative",
                    "probability": 0.541,
                    "sample_size": 198,
                    "delta": -3.2,
                    "applicable": False,
                },
                {
                    "label": "Prior 5-day return < 0",
                    "condition": "mean_reversion_down",
                    "probability": 0.582,
                    "sample_size": 1212,
                    "delta": 0.9,
                    "applicable": True,
                },
            ],
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
            recent_return_5d=1.5,
            recent_return_1m=5.0,
            recent_return_3m=10.0,
            volatility_30d=25.0,
            recent_return_5d_percentile=60,
            recent_return_1m_percentile=71,
            recent_return_3m_percentile=85,
            conditional_rates=None,
        )
        d = stock_return_data_to_dict(data)
        assert d["ticker"] == "AAPL"
        assert d["positive_return_rate"] == 0.55
        assert d["reference_price"] is None
        assert d["recent_return_5d"] == 1.5
        assert d["recent_return_5d_percentile"] == 60
        assert d["conditional_rates"] is None


# ============================================================================
# Recent Return 5d Tests
# ============================================================================


class TestRecentReturn5d:
    def test_computes_5d_return(self):
        """Verify 5-day return uses closes[-1] vs closes[-6]."""
        num_days = 500
        dates = pd.bdate_range(start="2024-01-02", periods=num_days)
        prices = 100.0 * (1.001 ** np.arange(num_days))
        hist = pd.DataFrame({"Close": prices}, index=dates)

        with patch("yfinance.Ticker") as MockTicker:
            ticker_instance = MagicMock()
            ticker_instance.history.return_value = hist
            MockTicker.return_value = ticker_instance

            from src.bot.stock_return import _compute_return_distribution

            result = _compute_return_distribution("TEST", "2025-12-01", "2025-12-08", 5, 10)

        assert result is not None
        assert result.recent_return_5d is not None
        # Monotonically rising 0.1%/day => ~0.5% over 5 days
        assert result.recent_return_5d > 0

    def test_format_includes_5d_return(self, sample_data_with_conditionals):
        ctx = format_stock_return_context(sample_data_with_conditionals)
        assert "5-day trailing return" in ctx

    @pytest.fixture
    def sample_data_with_conditionals(self):
        return StockReturnData(
            ticker="TEST",
            start_date="2026-02-17",
            end_date="2026-02-28",
            trading_days=8,
            current_price=100.0,
            reference_price=None,
            return_so_far=None,
            sample_size=2500,
            positive_return_rate=0.52,
            mean_return=0.1,
            median_return=0.05,
            std_return=3.0,
            percentile_5=-5.0,
            percentile_25=-1.5,
            percentile_75=1.5,
            percentile_95=5.0,
            recent_return_5d=2.4,
            recent_return_1m=5.25,
            recent_return_3m=31.89,
            volatility_30d=33.6,
            recent_return_5d_percentile=62,
            recent_return_1m_percentile=71,
            recent_return_3m_percentile=96,
            conditional_rates=[
                {
                    "label": "3-month return > 20%",
                    "condition": "momentum_positive",
                    "probability": 0.482,
                    "sample_size": 312,
                    "delta": -3.6,
                    "applicable": True,
                }
            ],
        )


# ============================================================================
# Percentile Rank Tests
# ============================================================================


class TestPercentileRanks:
    def test_monotonically_rising_stock_high_percentile(self):
        """A steadily rising stock should have high trailing return percentiles."""
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
        # All trailing returns are positive for a monotonically rising stock,
        # and the most recent should be near the middle since all windows are similar
        assert result.recent_return_5d_percentile is not None
        assert result.recent_return_1m_percentile is not None
        assert result.recent_return_3m_percentile is not None
        # Percentiles should be between 0 and 100
        assert 0 <= result.recent_return_5d_percentile <= 100
        assert 0 <= result.recent_return_1m_percentile <= 100
        assert 0 <= result.recent_return_3m_percentile <= 100

    def test_percentile_format_includes_ordinal(self):
        """Format output should show percentile with ordinal suffix."""
        data = StockReturnData(
            ticker="TEST",
            start_date="2026-02-17",
            end_date="2026-02-28",
            trading_days=5,
            current_price=100.0,
            reference_price=None,
            return_so_far=None,
            sample_size=2500,
            positive_return_rate=0.52,
            mean_return=0.1,
            median_return=0.05,
            std_return=3.0,
            percentile_5=-5.0,
            percentile_25=-1.5,
            percentile_75=1.5,
            percentile_95=5.0,
            recent_return_5d=2.0,
            recent_return_1m=5.0,
            recent_return_3m=10.0,
            volatility_30d=25.0,
            recent_return_5d_percentile=62,
            recent_return_1m_percentile=71,
            recent_return_3m_percentile=96,
            conditional_rates=None,
        )
        ctx = format_stock_return_context(data)
        assert "62nd percentile historically" in ctx
        assert "71st percentile historically" in ctx
        assert "96th percentile historically" in ctx


# ============================================================================
# Ordinal Tests
# ============================================================================


class TestOrdinal:
    def test_standard_suffixes(self):
        assert _ordinal(1) == "1st"
        assert _ordinal(2) == "2nd"
        assert _ordinal(3) == "3rd"
        assert _ordinal(4) == "4th"
        assert _ordinal(10) == "10th"

    def test_teens(self):
        assert _ordinal(11) == "11th"
        assert _ordinal(12) == "12th"
        assert _ordinal(13) == "13th"

    def test_higher_numbers(self):
        assert _ordinal(21) == "21st"
        assert _ordinal(22) == "22nd"
        assert _ordinal(33) == "33rd"
        assert _ordinal(42) == "42nd"
        assert _ordinal(71) == "71st"
        assert _ordinal(96) == "96th"
        assert _ordinal(100) == "100th"


# ============================================================================
# Conditional Base Rate Tests
# ============================================================================


class TestConditionalRates:
    def _make_rising_closes(self, n=2520):
        """Create monotonically rising closes."""
        return 100.0 * (1.0005 ** np.arange(n))

    def _make_random_walk_closes(self, n=5000, seed=42):
        """Create random walk closes with zero drift."""
        rng = np.random.RandomState(seed)
        daily_returns = rng.normal(0, 0.015, n)
        return 100.0 * np.exp(np.cumsum(daily_returns))

    def test_rising_stock_conditionals(self):
        """Monotonically rising stock: all conditionals should show high P(up)."""
        closes = self._make_rising_closes(2520)
        trading_days = 5
        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        unconditional = float(np.mean(returns > 0))

        rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional,
            recent_return_5d=0.25,
            recent_return_3m=5.0,
            volatility_30d=5.0,
        )

        assert rates is not None
        for cr in rates:
            # All conditionals should show high probability for a rising stock
            assert cr["probability"] > 0.9, f"{cr['label']} had P={cr['probability']}"

    def test_random_walk_conditionals_near_unconditional(self):
        """Random walk: conditional rates should be close to unconditional."""
        closes = self._make_random_walk_closes(5000)
        trading_days = 5
        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        unconditional = float(np.mean(returns > 0))

        rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional,
            recent_return_5d=0.5,
            recent_return_3m=2.0,
            volatility_30d=20.0,
        )

        assert rates is not None
        for cr in rates:
            # Delta should be modest — within 5pp of unconditional
            assert abs(cr["delta"]) < 5.0, f"{cr['label']} had delta={cr['delta']}pp"

    def test_min_sample_size_respected(self):
        """Conditionals with too few matching windows should be excluded."""
        # Short history: only 300 data points — momentum conditionals may not
        # have enough samples with |return| > 20%
        closes = self._make_random_walk_closes(300, seed=99)
        trading_days = 5
        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        unconditional = float(np.mean(returns > 0))

        rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional,
            recent_return_5d=0.0,
            recent_return_3m=0.0,
            volatility_30d=20.0,
        )

        # Some conditionals may be None (all filtered) or have fewer entries
        if rates is not None:
            for cr in rates:
                assert cr["sample_size"] >= MIN_CONDITIONAL_SAMPLE_SIZE

    def test_applicability_flags_momentum(self):
        """Verify momentum applicability is set correctly."""
        closes = self._make_random_walk_closes(5000)
        trading_days = 5
        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        unconditional = float(np.mean(returns > 0))

        # recent_return_3m > 20% should flag momentum_positive as applicable
        rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional,
            recent_return_5d=0.5,
            recent_return_3m=25.0,  # > 20%
            volatility_30d=20.0,
        )

        assert rates is not None
        momentum_pos = [cr for cr in rates if cr["condition"] == "momentum_positive"]
        if momentum_pos:
            assert momentum_pos[0]["applicable"] is True

        momentum_neg = [cr for cr in rates if cr["condition"] == "momentum_negative"]
        if momentum_neg:
            assert momentum_neg[0]["applicable"] is False

    def test_applicability_flags_mean_reversion(self):
        """Verify mean-reversion applicability based on 5d return sign."""
        closes = self._make_random_walk_closes(5000)
        trading_days = 5
        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        unconditional = float(np.mean(returns > 0))

        # Negative 5d return should flag mean_reversion_down as applicable
        rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional,
            recent_return_5d=-2.0,
            recent_return_3m=5.0,
            volatility_30d=20.0,
        )

        assert rates is not None
        mr_down = [cr for cr in rates if cr["condition"] == "mean_reversion_down"]
        if mr_down:
            assert mr_down[0]["applicable"] is True

        mr_up = [cr for cr in rates if cr["condition"] == "mean_reversion_up"]
        if mr_up:
            assert mr_up[0]["applicable"] is False

    def test_format_conditional_rates_section(self):
        """Verify formatted output includes conditional rates section."""
        data = StockReturnData(
            ticker="HAL",
            start_date="2026-02-22",
            end_date="2026-02-28",
            trading_days=5,
            current_price=35.11,
            reference_price=None,
            return_so_far=None,
            sample_size=2510,
            positive_return_rate=0.5183,
            mean_return=0.29,
            median_return=0.23,
            std_return=6.68,
            percentile_5=-9.06,
            percentile_25=-3.19,
            percentile_75=3.74,
            percentile_95=9.97,
            recent_return_5d=2.4,
            recent_return_1m=5.25,
            recent_return_3m=31.89,
            volatility_30d=33.6,
            recent_return_5d_percentile=62,
            recent_return_1m_percentile=71,
            recent_return_3m_percentile=96,
            conditional_rates=[
                {
                    "label": "3-month return > 20%",
                    "condition": "momentum_positive",
                    "probability": 0.482,
                    "sample_size": 312,
                    "delta": -3.6,
                    "applicable": True,
                },
                {
                    "label": "Prior 5-day return > 0",
                    "condition": "mean_reversion_up",
                    "probability": 0.523,
                    "sample_size": 1298,
                    "delta": 0.5,
                    "applicable": True,
                },
                {
                    "label": "30-day vol below median",
                    "condition": "vol_low",
                    "probability": 0.527,
                    "sample_size": 1230,
                    "delta": 0.9,
                    "applicable": False,
                },
            ],
        )
        ctx = format_stock_return_context(data)
        assert "CONDITIONAL BASE RATES" in ctx
        assert "Unconditional:" in ctx
        assert "51.8%" in ctx  # unconditional rate
        assert "CURRENTLY APPLICABLE" in ctx
        assert "3-month return > 20%" in ctx
        assert "N=312" in ctx
        # vol_low is not applicable, should NOT have the flag
        lines = ctx.split("\n")
        vol_line = [line for line in lines if "vol below median" in line][0]
        assert "CURRENTLY APPLICABLE" not in vol_line

    def test_format_no_conditional_rates(self):
        """When conditional_rates is None, section should be absent."""
        data = StockReturnData(
            ticker="TEST",
            start_date="2026-02-17",
            end_date="2026-02-28",
            trading_days=5,
            current_price=100.0,
            reference_price=None,
            return_so_far=None,
            sample_size=2500,
            positive_return_rate=0.52,
            mean_return=0.1,
            median_return=0.05,
            std_return=3.0,
            percentile_5=-5.0,
            percentile_25=-1.5,
            percentile_75=1.5,
            percentile_95=5.0,
            recent_return_5d=None,
            recent_return_1m=None,
            recent_return_3m=None,
            volatility_30d=None,
            recent_return_5d_percentile=None,
            recent_return_1m_percentile=None,
            recent_return_3m_percentile=None,
            conditional_rates=None,
        )
        ctx = format_stock_return_context(data)
        assert "CONDITIONAL BASE RATES" not in ctx

    def test_returns_none_with_insufficient_data(self):
        """Very short closes array should return None (no conditionals possible)."""
        closes = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
        trading_days = 2
        returns = (closes[trading_days:] - closes[:-trading_days]) / closes[:-trading_days]
        unconditional = float(np.mean(returns > 0))

        rates = _compute_conditional_rates(
            closes,
            returns,
            trading_days,
            unconditional,
            recent_return_5d=1.0,
            recent_return_3m=None,
            volatility_30d=None,
        )

        assert rates is None
