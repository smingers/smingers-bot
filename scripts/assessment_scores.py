#!/usr/bin/env python3
"""Parse assessment files and generate model performance analysis tables.

Extracts Outside View (S1) and Inside View (S2) scores per forecaster from
all assessment markdown files, then outputs aggregate tables by model and
question type.

Usage:
    poetry run python scripts/assessment_scores.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ASSESSMENTS_DIR = Path(__file__).parent.parent / "docs" / "assessments"

# Cross-pollination structure (fixed by pipeline design):
# S2-1 receives S1-1 (same model)
# S2-2 receives S1-4 (cross model)
# S2-3 receives S1-2 (cross model)
# S2-4 receives S1-3 (cross model)
# S2-5 receives S1-5 (same model)
CROSS_POLLINATION = {
    1: 1,  # S2-1 <- S1-1
    2: 4,  # S2-2 <- S1-4
    3: 2,  # S2-3 <- S1-2
    4: 3,  # S2-4 <- S1-3
    5: 5,  # S2-5 <- S1-5
}


def normalize_model(name: str) -> str:
    """Normalize model name to canonical form."""
    name = name.strip()
    if name.lower() == "gpt-5.2":
        return "GPT-5.2"
    if name.lower() == "haiku":
        return "Haiku"
    if name.lower() == "o3-mini":
        return "o3-mini"
    if name.lower() == "o3":
        return "o3"
    # Sonnet variants — preserve version
    m = re.match(r"(?:Claude\s+)?Sonnet\s+(4\.\d+)", name, re.IGNORECASE)
    if m:
        return f"Sonnet {m.group(1)}"
    return name


def parse_question_type(text: str) -> str | None:
    """Extract base question type from assessment text."""
    m = re.search(r"\*\*Question Type:\*\*\s+(\w+)", text)
    if m:
        return m.group(1)
    return None


def _parse_detailed_sections(section: str, stage: str) -> list[dict]:
    """Parse scores from detailed #### subsections."""
    results = []

    # Pattern 1: #### Step N Output M (Model)
    # Pattern 2: #### S2-N (Model, receives S1-M) or #### S2-N (Model): receives S1-M
    header_patterns = [
        re.compile(r"####\s+Step\s+[12]\s+Output\s+(\d+)\s+\(([^)]+)\)"),
        re.compile(r"####\s+S[12]-(\d+)\s+\(([^,)]+)"),
    ]
    score_pattern = re.compile(r"\*\*Score:\*\*\s+(\d+)/16")

    headers = []
    for pattern in header_patterns:
        headers.extend(pattern.finditer(section))

    # Sort by position in text and deduplicate by output_num
    headers.sort(key=lambda m: m.start())
    seen_nums = set()
    unique_headers = []
    for h in headers:
        num = int(h.group(1))
        if num not in seen_nums:
            seen_nums.add(num)
            unique_headers.append(h)
    headers = unique_headers

    for i, header in enumerate(headers):
        output_num = int(header.group(1))
        model = normalize_model(header.group(2))

        start = header.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(section)
        subsection = section[start:end]

        score_match = score_pattern.search(subsection)
        if score_match:
            score = int(score_match.group(1))
            results.append(
                {
                    "stage": stage,
                    "output_num": output_num,
                    "model": model,
                    "score": score,
                }
            )

    return results


def _parse_summary_table(section: str, stage: str) -> list[dict]:
    """Parse scores from compact summary tables.

    Handles rows like:
        | S1-1 | Sonnet 4.5 | 38% | ... | 13/16 |
        | F1 | Sonnet 4.5 | 64% | 15/16 | ... |
    """
    results = []
    # Match table rows that contain a score in X/16 format
    row_pattern = re.compile(
        r"\|\s*(?:S[12]-|F)(\d+)\s*\|\s*(?:Claude\s+)?([^|]+?)\s*\|"
        r"(.*?)"
        r"(\d+)/16"
        r"(.*?)\|",
    )
    for m in row_pattern.finditer(section):
        output_num = int(m.group(1))
        model = normalize_model(m.group(2))
        score = int(m.group(4))
        results.append(
            {
                "stage": stage,
                "output_num": output_num,
                "model": model,
                "score": score,
            }
        )
    return results


