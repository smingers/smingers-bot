"""
Search Pipeline

Key differences from previous approach:
1. Forecasters generate search queries directly in their responses (note: this does not appear to be true)
2. Queries are tagged with source (Google, Google News, Google Trends, FRED, yFinance, Agent)
3. AskNews is called programmatically for current search (not LLM-controlled)
4. Agentic search uses GPT to iteratively research
5. Articles are summarized with question context
"""

import asyncio
import logging
import math
import os
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import dateparser
import httpx
from rank_bm25 import BM25Plus

from ..utils.llm import LLMClient, get_cost_tracker
from .content_extractor import ConcurrentContentExtractor
from .prompts import CONTINUATION_SEARCH_PROMPT, INITIAL_SEARCH_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class QuestionDetails:
    """Question details for context-aware article summarization."""

    title: str
    resolution_criteria: str
    fine_print: str
    description: str
    resolution_date: str | None = None
    community_prediction_context: str | None = None  # Scraped CP data for meta-questions
    stock_return_context: str | None = None  # Programmatic stock return distribution


@dataclass
class SearchResult:
    """A search result with content."""

    url: str
    title: str
    content: str
    source: str  # google, google_news, asknews, agent
    date: str | None = None


@dataclass
class AgenticSearchStepData:
    """Data captured for a single step of agentic search."""

    step_number: int
    queries_executed: list[tuple[str, str]]  # (query, source) pairs
    search_results_raw: str  # Raw search results fed to LLM
    analysis_after_step: str  # Analysis produced after this step


@dataclass
class AgenticSearchResult:
    """
    Result from agentic search with full instrumentation.

    The `analysis` field contains the final output that gets passed to forecasters.
    The other fields provide visibility into the search process for debugging/analysis.
    """

    analysis: str  # Final analysis (this is what goes to forecasters)
    steps_taken: int
    queries_executed: list[str]  # All queries across all steps
    step_data: list[AgenticSearchStepData]  # Per-step details
    error: str | None = None


@dataclass
class GoogleScrapeResult:
    """Result from Google search + scrape with per-URL tracking."""

    formatted_output: str
    url_results: list[dict[str, Any]]  # Per-URL: url, domain, success, error, method, etc.


# Article summarization prompt template
ARTICLE_SUMMARY_PROMPT = """
You are an assistant to a superforecaster and your task involves high-quality information retrieval to help the forecaster make the most informed forecasts. Forecasting involves parsing through an immense trove of internet articles and web content. To make this easier for the forecaster, you read entire articles and extract the key pieces of the articles relevant to the question. The key pieces generally include:

1. Facts, statistics and other objective measurements described in the article
2. Opinions from reliable and named sources (e.g. if the article writes 'according to a 2023 poll by Gallup' or 'The 2025 presidential approval rating poll by Reuters' etc.)
3. Potentially useful opinions from less reliable/not-named sources (you explicitly document the less reliable origins of these opinions though)

Today, you're focusing on the question:

{title}

Resolution criteria:
{resolution_criteria}

Fine print:
{fine_print}

Background information:
{background}

Article to summarize:
{article}

Note: If the web content extraction is incomplete or you believe the quality of the extracted content isn't the best, feel free to add a disclaimer before your summary.

Please summarize only the article given, not injecting your own knowledge or providing a forecast. Aim to achieve a balance between a superficial summary and an overly verbose account.
"""


def _bm25_filter_content(content: str, query: str, max_chars: int = 8000) -> str:
    """Select the most relevant chunks of content using BM25 scoring.

    Splits content into paragraph-level chunks, scores each against the query,
    and greedily selects top-scoring chunks (in original document order) until
    the character budget is filled.

    Falls back to simple truncation when BM25 can't produce useful scores
    (e.g., no token overlap between query and content).
    """
    if not content or len(content) <= max_chars:
        return content

    # Split into chunks on paragraph boundaries
    raw_chunks = content.split("\n\n")
    chunks: list[tuple[int, str]] = []  # (original_index, text)
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Sub-split large chunks on single newlines
        if len(chunk) > 1000:
            sub_parts = chunk.split("\n")
            for sub in sub_parts:
                sub = sub.strip()
                if not sub:
                    continue
                # If a sub-chunk is still huge (no newlines to split on),
                # hard-truncate it so it doesn't blow the budget
                if len(sub) > max_chars:
                    sub = sub[:max_chars]
                chunks.append((len(chunks), sub))
        else:
            chunks.append((len(chunks), chunk))

    if not chunks:
        return content[:max_chars]

    # Tokenize
    tokenized_chunks = [c.lower().split() for _, c in chunks]
    tokenized_query = query.lower().split()

    if not tokenized_query:
        return content[:max_chars]

    # Score with BM25
    try:
        bm25 = BM25Plus(tokenized_chunks)
        scores = bm25.get_scores(tokenized_query)
    except (ValueError, ZeroDivisionError):
        return content[:max_chars]

    # Check if any scores are meaningful (non-zero)
    if max(scores) == 0:
        return content[:max_chars]

    # Rank chunks by score, select top ones within budget
    scored = sorted(
        zip(range(len(chunks)), scores, strict=True),
        key=lambda x: x[1],
        reverse=True,
    )

    selected_indices: list[int] = []
    total_chars = 0
    separator_len = 2  # "\n\n" between chunks
    for idx, _score in scored:
        chunk_len = len(chunks[idx][1])
        join_cost = separator_len if selected_indices else 0
        if total_chars + join_cost + chunk_len > max_chars:
            if not selected_indices:
                # Must select at least one chunk
                selected_indices.append(idx)
                total_chars += chunk_len
            continue  # Try smaller chunks that might fit
        selected_indices.append(idx)
        total_chars += join_cost + chunk_len

    # Re-sort by original document order
    selected_indices.sort()

    return "\n\n".join(chunks[i][1] for i in selected_indices)


