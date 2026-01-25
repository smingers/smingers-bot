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

        # Use mode-aware model selection (_active_models set by main.py)
        active_models = self.config.get("_active_models", {})
        model = active_models.get(
            "query_generator",
            self.config.get("models", {}).get("query_generator", "claude-3-haiku-20240307")
        )

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

    def _get_asknews_client(self):
        """Get or create AskNews SDK client.

        Uses OAuth credentials (ASKNEWS_CLIENT_ID + ASKNEWS_CLIENT_SECRET).
        Returns None if credentials not configured.
        """
        if hasattr(self, '_asknews_client') and self._asknews_client:
            return self._asknews_client

        try:
            from asknews_sdk import AskNewsSDK
        except ImportError:
            logger.error("asknews SDK not installed. Run: poetry add asknews")
            return None

        client_id = os.getenv("ASKNEWS_CLIENT_ID")
        client_secret = os.getenv("ASKNEWS_CLIENT_SECRET")

        if client_id and client_secret:
            try:
                self._asknews_client = AskNewsSDK(
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=["news", "chat", "stories", "analytics"],
                )
                logger.info("AskNews SDK initialized with OAuth credentials")
                return self._asknews_client
            except Exception as e:
                logger.error(f"Failed to initialize AskNews SDK: {e}")
                return None
        else:
            logger.warning("AskNews credentials not set (need ASKNEWS_CLIENT_ID + ASKNEWS_CLIENT_SECRET)")
            return None

    async def _search_asknews(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search news using AskNews SDK.

        Uses the official SDK for better reliability and features.
        Provides article summaries which are often sufficient without scraping.
        """
        client = self._get_asknews_client()
        if not client:
            return ("asknews", [])

        # Get config options
        sources = self.config.get("research", {}).get("sources", [])
        asknews_config = next((s for s in sources if s.get("type") == "asknews"), {})
        max_results = asknews_config.get("max_results", 10)
        hours_back = asknews_config.get("hours_back", 72)  # Default 3 days

        try:
            # SDK is synchronous, run in thread pool to avoid blocking
            def do_search():
                return client.news.search_news(
                    query=query,
                    n_articles=max_results,
                    return_type="dicts",
                    method="kw",  # Keyword search
                    hours_back=hours_back,
                    diversify_sources=True,
                )

            response = await asyncio.get_event_loop().run_in_executor(None, do_search)

            results = []
            articles = response.as_dicts if hasattr(response, 'as_dicts') else []

            for article in articles[:max_results]:
                # SDK returns objects with attributes, not dicts
                title = getattr(article, 'eng_title', None) or getattr(article, 'title', '')
                url = getattr(article, 'article_url', '')
                summary = getattr(article, 'summary', '')
                pub_date = getattr(article, 'pub_date', None)

                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=summary,
                    source="asknews",
                    published_date=str(pub_date) if pub_date else None,
                    full_content=summary,  # AskNews provides summaries
                ))

            logger.info(f"AskNews returned {len(results)} articles for query: {query[:50]}...")
            return ("asknews", results)

        except Exception as e:
            logger.error(f"AskNews search failed: {e}")
            return ("asknews", [])

    async def get_asknews_forecast(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str = "",
    ) -> Optional[dict]:
        """Get a forecast from AskNews for a question.

        This uses AskNews's forecast endpoint which provides:
        - Probability estimate (0-100)
        - Reasoning with sources
        - Timeline of relevant events
        - Confidence level

        This is a "deep API call" - costs more but provides expert-level analysis.

        Returns dict with forecast data or None if unavailable.
        """
        client = self._get_asknews_client()
        if not client:
            return None

        # Get config options
        sources = self.config.get("research", {}).get("sources", [])
        asknews_config = next((s for s in sources if s.get("type") == "asknews"), {})

        # Check if forecast is enabled
        if not asknews_config.get("forecast_enabled", False):
            logger.debug("AskNews forecast disabled in config")
            return None

        # Forecast-specific config
        lookback = asknews_config.get("forecast_lookback", 14)
        articles_to_use = asknews_config.get("forecast_articles", 15)
        model = asknews_config.get("forecast_model", "gpt-4.1-2025-04-14")
        web_search = asknews_config.get("forecast_web_search", True)

        # Build the forecast query
        query = f"{question_title}"
        if resolution_criteria:
            query += f"\n\nResolution criteria: {resolution_criteria[:500]}"

        try:
            def do_forecast():
                return client.chat.get_forecast(
                    query=query,
                    lookback=lookback,
                    articles_to_use=articles_to_use,
                    model=model,
                    web_search=web_search,
                    additional_context=question_text[:1000] if question_text else None,
                )

            response = await asyncio.get_event_loop().run_in_executor(None, do_forecast)

            # Extract relevant fields from ForecastResponse
            forecast_data = {
                "probability": response.probability / 100.0 if response.probability else None,
                "confidence": response.confidence,
                "llm_confidence": response.llm_confidence,
                "reasoning": response.reasoning,
                "summary": response.summary,
                "timeline": response.timeline,
                "sources": [
                    {
                        "title": s.get("eng_title", s.get("title", "")),
                        "url": s.get("article_url", ""),
                        "summary": s.get("summary", ""),
                    }
                    for s in (response.sources or [])[:10]
                ],
                "key_facets": response.key_facets,
                "model_used": response.model_used,
                "choice": response.choice,  # True/False for binary questions
                "likelihood": response.likelihood,  # e.g. "likely", "unlikely"
            }

            logger.info(f"AskNews forecast: {response.probability}% probability, "
                       f"confidence={response.confidence}")
            return forecast_data

        except Exception as e:
            logger.error(f"AskNews forecast failed: {e}")
            return None

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
