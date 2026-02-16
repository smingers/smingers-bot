"""
Tests for Tavily search integration.

Tests cover:
- _is_tavily_enabled() config/key checks
- _tavily_search_and_scrape() with mocked Tavily client
- _tavily_search_agentic() with mocked Tavily client
- _tavily_extract_urls() with mocked Tavily client
- Fallback to Google when Tavily fails
- Dispatch routing in execute_searches_from_response()
- Tavily Extract in scrape_question_urls()
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.bot.search import QuestionDetails, SearchPipeline

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def question_details():
    return QuestionDetails(
        title="Will X happen by 2026?",
        resolution_criteria="Resolves YES if X occurs before Dec 31, 2026.",
        fine_print="Based on official government data.",
        description="This question asks about X.",
        resolution_date="2026-12-31",
    )


@pytest.fixture
def tavily_config():
    """Config with Tavily enabled."""
    return {
        "research": {
            "tavily_enabled": True,
            "tavily_search_depth": "advanced",
            "tavily_max_results": 5,
            "tavily_include_answer": True,
            "tavily_extract_enabled": True,
            "max_content_length": 15000,
        },
        "models": {
            "article_summarizer": "openrouter/anthropic/claude-3.5-haiku",
        },
        "active_models": {
            "article_summarizer": "openrouter/anthropic/claude-3.5-haiku",
        },
        "llm": {
            "temperature": {
                "article_summarization": 0.1,
            },
        },
    }


@pytest.fixture
def tavily_disabled_config():
    """Config with Tavily disabled."""
    return {
        "research": {
            "tavily_enabled": False,
        },
    }


@pytest.fixture
def mock_tavily_search_response():
    """Standard Tavily search response."""
    return {
        "query": "test query",
        "answer": "Based on available evidence, X is likely to happen.",
        "results": [
            {
                "title": "Article about X",
                "url": "https://example.com/article1",
                "content": "Short snippet about X and its implications.",
                "raw_content": "Full article content about X. " * 50,
                "score": 0.95,
            },
            {
                "title": "Report on X",
                "url": "https://example.com/article2",
                "content": "Another snippet about X developments.",
                "raw_content": "Detailed report on X developments and analysis. " * 40,
                "score": 0.88,
            },
        ],
    }


@pytest.fixture
def mock_tavily_extract_response():
    """Standard Tavily extract response."""
    return {
        "results": [
            {
                "url": "https://example.com/report.pdf",
                "raw_content": "Extracted PDF content with tables and data. " * 100,
            },
            {
                "url": "https://example.com/data-page",
                "raw_content": "Extracted page content with statistics. " * 80,
            },
        ],
        "failed_results": [
            {
                "url": "https://blocked.com/page",
                "error": "Unable to extract content",
            },
        ],
    }


# ============================================================================
# _is_tavily_enabled() Tests
# ============================================================================


class TestIsTavilyEnabled:
    def test_enabled_with_key_and_config(self, tavily_config):
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"
        assert pipeline._is_tavily_enabled() is True

    def test_disabled_without_key(self, tavily_config):
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = None
        assert pipeline._is_tavily_enabled() is False

    def test_disabled_with_config_off(self, tavily_disabled_config):
        pipeline = SearchPipeline(tavily_disabled_config)
        pipeline.tavily_api_key = "tvly-test-key"
        assert pipeline._is_tavily_enabled() is False

    def test_disabled_empty_key(self, tavily_config):
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = ""
        assert pipeline._is_tavily_enabled() is False


# ============================================================================
# _tavily_search_and_scrape() Tests
# ============================================================================


class TestTavilySearchAndScrape:
    @pytest.fixture
    def pipeline(self, tavily_config):
        p = SearchPipeline(tavily_config)
        p.tavily_api_key = "tvly-test-key"
        return p

    @pytest.mark.asyncio
    async def test_returns_answer_and_summaries(
        self, pipeline, question_details, mock_tavily_search_response
    ):
        """Tavily search returns AI answer + summarized article content."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)

        # Mock the summarize call
        pipeline._summarize_article = AsyncMock(return_value="Summarized content here.")

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_and_scrape(
                query="test query",
                is_news=False,
                question_details=question_details,
            )

        assert "tavily-answer" in result
        assert "Based on available evidence" in result
        assert "Summarized content here." in result
        assert "<Summary" in result

    @pytest.mark.asyncio
    async def test_news_mode_sets_topic(
        self, pipeline, question_details, mock_tavily_search_response
    ):
        """When is_news=True, topic should be 'news'."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline._summarize_article = AsyncMock(return_value="Summary.")

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            await pipeline._tavily_search_and_scrape(
                query="test query",
                is_news=True,
                question_details=question_details,
            )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["topic"] == "news"

    @pytest.mark.asyncio
    async def test_general_mode_sets_topic(
        self, pipeline, question_details, mock_tavily_search_response
    ):
        """When is_news=False, topic should be 'general'."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline._summarize_article = AsyncMock(return_value="Summary.")

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            await pipeline._tavily_search_and_scrape(
                query="test query",
                is_news=False,
                question_details=question_details,
            )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["topic"] == "general"

    @pytest.mark.asyncio
    async def test_no_results_returns_message(self, pipeline, question_details):
        """Returns fallback message when Tavily returns no results."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"results": [], "answer": None})

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_and_scrape(
                query="obscure query",
                is_news=False,
                question_details=question_details,
            )

        assert "No results returned from Tavily" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_google_on_error(self, pipeline, question_details):
        """Falls back to Google search when Tavily raises an exception."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("Tavily API error"))

        pipeline._google_search_and_scrape = AsyncMock(return_value="Google result")

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_and_scrape(
                query="test query",
                is_news=False,
                question_details=question_details,
            )

        assert result == "Google result"
        pipeline._google_search_and_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_when_import_fails(self, pipeline, question_details):
        """Falls back to Google when tavily-python is not installed."""
        pipeline._google_search_and_scrape = AsyncMock(return_value="Google fallback")

        with patch.dict("sys.modules", {"tavily": None}):
            # Force ImportError by patching the import
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *args, **kwargs: (
                    (_ for _ in ()).throw(ImportError("No module named 'tavily'"))
                    if name == "tavily"
                    else __import__(name, *args, **kwargs)
                ),
            ):
                result = await pipeline._tavily_search_and_scrape(
                    query="test query",
                    is_news=False,
                    question_details=question_details,
                )

        assert result == "Google fallback"

    @pytest.mark.asyncio
    async def test_skips_short_content_results(self, pipeline, question_details):
        """Skips results with very short content."""
        mock_response = {
            "answer": None,
            "results": [
                {
                    "url": "https://example.com/1",
                    "content": "Too short.",
                    "raw_content": "Too short.",
                    "score": 0.9,
                },
            ],
        }
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_response)

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_and_scrape(
                query="test",
                is_news=False,
                question_details=question_details,
            )

        assert "No usable content" in result


