"""
Content Extractor

Multi-backend HTML content extraction with site-specific configs:
1. Site-specific CSS selectors (NYT, Reuters, Bloomberg, etc.)
2. Trafilatura (best for news articles)
3. Readability (fallback)
4. BoilerPy3 (last resort)

Also includes ConcurrentContentExtractor for concurrent URL fetching.
"""

import asyncio
import html as html_lib
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag

# Optional imports with graceful fallbacks
try:
    from trafilatura import extract as trafilatura_extract
    from trafilatura.settings import use_config

    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from readability import Document

    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False

try:
    from boilerpy3 import extractors

    HAS_BOILERPY = True
except ImportError:
    HAS_BOILERPY = False

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Extracted article content."""

    url: str
    title: str | None
    text: str
    success: bool
    method: str
    word_count: int
    author: str | None = None
    date: str | None = None
    source: str | None = None


class HTMLContentExtractor:
    """
    Multi-backend HTML content extractor with site-specific configurations.
    """

    # Site-specific extraction configs
    DEFAULT_SITE_CONFIGS = {
        "nytimes.com": {
            "cookies": {"nyt-gdpr": "accept"},
            "headers": {"Referer": "https://www.google.com/"},
            "wait_time": 2,
            "selectors": ["article#story", "div.StoryBodyCompanionColumn"],
            "remove_selectors": ["div.ad", "div.comments", "div.toolbar"],
        },
        "reuters.com": {
            "cookies": {"reuters-gdpr": "accept"},
            "headers": {"Referer": "https://news.google.com/"},
            "wait_time": 1,
            "selectors": ["article.article-body", 'div[data-testid="Body"]'],
            "remove_selectors": ["div.article-header", "div.article-share"],
        },
        "washingtonpost.com": {
            "cookies": {"wp_gdpr": "accept"},
            "headers": {"Referer": "https://www.google.com/"},
            "wait_time": 2,
            "selectors": ["div.article-body", "article.main-content"],
            "remove_selectors": ["div.interstitial", "div.newsletter-inline-unit"],
        },
        "economist.com": {
            "selectors": [
                "article.article__body",
                "div.article__lead",
                "div.article__content",
                "p.article__body-text",
            ],
            "remove_selectors": [
                "div.advert",
                "div.article__footnote",
                "div.share-links",
                "div.newsletter-signup",
            ],
        },
        "bloomberg.com": {
            "selectors": ["div.body-content", "div.body-copy", "article.article-body"],
            "remove_selectors": ["div.paywall", "div.newsletter-signup", "div.related-articles"],
        },
        "channelnewsasia.com": {
            "selectors": [
                "div.article-content",
                "div.article-body",
                "article",
                "div.article-text",
                "div.text-long",
            ],
            "remove_selectors": [
                "div.advertisement",
                "div.teaser",
                "div.partner-recommendations",
                "div.social-share",
                "div.also-worth-reading",
                "div.related-topics",
            ],
        },
        "techcrunch.com": {
            "selectors": [
                "div.article-content",
                "p.wp-block-paragraph",
                "ul.wp-block-list",
                "li.wp-block-list-item",
            ],
            "remove_selectors": [
                'div[class*="ad"]',
                'div[class*="related"]',
                'div[class*="promo"]',
                "aside",
                "nav",
                "header",
            ],
        },
    }

    # Patterns to remove from extracted content
    BLACKLIST_PATTERNS = [
        r"Advertisement\s*",
        r"ADVERTISEMENT\s*",
        r"Recommended\s*",
        r"###Embeddable###",
        r"Subscribe.*?(?=\n|$)",
        r"Sign up for.*?(?=\n|$)",
        r"Sign up here\.?",
        r"Newsletter.*?(?=\n|$)",
        r"Support quality journalism.*?(?=\n|$)",
        r"©\s*\d{4}.*?(?=\n|$)",
        r"All rights reserved.*?(?=\n|$)",
        r"PUBLISHED.*?, \d{2}:\d{2}.*?(?=\n|$)",
        r"PHOTO:.*?(?=\n|$)",
        r"Follow us on.*?(?=\n|$)",
        r"Share this article.*?(?=\n|$)",
        r"Thanks for sharing!.*?(?=\n|$)",
        r"Share full article.*?(?=\n|$)",
        r"Read more:.*?(?=\n|$)",
        r"More on this Topic.*?(?=\n|$)",
        r"See more on.*?(?=\n|$)",
        r"\[\s*\d+\s*chars\s*\]",
        r"^\s*https?://[^\s]+$",
    ]

    REMOVAL_KEYWORDS = [
        "embeddable",
        "subscribe",
        "subscription",
        "newsletter",
        "sign up",
        "share this",
        "follow us",
        "copyright",
        "all rights reserved",
        "read more",
        "more on this",
        "see more",
        "gallery",
        "slideshow",
        "click here",
        "download",
        "register",
        "privacy policy",
        "terms of service",
        "thanks for sharing",
        "photo:",
        "image:",
        "published",
        "updated",
    ]

    def __init__(self, site_configs: dict[str, dict] | None = None):
        self.site_configs = site_configs or self.DEFAULT_SITE_CONFIGS
        if HAS_BOILERPY:
            self.boilerpy_extractor = extractors.ArticleExtractor()
        else:
            self.boilerpy_extractor = None

    def _preprocess_html(self, html_content: str) -> str:
        """Pre-process HTML to improve extraction results."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script, style, and SVG tags
            for tag in soup.find_all(["script", "style", "svg", "noscript"]):
                tag.decompose()

            # Remove hidden elements
            for tag in soup.find_all(style=re.compile(r"display:\s*none|visibility:\s*hidden")):
                tag.decompose()

            # Remove footer/banner/sidebar/comment elements
            for div in soup.find_all("div", {"id": re.compile(r"footer|banner|sidebar|comment")}):
                div.decompose()

            # Remove header if it's navigation-like
            for div in soup.find_all("div", {"id": re.compile(r"header")}):
                header_text = div.get_text()
                if len(header_text) < 200 or re.search(
                    r"(menu|navigation|logo|sign in)", header_text.lower()
                ):
                    div.decompose()

            return str(soup)
        except Exception:
            return html_content

    def extract(self, url: str, html_content: str) -> str | None:
        """
        Extract article content from HTML using multiple backends.

        Returns the best extraction result based on quality scoring.
        """
        if not html_content or len(html_content.strip()) < 100:
            return None

        html_content = self._preprocess_html(html_content)
        metadata = self._get_article_metadata(html_content, url)
        soup = BeautifulSoup(html_content, "html.parser")

        cleaned_results = []

        # Strategy 1: Site-specific selectors
        site_specific = self._extract_with_selectors(html_content, url)
        if site_specific and len(site_specific.strip()) > 500:
            cleaned_results.append((site_specific, 1.2, "site-specific"))

        # Strategy 2: Trafilatura
        if HAS_TRAFILATURA:
            trafilatura_result = self._extract_trafilatura(html_content)
            if trafilatura_result:
                cleaned_results.append((trafilatura_result, 1.0, "trafilatura"))

        # Strategy 3: Readability
        if HAS_READABILITY:
            try:
                doc = Document(html_content)
                readability_soup = BeautifulSoup(doc.summary(), "html.parser")
                readability_text = self._fallback_extract_paragraphs(readability_soup)
                if readability_text:
                    cleaned_results.append((readability_text, 0.9, "readability"))
            except Exception as e:
                logger.debug(f"Readability failed: {e}")

        # Strategy 4: BoilerPy3
        if HAS_BOILERPY and self.boilerpy_extractor:
            try:
                boilerpy_result = self._extract_boilerpy(html_content)
                if boilerpy_result:
                    cleaned_results.append((boilerpy_result, 0.8, "boilerpy"))
            except Exception:
                pass

        # Score and select best result
        if cleaned_results:
            scored_results = []
            for content, base_weight, label in cleaned_results:
                score = self._calculate_content_quality(content)
                length_score = min(len(content) / 5000, 1.0)
                total_score = base_weight * score * length_score
                scored_results.append((content, total_score, label))

            best_result, _, label = max(scored_results, key=lambda x: x[1])
            logger.debug(f"Selected content from {label} with length {len(best_result)}")
            return self._format_with_metadata(self._clean_content(best_result), metadata)

        # Fallback: auto-detect main content div
        guessed_div = self._find_content_by_density(soup)
        if guessed_div:
            text = guessed_div.get_text(separator=" ", strip=True)
            if text:
                return self._format_with_metadata(self._clean_content(text), metadata)

        # Last resort: collect all <p> and <li> elements
        fallback = self._fallback_extract_paragraphs(soup)
        if fallback:
            return self._format_with_metadata(self._clean_content(fallback), metadata)

        return None

    def _extract_with_selectors(self, html_content: str, url: str) -> str | None:
        """Extract content using site-specific CSS selectors."""
        domain = urlparse(url).netloc
        config = {}

        for known_domain in self.site_configs:
            if known_domain in domain:
                config = self.site_configs[known_domain]
                break

        selectors = config.get("selectors", [])
        remove_selectors = config.get("remove_selectors", [])

        if not selectors:
            selectors = [
                "article",
                ".article",
                ".article-body",
                ".content",
                ".entry-content",
                'div[itemprop="articleBody"]',
                ".story-body",
                ".post-content",
                "main",
            ]

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove unwanted elements
            for selector in remove_selectors:
                for element in soup.select(selector):
                    element.decompose()

            for tag in soup.find_all(["aside", "nav", "footer"]):
                tag.decompose()

            for tag in soup.find_all(
                class_=re.compile(r"(ad-|banner|promo|sponsored|recommendation)")
            ):
                tag.decompose()

            content_parts = []

            for selector in selectors:
                for element in soup.select(selector):
                    self._clean_element(element)

                    paragraphs = []
                    children = list(element.children)
                    i = 0
                    while i < len(children):
                        child = children[i]
                        if not isinstance(child, Tag):
                            i += 1
                            continue

                        tag_name = child.name
                        text = child.get_text(separator=" ", strip=True)

                        if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"] and text:
                            merged_text = [text]
                            j = i + 1
                            while j < len(children):
                                next_child = children[j]
                                if isinstance(next_child, Tag) and next_child.name in [
                                    "p",
                                    "div",
                                    "ul",
                                    "ol",
                                ]:
                                    para = next_child.get_text(separator=" ", strip=True)
                                    if para and len(para) > 30 and not self._is_boilerplate(para):
                                        merged_text.append(para)
                                        i = j
                                        break
                                j += 1
                            paragraphs.append("\n".join(merged_text))
                        elif (
                            tag_name in ["p", "li"]
                            and text
                            and len(text) > 40
                            and not self._is_boilerplate(text)
                        ):
                            paragraphs.append(text)
                        i += 1

                    if paragraphs:
                        content_parts.append("\n\n".join(paragraphs))

            if not content_parts:
                paragraphs = []
                for p in soup.find_all(["p"]):
                    text = p.get_text(separator=" ", strip=True)
                    if text and len(text) > 20 and not self._is_boilerplate(text):
                        paragraphs.append(text)
                if paragraphs:
                    return "\n\n".join(paragraphs)
                return None

            return "\n\n".join(content_parts)
        except Exception as e:
            logger.debug(f"Error in _extract_with_selectors: {e}")
            return None

    def _clean_element(self, element):
        """Clean an element's internal structure."""
        for tag in element.find_all(["script", "style", "button", "form", "input", "iframe"]):
            tag.decompose()

        for tag in element.find_all(
            class_=re.compile(r"share|social|comment|related|promo|ad|subscribe|newsletter")
        ):
            tag.decompose()

        for p in element.find_all("p"):
            if (
                not p.get_text(separator=" ", strip=True)
                or len(p.get_text(separator=" ", strip=True)) < 5
            ):
                p.decompose()

    def _is_boilerplate(self, text: str) -> bool:
        """Check if text is likely boilerplate content."""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in self.REMOVAL_KEYWORDS):
            return True

        if len(text) < 20 and (
            text.isupper()
            or text.count(".") == 0
            or re.search(r"^\d+:\d+$", text)
            or re.search(r"^[^\w]*https?://", text)
        ):
            return True

        return False

    def _extract_trafilatura(self, html_content: str) -> str | None:
        """Extract content using trafilatura."""
        if not HAS_TRAFILATURA:
            return None
        try:
            config = use_config()
            if not config.has_section("EXTRACTION"):
                config.add_section("EXTRACTION")
            config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
            config.set("EXTRACTION", "favor_precision", "true")

            result = trafilatura_extract(html_content, config=config)
            return result if result and len(result) > 300 else None
        except Exception as e:
            logger.debug(f"Trafilatura failed: {e}")
            return None

    def _extract_boilerpy(self, html_content: str) -> str | None:
        """Extract content using boilerpy3."""
        if not self.boilerpy_extractor:
            return None
        try:
            content = self.boilerpy_extractor.get_content(html_content)
            if content:
                lines = content.split("\n")
                filtered_lines = [
                    line for line in lines if len(line) > 20 and not self._is_boilerplate(line)
                ]
                return "\n\n".join(filtered_lines) if filtered_lines else None
            return None
        except Exception:
            return None

    def _find_content_by_density(self, soup: BeautifulSoup) -> Tag | None:
        """Find the main content div based on text density."""
        candidates = []
        for div in soup.find_all("div"):
            class_attr = " ".join(div.get("class", []))
            if any(
                kw in class_attr for kw in ["footer", "nav", "sidebar", "header", "promo", "share"]
            ):
                continue
            text = div.get_text(separator=" ", strip=True)
            p_count = len(div.find_all("p"))
            if len(text) > 500 and p_count >= 3:
                candidates.append((div, len(text)))

        if candidates:
            return sorted(candidates, key=lambda x: x[1], reverse=True)[0][0]
        return None

    def _fallback_extract_paragraphs(self, soup: BeautifulSoup) -> str | None:
        """Fallback: extract all meaningful paragraphs."""
        paragraphs = []
        for tag in soup.find_all(["p", "li", "h2", "h3"]):
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 40 and not self._is_boilerplate(text):
                paragraphs.append(text)
        return "\n\n".join(paragraphs) if paragraphs else None

    def _calculate_content_quality(self, content: str) -> float:
        """Calculate a quality score for the content."""
        if not content:
            return 0.0

        avg_line_length = sum(len(line) for line in content.splitlines()) / max(
            1, len(content.splitlines())
        )
        sentence_count = content.count(".") + content.count("!") + content.count("?")
        word_count = len(content.split())

        quality_score = min(
            1.0, (sentence_count / max(1, word_count / 20)) * (min(avg_line_length, 100) / 100)
        )

        alphanumeric_ratio = sum(c.isalnum() or c.isspace() for c in content) / max(1, len(content))
        quality_score *= max(0.5, alphanumeric_ratio)

        uppercase_ratio = sum(c.isupper() for c in content) / max(
            1, len(content) - content.count(" ")
        )
        if uppercase_ratio > 0.3:
            quality_score *= 0.8

        return quality_score

    def _clean_content(self, content: str) -> str:
        """Clean extracted content."""
        if not content:
            return ""

        content = html_lib.unescape(content)

        # Remove invisible/control characters
        content = re.sub(r"[\x00-\x1F\x7F]", " ", content)

        # Fix punctuation spacing
        content = re.sub(r"\s+([.,;!?])", r"\1", content)
        content = re.sub(r"([.,;!?])(?=\w)", r"\1 ", content)

        # Fix joined words
        content = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", content)
        content = re.sub(r"(?<=[a-zA-Z])(?=\d)", " ", content)
        content = re.sub(r"(?<=\d)(?=[a-zA-Z])", " ", content)

        # Normalize spacing
        content = re.sub(r" {2,}", " ", content)
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Apply blacklist patterns
        for pattern in self.BLACKLIST_PATTERNS:
            content = re.sub(pattern, " ", content, flags=re.IGNORECASE | re.MULTILINE)

        # Final cleanup
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

        return content

    def _get_article_metadata(self, html_content: str, url: str) -> dict:
        """Extract metadata from the article."""
        try:
            metadata = {}
            soup = BeautifulSoup(html_content, "html.parser")

            metadata["title"] = self._extract_title(soup)
            metadata["author"] = self._extract_author(soup)
            metadata["date"] = self._extract_date(soup)
            metadata["source"] = self._extract_source(soup, url)

            return {k: v for k, v in metadata.items() if v}
        except Exception:
            return {}

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract the article title."""
        for meta in soup.find_all("meta"):
            if meta.get("property") in ["og:title", "twitter:title"] and meta.get("content"):
                return meta.get("content").strip()

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(separator=" ", strip=True)

        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(separator=" ", strip=True)

        return None

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        """Extract the author name."""
        for meta in soup.find_all("meta"):
            if meta.get("name") in ["author", "article:author"] and meta.get("content"):
                return meta.get("content").strip()

        for selector in [".author", ".byline", ".writer", '[rel="author"]']:
            author_elem = soup.select_one(selector)
            if author_elem:
                return author_elem.get_text(separator=" ", strip=True)

        return None

    def _extract_date(self, soup: BeautifulSoup) -> str | None:
        """Extract publication date."""
        for meta in soup.find_all("meta"):
            if meta.get("property") in ["article:published_time", "og:published_time"] and meta.get(
                "content"
            ):
                return meta.get("content").strip()

        time_elem = soup.find("time")
        if time_elem and time_elem.get("datetime"):
            return time_elem.get("datetime")

        for selector in [".date", ".published", ".timestamp", ".pubdate"]:
            date_elem = soup.select_one(selector)
            if date_elem:
                return date_elem.get_text(separator=" ", strip=True)

        return None

    def _extract_source(self, soup: BeautifulSoup, url: str) -> str:
        """Extract publication source name."""
        for meta in soup.find_all("meta"):
            if meta.get("property") in ["og:site_name"] and meta.get("content"):
                return meta.get("content").strip()

        domain = urlparse(url).netloc
        source = domain.replace("www.", "")
        source = re.sub(r"\.(com|org|net|gov|edu|io)$", "", source)
        return source.capitalize()

    def _format_with_metadata(self, content: str, metadata: dict) -> str:
        """Format content with metadata header."""
        if not content:
            return ""

        has_title = False
        if "title" in metadata and metadata["title"]:
            title_start = metadata["title"][:30].lower()
            content_start = content[:100].lower()
            has_title = title_start in content_start

        header_parts = []

        if "title" in metadata and metadata["title"] and not has_title:
            header_parts.append(f"# {metadata['title']}")

        meta_parts = []

        if "source" in metadata and metadata["source"]:
            meta_parts.append(f"Content source: {metadata['source']}")

        if "date" in metadata and metadata["date"]:
            try:
                from dateutil.parser import parse as parse_date

                parsed_date = parse_date(metadata["date"])
                formatted_date = parsed_date.strftime("%B %d, %Y")
                meta_parts.append(f"Date: {formatted_date}")
            except Exception:
                meta_parts.append(f"Date: {metadata['date']}")

        if "author" in metadata and metadata["author"]:
            meta_parts.append(f"Author: {metadata['author']}")

        if meta_parts:
            header_parts.append("\n".join(meta_parts))

        if header_parts:
            return "\n\n".join(header_parts + [content])

        return content


class ConcurrentContentExtractor:
    """
    Concurrent URL fetcher and content extractor.

    Uses httpx for async HTTP requests and HTMLContentExtractor for parsing.
    Optionally supports Bright Data API for more reliable scraping.
    """

    # Sites that commonly block or have anti-bot measures
    BLOCKED_DOMAINS = [
        "twitter.com",
        "x.com",
        "facebook.com",
        "fb.com",
        "instagram.com",
        "linkedin.com",
        "tiktok.com",
    ]

    # Maximum content length to return (chars)
    MAX_CONTENT_LENGTH = 15000

    # Request timeout
    TIMEOUT = 15.0

    def __init__(self, bright_data_api_key: str | None = None):
        """
        Initialize the concurrent content extractor.

        Args:
            bright_data_api_key: Optional Bright Data API key for more reliable scraping.
                                If not provided, uses direct HTTP requests.
        """
        self.bright_data_api_key = bright_data_api_key
        self.html_extractor = HTMLContentExtractor()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _is_blocked_domain(self, url: str) -> bool:
        """Check if URL is from a domain that typically blocks scraping."""
        for domain in self.BLOCKED_DOMAINS:
            if domain in url.lower():
                return True
        return False

    async def _fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch a single URL and extract content."""
        if self._is_blocked_domain(url):
            return {
                "url": url,
                "domain": urlparse(url).netloc,
                "content": None,
                "error": "Blocked domain",
                "success": False,
            }

        try:
            # Try Bright Data API if available
            if self.bright_data_api_key:
                return await self._fetch_with_bright_data(url)

            # Direct HTTP request
            response = await self._client.get(url)
            response.raise_for_status()
            raw_html = response.text

            if not raw_html or len(raw_html.strip()) < 100:
                return {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "content": None,
                    "error": "Empty or very short HTML received",
                    "success": False,
                }

            # Extract content
            processed_content = self.html_extractor.extract(url, raw_html)

            if not processed_content:
                return {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "content": None,
                    "error": "Content extraction failed",
                    "success": False,
                }

            # Truncate if too long
            if len(processed_content) > self.MAX_CONTENT_LENGTH:
                processed_content = processed_content[: self.MAX_CONTENT_LENGTH] + "...[truncated]"

            return {
                "url": url,
                "domain": urlparse(url).netloc,
                "content": processed_content,
                "success": True,
            }

        except TimeoutError:
            return {
                "url": url,
                "domain": urlparse(url).netloc,
                "content": None,
                "error": "Request timed out",
                "success": False,
            }
        except Exception as e:
            logger.debug(f"Error processing {url}: {e}")
            return {
                "url": url,
                "domain": urlparse(url).netloc,
                "content": None,
                "error": str(e),
                "success": False,
            }

    async def _fetch_with_bright_data(self, url: str) -> dict[str, Any]:
        """Fetch URL using Bright Data API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.bright_data_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "url": url,
                "zone": "web_scraper",
                "format": "raw",
            }

            response = await self._client.post(
                "https://api.brightdata.com/request", headers=headers, json=payload
            )

            if response.status_code != 200:
                return {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "content": None,
                    "error": f"Bright Data API error: {response.status_code}",
                    "success": False,
                }

            raw_html = response.text

            if not raw_html or len(raw_html.strip()) < 100:
                return {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "content": None,
                    "error": "Empty HTML from Bright Data",
                    "success": False,
                }

            processed_content = self.html_extractor.extract(url, raw_html)

            if not processed_content:
                return {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "content": None,
                    "error": "Content extraction failed",
                    "success": False,
                }

            if len(processed_content) > self.MAX_CONTENT_LENGTH:
                processed_content = processed_content[: self.MAX_CONTENT_LENGTH] + "...[truncated]"

            return {
                "url": url,
                "domain": urlparse(url).netloc,
                "content": processed_content,
                "success": True,
            }

        except Exception as e:
            logger.debug(f"Bright Data error for {url}: {e}")
            return {
                "url": url,
                "domain": urlparse(url).netloc,
                "content": None,
                "error": str(e),
                "success": False,
            }

    async def extract_content(self, urls: list[str]) -> dict[str, dict[str, Any]]:
        """
        Extract content from multiple URLs concurrently.

        Args:
            urls: List of URLs to extract

        Returns:
            Dict mapping URL to extraction result
        """
        results = {}

        try:
            tasks = [asyncio.create_task(self._fetch_url(url)) for url in urls]

            # Wait for tasks with timeout
            done, pending = await asyncio.wait(tasks, timeout=75)

            # Handle completed tasks
            for task in done:
                try:
                    result = task.result()
                    results[result["url"]] = result
                except Exception as e:
                    logger.debug(f"Error getting task result: {e}")

            # Handle pending tasks (timed out)
            for task in pending:
                task.cancel()
                try:
                    task_index = None
                    for i, t in enumerate(tasks):
                        if t == task:
                            task_index = i
                            break

                    url = urls[task_index] if task_index is not None else "unknown"
                    logger.debug(f"Task for {url} timed out")
                    results[url] = {
                        "url": url,
                        "domain": urlparse(url).netloc if url != "unknown" else "unknown",
                        "content": None,
                        "error": "Operation timed out",
                        "success": False,
                    }
                except Exception as e:
                    logger.debug(f"Error handling cancelled task: {e}")

        except Exception as e:
            logger.error(f"Error in extract_content: {e}")

        return results

    async def process_urls(self, urls: list[str]) -> dict[str, tuple[str, bool]]:
        """
        Process URLs and return simplified results.

        Args:
            urls: List of URLs to process

        Returns:
            Dict mapping URL to (content, success) tuple
        """
        results_dict = await self.extract_content(urls)
        processed_results = {}

        for url, result in results_dict.items():
            content = result.get("content", "")
            success = result.get("success", False)
            processed_results[url] = (content or "", success)

        return processed_results


async def extract_article(url: str) -> ExtractedContent:
    """
    Convenience function to extract a single article.

    Usage:
        content = await extract_article("https://example.com/article")
        print(content.text)
    """
    async with ConcurrentContentExtractor() as extractor:
        results = await extractor.extract_content([url])

        if url in results and results[url]["success"]:
            result = results[url]
            # Try to parse metadata from content
            content_text = result["content"] or ""
            title = None

            # Try to extract title from first line if it starts with #
            if content_text.startswith("# "):
                first_line_end = content_text.find("\n")
                if first_line_end > 0:
                    title = content_text[2:first_line_end].strip()

            return ExtractedContent(
                url=url,
                title=title,
                text=content_text,
                success=True,
                method="fast_extractor",
                word_count=len(content_text.split()),
            )

        return ExtractedContent(
            url=url, title=None, text="", success=False, method="failed", word_count=0
        )


async def extract_articles_batch(
    urls: list[str], max_concurrent: int = 10
) -> list[ExtractedContent]:
    """
    Extract multiple articles concurrently.

    Usage:
        urls = ["https://example.com/1", "https://example.com/2"]
        results = await extract_articles_batch(urls)
        for result in results:
            print(f"{result.url}: {result.word_count} words")
    """
    async with ConcurrentContentExtractor() as extractor:
        results_dict = await extractor.extract_content(urls)

        results = []
        for url in urls:
            if url in results_dict and results_dict[url]["success"]:
                result = results_dict[url]
                content_text = result["content"] or ""
                title = None

                if content_text.startswith("# "):
                    first_line_end = content_text.find("\n")
                    if first_line_end > 0:
                        title = content_text[2:first_line_end].strip()

                results.append(
                    ExtractedContent(
                        url=url,
                        title=title,
                        text=content_text,
                        success=True,
                        method="fast_extractor",
                        word_count=len(content_text.split()),
                    )
                )
            else:
                results.append(
                    ExtractedContent(
                        url=url, title=None, text="", success=False, method="failed", word_count=0
                    )
                )

        return results
