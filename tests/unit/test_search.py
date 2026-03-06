"""
Tests for search pipeline query parsing.

Tests cover:
- Extracting search queries from LLM responses
- Handling different query formats and sources
- Metadata tracking
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.search import (
    AgenticSearchResult,
    AgenticSearchStepData,
    AgenticStepSearchResult,
    GoogleScrapeResult,
    QuestionDetails,
    SearchPipeline,
)

# ============================================================================
# Query Parsing Tests
# ============================================================================


class TestSearchQueryParsing:
    """Tests for parsing search queries from LLM responses."""

    @pytest.fixture
    def question_details(self):
        """Sample question details for tests."""
        return QuestionDetails(
            title="Will X happen by 2026?",
            resolution_criteria="Resolves YES if X occurs.",
            fine_print="Edge cases...",
            description="Background info.",
        )

    @pytest.fixture
    def config(self):
        """Minimal config for SearchPipeline."""
        return {
            "_active_models": {},
            "models": {},
        }

    def test_parses_google_query(self, llm_search_queries_response):
        """'query' (Google) parsed correctly."""
        # Use regex to verify format matches what the code expects
        pattern = (
            r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Agent|AskNews)[\)\]]'
        )

        matches = re.findall(pattern, llm_search_queries_response)

        # Should find at least one Google query
        google_queries = [m for m in matches if m[2] == "Google"]
        assert len(google_queries) >= 1
        assert "climate change policy 2026" in google_queries[0][1]

    def test_parses_google_news_query(self, llm_search_queries_response):
        """'query' (Google News) parsed correctly."""
        pattern = (
            r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Agent|AskNews)[\)\]]'
        )

        matches = re.findall(pattern, llm_search_queries_response)

        google_news_queries = [m for m in matches if m[2] == "Google News"]
        assert len(google_news_queries) >= 1
        assert "renewable energy news" in google_news_queries[0][1]

    def test_parses_agent_query(self, llm_search_queries_response):
        """'query' (Agent) parsed correctly."""
        pattern = (
            r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Agent|AskNews)[\)\]]'
        )

        matches = re.findall(pattern, llm_search_queries_response)

        agent_queries = [m for m in matches if m[2] == "Agent"]
        assert len(agent_queries) >= 1
        assert "energy transition" in agent_queries[0][1]

    def test_parses_asknews_query(self, llm_search_queries_with_asknews):
        """'query' (AskNews) parsed correctly."""
        pattern = (
            r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Agent|AskNews)[\)\]]'
        )

        matches = re.findall(pattern, llm_search_queries_with_asknews)

        asknews_queries = [m for m in matches if m[2] == "AskNews"]
        assert len(asknews_queries) >= 1
        assert "renewable energy policy" in asknews_queries[0][1]

    def test_handles_no_queries_block(self, llm_search_queries_empty):
        """Returns empty when no 'Search queries:' block."""
        # The code looks for 'Search queries:' block
        search_block = re.search(
            r"(?:Search queries:)(.*)", llm_search_queries_empty, re.DOTALL | re.IGNORECASE
        )

        assert search_block is None

    def test_handles_malformed_queries(self, llm_search_queries_malformed):
        """Gracefully handles malformed query format."""
        pattern = (
            r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Agent|AskNews)[\)\]]'
        )

        matches = re.findall(pattern, llm_search_queries_malformed)

        # Should only find the valid query
        assert len(matches) == 1
        assert matches[0][2] == "Google"


# ============================================================================
# SearchPipeline execute_searches_from_response Tests
# ============================================================================


class TestSearchPipelineProcessQueries:
    """Tests for SearchPipeline.execute_searches_from_response()."""

    @pytest.fixture
    def question_details(self):
        """Sample question details."""
        return QuestionDetails(
            title="Test Question",
            resolution_criteria="Criteria",
            fine_print="Fine print",
            description="Description",
        )

    @pytest.fixture
    def config(self):
        """Config with disabled external services."""
        return {
            "_active_models": {},
            "models": {},
        }

    @pytest.mark.asyncio
    async def test_returns_metadata_with_tools_used(
        self, config, question_details, llm_search_queries_response
    ):
        """Metadata includes tools_used set."""
        # We need to mock the actual search methods
        mock_agentic_result = AgenticSearchResult(
            analysis="Test analysis",
            steps_taken=1,
            queries_executed=["test query"],
            step_data=[],
            error=None,
        )
        with patch.object(
            SearchPipeline,
            "_google_search_and_scrape",
            AsyncMock(return_value=GoogleScrapeResult(formatted_output="", url_results=[])),
        ):
            with patch.object(
                SearchPipeline, "_agentic_search", AsyncMock(return_value=mock_agentic_result)
            ):
                pipeline = SearchPipeline(config)
                # Mock the http_client with async-compatible aclose
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                _, metadata = await pipeline.execute_searches_from_response(
                    llm_search_queries_response,
                    search_id="test",
                    question_details=question_details,
                )

                assert "tools_used" in metadata
                assert isinstance(metadata["tools_used"], list)
                # Should have Google, Google News, Agent from the fixture
                assert "Google" in metadata["tools_used"]

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_queries(
        self, config, question_details, llm_search_queries_empty
    ):
        """Returns empty string and metadata when no queries found."""
        pipeline = SearchPipeline(config)
        # Mock the http_client with async-compatible aclose
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        pipeline.http_client = mock_client

        results, metadata = await pipeline.execute_searches_from_response(
            llm_search_queries_empty,
            search_id="test",
            question_details=question_details,
        )

        assert results == ""
        assert metadata["searched"] is False
        assert metadata["num_queries"] == 0

    @pytest.mark.asyncio
    async def test_tracks_query_count(self, config, question_details, llm_search_queries_response):
        """Metadata tracks number of queries."""
        mock_agentic_result = AgenticSearchResult(
            analysis="Test analysis",
            steps_taken=1,
            queries_executed=["test query"],
            step_data=[],
            error=None,
        )
        with patch.object(
            SearchPipeline,
            "_google_search_and_scrape",
            AsyncMock(return_value=GoogleScrapeResult(formatted_output="", url_results=[])),
        ):
            with patch.object(
                SearchPipeline, "_agentic_search", AsyncMock(return_value=mock_agentic_result)
            ):
                pipeline = SearchPipeline(config)
                # Mock the http_client with async-compatible aclose
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                _, metadata = await pipeline.execute_searches_from_response(
                    llm_search_queries_response,
                    search_id="test",
                    question_details=question_details,
                )

                assert metadata["searched"] is True
                assert metadata["num_queries"] >= 3  # Google, Google News, Agent

    @pytest.mark.asyncio
    async def test_includes_asknews_when_requested(self, config, question_details):
        """AskNews is called when include_asknews=True."""
        response = """
