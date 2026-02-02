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

from src.bot.search import QuestionDetails, SearchPipeline

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
        with patch.object(SearchPipeline, "_google_search_and_scrape", AsyncMock(return_value="")):
            with patch.object(SearchPipeline, "_agentic_search", AsyncMock(return_value="")):
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
        with patch.object(SearchPipeline, "_google_search_and_scrape", AsyncMock(return_value="")):
            with patch.object(SearchPipeline, "_agentic_search", AsyncMock(return_value="")):
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
        with patch.object(SearchPipeline, "_google_search_and_scrape", AsyncMock(return_value="")):
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