class SearchPipeline:
    """
    Search pipeline that processes queries generated by forecasters.

    Supports multiple search sources:
    - Google (web search via Serper)
    - Google News (news search via Serper)
    - AskNews (news + deep research, called programmatically for current search)
    - Agent (agentic search with iterative GPT analysis)
    - Google Trends (historical trend data for search terms)
    - FRED (Federal Reserve Economic Data for economic indicators)
    - yFinance (stock/ETF price history, fundamentals, options data)
    """

    def __init__(self, config: dict, llm_client: LLMClient | None = None):
        """
        Initialize search pipeline.

        Args:
            config: Configuration dict with model settings
            llm_client: Optional LLMClient instance (creates one if not provided)
        """
        self.config = config
        if llm_client:
            self.llm = llm_client
        else:
            llm_timeout = config.get("llm", {}).get("timeout_seconds")
            self.llm = LLMClient(timeout_seconds=llm_timeout)
        self.http_client: httpx.AsyncClient | None = None

        # Temperature defaults per task type
        self._default_temperatures: dict[str, float] = {
            "article_summarization": 0.1,
            "agentic_search": 0.3,
        }

        # API keys
        self.serper_key = os.getenv("SERPER_API_KEY") or os.getenv("SERPER_KEY")
        self.asknews_client_id = os.getenv("ASKNEWS_CLIENT_ID")
        self.asknews_secret = os.getenv("ASKNEWS_CLIENT_SECRET") or os.getenv("ASKNEWS_SECRET")
        self.fred_api_key = os.getenv("FRED_API_KEY")
        self._fred_client = None  # Lazily initialized in _get_fred_client

        # Rate limiter for AskNews calls (free tier has concurrency limit)
        self._asknews_rate_limiter = asyncio.Semaphore(1)

    def _get_temperature(self, task: str) -> float:
        """Get configured temperature for a task type from llm.temperature config."""
        llm_config = self.config.get("llm", {})
        temp_config = llm_config.get("temperature", {})
        return float(temp_config.get(task, self._default_temperatures.get(task, 0.7)))

    async def __aenter__(self):
        self.http_client = httpx.AsyncClient(timeout=70.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    # -------------------------------------------------------------------------
    # Main entry point: process search queries from forecaster response
    # -------------------------------------------------------------------------

    async def execute_searches_from_response(
        self,
        response: str,
        search_id: str,
        question_details: QuestionDetails,
        include_asknews: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        Parse search queries from a response and execute them.

        Queries are expected in format:
        Search queries:
        1. "query text" (Google)
        2. "query text" (Google News)
        3. "query text" (Agent)

        Args:
            response: The response containing search queries (from query generation)
            search_id: Identifier for logging (e.g., "historical", "current")
            question_details: Question context for summarization
            include_asknews: If True, also call AskNews for current search

        Returns:
            Tuple of (formatted_results_string, metadata_dict)
        """
        cost_tracker = get_cost_tracker()
        start_cost = cost_tracker.total_cost

        metadata = {
            "search_id": search_id,
            "searched": False,
            "num_queries": 0,
            "queries": [],
            "tools_used": set(),
        }

        # Track costs by operation type
        self._current_summarization_cost = 0.0
        self._current_agentic_cost = 0.0
        try:
            # Extract the "Search queries:" block
            search_queries_block = re.search(
                r"(?:Search queries:)(.*)", response, re.DOTALL | re.IGNORECASE
            )
            if not search_queries_block:
                logger.info(f"Search[{search_id}]: No search queries block found")
                return "", metadata

            queries_text = search_queries_block.group(1).strip()

            # Parse queries with sources
            # Format: 1. "text" (Source) or 1. text (Source) or 1. text [Source]
            search_queries = re.findall(
                r'(?:\d+\.\s*)?(["\']?(.*?)["\']?)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED|yFinance)[\)\]]',
                queries_text,
            )

            # Fallback to unquoted queries
            if not search_queries:
                search_queries = re.findall(
                    r"(?:\d+\.\s*)?([^(\[\n]+)\s*[\(\[](Google|Google News|Google Trends|Agent|AskNews|FRED|yFinance)[\)\]]",
                    queries_text,
                )

            if not search_queries:
                logger.info(f"Search[{search_id}]: No valid search queries found:\n{queries_text}")
                return "", metadata

            logger.info(f"Search[{search_id}]: Processing {len(search_queries)} search queries")

            metadata["searched"] = True
            metadata["num_queries"] = len(search_queries)

            # Build tasks for each query
            tasks = []
            query_sources = []

            # Track LLM-generated AskNews query (used for news search + Deep Research)
            asknews_query: str | None = None

            for match in search_queries:
                if len(match) == 3:
                    _, raw_query, source = match
                else:
                    raw_query, source = match

                query = raw_query.strip().strip('"').strip("'")
                if not query:
                    continue

                logger.info(f"Search[{search_id}]: Query='{query}' Source={source}")

                # Track query and tool usage in metadata
                metadata["queries"].append({"query": query, "tool": source})
                metadata["tools_used"].add(source)

                if source in ("Google", "Google News"):
                    query_sources.append((query, source))
                    tasks.append(
                        self._google_search_and_scrape(
                            query=query,
                            is_news=(source == "Google News"),
                            question_details=question_details,
                            date_before=question_details.resolution_date,
                        )
                    )
                elif source == "Google Trends":
                    # Check if Google Trends is enabled in config
                    if not self.config.get("research", {}).get("google_trends_enabled", True):
                        logger.info(f"Search[{search_id}]: Google Trends disabled, skipping query")
                        continue
                    query_sources.append((query, source))
                    tasks.append(
                        self._google_trends_search(query, question_details=question_details)
                    )
                elif source == "FRED":
                    if not self.config.get("research", {}).get("fred_enabled", True):
                        logger.info(f"Search[{search_id}]: FRED disabled, skipping query")
                        continue
                    query_sources.append((query, source))
                    tasks.append(self._fred_search(query))
                elif source == "Agent":
                    query_sources.append((query, source))
                    # Build context string from question details for agentic search
                    agentic_context = (
                        f"Question: {question_details.title}\n\n"
                        f"Description:\n{question_details.description}\n\n"
                        f"Resolution criteria:\n{question_details.resolution_criteria}"
                    )
                    # For stock close price questions, include computed return
                    # distribution so the agentic agent can focus on catalysts/news
                    # rather than trying to compute statistics it can't
                    if question_details.stock_return_context:
                        agentic_context += f"\n\n{question_details.stock_return_context}"
                    tasks.append(self._agentic_search(query, context=agentic_context))
                elif source == "AskNews":
                    # Store the LLM-generated query for news search + Deep Research
                    # The actual AskNews call will be added below with include_asknews
                    asknews_query = query
                    logger.info(
                        f"Search[{search_id}]: Found AskNews query: {query[:50]}..."
                    )

            # Programmatically add AskNews for current search
            # Uses LLM-generated query for news search and Deep Research (falls back to title)
            if include_asknews:
                news_query = asknews_query or question_details.title
                if asknews_query:
                    logger.info(
                        f"Search[{search_id}]: Adding AskNews search with LLM-generated query: {asknews_query[:50]}..."
                    )
                else:
                    logger.info(
                        f"Search[{search_id}]: Adding AskNews search with question title (no LLM query found)"
                    )
                tasks.append(
                    self._call_asknews(
                        news_query=news_query,
                        deep_research_query=asknews_query,
                    )
                )
                query_sources.append((news_query, "AskNews"))
                # Track in metadata
                asknews_metadata = {"query": news_query, "tool": "AskNews"}
                metadata["queries"].append(asknews_metadata)
                metadata["tools_used"].add("AskNews")

            if not tasks:
                logger.info(f"Search[{search_id}]: No tasks generated")
                return "", metadata

            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Format outputs and count results
            formatted_results = ""
            for i, ((query, source), result) in enumerate(zip(query_sources, results, strict=True)):
                if isinstance(result, Exception):
                    logger.error(f"Search[{search_id}]: Error for '{query}' → {result}")
                    metadata["queries"][i]["success"] = False
                    metadata["queries"][i]["error"] = str(result)
                    metadata["queries"][i]["num_results"] = 0

                    if source == "AskNews":
                        formatted_results += f"\n<Asknews_articles>\nQuery: {query}\nError retrieving results: {result}\n</Asknews_articles>\n"
                    elif source == "Agent":
                        formatted_results += (
                            f"\n<Agent_report>\nQuery: {query}\nError: {result}\n</Agent_report>\n"
                        )
                    elif source == "Google Trends":
                        formatted_results += f'<GoogleTrendsData term="{query}">\nError: {result}\n</GoogleTrendsData>\n'
                    elif source == "FRED":
                        formatted_results += (
                            f'<FREDData query="{query}">\nError: {result}\n</FREDData>\n'
                        )
                    elif source == "yFinance":
                        formatted_results += (
                            f'<YFinanceData query="{query}">\nError: {result}\n</YFinanceData>\n'
                        )
                    else:
                        formatted_results += (
                            f'\n<Summary query="{query}">\nError: {result}\n</Summary>\n'
                        )
                else:
                    logger.info(f"Search[{search_id}]: Query '{query}' processed successfully")

                    # Count results by looking for tags in the result string
                    if source == "AskNews":
                        num_results = result.count("**") // 2  # AskNews articles have ** in titles
                        formatted_results += (
                            f"\n<Asknews_articles>\nQuery: {query}\n{result}</Asknews_articles>\n"
                        )
                    elif source == "Agent":
                        # Agent returns AgenticSearchResult with instrumentation
                        agentic_result: AgenticSearchResult = result
                        analysis = agentic_result.analysis

                        # Count as 1 if substantial content exists, 0 if error or empty
                        num_results = 1 if len(analysis) > 500 and not agentic_result.error else 0

                        # Format for prompt (same as before - just the analysis)
                        if agentic_result.error:
                            formatted_results += f"\n<Agent_report>\nQuery: {query}\nError: {agentic_result.error}\n</Agent_report>\n"
                        else:
                            formatted_results += (
                                f"\n<Agent_report>\nQuery: {query}\n{analysis}</Agent_report>\n"
                            )

                        # Store instrumentation data in metadata
                        metadata["queries"][i]["agentic_instrumentation"] = {
                            "steps_taken": agentic_result.steps_taken,
                            "queries_executed": agentic_result.queries_executed,
                            "step_data": [
                                {
                                    "step_number": sd.step_number,
                                    "queries_executed": sd.queries_executed,
                                    "search_results_chars": len(sd.search_results_raw),
                                    "analysis_chars": len(sd.analysis_after_step),
                                }
                                for sd in agentic_result.step_data
                            ],
                            "error": agentic_result.error,
                        }
                    elif source == "Google Trends":
                        # Google Trends returns 1 data block with statistics
                        num_results = 1 if "Error" not in result[:100] else 0
                        formatted_results += f"\n{result}\n"
                    elif source == "FRED":
                        num_results = 1 if "Error" not in result[:100] else 0
                        formatted_results += f"\n{result}\n"
                    elif source == "yFinance":
                        num_results = 1 if "Error" not in result[:100] else 0
                        formatted_results += f"\n{result}\n"
                    elif source in ("Google", "Google News"):
                        scrape_result: GoogleScrapeResult = result
                        num_results = scrape_result.formatted_output.count("<Summary")
                        formatted_results += scrape_result.formatted_output
                        # Attach per-URL scrape details to metadata
                        metadata["queries"][i]["url_results"] = scrape_result.url_results
                        metadata["queries"][i]["scrape_stats"] = {
                            "urls_returned": len(scrape_result.url_results),
                            "urls_extracted": sum(
                                1 for u in scrape_result.url_results if u["success"]
                            ),
                            "urls_failed": sum(
                                1 for u in scrape_result.url_results if not u["success"]
                            ),
                            "urls_summarized": num_results,
                        }
                    else:
                        num_results = result.count("<Summary")
                        formatted_results += result

                    metadata["queries"][i]["success"] = True
                    metadata["queries"][i]["num_results"] = num_results

            # Convert set to list for JSON serialization
            metadata["tools_used"] = list(metadata["tools_used"])

            # Track LLM costs by operation type
            metadata["llm_cost"] = round(cost_tracker.total_cost - start_cost, 4)
            metadata["llm_cost_summarization"] = round(self._current_summarization_cost, 4)
            metadata["llm_cost_agentic"] = round(self._current_agentic_cost, 4)

            return formatted_results, metadata

        except Exception as e:
            logger.error(f"Search[{search_id}]: Error processing search queries: {e}")
            traceback.print_exc()
            metadata["error"] = str(e)
            return (
                "Error processing some search queries. Partial results may be available.",
                metadata,
            )

    # -------------------------------------------------------------------------
    # Question URL Extraction + Scrape
    # -------------------------------------------------------------------------

    # Minimum word count for scraped content to be worth summarizing.
    # Lower than the 100-word threshold for regular Google results because
    # resolution source pages (EIA, FRED) often have sparse data tables.
    _MIN_QUESTION_URL_CONTENT_WORDS = 50

    # Domains to filter out (internal cross-references, not data sources)
    _FILTERED_DOMAINS = {
        "metaculus.com",
        "www.metaculus.com",
    }

    # Regex: markdown links [text](url)
    # Note: won't match URLs with nested parens (e.g., Wikipedia disambiguation pages).
    # This is acceptable since resolution sources are typically data APIs, not Wikipedia.
    _MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^\)]+)\)")

    # Regex: bare URLs not already inside markdown link parens
    _BARE_URL_RE = re.compile(r"(?<!\()(https?://[^\s\)>\]\"\,]+)")

    @staticmethod
    def extract_urls_from_question_text(question_details: QuestionDetails) -> list[str]:
        """
        Extract unique, scrapable URLs from question text fields.

        Handles both markdown-style [text](url) and bare URLs.
        Filters out Metaculus internal URLs and deduplicates.
        Prioritizes resolution_criteria URLs (listed first).

        Args:
            question_details: Question context containing text fields with URLs

        Returns:
            Ordered list of unique URLs, resolution_criteria first.
        """
        seen: set[str] = set()
        urls: list[str] = []

        # Process fields in priority order
        fields = [
            question_details.resolution_criteria,
            question_details.fine_print,
            question_details.description,
        ]

        for field_text in fields:
            if not field_text:
                continue

            # Clean escaped underscores from markdown (Metaculus sometimes has these)
            cleaned = field_text.replace("\\_", "_")

            # Extract markdown link URLs first
            for _, url in SearchPipeline._MARKDOWN_LINK_RE.findall(cleaned):
                normalized = url.rstrip(".,;:")
                domain = urlparse(normalized).netloc.lower()
                if domain not in SearchPipeline._FILTERED_DOMAINS and normalized not in seen:
                    seen.add(normalized)
                    urls.append(normalized)

            # Extract bare URLs (skip those already found in markdown links)
            for url in SearchPipeline._BARE_URL_RE.findall(cleaned):
                normalized = url.rstrip(".,;:")
                domain = urlparse(normalized).netloc.lower()
                if domain not in SearchPipeline._FILTERED_DOMAINS and normalized not in seen:
                    seen.add(normalized)
                    urls.append(normalized)

        return urls

    async def scrape_question_urls(
        self,
        question_details: QuestionDetails,
    ) -> tuple[str, dict[str, Any]]:
        """
        Extract URLs from question text fields, scrape, and summarize them.

        These are structural URLs from the question itself (resolution criteria,
        fine print, description) -- not from LLM-generated queries.

        Args:
            question_details: Question context containing text fields with URLs

        Returns:
            Tuple of (formatted_results_string, metadata_dict)
        """
        metadata: dict[str, Any] = {
            "search_id": "question_urls",
            "searched": False,
            "urls_found": 0,
            "urls_scraped": 0,
            "urls_summarized": 0,
            "urls": [],
            "tools_used": [],
        }

        # Check config
        if not self.config.get("research", {}).get("question_url_scraping_enabled", True):
            return "", metadata

        # Extract URLs
        urls = self.extract_urls_from_question_text(question_details)
        metadata["urls_found"] = len(urls)

        if not urls:
            return "", metadata

        metadata["searched"] = True
        metadata["tools_used"] = ["QuestionURLScrape"]

        # Cap at configured limit
        max_urls = self.config.get("research", {}).get("question_url_max_scrape", 5)
        urls = urls[:max_urls]

        logger.info(f"[question_urls] Found {len(urls)} URLs in question text fields")

        # Scrape URLs using existing infrastructure
        try:
            async with ConcurrentContentExtractor() as extractor:
                results = await extractor.extract_content(urls)
        except Exception as e:
            logger.error(f"[question_urls] Scraping failed: {e}")
            metadata["error"] = str(e)
            return "", metadata

        # Summarize successfully scraped content
        summarize_tasks = []
        valid_urls = []

        for url in urls:
            extraction = results.get(url, {})
            content = (extraction.get("content") or "").strip()

            url_meta: dict[str, Any] = {
                "url": url,
                "domain": extraction.get("domain", urlparse(url).netloc),
                "scraped": extraction.get("success", False),
                "method": extraction.get("method"),
                "status_code": extraction.get("status_code"),
            }

            if (
                extraction.get("success")
                and len(content.split()) >= self._MIN_QUESTION_URL_CONTENT_WORDS
            ):
                max_content = self.config.get("research", {}).get("max_content_length", 15000)
                truncated = _bm25_filter_content(
                    content, question_details.title, max_chars=max_content
                )
                summarize_tasks.append(self._summarize_article(truncated, question_details))
                valid_urls.append(url)
                url_meta["content_words"] = len(content.split())
                metadata["urls_scraped"] += 1
            else:
                url_meta["error"] = extraction.get("error", "Insufficient content")

            metadata["urls"].append(url_meta)

        if not summarize_tasks:
            logger.info("[question_urls] No scrapable content found in question URLs")
            return "", metadata

        # Run summarizations in parallel
        summaries = await asyncio.gather(*summarize_tasks, return_exceptions=True)

        # Format output with <QuestionSource> tag (distinct from <Summary> used by
        # Google search results, <Agent_report>, <FREDData>, <GoogleTrendsData>, etc.)
        # so forecasters can distinguish resolution-source data from search results.
        output = ""
        for url, summary in zip(valid_urls, summaries, strict=True):
            if isinstance(summary, Exception):
                logger.error(f"[question_urls] Summarization error for {url}: {summary}")
            else:
                output += f'\n<QuestionSource url="{url}">\n{summary}\n</QuestionSource>\n'
                metadata["urls_summarized"] += 1

        logger.info(
            f"[question_urls] Scraped {metadata['urls_scraped']}, "
            f"summarized {metadata['urls_summarized']} of {metadata['urls_found']} URLs"
        )

        return output, metadata

    # -------------------------------------------------------------------------
    # Google Search + Scrape
    # -------------------------------------------------------------------------

    async def _google_search(
        self,
        query: str,
        is_news: bool = False,
        date_before: str | None = None,
    ) -> list[str]:
        """
        Search Google via Serper API.

        Args:
            query: Search query
            is_news: Use Google News instead of web search
            date_before: Only include results before this date

        Returns:
            List of URLs
        """
        if not self.serper_key:
            logger.warning("SERPER_API_KEY not set, skipping Google search")
            return []

        # Clean query
        query = query.replace('"', "").replace("'", "").strip()
        logger.debug(f"[google_search] Query: '{query}' is_news={is_news}")

        search_type = "news" if is_news else "search"
        url = f"https://google.serper.dev/{search_type}"

        try:
            response = await self.http_client.post(
                url,
                headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                json={"q": query, "num": 20},
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("news" if is_news else "organic", [])
            logger.debug(f"[google_search] Found {len(items)} raw results")

            # Filter by date if specified
            filtered_items = []
            for item in items:
                if date_before:
                    item_date_str = item.get("date", "")
                    item_date = self._parse_date(item_date_str)
                    if item_date != "Unknown" and self._is_before_resolution_date(
                        date_before, item_date
                    ):
                        filtered_items.append(item)
                    # Skip items we can't validate
                else:
                    filtered_items.append(item)

                if len(filtered_items) >= 12:
                    break

            urls = [item["link"] for item in filtered_items]
            logger.info(f"[google_search] Returning {len(urls)} URLs")
            return urls

        except Exception as e:
            logger.error(f"[google_search] Error: {e}")
            return []

    async def _google_search_and_scrape(
        self,
        query: str,
        is_news: bool,
        question_details: QuestionDetails,
        date_before: str | None = None,
    ) -> GoogleScrapeResult:
        """
        Search Google and scrape/summarize results.

        Args:
            query: Search query
            is_news: Use Google News
            question_details: Question context for summarization
            date_before: Date filter

        Returns:
            GoogleScrapeResult with formatted output and per-URL scrape details
        """
        logger.debug(f"[google_search_and_scrape] query='{query}' is_news={is_news}")

        try:
            urls = await self._google_search(query, is_news, date_before)

            if not urls:
                logger.warning(f"[google_search_and_scrape] No URLs returned for: '{query}'")
                return GoogleScrapeResult(
                    formatted_output=f'<Summary query="{query}">No URLs returned from Google.</Summary>\n',
                    url_results=[],
                )

            # Extract content from URLs
            async with ConcurrentContentExtractor() as extractor:
                logger.info(f"[google_search_and_scrape] Extracting content from {len(urls)} URLs")
                results = await extractor.extract_content(urls)

            # Build per-URL tracking data
            url_results = []
            for url in urls:
                extraction = results.get(url, {})
                url_results.append(
                    {
                        "url": url,
                        "domain": extraction.get("domain", urlparse(url).netloc),
                        "success": extraction.get("success", False),
                        "error": extraction.get("error"),
                        "method": extraction.get("method"),
                        "status_code": extraction.get("status_code"),
                        "content_chars": extraction.get("content_chars", 0),
                        "truncated": extraction.get("truncated", False),
                    }
                )

            # Summarize top results
            summarize_tasks = []
            valid_urls = []
            max_results = 3

            for url, extraction in results.items():
                if len(summarize_tasks) >= max_results:
                    break

                content = (extraction.get("content") or "").strip()
                if len(content.split()) < 100:
                    logger.debug(f"[google_search_and_scrape] Skipping low-content: {url}")
                    continue

                if content:
                    truncated = _bm25_filter_content(content, question_details.title)
                    logger.debug(
                        f"[google_search_and_scrape] Summarizing {len(truncated)} chars from {url}"
                    )
                    summarize_tasks.append(self._summarize_article(truncated, question_details))
                    valid_urls.append(url)

            if not summarize_tasks:
                logger.warning("[google_search_and_scrape] No content to summarize")
                return GoogleScrapeResult(
                    formatted_output=f'<Summary query="{query}">No usable content extracted from any URL.</Summary>\n',
                    url_results=url_results,
                )

            summaries = await asyncio.gather(*summarize_tasks, return_exceptions=True)

            # Format output
            output = ""
            for url, summary in zip(valid_urls, summaries, strict=True):
                if isinstance(summary, Exception):
                    logger.error(f"[google_search_and_scrape] Error summarizing {url}: {summary}")
                    output += f'\n<Summary source="{url}">\nError: {summary}\n</Summary>\n'
                else:
                    output += f'\n<Summary source="{url}">\n{summary}\n</Summary>\n'

            return GoogleScrapeResult(
                formatted_output=output,
                url_results=url_results,
            )

        except Exception as e:
            logger.error(f"[google_search_and_scrape] Error: {e}")
            traceback.print_exc()
            return GoogleScrapeResult(
                formatted_output=f'<Summary query="{query}">Error during search and scrape: {e}</Summary>\n',
                url_results=[],
            )

    async def _summarize_article(
        self,
        article: str,
        question_details: QuestionDetails,
    ) -> str:
        """Summarize an article with question context."""
        prompt = ARTICLE_SUMMARY_PROMPT.format(
            title=question_details.title,
            resolution_criteria=question_details.resolution_criteria,
            fine_print=question_details.fine_print,
            background=question_details.description,
            article=article,
        )

        # Use haiku for summarization (fast, cheap)
        active_models = self.config.get("active_models", {})
        model = active_models.get(
            "article_summarizer",
            self.config.get("models", {}).get("article_summarizer", "claude-3-haiku-20240307"),
        )

        try:
            response = await self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=self._get_temperature("article_summarization"),
            )
            # Track summarization cost
            self._current_summarization_cost += response.cost
            return response.content
        except Exception as e:
            logger.error(f"Article summarization failed: {e}")
            return f"Error summarizing article: {e}"

    # -------------------------------------------------------------------------
    # AskNews
    # -------------------------------------------------------------------------

    async def _call_asknews(
        self,
        news_query: str,
        deep_research_query: str | None = None,
    ) -> str:
        """
        Search AskNews for relevant articles and run Deep Research.

        Uses three strategies:
        1. Latest news (recent/hot articles) - uses news_query
        2. Historical news (news knowledge archive) - uses news_query
        3. Deep Research (AI-synthesized analysis) - uses deep_research_query if provided

        Args:
            news_query: Query for news search (typically question title)
            deep_research_query: Query for Deep Research (LLM-generated, should request
                information rather than ask a yes/no forecasting question)

        Uses semaphore to respect AskNews free tier concurrency limits.
        """
        if not self.asknews_client_id or not self.asknews_secret:
            logger.warning("AskNews credentials not set")
            return "AskNews credentials not configured."

        # Rate limit AskNews calls (free tier limit)
        async with self._asknews_rate_limiter:
            articles_markdown = ""

            # Part 1: News search (latest + historical)
            try:
                from asknews_sdk import AskNewsSDK

                ask = AskNewsSDK(
                    client_id=self.asknews_client_id,
                    client_secret=self.asknews_secret,
                    scopes=set(["news"]),
                )

                # Pull config values
                research_cfg = self.config.get("research", {})
                n_articles = research_cfg.get("asknews_max_results", 10)

                # Run searches sequentially with rate limit delay
                # AskNews Pro tier (via Metaculus): 1 request per 10 seconds, add 2s buffer
                rate_limit_delay = 12

                logger.debug(f"[call_asknews] Searching latest news for: {news_query[:50]}...")
                hot_response = await asyncio.to_thread(
                    ask.news.search_news,
                    query=news_query,
                    n_articles=n_articles,
                    return_type="both",
                    strategy="latest news",
                )

                # Rate limit delay between calls
                logger.debug(f"[call_asknews] Waiting {rate_limit_delay}s for rate limit...")
                await asyncio.sleep(rate_limit_delay)

                logger.debug(f"[call_asknews] Searching historical news for: {news_query[:50]}...")
                historical_response = await asyncio.to_thread(
                    ask.news.search_news,
                    query=news_query,
                    n_articles=n_articles,
                    return_type="both",
                    strategy="news knowledge",
                )

                # Combine and deduplicate articles by URL
                hot_articles = hot_response.as_dicts or []
                historical_articles = historical_response.as_dicts or []

                seen_urls = set()
                unique_articles = []

                # Process hot articles first (they're more recent)
                for article in hot_articles:
                    article_dict = article.__dict__
                    url = article_dict.get("article_url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_articles.append(article_dict)

                # Then add historical articles that aren't duplicates
                for article in historical_articles:
                    article_dict = article.__dict__
                    url = article_dict.get("article_url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_articles.append(article_dict)

                # Sort by date (newest first)
                unique_articles = sorted(
                    unique_articles, key=lambda article: article["pub_date"], reverse=True
                )

                duplicates_removed = (len(hot_articles) + len(historical_articles)) - len(
                    unique_articles
                )
                if duplicates_removed > 0:
                    logger.info(f"[call_asknews] Removed {duplicates_removed} duplicate articles")

                # Format news results
                articles_markdown = "Here are the relevant news articles:\n\n"

                for article in unique_articles:
                    pub_date = article["pub_date"].strftime("%B %d, %Y %I:%M %p")
                    articles_markdown += (
                        f"**{article['eng_title']}**\n"
                        f"{article['summary']}\n"
                        f"Original language: {article['language']}\n"
                        f"Publish date: {pub_date}\n"
                        f"Source:[{article['source_id']}]({article['article_url']})\n\n"
                    )

                if not unique_articles:
                    articles_markdown += "No articles were found.\n\n"

            except Exception as e:
                logger.error(f"[call_asknews] News search error: {e}")
                articles_markdown = f"Error retrieving news articles: {e}\n\n"

            # Part 2: Deep Research (only if deep_research_query provided)
            if deep_research_query:
                try:
                    logger.debug(
                        f"[call_asknews] Waiting {rate_limit_delay}s before deep research..."
                    )
                    await asyncio.sleep(rate_limit_delay)

                    logger.info(
                        f"[call_asknews] Running deep research for: {deep_research_query[:50]}..."
                    )
                    deep_research_result = await self._call_asknews_deep_research(
                        deep_research_query, preset="low-depth", _skip_semaphore=True
                    )

                    articles_markdown += (
                        f"\n--- Deep Research Analysis ---\n{deep_research_result}\n"
                    )
                    logger.info(
                        f"[call_asknews] Deep research complete, got {len(deep_research_result)} chars"
                    )

                except Exception as e:
                    logger.error(f"[call_asknews] Deep research error: {e}")
                    articles_markdown += f"\n--- Deep Research Analysis ---\nError: {e}\n"
            else:
                logger.info(
                    "[call_asknews] Skipping deep research (no deep_research_query provided)"
                )

            return articles_markdown

    async def _call_asknews_deep_research(
        self,
        query: str,
        preset: str = "low-depth",
        _skip_semaphore: bool = False,
    ) -> str:
        """
        Use AskNews Deep Research for AI-synthesized research.

        Matches the template bot's implementation with three depth presets.

        Args:
            query: Research query/question
            preset: One of "low-depth", "medium-depth", "high-depth"
            _skip_semaphore: Internal flag to skip semaphore when called from _call_asknews

        Returns:
            Formatted research text
        """
        if not self.asknews_client_id or not self.asknews_secret:
            logger.warning("AskNews credentials not set")
            return "AskNews credentials not configured."

        async def _do_deep_research():
            try:
                from asknews_sdk import AsyncAskNewsSDK
                from asknews_sdk.dto.deepnews import CreateDeepNewsResponse
            except ImportError:
                logger.error(
                    "asknews_sdk not installed or outdated. Run: poetry add asknews@0.11.6"
                )
                return "AskNews SDK not available for deep research."

            # Configure based on preset
            # Metaculus plan only allows asknews as source
            if preset == "low-depth":
                sources = ["asknews"]
                search_depth = 1
                max_depth = 1
                filter_params = None
            elif preset == "medium-depth":
                sources = ["asknews"]
                search_depth = 2
                max_depth = 4
                filter_params = None
            elif preset == "high-depth":
                sources = ["asknews"]
                search_depth = 4
                max_depth = 6
                filter_params = None
            else:
                logger.warning(f"Unknown preset '{preset}', using low-depth")
                sources = ["asknews"]
                search_depth = 1
                max_depth = 1
                filter_params = None

            model = "deepseek-basic"  # Default model matching template

            logger.info(
                f"[asknews_deep_research] Starting {preset} research: {query[:50]}... "
                f"(sources={sources}, depth={search_depth}/{max_depth})"
            )

            try:
                async with AsyncAskNewsSDK(
                    client_id=self.asknews_client_id,
                    client_secret=self.asknews_secret,
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

                    text = response.choices[0].message.content

                    # Extract content from <final_answer> tags if present
                    start_tag = "<final_answer>"
                    end_tag = "</final_answer>"
                    start_index = text.find(start_tag)

                    if start_index != -1:
                        start_index += len(start_tag)
                        end_index = text.find(end_tag, start_index)
                        if end_index != -1:
                            text = text[start_index:end_index].strip()

                    logger.info(f"[asknews_deep_research] Complete, got {len(text)} chars")
                    return text

            except Exception as e:
                logger.error(f"[asknews_deep_research] Error: {e}")
                return f"Error running deep research: {e}"

        # If called from _call_asknews, rate limiter is already held
        if _skip_semaphore:
            return await _do_deep_research()
        else:
            async with self._asknews_rate_limiter:
                return await _do_deep_research()

    # -------------------------------------------------------------------------
    # Agentic Search
    # -------------------------------------------------------------------------

    async def _agentic_search(self, query: str, context: str = "") -> AgenticSearchResult:
        """
        Perform iterative agentic search using LLM.

        The LLM generates search queries, analyzes results, and iterates
        until it has enough information or reaches max steps.

        Args:
            query: The research query/goal to investigate.
            context: Optional context about the forecasting question to help
                guide the research (e.g., what's already known, resolution criteria).

        Returns:
            AgenticSearchResult with analysis and full instrumentation data.
        """
        logger.info(f"[agentic_search] Starting research for: {query}")

        max_steps = self.config.get("research", {}).get("agentic_search_max_steps", 7)
        current_analysis = ""
        all_search_queries: list[str] = []
        search_results = ""
        step_data_list: list[AgenticSearchStepData] = []

        # Get model for agentic search from active models (respects mode)
        active_models = self.config.get("active_models", {})
        model = active_models.get(
            "agentic_search",
            # Fallback: check if there's a query_generator, else default to haiku
            active_models.get("query_generator", "openrouter/anthropic/claude-3.5-haiku"),
        )

        for step in range(max_steps):
            try:
                # Build prompt
                if step == 0:
                    prompt = INITIAL_SEARCH_PROMPT.format(query=query, context=context)
                else:
                    if current_analysis:
                        previous_section = (
                            f"Your previous analysis:\n{current_analysis}\n\n"
                            f"Previous search queries used: {', '.join(all_search_queries)}\n"
                        )
                    else:
                        previous_section = (
                            f"Previous search queries used: {', '.join(all_search_queries)}\n"
                        )

                    prompt = CONTINUATION_SEARCH_PROMPT.format(
                        query=query,
                        context=context,
                        previous_section=previous_section,
                        search_results=search_results,
                    )

                logger.info(f"[agentic_search] Step {step + 1}: Calling LLM")
                response = await self.llm.complete(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                    temperature=self._get_temperature("agentic_search"),
                )

                # Track agentic search cost
                self._current_agentic_cost += response.cost

                response_text = response.content

                # Parse analysis
                analysis_match = re.search(
                    r"Analysis:\s*(.*?)(?=Search queries:|$)", response_text, re.DOTALL
                )
                if not analysis_match:
                    logger.warning("[agentic_search] Could not parse analysis from response")
                    return AgenticSearchResult(
                        analysis="",
                        steps_taken=step + 1,
                        queries_executed=all_search_queries,
                        step_data=step_data_list,
                        error=f"Failed to parse analysis at step {step + 1}",
                    )

                if step > 0:
                    current_analysis = analysis_match.group(1).strip()
                    logger.info(
                        f"[agentic_search] Step {step + 1}: Analysis updated ({len(current_analysis)} chars)"
                    )

                # Check for search queries
                search_queries_match = re.search(
                    r"Search queries:\s*(.*)", response_text, re.DOTALL
                )

                if step == 0 and not search_queries_match:
                    logger.warning("[agentic_search] No search queries in initial response")
                    return AgenticSearchResult(
                        analysis="",
                        steps_taken=step + 1,
                        queries_executed=all_search_queries,
                        step_data=step_data_list,
                        error="Failed to generate initial search queries",
                    )

                if not search_queries_match or step == max_steps - 1:
                    if step > 0:
                        logger.info(f"[agentic_search] Research complete at step {step + 1}")
                        break

                # Extract queries with sources
                queries_text = search_queries_match.group(1).strip()
                search_queries_with_source = re.findall(
                    r"\d+\.\s*([^(]+?)\s*\((Google|Google News|yFinance|FRED)\)",
                    queries_text,
                )

                if not search_queries_with_source:
                    if step == 0:
                        logger.warning("[agentic_search] No valid queries in initial response")
                        return AgenticSearchResult(
                            analysis="",
                            steps_taken=step + 1,
                            queries_executed=all_search_queries,
                            step_data=step_data_list,
                            error="Failed to parse initial search queries",
                        )
                    else:
                        logger.info("[agentic_search] No new queries, completing research")
                        break

                # Limit to 5 queries
                search_queries_with_source = [
                    (q.strip(), source) for q, source in search_queries_with_source[:5]
                ]

                logger.info(
                    f"[agentic_search] Step {step + 1}: Found {len(search_queries_with_source)} queries"
                )
                all_search_queries.extend([q for q, _ in search_queries_with_source])

                # Execute searches
                yfinance_enabled = self.config.get("research", {}).get("yfinance_enabled", True)
                fred_enabled = self.config.get("research", {}).get("fred_enabled", True)
                search_tasks = []
                executed_queries = []
                for sq, source in search_queries_with_source:
                    logger.debug(f"[agentic_search] Searching: {sq} (Source: {source})")
                    if source == "yFinance":
                        if not yfinance_enabled:
                            logger.info(f"[agentic_search] yFinance disabled, skipping: {sq}")
                            continue
                        search_tasks.append(self._yfinance_search(sq))
                    elif source == "FRED":
                        if not fred_enabled:
                            logger.info(f"[agentic_search] FRED disabled, skipping: {sq}")
                            continue
                        search_tasks.append(self._fred_search(sq))
                    else:
                        search_tasks.append(
                            self._google_search_agentic(sq, is_news=(source == "Google News"))
                        )
                    executed_queries.append((sq, source))

                search_results_list = await asyncio.gather(*search_tasks, return_exceptions=True)

                # Format search results
                search_results = ""
                for (sq, source), result in zip(executed_queries, search_results_list, strict=True):
                    if isinstance(result, Exception):
                        search_results += (
                            f"\nSearch query: {sq} (Source: {source})\nError: {result}\n"
                        )
                    else:
                        search_results += f"\nSearch query: {sq} (Source: {source})\n{result}\n"

                logger.info(
                    f"[agentic_search] Step {step + 1}: Search complete, {len(search_results)} chars"
                )

                # Record step data for instrumentation
                step_data_list.append(
                    AgenticSearchStepData(
                        step_number=step + 1,
                        queries_executed=search_queries_with_source,
                        search_results_raw=search_results,
                        analysis_after_step=current_analysis,
                    )
                )

            except Exception as e:
                logger.error(f"[agentic_search] Error at step {step + 1}: {e}")
                if current_analysis:
                    break
                else:
                    return AgenticSearchResult(
                        analysis="",
                        steps_taken=step + 1,
                        queries_executed=all_search_queries,
                        step_data=step_data_list,
                        error=f"Error during agentic search: {e}",
                    )

        if not current_analysis:
            return AgenticSearchResult(
                analysis="",
                steps_taken=step + 1,
                queries_executed=all_search_queries,
                step_data=step_data_list,
                error="No analysis was generated during the research process",
            )

        logger.info(f"[agentic_search] Complete: {step + 1} steps")
        return AgenticSearchResult(
            analysis=current_analysis,
            steps_taken=step + 1,
            queries_executed=all_search_queries,
            step_data=step_data_list,
            error=None,
        )

    async def _google_search_agentic(self, query: str, is_news: bool = False) -> str:
        """
        Google search that returns raw content (no summarization).

        Used by agentic search where the agent analyzes raw content.
        """
        logger.debug(f"[google_search_agentic] query='{query}' is_news={is_news}")

        try:
            urls = await self._google_search(query, is_news)

            if not urls:
                return f'<RawContent query="{query}">No URLs returned from Google.</RawContent>\n'

            async with ConcurrentContentExtractor() as extractor:
                results = await extractor.extract_content(urls)

            output = ""
            max_results = 3
            results_count = 0

            for url, extraction in results.items():
                if results_count >= max_results:
                    break

                content = (extraction.get("content") or "").strip()
                if len(content.split()) < 100:
                    continue

                if content:
                    truncated = _bm25_filter_content(content, query)
                    output += f'\n<RawContent source="{url}">\n{truncated}\n</RawContent>\n'
                    results_count += 1

            if not output:
                return f'<RawContent query="{query}">No usable content extracted.</RawContent>\n'

            return output

        except Exception as e:
            logger.error(f"[google_search_agentic] Error: {e}")
            return f'<RawContent query="{query}">Error during search: {e}</RawContent>\n'

    # -------------------------------------------------------------------------
    # Google Trends
    # -------------------------------------------------------------------------

    async def _google_trends_search(
        self, query: str, question_details: QuestionDetails | None = None
    ) -> str:
        """
        Get Google Trends historical data and compute base rate statistics.

        Query should be the search term (e.g., "hospital", "luigi mangione").
        Returns formatted statistics for forecaster consumption including:
        - Directional base rates (increase vs decrease separately)
        - Window-matched analysis (uses question's actual timeframe if available)
        """
        try:
            from trendspy import Trends

            # Extract the term - query might be "Google Trends data for hospital" or just "hospital"
            term = self._extract_trends_term(query)
            logger.info(f"[google_trends_search] Fetching data for term: '{term}'")

            # Try to extract window length from question details
            window_days = self._extract_trends_window(question_details)
            logger.info(f"[google_trends_search] Using window of {window_days} days")

            # Run synchronous trendspy call in thread pool
            def fetch_trends():
                tr = Trends()
                return tr.interest_over_time(term, timeframe="today 90-d", geo="US")

            df = await asyncio.to_thread(fetch_trends)

            if df is None or df.empty:
                logger.warning(f"[google_trends_search] No data available for term: '{term}'")
                return f'<GoogleTrendsData term="{term}">\nNo data available for this search term.\n</GoogleTrendsData>'

            # Compute statistics
            current = df[term].iloc[-1]
            mean = df[term].mean()
            std = df[term].std()

            # Compute base rates with directional split
            # Calculate all possible N-day changes where N matches the question window
            changes = df[term].diff(periods=window_days).dropna()

            # Directional analysis (without abs())
            pct_increase_gt_3 = (changes > 3).mean() * 100
            pct_decrease_gt_3 = (changes < -3).mean() * 100
            pct_no_change = (changes.abs() <= 3).mean() * 100

            # Recent trend
            last_7 = df[term].iloc[-7:].mean()
            prior_7 = df[term].iloc[-14:-7].mean()
            if last_7 > prior_7 + 1:
                trend = "increasing"
            elif last_7 < prior_7 - 1:
                trend = "decreasing"
            else:
                trend = "stable"

            # Generate daily data table (last 30 days for context)
            daily_data_lines = ["Date,Value"]
            for date, row in df.tail(30).iterrows():
                daily_data_lines.append(f"{date.strftime('%Y-%m-%d')},{int(row[term])}")
            daily_data_csv = "\n".join(daily_data_lines)

            stats = f"""<GoogleTrendsData term="{term}">
Google Trends US data for "{term}" (last 90 days):

Current value: {current:.0f}
90-day mean: {mean:.1f}
90-day std dev: {std:.1f}

BASE RATE ANALYSIS (using {window_days}-day windows to match question timeframe):
- In {pct_no_change:.0f}% of {window_days}-day windows, the value changed by ≤3 points ("Doesn't change")
- In {pct_increase_gt_3:.0f}% of {window_days}-day windows, the value INCREASED by >3 points
- In {pct_decrease_gt_3:.0f}% of {window_days}-day windows, the value DECREASED by >3 points

Recent trend: {trend} (last 7 days avg: {last_7:.1f} vs prior 7 days: {prior_7:.1f})

DAILY VALUES (last 30 days):
{daily_data_csv}

Note: Google Trends values are relative (0-100 scale), not absolute search volumes.
</GoogleTrendsData>"""

            logger.info(
                f"[google_trends_search] Successfully retrieved data for '{term}': "
                f"current={current:.0f}, mean={mean:.1f}, std={std:.1f}, "
                f"window={window_days}d, increase={pct_increase_gt_3:.0f}%, "
                f"decrease={pct_decrease_gt_3:.0f}%, no_change={pct_no_change:.0f}%"
            )
            return stats

        except Exception as e:
            logger.error(f"[google_trends_search] Error: {e}")
            return f'<GoogleTrendsData term="{query}">\nError retrieving data: {e}\n</GoogleTrendsData>'

    def _extract_trends_window(self, question_details: QuestionDetails | None) -> int:
        """
        Extract the forecast window length in days from question details.

        Looks for JSON metadata in the description with trend_start and trend_end dates.
        Falls back to 10 days if not found.
        """
        if question_details is None:
            return 10  # Default fallback

        import json

        # Look for JSON block in description with trend dates
        # Format: {"format":"trends_interest_change_magnitude","info":{"trend_start":"2026-02-05","trend_end":"2026-02-14"}}
        description = question_details.description or ""

        # Find JSON block (typically wrapped in backticks)
        json_match = re.search(r"`(\{[^`]+\})`", description)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                info = data.get("info", {})
                trend_start = info.get("trend_start")
                trend_end = info.get("trend_end")

                if trend_start and trend_end:
                    start_date = datetime.strptime(trend_start, "%Y-%m-%d")
                    end_date = datetime.strptime(trend_end, "%Y-%m-%d")
                    window_days = (end_date - start_date).days
                    if 1 <= window_days <= 90:  # Sanity check
                        logger.info(
                            f"[_extract_trends_window] Extracted window: {window_days} days "
                            f"({trend_start} to {trend_end})"
                        )
                        return window_days
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[_extract_trends_window] Failed to parse JSON: {e}")

        # Fallback: try to find dates in resolution criteria
        resolution = question_details.resolution_criteria or ""
        # Look for date patterns like "2026-02-05" and "2026-02-14"
        dates = re.findall(r"(\d{4}-\d{2}-\d{2})", resolution)
        if len(dates) >= 2:
            try:
                # Use the first two distinct dates found
                unique_dates = list(dict.fromkeys(dates))  # Remove duplicates, preserve order
                if len(unique_dates) >= 2:
                    start_date = datetime.strptime(unique_dates[0], "%Y-%m-%d")
                    end_date = datetime.strptime(unique_dates[1], "%Y-%m-%d")
                    window_days = abs((end_date - start_date).days)
                    if 1 <= window_days <= 90:
                        logger.info(
                            f"[_extract_trends_window] Extracted window from resolution: "
                            f"{window_days} days"
                        )
                        return window_days
            except ValueError as e:
                logger.warning(f"[_extract_trends_window] Failed to parse dates: {e}")

        logger.info("[_extract_trends_window] Using default window of 10 days")
        return 10  # Default fallback

    def _extract_trends_term(self, query: str) -> str:
        """Extract the search term from a query like 'Google Trends data for "hospital"'"""
        # Try to find quoted term first
        quoted = re.search(r'["\']([^"\']+)["\']', query)
        if quoted:
            return quoted.group(1)

        # Otherwise, try to extract term after common phrases
        query_lower = query.lower()
        for phrase in ["for ", "of ", "term ", "trends "]:
            if phrase in query_lower:
                idx = query_lower.find(phrase) + len(phrase)
                return query[idx:].strip().strip("\"'")

        # Last resort: return the whole query
        return query.strip()

    # -------------------------------------------------------------------------
    # FRED (Federal Reserve Economic Data)
    # -------------------------------------------------------------------------

    async def _fred_search(self, query: str) -> str:
        """
        Search FRED for an economic data series and return historical data with statistics.

        The query can be a plain-language description (e.g., "US unemployment rate")
        or a known FRED series ID (e.g., "UNRATE").
        """
        try:
            from fredapi import Fred

            if not self.fred_api_key:
                logger.warning("[fred_search] No FRED_API_KEY set, skipping")
                return (
                    f'<FREDData query="{query}">\nError: FRED_API_KEY not configured.\n</FREDData>'
                )

            cleaned_query = self._extract_fred_query(query)
            logger.info(f"[fred_search] Searching for: '{cleaned_query}'")

            if self._fred_client is None:
                self._fred_client = Fred(api_key=self.fred_api_key)
            fred = self._fred_client

            # If query looks like a series ID (all uppercase, no spaces, 2-20 chars),
            # try fetching it directly
            is_series_id = (
                cleaned_query == cleaned_query.upper()
                and " " not in cleaned_query
                and 2 <= len(cleaned_query) <= 20
            )

            series_id = None
            series_title = None
            series_units = None
            series_frequency = None

            if is_series_id:
                try:
                    info = await asyncio.to_thread(fred.get_series_info, cleaned_query)
                    series_id = cleaned_query
                    series_title = info.get("title", cleaned_query)
                    series_units = info.get("units", "N/A")
                    series_frequency = info.get("frequency", "N/A")
                    logger.info(
                        f"[fred_search] Direct series ID match: {series_id} - {series_title}"
                    )
                except Exception:
                    logger.info(
                        f"[fred_search] '{cleaned_query}' not a valid series ID, falling back to search"
                    )
                    is_series_id = False

            if series_id is None:
                # Search for matching series
                search_results = await asyncio.to_thread(fred.search, cleaned_query)

                if search_results is None or search_results.empty:
                    logger.warning(f"[fred_search] No series found for: '{cleaned_query}'")
                    return f'<FREDData query="{cleaned_query}">\nNo matching FRED series found for "{cleaned_query}".\n</FREDData>'

                # Sort by popularity (descending) and pick the top result
                if "popularity" in search_results.columns:
                    search_results = search_results.sort_values("popularity", ascending=False)

                top = search_results.iloc[0]
                series_id = top.name  # Index is the series ID
                series_title = top.get("title", series_id)
                series_units = top.get("units", "N/A")
                series_frequency = top.get("frequency", "N/A")

                # Log top 3 for visibility
                for j, (sid, row) in enumerate(search_results.head(3).iterrows()):
                    pop = row.get("popularity", "?")
                    logger.info(
                        f"[fred_search] Candidate {j + 1}: {sid} - {row.get('title', '?')} "
                        f"(popularity={pop})"
                    )

            # Fetch the full time series
            logger.info(f"[fred_search] Fetching data for series: {series_id}")
            data = await asyncio.to_thread(fred.get_series, series_id)

            if data is None or data.empty:
                return (
                    f'<FREDData series="{series_id}" query="{cleaned_query}">\n'
                    f"FRED series {series_id} ({series_title}) found but contains no observations.\n"
                    f"</FREDData>"
                )

            # Drop NaN values for statistics
            data = data.dropna()

            if data.empty:
                return (
                    f'<FREDData series="{series_id}" query="{cleaned_query}">\n'
                    f"FRED series {series_id} ({series_title}) found but all values are NaN.\n"
                    f"</FREDData>"
                )

            # Compute statistics
            latest_value = data.iloc[-1]
            latest_date = data.index[-1].strftime("%Y-%m-%d")
            start_date = data.index[0].strftime("%Y-%m-%d")

            now = data.index[-1]

            stats_lines = []
            for label, years in [("1-year", 1), ("5-year", 5), ("10-year", 10)]:
                cutoff = now - timedelta(days=years * 365)
                window = data[data.index >= cutoff]
                if len(window) >= 2:
                    stats_lines.append(
                        f"- {label}: mean={window.mean():.2f}, min={window.min():.2f}, "
                        f"max={window.max():.2f}"
                    )
            # All-time
            stats_lines.append(
                f"- All-time: mean={data.mean():.2f}, min={data.min():.2f}, "
                f"max={data.max():.2f} (since {start_date})"
            )
            stats_block = "\n".join(stats_lines)

            # Recent changes
            change_lines = []
            for label, months in [("1-month", 1), ("3-month", 3), ("6-month", 6)]:
                cutoff = now - timedelta(days=months * 30)
                past_data = data[data.index <= cutoff]
                if not past_data.empty:
                    past_value = past_data.iloc[-1]
                    abs_change = latest_value - past_value
                    pct_change = (abs_change / past_value * 100) if past_value != 0 else 0
                    sign = "+" if abs_change >= 0 else ""
                    change_lines.append(
                        f"- {label} change: {sign}{abs_change:.2f} ({sign}{pct_change:.1f}%)"
                    )

            # Year-over-year
            yoy_cutoff = now - timedelta(days=365)
            yoy_data = data[data.index <= yoy_cutoff]
            if not yoy_data.empty:
                yoy_value = yoy_data.iloc[-1]
                yoy_change = latest_value - yoy_value
                yoy_pct = (yoy_change / yoy_value * 100) if yoy_value != 0 else 0
                sign = "+" if yoy_change >= 0 else ""
                change_lines.append(
                    f"- Year-over-year: {latest_value:.2f} vs {yoy_value:.2f} "
                    f"({sign}{yoy_pct:.1f}%)"
                )
            changes_block = "\n".join(change_lines) if change_lines else "- Insufficient data"

            # Recent values table (last 12 data points)
            recent = data.tail(12)
            recent_lines = ["Date,Value"]
            for date, value in recent.items():
                recent_lines.append(f"{date.strftime('%Y-%m-%d')},{value:.2f}")
            recent_csv = "\n".join(recent_lines)

            output = f"""<FREDData series="{series_id}" query="{cleaned_query}">
FRED Economic Data: {series_title}
Series ID: {series_id}
Units: {series_units}
Frequency: {series_frequency}
Latest observation: {latest_value:.2f} ({latest_date})

HISTORICAL STATISTICS:
{stats_block}

RECENT CHANGES:
{changes_block}

RECENT VALUES ({series_frequency}):
{recent_csv}

Source: Federal Reserve Economic Data (FRED), St. Louis Fed
</FREDData>"""

            logger.info(
                f"[fred_search] Successfully retrieved {series_id} ({series_title}): "
                f"latest={latest_value:.2f} ({latest_date}), {len(data)} observations"
            )
            return output

        except Exception as e:
            logger.error(f"[fred_search] Error: {e}\n{traceback.format_exc()}")
            return f'<FREDData query="{query}">\nError retrieving FRED data: {e}\n</FREDData>'

    def _extract_fred_query(self, query: str) -> str:
        """Extract the search term from a query like 'FRED data for US unemployment rate'."""
        # Try to find quoted term first
        quoted = re.search(r'["\']([^"\']+)["\']', query)
        if quoted:
            return quoted.group(1)

        # Strip common prefixes
        query_lower = query.lower()
        for phrase in [
            "fred data for ",
            "fred series for ",
            "fred series ",
            "fred data ",
            "fred ",
            "economic data for ",
            "economic data ",
        ]:
            if query_lower.startswith(phrase):
                return query[len(phrase) :].strip().strip("\"'")

        return query.strip()

    # -------------------------------------------------------------------------
    # yFinance (Stock/ETF Market Data)
    # -------------------------------------------------------------------------

    async def _yfinance_search(self, query: str) -> str:
        """
        Search yFinance for stock/ETF data and return prices, fundamentals, and options data.

        The query can be a ticker symbol (e.g., "AAPL"), a ticker with description
        (e.g., "AAPL price history"), or a company name (less reliable).
        """
        try:
            import yfinance as yf

            cleaned_query = self._extract_yfinance_query(query)
            logger.info(f"[yfinance_search] Searching for: '{cleaned_query}'")

            # Resolve ticker symbol
            ticker_symbol = self._resolve_yfinance_ticker(cleaned_query)
            logger.info(f"[yfinance_search] Resolved ticker: '{ticker_symbol}'")

            # Fetch data (synchronous yfinance calls wrapped in to_thread)
            info, hist_1y, hist_5y, options_chains = await asyncio.to_thread(
                self._fetch_yfinance_data, yf, ticker_symbol
            )

            # Validate - need at least some data
            current_price = info.get("regularMarketPrice") or info.get("currentPrice")
            if current_price is None and (hist_1y is None or hist_1y.empty):
                # Fallback: search yfinance for the correct ticker
                logger.info(
                    f"[yfinance_search] No data for '{ticker_symbol}', "
                    f"searching yfinance for '{cleaned_query}'..."
                )
                resolved = await self._search_yfinance_ticker(cleaned_query)
                if resolved is not None:
                    ticker_symbol, info, hist_1y, hist_5y, options_chains = resolved
                    current_price = info.get("regularMarketPrice") or info.get("currentPrice")
                else:
                    logger.warning(
                        f"[yfinance_search] No data found for '{ticker_symbol}' "
                        f"and search fallback found no match"
                    )
                    return (
                        f'<YFinanceData ticker="{ticker_symbol}" query="{cleaned_query}">\n'
                        f'No data found for ticker "{ticker_symbol}". '
                        f"Verify the ticker symbol is correct.\n"
                        f"</YFinanceData>"
                    )

            # If no current price from info, use last close from history
            if current_price is None and hist_1y is not None and not hist_1y.empty:
                current_price = hist_1y["Close"].iloc[-1]

            # Build output sections
            header = self._format_yf_header(ticker_symbol, info)
            price_current = self._format_yf_current_price(info, current_price)
            price_stats = self._format_yf_price_stats(hist_1y, hist_5y)
            changes = self._format_yf_price_changes(current_price, hist_1y)
            fundamentals = self._format_yf_fundamentals(info)
            recent_prices = self._format_yf_recent_prices(hist_1y)
            options_section = self._format_yf_options(current_price, options_chains)
            analyst_section = self._format_yf_analyst_targets(info)

            output = f'<YFinanceData ticker="{ticker_symbol}" query="{cleaned_query}">\n'
            output += header
            output += price_current
            output += price_stats
            output += changes
            output += fundamentals
            output += recent_prices
            output += options_section
            output += analyst_section
            output += "\nSource: Yahoo Finance via yfinance\n"
            output += "</YFinanceData>"

            hist_len = len(hist_1y) if hist_1y is not None else 0
            logger.info(
                f"[yfinance_search] Successfully retrieved {ticker_symbol}: "
                f"price={current_price}, {hist_len} 1y observations"
            )
            return output

        except Exception as e:
            logger.error(f"[yfinance_search] Error: {e}\n{traceback.format_exc()}")
            return (
                f'<YFinanceData query="{query}">\n'
                f"Error retrieving yFinance data: {e}\n"
                f"</YFinanceData>"
            )

    def _extract_yfinance_query(self, query: str) -> str:
        """Extract the ticker/search term from a query like 'yFinance data for AAPL'."""
        # Try to find quoted term first
        quoted = re.search(r'["\']([^"\']+)["\']', query)
        if quoted:
            return quoted.group(1)

        # Strip common prefixes
        query_lower = query.lower()
        for phrase in [
            "yfinance data for ",
            "yfinance ticker ",
            "yfinance ",
            "stock data for ",
            "stock price for ",
            "stock price ",
            "options data for ",
            "options for ",
            "market data for ",
            "market data ",
            "ticker ",
        ]:
            if query_lower.startswith(phrase):
                return query[len(phrase) :].strip().strip("\"'")

        return query.strip()

    def _resolve_yfinance_ticker(self, cleaned_query: str) -> str:
        """Resolve a cleaned query to a ticker symbol.

        Handles standard tickers (AAPL), indices (^GSPC), international
        tickers (2330.TW), and tickers followed by descriptions.
        """
        stripped = cleaned_query.strip()

        # Ticker pattern: optional ^ prefix, alphanumeric, optional .suffix
        # Matches: AAPL, ^GSPC, ^TWII, BRK.B, 2330.TW
        ticker_pattern = r"\^?[A-Z0-9]{1,6}(?:\.[A-Z]{1,2})?"

        # Direct ticker only
        if re.match(f"^{ticker_pattern}$", stripped, re.IGNORECASE):
            return "^" + stripped[1:].upper() if stripped.startswith("^") else stripped.upper()

        # First word might be a ticker followed by description: "^TWII price history"
        first_word = stripped.split()[0] if stripped.split() else stripped
        if re.match(f"^{ticker_pattern}$", first_word, re.IGNORECASE):
            return (
                "^" + first_word[1:].upper() if first_word.startswith("^") else first_word.upper()
            )

        # Last resort: uppercase the whole thing (may not work well for names)
        return stripped.upper().replace(" ", "")

    async def _search_yfinance_ticker(self, cleaned_query: str):
        """Fallback: search Yahoo Finance to find the correct ticker symbol.

        Called when the initial ticker guess returns no data. Tries multiple
        search terms derived from the query, picks the best match, fetches
        data, and returns it (or None if nothing works).

        Returns:
            Tuple of (ticker_symbol, info, hist_1y, hist_5y, options_chains)
            or None if no valid ticker was found.
        """
        import yfinance as yf
        from yfinance import Search

        # Build search terms from the query — try multiple variations
        search_terms = []
        base = cleaned_query.strip()
        if base:
            search_terms.append(base)
            # If the query is all uppercase (ticker-like), also try with ^ prefix
            # (Yahoo Finance uses ^ for indices like ^TWII, ^GSPC, ^DJI)
            if base.isalpha() and base.isupper():
                search_terms.append(f"^{base}")

        seen_symbols = set()
        for term in search_terms:
            try:
                results = await asyncio.to_thread(lambda t=term: Search(t).quotes)
            except Exception as e:
                logger.debug(f"[yfinance_search] Search for '{term}' failed: {e}")
                continue

            if not results:
                continue

            # Score candidates: prefer INDEX/ETF types, prefer first results
            candidates = []
            for i, quote in enumerate(results[:5]):
                symbol = quote.get("symbol")
                if not symbol or symbol in seen_symbols:
                    continue
                seen_symbols.add(symbol)
                # Prefer indices, then ETFs, then equities
                type_score = {"INDEX": 3, "ETF": 2, "EQUITY": 1}.get(quote.get("quoteType", ""), 0)
                candidates.append((type_score, -i, symbol, quote))

            # Try candidates in priority order
            for _type_score, _pos, symbol, quote in sorted(candidates, reverse=True):
                logger.info(
                    f"[yfinance_search] Trying fallback ticker '{symbol}' "
                    f"({quote.get('shortname', '')}) from search '{term}'"
                )
                try:
                    data = await asyncio.to_thread(self._fetch_yfinance_data, yf, symbol)
                    info, hist_1y, hist_5y, options_chains = data
                    price = info.get("regularMarketPrice") or info.get("currentPrice")
                    has_data = price is not None or (hist_1y is not None and not hist_1y.empty)
                    if has_data:
                        logger.info(
                            f"[yfinance_search] Fallback success: '{cleaned_query}' -> '{symbol}'"
                        )
                        return symbol, info, hist_1y, hist_5y, options_chains
                except Exception as e:
                    logger.debug(f"[yfinance_search] Fallback ticker '{symbol}' failed: {e}")
                    continue

        return None

    @staticmethod
    def _fetch_yfinance_data(yf, symbol: str):
        """Fetch price history, info, and options data for a yFinance ticker.

        Runs synchronously — call via asyncio.to_thread.
        """
        t = yf.Ticker(symbol)
        info = t.info or {}
        hist_1y = t.history(period="1y")
        hist_5y = t.history(period="5y")

        options_chains = []
        try:
            expiries = list(t.options)[:3]
            for exp in expiries:
                options_chains.append((exp, t.option_chain(exp)))
        except Exception:
            pass

        return info, hist_1y, hist_5y, options_chains

    def _format_yf_header(self, ticker_symbol: str, info: dict) -> str:
        """Format the header section with company info."""
        name = info.get("longName") or info.get("shortName") or ticker_symbol
        exchange = info.get("exchange", "")
        currency = info.get("currency", "USD")
        sector = info.get("sector", "")
        industry = info.get("industry", "")

        header = f"MARKET DATA: {name} ({ticker_symbol})\n"
        if exchange or currency:
            header += f"Exchange: {exchange} | Currency: {currency}\n"
        if sector or industry:
            header += f"Sector: {sector} | Industry: {industry}\n"
        return header

    def _format_yf_current_price(self, info: dict, current_price: float | None) -> str:
        """Format the current price section."""
        if current_price is None:
            return ""

        currency = info.get("currency", "USD")
        symbol = "$" if currency == "USD" else ""
        lines = [f"\nCURRENT PRICE: {symbol}{current_price:.2f}"]

        prev_close = info.get("previousClose")
        if prev_close:
            lines.append(f"Previous Close: {symbol}{prev_close:.2f}")

        market_cap = info.get("marketCap")
        if market_cap:
            if market_cap >= 1e12:
                lines.append(f"Market Cap: {symbol}{market_cap / 1e12:.2f}T")
            elif market_cap >= 1e9:
                lines.append(f"Market Cap: {symbol}{market_cap / 1e9:.2f}B")
            elif market_cap >= 1e6:
                lines.append(f"Market Cap: {symbol}{market_cap / 1e6:.2f}M")

        low_52 = info.get("fiftyTwoWeekLow")
        high_52 = info.get("fiftyTwoWeekHigh")
        if low_52 and high_52:
            lines.append(f"52-Week Range: {symbol}{low_52:.2f} - {symbol}{high_52:.2f}")

        return "\n".join(lines) + "\n"

    def _format_yf_price_stats(self, hist_1y, hist_5y) -> str:
        """Format price statistics for 1yr and 5yr windows."""
        lines = []

        if hist_1y is not None and not hist_1y.empty and len(hist_1y) >= 2:
            close = hist_1y["Close"]
            lines.append(
                f"\nPRICE STATISTICS (1-Year):\n"
                f"- Mean: {close.mean():.2f}, Std Dev: {close.std():.2f}\n"
                f"- Min: {close.min():.2f}, Max: {close.max():.2f}"
            )

        if hist_5y is not None and not hist_5y.empty and len(hist_5y) >= 2:
            close = hist_5y["Close"]
            lines.append(
                f"\nPRICE STATISTICS (5-Year):\n"
                f"- Mean: {close.mean():.2f}, Min: {close.min():.2f}, Max: {close.max():.2f}"
            )

        return "\n".join(lines) + "\n" if lines else ""

    def _format_yf_price_changes(self, current_price: float | None, hist_1y) -> str:
        """Format recent price changes (mirrors FRED's RECENT CHANGES)."""
        if current_price is None or hist_1y is None or hist_1y.empty:
            return ""

        close = hist_1y["Close"]
        lines = ["\nRECENT PRICE CHANGES:"]

        for label, days in [
            ("1-week", 5),
            ("1-month", 21),
            ("3-month", 63),
            ("6-month", 126),
            ("1-year", 252),
        ]:
            if len(close) > days:
                past_price = close.iloc[-(days + 1)]
                abs_change = current_price - past_price
                pct_change = (abs_change / past_price * 100) if past_price != 0 else 0
                sign = "+" if abs_change >= 0 else ""
                lines.append(f"- {label}: {sign}{abs_change:.2f} ({sign}{pct_change:.1f}%)")

        return "\n".join(lines) + "\n" if len(lines) > 1 else ""

    def _format_yf_fundamentals(self, info: dict) -> str:
        """Format key fundamental metrics."""
        lines = []

        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        if trailing_pe or forward_pe:
            pe_parts = []
            if trailing_pe:
                pe_parts.append(f"Trailing P/E: {trailing_pe:.1f}")
            if forward_pe:
                pe_parts.append(f"Forward P/E: {forward_pe:.1f}")
            lines.append(" | ".join(pe_parts))

        revenue = info.get("totalRevenue")
        if revenue:
            if revenue >= 1e9:
                lines.append(f"Revenue (TTM): ${revenue / 1e9:.2f}B")
            elif revenue >= 1e6:
                lines.append(f"Revenue (TTM): ${revenue / 1e6:.2f}M")

        net_income = info.get("netIncomeToCommon")
        if net_income:
            if abs(net_income) >= 1e9:
                lines.append(f"Net Income (TTM): ${net_income / 1e9:.2f}B")
            elif abs(net_income) >= 1e6:
                lines.append(f"Net Income (TTM): ${net_income / 1e6:.2f}M")

        eps = info.get("trailingEps")
        if eps:
            lines.append(f"EPS (TTM): ${eps:.2f}")

        div_yield = info.get("dividendYield")
        if div_yield:
            lines.append(f"Dividend Yield: {div_yield * 100:.2f}%")

        margin = info.get("profitMargins")
        if margin:
            lines.append(f"Profit Margin: {margin * 100:.1f}%")

        if lines:
            return "\nKEY FUNDAMENTALS:\n- " + "\n- ".join(lines) + "\n"
        return ""

    def _format_yf_recent_prices(self, hist_1y) -> str:
        """Format the last 10 trading days as CSV."""
        if hist_1y is None or hist_1y.empty:
            return ""

        recent = hist_1y.tail(10)
        lines = ["\nRECENT DAILY PRICES (last 10 trading days):", "Date,Open,High,Low,Close,Volume"]
        for date, row in recent.iterrows():
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
            lines.append(
                f"{date_str},{row['Open']:.2f},{row['High']:.2f},"
                f"{row['Low']:.2f},{row['Close']:.2f},{int(row['Volume'])}"
            )
        return "\n".join(lines) + "\n"

    def _format_yf_options(self, current_price: float | None, options_chains: list) -> str:
        """Format options-implied data from option chains."""
        if not options_chains or current_price is None:
            return ""

        lines = ["\nOPTIONS-IMPLIED DATA:"]

        for expiry, chain in options_chains:
            calls = chain.calls
            puts = chain.puts

            if calls.empty and puts.empty:
                continue

            lines.append(f"Expiry: {expiry}")

            atm_iv = None

            # ATM implied volatility (closest strike to current price)
            if not calls.empty and "impliedVolatility" in calls.columns:
                atm_idx = (calls["strike"] - current_price).abs().idxmin()
                atm_call = calls.loc[atm_idx]
                iv = atm_call.get("impliedVolatility")
                if iv and iv > 0:
                    atm_iv = iv
                    lines.append(f"- ATM Implied Volatility (calls): {iv * 100:.1f}%")

            if not puts.empty and "impliedVolatility" in puts.columns:
                atm_idx = (puts["strike"] - current_price).abs().idxmin()
                atm_put = puts.loc[atm_idx]
                iv = atm_put.get("impliedVolatility")
                if iv and iv > 0:
                    lines.append(f"- ATM Implied Volatility (puts): {iv * 100:.1f}%")

            # Put/Call open interest ratio
            total_call_oi = (
                calls["openInterest"].sum()
                if "openInterest" in calls.columns and not calls["openInterest"].isna().all()
                else 0
            )
            total_put_oi = (
                puts["openInterest"].sum()
                if "openInterest" in puts.columns and not puts["openInterest"].isna().all()
                else 0
            )
            if total_call_oi > 0:
                pc_ratio = total_put_oi / total_call_oi
                lines.append(f"- Put/Call Open Interest Ratio: {pc_ratio:.2f}")

            # Highest OI strikes
            if not calls.empty and "openInterest" in calls.columns:
                valid_calls = calls.dropna(subset=["openInterest"])
                if not valid_calls.empty:
                    max_call = valid_calls.loc[valid_calls["openInterest"].idxmax()]
                    lines.append(
                        f"- Highest OI call strike: ${max_call['strike']:.2f} "
                        f"(OI: {int(max_call['openInterest']):,})"
                    )

            if not puts.empty and "openInterest" in puts.columns:
                valid_puts = puts.dropna(subset=["openInterest"])
                if not valid_puts.empty:
                    max_put = valid_puts.loc[valid_puts["openInterest"].idxmax()]
                    lines.append(
                        f"- Highest OI put strike: ${max_put['strike']:.2f} "
                        f"(OI: {int(max_put['openInterest']):,})"
                    )

            # 1-sigma range from IV
            if atm_iv and atm_iv > 0:
                try:
                    days_to_expiry = (datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days
                    if days_to_expiry > 0:
                        sigma = current_price * atm_iv * math.sqrt(days_to_expiry / 365)
                        lines.append(
                            f"- 1-sigma range ({days_to_expiry}d): "
                            f"${current_price - sigma:.2f} - ${current_price + sigma:.2f}"
                        )
                except (ValueError, TypeError):
                    pass

            lines.append("")  # blank line between expiries

        return "\n".join(lines) + "\n" if len(lines) > 1 else ""

    def _format_yf_analyst_targets(self, info: dict) -> str:
        """Format analyst price targets."""
        mean_target = info.get("targetMeanPrice")
        if not mean_target:
            return ""

        lines = ["\nANALYST TARGETS:"]
        low = info.get("targetLowPrice")
        high = info.get("targetHighPrice")
        num_analysts = info.get("numberOfAnalystOpinions")

        target_parts = [f"Mean: ${mean_target:.2f}"]
        if low:
            target_parts.append(f"Low: ${low:.2f}")
        if high:
            target_parts.append(f"High: ${high:.2f}")
        lines.append("- " + " | ".join(target_parts))

        if num_analysts:
            lines.append(f"- Number of analysts: {num_analysts}")

        return "\n".join(lines) + "\n"

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to standardized format."""
        if not date_str:
            return "Unknown"
        parsed_date = dateparser.parse(date_str, settings={"STRICT_PARSING": False})
        if parsed_date:
            return parsed_date.strftime("%b %d, %Y")
        return "Unknown"

    def _is_before_resolution_date(self, before_date_str: str, source_date_str: str) -> bool:
        """Check if source date is before the resolution cutoff date."""
        if source_date_str == "Unknown":
            return False
        before_date = dateparser.parse(before_date_str)
        source_date = dateparser.parse(source_date_str)
        if before_date and source_date:
            return source_date <= before_date
        return False


# -------------------------------------------------------------------------
# Convenience functions
# -------------------------------------------------------------------------


async def execute_searches_from_response(
    response: str,
    search_id: str,
    question_details: dict,
    config: dict,
    llm_client: LLMClient | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Convenience function to process search queries from a response.

    Args:
        response: Response containing search queries (from query generation)
        search_id: Identifier for logging (e.g., "historical", "current")
        question_details: Dict with title, resolution_criteria, fine_print, description
        config: Configuration dict
        llm_client: Optional LLMClient instance

    Returns:
        Tuple of (formatted_search_results_string, metadata_dict)
    """
    qd = QuestionDetails(
        title=question_details.get("title", ""),
        resolution_criteria=question_details.get("resolution_criteria", ""),
        fine_print=question_details.get("fine_print", ""),
        description=question_details.get("description", ""),
        resolution_date=question_details.get("resolution_date"),
    )

    async with SearchPipeline(config, llm_client) as pipeline:
        return await pipeline.execute_searches_from_response(response, search_id, qd)