Search queries:
1. "test query" (Google)
"""
        with patch.object(
            SearchPipeline,
            "_google_search_and_scrape",
            AsyncMock(return_value=GoogleScrapeResult(formatted_output="", url_results=[])),
        ):
            with patch.object(
                SearchPipeline, "_call_asknews", AsyncMock(return_value="AskNews results")
            ) as mock_asknews:
                pipeline = SearchPipeline(config)
                # Mock the http_client with async-compatible aclose
                mock_client = MagicMock()
                mock_client.aclose = AsyncMock()
                pipeline.http_client = mock_client

                results, metadata = await pipeline.execute_searches_from_response(
                    response,
                    search_id="test",
                    question_details=question_details,
                    include_asknews=True,
                )

                mock_asknews.assert_called_once()
                assert "AskNews" in metadata["tools_used"]


# ============================================================================
# QuestionDetails Tests
# ============================================================================


class TestQuestionDetails:
    """Tests for QuestionDetails dataclass."""

    def test_all_fields_set(self):
        """All fields can be set."""
        qd = QuestionDetails(
            title="Title",
            resolution_criteria="Criteria",
            fine_print="Fine print",
            description="Description",
            resolution_date="2026-12-31",
        )

        assert qd.title == "Title"
        assert qd.resolution_criteria == "Criteria"
        assert qd.fine_print == "Fine print"
        assert qd.description == "Description"
        assert qd.resolution_date == "2026-12-31"

    def test_resolution_date_optional(self):
        """resolution_date defaults to None."""
        qd = QuestionDetails(
            title="Title",
            resolution_criteria="Criteria",
            fine_print="Fine print",
            description="Description",
        )

        assert qd.resolution_date is None


# ============================================================================
# Date Parsing Tests
# ============================================================================


class TestSearchDateParsing:
    """Tests for date parsing utilities in search."""

    def test_parse_date_standard(self):
        """Standard date string parsed."""
        from src.bot.search import SearchPipeline

        pipeline = SearchPipeline({})
        result = pipeline._parse_date("January 15, 2026")

        assert result == "Jan 15, 2026"

    def test_parse_date_relative(self):
        """Relative date string parsed."""
        from src.bot.search import SearchPipeline

        pipeline = SearchPipeline({})
        # "2 days ago" should parse to a valid date
        result = pipeline._parse_date("2 days ago")

        assert result != "Unknown"

    def test_parse_date_invalid(self):
        """Invalid date returns Unknown."""
        from src.bot.search import SearchPipeline

        pipeline = SearchPipeline({})
        result = pipeline._parse_date("")

        assert result == "Unknown"

    def test_is_before_resolution_date_true(self):
        """_is_before_resolution_date returns True when source is before cutoff."""
        from src.bot.search import SearchPipeline

        pipeline = SearchPipeline({})
        result = pipeline._is_before_resolution_date("Dec 31, 2026", "Jan 15, 2026")

        assert result is True

    def test_is_before_resolution_date_false(self):
        """_is_before_resolution_date returns False when source is after cutoff."""
        from src.bot.search import SearchPipeline

        pipeline = SearchPipeline({})
        result = pipeline._is_before_resolution_date("Jan 1, 2026", "Jan 15, 2026")

        assert result is False

    def test_is_before_resolution_date_unknown(self):
        """_is_before_resolution_date returns False for Unknown dates."""
        from src.bot.search import SearchPipeline

        pipeline = SearchPipeline({})
        result = pipeline._is_before_resolution_date("Dec 31, 2026", "Unknown")

        assert result is False


# ============================================================================
# Error Handling Tests
# ============================================================================


# ============================================================================
# Google Trends Term Extraction Tests
# ============================================================================


class TestExtractTrendsTerm:
    """Tests for _extract_trends_term method."""

    @pytest.fixture
    def pipeline(self):
        return SearchPipeline({})

    def test_extracts_double_quoted_term(self, pipeline):
        """Extracts term from double quotes."""
        result = pipeline._extract_trends_term('"hospital"')
        assert result == "hospital"

    def test_extracts_single_quoted_term(self, pipeline):
        """Extracts term from single quotes."""
        result = pipeline._extract_trends_term("'luigi mangione'")
        assert result == "luigi mangione"

    def test_extracts_term_after_for(self, pipeline):
        """Extracts term after 'for' keyword."""
        result = pipeline._extract_trends_term('Google Trends data for "hospital"')
        assert result == "hospital"

    def test_extracts_term_after_trends(self, pipeline):
        """Extracts term after 'trends' keyword when no quotes."""
        result = pipeline._extract_trends_term("Google Trends hospital")
        assert result == "hospital"

    def test_returns_whole_query_as_fallback(self, pipeline):
        """Returns entire query when no pattern matches."""
        result = pipeline._extract_trends_term("hospital")
        assert result == "hospital"

    def test_handles_complex_query(self, pipeline):
        """Handles complex multi-word quoted terms."""
        result = pipeline._extract_trends_term('historical data for "united healthcare"')
        assert result == "united healthcare"

    def test_strips_whitespace(self, pipeline):
        """Strips leading/trailing whitespace."""
        result = pipeline._extract_trends_term("  hospital  ")
        assert result == "hospital"


class TestGoogleTrendsQueryParsing:
    """Tests for parsing Google Trends queries from LLM responses."""

    def test_parses_google_trends_query(self):
        """'query' (Google Trends) parsed correctly."""
        response = """