def parse_scores(text: str):
    """Extract S1 and S2 scores with model labels from assessment text.

    Tries detailed #### subsections first, falls back to summary table parsing.

    Returns:
        list of dicts with keys: stage, output_num, model, score
    """
    results = []

    # Split into S1 and S2 sections
    s1_match = re.search(
        r"##\s+\d+\.\s+Step 1\s*\(Outside View\)\s*Analysis(.*?)(?=##\s+\d+\.\s+Step 2)",
        text,
        re.DOTALL,
    )
    s2_match = re.search(
        r"##\s+\d+\.\s+Step 2\s*\(Inside View\)\s*Analysis(.*?)(?=##\s+\d+\.\s+(?:Cross-Pollination|Factual|Overall|Supervisor))",
        text,
        re.DOTALL,
    )

    for stage, section_match in [("S1", s1_match), ("S2", s2_match)]:
        if not section_match:
            continue
        section = section_match.group(1)

        # Try detailed subsections first
        stage_results = _parse_detailed_sections(section, stage)

        # Fall back to summary table parsing
        if not stage_results:
            stage_results = _parse_summary_table(section, stage)

        results.extend(stage_results)

    return results


def parse_assessment(filepath: Path) -> dict | None:
    """Parse a single assessment file."""
    text = filepath.read_text()
    question_type = parse_question_type(text)
    if not question_type:
        return None

    scores = parse_scores(text)
    if not scores:
        return None

    # Extract question ID from filename
    m = re.match(r"(\d+)_", filepath.name)
    question_id = int(m.group(1)) if m else None

    return {
        "file": filepath.name,
        "question_id": question_id,
        "question_type": question_type,
        "scores": scores,
    }


