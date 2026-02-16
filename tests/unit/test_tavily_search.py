"""
Tests for Tavily search integration.

Tests cover:
- _is_tavily_enabled() config/key checks
- _get_tavily_client() lazy initialization
- _tavily_search_and_scrape() with mocked Tavily client
- _tavily_search_agentic() with mocked Tavily client
- _tavily_extract_urls() with mocked Tavily client
- Fallback to Google when Tavily fails
- Dispatch routing in execute_searches_from_response()
- Tavily Extract in scrape_question_urls()
"""

from unittest.mock import AsyncMock, MagicMock, patch

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
                "content": "Short snippet about X and its implications. " * 20,
                "raw_content": "Full article content about X. " * 50,
                "score": 0.95,
            },
            {
                "title": "Report on X",
                "url": "https://example.com/article2",
                "content": "Another snippet about X developments and analysis. " * 15,
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


def _make_pipeline_with_mock_client(config, mock_client):
    """Create a pipeline with a pre-injected mock Tavily client."""
    p = SearchPipeline(config)
    p.tavily_api_key = "tvly-test-key"
    p._tavily_client = mock_client
    return p


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
# _get_tavily_client() Tests
# ============================================================================


class TestGetTavilyClient:
    def test_returns_cached_client(self, tavily_config):
        """Returns the same client on subsequent calls."""
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"

        mock_client = AsyncMock()
        pipeline._tavily_client = mock_client

        assert pipeline._get_tavily_client() is mock_client

    def test_returns_none_when_import_fails(self, tavily_config):
        """Returns None when tavily-python is not installed."""
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"

        with patch.dict("sys.modules", {"tavily": None}):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *args, **kwargs: (
                    (_ for _ in ()).throw(ImportError("No module named 'tavily'"))
                    if name == "tavily"
                    else __import__(name, *args, **kwargs)
                ),
            ):
                result = pipeline._get_tavily_client()

        assert result is None

    def test_creates_client_on_first_call(self, tavily_config):
        """Creates and caches a new client on first call."""
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"

        mock_instance = AsyncMock()
        mock_cls = MagicMock(return_value=mock_instance)

        with patch("tavily.AsyncTavilyClient", mock_cls):
            result = pipeline._get_tavily_client()

        assert result is mock_instance
        assert pipeline._tavily_client is mock_instance
        mock_cls.assert_called_once_with(api_key="tvly-test-key")


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
    async def test_returns_answer_and_content(
        self, tavily_config, question_details, mock_tavily_search_response
    ):
        """Tavily search returns AI answer + content directly (no summarization)."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        result = await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=False,
            question_details=question_details,
        )

        assert "tavily-answer" in result
        assert "Based on available evidence" in result
        # Content should come directly from Tavily, not from _summarize_article
        assert "Short snippet about X" in result
        assert "<Summary" in result

    @pytest.mark.asyncio
    async def test_does_not_call_summarize_article(
        self, tavily_config, question_details, mock_tavily_search_response
    ):
        """Tavily search path should NOT call _summarize_article."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)
        pipeline._summarize_article = AsyncMock(return_value="Should not appear")

        await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=False,
            question_details=question_details,
        )

        pipeline._summarize_article.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_request_raw_content(
        self, tavily_config, question_details, mock_tavily_search_response
    ):
        """Regular search should use include_raw_content=False to save cost."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=False,
            question_details=question_details,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["include_raw_content"] is False

    @pytest.mark.asyncio
    async def test_news_mode_sets_topic(
        self, tavily_config, question_details, mock_tavily_search_response
    ):
        """When is_news=True, topic should be 'news'."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=True,
            question_details=question_details,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["topic"] == "news"

    @pytest.mark.asyncio
    async def test_general_mode_sets_topic(
        self, tavily_config, question_details, mock_tavily_search_response
    ):
        """When is_news=False, topic should be 'general'."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=False,
            question_details=question_details,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["topic"] == "general"

    @pytest.mark.asyncio
    async def test_no_results_returns_message(self, tavily_config, question_details):
        """Returns fallback message when Tavily returns no results."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"results": [], "answer": None})
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        result = await pipeline._tavily_search_and_scrape(
            query="obscure query",
            is_news=False,
            question_details=question_details,
        )

        assert "No results returned from Tavily" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_google_on_error(self, tavily_config, question_details):
        """Falls back to Google search when Tavily raises an exception."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("Tavily API error"))
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)
        pipeline._google_search_and_scrape = AsyncMock(return_value="Google result")

        result = await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=False,
            question_details=question_details,
        )

        assert result == "Google result"
        pipeline._google_search_and_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_when_client_unavailable(self, tavily_config, question_details):
        """Falls back to Google when _get_tavily_client returns None."""
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"
        pipeline._tavily_client = None
        pipeline._get_tavily_client = lambda: None
        pipeline._google_search_and_scrape = AsyncMock(return_value="Google fallback")

        result = await pipeline._tavily_search_and_scrape(
            query="test query",
            is_news=False,
            question_details=question_details,
        )

        assert result == "Google fallback"

    @pytest.mark.asyncio
    async def test_skips_short_content_results(self, tavily_config, question_details):
        """Skips results with very short content."""
        mock_response = {
            "answer": None,
            "results": [
                {
                    "url": "https://example.com/1",
                    "content": "Too short.",
                    "score": 0.9,
                },
            ],
        }
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        result = await pipeline._tavily_search_and_scrape(
            query="test",
            is_news=False,
            question_details=question_details,
        )

        assert "No usable content" in result

    @pytest.mark.asyncio
    async def test_respects_max_results_config(self, question_details):
        """Uses tavily_max_results from config instead of hardcoded limit."""
        config = {
            "research": {
                "tavily_enabled": True,
                "tavily_search_depth": "basic",
                "tavily_max_results": 2,
                "tavily_include_answer": False,
                "max_content_length": 15000,
            },
            "llm": {"temperature": {}},
        }
        mock_response = {
            "answer": None,
            "results": [
                {
                    "url": f"https://example.com/{i}",
                    "content": f"Content for article {i} with enough words. " * 20,
                    "score": 0.9 - i * 0.1,
                }
                for i in range(5)
            ],
        }
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_response)
        pipeline = _make_pipeline_with_mock_client(config, mock_client)

        result = await pipeline._tavily_search_and_scrape(
            query="test",
            is_news=False,
            question_details=question_details,
        )

        # With tavily_max_results=2, should only include 2 results
        assert result.count('<Summary source="https://example.com/') == 2


# ============================================================================
# _tavily_search_agentic() Tests
# ============================================================================


class TestTavilySearchAgentic:
    @pytest.mark.asyncio
    async def test_returns_raw_content(self, tavily_config, mock_tavily_search_response):
        """Returns raw content in RawContent tags for agentic search."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        result = await pipeline._tavily_search_agentic("test query")

        assert "<RawContent" in result
        assert "example.com/article1" in result

    @pytest.mark.asyncio
    async def test_requests_raw_content(self, tavily_config, mock_tavily_search_response):
        """Agentic search should use include_raw_content=True for full page content."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_tavily_search_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        await pipeline._tavily_search_agentic("test query")

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["include_raw_content"] is True

    @pytest.mark.asyncio
    async def test_no_results(self, tavily_config):
        """Returns fallback when no results."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"results": []})
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        result = await pipeline._tavily_search_agentic("empty query")

        assert "No results from Tavily" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_google_on_error(self, tavily_config):
        """Falls back to _google_search_agentic on failure."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("API error"))
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)
        pipeline._google_search_agentic = AsyncMock(return_value="Google agentic result")

        result = await pipeline._tavily_search_agentic("test query")

        assert result == "Google agentic result"

    @pytest.mark.asyncio
    async def test_falls_back_when_client_unavailable(self, tavily_config):
        """Falls back to Google when _get_tavily_client returns None."""
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"
        pipeline._get_tavily_client = lambda: None
        pipeline._google_search_agentic = AsyncMock(return_value="Google fallback")

        result = await pipeline._tavily_search_agentic("test query")

        assert result == "Google fallback"

    @pytest.mark.asyncio
    async def test_respects_max_results_config(self):
        """Uses tavily_max_results from config instead of hardcoded limit."""
        config = {
            "research": {
                "tavily_enabled": True,
                "tavily_search_depth": "advanced",
                "tavily_max_results": 3,
                "max_content_length": 15000,
            },
            "llm": {"temperature": {}},
        }
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
        pipeline = _make_pipeline_with_mock_client(config, mock_client)

        result = await pipeline._tavily_search_agentic("test query")

        # With tavily_max_results=3, should return exactly 3 results
        assert result.count("<RawContent") == 3

    @pytest.mark.asyncio
    async def test_uses_all_results_when_config_allows(self):
        """When tavily_max_results=5 and 5 results returned, uses all 5."""
        config = {
            "research": {
                "tavily_enabled": True,
                "tavily_search_depth": "advanced",
                "tavily_max_results": 5,
                "max_content_length": 15000,
            },
            "llm": {"temperature": {}},
        }
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
        pipeline = _make_pipeline_with_mock_client(config, mock_client)

        result = await pipeline._tavily_search_agentic("test query")

        assert result.count("<RawContent") == 5


# ============================================================================
# _tavily_extract_urls() Tests
# ============================================================================


class TestTavilyExtractUrls:
    @pytest.mark.asyncio
    async def test_extracts_content_from_urls(self, tavily_config, mock_tavily_extract_response):
        """Successfully extracts content from URLs."""
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(return_value=mock_tavily_extract_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        results = await pipeline._tavily_extract_urls(
            ["https://example.com/report.pdf", "https://example.com/data-page"]
        )

        assert "https://example.com/report.pdf" in results
        assert results["https://example.com/report.pdf"]["success"] is True
        assert "Extracted PDF content" in results["https://example.com/report.pdf"]["content"]

    @pytest.mark.asyncio
    async def test_tracks_failed_extractions(self, tavily_config, mock_tavily_extract_response):
        """Records failed extraction attempts."""
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(return_value=mock_tavily_extract_response)
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        results = await pipeline._tavily_extract_urls(
            [
                "https://example.com/report.pdf",
                "https://blocked.com/page",
            ]
        )

        assert "https://blocked.com/page" in results
        assert results["https://blocked.com/page"]["success"] is False

    @pytest.mark.asyncio
    async def test_truncates_long_content(self, tavily_config):
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
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        results = await pipeline._tavily_extract_urls(["https://example.com/long"])

        content = results["https://example.com/long"]["content"]
        assert len(content) <= 15000 + len("...[truncated]")

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, tavily_config):
        """Returns empty dict on API error."""
        mock_client = AsyncMock()
        mock_client.extract = AsyncMock(side_effect=Exception("API failure"))
        pipeline = _make_pipeline_with_mock_client(tavily_config, mock_client)

        results = await pipeline._tavily_extract_urls(["https://example.com/page"])

        assert results == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_client_unavailable(self, tavily_config):
        """Returns empty dict when _get_tavily_client returns None."""
        pipeline = SearchPipeline(tavily_config)
        pipeline.tavily_api_key = "tvly-test-key"
        pipeline._get_tavily_client = lambda: None

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


# ============================================================================
# Rate Limiter Tests
# ============================================================================


class TestTavilyRateLimiter:
    def test_rate_limiter_initialized(self, tavily_config):
        """Pipeline initializes a Tavily rate limiter semaphore."""
        pipeline = SearchPipeline(tavily_config)
        assert hasattr(pipeline, "_tavily_rate_limiter")
        # Semaphore with value 2
        assert pipeline._tavily_rate_limiter._value == 2
