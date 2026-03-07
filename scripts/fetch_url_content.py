#!/usr/bin/env python3
"""
Fetch a single URL using the bot's existing scraping strategy (ConcurrentContentExtractor)
and print the exact result: metadata and full content.

Usage:
  poetry run python scripts/fetch_url_content.py <url>
"""

import asyncio
import json
import sys

from src.bot.content_extractor import ConcurrentContentExtractor


async def main(url: str) -> None:
    async with ConcurrentContentExtractor() as extractor:
        results = await extractor.extract_content([url])
    result = results.get(url, {})
    # Print metadata (excluding raw content for readability in summary)
    meta = {k: v for k, v in result.items() if k != "content"}
    print("--- METADATA ---")
    print(json.dumps(meta, indent=2))
    print()
    print("--- CONTENT (exact output) ---")
    content = result.get("content")
    if content is None:
        print("(null)")
    else:
        print(content)
    print()
    print("--- END ---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: poetry run python scripts/fetch_url_content.py <url>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1].strip()
    if not url:
        print("Usage: poetry run python scripts/fetch_url_content.py <url>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(url))
