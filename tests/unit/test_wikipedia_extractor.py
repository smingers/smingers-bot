"""
Tests for Wikipedia API extraction and Google Trends blocking.

Tests the ConcurrentContentExtractor's Wikipedia-specific fetching via
the MediaWiki API, and verifies Google Trends URLs are blocked.
"""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bot.content_extractor import ConcurrentContentExtractor

# ---------------------------------------------------------------------------
# _is_wikipedia_url tests
# ---------------------------------------------------------------------------


class TestIsWikipediaUrl:
    def test_standard_article(self):
        assert ConcurrentContentExtractor._is_wikipedia_url(
            "https://en.wikipedia.org/wiki/Python_(programming_language)"
        )

    def test_special_statistics(self):
        assert ConcurrentContentExtractor._is_wikipedia_url(
            "https://en.wikipedia.org/wiki/Special:Statistics"
        )

    def test_non_english_wikipedia(self):
        assert ConcurrentContentExtractor._is_wikipedia_url("https://fr.wikipedia.org/wiki/France")

    def test_url_encoded(self):
        assert ConcurrentContentExtractor._is_wikipedia_url(
            "https://en.wikipedia.org/wiki/2020_Malian_coup_d%27%C3%A9tat"
        )

    def test_with_fragment(self):
        assert ConcurrentContentExtractor._is_wikipedia_url(
            "https://en.wikipedia.org/wiki/Artemis_II#Launch_date"
        )

    def test_not_wikipedia(self):
        assert not ConcurrentContentExtractor._is_wikipedia_url("https://example.com/wiki/Page")

    def test_wikipedia_api_not_matched(self):
        assert not ConcurrentContentExtractor._is_wikipedia_url(
            "https://en.wikipedia.org/w/api.php?action=query"
        )

    def test_case_insensitive(self):
        assert ConcurrentContentExtractor._is_wikipedia_url("https://en.Wikipedia.org/wiki/Test")


# ---------------------------------------------------------------------------
# _fetch_wikipedia tests (mocked HTTP)
# ---------------------------------------------------------------------------


def _mock_transport(handler):
    """Create an httpx.MockTransport from a handler function."""
    return httpx.MockTransport(handler)


def _make_json_response(data: dict) -> httpx.Response:
    return httpx.Response(200, json=data)


