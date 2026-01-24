"""
Content Extractor

Extracts full article text from URLs using multiple fallback strategies:
1. Trafilatura - best for news articles
2. BeautifulSoup with readability heuristics
3. Basic HTML parsing fallback

Inspired by Q2 winner's FastContentExtractor approach.
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Try to import trafilatura (optional but recommended)
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    logger.warning("trafilatura not installed, using fallback extraction")


@dataclass
class ExtractedContent:
    """Extracted article content."""
    url: str
    title: Optional[str]
    text: str
    success: bool
    method: str  # Which extraction method worked
    word_count: int


class ContentExtractor:
    """
    Fast content extractor with multiple fallback strategies.

    Usage:
        extractor = ContentExtractor()
        content = await extractor.extract(url)
        print(content.text)
    """

    # Sites that commonly block or have anti-bot measures
    BLOCKED_DOMAINS = [
        "twitter.com", "x.com",
        "facebook.com", "fb.com",
        "instagram.com",
        "linkedin.com",
        "tiktok.com",
    ]

    # Maximum content length to return (chars)
    MAX_CONTENT_LENGTH = 15000

    # Request timeout
    TIMEOUT = 10.0

    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    async def close(self):
        """Clean up HTTP client."""
        await self.http_client.aclose()

    def _is_blocked_domain(self, url: str) -> bool:
        """Check if URL is from a domain that typically blocks scraping."""
        for domain in self.BLOCKED_DOMAINS:
            if domain in url.lower():
                return True
        return False

    async def extract(self, url: str) -> ExtractedContent:
        """
        Extract article content from a URL.

        Tries multiple strategies in order:
        1. Trafilatura (best for articles)
        2. BeautifulSoup with content heuristics
        3. Basic text extraction
        """
        if self._is_blocked_domain(url):
            return ExtractedContent(
                url=url,
                title=None,
                text="",
                success=False,
                method="blocked",
                word_count=0,
            )

        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return ExtractedContent(
                url=url,
                title=None,
                text="",
                success=False,
                method="fetch_failed",
                word_count=0,
            )

        # Try extraction strategies in order
        content = None
        method = "none"
        title = None

        # Strategy 1: Trafilatura (most reliable for articles)
        if HAS_TRAFILATURA and content is None:
            try:
                result = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                    favor_precision=True,
                )
                if result and len(result) > 100:
                    content = result
                    method = "trafilatura"
                    # Try to get title
                    metadata = trafilatura.extract_metadata(html)
                    if metadata:
                        title = metadata.title
            except Exception as e:
                logger.debug(f"Trafilatura failed for {url}: {e}")

        # Strategy 2: BeautifulSoup with readability heuristics
        if content is None:
            try:
                soup = BeautifulSoup(html, 'lxml')

                # Get title
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)

                # Remove script, style, nav, header, footer, aside
                for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                                 'aside', 'form', 'iframe', 'noscript']):
                    tag.decompose()

                # Try to find main content area
                main_content = None
                for selector in ['article', 'main', '[role="main"]',
                                 '.article-content', '.post-content',
                                 '.entry-content', '.content', '#content']:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break

                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    # Fallback: get body text
                    body = soup.find('body')
                    if body:
                        content = body.get_text(separator='\n', strip=True)

                if content and len(content) > 100:
                    method = "beautifulsoup"
                else:
                    content = None

            except Exception as e:
                logger.debug(f"BeautifulSoup failed for {url}: {e}")

        # Strategy 3: Basic extraction (last resort)
        if content is None:
            try:
                soup = BeautifulSoup(html, 'html.parser')
                content = soup.get_text(separator='\n', strip=True)
                if content and len(content) > 100:
                    method = "basic"
                else:
                    content = ""
            except Exception as e:
                logger.debug(f"Basic extraction failed for {url}: {e}")
                content = ""

        # Clean and truncate content
        if content:
            content = self._clean_content(content)
            if len(content) > self.MAX_CONTENT_LENGTH:
                content = content[:self.MAX_CONTENT_LENGTH] + "...[truncated]"

        word_count = len(content.split()) if content else 0

        return ExtractedContent(
            url=url,
            title=title,
            text=content or "",
            success=bool(content and len(content) > 100),
            method=method,
            word_count=word_count,
        )

    def _clean_content(self, text: str) -> str:
        """Clean extracted content."""
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            line = line.strip()
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False

        return '\n'.join(cleaned_lines).strip()

    async def extract_batch(
        self,
        urls: list[str],
        max_concurrent: int = 5,
        max_urls: int = 10,
    ) -> list[ExtractedContent]:
        """
        Extract content from multiple URLs concurrently.

        Args:
            urls: List of URLs to extract
            max_concurrent: Maximum concurrent requests
            max_urls: Maximum URLs to process

        Returns:
            List of ExtractedContent results
        """
        # Limit URLs
        urls = urls[:max_urls]

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_with_semaphore(url: str) -> ExtractedContent:
            async with semaphore:
                return await self.extract(url)

        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.debug(f"Extraction failed for {url}: {result}")
                final_results.append(ExtractedContent(
                    url=url,
                    title=None,
                    text="",
                    success=False,
                    method="exception",
                    word_count=0,
                ))
            else:
                final_results.append(result)

        return final_results
