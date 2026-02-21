#!/usr/bin/env python3
"""Compare BM25 content filtering vs simple truncation on real URLs.

Fetches real web pages, applies both approaches, and prints a side-by-side
comparison so you can manually verify BM25 produces at least as good output.

Usage:
    poetry run python scripts/test_bm25_comparison.py
"""

import asyncio
import textwrap
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from src.bot.content_extractor import ConcurrentContentExtractor  # noqa: E402
from src.bot.search import _bm25_filter_content  # noqa: E402

# Test cases from actual forecast history: (url, question_title_as_bm25_query)
TEST_CASES = [
    # Long Wikipedia articles - content buried deep
    (
        "https://en.wikipedia.org/wiki/Ford_Motor_Company",
        "Will F's market close price on 2026-02-26 be higher than its market close price on 2026-02-20?",
    ),
    (
        "https://en.wikipedia.org/wiki/2026_Hungarian_parliamentary_election",
        "Will any political party or coalition acquire a supermajority in the 2026 Hungarian parliamentary elections?",
    ),
    # News articles - typically shorter but may have boilerplate
    (
        "https://www.kiplinger.com/economic-forecasts/interest-rates",
        "What will be the upper bound of the Federal Funds Target Range on March 31, 2026?",
    ),
    (
        "https://www.macrotrends.net/stocks/charts/NFLX/netflix/revenue",
        "How much will Netflix's revenue grow year-over-year in its Q1 2026 earnings report?",
    ),
    # Finance/economics - data-heavy pages
    (
        "https://fred.stlouisfed.org/series/SP500",
        "What will be the closing value of the S&P 500 on March 13, 2026?",
    ),
    (
        "https://www.ceicdata.com/en/indicator/pakistan/policy-rate",
        "What will be the State Bank of Pakistan's target policy rate as of May 1, 2026?",
    ),
    # Policy/analysis - long-form content
    (
        "https://www.csis.org/events/putin-succession-whats-stake-and-what-expect",
        "Will Vladimir Putin cease to be the President of the Russian Federation before May 1, 2026?",
    ),
    (
        "https://www.pubaffairsbruxelles.eu/opinion-analysis/can-hungarys-opposition-win-and-restore-democracy/",
        "Will the Tisza Party win more parliamentary seats than Fidesz-KDNP in Hungary's 2026 parliamentary election?",
    ),
    # Japan politics
    (
        "https://fsi.stanford.edu/news/what-know-about-sanae-takaichi-japans-first-female-prime-minister-and-her-agenda",
        "How many days will Takaichi Sanae serve as Prime Minister of Japan before 2032?",
    ),
    # Oil/energy
    (
        "https://www.deloitte.com/us/en/insights/industry/oil-and-gas/oil-and-gas-industry-outlook.html",
        "Will the average daily price of kerosene jet fuel in the US Gulf Coast be greater than $2.50 per gallon in March 2026?",
    ),
]

MAX_CHARS = 8000


def preview(text: str, max_lines: int = 10) -> str:
    """Show first and last few lines of text."""
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    half = max_lines // 2
    return "\n".join(
        lines[:half] + [f"  ... ({len(lines) - max_lines} lines omitted) ..."] + lines[-half:]
    )


async def main():
    urls = [url for url, _ in TEST_CASES]

    print("Fetching URLs...")
    async with ConcurrentContentExtractor() as extractor:
        results = await extractor.extract_content(urls)

    num_compared = 0
    num_different = 0

    for url, query in TEST_CASES:
        extraction = results.get(url, {})
        content = (extraction.get("content") or "").strip()
        success = extraction.get("success", False)

        print("\n" + "=" * 80)
        print(f"URL: {url}")
        print(f"Query: {query[:100]}")
        print(f"Success: {success}")
        print(f"Content length: {len(content)} chars")

        if not content or len(content) < 100:
            print("  SKIPPED (insufficient content)")
            continue

        if len(content) <= MAX_CHARS:
            print(f"  Content fits within {MAX_CHARS} chars - no filtering needed")
            continue

        num_compared += 1

        # Simple truncation
        truncated = content[:MAX_CHARS]

        # BM25 filtering
        bm25_result = _bm25_filter_content(content, query, max_chars=MAX_CHARS)

        # Check if they're different
        same = truncated == bm25_result
        print(f"\n  Truncation: {len(truncated)} chars")
        print(f"  BM25:       {len(bm25_result)} chars")
        print(f"  Same output: {same}")

        if same:
            continue

        num_different += 1

        # Show what's different
        trunc_words = set(truncated.lower().split())
        bm25_words = set(bm25_result.lower().split())
        only_in_bm25 = bm25_words - trunc_words
        only_in_trunc = trunc_words - bm25_words

        print(f"\n  Words only in BM25 result ({len(only_in_bm25)} unique):")
        interesting = sorted([w for w in only_in_bm25 if len(w) > 5], key=len, reverse=True)[:20]
        if interesting:
            print(f"    {', '.join(interesting)}")

        print(f"\n  Words only in truncation result ({len(only_in_trunc)} unique):")
        interesting = sorted([w for w in only_in_trunc if len(w) > 5], key=len, reverse=True)[:20]
        if interesting:
            print(f"    {', '.join(interesting)}")

        print("\n  --- TRUNCATION first 500 chars ---")
        print(textwrap.indent(truncated[:500], "  "))

        print("\n  --- BM25 first 500 chars ---")
        print(textwrap.indent(bm25_result[:500], "  "))

        print("\n  --- BM25 last 500 chars ---")
        print(textwrap.indent(bm25_result[-500:], "  "))

    print("\n" + "=" * 80)
    print(
        f"Summary: {num_compared} URLs over {MAX_CHARS} chars, {num_different} had different output"
    )
    print("Done. Review the output above to verify BM25 produces good results.")


if __name__ == "__main__":
    asyncio.run(main())
