#!/usr/bin/env python3
"""
Reference Class Selection Test

Fetches a Metaculus question and makes a single focused LLM call to identify
candidate reference classes and recommend the most appropriate one.

This tests whether a model can select the right base rate from question text
alone, before any research is executed. Run it on multiple questions with
different models to calibrate whether this approach is worth building into
the pipeline.

Usage:
    # Basic: fetch question and test reference class selection
    poetry run python scripts/test_reference_class.py --question 41594

    # Use a specific model (default: claude-3.5-haiku, cheap)
    poetry run python scripts/test_reference_class.py --question 41594 \
        --model openrouter/openai/o3-mini

    # Save output to a file (default output dir)
    poetry run python scripts/test_reference_class.py --question 41594 \
        --save scratchpad/base_rate_selection/rc_41594.md

    # Show the prompt being sent (default: hidden to keep output clean)
    poetry run python scripts/test_reference_class.py --question 41594 \
        --show-prompt
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.llm import LLMClient  # noqa: E402
from src.utils.metaculus_api import MetaculusClient  # noqa: E402

# ---------------------------------------------------------------------------
# Default model: cheap but capable enough for this reasoning task
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "openrouter/anthropic/claude-3.5-haiku"

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

REFERENCE_CLASS_PROMPT = """You are a forecasting expert preparing to research a prediction question.

Before running any searches, your task is to identify the most appropriate reference class(es) for this question. A reference class is a set of past situations comparable enough to the current one that their historical frequency can anchor a base rate.

Good reference class selection is often the most important step in superforecasting: too broad a class dilutes the signal; too narrow a class gives too few cases to be reliable. The goal is the most specific class that still has enough historical cases to be meaningful.

---

QUESTION: {title}
Type: {question_type}
Today: {today}
Resolves: {scheduled_resolve_time}

Background:
{background}

Resolution criteria:
{resolution_criteria}

Fine print:
{fine_print}

---

YOUR TASK

Propose 3 candidate reference classes at different levels of specificity:

1. NARROW — A tightly defined class with high comparability to the current situation (possibly few cases)
2. MEDIUM — A moderately scoped class balancing comparability and sample size
3. BROAD — A general class with many cases but lower comparability

For each class, provide:
- A precise description of what historical cases qualify
- Your best estimate of the base rate (even if rough — "~15%" is fine; "unknown" is not useful)
- A brief argument for and against using this class

Then choose the most appropriate class and explain why. Key considerations:
- Does the proposed class actually match the resolution criteria (not just the surface topic)?
- Are the conditions that distinguish this situation from others relevant to the outcome?
- Is the sample size large enough to be informative?

Finally, propose one concrete research query that would confirm or refine the base rate for your recommended class.

---

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:

Candidate Reference Classes:

1. Narrow: [precise description]
   Estimated cases: [N or range]
   Estimated base rate: [X%]
   For: [1-2 sentences]
   Against: [1-2 sentences]

2. Medium: [precise description]
   Estimated cases: [N or range]
   Estimated base rate: [X%]
   For: [1-2 sentences]
   Against: [1-2 sentences]

3. Broad: [precise description]
   Estimated cases: [N or range]
   Estimated base rate: [X%]
   For: [1-2 sentences]
   Against: [1-2 sentences]

Recommended Class: [Narrow / Medium / Broad]
Reasoning: [Why this class is most appropriate for THIS question]
Estimated Base Rate: [Your best estimate from the recommended class]

Key Uncertainty: [The single biggest factor that could make the true base rate different from your estimate]

Research Query: [One concrete query — ideally for the Agent tool — that would confirm or refine this base rate]
"""


def build_prompt(q) -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    # Collapse background fields — use description, fallback to background_info
    background = q.description or q.background_info or "(none provided)"
    resolution_criteria = q.resolution_criteria or "(none provided)"
    fine_print = q.fine_print or "(none provided)"

    return REFERENCE_CLASS_PROMPT.format(
        title=q.title,
        question_type=q.question_type,
        today=today,
        scheduled_resolve_time=q.scheduled_resolve_time or "unknown",
        background=background,
        resolution_criteria=resolution_criteria,
        fine_print=fine_print,
    )


def format_question_summary(q) -> str:
    lines = [
        f"  Title:    {q.title}",
        f"  Type:     {q.question_type}",
        f"  Status:   {q.status}",
        f"  Resolves: {q.scheduled_resolve_time}",
        f"  URL:      {q.page_url}",
    ]
    if q.num_forecasters:
        lines.append(f"  Forecasters: {q.num_forecasters}")
    return "\n".join(lines)


def format_output(q, prompt: str, response: str, model: str, cost: float, latency_ms: int) -> str:
    sep = "=" * 72
    thin = "-" * 72

    parts = [
        sep,
        "REFERENCE CLASS SELECTION TEST",
        sep,
        "",
        "QUESTION",
        thin,
        format_question_summary(q),
        "",
        "MODEL",
        thin,
        f"  {model}",
        "",
        "RESPONSE",
        thin,
        response,
        "",
        "COST / PERFORMANCE",
        thin,
        f"  Cost:    ${cost:.4f}",
        f"  Latency: {latency_ms}ms",
        sep,
    ]
    return "\n".join(parts)


async def run(question_id: int, model: str, show_prompt: bool, save_path: str | None) -> None:
    print(f"\nFetching question {question_id} from Metaculus...")
    async with MetaculusClient() as client:
        q = await client.get_question(question_id)

    print(f"  {q.title[:80]}")
    print(f"  Type: {q.question_type}  |  Status: {q.status}")

    prompt = build_prompt(q)

    if show_prompt:
        print("\n" + "=" * 72)
        print("PROMPT")
        print("-" * 72)
        print(prompt)

    print(f"\nCalling {model}...")

    llm = LLMClient()
    response = await llm.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Low temperature: this is a reasoning/classification task
    )

    output = format_output(
        q=q,
        prompt=prompt,
        response=response.content,
        model=model,
        cost=response.cost,
        latency_ms=response.latency_ms,
    )

    print("\n" + output)

    if save_path:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Save both prompt and response when saving to file
        full_output = (
            output
            + "\n\nFULL PROMPT\n"
            + "-" * 72
            + "\n"
            + prompt
        )
        path.write_text(full_output)
        print(f"\nSaved to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Test reference class selection on a Metaculus question",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--question",
        type=int,
        required=True,
        help="Metaculus question ID (post ID from the URL)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the full prompt before sending",
    )
    parser.add_argument(
        "--save",
        metavar="PATH",
        help="Save the full output (including prompt) to a file",
    )
    args = parser.parse_args()

    asyncio.run(
        run(
            question_id=args.question,
            model=args.model,
            show_prompt=args.show_prompt,
            save_path=args.save,
        )
    )


if __name__ == "__main__":
    main()