def build_tables(assessments: list[dict]) -> str:
    """Generate markdown tables from parsed assessments."""
    lines = []

    # Collect all scores by model and stage
    s1_by_model: dict[str, list[int]] = defaultdict(list)
    s2_by_model: dict[str, list[int]] = defaultdict(list)
    s1_by_model_type: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    s2_by_model_type: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    # Cross-pollination: keyed by (s1_model, s2_model, forecaster_pair_label)
    cross_poll: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    question_type_counts: dict[str, int] = defaultdict(int)
    seen_questions: set[str] = set()

    for assessment in assessments:
        qtype = assessment["question_type"]
        file_key = assessment["file"]

        # Count unique assessments (not unique questions, since some have multiple runs)
        if file_key not in seen_questions:
            seen_questions.add(file_key)
            question_type_counts[qtype] += 1

        # Index scores by output_num for cross-pollination lookup
        s1_models = {}
        s2_entries = []
        for entry in assessment["scores"]:
            if entry["stage"] == "S1":
                s1_by_model[entry["model"]].append(entry["score"])
                s1_by_model_type[entry["model"]][qtype].append(entry["score"])
                s1_models[entry["output_num"]] = entry["model"]
            else:
                s2_by_model[entry["model"]].append(entry["score"])
                s2_by_model_type[entry["model"]][qtype].append(entry["score"])
                s2_entries.append(entry)

        # Cross-pollination analysis
        for entry in s2_entries:
            s2_num = entry["output_num"]
            s1_num = CROSS_POLLINATION.get(s2_num)
            if s1_num and s1_num in s1_models:
                s1_model = s1_models[s1_num]
                s2_model = entry["model"]
                pair_label = f"S1-{s1_num} → S2-{s2_num}"
                cross_poll[(s1_model, s2_model, pair_label)].append(entry["score"])

    # Determine model display order
    model_order = []
    for m in ["Sonnet 4.5", "Sonnet 4.6", "Haiku", "GPT-5.2", "o3-mini", "o3"]:
        if m in s1_by_model or m in s2_by_model:
            model_order.append(m)
    # Add any remaining models not in the predefined order
    for m in sorted(set(s1_by_model) | set(s2_by_model)):
        if m not in model_order:
            model_order.append(m)

    total_assessments = len(seen_questions)

    # --- Header ---
    lines.append("## Model Performance Analysis")
    lines.append("")
    lines.append(f"*Based on {total_assessments} assessed forecasts.*")
    lines.append("")

    # --- Outside View Scores ---
    lines.append("### Outside View Scores")
    lines.append("")
    lines.append("| Model | Avg Score | N |")
    lines.append("|-------|----------|---|")
    for m in model_order:
        scores = s1_by_model.get(m, [])
        if scores:
            avg = mean(scores)
            lines.append(f"| {m} | {avg:.1f} / 16 | {len(scores)} |")
    lines.append("")

    # --- Inside View Scores ---
    lines.append("### Inside View Scores")
    lines.append("")
    lines.append("| Model | Avg Score | N |")
    lines.append("|-------|----------|---|")
    for m in model_order:
        scores = s2_by_model.get(m, [])
        if scores:
            avg = mean(scores)
            lines.append(f"| {m} | {avg:.1f} / 16 | {len(scores)} |")
    lines.append("")

    # --- Outside View by Question Type ---
    qtypes_sorted = sorted(question_type_counts.keys())
    qtype_headers = [f"{qt} ({question_type_counts[qt]})" for qt in qtypes_sorted]

    lines.append("### Outside View Scores by Question Type")
    lines.append("")
    lines.append("| Model | " + " | ".join(qtype_headers) + " |")
    lines.append("|-------" + "|---" * len(qtypes_sorted) + "|")
    for m in model_order:
        cells = []
        for qt in qtypes_sorted:
            scores = s1_by_model_type.get(m, {}).get(qt, [])
            if scores:
                cells.append(f"{mean(scores):.1f}")
            else:
                cells.append("—")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Inside View by Question Type ---
    lines.append("### Inside View Scores by Question Type")
    lines.append("")
    lines.append("| Model | " + " | ".join(qtype_headers) + " |")
    lines.append("|-------" + "|---" * len(qtypes_sorted) + "|")
    for m in model_order:
        cells = []
        for qt in qtypes_sorted:
            scores = s2_by_model_type.get(m, {}).get(qt, [])
            if scores:
                cells.append(f"{mean(scores):.1f}")
            else:
                cells.append("—")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Score Distribution: Outside View ---
    lines.append("### Score Distribution — Outside View")
    lines.append("")
    score_cols = list(range(16, 6, -1)) + ["≤6"]
    lines.append("| Model | " + " | ".join(str(s) for s in score_cols) + " |")
    lines.append("|-------" + "|---" * len(score_cols) + "|")
    for m in model_order:
        scores = s1_by_model.get(m, [])
        counts = defaultdict(int)
        for s in scores:
            if s <= 6:
                counts["≤6"] += 1
            else:
                counts[s] += 1
        cells = [str(counts.get(c, 0)) for c in score_cols]
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Score Distribution: Inside View ---
    lines.append("### Score Distribution — Inside View")
    lines.append("")
    lines.append("| Model | " + " | ".join(str(s) for s in score_cols) + " |")
    lines.append("|-------" + "|---" * len(score_cols) + "|")
    for m in model_order:
        scores = s2_by_model.get(m, [])
        counts = defaultdict(int)
        for s in scores:
            if s <= 6:
                counts["≤6"] += 1
            else:
                counts[s] += 1
        cells = [str(counts.get(c, 0)) for c in score_cols]
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Cross-Pollination ---
    lines.append("### Cross-Pollination: Inside View Scores by S1→S2 Pairing")
    lines.append("")
    lines.append(
        "Each row shows the average Inside View (S2) score for a specific "
        "Outside View → Inside View model combination."
    )
    lines.append("")
    lines.append(
        "| S1 Model (Outside View) | S2 Model (Inside View) | Forecaster Pair | Avg S2 Score | N |"
    )
    lines.append("|---|---|---|---|---|")

    # Sort cross-pollination entries by pair label
    sorted_pairs = sorted(cross_poll.keys(), key=lambda x: x[2])
    for s1_model, s2_model, pair_label in sorted_pairs:
        scores = cross_poll[(s1_model, s2_model, pair_label)]
        avg = mean(scores)
        lines.append(f"| {s1_model} | {s2_model} | {pair_label} | {avg:.1f} / 16 | {len(scores)} |")
    lines.append("")

    return "\n".join(lines)


def main():
    assessment_files = sorted(ASSESSMENTS_DIR.glob("*_assessment.md"))
    if not assessment_files:
        print(f"No assessment files found in {ASSESSMENTS_DIR}", file=sys.stderr)
        sys.exit(1)

    assessments = []
    parse_failures = []
    for f in assessment_files:
        result = parse_assessment(f)
        if result:
            assessments.append(result)
        else:
            parse_failures.append(f.name)

    # Print summary to stderr
    print(f"Parsed {len(assessments)} / {len(assessment_files)} assessments", file=sys.stderr)
    if parse_failures:
        print(f"Failed to parse: {', '.join(parse_failures)}", file=sys.stderr)

    # Save raw data as JSON
    raw_output = ASSESSMENTS_DIR / "score_data.json"
    with open(raw_output, "w") as fp:
        json.dump(assessments, fp, indent=2)
    print(f"Raw data saved to {raw_output}", file=sys.stderr)

    # Print markdown tables to stdout
    tables = build_tables(assessments)
    print(tables)


if __name__ == "__main__":
    main()
