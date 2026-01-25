"""
Research Orchestrator

Coordinates multiple search sources to gather information for forecasting:
- AskNews API (news search, Wikipedia, deep research)
- Perplexity API (reasoning + search)
- Web search (via Serper)
- Google News (via Serper)
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
from .asknews_searcher import AskNewsSearcher, AskNewsCache

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
class ResearchIteration:
    """A single iteration of iterative research."""
    iteration: int
    queries: list[str]
    results: list[SearchResult]
    gaps_identified: list[str]
    confidence_score: float  # 0-1, how confident the LLM is that research is sufficient


@dataclass
class ResearchResults:
    """Aggregated research results from all sources."""
    queries: list[str]
    results_by_source: dict[str, list[SearchResult]]
    perplexity_synthesis: Optional[str] = None
    total_results: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Iterative research tracking
    iterations: list[ResearchIteration] = field(default_factory=list)
    final_confidence: float = 0.0
    # Deep research output (from AskNews get_deep_news)
    deep_research: Optional[str] = None
    # Formatted news output (from AskNews dual strategy search)
    formatted_news: Optional[str] = None

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

        # Initialize AskNews searcher (if credentials available)
        self._asknews_searcher: Optional[AskNewsSearcher] = None
        self._init_asknews_searcher()

    def _init_asknews_searcher(self) -> None:
        """Initialize AskNews searcher if credentials are available."""
        client_id = os.getenv("ASKNEWS_CLIENT_ID")
        client_secret = os.getenv("ASKNEWS_CLIENT_SECRET")

        if client_id and client_secret:
            try:
                # Get cache mode from config
                asknews_config = self._get_asknews_config()
                cache_mode = asknews_config.get("cache_mode", "no_cache")

                self._asknews_searcher = AskNewsSearcher(
                    client_id=client_id,
                    client_secret=client_secret,
                    cache_mode=cache_mode,
                )
                logger.info("AskNews searcher initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AskNews searcher: {e}")
                self._asknews_searcher = None
        else:
            logger.debug("AskNews credentials not set, searcher not initialized")

    def _get_asknews_config(self) -> dict:
        """Get AskNews configuration from config."""
        sources = self.config.get("research", {}).get("sources", [])
        return next((s for s in sources if s.get("type") == "asknews"), {})

    async def close(self):
        """Clean up resources."""
        await self.http_client.aclose()
        await self.extractor.close()

    async def research(
        self,
        question_title: str,
        question_text: str,
        question_type: str = "binary",
        options: list[str] | None = None,
    ) -> ResearchResults:
        """
        Conduct research on a question.

        Uses iterative research if enabled in config, otherwise single-pass.

        Args:
            question_title: The question title
            question_text: Full question description
            question_type: binary, numeric, or multiple_choice
            options: List of option labels for multiple choice questions

        Returns:
            ResearchResults with all gathered information
        """
        # Check if iterative research is enabled
        iterative_config = self.config.get("research", {}).get("iterative", {})
        if iterative_config.get("enabled", False):
            return await self._research_iterative(
                question_title=question_title,
                question_text=question_text,
                question_type=question_type,
                options=options,
            )

        # Single-pass research (original behavior)
        return await self._research_single_pass(
            question_title=question_title,
            question_text=question_text,
            question_type=question_type,
            options=options,
        )

    async def _research_single_pass(
        self,
        question_title: str,
        question_text: str,
        question_type: str = "binary",
        options: list[str] | None = None,
    ) -> ResearchResults:
        """
        Single-pass research (original non-iterative approach).
        """
        # Step 1: Generate search queries
        queries = await self._generate_queries(question_title, question_text, options)
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

        # Deduplicate results
        results_by_source = self._deduplicate_results(results_by_source)

        # Count total results
        total_results = sum(len(items) for items in results_by_source.values())

        # Get Perplexity synthesis if available
        perplexity_synthesis = None
        if "perplexity" in results_by_source:
            # Perplexity returns synthesis as a "result"
            perplexity_results = results_by_source.get("perplexity", [])
            if perplexity_results and perplexity_results[0].snippet:
                perplexity_synthesis = perplexity_results[0].snippet

        # Step 4: Get deep research if enabled
        # This is the AI-synthesized research from AskNews get_deep_news endpoint
        deep_research_result = None
        if self._is_deep_research_enabled() and self._asknews_searcher:
            # Wait for rate limit before deep research
            # Free tier: 1 req/10s, so we wait 12s to be safe
            logger.info("Waiting 12s for AskNews rate limit before deep research...")
            await asyncio.sleep(12)
            logger.info("Running deep research via AskNews get_deep_news...")
            try:
                deep_research_result = await self.get_deep_research(
                    query=f"{question_title}\n\n{question_text}"
                )
                if deep_research_result:
                    logger.info(f"Deep research completed: {len(deep_research_result)} chars")
                else:
                    logger.warning("Deep research returned no results")
            except Exception as e:
                logger.error(f"Deep research failed: {e}")

        return ResearchResults(
            queries=queries,
            results_by_source=results_by_source,
            perplexity_synthesis=perplexity_synthesis,
            total_results=total_results,
            deep_research=deep_research_result,
        )

    async def _research_iterative(
        self,
        question_title: str,
        question_text: str,
        question_type: str = "binary",
        options: list[str] | None = None,
    ) -> ResearchResults:
        """
        Iterative/agentic research approach.

        The LLM analyzes initial results, identifies gaps, and generates
        targeted follow-up queries. This continues until:
        - The LLM is confident enough (>= confidence_threshold)
        - Max iterations reached
        - No new information gaps identified

        Based on AIA Forecaster paper showing agentic search improves Brier scores.
        """
        iterative_config = self.config.get("research", {}).get("iterative", {})
        max_iterations = iterative_config.get("max_iterations", 3)
        confidence_threshold = iterative_config.get("confidence_threshold", 0.7)
        queries_per_iteration = iterative_config.get("queries_per_iteration", 2)

        logger.info(f"Starting iterative research (max {max_iterations} iterations, "
                   f"confidence threshold: {confidence_threshold})")

        # Track all results across iterations
        all_queries: list[str] = []
        all_results_by_source: dict[str, list[SearchResult]] = {}
        iterations: list[ResearchIteration] = []

        # Build context for the question
        options_context = ""
        if options:
            options_str = "\n".join(f"- {opt}" for opt in options)
            options_context = f"\n\nOptions/Choices:\n{options_str}"

        for iteration in range(max_iterations):
            logger.info(f"Research iteration {iteration + 1}/{max_iterations}")

            if iteration == 0:
                # First iteration: generate initial queries
                queries = await self._generate_queries(question_title, question_text, options)
            else:
                # Subsequent iterations: generate targeted follow-up queries
                queries = await self._generate_followup_queries(
                    question_title=question_title,
                    question_text=question_text,
                    options_context=options_context,
                    current_results=all_results_by_source,
                    gaps=iterations[-1].gaps_identified if iterations else [],
                    num_queries=queries_per_iteration,
                )

            if not queries:
                logger.info("No more queries to execute, ending iteration")
                break

            all_queries.extend(queries)
            logger.info(f"Iteration {iteration + 1}: executing {len(queries)} queries")

            # Execute searches for this iteration
            iteration_results = await self._execute_searches(queries, question_title, question_text)

            # Merge results
            for source, results in iteration_results.items():
                if source not in all_results_by_source:
                    all_results_by_source[source] = []
                all_results_by_source[source].extend(results)

            # Deduplicate results (important for wiki which often returns same articles)
            all_results_by_source = self._deduplicate_results(all_results_by_source)

            # Scrape articles if enabled
            if self._is_source_enabled("article_scraping"):
                all_results_by_source = await self._scrape_articles(all_results_by_source)

            # Analyze results and identify gaps
            analysis = await self._analyze_research_gaps(
                question_title=question_title,
                question_text=question_text,
                options_context=options_context,
                results_by_source=all_results_by_source,
            )

            iteration_record = ResearchIteration(
                iteration=iteration + 1,
                queries=queries,
                results=list(iteration_results.values())[0] if iteration_results else [],
                gaps_identified=analysis["gaps"],
                confidence_score=analysis["confidence"],
            )
            iterations.append(iteration_record)

            logger.info(f"Iteration {iteration + 1}: confidence={analysis['confidence']:.2f}, "
                       f"gaps identified: {len(analysis['gaps'])}")

            # Check stopping conditions
            if analysis["confidence"] >= confidence_threshold:
                logger.info(f"Confidence threshold reached ({analysis['confidence']:.2f} >= "
                           f"{confidence_threshold}), stopping iteration")
                break

            if not analysis["gaps"]:
                logger.info("No information gaps identified, stopping iteration")
                break

            # Add delay between iterations to respect AskNews rate limits
            # Free tier: 1 req/10s, Spelunker: 1 req/s, Analyst: 5 req/s
            if iteration < max_iterations - 1:
                delay = iterative_config.get("iteration_delay_seconds", 2.0)
                if delay > 0:
                    logger.info(f"Waiting {delay}s before next iteration (rate limit protection)")
                    await asyncio.sleep(delay)

        # Count total results
        total_results = sum(len(items) for items in all_results_by_source.values())

        # Get Perplexity synthesis if available
        perplexity_synthesis = None
        if "perplexity" in all_results_by_source:
            perplexity_results = all_results_by_source.get("perplexity", [])
            if perplexity_results and perplexity_results[0].snippet:
                perplexity_synthesis = perplexity_results[0].snippet

        final_confidence = iterations[-1].confidence_score if iterations else 0.0

        # Run deep research if enabled
        # This is the AI-synthesized research from AskNews get_deep_news endpoint
        deep_research_result = None
        if self._is_deep_research_enabled() and self._asknews_searcher:
            # Wait for rate limit before deep research
            # Free tier: 1 req/10s, so we wait 12s to be safe
            logger.info("Waiting 12s for AskNews rate limit before deep research...")
            await asyncio.sleep(12)
            logger.info("Running deep research via AskNews get_deep_news...")
            try:
                deep_research_result = await self.get_deep_research(
                    query=f"{question_title}\n\n{question_text}"
                )
                if deep_research_result:
                    logger.info(f"Deep research completed: {len(deep_research_result)} chars")
                else:
                    logger.warning("Deep research returned no results")
            except Exception as e:
                logger.error(f"Deep research failed: {e}")

        logger.info(f"Iterative research complete: {len(iterations)} iterations, "
                   f"{total_results} total results, final confidence: {final_confidence:.2f}")

        return ResearchResults(
            queries=all_queries,
            results_by_source=all_results_by_source,
            perplexity_synthesis=perplexity_synthesis,
            total_results=total_results,
            iterations=iterations,
            final_confidence=final_confidence,
            deep_research=deep_research_result,
        )

    async def _execute_searches(
        self,
        queries: list[str],
        question_title: str,
        question_text: str,
    ) -> dict[str, list[SearchResult]]:
        """Execute searches across enabled sources for given queries."""
        results_by_source: dict[str, list[SearchResult]] = {}

        # Split tasks: non-AskNews can run in parallel, AskNews sources share rate limit
        non_asknews_tasks = []
        asknews_searches = []  # Will run sequentially due to shared rate limit

        # Perplexity (if enabled) - use question, not individual queries
        if self._is_source_enabled("perplexity"):
            non_asknews_tasks.append(self._search_perplexity(question_title, question_text))

        # Web search via Serper (if enabled)
        if self._is_source_enabled("web_search"):
            for query in queries[:3]:
                non_asknews_tasks.append(self._search_web(query))

        # Google News via Serper (if enabled)
        if self._is_source_enabled("google_news"):
            for query in queries[:2]:
                non_asknews_tasks.append(self._search_google_news(query))

        # Claude native web search (if enabled)
        if self._is_source_enabled("claude_web_search"):
            non_asknews_tasks.append(self._search_claude_native(question_title, question_text))

        # AskNews sources - collect for sequential execution
        # Note: AskNews news and wiki share the same rate limit (free tier: 1 req/10s)
        if self._is_source_enabled("asknews"):
            asknews_searches.append(("news", queries[0] if queries else question_title))

        if self._is_source_enabled("asknews_wiki"):
            # For wiki, search each option/entity if available, or use first query
            asknews_searches.append(("wiki", queries[0] if queries else question_title))

        # Execute non-AskNews searches in parallel
        if non_asknews_tasks:
            search_results = await asyncio.gather(*non_asknews_tasks, return_exceptions=True)

            for result in search_results:
                if isinstance(result, Exception):
                    logger.warning(f"Search failed: {result}")
                    continue
                if isinstance(result, tuple):
                    source, items = result
                    if source not in results_by_source:
                        results_by_source[source] = []
                    results_by_source[source].extend(items)

        # Execute AskNews searches sequentially with rate limit delay
        # Free tier: 1 req/10s, so we need to space out calls
        iterative_config = self.config.get("research", {}).get("iterative", {})
        asknews_delay = iterative_config.get("iteration_delay_seconds", 10)

        for i, (search_type, query) in enumerate(asknews_searches):
            # Add delay between AskNews API calls (not before the first one)
            if i > 0 and asknews_delay > 0:
                logger.info(f"Waiting {asknews_delay}s for AskNews rate limit...")
                await asyncio.sleep(asknews_delay)

            try:
                if search_type == "news":
                    source, items = await self._search_asknews(query)
                elif search_type == "wiki":
                    source, items = await self._search_asknews_wiki(query)
                else:
                    continue

                if source not in results_by_source:
                    results_by_source[source] = []
                results_by_source[source].extend(items)
            except Exception as e:
                logger.warning(f"AskNews {search_type} search failed: {e}")

        return results_by_source

    async def _generate_followup_queries(
        self,
        question_title: str,
        question_text: str,
        options_context: str,
        current_results: dict[str, list[SearchResult]],
        gaps: list[str],
        num_queries: int = 2,
    ) -> list[str]:
        """Generate targeted follow-up queries to fill identified gaps."""
        # Summarize what we already know
        results_summary = self._summarize_results_for_llm(current_results)

        gaps_text = "\n".join(f"- {gap}" for gap in gaps) if gaps else "None identified"

        prompt = f"""You are helping research a forecasting question. Based on what we've found so far,
