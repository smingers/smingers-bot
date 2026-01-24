"""
Research Orchestrator

Coordinates multiple search sources to gather information for forecasting:
- Perplexity API (reasoning + search)
- Web search (via Serper)
- Google News (via Serper)
- AskNews API
- Full article scraping (via Trafilatura/BeautifulSoup)
"""

import asyncio
import os
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from ..utils.llm import LLMClient, LLMResponse
from .extractor import ContentExtractor, ExtractedContent

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str  # Which search provider
    published_date: Optional[str] = None
    full_content: Optional[str] = None  # Full article text if scraped


@dataclass
class ResearchResults:
    """Aggregated research results from all sources."""
    queries: list[str]
    results_by_source: dict[str, list[SearchResult]]
    perplexity_synthesis: Optional[str] = None
    total_results: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_all_results(self) -> list[SearchResult]:
        """Get all results flattened."""
        all_results = []
        for source_results in self.results_by_source.values():
            all_results.extend(source_results)
        return all_results


class ResearchOrchestrator:
    """
    Coordinates research across multiple sources.

    Usage:
        orchestrator = ResearchOrchestrator(config)
        results = await orchestrator.research(question)
    """

    def __init__(self, config: dict):
        self.config = config
        self.llm = LLMClient()

        # Initialize HTTP clients for various APIs
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Content extractor for full article scraping
        self.extractor = ContentExtractor()

    async def close(self):
        """Clean up resources."""
        await self.http_client.aclose()
        await self.extractor.close()

    async def research(
        self,
        question_title: str,
        question_text: str,
        question_type: str = "binary",
    ) -> ResearchResults:
        """
        Conduct research on a question.

        Args:
            question_title: The question title
            question_text: Full question description
            question_type: binary, numeric, or multiple_choice

        Returns:
            ResearchResults with all gathered information
        """
        # Step 1: Generate search queries
        queries = await self._generate_queries(question_title, question_text)
        logger.info(f"Generated {len(queries)} search queries")

        # Step 2: Execute searches in parallel
        results_by_source: dict[str, list[SearchResult]] = {}
        tasks = []

        # Perplexity (if enabled)
        if self._is_source_enabled("perplexity"):
            tasks.append(self._search_perplexity(question_title, question_text))

        # Web search via Serper (if enabled)
        if self._is_source_enabled("web_search"):
            for query in queries[:3]:  # Limit queries
                tasks.append(self._search_web(query))

        # Google News via Serper (if enabled)
        if self._is_source_enabled("google_news"):
            for query in queries[:2]:  # Limit news queries
                tasks.append(self._search_google_news(query))

        # Claude native web search (if enabled)
        if self._is_source_enabled("claude_web_search"):
            tasks.append(self._search_claude_native(question_title, question_text))

        # AskNews (if enabled)
        if self._is_source_enabled("asknews"):
            tasks.append(self._search_asknews(question_title))

        # Execute all searches
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in search_results:
                if isinstance(result, Exception):
                    logger.warning(f"Search failed: {result}")
                    continue
                if isinstance(result, tuple):
                    source, items = result
                    if source not in results_by_source:
                        results_by_source[source] = []
                    results_by_source[source].extend(items)

        # Step 3: Scrape full article content (if enabled)
        if self._is_source_enabled("article_scraping"):
            results_by_source = await self._scrape_articles(results_by_source)

        # Count total results
        total_results = sum(len(items) for items in results_by_source.values())

        # Get Perplexity synthesis if available
        perplexity_synthesis = None
        if "perplexity" in results_by_source:
            # Perplexity returns synthesis as a "result"
            perplexity_results = results_by_source.get("perplexity", [])
            if perplexity_results and perplexity_results[0].snippet:
                perplexity_synthesis = perplexity_results[0].snippet

        return ResearchResults(
            queries=queries,
            results_by_source=results_by_source,
            perplexity_synthesis=perplexity_synthesis,
            total_results=total_results,
        )

    def _is_source_enabled(self, source_type: str) -> bool:
        """Check if a research source is enabled in config."""
        sources = self.config.get("research", {}).get("sources", [])
        for source in sources:
            if source.get("type") == source_type and source.get("enabled", False):
                return True
        return False

    async def _generate_queries(
        self,
        question_title: str,
        question_text: str,
    ) -> list[str]:
        """Generate search queries using an LLM."""
        num_queries = self.config.get("research", {}).get("queries_per_question", 5)

        description_text = question_text[:1000] if question_text else "(No description provided)"
        prompt = f"""Generate {num_queries} diverse search queries to research this forecasting question.

Question: {question_title}

Description: {description_text}

Generate queries that will help find:
1. Historical base rates and precedents
2. Recent news and developments
3. Expert opinions and analysis
4. Statistical data and trends
5. Counterarguments and alternative perspectives

Output exactly {num_queries} queries, one per line, no numbering or bullets.
Keep queries concise (under 10 words each).
"""

        model = self.config.get("models", {}).get("query_generator", "claude-3-haiku-20240307")

        try:
            response = await self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
            return queries[:num_queries]
        except Exception as e:
            logger.error(f"Failed to generate queries: {e}")
            # Fallback to simple queries
            return [question_title, f"{question_title} statistics", f"{question_title} recent news"]

    async def _search_perplexity(
        self,
        question_title: str,
        question_text: str,
    ) -> tuple[str, list[SearchResult]]:
        """Search using Perplexity API."""
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            logger.warning("PERPLEXITY_API_KEY not set, skipping Perplexity search")
            return ("perplexity", [])

        # Get model from config
        sources = self.config.get("research", {}).get("sources", [])
        perplexity_config = next((s for s in sources if s.get("type") == "perplexity"), {})
        model = perplexity_config.get("model", "sonar-reasoning-pro")

        description_text = question_text[:2000] if question_text else "(No description provided)"
        prompt = f"""Research this forecasting question and provide relevant information:

Question: {question_title}

Description: {description_text}

Provide:
1. Relevant historical precedents and base rates
2. Recent developments and news
3. Key factors that could influence the outcome
4. Expert opinions if available
5. Data and statistics

Be thorough and cite sources where possible.
"""

        try:
            response = await self.http_client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Return as a single "result" with the synthesis
            return ("perplexity", [SearchResult(
                title="Perplexity Research Synthesis",
                url="https://perplexity.ai",
                snippet=content,
                source="perplexity",
            )])

        except Exception as e:
            logger.error(f"Perplexity search failed: {e}")
            return ("perplexity", [])

    async def _search_web(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search the web using Serper API."""
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            logger.warning("SERPER_API_KEY not set, skipping web search")
            return ("web_search", [])

        try:
            # Remove quotes from query - Serper doesn't handle them well
            clean_query = query.replace('"', '').replace("'", "")
            response = await self.http_client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": clean_query, "num": 10},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", [])[:10]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper",
                ))

            logger.info(f"Serper returned {len(results)} results for query: {query[:50]}...")
            return ("web_search", results)

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ("web_search", [])

    async def _search_google_news(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search Google News using Serper API."""
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            logger.warning("SERPER_API_KEY not set, skipping Google News search")
            return ("google_news", [])

        try:
            clean_query = query.replace('"', '').replace("'", "")
            response = await self.http_client.post(
                "https://google.serper.dev/news",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": clean_query, "num": 10},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("news", [])[:10]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google_news",
                    published_date=item.get("date"),
                ))

            logger.info(f"Google News returned {len(results)} results for query: {query[:50]}...")
            return ("google_news", results)

        except Exception as e:
            logger.error(f"Google News search failed: {e}")
            return ("google_news", [])

    async def _scrape_articles(
        self,
        results_by_source: dict[str, list[SearchResult]],
    ) -> dict[str, list[SearchResult]]:
        """Scrape full article content for search results."""
        # Get scraping config
        sources = self.config.get("research", {}).get("sources", [])
        scraping_config = next(
            (s for s in sources if s.get("type") == "article_scraping"),
            {}
        )
        max_articles = scraping_config.get("max_articles", 5)
        max_content_per_article = scraping_config.get("max_content_length", 5000)

        # Collect URLs to scrape (prioritize news sources)
        urls_to_scrape = []
        url_to_result: dict[str, SearchResult] = {}

        # Priority order: google_news, asknews, web_search
        for source in ["google_news", "asknews", "web_search"]:
            if source in results_by_source:
                for result in results_by_source[source]:
                    if result.url and result.url not in url_to_result:
                        urls_to_scrape.append(result.url)
                        url_to_result[result.url] = result

        # Limit URLs
        urls_to_scrape = urls_to_scrape[:max_articles]

        if not urls_to_scrape:
            return results_by_source

        logger.info(f"Scraping {len(urls_to_scrape)} articles...")

        # Extract content
        extracted = await self.extractor.extract_batch(
            urls_to_scrape,
            max_concurrent=5,
            max_urls=max_articles,
        )

        # Update results with full content
        success_count = 0
        for content in extracted:
            if content.success and content.url in url_to_result:
                result = url_to_result[content.url]
                # Truncate content if needed
                text = content.text
                if len(text) > max_content_per_article:
                    text = text[:max_content_per_article] + "...[truncated]"
                result.full_content = text
                success_count += 1

        logger.info(f"Successfully scraped {success_count}/{len(urls_to_scrape)} articles")

        return results_by_source

    async def _search_asknews(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search using AskNews API.

        Supports two auth methods:
        1. API Key (ASKNEWS_API_KEY) - simpler, static token (scopes set at key creation)
        2. OAuth (ASKNEWS_CLIENT_ID + ASKNEWS_CLIENT_SECRET) - short-lived tokens

        IMPORTANT: Your credentials must have the 'news' scope enabled.
        Go to https://my.asknews.app -> API Credentials to check/regenerate.
        """
        api_key = os.getenv("ASKNEWS_API_KEY")
        client_id = os.getenv("ASKNEWS_CLIENT_ID")
        client_secret = os.getenv("ASKNEWS_CLIENT_SECRET")

        # Determine auth method
        if api_key:
            # Use API key directly (scopes defined at key creation time)
            headers = {"Authorization": f"Bearer {api_key}"}
        elif client_id and client_secret:
            # Use OAuth flow to get token with required scopes
            # Token URL from AskNews SDK: https://auth.asknews.app/oauth2/token
            try:
                import base64
                # AskNews uses HTTP Basic Auth for the token endpoint
                credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
                auth_response = await self.http_client.post(
                    "https://auth.asknews.app/oauth2/token",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "client_credentials",
                        # Request the scopes needed for news search
                        "scope": "news chat stories analytics offline openid",
                    },
                )
                auth_response.raise_for_status()
                token = auth_response.json().get("access_token")
                headers = {"Authorization": f"Bearer {token}"}
            except httpx.HTTPStatusError as e:
                logger.error(f"AskNews OAuth failed (HTTP {e.response.status_code}): {e.response.text}")
                if e.response.status_code == 403:
                    logger.error("403 Forbidden - Your credentials may not have the required scopes. "
                                "Go to https://my.asknews.app -> API Credentials and regenerate "
                                "with 'news' scope enabled.")
                return ("asknews", [])
            except Exception as e:
                logger.error(f"AskNews OAuth failed: {e}")
                return ("asknews", [])
        else:
            logger.warning("AskNews credentials not set (need ASKNEWS_API_KEY or CLIENT_ID+SECRET)")
            return ("asknews", [])

        try:
            response = await self.http_client.get(
                "https://api.asknews.app/v1/news/search",
                headers=headers,
                params={"q": query, "n_articles": 10},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for article in data.get("articles", [])[:10]:
                results.append(SearchResult(
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    snippet=article.get("summary", ""),
                    source="asknews",
                    published_date=article.get("published_at"),
                ))

            logger.info(f"AskNews returned {len(results)} articles")
            return ("asknews", results)

        except httpx.HTTPStatusError as e:
            logger.error(f"AskNews search failed (HTTP {e.response.status_code}): {e.response.text}")
            if e.response.status_code == 403:
                logger.error("403 Forbidden - Your credentials may not have the 'news' scope. "
                            "Go to https://my.asknews.app -> API Credentials and regenerate "
                            "with 'news' scope enabled.")
            return ("asknews", [])
        except Exception as e:
            logger.error(f"AskNews search failed: {e}")
            return ("asknews", [])

    async def _search_claude_native(
        self,
        question_title: str,
        question_text: str,
    ) -> tuple[str, list[SearchResult]]:
        """Search using Claude's native web search tool (API feature).

        Requires Anthropic API. Cost: $10 per 1,000 searches + token costs.
        Works with Haiku, Sonnet 3.5, and Sonnet 3.7.
        """
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping Claude web search")
            return ("claude_web_search", [])

        # Get model from config (default to haiku for cost)
        sources = self.config.get("research", {}).get("sources", [])
        claude_config = next((s for s in sources if s.get("type") == "claude_web_search"), {})
        model = claude_config.get("model", "claude-3-haiku-20240307")

        description_text = question_text[:2000] if question_text else "(No description provided)"
        prompt = f"""Research this forecasting question and provide relevant, up-to-date information:

Question: {question_title}

Description: {description_text}

Search for:
1. Recent news and developments (last few months)
2. Historical precedents and base rates
3. Expert analysis and opinions
4. Relevant statistics and data

Provide a comprehensive summary with specific facts, dates, and sources."""

        try:
            client = anthropic.Anthropic(api_key=api_key)

            response = client.messages.create(
                model=model,
                max_tokens=2048,
                tools=[{"type": "web_search", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
                betas=["web-search-2025-03-05"],
            )

            # Extract the text content from response
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text

            logger.info(f"Claude web search completed, got {len(content)} chars")

            return ("claude_web_search", [SearchResult(
                title="Claude Web Search Synthesis",
                url="https://anthropic.com",
                snippet=content,
                source="claude_web_search",
            )])

        except Exception as e:
            logger.error(f"Claude web search failed: {e}")
            return ("claude_web_search", [])

    def synthesize_results(self, results: ResearchResults) -> str:
        """
        Create a markdown synthesis of all research results.
        This becomes the research artifact.
        """
        lines = []

        lines.append("# Research Synthesis")
        lines.append("")
        lines.append(f"**Generated:** {results.timestamp}")
        lines.append(f"**Total Sources:** {results.total_results}")
        lines.append("")

        # Queries used
        lines.append("## Search Queries")
        for i, query in enumerate(results.queries, 1):
            lines.append(f"{i}. {query}")
        lines.append("")

        # Perplexity synthesis (if available)
        if results.perplexity_synthesis:
            lines.append("## AI-Synthesized Research (Perplexity)")
            lines.append("")
            lines.append(results.perplexity_synthesis)
            lines.append("")

        # Google News results
        if "google_news" in results.results_by_source:
            lines.append("## Google News Results")
            lines.append("")
            for result in results.results_by_source["google_news"]:
                date_str = f" ({result.published_date})" if result.published_date else ""
                lines.append(f"### [{result.title}]({result.url}){date_str}")
                lines.append(f"> {result.snippet}")
                if result.full_content:
                    lines.append("")
                    lines.append("**Full Article:**")
                    lines.append(result.full_content[:3000])  # Limit for synthesis
                lines.append("")

        # Web search results
        if "web_search" in results.results_by_source:
            lines.append("## Web Search Results")
            lines.append("")
            for result in results.results_by_source["web_search"]:
                lines.append(f"### [{result.title}]({result.url})")
                lines.append(f"> {result.snippet}")
                if result.full_content:
                    lines.append("")
                    lines.append("**Full Article:**")
                    lines.append(result.full_content[:3000])  # Limit for synthesis
                lines.append("")

        # AskNews results
        if "asknews" in results.results_by_source:
            lines.append("## News Articles (AskNews)")
            lines.append("")
            for result in results.results_by_source["asknews"]:
                date_str = f" ({result.published_date})" if result.published_date else ""
                lines.append(f"### [{result.title}]({result.url}){date_str}")
                lines.append(f"> {result.snippet}")
                if result.full_content:
                    lines.append("")
                    lines.append("**Full Article:**")
                    lines.append(result.full_content[:3000])
                lines.append("")

        # Claude web search results
        if "claude_web_search" in results.results_by_source:
            lines.append("## Claude Web Search Results")
            lines.append("")
            for result in results.results_by_source["claude_web_search"]:
                lines.append(result.snippet)
                lines.append("")

        return "\n".join(lines)
