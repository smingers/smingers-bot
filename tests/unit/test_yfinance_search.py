"""
Tests for yFinance (Yahoo Finance market data) integration.

Tests cover:
- Query extraction (_extract_yfinance_query)
- Ticker resolution (_resolve_yfinance_ticker)
- Regex parsing of (yFinance) tagged queries
- _yfinance_search handler with mocked yfinance
- Error handling (invalid ticker, empty results, API exceptions)
- Config toggle (yfinance_enabled)
"""

import re
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.bot.search import QuestionDetails, SearchPipeline

# ============================================================================
# Helper to mock asyncio.to_thread so it runs the function synchronously
# ============================================================================


async def _sync_to_thread(fn, *args, **kwargs):
    """Replace asyncio.to_thread: just call the function directly."""
    return fn(*args, **kwargs)


# ============================================================================
# yFinance Query Extraction Tests
# ============================================================================


class TestExtractYfinanceQuery:
    """Tests for _extract_yfinance_query method."""

    @pytest.fixture
    def pipeline(self):
        return SearchPipeline({})

    def test_extracts_double_quoted_term(self, pipeline):
        result = pipeline._extract_yfinance_query('"AAPL"')
        assert result == "AAPL"

    def test_extracts_single_quoted_term(self, pipeline):
        result = pipeline._extract_yfinance_query("'MSFT'")
        assert result == "MSFT"

    def test_strips_yfinance_data_for_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("yFinance data for AAPL")
        assert result == "AAPL"

    def test_strips_yfinance_ticker_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("yFinance ticker TSLA")
        assert result == "TSLA"

    def test_strips_yfinance_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("yFinance NVDA")
        assert result == "NVDA"

    def test_strips_stock_data_for_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("stock data for GOOG")
        assert result == "GOOG"

    def test_strips_stock_price_for_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("stock price for AMZN")
        assert result == "AMZN"

    def test_strips_stock_price_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("stock price META")
        assert result == "META"

    def test_strips_options_data_for_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("options data for SPY")
        assert result == "SPY"

    def test_strips_market_data_for_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("market data for QQQ")
        assert result == "QQQ"

    def test_strips_ticker_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query("ticker BA")
        assert result == "BA"

    def test_returns_ticker_unchanged(self, pipeline):
        result = pipeline._extract_yfinance_query("AAPL")
        assert result == "AAPL"

    def test_returns_plain_query_unchanged(self, pipeline):
        result = pipeline._extract_yfinance_query("Apple stock")
        assert result == "Apple stock"

    def test_strips_whitespace(self, pipeline):
        result = pipeline._extract_yfinance_query("  AAPL  ")
        assert result == "AAPL"

    def test_quoted_term_in_prefix(self, pipeline):
        result = pipeline._extract_yfinance_query('yFinance data for "AAPL"')
        assert result == "AAPL"


# ============================================================================
# Ticker Resolution Tests
# ============================================================================


class TestResolveYfinanceTicker:
    """Tests for _resolve_yfinance_ticker method."""

    @pytest.fixture
    def pipeline(self):
        return SearchPipeline({})

    def test_direct_ticker(self, pipeline):
        assert pipeline._resolve_yfinance_ticker("AAPL") == "AAPL"

    def test_single_letter_ticker(self, pipeline):
        assert pipeline._resolve_yfinance_ticker("F") == "F"

    def test_ticker_with_dot(self, pipeline):
        assert pipeline._resolve_yfinance_ticker("BRK.B") == "BRK.B"

    def test_ticker_with_description(self, pipeline):
        result = pipeline._resolve_yfinance_ticker("AAPL price history")
        assert result == "AAPL"

    def test_lowercase_query_uppercased(self, pipeline):
        result = pipeline._resolve_yfinance_ticker("aapl")
        # lowercase doesn't match ticker pattern, falls to last resort
        assert result == "AAPL"

    def test_multi_word_query(self, pipeline):
        result = pipeline._resolve_yfinance_ticker("apple inc stock")
        # first word "apple" matches ticker pattern (1-5 alpha, case-insensitive)
        assert result == "APPLE"


# ============================================================================
# yFinance Query Parsing (Regex) Tests
# ============================================================================


