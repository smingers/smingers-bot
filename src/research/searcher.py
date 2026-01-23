"""
Research Orchestrator

Coordinates multiple search sources to gather information for forecasting:
- Perplexity API (reasoning + search)
- Web search (via Serper or Exa)
- AskNews API
"""

import asyncio
import os
import logging
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from ..utils.llm import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str  # Which search provider
    published_date: Optional[str] = None


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

    async def close(self):
        """Clean up resources."""
        await self.http_client.aclose()

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

        # Web search (if enabled)
        if self._is_source_enabled("web_search"):
            for query in queries[:3]:  # Limit queries
                tasks.append(self._search_web(query))

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

        prompt = f"""Generate {num_queries} diverse search queries to research this forecasting question.

Question: {question_title}

Description: {question_text[:1000]}

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

        prompt = f"""Research this forecasting question and provide relevant information:

Question: {question_title}

Description: {question_text[:2000]}

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
            response = await self.http_client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": 10},
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

            return ("web_search", results)

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ("web_search", [])

    async def _search_asknews(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search using AskNews API."""
        client_id = os.getenv("ASKNEWS_CLIENT_ID")
        client_secret = os.getenv("ASKNEWS_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.warning("AskNews credentials not set, skipping AskNews search")
            return ("asknews", [])

        try:
            # First get access token
            auth_response = await self.http_client.post(
                "https://api.asknews.app/v1/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            auth_response.raise_for_status()
            token = auth_response.json().get("access_token")

            # Then search
            response = await self.http_client.get(
                "https://api.asknews.app/v1/news/search",
                headers={"Authorization": f"Bearer {token}"},
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

            return ("asknews", results)

        except Exception as e:
            logger.error(f"AskNews search failed: {e}")
            return ("asknews", [])

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

        # Web search results
        if "web_search" in results.results_by_source:
            lines.append("## Web Search Results")
            lines.append("")
            for result in results.results_by_source["web_search"]:
                lines.append(f"### [{result.title}]({result.url})")
                lines.append(f"> {result.snippet}")
                lines.append("")

        # AskNews results
        if "asknews" in results.results_by_source:
            lines.append("## News Articles (AskNews)")
            lines.append("")
            for result in results.results_by_source["asknews"]:
                date_str = f" ({result.published_date})" if result.published_date else ""
                lines.append(f"### [{result.title}]({result.url}){date_str}")
                lines.append(f"> {result.snippet}")
                lines.append("")

        return "\n".join(lines)
