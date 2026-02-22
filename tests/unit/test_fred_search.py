"""
Tests for FRED (Federal Reserve Economic Data) integration.

Tests cover:
- Query extraction (_extract_fred_query)
- Regex parsing of (FRED) tagged queries
- _fred_search handler with mocked fredapi
- Error handling (no API key, empty results, API exceptions)
- Config toggle (fred_enabled)
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.bot.search import GoogleScrapeResult, QuestionDetails, SearchPipeline

# ============================================================================
# Helper to mock asyncio.to_thread so it runs the function synchronously
# ============================================================================


async def _sync_to_thread(fn, *args, **kwargs):
    """Replace asyncio.to_thread: just call the function directly."""
    return fn(*args, **kwargs)


# ============================================================================
# FRED Query Extraction Tests
# ============================================================================


class TestExtractFredQuery:
    """Tests for _extract_fred_query method."""

    @pytest.fixture
    def pipeline(self):
        return SearchPipeline({})

    def test_extracts_double_quoted_term(self, pipeline):
        result = pipeline._extract_fred_query('"US unemployment rate"')
        assert result == "US unemployment rate"

    def test_extracts_single_quoted_term(self, pipeline):
        result = pipeline._extract_fred_query("'consumer price index'")
        assert result == "consumer price index"

    def test_strips_fred_data_for_prefix(self, pipeline):
        result = pipeline._extract_fred_query("FRED data for US unemployment rate")
        assert result == "US unemployment rate"

    def test_strips_fred_series_for_prefix(self, pipeline):
        result = pipeline._extract_fred_query("FRED series for GDP")
        assert result == "GDP"

    def test_strips_fred_prefix(self, pipeline):
        result = pipeline._extract_fred_query("FRED consumer price index")
        assert result == "consumer price index"

    def test_strips_economic_data_for_prefix(self, pipeline):
        result = pipeline._extract_fred_query("economic data for federal funds rate")
        assert result == "federal funds rate"

    def test_returns_series_id_unchanged(self, pipeline):
        result = pipeline._extract_fred_query("UNRATE")
        assert result == "UNRATE"

    def test_returns_plain_query_unchanged(self, pipeline):
        result = pipeline._extract_fred_query("inflation rate")
        assert result == "inflation rate"

    def test_strips_whitespace(self, pipeline):
        result = pipeline._extract_fred_query("  GDP  ")
        assert result == "GDP"

    def test_quoted_term_in_prefix(self, pipeline):
        result = pipeline._extract_fred_query('FRED data for "real GDP"')
        assert result == "real GDP"


# ============================================================================
# FRED Query Parsing (Regex) Tests
# ============================================================================


class TestFredQueryParsing:
    """Tests for parsing FRED queries from LLM responses."""

    def test_parses_fred_query(self):
        """'query' (FRED) parsed correctly."""
        response = """
Search queries:
1. unemployment rate 2025 (Google)
2. jobs report latest (Google News)
3. What are the historical trends in US unemployment? (Agent)
4. US unemployment rate (FRED)
"""
        pattern = r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED)[\)\]]'
        matches = re.findall(pattern, response)

        fred_queries = [m for m in matches if m[2] == "FRED"]
        assert len(fred_queries) == 1
        assert "US unemployment rate" in fred_queries[0][1]

    def test_parses_fred_alongside_other_sources(self):
        """FRED parsed alongside Google, Agent, etc."""
        response = """