class TestYfinanceQueryParsing:
    """Tests for parsing yFinance queries from LLM responses."""

    def test_parses_yfinance_query(self):
        """'query' (yFinance) parsed correctly."""
        response = """
Search queries:
1. S&P 500 forecast 2026 (Google)
2. stock market outlook (Google News)
3. What are the recent trends in the S&P 500? (Agent)
4. SPY (yFinance)
"""
        pattern = r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED|yFinance)[\)\]]'
        matches = re.findall(pattern, response)

        yfinance_queries = [m for m in matches if m[2] == "yFinance"]
        assert len(yfinance_queries) == 1
        assert "SPY" in yfinance_queries[0][1]

    def test_parses_yfinance_alongside_other_sources(self):
        """yFinance parsed alongside Google, Agent, FRED, etc."""
        response = """
Search queries:
1. Tesla stock price 2026 (Google)
2. Tesla earnings report (Google News)
3. Analyze Tesla delivery numbers (Agent)
4. TSLA (yFinance)
"""
        pattern = r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED|yFinance)[\)\]]'
        matches = re.findall(pattern, response)

        sources = [m[2] for m in matches]
        assert "Google" in sources
        assert "Google News" in sources
        assert "Agent" in sources
        assert "yFinance" in sources

    def test_fallback_regex_parses_yfinance(self):
        """Fallback regex also parses yFinance queries."""
        response = "1. AAPL (yFinance)"
        pattern = r"(?:\d+\.\s*)?([^(\[\n]+)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED|yFinance)[\)\]]"
        matches = re.findall(pattern, response)

        yfinance_queries = [m for m in matches if m[1] == "yFinance"]
        assert len(yfinance_queries) == 1


# ============================================================================
# yFinance Search Handler Tests
# ============================================================================


