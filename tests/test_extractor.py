"""
Tests for the content extractor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.research.extractor import ContentExtractor, ExtractedContent


class TestContentExtractor:
    """Test content extraction functionality."""

    def test_blocked_domain_detection(self):
        """Test that blocked domains are detected."""
        extractor = ContentExtractor()

        assert extractor._is_blocked_domain("https://twitter.com/user/status/123")
        assert extractor._is_blocked_domain("https://x.com/post")
        assert extractor._is_blocked_domain("https://facebook.com/page")
        assert extractor._is_blocked_domain("https://linkedin.com/in/user")

        assert not extractor._is_blocked_domain("https://reuters.com/article")
        assert not extractor._is_blocked_domain("https://bbc.com/news")
        assert not extractor._is_blocked_domain("https://nytimes.com/article")

    def test_clean_content(self):
        """Test content cleaning."""
        extractor = ContentExtractor()

        # Test excessive whitespace removal
        dirty = "Line 1\n\n\n\nLine 2\n\n\nLine 3"
        clean = extractor._clean_content(dirty)
        # Should have at most one blank line between content
        assert "\n\n\n" not in clean
        assert "Line 1" in clean
        assert "Line 2" in clean
        assert "Line 3" in clean

    def test_extracted_content_dataclass(self):
        """Test ExtractedContent dataclass."""
        content = ExtractedContent(
            url="https://example.com",
            title="Test Title",
            text="Test content here",
            success=True,
            method="trafilatura",
            word_count=3,
        )
        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.success is True
        assert content.word_count == 3


class TestContentExtractionStrategies:
    """Test different extraction strategies."""

    @pytest.mark.asyncio
    async def test_extraction_with_mock_response(self):
        """Test extraction with mocked HTTP response."""
        extractor = ContentExtractor()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Main Headline</h1>
                <p>This is the main content of the article with enough text to pass the minimum threshold for extraction. We need at least 100 characters to be considered successful.</p>
            </article>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()

        with patch.object(extractor.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await extractor.extract("https://example.com/article")

        assert result.success is True
        assert result.method in ["trafilatura", "beautifulsoup", "basic"]
        assert len(result.text) > 0

        await extractor.close()

    @pytest.mark.asyncio
    async def test_extraction_blocked_domain(self):
        """Test extraction returns failure for blocked domains."""
        extractor = ContentExtractor()

        result = await extractor.extract("https://twitter.com/user/status/123")

        assert result.success is False
        assert result.method == "blocked"
        assert result.text == ""

        await extractor.close()

    @pytest.mark.asyncio
    async def test_extraction_http_error(self):
        """Test extraction handles HTTP errors gracefully."""
        extractor = ContentExtractor()

        with patch.object(extractor.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            result = await extractor.extract("https://example.com/article")

        assert result.success is False
        assert result.method == "fetch_failed"

        await extractor.close()


class TestBatchExtraction:
    """Test batch extraction functionality."""

    @pytest.mark.asyncio
    async def test_batch_extraction_limits_urls(self):
        """Test that batch extraction respects max_urls."""
        extractor = ContentExtractor()

        urls = [f"https://example.com/article{i}" for i in range(20)]

        with patch.object(extractor, 'extract', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = ExtractedContent(
                url="test",
                title="Test",
                text="Content",
                success=True,
                method="mock",
                word_count=1,
            )
            results = await extractor.extract_batch(urls, max_urls=5)

        assert len(results) == 5
        assert mock_extract.call_count == 5

        await extractor.close()

    @pytest.mark.asyncio
    async def test_batch_extraction_handles_exceptions(self):
        """Test that batch extraction handles individual failures."""
        extractor = ContentExtractor()

        async def mock_extract(url):
            if "fail" in url:
                raise Exception("Simulated failure")
            return ExtractedContent(
                url=url,
                title="Test",
                text="Content",
                success=True,
                method="mock",
                word_count=1,
            )

        urls = [
            "https://example.com/good1",
            "https://example.com/fail",
            "https://example.com/good2",
        ]

        with patch.object(extractor, 'extract', side_effect=mock_extract):
            results = await extractor.extract_batch(urls, max_urls=3)

        # Should have 3 results, even if one failed
        assert len(results) == 3
        # Failed one should have success=False
        failed = [r for r in results if not r.success]
        assert len(failed) == 1

        await extractor.close()