# ============================================================================
# _tavily_search_agentic() Tests
# ============================================================================


class TestTavilySearchAgentic:
    @pytest.fixture
    def pipeline(self, tavily_config):
        p = SearchPipeline(tavily_config)
        p.tavily_api_key = "tvly-test-key"
        return p

    @pytest.mark.asyncio
    async def test_returns_raw_content(self, pipeline, mock_tavily_search_response):
        """Returns raw content in RawContent tags for agentic search."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_agentic("test query")

        assert "<RawContent" in result
        assert "example.com/article1" in result

    @pytest.mark.asyncio
    async def test_no_results(self, pipeline):
        """Returns fallback when no results."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"results": []})

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_agentic("empty query")

        assert "No results from Tavily" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_google_on_error(self, pipeline):
        """Falls back to _google_search_agentic on failure."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("API error"))

        pipeline._google_search_agentic = AsyncMock(return_value="Google agentic result")

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_agentic("test query")

        assert result == "Google agentic result"

    @pytest.mark.asyncio
    async def test_limits_to_3_results(self, pipeline):
        """Only returns up to 3 results."""
        mock_response = {
            "results": [
                {
                    "url": f"https://example.com/{i}",
                    "content": f"Content for article {i}. " * 20,
                    "raw_content": f"Full content for article {i}. " * 50,
                    "score": 0.9 - i * 0.1,
                }
                for i in range(5)
            ],
        }
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_response)

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            result = await pipeline._tavily_search_agentic("test query")

        # Count RawContent blocks
        assert result.count("<RawContent") == 3


# ============================================================================
# _tavily_extract_urls() Tests
# ============================================================================


class TestTavilyExtractUrls:
    @pytest.fixture
    def pipeline(self, tavily_config):
        p = SearchPipeline(tavily_config)
        p.tavily_api_key = "tvly-test-key"
        return p

    @pytest.mark.asyncio
    async def test_extracts_content_from_urls(self, pipeline, mock_tavily_extract_response):
        """Successfully extracts content from URLs."""
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(return_value=mock_tavily_extract_response)

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            results = await pipeline._tavily_extract_urls(
                ["https://example.com/report.pdf", "https://example.com/data-page"]
            )

        assert "https://example.com/report.pdf" in results
        assert results["https://example.com/report.pdf"]["success"] is True
        assert "Extracted PDF content" in results["https://example.com/report.pdf"]["content"]

    @pytest.mark.asyncio
    async def test_tracks_failed_extractions(self, pipeline, mock_tavily_extract_response):
        """Records failed extraction attempts."""
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(return_value=mock_tavily_extract_response)

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            results = await pipeline._tavily_extract_urls(
                [
                    "https://example.com/report.pdf",
                    "https://blocked.com/page",
                ]
            )

        assert "https://blocked.com/page" in results
        assert results["https://blocked.com/page"]["success"] is False

    @pytest.mark.asyncio
    async def test_truncates_long_content(self, pipeline):
        """Truncates content exceeding max_content_length."""
        long_content = "x" * 20000
        mock_response = {
            "results": [
                {"url": "https://example.com/long", "raw_content": long_content},
            ],
            "failed_results": [],
        }
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(return_value=mock_response)

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            results = await pipeline._tavily_extract_urls(["https://example.com/long"])

        content = results["https://example.com/long"]["content"]
        assert len(content) <= 15000 + len("...[truncated]")

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, pipeline):
        """Returns empty dict on API error."""
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(side_effect=Exception("API failure"))

        with patch("tavily.AsyncTavilyClient", return_value=mock_client):
            results = await pipeline._tavily_extract_urls(["https://example.com/page"])

        assert results == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_import_fails(self, pipeline):
        """Returns empty dict when tavily-python not installed."""
        with patch.dict("sys.modules", {"tavily": None}):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *args, **kwargs: (
                    (_ for _ in ()).throw(ImportError("No module named 'tavily'"))
                    if name == "tavily"
                    else __import__(name, *args, **kwargs)
                ),
            ):
                results = await pipeline._tavily_extract_urls(["https://example.com/page"])

        assert results == {}


# ============================================================================
# Dispatch Routing Tests
# ============================================================================


class TestTavilyDispatchRouting:
    """Test that Tavily is used when enabled in query dispatch."""

    @pytest.fixture
    def pipeline_tavily(self, tavily_config):
        p = SearchPipeline(tavily_config)
        p.tavily_api_key = "tvly-test-key"
        return p

    @pytest.fixture
    def pipeline_no_tavily(self, tavily_disabled_config):
        p = SearchPipeline(tavily_disabled_config)
        p.tavily_api_key = None
        return p

    @pytest.mark.asyncio
    async def test_google_dispatches_to_tavily_when_enabled(
        self, pipeline_tavily, question_details
    ):
        """Google queries dispatch to Tavily when enabled."""
        pipeline_tavily._tavily_search_and_scrape = AsyncMock(return_value="Tavily result")
        pipeline_tavily._google_search_and_scrape = AsyncMock(return_value="Google result")
        pipeline_tavily.http_client = AsyncMock()

        response_text = """Search queries:
1. test query (Google)
"""
        result, metadata = await pipeline_tavily.execute_searches_from_response(
            response=response_text,
            search_id="test",
            question_details=question_details,
        )

        pipeline_tavily._tavily_search_and_scrape.assert_called_once()
        pipeline_tavily._google_search_and_scrape.assert_not_called()

    @pytest.mark.asyncio
    async def test_google_dispatches_normally_when_tavily_disabled(
        self, pipeline_no_tavily, question_details
    ):
        """Google queries use standard search when Tavily is disabled."""
        pipeline_no_tavily._tavily_search_and_scrape = AsyncMock(return_value="Tavily result")
        pipeline_no_tavily._google_search_and_scrape = AsyncMock(return_value="Google result")
        pipeline_no_tavily.http_client = AsyncMock()

        response_text = """Search queries:
1. test query (Google)
"""
        result, metadata = await pipeline_no_tavily.execute_searches_from_response(
            response=response_text,
            search_id="test",
            question_details=question_details,
        )

        pipeline_no_tavily._google_search_and_scrape.assert_called_once()
        pipeline_no_tavily._tavily_search_and_scrape.assert_not_called()