class TestYfinanceSearch:
    """Tests for _yfinance_search handler method."""

    @pytest.fixture
    def pipeline(self):
        return SearchPipeline({})

    @pytest.fixture
    def mock_ticker_info(self):
        """Mock yf.Ticker.info dict."""
        return {
            "longName": "Apple Inc.",
            "shortName": "Apple Inc.",
            "symbol": "AAPL",
            "regularMarketPrice": 187.44,
            "previousClose": 186.01,
            "marketCap": 2890000000000,
            "currency": "USD",
            "exchange": "NMS",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "fiftyTwoWeekLow": 155.00,
            "fiftyTwoWeekHigh": 199.62,
            "trailingPE": 30.2,
            "forwardPE": 28.1,
            "totalRevenue": 394330000000,
            "netIncomeToCommon": 100910000000,
            "trailingEps": 6.42,
            "dividendYield": 0.0052,
            "profitMargins": 0.256,
            "targetMeanPrice": 198.50,
            "targetLowPrice": 165.00,
            "targetHighPrice": 225.00,
            "numberOfAnalystOpinions": 38,
        }

    @pytest.fixture
    def mock_history_1y(self):
        """Mock 1-year price history DataFrame."""
        np.random.seed(42)
        dates = pd.date_range("2025-02-05", periods=252, freq="B")
        base_prices = 170 + np.cumsum(np.random.randn(252) * 1.5)
        return pd.DataFrame(
            {
                "Open": base_prices - 0.5,
                "High": base_prices + 1.0,
                "Low": base_prices - 1.0,
                "Close": base_prices,
                "Volume": np.random.randint(40000000, 60000000, 252),
            },
            index=dates,
        )

    @pytest.fixture
    def mock_history_5y(self, mock_history_1y):
        """Mock 5-year price history (reuse 1y for simplicity)."""
        return mock_history_1y

    @pytest.fixture
    def mock_options_chain(self):
        """Mock options chain data."""
        OptionChain = namedtuple("OptionChain", ["calls", "puts"])
        calls = pd.DataFrame(
            {
                "strike": [180.0, 185.0, 190.0, 195.0, 200.0],
                "impliedVolatility": [0.35, 0.30, 0.283, 0.28, 0.32],
                "openInterest": [5000, 8000, 12000, 15234, 9000],
            }
        )
        puts = pd.DataFrame(
            {
                "strike": [170.0, 175.0, 180.0, 185.0, 190.0],
                "impliedVolatility": [0.33, 0.291, 0.30, 0.31, 0.35],
                "openInterest": [6000, 12891, 10000, 7000, 4000],
            }
        )
        return OptionChain(calls=calls, puts=puts)

    @pytest.mark.asyncio
    async def test_returns_data_for_valid_ticker(
        self, pipeline, mock_ticker_info, mock_history_1y, mock_history_5y
    ):
        """Returns formatted data block for valid ticker."""
        mock_ticker = MagicMock()
        mock_ticker.info = mock_ticker_info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert '<YFinanceData ticker="AAPL"' in result
        assert "Apple Inc." in result
        assert "CURRENT PRICE" in result
        assert "187.44" in result
        assert "PRICE STATISTICS" in result
        assert "RECENT PRICE CHANGES" in result
        assert "KEY FUNDAMENTALS" in result
        assert "RECENT DAILY PRICES" in result
        assert "Source: Yahoo Finance via yfinance" in result

    @pytest.mark.asyncio
    async def test_fundamentals_section_present(self, pipeline, mock_ticker_info, mock_history_1y):
        """Output contains KEY FUNDAMENTALS section with metrics."""
        mock_ticker = MagicMock()
        mock_ticker.info = mock_ticker_info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert "Trailing P/E: 30.2" in result
        assert "Forward P/E: 28.1" in result
        assert "Revenue (TTM):" in result
        assert "EPS (TTM): $6.42" in result
        assert "Dividend Yield: 0.52%" in result
        assert "Profit Margin: 25.6%" in result

    @pytest.mark.asyncio
    async def test_analyst_targets_present(self, pipeline, mock_ticker_info, mock_history_1y):
        """Output contains ANALYST TARGETS when data available."""
        mock_ticker = MagicMock()
        mock_ticker.info = mock_ticker_info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert "ANALYST TARGETS:" in result
        assert "Mean: $198.50" in result
        assert "Low: $165.00" in result
        assert "High: $225.00" in result
        assert "Number of analysts: 38" in result

    @pytest.mark.asyncio
    async def test_analyst_targets_absent_gracefully(self, pipeline, mock_history_1y):
        """No ANALYST TARGETS section when data not available."""
        info = {"regularMarketPrice": 100.0, "currency": "USD"}
        mock_ticker = MagicMock()
        mock_ticker.info = info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("XYZ")

        assert "ANALYST TARGETS" not in result

    @pytest.mark.asyncio
    async def test_options_data_included(
        self, pipeline, mock_ticker_info, mock_history_1y, mock_options_chain
    ):
        """Output contains OPTIONS-IMPLIED DATA when options available."""
        mock_ticker = MagicMock()
        mock_ticker.info = mock_ticker_info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = ["2026-03-21"]
        mock_ticker.option_chain.return_value = mock_options_chain

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert "OPTIONS-IMPLIED DATA:" in result
        assert "ATM Implied Volatility" in result
        assert "Put/Call Open Interest Ratio" in result
        assert "Highest OI call strike" in result
        assert "Highest OI put strike" in result

    @pytest.mark.asyncio
    async def test_options_data_absent_gracefully(
        self, pipeline, mock_ticker_info, mock_history_1y
    ):
        """No OPTIONS section when options not available."""
        mock_ticker = MagicMock()
        mock_ticker.info = mock_ticker_info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []  # No options

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert "OPTIONS-IMPLIED DATA" not in result

    @pytest.mark.asyncio
    async def test_handles_invalid_ticker(self, pipeline):
        """Returns error message for invalid ticker with no data."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("ZZZZZ")

        assert "<YFinanceData" in result
        assert "No data found" in result

    @pytest.mark.asyncio
    async def test_handles_empty_history_with_info(self, pipeline, mock_ticker_info):
        """Returns partial data when history is empty but info is available."""
        mock_ticker = MagicMock()
        mock_ticker.info = mock_ticker_info
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert "<YFinanceData" in result
        assert "CURRENT PRICE" in result
        # No price stats since history is empty
        assert "PRICE STATISTICS (1-Year)" not in result

    @pytest.mark.asyncio
    async def test_handles_yfinance_exception(self, pipeline):
        """Catches and formats general exceptions."""

        def raise_error():
            raise ConnectionError("Network error")

        with patch(
            "src.bot.search.asyncio.to_thread", side_effect=ConnectionError("Network error")
        ):
            result = await pipeline._yfinance_search("AAPL")

        assert "<YFinanceData" in result
        assert "Error" in result
        assert "Network error" in result

    @pytest.mark.asyncio
    async def test_fallback_to_history_price(self, pipeline, mock_history_1y):
        """Uses last close from history when info has no current price."""
        info = {"currency": "USD", "longName": "Test Corp"}  # No regularMarketPrice
        mock_ticker = MagicMock()
        mock_ticker.info = info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("TEST")

        assert "<YFinanceData" in result
        assert "CURRENT PRICE" in result
        assert "PRICE STATISTICS" in result

    @pytest.mark.asyncio
    async def test_market_cap_formatting(self, pipeline, mock_history_1y):
        """Market cap formatted correctly for different magnitudes."""
        # Trillion
        info = {"regularMarketPrice": 100.0, "currency": "USD", "marketCap": 2.89e12}
        mock_ticker = MagicMock()
        mock_ticker.info = info
        mock_ticker.history.return_value = mock_history_1y
        mock_ticker.options = []

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                result = await pipeline._yfinance_search("AAPL")

        assert "$2.89T" in result


# ============================================================================
# Config Toggle Tests
# ============================================================================


class TestYfinanceConfigToggle:
    """Tests for yFinance config enable/disable."""

    @pytest.fixture
    def question_details(self):
        return QuestionDetails(
            title="Test",
            resolution_criteria="Test",
            fine_print="Test",
            description="Test",
        )

    @pytest.mark.asyncio
    async def test_yfinance_search_not_called_when_disabled(self, question_details):
        """yFinance handler is not called when yfinance_enabled is false."""
        config = {
            "_active_models": {},
            "models": {},
            "research": {"yfinance_enabled": False},
        }
        response = """