generate {num_queries} targeted search queries to fill the information gaps.

QUESTION: {question_title}
{options_context}

WHAT WE'VE FOUND SO FAR:
{results_summary[:3000]}

INFORMATION GAPS TO FILL:
{gaps_text}

Generate {num_queries} specific, targeted search queries that will help fill these gaps.
Focus on finding concrete facts, statistics, recent developments, or expert opinions.
Each query should be concise (under 10 words) and directly address a gap.

Output exactly {num_queries} queries, one per line, no numbering or bullets.
"""

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
                max_tokens=300,
            )
            queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
            return queries[:num_queries]
        except Exception as e:
            logger.error(f"Failed to generate follow-up queries: {e}")
            return []

    async def _analyze_research_gaps(
        self,
        question_title: str,
        question_text: str,
        options_context: str,
        results_by_source: dict[str, list[SearchResult]],
    ) -> dict:
        """
        Analyze current research results to identify gaps and assess confidence.

        Returns:
            dict with 'gaps' (list of strings) and 'confidence' (float 0-1)
        """
        results_summary = self._summarize_results_for_llm(results_by_source)

        prompt = f"""You are a research analyst helping with a forecasting question.
Analyze the research gathered so far and identify what information is still missing.

QUESTION: {question_title}

DESCRIPTION: {question_text[:1000] if question_text else "(none)"}
{options_context}