class TestFetchWikipediaArticle:
    @pytest.mark.asyncio
    async def test_regular_article(self):
        article_text = "Wisconsin held elections in 2026. " * 10  # > 50 chars

        def handler(request: httpx.Request) -> httpx.Response:
            assert "action=query" in str(request.url)
            assert "prop=extracts" in str(request.url)
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "12345": {
                                "pageid": 12345,
                                "title": "2026 Wisconsin Elections",
                                "extract": article_text,
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia(
            "https://en.wikipedia.org/wiki/2026_Wisconsin_Elections"
        )

        assert result["success"] is True
        assert "2026 Wisconsin Elections" in result["content"]
        assert "Wisconsin held elections" in result["content"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_missing_page(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "-1": {
                                "ns": 0,
                                "title": "Nonexistent Page",
                                "missing": "",
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia("https://en.wikipedia.org/wiki/Nonexistent_Page")

        assert result["success"] is False
        assert "not found" in result["error"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_empty_extract(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "999": {
                                "pageid": 999,
                                "title": "Stub Article",
                                "extract": "Short.",
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia("https://en.wikipedia.org/wiki/Stub_Article")

        assert result["success"] is False
        assert "too short" in result["error"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_fragment_stripped(self):
        article_text = "Artemis II is a crewed mission. " * 10

        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            assert "Artemis_II" in url_str
            assert "Launch_date" not in url_str
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "100": {
                                "pageid": 100,
                                "title": "Artemis II",
                                "extract": article_text,
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia(
            "https://en.wikipedia.org/wiki/Artemis_II#Launch_date"
        )

        assert result["success"] is True
        assert "Artemis II" in result["content"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_api_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia("https://en.wikipedia.org/wiki/Some_Page")

        assert result["success"] is False
        assert "Wikipedia API error" in result["error"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_url_encoded_characters(self):
        article_text = "The 2020 Malian coup d'etat occurred in August. " * 5

        def handler(request: httpx.Request) -> httpx.Response:
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "200": {
                                "pageid": 200,
                                "title": "2020 Malian coup d'etat",
                                "extract": article_text,
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia(
            "https://en.wikipedia.org/wiki/2020_Malian_coup_d%27%C3%A9tat"
        )

        assert result["success"] is True
        assert "Malian coup" in result["content"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_content_truncated_when_too_long(self):
        article_text = "A" * 20000  # exceeds MAX_CONTENT_LENGTH (15000)

        def handler(request: httpx.Request) -> httpx.Response:
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "300": {
                                "pageid": 300,
                                "title": "Long Article",
                                "extract": article_text,
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia("https://en.wikipedia.org/wiki/Long_Article")

        assert result["success"] is True
        assert result["content"].endswith("...[truncated]")
        assert len(result["content"]) <= 15000 + 50  # MAX_CONTENT_LENGTH + header + suffix

        await extractor._client.aclose()


class TestFetchWikipediaSpecialStatistics:
    @pytest.mark.asyncio
    async def test_special_statistics(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "meta=siteinfo" in str(request.url)
            assert "siprop=statistics" in str(request.url)
            return _make_json_response(
                {
                    "query": {
                        "statistics": {
                            "pages": 60000000,
                            "articles": 7140467,
                            "edits": 1200000000,
                            "images": 900000,
                            "users": 48000000,
                            "activeusers": 120000,
                            "admins": 1000,
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia(
            "https://en.wikipedia.org/wiki/Special:Statistics"
        )

        assert result["success"] is True
        assert "7,140,467" in result["content"]
        assert "Content pages (articles)" in result["content"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_special_statistics_empty_response(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _make_json_response({"query": {"statistics": {}}})

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_wikipedia(
            "https://en.wikipedia.org/wiki/Special:Statistics"
        )

        assert result["success"] is False
        assert "No statistics" in result["error"]

        await extractor._client.aclose()


# ---------------------------------------------------------------------------
# Google Trends blocking
# ---------------------------------------------------------------------------


class TestGoogleTrendsBlocked:
    def test_trends_in_blocked_domains(self):
        assert "trends.google.com" in ConcurrentContentExtractor.BLOCKED_DOMAINS

    def test_trends_url_is_blocked(self):
        extractor = ConcurrentContentExtractor()
        assert extractor._is_blocked_domain("https://trends.google.com/trends/explore?q=test")

    def test_regular_google_not_blocked(self):
        extractor = ConcurrentContentExtractor()
        assert not extractor._is_blocked_domain("https://www.google.com/search?q=test")


# ---------------------------------------------------------------------------
# Integration through _fetch_url routing
# ---------------------------------------------------------------------------


class TestFetchUrlRouting:
    @pytest.mark.asyncio
    async def test_wikipedia_url_routed_to_api(self):
        """Verify that _fetch_url routes Wikipedia URLs to _fetch_wikipedia."""
        article_text = "This article is about elections in Wisconsin. " * 5

        def handler(request: httpx.Request) -> httpx.Response:
            # Should hit the MediaWiki API, not the raw page
            assert "api.php" in str(request.url)
            return _make_json_response(
                {
                    "query": {
                        "pages": {
                            "1": {
                                "pageid": 1,
                                "title": "Test",
                                "extract": article_text,
                            }
                        }
                    }
                }
            )

        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient(transport=_mock_transport(handler))

        result = await extractor._fetch_url("https://en.wikipedia.org/wiki/Test")

        assert result["success"] is True
        assert "elections in Wisconsin" in result["content"]

        await extractor._client.aclose()

    @pytest.mark.asyncio
    async def test_google_trends_blocked_via_fetch_url(self):
        """Verify that _fetch_url blocks Google Trends URLs."""
        extractor = ConcurrentContentExtractor()
        extractor._client = httpx.AsyncClient()

        result = await extractor._fetch_url("https://trends.google.com/trends/explore?q=test")

        assert result["success"] is False
        assert result["error"] == "Blocked domain"

        await extractor._client.aclose()
