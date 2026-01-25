"""
AskNews Searcher - Mirrors Metaculus template implementation

This module provides a complete AskNews integration matching the functionality
of the Metaculus forecasting-tools template bot, including:
- AsyncAskNewsSDK for native async support
- Dual search strategy (latest news + historical/news knowledge)
- Deep research via get_deep_news endpoint
- Response caching with configurable modes
- Research presets for easy configuration

Reference: https://docs.asknews.app/en/news
Reference: https://docs.asknews.app/en/deepnews
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Implementation
# =============================================================================

@dataclass
class CacheEntry:
    """A cached response entry."""
    query: str
    result: str
    timestamp: str


class AskNewsCache:
    """
    Cache for AskNews responses to avoid redundant API calls.

    Matches Metaculus implementation with:
    - File-based cache in ~/.cache/metaculus-bot/asknews/
    - 24-hour expiry
    - Three modes: use_cache, use_cache_with_fallback, no_cache
    """

    _cache_directory = Path.home() / ".cache" / "metaculus-bot" / "asknews"
    _cache_expiry_hours = 24

    def __init__(
        self,
        cache_mode: Literal["use_cache", "use_cache_with_fallback", "no_cache"] = "no_cache",
        cache_directory: Path | None = None,
    ) -> None:
        self.cache_mode = cache_mode
        if cache_directory:
            self._cache_directory = cache_directory

        if self.cache_mode != "no_cache":
            self._cache_directory.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, query: str) -> str:
        """Generate cache key from query (date + hash)."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{today}_{query_hash}"

    def _get_cache_filepath(self, cache_key: str) -> Path:
        return self._cache_directory / f"{cache_key}.json"

    def get(self, query: str) -> str | None:
        """Get cached result for query, or None if not found/expired."""
        if self.cache_mode == "no_cache":
            return None

        cache_key = self._get_cache_key(query)
        cache_file = self._get_cache_filepath(cache_key)

        if not cache_file.exists():
            if self.cache_mode == "use_cache":
                raise ValueError(f"Cache mode is 'use_cache' but no cache found for query: {query[:100]}")
            return None

        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)

            cached_time = datetime.fromisoformat(cache_data["timestamp"])
            hours_since_cache = (datetime.now(timezone.utc) - cached_time).total_seconds() / 3600

            if hours_since_cache > self._cache_expiry_hours:
                cache_file.unlink()
                if self.cache_mode == "use_cache":
                    raise ValueError(f"Cache expired for query: {query[:100]}")
                return None

            logger.debug(f"Cache hit for query: {query[:50]}...")
            return cache_data["result"]

        except (json.JSONDecodeError, KeyError) as e:
            if self.cache_mode == "use_cache":
                raise ValueError(f"Failed to read cache for query: {query[:100]}") from e
            return None

    def set(self, query: str, result: str) -> None:
        """Cache a result for a query."""
        if self.cache_mode == "no_cache":
            return

        cache_key = self._get_cache_key(query)
        cache_file = self._get_cache_filepath(cache_key)

        cache_data = {
            "query": query,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)

        logger.debug(f"Cached result for query: {query[:50]}...")

    def clear_expired(self) -> int:
        """Clear expired cache entries. Returns count of cleared entries."""
        if self.cache_mode == "no_cache":
            return 0

        count = 0
        current_time = datetime.now(timezone.utc)

        for cache_file in self._cache_directory.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)

                cached_time = datetime.fromisoformat(cache_data["timestamp"])
                hours_since_cache = (current_time - cached_time).total_seconds() / 3600

                if hours_since_cache > self._cache_expiry_hours:
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError, OSError):
                cache_file.unlink()
                count += 1

        return count

    def clear_all(self) -> int:
        """Clear all cache entries. Returns count of cleared entries."""
        count = 0
        for cache_file in self._cache_directory.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count


# =============================================================================
# AskNews Searcher
# =============================================================================