RESEARCH GATHERED:
{results_summary[:4000]}

Analyze this research and provide:

1. CONFIDENCE SCORE (0.0 to 1.0): How confident are you that we have enough information to make a well-informed forecast? Consider:
   - Do we have relevant base rates or historical precedents?
   - Do we have recent/current information about the situation?
   - Do we understand the key factors that will determine the outcome?
   - Are there major unknowns that would significantly change the forecast?

2. INFORMATION GAPS: List specific pieces of information that are still missing and would help improve the forecast. Be specific about what exactly is needed.

Format your response EXACTLY as:
CONFIDENCE: [number between 0.0 and 1.0]

GAPS:
- [specific gap 1]
- [specific gap 2]
- [etc, or "None - research is sufficient" if confident]
"""

        active_models = self.config.get("_active_models", {})
        model = active_models.get(
            "query_generator",
            self.config.get("models", {}).get("query_generator", "claude-3-haiku-20240307")
        )

        try:
            response = await self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.content

            # Parse confidence score
            confidence = 0.5  # default
            import re
            conf_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", content)
            if conf_match:
                try:
                    confidence = float(conf_match.group(1))
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass

            # Parse gaps
            gaps = []
            gaps_section = re.search(r"GAPS:\s*\n(.*)", content, re.DOTALL)
            if gaps_section:
                gaps_text = gaps_section.group(1)
                for line in gaps_text.split("\n"):
                    line = line.strip()
                    if line.startswith("-"):
                        gap = line[1:].strip()
                        if gap and "none" not in gap.lower() and "sufficient" not in gap.lower():
                            gaps.append(gap)

            return {"confidence": confidence, "gaps": gaps}

        except Exception as e:
            logger.error(f"Failed to analyze research gaps: {e}")
            return {"confidence": 0.5, "gaps": ["Analysis failed"]}

    def _summarize_results_for_llm(
        self,
        results_by_source: dict[str, list[SearchResult]],
        max_length: int = 4000,
    ) -> str:
        """Create a concise summary of results for LLM consumption."""
        lines = []
        total_chars = 0

        for source, results in results_by_source.items():
            if total_chars >= max_length:
                break

            lines.append(f"\n### {source.upper()} ({len(results)} results)")

            for result in results[:5]:  # Limit per source
                if total_chars >= max_length:
                    break

                entry = f"- {result.title}"
                if result.published_date:
                    entry += f" ({result.published_date})"
                entry += f"\n  {result.snippet[:300]}"

                if len(entry) + total_chars < max_length:
                    lines.append(entry)
                    total_chars += len(entry)

        return "\n".join(lines)

    def _is_source_enabled(self, source_type: str) -> bool:
        """Check if a research source is enabled in config."""
        sources = self.config.get("research", {}).get("sources", [])
        for source in sources:
            if source.get("type") == source_type and source.get("enabled", False):
                return True
        return False

    def _is_deep_research_enabled(self) -> bool:
        """Check if deep research is enabled in AskNews config."""
        asknews_config = self._get_asknews_config()
        if not asknews_config:
            return False
        deep_research_config = asknews_config.get("deep_research", {})
        return deep_research_config.get("enabled", False)

    def _deduplicate_results(
        self,
        results_by_source: dict[str, list[SearchResult]],
    ) -> dict[str, list[SearchResult]]:
        """Remove duplicate results within each source based on URL.

        This is important because:
        1. Iterative research may return the same articles across iterations
        2. Wikipedia often returns the same article for similar queries
        3. Duplicates waste context and may bias LLM analysis
        """
        deduped = {}
        for source, results in results_by_source.items():
            seen_urls = set()
            unique_results = []
            for result in results:
                # Use URL as primary dedup key, fall back to title
                key = result.url if result.url else result.title
                if key not in seen_urls:
                    seen_urls.add(key)
                    unique_results.append(result)
            deduped[source] = unique_results

            # Log if significant deduplication occurred
            if len(results) != len(unique_results):
                logger.info(f"Deduplicated {source}: {len(results)} -> {len(unique_results)} results")

        return deduped

    async def _generate_queries(
        self,
        question_title: str,
        question_text: str,
        options: list[str] | None = None,
    ) -> list[str]:
        """Generate search queries using an LLM."""
        num_queries = self.config.get("research", {}).get("queries_per_question", 5)

        description_text = question_text[:1000] if question_text else "(No description provided)"

        # Build options context for multiple choice questions
        options_context = ""
        if options:
            options_str = "\n".join(f"- {opt}" for opt in options)
            options_context = f"""