Search queries:
1. test query (Google)
2. hospital (Google Trends)
3. news query (Google News)
"""
        pattern = r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews)[\)\]]'
        matches = re.findall(pattern, response)

        google_trends_queries = [m for m in matches if m[2] == "Google Trends"]
        assert len(google_trends_queries) == 1
        assert "hospital" in google_trends_queries[0][1]


class TestExtractTrendsTopic:
    """Tests for _extract_trends_topic (Google Trends pre-research detection)."""

    def test_returns_topic_for_trends_interest_change_magnitude(self):
        """Question with format trends_interest_change_magnitude and topic returns topic."""
        pipeline = SearchPipeline({})
        qd = QuestionDetails(
            title="Trends question",
            resolution_criteria="Resolves by trend value.",
            fine_print="",
            description='Background. `{"format":"trends_interest_change_magnitude","info":{"topic":"ethel kennedy","trend_start":"2026-03-04","trend_end":"2026-03-14"}}`',
        )
        assert pipeline._extract_trends_topic(qd) == "ethel kennedy"

    def test_returns_none_when_format_not_trends(self):
        """Question with other format in JSON returns None."""
        pipeline = SearchPipeline({})
        qd = QuestionDetails(
            title="Other",
            resolution_criteria="",
            fine_print="",
            description='`{"format":"other_format","info":{"topic":"foo"}}`',
        )
        assert pipeline._extract_trends_topic(qd) is None

    def test_returns_none_when_no_json_block(self):
        """Question with no backtick JSON block returns None."""
        pipeline = SearchPipeline({})
        qd = QuestionDetails(
            title="No JSON",
            resolution_criteria="",
            fine_print="",
            description="No JSON here.",
        )
        assert pipeline._extract_trends_topic(qd) is None

    def test_returns_none_for_none_question_details(self):
        """None question_details returns None."""
        pipeline = SearchPipeline({})
        assert pipeline._extract_trends_topic(None) is None


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestSearchErrorHandling:
    """Tests for error handling in search pipeline."""

    @pytest.fixture
    def config(self):
        return {}

    @pytest.fixture
    def question_details(self):
        return QuestionDetails(
            title="Test",
            resolution_criteria="Test",
            fine_print="Test",
            description="Test",
        )

    @pytest.mark.asyncio
    async def test_handles_search_exception(self, config, question_details):
        """Gracefully handles exceptions during search."""
        response = """
