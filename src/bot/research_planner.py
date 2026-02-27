"""
Iterative Research Planner

Replaces the legacy 2-step query generation (independent historical + current) with
a unified plan-execute-reflect loop:

  Phase 0: PRE-RESEARCH  — Scrape question URLs to build seed context
  Phase 1: RESEARCH PLAN — Single LLM call generates 5-10 tagged queries
  Phase 2: EXECUTE        — Run all queries via SearchPipeline
  Phase 3: REFLECT        — Evaluate coverage, generate gap-fill queries if needed
  Phase 4: ASSEMBLE       — Partition results into historical_context + current_context

Key improvements over legacy:
- All queries planned in one pass (prevents overlap between historical/current)
- Seed context from question URLs informs query planning
- Coverage dimensions explicitly enumerated in prompt
- Reflection step identifies and fills gaps
"""

import asyncio
import logging
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from ..utils.llm import LLMClient, get_cost_tracker
from .handler_mixin import ForecasterMixin
from .prompts import RESEARCH_PLAN_PROMPT, RESEARCH_REFLECT_PROMPT
from .search import AgenticSearchResult, GoogleScrapeResult, QuestionDetails, SearchPipeline

logger = logging.getLogger(__name__)


# =============================================================================
# Data structures
# =============================================================================


@dataclass
class ResearchQuery:
    """A single search query with routing metadata."""

    query: str  # The search text
    tool: str  # "Google", "Google News", "Agent", "AskNews", "FRED", "yFinance", "Google Trends"
    temporal_role: str  # "historical" or "current"
    intent: str  # What information need this serves
    phase: str = "plan"  # "plan" or "reflect" (which phase generated it)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryResult:
    """Result from executing a single ResearchQuery."""

    query: ResearchQuery
    formatted_output: str  # XML-tagged result string (same conventions as SearchPipeline)
    success: bool
    num_results: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchPlanResult:
    """Complete output of the iterative research planner."""

    historical_context: str
    current_context: str
    plan_analysis: str
    reflect_analysis: str | None
    queries_planned: list[ResearchQuery]
    gap_queries: list[ResearchQuery]
    seed_context: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_analysis": self.plan_analysis,
            "reflect_analysis": self.reflect_analysis,
            "queries_planned": [q.to_dict() for q in self.queries_planned],
            "gap_queries": [q.to_dict() for q in self.gap_queries],
            "seed_context_chars": len(self.seed_context),
            "historical_context_chars": len(self.historical_context),
            "current_context_chars": len(self.current_context),
            **self.metadata,
        }


# =============================================================================
# Iterative Research Planner
# =============================================================================


# Valid tools that the planner can dispatch to
VALID_TOOLS = {"Google", "Google News", "Agent", "AskNews", "FRED", "yFinance", "Google Trends"}

# Tool descriptions for the planner prompt, keyed by tool name.
# Google and Google News are always available; others are gated by config.
TOOL_DESCRIPTIONS = {
    "Google": (
        "Google: Keyword search. Write short queries (max 6 words) using terms likely "
        "to appear on relevant web pages. Best for reference pages, datasets, official reports."
    ),
    "Google News": (
        "Google News: Keyword search over recent news articles. Max 6 words. "
        "Best for breaking news, recent events, and current developments."
    ),
    "Agent": (
        "Agent: Your query will be processed by a reasoning model with web search capability. "
        "Write a detailed, multi-part query of up to 3 sentences. Best for complex questions "
        "needing synthesis across sources, base rate computation, or multi-factor analysis. "
        "IMPORTANT: Use exactly one Agent query, tagged [HISTORICAL], for base rate or "
        "reference class research. Do not use Agent for current events."
    ),
    "AskNews": (
        "AskNews: Semantic (meaning-based) news search. Write a descriptive 1-2 sentence "
        "natural language query focusing on the underlying topic, key actors, and context. "
        "Include relevant scope: geography, industry, time period. Avoid ambiguous acronyms. "
        "Best for finding conceptually related coverage even without exact keyword matches."
    ),
    "FRED": (
        'FRED: Federal Reserve Economic Data. Use a FRED series ID (e.g., "UNRATE", '
        '"CPIAUCSL") or a plain-language description (e.g., "US unemployment rate"). '
        "Returns historical data with computed statistics. Only use for economic/financial data."
    ),
    "yFinance": (
        'yFinance: Yahoo Finance ticker symbol (e.g., "AAPL", "^GSPC"). Returns price '
        "history, fundamentals, analyst targets, and options data. Only use for stocks, "
        "indices, or ETFs."
    ),
    "Google Trends": (
        'Google Trends: A search term (e.g., "hospital"). Returns 90-day search interest '
        "data with base rate analysis. Only use when the question specifically involves "
        "Google Trends data."
    ),
}