Search queries:
1. GDP growth 2025 (Google)
2. economic outlook (Google News)
3. Analyze recent GDP trends (Agent)
4. GDP (FRED)
"""
        pattern = r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED)[\)\]]'
        matches = re.findall(pattern, response)

        sources = [m[2] for m in matches]
        assert "Google" in sources
        assert "Google News" in sources
        assert "Agent" in sources
        assert "FRED" in sources

    def test_fallback_regex_parses_fred(self):
        """Fallback regex also parses FRED queries."""
        response = "1. US unemployment rate (FRED)"
        pattern = r"(?:\d+\.\s*)?([^(\[\n]+)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED)[\)\]]"
        matches = re.findall(pattern, response)

        fred_queries = [m for m in matches if m[1] == "FRED"]
        assert len(fred_queries) == 1


# ============================================================================
# FRED Search Handler Tests
# ============================================================================


class TestFredSearch:
    """Tests for _fred_search handler method."""

    @pytest.fixture
    def pipeline(self):
        p = SearchPipeline({})
        p.fred_api_key = "test_key"
        return p

    @pytest.fixture
    def mock_search_results(self):
        """Mock FRED search results DataFrame."""
        return pd.DataFrame(
            {
                "title": ["Unemployment Rate", "Civilian Unemployment Rate"],
                "units": ["Percent", "Percent"],
                "frequency": ["Monthly", "Monthly"],
                "popularity": [95, 60],
            },
            index=["UNRATE", "LNS14000000"],
        )

    @pytest.fixture
    def mock_series_data(self):
        """Mock FRED time series data."""
        dates = pd.date_range("2024-01-01", periods=24, freq="MS")
        values = [
            3.7,
            3.7,
            3.8,
            3.9,
            4.0,
            4.0,
            4.1,
            4.2,
            4.2,
            4.1,
            4.1,
            4.0,
            4.0,
            3.9,
            3.9,
            4.0,
            4.0,
            4.1,
            4.1,
            4.2,
            4.2,
            4.1,
            4.0,
            4.1,
        ]
        return pd.Series(values, index=dates)

    @pytest.fixture
    def mock_series_info(self):
        """Mock FRED series info."""
        return {
            "title": "Unemployment Rate",
            "units": "Percent",
            "frequency": "Monthly",
        }

    @pytest.mark.asyncio
    async def test_returns_error_without_api_key(self):
        """Returns error when FRED_API_KEY not set."""
        pipeline = SearchPipeline({})
        pipeline.fred_api_key = None

        result = await pipeline._fred_search("unemployment rate")

        assert "<FREDData" in result
        assert "FRED_API_KEY not configured" in result

    @pytest.mark.asyncio
    async def test_searches_by_text_and_returns_data(
        self, pipeline, mock_search_results, mock_series_data
    ):
        """Searches FRED by text, picks top result, and returns formatted data."""
        mock_fred = MagicMock()
        mock_fred.search.return_value = mock_search_results
        mock_fred.get_series.return_value = mock_series_data

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("fredapi.Fred", return_value=mock_fred):
                result = await pipeline._fred_search("US unemployment rate")

        assert '<FREDData series="UNRATE"' in result
        assert "Unemployment Rate" in result
        assert "Units: Percent" in result
        assert "Frequency: Monthly" in result
        assert "HISTORICAL STATISTICS:" in result
        assert "RECENT CHANGES:" in result
        assert "RECENT VALUES" in result
        assert "Source: Federal Reserve Economic Data" in result

    @pytest.mark.asyncio
    async def test_direct_series_id_lookup(self, pipeline, mock_series_data, mock_series_info):
        """Directly fetches series when query looks like a series ID."""
        mock_fred = MagicMock()
        mock_fred.get_series_info.return_value = mock_series_info
        mock_fred.get_series.return_value = mock_series_data

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("fredapi.Fred", return_value=mock_fred):
                result = await pipeline._fred_search("UNRATE")

        assert '<FREDData series="UNRATE"' in result
        # search() should NOT have been called since we used direct ID
        mock_fred.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_series_id_fallback_to_search(
        self, pipeline, mock_search_results, mock_series_data
    ):
        """Falls back to text search when series ID lookup fails."""
        mock_fred = MagicMock()
        # get_series_info raises -> not a valid series ID
        mock_fred.get_series_info.side_effect = Exception("Bad series id")
        # Fallback search succeeds
        mock_fred.search.return_value = mock_search_results
        mock_fred.get_series.return_value = mock_series_data

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("fredapi.Fred", return_value=mock_fred):
                # Reset cached client so our mock is used
                pipeline._fred_client = None
                result = await pipeline._fred_search("NOTREAL")

        # Should have tried get_series_info, failed, then fallen back to search
        mock_fred.get_series_info.assert_called_once_with("NOTREAL")
        mock_fred.search.assert_called_once_with("NOTREAL")
        # Should still produce valid output from the fallback search
        assert '<FREDData series="UNRATE"' in result
        assert "Unemployment Rate" in result

    @pytest.mark.asyncio
    async def test_empty_search_results(self, pipeline):
        """Returns error message when no series found."""
        mock_fred = MagicMock()
        mock_fred.search.return_value = pd.DataFrame()

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("fredapi.Fred", return_value=mock_fred):
                result = await pipeline._fred_search("totally nonexistent indicator xyz")

        assert "No matching FRED series found" in result

    @pytest.mark.asyncio
    async def test_handles_api_exception(self, pipeline):
        """Catches and formats API exceptions."""
        mock_fred = MagicMock()
        mock_fred.search.side_effect = Exception("FRED API error")

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("fredapi.Fred", return_value=mock_fred):
                result = await pipeline._fred_search("unemployment")

        assert "<FREDData" in result
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_handles_nan_only_series(self, pipeline, mock_search_results):
        """Returns error when all values in series are NaN."""
        mock_fred = MagicMock()
        mock_fred.search.return_value = mock_search_results

        dates = pd.date_range("2024-01-01", periods=12, freq="MS")
        nan_series = pd.Series([float("nan")] * 12, index=dates)
        mock_fred.get_series.return_value = nan_series

        with patch("src.bot.search.asyncio.to_thread", side_effect=_sync_to_thread):
            with patch("fredapi.Fred", return_value=mock_fred):
                result = await pipeline._fred_search("test series")

        assert "all values are NaN" in result


# ============================================================================
# Config Toggle Tests
# ============================================================================


class TestFredConfigToggle:
    """Tests for FRED config enable/disable."""

    @pytest.fixture
    def question_details(self):
        return QuestionDetails(
            title="Test",
            resolution_criteria="Test",
            fine_print="Test",
            description="Test",
        )

    @pytest.mark.asyncio
    async def test_fred_search_not_called_when_disabled(self, question_details):
        """FRED handler is not called when fred_enabled is false."""
        config = {
            "_active_models": {},
            "models": {},
            "research": {"fred_enabled": False},
        }
        response = """
