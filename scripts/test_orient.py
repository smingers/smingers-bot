#!/usr/bin/env python3
"""
Orient Phase Test

Loads a forecast artifact directory, extracts the question and pre-research
context, runs the orient step (cheap LLM → 1-2 Google queries → scrape),
and saves the output to scratchpad/orient/.

Usage:
    poetry run python scripts/test_orient.py data/42419_20260304_063137
    poetry run python scripts/test_orient.py data/42419_20260304_063137 --show-prompt
    poetry run python scripts/test_orient.py data/42419_20260304_063137 --model openrouter/google/gemini-3-flash-preview
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.prompts import ORIENT_PROMPT  # noqa: E402
from src.bot.research_planner import IterativeResearchPlanner  # noqa: E402
from src.bot.search import QuestionDetails, SearchPipeline  # noqa: E402
from src.utils.llm import LLMClient  # noqa: E402

SAVE_DIR = Path(__file__).parent.parent / "scratchpad" / "orient"
DEFAULT_MODEL = "openrouter/google/gemini-3-flash-preview"


def load_artifact(artifact_dir: Path) -> tuple[dict, str]:
    """Load question metadata and pre-research context from artifact directory."""
    q_path = artifact_dir / "question.json"
    if not q_path.exists():
        raise FileNotFoundError(f"question.json not found in {artifact_dir}")

    raw = json.loads(q_path.read_text())
    q_inner = raw.get("question", raw)

    metadata = {
        "id": raw.get("id") or q_inner.get("post_id"),
        "title": raw.get("title") or q_inner.get("title", ""),
        "question_type": q_inner.get("type", "binary"),
        "scheduled_resolve_time": raw.get("scheduled_resolve_time")
        or q_inner.get("scheduled_resolve_time")
        or "unknown",
        "status": raw.get("status") or q_inner.get("status", "unknown"),
        "background_info": q_inner.get("description", ""),
        "resolution_criteria": q_inner.get("resolution_criteria", ""),
        "fine_print": q_inner.get("fine_print", ""),
    }

    # Load pre-research context from the plan prompt (everything before YOUR TASK:)
    prompt_path = artifact_dir / "research" / "query_plan_prompt.md"
    seed_context = ""
    if prompt_path.exists():
        text = prompt_path.read_text()
        # Extract the PRE-RESEARCH CONTEXT section
        pre_idx = text.find("PRE-RESEARCH CONTEXT:")
        task_idx = text.find("YOUR TASK:")
        if pre_idx != -1 and task_idx != -1:
            seed_context = text[pre_idx:task_idx].strip()
            # Strip the header line
            header_end = seed_context.find("\n")
            if header_end != -1:
                seed_context = seed_context[header_end:].strip()
                # Also strip the boilerplate line about "already gathered"
                boilerplate = "The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed."
                seed_context = seed_context.replace(boilerplate, "").strip()

    return metadata, seed_context


def build_orient_prompt(metadata: dict, seed_context: str) -> str:
    """Build the orient prompt from question metadata and seed context."""
    seed_section = ""
    if seed_context:
        seed_section = (
            "PRE-RESEARCH CONTEXT (already gathered):\n"
            f"{seed_context[:3000]}\n"
        )

    return ORIENT_PROMPT.format(
        title=metadata["title"],
        question_type=metadata["question_type"],
        scheduled_resolve_time=metadata["scheduled_resolve_time"],
        background=metadata["background_info"][:2000],
        resolution_criteria=metadata["resolution_criteria"],
        seed_context_section=seed_section,
    )


async def run(artifact_dir: Path, model: str, show_prompt: bool) -> None:
    """Run the orient phase on an artifact directory."""
    print(f"\nLoading {artifact_dir.name}...")
    metadata, seed_context = load_artifact(artifact_dir)

    print(f"  {metadata['title'][:80]}")
    print(f"  Type: {metadata['question_type']}  |  Status: {metadata['status']}")
    if seed_context:
        print(f"  Pre-research context: {len(seed_context)} chars")
    else:
        print("  No pre-research context found")

    # Step 1: Build and call orient prompt
    prompt = build_orient_prompt(metadata, seed_context)

    if show_prompt:
        print("\n" + "=" * 72)
        print("ORIENT PROMPT")
        print("-" * 72)
        print(prompt)
        print("=" * 72)

    print(f"\nStep 1: Calling {model} for orient queries...")
    llm = LLMClient()
    response = await llm.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    print(f"  Cost: ${response.cost:.4f}  |  Latency: {response.latency_ms}ms")
    print(f"\n  LLM response:\n  {response.content}")

    # Step 2: Parse queries
    queries = IterativeResearchPlanner._parse_orient_queries(response.content)
    print(f"\n  Parsed {len(queries)} orient queries:")
    for i, q in enumerate(queries, 1):
        print(f"    {i}. {q}")

    if not queries:
        print("\n  No queries parsed, stopping.")
        return

    # Step 3: Execute queries via Google search + scrape
    print(f"\nStep 2: Executing {len(queries)} Google searches...")

    # Build minimal question details for the search pipeline
    question_details = QuestionDetails(
        title=metadata["title"],
        resolution_criteria=metadata["resolution_criteria"],
        fine_print=metadata["fine_print"],
        description=metadata["background_info"],
    )

    # Minimal config for search pipeline
    config = {
        "research": {
            "google_enabled": True,
            "google_max_results": 10,
            "scraping_enabled": True,
            "max_articles_to_scrape": 10,
            "max_content_length": 15000,
        },
        "llm": {
            "temperature": {"article_summary": 0.1},
            "max_output_tokens": 5000,
        },
        "active_models": {},
    }

    seen_urls: set[str] = set()
    orient_results: list[dict] = []

    async with SearchPipeline(config, llm) as search:
        for query_text in queries:
            print(f"\n  Searching: {query_text}")
            result = await search._google_search_and_scrape(
                query=query_text,
                is_news=False,
                question_details=question_details,
                seen_urls=seen_urls,
            )
            orient_results.append({
                "query": query_text,
                "output": result.formatted_output,
                "url_results": result.url_results,
            })
            # Count summaries
            n_summaries = result.formatted_output.count("<Summary")
            n_urls = len(result.url_results)
            print(f"    {n_urls} URLs found, {n_summaries} summarized")

    # Format output
    sep = "=" * 72
    thin = "-" * 72

    output_parts = [
        sep,
        "ORIENT PHASE TEST",
        sep,
        "",
        "QUESTION",
        thin,
        f"  {metadata['title']}",
        f"  Type: {metadata['question_type']}  |  Resolves: {metadata['scheduled_resolve_time']}",
        "",
        "MODEL",
        thin,
        f"  {model}",
        f"  Cost: ${response.cost:.4f}  |  Latency: {response.latency_ms}ms",
        "",
        "ORIENT QUERIES",
        thin,
    ]
    for i, q in enumerate(queries, 1):
        output_parts.append(f"  {i}. {q}")

    output_parts.extend(["", "ORIENT RESULTS", thin])
    for r in orient_results:
        output_parts.append(f"\n--- Query: {r['query']} ---")
        output_parts.append(r["output"])

    # The combined orient context that would be injected as seed context
    orient_context = "\n".join(
        f'<OrientSearch query="{r["query"]}">\n{r["output"]}\n</OrientSearch>'
        for r in orient_results
        if r["output"]
    )
    output_parts.extend([
        "",
        "COMBINED ORIENT CONTEXT (would be injected as seed context)",
        thin,
        f"  {len(orient_context)} chars",
        "",
        sep,
    ])

    output = "\n".join(output_parts)
    print("\n" + output)

    # Save
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    save_path = SAVE_DIR / f"{metadata['id']}_{timestamp}.md"

    full_output = output + "\n\nFULL ORIENT CONTEXT\n" + thin + "\n" + orient_context
    full_output += "\n\nORIENT PROMPT\n" + thin + "\n" + prompt
    save_path.write_text(full_output)
    print(f"\nSaved to {save_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Test orient phase on a forecast artifact directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "artifact_dir",
        type=Path,
        help="Path to forecast artifact directory (e.g. data/42419_20260304_063137)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model for orient query generation (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Show the orient prompt before calling the LLM",
    )
    args = parser.parse_args()

    if not args.artifact_dir.is_dir():
        parser.error(f"Not a directory: {args.artifact_dir}")

    asyncio.run(run(args.artifact_dir, args.model, args.show_prompt))


if __name__ == "__main__":
    main()