# Regex for parsing tagged queries from LLM output
# Matches: 1. [HISTORICAL] query text (Google) -- Intent: description
_TAGGED_QUERY_PATTERN = re.compile(
    r"\d+\.\s*\[(HISTORICAL|CURRENT)\]\s*(.+?)\s*"
    r"\((Google|Google News|Agent|AskNews|FRED|yFinance|Google Trends)\)"
    r"(?:\s*--\s*Intent:\s*(.+))?$",
    re.MULTILINE,
)


class IterativeResearchPlanner(ForecasterMixin):
    """
    Iterative research planner: plan → execute → reflect → gap-fill.

    Uses ForecasterMixin for model resolution, temperature config, and LLM calls.
    Requires self.config and self.llm to be set (provided by mixin contract).
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient,
        artifact_store: Any | None = None,
    ):
        self.config = config
        self.llm = llm_client
        self.artifact_store = artifact_store

    # -------------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------------

    async def run(
        self,
        question_details: QuestionDetails,
        question_type: str,
        question_params: dict,
        log: Callable[[str], Any] = print,
    ) -> ResearchPlanResult:
        """
        Run the full iterative research pipeline.

        Replaces Steps 1-2 of base_forecaster.forecast().

        Returns:
            ResearchPlanResult with historical_context and current_context
            ready for the forecaster ensemble.
        """
        cost_tracker = get_cost_tracker()
        start_cost = cost_tracker.total_cost
        pipeline_start = time.time()

        metadata: dict[str, Any] = {
            "phases": {},
            "total_queries_planned": 0,
            "total_queries_executed": 0,
            "total_gap_queries": 0,
        }

        # Phase 0: Pre-research
        log("\n--- Phase 0: Pre-research (scraping question URLs) ---")
        phase0_start = time.time()
        seed_context, seed_metadata = await self._gather_seed_context(question_details)
        metadata["phases"]["pre_research"] = {
            "duration_seconds": round(time.time() - phase0_start, 2),
            "seed_context_chars": len(seed_context),
            **seed_metadata,
        }
        if seed_context:
            log(f"  Seed context: {len(seed_context)} chars from question URLs")
        else:
            log("  No seed context from question URLs")

        # Build the cross-phase URL deduplication set from Phase 0 results.
        # All URLs attempted during Phase 0 are pre-claimed so Phase 2/3 Google
        # searches skip them automatically.
        seen_urls: set[str] = {u["url"] for u in seed_metadata.get("urls", [])}

        # Phase 1: Generate research plan
        log("\n--- Phase 1: Generating research plan ---")
        phase1_start = time.time()
        phase1_cost_start = cost_tracker.total_cost
        plan_analysis, planned_queries = await self._generate_plan(
            question_details, question_type, question_params, seed_context
        )
        metadata["phases"]["plan"] = {
            "duration_seconds": round(time.time() - phase1_start, 2),
            "cost": round(cost_tracker.total_cost - phase1_cost_start, 4),
            "num_queries": len(planned_queries),
        }
        metadata["total_queries_planned"] = len(planned_queries)
        log(f"  Generated {len(planned_queries)} queries")
        for q in planned_queries:
            log(f"    [{q.temporal_role.upper()}] {q.query[:60]}... ({q.tool})")

        # Phase 2: Execute all planned queries
        log("\n--- Phase 2: Executing planned queries ---")
        phase2_start = time.time()
        phase2_cost_start = cost_tracker.total_cost
        query_results = await self._execute_queries(planned_queries, question_details, seen_urls)
        successful = sum(1 for r in query_results if r.success)
        metadata["phases"]["execute"] = {
            "duration_seconds": round(time.time() - phase2_start, 2),
            "cost": round(cost_tracker.total_cost - phase2_cost_start, 4),
            "queries_executed": len(query_results),
            "queries_successful": successful,
        }
        metadata["total_queries_executed"] = len(query_results)
        log(f"  Executed {len(query_results)} queries ({successful} successful)")

        # Phase 3: Reflect and gap-fill (if enabled)
        gap_queries: list[ResearchQuery] = []
        reflect_analysis: str | None = None

        if self._is_reflection_enabled():
            log("\n--- Phase 3: Reflecting on coverage ---")
            phase3_start = time.time()
            phase3_cost_start = cost_tracker.total_cost
            reflect_analysis, gap_queries = await self._reflect_and_gap_fill(
                question_details, question_type, question_params, query_results
            )
            metadata["phases"]["reflect"] = {
                "duration_seconds": round(time.time() - phase3_start, 2),
                "cost": round(cost_tracker.total_cost - phase3_cost_start, 4),
                "gaps_found": len(gap_queries) > 0,
                "gap_queries": len(gap_queries),
            }
            metadata["total_gap_queries"] = len(gap_queries)

            if gap_queries:
                log(f"  Found gaps, executing {len(gap_queries)} gap-fill queries")
                gap_results = await self._execute_queries(gap_queries, question_details, seen_urls)
                query_results.extend(gap_results)
                gap_successful = sum(1 for r in gap_results if r.success)
                log(f"  Gap-fill: {gap_successful}/{len(gap_results)} successful")
            else:
                log("  Coverage sufficient, no gap-fill needed")
        else:
            log("\n--- Phase 3: Reflection disabled, skipping ---")

        # Phase 4: Assemble contexts
        log("\n--- Phase 4: Assembling contexts ---")
        historical_context, current_context = self._assemble_contexts(
            seed_context, query_results, question_params
        )
        metadata["phases"]["assemble"] = {
            "historical_context_chars": len(historical_context),
            "current_context_chars": len(current_context),
        }
        log(f"  Historical context: {len(historical_context)} chars")
        log(f"  Current context: {len(current_context)} chars")

        # Final metadata
        metadata["total_cost"] = round(cost_tracker.total_cost - start_cost, 4)
        metadata["total_duration_seconds"] = round(time.time() - pipeline_start, 2)

        # Build per-query details for tool_usage tracking
        metadata["query_details"] = [
            {
                "query": r.query.query,
                "tool": r.query.tool,
                "temporal_role": r.query.temporal_role,
                "intent": r.query.intent,
                "phase": r.query.phase,
                "success": r.success,
                "num_results": r.num_results,
                "error": r.error,
            }
            for r in query_results
        ]

        result = ResearchPlanResult(
            historical_context=historical_context,
            current_context=current_context,
            plan_analysis=plan_analysis,
            reflect_analysis=reflect_analysis,
            queries_planned=planned_queries,
            gap_queries=gap_queries,
            seed_context=seed_context,
            metadata=metadata,
        )

        # Save artifacts
        if self.artifact_store:
            self.artifact_store.save_search_results("research_plan", result.to_dict())

        return result

    # -------------------------------------------------------------------------
    # Phase 0: Pre-research
    # -------------------------------------------------------------------------

    async def _gather_seed_context(
        self,
        question_details: QuestionDetails,
    ) -> tuple[str, dict[str, Any]]:
        """
        Scrape URLs found in question text to build seed context.

        Runs BEFORE query generation so the planner can avoid redundant queries
        and build on what's already available from resolution sources.
        """
        async with SearchPipeline(self.config, self.llm) as search:
            seed_context, seed_metadata = await search.scrape_question_urls(question_details)

        # Save seed context artifact
        if self.artifact_store and seed_context:
            self.artifact_store.save_search_results("question_urls", {"context": seed_context})

        return seed_context, seed_metadata

    # -------------------------------------------------------------------------
    # Phase 1: Generate research plan
    # -------------------------------------------------------------------------

    async def _generate_plan(
        self,
        question_details: QuestionDetails,
        question_type: str,
        question_params: dict,
        seed_context: str,
    ) -> tuple[str, list[ResearchQuery]]:
        """
        Single LLM call to generate a unified research plan.

        Returns:
            Tuple of (analysis_text, list_of_research_queries)
        """
        # Build type-specific fields
        type_specific = self._build_type_specific_fields(question_type, question_params)

        # Compute days to resolution
        days_to_resolution = self._compute_days_to_resolution(question_params)

        # Get stock return context if available
        stock_return_context = question_params.get("stock_return_context", "")

        # Build seed context section
        seed_section = seed_context if seed_context else "No pre-research context available."

        # Build stock return section
        stock_section = stock_return_context if stock_return_context else ""

        # Get planner config
        planner_config = self.config.get("research", {}).get("planner", {})
        max_queries = planner_config.get("max_plan_queries", 10)

        # Build available tools section based on enabled config flags
        available_tools = self._build_available_tools()

        # Format prompt
        prompt = RESEARCH_PLAN_PROMPT.format(
            title=question_params.get("question_title", ""),
            question_type=question_type,
            background=question_params.get("background_info", "")
            or question_params.get("question_text", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            today=question_params.get("today", ""),
            days_to_resolution=days_to_resolution,
            type_specific=type_specific,
            seed_context=seed_section,
            stock_return_context=stock_section,
            max_queries=max_queries,
            available_tools=available_tools,
        )

        # Call LLM
        model = self._resolve_model("query_generator", "openrouter/openai/o3")
        temperature = self._get_temperature("research_planning")
        response = await self._call_model(model, prompt, temperature=temperature)

        # Save artifacts
        if self.artifact_store:
            self.artifact_store.save_query_generation("plan", prompt, response)

        # Parse queries
        analysis = self._extract_analysis(response)
        queries = self._parse_tagged_queries(response, phase="plan")

        if not queries:
            logger.warning(
                "Tagged query parser found 0 matches, falling back to untagged parser. "
                "Response snippet: %s",
                response[:300],
            )
            queries = self._parse_untagged_queries_fallback(response)

        return analysis, queries

    # -------------------------------------------------------------------------
    # Phase 2: Execute queries
    # -------------------------------------------------------------------------

    async def _execute_queries(
        self,
        queries: list[ResearchQuery],
        question_details: QuestionDetails,
        seen_urls: set[str] | None = None,
    ) -> list[QueryResult]:
        """
        Execute a list of research queries via SearchPipeline.

        Dispatches each query to the appropriate search tool and runs all
        queries concurrently.

        Args:
            queries: Research queries to execute.
            question_details: Question context for summarization.
            seen_urls: Shared set of already-processed URLs for cross-phase
                deduplication. Updated in place as new URLs are claimed.
        """
        if not queries:
            return []

        async with SearchPipeline(self.config, self.llm) as search:
            # Build async tasks
            tasks = []
            task_queries = []

            for rq in queries:
                task = self._build_search_task(search, rq, question_details, seen_urls)
                if task is not None:
                    tasks.append(task)
                    task_queries.append(rq)

            if not tasks:
                return []

            # Execute all tasks concurrently
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        query_results = []
        for rq, raw in zip(task_queries, raw_results, strict=True):
            query_results.append(self._process_search_result(rq, raw))

        return query_results

    def _build_search_task(
        self,
        search: SearchPipeline,
        rq: ResearchQuery,
        question_details: QuestionDetails,
        seen_urls: set[str] | None = None,
    ) -> Any | None:
        """Build an async task for a single query dispatch."""
        tool = rq.tool
        query = rq.query
        research_config = self.config.get("research", {})

        if tool in ("Google", "Google News"):
            return search._google_search_and_scrape(
                query=query,
                is_news=(tool == "Google News"),
                question_details=question_details,
                date_before=question_details.resolution_date,
                seen_urls=seen_urls,
            )
        elif tool == "Agent":
            if not research_config.get("agentic_search_enabled", True):
                logger.info(f"Agentic search disabled, skipping: {query[:50]}")
                return None
            agentic_context = (
                f"Question: {question_details.title}\n\n"
                f"Description:\n{question_details.description}\n\n"
                f"Resolution criteria:\n{question_details.resolution_criteria}"
            )
            if question_details.stock_return_context:
                agentic_context += f"\n\n{question_details.stock_return_context}"
            return search._agentic_search(query, context=agentic_context)
        elif tool == "AskNews":
            if not research_config.get("asknews_enabled", True):
                logger.info(f"AskNews disabled, skipping: {query[:50]}")
                return None
            return search._call_asknews(
                news_query=query,
                deep_research_query=query,
            )
        elif tool == "FRED":
            if not research_config.get("fred_enabled", True):
                logger.info(f"FRED disabled, skipping: {query[:50]}")
                return None
            return search._fred_search(query)
        elif tool == "yFinance":
            if not research_config.get("yfinance_enabled", True):
                logger.info(f"yFinance disabled, skipping: {query[:50]}")
                return None
            return search._yfinance_search(query)
        elif tool == "Google Trends":
            if not research_config.get("google_trends_enabled", True):
                logger.info(f"Google Trends disabled, skipping: {query[:50]}")
                return None
            return search._google_trends_search(query, question_details=question_details)
        else:
            logger.warning(f"Unknown tool '{tool}' for query: {query[:50]}")
            return None

    def _process_search_result(
        self,
        rq: ResearchQuery,
        raw: Any,
    ) -> QueryResult:
        """Process a raw search result into a QueryResult with formatted output."""
        if isinstance(raw, Exception):
            logger.error(f"Search error for '{rq.query[:50]}' ({rq.tool}): {raw}")
            error_output = self._format_error_output(rq, raw)
            return QueryResult(
                query=rq,
                formatted_output=error_output,
                success=False,
                error=str(raw),
            )

        tool = rq.tool
        query = rq.query

        if tool in ("Google", "Google News"):
            scrape_result: GoogleScrapeResult = raw
            num_results = scrape_result.formatted_output.count("<Summary")
            return QueryResult(
                query=rq,
                formatted_output=scrape_result.formatted_output,
                success=True,
                num_results=num_results,
                metadata={"url_results": scrape_result.url_results},
            )
        elif tool == "Agent":
            agentic_result: AgenticSearchResult = raw
            if agentic_result.error:
                output = (
                    f"\n<Agent_report>\nQuery: {query}\n"
                    f"Error: {agentic_result.error}\n</Agent_report>\n"
                )
                return QueryResult(
                    query=rq,
                    formatted_output=output,
                    success=False,
                    error=agentic_result.error,
                    metadata={
                        "steps_taken": agentic_result.steps_taken,
                        "queries_executed": agentic_result.queries_executed,
                    },
                )
            output = f"\n<Agent_report>\nQuery: {query}\n{agentic_result.analysis}</Agent_report>\n"
            num_results = 1 if len(agentic_result.analysis) > 500 else 0
            return QueryResult(
                query=rq,
                formatted_output=output,
                success=True,
                num_results=num_results,
                metadata={
                    "steps_taken": agentic_result.steps_taken,
                    "queries_executed": agentic_result.queries_executed,
                },
            )
        elif tool == "AskNews":
            output = f"\n<Asknews_articles>\nQuery: {query}\n{raw}</Asknews_articles>\n"
            num_results = raw.count("**") // 2
            return QueryResult(
                query=rq,
                formatted_output=output,
                success=True,
                num_results=num_results,
            )
        elif tool in ("Google Trends", "FRED", "yFinance"):
            # These tools return pre-formatted XML strings
            has_error = "Error" in raw[:100] if raw else True
            return QueryResult(
                query=rq,
                formatted_output=f"\n{raw}\n" if raw else "",
                success=not has_error,
                num_results=0 if has_error else 1,
            )
        else:
            return QueryResult(
                query=rq,
                formatted_output=raw if isinstance(raw, str) else str(raw),
                success=True,
                num_results=1,
            )

    def _format_error_output(self, rq: ResearchQuery, error: Exception) -> str:
        """Format an error into the appropriate XML tag for the tool."""
        query = rq.query
        tool = rq.tool
        err_str = str(error)

        if tool == "AskNews":
            return f"\n<Asknews_articles>\nQuery: {query}\nError: {err_str}\n</Asknews_articles>\n"
        elif tool == "Agent":
            return f"\n<Agent_report>\nQuery: {query}\nError: {err_str}\n</Agent_report>\n"
        elif tool == "Google Trends":
            return f'<GoogleTrendsData term="{query}">\nError: {err_str}\n</GoogleTrendsData>\n'
        elif tool == "FRED":
            return f'<FREDData query="{query}">\nError: {err_str}\n</FREDData>\n'
        elif tool == "yFinance":
            return f'<YFinanceData query="{query}">\nError: {err_str}\n</YFinanceData>\n'
        else:
            return f'\n<Summary query="{query}">\nError: {err_str}\n</Summary>\n'

    # -------------------------------------------------------------------------
    # Phase 3: Reflect and gap-fill
    # -------------------------------------------------------------------------

    async def _reflect_and_gap_fill(
        self,
        question_details: QuestionDetails,
        question_type: str,
        question_params: dict,
        query_results: list[QueryResult],
    ) -> tuple[str, list[ResearchQuery]]:
        """
        Evaluate research coverage and generate gap-fill queries if needed.

        Returns:
            Tuple of (analysis_text, gap_fill_queries)
        """
        # Build results summary (truncated to keep context manageable)
        results_summary = self._build_results_summary(query_results)

        days_to_resolution = self._compute_days_to_resolution(question_params)

        # Get planner config
        planner_config = self.config.get("research", {}).get("planner", {})
        max_gap_queries = planner_config.get("max_gap_queries", 3)

        prompt = RESEARCH_REFLECT_PROMPT.format(
            title=question_params.get("question_title", ""),
            question_type=question_type,
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            days_to_resolution=days_to_resolution,
            results_summary=results_summary,
            max_gap_queries=max_gap_queries,
        )

        model = self._resolve_model("query_generator", "openrouter/openai/o3")
        temperature = self._get_temperature("research_reflection")
        response = await self._call_model(model, prompt, temperature=temperature)

        # Save artifacts
        if self.artifact_store:
            self.artifact_store.save_query_generation("reflect", prompt, response)

        analysis = self._extract_analysis(response)

        # Check if coverage is sufficient
        if re.search(r"Coverage:\s*SUFFICIENT", response, re.IGNORECASE):
            return analysis, []

        # Parse gap-fill queries
        gap_queries = self._parse_tagged_queries(response, phase="reflect")

        # Cap at max
        if len(gap_queries) > max_gap_queries:
            gap_queries = gap_queries[:max_gap_queries]

        return analysis, gap_queries

    def _build_results_summary(
        self,
        query_results: list[QueryResult],
        max_chars_per_result: int = 500,
    ) -> str:
        """Build a truncated summary of search results for the reflection prompt."""
        parts = []
        for r in query_results:
            status = "SUCCESS" if r.success else f"FAILED ({r.error})"
            truncated = r.formatted_output[:max_chars_per_result]
            if len(r.formatted_output) > max_chars_per_result:
                truncated += "... [truncated]"
            parts.append(
                f"[{r.query.temporal_role.upper()}] {r.query.query} ({r.query.tool}) — {status}\n"
                f"{truncated}\n"
            )
        return "\n---\n".join(parts)

    # -------------------------------------------------------------------------
    # Phase 4: Context assembly
    # -------------------------------------------------------------------------

    def _assemble_contexts(
        self,
        seed_context: str,
        query_results: list[QueryResult],
        question_params: dict,
    ) -> tuple[str, str]:
        """
        Partition results by temporal role into historical_context and current_context.

        Matches the interface expected by base_forecaster Steps 3-7.
        """
        historical_parts: list[str] = []
        current_parts: list[str] = []

        for r in query_results:
            if not r.formatted_output:
                continue
            if r.query.temporal_role == "historical":
                historical_parts.append(r.formatted_output)
            else:
                current_parts.append(r.formatted_output)

        historical_context = "\n".join(historical_parts)
        current_context = "\n".join(current_parts)

        # Prepend seed context to historical (resolution sources first)
        if seed_context:
            historical_context = seed_context + "\n" + historical_context

        # Prepend stock return distribution to both contexts
        stock_return_context = question_params.get("stock_return_context", "")
        if stock_return_context:
            historical_context = stock_return_context + "\n" + historical_context
            current_context = stock_return_context + "\n" + current_context

        return historical_context, current_context

    # -------------------------------------------------------------------------
    # Parsing helpers
    # -------------------------------------------------------------------------

    def _parse_tagged_queries(
        self,
        response: str,
        phase: str = "plan",
    ) -> list[ResearchQuery]:
        """
        Parse tagged queries from LLM output.

        Expected format:
            1. [HISTORICAL] query text (Google) -- Intent: description
        """
        # Extract only the queries section (after "Search queries:")
        queries_block = re.search(r"Search queries:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        if not queries_block:
            return []

        text = queries_block.group(1)
        matches = _TAGGED_QUERY_PATTERN.findall(text)

        queries = []
        for match in matches:
            temporal_role, query, tool, intent = match
            query = query.strip().strip('"').strip("'")
            if not query:
                continue
            if tool not in VALID_TOOLS:
                logger.warning(f"Skipping query with unknown tool '{tool}': {query[:50]}")
                continue

            queries.append(
                ResearchQuery(
                    query=query,
                    tool=tool,
                    temporal_role=temporal_role.lower(),
                    intent=intent.strip() if intent else "",
                    phase=phase,
                )
            )

        if queries:
            hist_count = sum(1 for q in queries if q.temporal_role == "historical")
            curr_count = sum(1 for q in queries if q.temporal_role == "current")
            logger.info(
                f"Parsed {len(queries)} tagged queries "
                f"({hist_count} historical, {curr_count} current) from {phase} phase"
            )
        else:
            logger.warning(f"No tagged queries parsed from {phase} phase response")

        return queries

    def _parse_untagged_queries_fallback(
        self,
        response: str,
    ) -> list[ResearchQuery]:
        """
        Fallback parser for queries without [HISTORICAL]/[CURRENT] tags.

        Uses heuristics to assign temporal roles.
        """
        queries_block = re.search(r"Search queries:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        if not queries_block:
            return []

        text = queries_block.group(1)

        # Try to match untagged format: 1. query (Tool)
        pattern = re.compile(
            r"\d+\.\s*(.+?)\s*"
            r"\((Google|Google News|Agent|AskNews|FRED|yFinance|Google Trends)\)"
            r"(?:\s*--\s*Intent:\s*(.+))?$",
            re.MULTILINE,
        )
        matches = pattern.findall(text)

        queries = []
        for i, match in enumerate(matches):
            query_text, tool, intent = match
            query_text = query_text.strip().strip('"').strip("'")
            # Remove any [HISTORICAL] or [CURRENT] tags that weren't caught
            query_text = re.sub(r"^\[(HISTORICAL|CURRENT)\]\s*", "", query_text)
            if not query_text or tool not in VALID_TOOLS:
                continue

            # Heuristic: first ~60% historical, rest current
            role = "historical" if i < len(matches) * 0.6 else "current"

            # Override based on tool: AskNews and Google News lean current
            if tool == "AskNews":
                role = "current"

            queries.append(
                ResearchQuery(
                    query=query_text,
                    tool=tool,
                    temporal_role=role,
                    intent=intent.strip() if intent else "",
                    phase="plan",
                )
            )

        if queries:
            logger.info(f"Fallback parser found {len(queries)} untagged queries")
        return queries

    def _extract_analysis(self, response: str) -> str:
        """Extract the Analysis section from an LLM response."""
        match = re.search(
            r"Analysis:\s*(.*?)(?=Search queries:|Coverage:|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        return match.group(1).strip() if match else ""

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _build_available_tools(self) -> str:
        """Build the AVAILABLE TOOLS prompt section based on enabled config flags."""
        research_config = self.config.get("research", {})

        # Google and Google News are always available
        enabled = ["Google", "Google News"]

        # Conditionally add tools based on config
        if research_config.get("agentic_search_enabled", True):
            enabled.append("Agent")
        if research_config.get("asknews_enabled", True):
            enabled.append("AskNews")
        if research_config.get("fred_enabled", True):
            enabled.append("FRED")
        if research_config.get("yfinance_enabled", True):
            enabled.append("yFinance")
        if research_config.get("google_trends_enabled", True):
            enabled.append("Google Trends")

        return "\n".join(f"- {TOOL_DESCRIPTIONS[t]}" for t in enabled)

    def _build_type_specific_fields(
        self,
        question_type: str,
        question_params: dict,
    ) -> str:
        """Build type-specific prompt section."""
        parts = []
        if question_type == "multiple_choice":
            options = question_params.get("options", "")
            if options:
                parts.append(f"Options: {options}")
        elif question_type == "numeric":
            units = question_params.get("units", "")
            bounds_info = question_params.get("bounds_info", "")
            if units:
                parts.append(f"Units: {units}")
            if bounds_info:
                parts.append(f"Bounds: {bounds_info}")
        return "\n".join(parts) if parts else ""

    def _compute_days_to_resolution(self, question_params: dict) -> str:
        """Compute days from today to resolution date."""
        today_str = question_params.get("today", "")
        resolve_str = question_params.get("scheduled_resolve_time", "")
        if not today_str or not resolve_str:
            return "unknown"
        try:
            today = datetime.strptime(today_str, "%Y-%m-%d")
            # Handle ISO format with possible timezone info
            resolve_clean = resolve_str.split("T")[0] if "T" in resolve_str else resolve_str
            resolve = datetime.strptime(resolve_clean, "%Y-%m-%d")
            days = (resolve - today).days
            return str(max(0, days))
        except (ValueError, TypeError):
            return "unknown"

    def _is_reflection_enabled(self) -> bool:
        """Check if the reflection phase is enabled in config."""
        planner_config = self.config.get("research", {}).get("planner", {})
        return planner_config.get("reflection_enabled", True)
