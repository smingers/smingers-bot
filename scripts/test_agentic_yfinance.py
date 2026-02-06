"""
Test script: Verify that agentic search can use yFinance and self-correct bad tickers.

Simulates the query that the query builder agent would pass to agentic search
for the TAIEX question (36030). The agentic search should:
1. Attempt a yFinance query (likely with a wrong ticker like TWEX)
2. See the "No data found" error in results
3. Google for the correct ticker
4. Retry with ^TWII and succeed
"""

import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

from src.bot.search import SearchPipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def test_agentic_yfinance():
    config = {
        "research": {
            "google_enabled": True,
            "yfinance_enabled": True,
            "agentic_search_max_steps": 4,
            "scraping_enabled": True,
            "max_articles_to_scrape": 3,
            "max_content_length": 5000,
        },
        "active_models": {
            "agentic_search": "openrouter/anthropic/claude-3.5-haiku",
            "article_summarizer": "openrouter/anthropic/claude-3.5-haiku",
        },
    }

    pipeline = SearchPipeline(config)
    pipeline._current_agentic_cost = 0.0
    async with pipeline:
        # This is the kind of query the query builder agent generates for agentic search
        result = await pipeline._agentic_search(
            query=(
                "Analyze potential scenarios for the Taiwan Stock Exchange "
                "Capitalization Weighted Index (TAIEX) considering geopolitical "
                "risks and semiconductor industry trends in 2026"
            ),
            context=(
                "Question: What will be the value of the Taiwan Stock Index "
                "(TAIEX) at the end of 2026?\n\n"
                "Resolution criteria: Resolves based on the closing value of "
                "the TAIEX on December 31, 2026.\n\n"
                "The TAIEX is the main stock market index for the Taiwan Stock "
                "Exchange."
            ),
        )

    print("\n" + "=" * 80)
    print(f"RESULT: {result.steps_taken} steps taken")
    print(f"Total queries executed: {result.queries_executed}")
    if result.error:
        print(f"Error: {result.error}")
    print("=" * 80)

    # Show step-by-step detail
    for step in result.step_data:
        print(f"\n--- Step {step.step_number} ---")
        print(f"Queries: {step.queries_executed}")

    # Check if yFinance was used and whether it self-corrected
    yfinance_queries = [q for q in result.queries_executed if q.startswith("^") or q.isupper()]
    print(f"\nPotential yFinance queries: {yfinance_queries}")

    # Check if the analysis mentions TAIEX price data
    if result.analysis:
        print(f"\nAnalysis length: {len(result.analysis)} chars")
        # Look for signs of successful yFinance data
        for keyword in ["^TWII", "TAIEX", "regularMarketPrice", "MARKET DATA"]:
            if keyword in result.analysis:
                print(f"  ✓ Found '{keyword}' in analysis")
            # Also check in step data search results
            for step in result.step_data:
                raw = step.search_results_raw or ""
                if keyword in raw:
                    print(f"  ✓ Found '{keyword}' in step {step.step_number} search results")
                    break
    else:
        print("\nNo analysis produced")


if __name__ == "__main__":
    asyncio.run(test_agentic_yfinance())