OPTIONS/CHOICES (IMPORTANT - search for information about EACH of these):
{options_str}

"""

        prompt = f"""Generate {num_queries} diverse search queries to research this forecasting question.

Question: {question_title}

Description: {description_text}
{options_context}
Generate queries that will help find:
1. Historical base rates and precedents
2. Recent news and developments
3. Expert opinions and analysis
4. Statistical data and trends
5. Counterarguments and alternative perspectives
{"6. Specific information about EACH option/choice listed above" if options else ""}

IMPORTANT: {"Include queries that specifically search for the key entities/names in the options (e.g., artist names, album names, team names, candidate names)." if options else ""}

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

    # -------------------------------------------------------------------------
    # AskNews Methods (using new AskNewsSearcher)
    # -------------------------------------------------------------------------

    async def _search_asknews(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search news using AskNews with dual strategy (latest + historical).

        Uses the new AskNewsSearcher which mirrors Metaculus template functionality.
        Returns formatted news that includes both recent and historical articles.
        """
        if not self._asknews_searcher:
            logger.warning("AskNews searcher not initialized")
            return ("asknews", [])

        try:
            # Get formatted news (dual strategy: latest + historical)
            formatted_news = await self._asknews_searcher.get_formatted_news_async(query)

            # Store the formatted news for later synthesis
            # We return an empty list of SearchResult since the formatted output
            # is more useful than individual results for this approach
            return ("asknews", [SearchResult(
                title="AskNews Research",
                url="",
                snippet=formatted_news,
                source="asknews",
                published_date=None,
                full_content=formatted_news,
            )])

        except Exception as e:
            logger.error(f"AskNews search failed: {e}")
            return ("asknews", [])

    async def _search_asknews_wiki(self, query: str) -> tuple[str, list[SearchResult]]:
        """Search Wikipedia using AskNews SDK."""
        if not self._asknews_searcher:
            logger.warning("AskNews searcher not initialized")
            return ("asknews_wiki", [])

        try:
            formatted_wiki = await self._asknews_searcher.search_wiki(query)

            return ("asknews_wiki", [SearchResult(
                title="Wikipedia Research",
                url="",
                snippet=formatted_wiki[:500],
                source="asknews_wiki",
                published_date=None,
                full_content=formatted_wiki,
            )])

        except Exception as e:
            logger.error(f"AskNews Wiki search failed: {e}")
            return ("asknews_wiki", [])

    async def get_deep_research(self, query: str, preset: str | None = None) -> Optional[str]:
        """Get deep research using AskNews get_deep_news endpoint.

        This is the most powerful research method, combining multiple sources
        with AI synthesis.

        Args:
            query: Research query/question
            preset: Optional preset to use:
                - "asknews/news-summaries" - Dual strategy news search
                - "asknews/deep-research/low-depth" - Light deep research
                - "asknews/deep-research/medium-depth" - Medium depth
                - "asknews/deep-research/high-depth" - Maximum depth

        Returns:
            Formatted research text or None if unavailable
        """
        if not self._asknews_searcher:
            logger.warning("AskNews searcher not initialized")
            return None

        try:
            # Get preset from config if not specified
            if preset is None:
                asknews_config = self._get_asknews_config()
                preset = asknews_config.get("research_preset", "asknews/deep-research/low-depth")

            return await self._asknews_searcher.call_preconfigured_version(preset, query)

        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            return None

    async def get_formatted_news(self, query: str) -> Optional[str]:
        """Get formatted news using dual search strategy.

        Convenience method that returns just the formatted news string.
        """
        if not self._asknews_searcher:
            logger.warning("AskNews searcher not initialized")
            return None

        try:
            return await self._asknews_searcher.get_formatted_news_async(query)
        except Exception as e:
            logger.error(f"Formatted news search failed: {e}")
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

        # Deep research (from AskNews get_deep_news) - highest priority
        if results.deep_research:
            lines.append("## Deep Research (AskNews)")
            lines.append("")
            lines.append(results.deep_research)
            lines.append("")

        # Formatted news (from AskNews dual strategy)
        if results.formatted_news:
            lines.append("## News Research (AskNews)")
            lines.append("")
            lines.append(results.formatted_news)
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

        # AskNews results (individual articles if not using formatted_news)
        if "asknews" in results.results_by_source and not results.formatted_news:
            lines.append("## News Articles (AskNews)")
            lines.append("")
            for result in results.results_by_source["asknews"]:
                # If full_content is the formatted news, just include it directly
                if result.full_content and result.title == "AskNews Research":
                    lines.append(result.full_content)
                else:
                    date_str = f" ({result.published_date})" if result.published_date else ""
                    lines.append(f"### [{result.title}]({result.url}){date_str}")
                    lines.append(f"> {result.snippet}")
                    if result.full_content:
                        lines.append("")
                        lines.append("**Full Article:**")
                        lines.append(result.full_content[:3000])
                lines.append("")

        # AskNews Wikipedia results
        if "asknews_wiki" in results.results_by_source:
            lines.append("## Wikipedia (AskNews)")
            lines.append("")
            for result in results.results_by_source["asknews_wiki"]:
                if result.full_content and result.title == "Wikipedia Research":
                    lines.append(result.full_content)
                else:
                    lines.append(f"### {result.title}")
                    if result.full_content:
                        lines.append(result.full_content[:4000])
                    else:
                        lines.append(result.snippet)
                lines.append("")

        # Claude web search results
        if "claude_web_search" in results.results_by_source:
            lines.append("## Claude Web Search Results")
            lines.append("")
            for result in results.results_by_source["claude_web_search"]:
                lines.append(result.snippet)
                lines.append("")

        return "\n".join(lines)