@dataclass
class NewsArticle:
    """A news article from AskNews."""
    title: str
    summary: str
    url: str
    source_id: str
    language: str
    pub_date: datetime | None

    def to_formatted_string(self) -> str:
        """Format article for inclusion in prompts."""
        date_str = self.pub_date.strftime("%B %d, %Y %I:%M %p") if self.pub_date else "Unknown date"
        return (
            f"**{self.title}**\n"
            f"{self.summary}\n"
            f"Original language: {self.language}\n"
            f"Publish date: {date_str}\n"
            f"Source: [{self.source_id}]({self.url})\n"
        )


class AskNewsSearcher:
    """
    AskNews integration matching Metaculus template functionality.

    Features:
    - Dual search strategy: latest news + historical/news knowledge
    - Deep research via get_deep_news endpoint
    - Response caching
    - Configurable presets

    Usage:
        searcher = AskNewsSearcher()

        # Simple news search
        news = await searcher.get_formatted_news_async("Grammy nominees 2025")

        # Deep research
        research = await searcher.get_formatted_deep_research("Who will win the Grammy?")

        # Using presets
        result = await searcher.call_preconfigured_version(
            "asknews/deep-research/low-depth",
            "Grammy predictions"
        )
    """

    # Defaults matching Metaculus template
    _default_rate_limit = 12  # seconds between calls (free tier: 1 req/10s, add buffer)
    _default_search_depth = 1
    _default_max_depth = 1
    _default_model = "deepseek-basic"
    _default_sources = ["asknews"]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        cache_mode: Literal["use_cache", "use_cache_with_fallback", "no_cache"] | None = None,
    ) -> None:
        """
        Initialize AskNews searcher.

        Args:
            client_id: AskNews OAuth client ID (or set ASKNEWS_CLIENT_ID env var)
            client_secret: AskNews OAuth client secret (or set ASKNEWS_CLIENT_SECRET env var)
            cache_mode: Cache behavior - "no_cache", "use_cache", or "use_cache_with_fallback"
        """
        if cache_mode is None:
            cache_mode = os.getenv("ASKNEWS_CACHE_MODE", "no_cache")  # type: ignore

        self.client_id = client_id or os.getenv("ASKNEWS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ASKNEWS_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "AskNews credentials not provided. "
                "Set ASKNEWS_CLIENT_ID and ASKNEWS_CLIENT_SECRET environment variables."
            )

        self.cache = AskNewsCache(cache_mode=cache_mode)
        self._rate_limit_delay = self._default_rate_limit

    # -------------------------------------------------------------------------
    # News Search (dual strategy)
    # -------------------------------------------------------------------------

    async def get_formatted_news_async(
        self,
        query: str,
        n_latest: int = 6,
        n_historical: int = 10,
    ) -> str:
        """
        Get formatted news using dual search strategy.

        Searches both:
        1. Latest news (recent/hot articles)
        2. Historical news (news knowledge archive going back to 2023)

        Args:
            query: Search query
            n_latest: Number of latest articles to fetch
            n_historical: Number of historical articles to fetch

        Returns:
            Formatted string of news articles for inclusion in prompts
        """
        # Check cache first
        cached_result = self.cache.get(query)
        if cached_result is not None:
            logger.info(f"Using cached news for query: {query[:50]}...")
            return cached_result

        try:
            from asknews_sdk import AsyncAskNewsSDK
        except ImportError:
            raise ImportError("asknews_sdk not installed. Run: poetry add asknews")

        async with AsyncAskNewsSDK(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes={"news"},
        ) as sdk:
            # Strategy 1: Latest news (recent/hot)
            logger.info(f"Searching latest news for: {query[:50]}...")
            hot_response = await sdk.news.search_news(
                query=query,
                n_articles=n_latest,
                return_type="both",
                strategy="latest news",
            )

            # Rate limit delay
            logger.debug(f"Waiting {self._rate_limit_delay}s for rate limit...")
            await asyncio.sleep(self._rate_limit_delay)

            # Strategy 2: Historical news (news knowledge)
            logger.info(f"Searching historical news for: {query[:50]}...")
            historical_response = await sdk.news.search_news(
                query=query,
                n_articles=n_historical,
                return_type="both",
                strategy="news knowledge",
            )

        hot_articles = hot_response.as_dicts if hot_response.as_dicts else []
        historical_articles = historical_response.as_dicts if historical_response.as_dicts else []

        logger.info(f"Found {len(hot_articles)} latest + {len(historical_articles)} historical articles")

        # Format results
        formatted = "Here are the relevant news articles:\n\n"

        if hot_articles:
            formatted += self._format_articles(hot_articles)
        if historical_articles:
            formatted += self._format_articles(historical_articles)
        if not hot_articles and not historical_articles:
            formatted += "No articles were found.\n\n"

        # Cache result
        self.cache.set(query, formatted)

        return formatted

    def get_formatted_news(self, query: str) -> str:
        """Synchronous wrapper for get_formatted_news_async."""
        return asyncio.run(self.get_formatted_news_async(query))

    def _format_articles(self, articles: list) -> str:
        """Format a list of articles for prompt inclusion."""
        formatted = ""

        # Sort by date (newest first)
        sorted_articles = sorted(
            articles,
            key=lambda x: x.pub_date if hasattr(x, 'pub_date') and x.pub_date else datetime.min,
            reverse=True,
        )

        for article in sorted_articles:
            title = getattr(article, 'eng_title', None) or getattr(article, 'title', 'Untitled')
            summary = getattr(article, 'summary', '')
            language = getattr(article, 'language', 'unknown')
            source_id = getattr(article, 'source_id', 'unknown')
            url = getattr(article, 'article_url', '')
            pub_date = getattr(article, 'pub_date', None)

            if pub_date:
                date_str = pub_date.strftime("%B %d, %Y %I:%M %p")
            else:
                date_str = "Unknown date"

            formatted += (
                f"**{title}**\n"
                f"{summary}\n"
                f"Original language: {language}\n"
                f"Publish date: {date_str}\n"
                f"Source: [{source_id}]({url})\n\n"
            )

        return formatted

    # -------------------------------------------------------------------------
    # Deep Research
    # -------------------------------------------------------------------------

    async def get_formatted_deep_research(
        self,
        query: str,
        sources: list[str] | None = None,
        model: str = _default_model,
        search_depth: int = _default_search_depth,
        max_depth: int = _default_max_depth,
        filter_params: dict[str, bool] | None = None,
    ) -> str:
        """
        Get deep research results formatted for prompts.

        Uses AskNews's get_deep_news endpoint which provides AI-synthesized
        research combining multiple sources.

        Args:
            query: Research query/question
            sources: Sources to search - ["asknews", "google", "x", "wiki"]
            model: Model to use - "deepseek-basic", "deepseek", "claude-3-7-sonnet-latest", "o3-mini"
            search_depth: Search depth (1-4)
            max_depth: Maximum depth (1-6)
            filter_params: Optional filter parameters (e.g., {"premium": True})

        Returns:
            Formatted research text
        """
        response = await self.run_deep_research(
            query=query,
            sources=sources,
            model=model,
            search_depth=search_depth,
            max_depth=max_depth,
            filter_params=filter_params,
        )

        text = response.choices[0].message.content

        # Extract content from <final_answer> tags if present
        start_tag = "<final_answer>"
        end_tag = "</final_answer>"
        start_index = text.find(start_tag)

        if start_index != -1:
            start_index += len(start_tag)
            end_index = text.find(end_tag, start_index)
            if end_index != -1:
                return text[start_index:end_index].strip()

        return text

    async def run_deep_research(
        self,
        query: str,
        sources: list[str] | None = None,
        model: str = _default_model,
        search_depth: int = _default_search_depth,
        max_depth: int = _default_max_depth,
        filter_params: dict[str, bool] | None = None,
    ):
        """
        Run deep research and return raw response.

        Args:
            query: Research query
            sources: Sources to search
            model: Model to use
            search_depth: Search depth
            max_depth: Maximum depth
            filter_params: Optional filters

        Returns:
            CreateDeepNewsResponse from AskNews SDK
        """
        try:
            from asknews_sdk import AsyncAskNewsSDK
            from asknews_sdk.dto.deepnews import CreateDeepNewsResponse
        except ImportError:
            raise ImportError(
                "asknews_sdk not installed or outdated. Run: poetry add asknews@0.11.6"
            )

        if sources is None:
            sources = self._default_sources

        logger.info(f"Running deep research: {query[:50]}... (sources={sources}, depth={search_depth}/{max_depth})")

        async with AsyncAskNewsSDK(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes={"chat", "news", "stories", "analytics"},
        ) as sdk:
            response = await sdk.chat.get_deep_news(
                messages=[{"role": "user", "content": query}],
                search_depth=search_depth,
                max_depth=max_depth,
                sources=sources,
                stream=False,
                return_sources=False,
                model=model,
                inline_citations="numbered",
                filter_params=filter_params,
            )

            if not isinstance(response, CreateDeepNewsResponse):
                raise ValueError("Response is not a CreateDeepNewsResponse")

            logger.info("Deep research complete")
            return response

    # -------------------------------------------------------------------------
    # Presets (matching Metaculus template)
    # -------------------------------------------------------------------------

    async def call_preconfigured_version(self, preset: str, prompt: str) -> str:
        """
        Call a preconfigured research preset.

        Available presets:
        - "asknews/news-summaries" - Dual strategy news search
        - "asknews/deep-research/low-depth" - Light deep research (asknews only)
        - "asknews/deep-research/medium-depth" - Medium deep research (all sources)
        - "asknews/deep-research/high-depth" - Deep research (all sources, max depth)

        Model can be appended: "asknews/deep-research/low-depth/claude-3-7-sonnet-latest"

        Args:
            preset: Preset name
            prompt: Query/prompt to research

        Returns:
            Formatted research results
        """
        if "asknews/news-summaries" in preset:
            return await self.get_formatted_news_async(prompt)

        if "deep-research" not in preset:
            raise ValueError(f"Unknown preset: {preset}")

        # Extract model from preset if specified
        parts = preset.split("/")
        try:
            model = parts[3] if len(parts) > 3 else self._default_model
        except IndexError:
            model = self._default_model

        if "asknews/deep-research/low-depth" in preset:
            return await self.get_formatted_deep_research(
                prompt,
                sources=self._default_sources,
                search_depth=1,
                max_depth=1,
                model=model,
            )
        elif "asknews/deep-research/medium-depth" in preset:
            return await self.get_formatted_deep_research(
                prompt,
                sources=["asknews", "google", "x", "wiki"],
                filter_params={"premium": True},
                search_depth=2,
                max_depth=4,
                model=model,
            )
        elif "asknews/deep-research/high-depth" in preset:
            return await self.get_formatted_deep_research(
                prompt,
                sources=["asknews", "google", "x", "wiki"],
                filter_params={"premium": True},
                search_depth=4,
                max_depth=6,
                model=model,
            )
        else:
            raise ValueError(f"Unknown preset: {preset}")

    # -------------------------------------------------------------------------
    # Wikipedia Search
    # -------------------------------------------------------------------------

    async def search_wiki(self, query: str) -> str:
        """
        Search Wikipedia using AskNews SDK.

        Args:
            query: Search query

        Returns:
            Formatted Wikipedia content
        """
        try:
            from asknews_sdk import AsyncAskNewsSDK
        except ImportError:
            raise ImportError("asknews_sdk not installed. Run: poetry add asknews")

        logger.info(f"Searching Wikipedia for: {query[:50]}...")

        async with AsyncAskNewsSDK(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes={"news"},  # Wiki uses news scope
        ) as sdk:
            response = await sdk.wiki.search_wiki(query=query)

        documents = response.documents if hasattr(response, 'documents') else []

        if not documents:
            return f"No Wikipedia results found for: {query}\n"

        formatted = f"## Wikipedia Results for: {query}\n\n"
        for doc in documents:
            content = getattr(doc, 'content', '')
            if content:
                # First line is usually the title
                lines = content.split('\n')
                title = lines[0].strip() if lines else query
                body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else content
                formatted += f"### {title}\n{body}\n\n"

        logger.info(f"Found {len(documents)} Wikipedia documents")
        return formatted