Search queries:
1. "test" (Google)
"""
        with patch.object(
            SearchPipeline,
            "_google_search_and_scrape",
            AsyncMock(side_effect=RuntimeError("Search failed")),
        ):
            pipeline = SearchPipeline(config)
            # Mock the http_client with async-compatible aclose
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            pipeline.http_client = mock_client

            results, metadata = await pipeline.execute_searches_from_response(
                response,
                search_id="test",
                question_details=question_details,
            )

            # Should not raise, but record error in metadata
            assert metadata["queries"][0]["success"] is False
            assert "Search failed" in metadata["queries"][0]["error"]


# ============================================================================
# URL Tracking Tests
# ============================================================================


class TestAgenticStepSearchResult:
    """Tests for the AgenticStepSearchResult dataclass and _google_search_agentic."""

    def test_dataclass_construction(self):
        """AgenticStepSearchResult holds content and url_results."""
        url_records = [
            {
                "url": "https://example.com",
                "domain": "example.com",
                "success": True,
                "status_code": 200,
                "error": None,
                "response_time_ms": 123,
                "method": "trafilatura",
                "content_chars": 5000,
                "truncated": False,
                "usage": "raw_to_agent",
            }
        ]
        result = AgenticStepSearchResult(
            content="<RawContent>text</RawContent>", url_results=url_records
        )
        assert result.content == "<RawContent>text</RawContent>"
        assert len(result.url_results) == 1
        assert result.url_results[0]["usage"] == "raw_to_agent"

    def test_empty_url_results(self):
        """AgenticStepSearchResult accepts empty url_results."""
        result = AgenticStepSearchResult(content="no urls", url_results=[])
        assert result.url_results == []

    @pytest.mark.asyncio
    async def test_google_search_agentic_returns_step_result(self):
        """_google_search_agentic returns AgenticStepSearchResult, not a plain str."""
        config = {"_active_models": {}, "models": {}, "research": {}}
        with (
            patch(
                "src.bot.search.SearchPipeline._google_search", new_callable=AsyncMock
            ) as mock_search,
            patch("src.bot.search.ConcurrentContentExtractor") as mock_extractor_cls,
        ):
            mock_search.return_value = ["https://example.com/article"]
            mock_extractor = AsyncMock()
            mock_extractor.__aenter__ = AsyncMock(return_value=mock_extractor)
            mock_extractor.__aexit__ = AsyncMock(return_value=False)
            mock_extractor.extract_content = AsyncMock(
                return_value={
                    "https://example.com/article": {
                        "success": True,
                        "content": "word " * 150,
                        "domain": "example.com",
                        "status_code": 200,
                        "error": None,
                        "response_time_ms": 200,
                        "method": "trafilatura",
                        "content_chars": 750,
                        "truncated": False,
                    }
                }
            )
            mock_extractor_cls.return_value = mock_extractor

            pipeline = SearchPipeline(config)
            result = await pipeline._google_search_agentic("hospital trends")

        assert isinstance(result, AgenticStepSearchResult)
        assert isinstance(result.content, str)
        assert len(result.url_results) == 1
        assert result.url_results[0]["url"] == "https://example.com/article"
        assert result.url_results[0]["usage"] == "raw_to_agent"
        assert result.url_results[0]["truncated"] is False

    @pytest.mark.asyncio
    async def test_google_search_agentic_blocked_domain_usage(self):
        """URLs blocked by extractor get usage='blocked'."""
        config = {"_active_models": {}, "models": {}, "research": {}}
        with (
            patch(
                "src.bot.search.SearchPipeline._google_search", new_callable=AsyncMock
            ) as mock_search,
            patch("src.bot.search.ConcurrentContentExtractor") as mock_extractor_cls,
        ):
            mock_search.return_value = ["https://twitter.com/post/123"]
            mock_extractor = AsyncMock()
            mock_extractor.__aenter__ = AsyncMock(return_value=mock_extractor)
            mock_extractor.__aexit__ = AsyncMock(return_value=False)
            mock_extractor.extract_content = AsyncMock(
                return_value={
                    "https://twitter.com/post/123": {
                        "success": False,
                        "content": None,
                        "domain": "twitter.com",
                        "status_code": None,
                        "error": "Blocked domain",
                        "response_time_ms": 0,
                        "method": None,
                        "content_chars": 0,
                        "truncated": False,
                    }
                }
            )
            mock_extractor_cls.return_value = mock_extractor

            pipeline = SearchPipeline(config)
            result = await pipeline._google_search_agentic("twitter news")

        assert isinstance(result, AgenticStepSearchResult)
        assert result.url_results[0]["usage"] == "blocked"

    @pytest.mark.asyncio
    async def test_google_search_agentic_exception_returns_step_result(self):
        """On exception, returns AgenticStepSearchResult with url_results=[]."""
        config = {"_active_models": {}, "models": {}, "research": {}}
        with patch(
            "src.bot.search.SearchPipeline._google_search",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network error"),
        ):
            pipeline = SearchPipeline(config)
            result = await pipeline._google_search_agentic("some query")

        assert isinstance(result, AgenticStepSearchResult)
        assert result.url_results == []
        assert "Error during search" in result.content


class TestAgenticSearchStepDataUrlResults:
    """Tests for url_results field on AgenticSearchStepData."""

    def test_default_url_results_is_empty_dict(self):
        """url_results defaults to {} (not shared across instances)."""
        step1 = AgenticSearchStepData(
            step_number=1,
            queries_executed=[("q1", "Google")],
            search_results_raw="raw",
            analysis_after_step="analysis",
        )
        step2 = AgenticSearchStepData(
            step_number=2,
            queries_executed=[("q2", "Google")],
            search_results_raw="raw2",
            analysis_after_step="analysis2",
        )
        # Mutating one should not affect the other
        step1.url_results["q1 (Google)"] = [{"url": "https://a.com"}]
        assert step2.url_results == {}

    def test_url_results_serialized_in_agentic_instrumentation(self):
        """url_results from AgenticSearchStepData appears in instrumentation dict."""
        url_record = {
            "url": "https://cdc.gov/report",
            "domain": "cdc.gov",
            "success": True,
            "status_code": 200,
            "error": None,
            "response_time_ms": 300,
            "method": "trafilatura",
            "content_chars": 8000,
            "truncated": False,
            "usage": "raw_to_agent",
        }
        step = AgenticSearchStepData(
            step_number=1,
            queries_executed=[("hospital data", "Google")],
            search_results_raw="<RawContent>...</RawContent>",
            analysis_after_step="Analysis here",
            url_results={"hospital data (Google)": [url_record]},
        )

        # Simulate the serialization done in execute_searches_from_response
        serialized = {
            "step_number": step.step_number,
            "queries_executed": step.queries_executed,
            "search_results_chars": len(step.search_results_raw),
            "analysis_chars": len(step.analysis_after_step),
            "url_results": step.url_results,
        }

        assert "url_results" in serialized
        assert "hospital data (Google)" in serialized["url_results"]
        records = serialized["url_results"]["hospital data (Google)"]
        assert len(records) == 1
        assert records[0]["usage"] == "raw_to_agent"
        assert records[0]["truncated"] is False
