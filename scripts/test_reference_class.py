#!/usr/bin/env python3
"""
Reference Class Selection Test

Loads a forecast artifact directory and makes one LLM call to identify
the most appropriate reference class for base rate estimation.

Usage:
    poetry run python scripts/test_reference_class.py data/41594_20260226_211645
    poetry run python scripts/test_reference_class.py data/41594_20260226_211645 --show-prompt

Runs two passes (o3 and gemini-3-flash-preview) and saves combined output for comparison.
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

from src.utils.llm import LLMClient  # noqa: E402

SAVE_DIR = Path(__file__).parent.parent / "scratchpad" / "base_rate_selection"
MODELS = [
    "openrouter/openai/o3",
    "openrouter/google/gemini-3-flash-preview",
]

PROMPT_TEMPLATE = """You are a research planner for a forecasting question. Your task is to analyze the question and the pre-research context to identify the most appropriate reference class for base rate estimation.

---

QUESTION: {title}
Type: {question_type}
Today: {today}
Resolves: {scheduled_resolve_time}

Question and pre-research context:

{context_block}

---

YOUR TASK

Step 1: Describe the current situation in 2-4 key dimensions that matter for the outcome.

Step 2: Define a reference class as a set of past situations that match those dimensions. How many cases? In what fraction did the outcome occur?

Step 3: State your base rate estimate and the biggest uncertainty.

Step 4: Propose one research query to validate the base rate.

---

FORMAT:

Current Situation:
- [Dimension 1]: [State]
- [Dimension 2]: [State]
- [Dimension 3]: [State]
- [Dimension 4]: [State]

Reference Class: [Description of past situations that match]
Cases: [N]
Base Rate: [X% of those cases led to the outcome]

Estimate: [Your final probability]
Key Uncertainty: [Biggest factor that could change this]
Research Query: [One query to validate]
"""


def load_artifact(artifact_dir: Path) -> tuple[dict, str]:
    """Load question metadata and context from artifact directory."""
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
    }

    prompt_path = artifact_dir / "research" / "query_plan_prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            "research/query_plan_prompt.md not found; only recent forecasts have this file"
        )

    text = prompt_path.read_text()
    idx = text.find("YOUR TASK:")
    if idx == -1:
        raise ValueError("Could not find 'YOUR TASK:' marker in query_plan_prompt.md")

    context_block = text[:idx].rstrip()

    # Replace first line: research planner intro → reference class framing
    old_first_line = "You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base."
    new_first_line = "You are a research planner for a forecasting question. Your task is to identify the most appropriate reference class(es) for this question. A reference class is a set of past situations comparable enough to the current one that their historical frequency can anchor a base rate."

    if context_block.startswith(old_first_line):
        context_block = new_first_line + context_block[len(old_first_line) :]

    return metadata, context_block


def build_prompt(metadata: dict, context_block: str) -> str:
    """Build the reference class prompt."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return PROMPT_TEMPLATE.format(
        title=metadata["title"],
        question_type=metadata["question_type"],
        today=today,
        scheduled_resolve_time=metadata["scheduled_resolve_time"],
        context_block=context_block,
    )


async def run_one(
    llm: LLMClient,
    prompt: str,
    model: str,
) -> tuple[str, float, int]:
    """Run reference class selection for one model. Returns (content, cost, latency_ms)."""
    response = await llm.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return (response.content, response.cost, response.latency_ms)


async def run(artifact_dir: Path, show_prompt: bool) -> None:
    """Run reference class selection with two passes (o3 and gemini-3-flash-preview)."""
    print(f"\nLoading {artifact_dir.name}...")
    metadata, context_block = load_artifact(artifact_dir)

    print(f"  {metadata['title'][:80]}")
    print(f"  Type: {metadata['question_type']}  |  Status: {metadata['status']}")

    prompt = build_prompt(metadata, context_block)

    if show_prompt:
        lines = prompt.splitlines()
        preview = "\n".join(lines[:50])
        if len(lines) > 50:
            preview += f"\n\n... [{len(lines) - 50} more lines]"
        print("\n" + "=" * 72)
        print("PROMPT")
        print("-" * 72)
        print(preview)

    llm = LLMClient()
    sep = "=" * 72
    thin = "-" * 72
    sections: list[str] = [
        sep,
        "REFERENCE CLASS SELECTION (two passes)",
        sep,
        "",
        "QUESTION",
        thin,
        f"  {metadata['title']}",
        f"  Type: {metadata['question_type']}  |  Resolves: {metadata['scheduled_resolve_time']}",
        "",
    ]

    for model in MODELS:
        print(f"\nCalling {model}...")
        content, cost, latency_ms = await run_one(llm, prompt, model)
        sections.extend(
            [
                f"MODEL: {model}",
                thin,
                "",
                "RESPONSE",
                thin,
                content,
                "",
                "COST / PERFORMANCE",
                thin,
                f"  Cost:    ${cost:.4f}",
                f"  Latency: {latency_ms}ms",
                "",
                sep,
                "",
            ]
        )

    output = "\n".join(sections)
    print("\n" + output)

    # Save
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    save_path = SAVE_DIR / f"{metadata['id']}_{timestamp}.md"
    full_output = output + "\n\nFULL PROMPT\n" + "-" * 72 + "\n" + prompt
    save_path.write_text(full_output)
    print(f"\nSaved to {save_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Reference class selection from forecast artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "artifact_dir",
        type=Path,
        help="Path to forecast artifact directory (e.g. data/41594_20260226_211645)",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Show prompt preview before calling LLM",
    )
    args = parser.parse_args()

    if not args.artifact_dir.is_dir():
        parser.error(f"Not a directory: {args.artifact_dir}")

    asyncio.run(run(args.artifact_dir, args.show_prompt))


if __name__ == "__main__":
    main()