Search queries:
1. "test query" (Google)
2. US unemployment rate (FRED)
"""
        with patch.object(
            SearchPipeline,
            "_google_search_and_scrape",
            AsyncMock(return_value=GoogleScrapeResult(formatted_output="", url_results=[])),
        ):
            with patch.object(
                SearchPipeline, "_fred_search", AsyncMock(return_value="should not be called")
            ) as mock_fred:
                pipeline = SearchPipeline(config)
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                await pipeline.execute_searches_from_response(
                    response,
                    search_id="test",
                    question_details=question_details,
                )

                # _fred_search should NOT have been called
                mock_fred.assert_not_called()


# ============================================================================
# Pipeline Integration Tests (FRED routing)
# ============================================================================


class TestFredPipelineRouting:
    """Tests for FRED query routing through the pipeline."""

    @pytest.fixture
    def question_details(self):
        return QuestionDetails(
            title="What will the US unemployment rate be?",
            resolution_criteria="Based on BLS data",
            fine_print="",
            description="Economic question",
        )

    @pytest.mark.asyncio
    async def test_fred_query_routed_to_handler(self, question_details):
        """FRED queries are routed to _fred_search handler."""
        config = {
            "_active_models": {},
            "models": {},
            "research": {"fred_enabled": True},
        }
        response = """
Search queries:
1. "unemployment rate" (Google)
2. UNRATE (FRED)
"""
        fred_result = '<FREDData series="UNRATE">Test data</FREDData>'
        with patch.object(
            SearchPipeline,
            "_google_search_and_scrape",
            AsyncMock(return_value=GoogleScrapeResult(formatted_output="", url_results=[])),
        ):
            with patch.object(
                SearchPipeline, "_fred_search", AsyncMock(return_value=fred_result)
            ) as mock_fred:
                pipeline = SearchPipeline(config)
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                results, metadata = await pipeline.execute_searches_from_response(
                    response,
                    search_id="test",
                    question_details=question_details,
                )

                mock_fred.assert_called_once()
                assert "FRED" in metadata["tools_used"]
                assert "FREDData" in results

    @pytest.mark.asyncio
    async def test_fred_error_formatted_correctly(self, question_details):
        """FRED exceptions produce properly formatted error blocks."""
        config = {
            "_active_models": {},
            "models": {},
            "research": {"fred_enabled": True},
        }
        response = """
Search queries:
1. UNRATE (FRED)
"""
        with patch.object(
            SearchPipeline,
            "_fred_search",
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
            assert "<FREDData" in results
            assert "Error" in results
