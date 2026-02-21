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

# Test cases: (url, question_title_as_bm25_query)
TEST_CASES = [
    (
        "https://en.wikipedia.org/wiki/2026_Hungarian_parliamentary_election",
        "Will any political party or coalition acquire a supermajority in the 2026 Hungarian parliamentary elections?",
    ),
    (
        "https://en.wikipedia.org/wiki/Special:Statistics",
        "Will the English Wikipedia have at least 7,145,000 articles before March 1, 2026?",
    ),
    (
        "https://www.reuters.com/world/",
        "Will there be a ceasefire in the Russia-Ukraine war before 2027?",
    ),
    (
        "https://fred.stlouisfed.org/series/UNRATE",
        "Will the US unemployment rate exceed 5% before July 2026?",
    ),
    (
        "https://en.wikipedia.org/wiki/Ford_Motor_Company",
        "Will F's market close price on 2026-02-26 be higher than its market close price on 2026-02-20?",
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

    for url, query in TEST_CASES:
        extraction = results.get(url, {})
        content = (extraction.get("content") or "").strip()
        success = extraction.get("success", False)

        print("\n" + "=" * 80)
        print(f"URL: {url}")
        print(f"Query: {query[:80]}...")
        print(f"Success: {success}")
        print(f"Content length: {len(content)} chars")

        if not content or len(content) < 100:
            print("  SKIPPED (insufficient content)")
            continue

        # Simple truncation
        truncated = content[:MAX_CHARS]

        # BM25 filtering
        bm25_result = _bm25_filter_content(content, query, max_chars=MAX_CHARS)

        # Compare
        if content == truncated == bm25_result:
            print(f"  Content fits within {MAX_CHARS} chars — no filtering needed")
            continue

        # Check if they're different
        same = truncated == bm25_result
        print(f"\n  Truncation: {len(truncated)} chars")
        print(f"  BM25:       {len(bm25_result)} chars")
        print(f"  Same output: {same}")

        if not same:
            # Show what's different
            trunc_words = set(truncated.lower().split())
            bm25_words = set(bm25_result.lower().split())
            only_in_bm25 = bm25_words - trunc_words
            only_in_trunc = trunc_words - bm25_words

            print(f"\n  Words only in BM25 result ({len(only_in_bm25)} unique):")
            # Show most interesting unique words (longer ones, likely meaningful)
            interesting = sorted([w for w in only_in_bm25 if len(w) > 5], key=len, reverse=True)[
                :20
            ]
            if interesting:
                print(f"    {', '.join(interesting)}")

            print(f"\n  Words only in truncation result ({len(only_in_trunc)} unique):")
            interesting = sorted([w for w in only_in_trunc if len(w) > 5], key=len, reverse=True)[
                :20
            ]
            if interesting:
                print(f"    {', '.join(interesting)}")

            print("\n  --- BM25 output preview ---")
            print(textwrap.indent(preview(bm25_result, max_lines=15), "  "))

    print("\n" + "=" * 80)
    print("Done. Review the output above to verify BM25 produces good results.")


if __name__ == "__main__":
    asyncio.run(main())
