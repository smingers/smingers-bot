#!/usr/bin/env python3
"""
Manual test script for the Analyst tool.

Usage:
    poetry run python scripts/test_analyst.py "Compute 7-day return distribution for ^N225"
    poetry run python scripts/test_analyst.py --verbose "Query here"
    poetry run python scripts/test_analyst.py --model openrouter/openai/gpt-4o "Query here"
    poetry run python scripts/test_analyst.py --timeout 60 "Long-running query here"
"""

import argparse
import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

from src.bot.analyst import AnalystTool  # noqa: E402
from src.utils.llm import LLMClient  # noqa: E402

DEFAULT_MODEL = "openrouter/openai/o3"


async def main():
    parser = argparse.ArgumentParser(description="Test the Analyst tool with a query")
    parser.add_argument("query", help="Natural-language analysis query")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"LLM model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument("--verbose", action="store_true", help="Show generated code")
    parser.add_argument("--timeout", type=int, default=30, help="Execution timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="Max retries on failure")
    args = parser.parse_args()

    print(f"Query: {args.query}")
    print(f"Model: {args.model}")
    print(f"Timeout: {args.timeout}s | Max retries: {args.retries}")
    print("-" * 60)

    llm = LLMClient()
    tool = AnalystTool(llm=llm, model=args.model, max_retries=args.retries, timeout=args.timeout)

    start = time.time()
    result = await tool.run(args.query)
    elapsed = time.time() - start

    if args.verbose and tool._last_code:
        print("\n=== GENERATED CODE ===")
        print(tool._last_code)
        print("=== END CODE ===\n")

    # On failure, show raw LLM response for diagnostics
    if "Error:" in result and tool._last_raw_response:
        print("\n=== RAW LLM RESPONSE (diagnostics) ===")
        print(tool._last_raw_response[:2000])
        if len(tool._last_raw_response) > 2000:
            print(f"... ({len(tool._last_raw_response)} chars total)")
        print("=== END RAW RESPONSE ===\n")

    print(result)
    print("-" * 60)
    print(f"Time: {elapsed:.1f}s | LLM cost: ${tool.total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