Search queries:
1. "test query" (Google)
2. AAPL (yFinance)
"""
        with patch.object(SearchPipeline, "_google_search_and_scrape", AsyncMock(return_value="")):
            with patch.object(
                SearchPipeline,
                "_yfinance_search",
                AsyncMock(return_value="should not be called"),
            ) as mock_yf:
                pipeline = SearchPipeline(config)
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                await pipeline.execute_searches_from_response(
                    response,
                    search_id="test",
                    question_details=question_details,
                )

                # _yfinance_search should NOT have been called
                mock_yf.assert_not_called()


# ============================================================================
# Pipeline Integration Tests (yFinance routing)
# ============================================================================


class TestYfinancePipelineRouting:
    """Tests for yFinance query routing through the pipeline."""

    @pytest.fixture
    def question_details(self):
        return QuestionDetails(
            title="What will the S&P 500 close at?",
            resolution_criteria="Based on market close data",
            fine_print="",
            description="Stock market question",
        )

    @pytest.mark.skip(
        reason="Direct yFinance routing disabled — yFinance now goes through agentic search"
    )
    @pytest.mark.asyncio
    async def test_yfinance_query_routed_to_handler(self, question_details):
        """yFinance queries are routed to _yfinance_search handler."""
        config = {
            "_active_models": {},
            "models": {},
            "research": {"yfinance_enabled": True},
        }
        response = """
Search queries:
1. "S&P 500 forecast" (Google)
2. SPY (yFinance)
"""
        yf_result = '<YFinanceData ticker="SPY">Test data</YFinanceData>'
        with patch.object(SearchPipeline, "_google_search_and_scrape", AsyncMock(return_value="")):
            with patch.object(
                SearchPipeline, "_yfinance_search", AsyncMock(return_value=yf_result)
            ) as mock_yf:
                pipeline = SearchPipeline(config)
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                results, metadata = await pipeline.execute_searches_from_response(
                    response,
                    search_id="test",
                    question_details=question_details,
                )

                mock_yf.assert_called_once()
                assert "yFinance" in metadata["tools_used"]
                assert "YFinanceData" in results

    @pytest.mark.skip(
        reason="Direct yFinance routing disabled — yFinance now goes through agentic search"
    )
    @pytest.mark.asyncio
    async def test_yfinance_error_formatted_correctly(self, question_details):
        """yFinance exceptions produce properly formatted error blocks."""
        config = {
            "_active_models": {},
            "models": {},
            "research": {"yfinance_enabled": True},
        }
        response = """
Search queries:
1. AAPL (yFinance)
"""
        with patch.object(
            SearchPipeline,
            "_yfinance_search",
            AsyncMock(side_effect=RuntimeError("Connection failed")),
        ):
            pipeline = SearchPipeline(config)
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            pipeline.http_client = mock_client

            results, metadata = await pipeline.execute_searches_from_response(
                response,
                search_id="test",
                question_details=question_details,
            )

            assert metadata["queries"][0]["success"] is False
            assert "Connection failed" in metadata["queries"][0]["error"]
            assert "<YFinanceData" in results
            assert "Error" in results
