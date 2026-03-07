#!/usr/bin/env python3
"""
Analyze forecaster_*_inside_view.md files: compare probability before vs after
the Checklist / Probability Checklist. Reports how often the LLM changes its forecast.
"""

import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

# Patterns for a stated probability (label: number%). Capture group 1 = number.
# Allow bold ** around number and ~ for "~55%"
INITIAL_PATTERNS = [
    re.compile(
        r"(?:Inside view|Final estimate|My probability|Probability)\s*:\s*\*?\s*~?\s*(\d+(?:\.\d+)?)\s*%",
        re.I,
    ),
    re.compile(
        r"\*\*(?:Inside view|Final estimate|My probability|Probability)\s*:\s*(\d+(?:\.\d+)?)\s*%\*\*",
        re.I,
    ),
    re.compile(r"(?:probability|estimate)\s+at\s+\*?\*?(\d+(?:\.\d+)?)\s*%\*?\*?", re.I),
]
# Final line is typically "Probability: X%" at end of file
FINAL_PATTERN = re.compile(r"Probability\s*:\s*\*?\s*(\d+(?:\.\d+)?)\s*%", re.I)


def parse_prob(s: str) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def extract_probs_from_text(text: str) -> list[tuple[float, int]]:
    """Extract (probability, position) from text. position = char index for ordering."""
    out = []
    for pat in INITIAL_PATTERNS:
        for m in pat.finditer(text):
            p = parse_prob(m.group(1))
            if p is not None and 0 <= p <= 100:
                out.append((p, m.start()))
    for m in FINAL_PATTERN.finditer(text):
        p = parse_prob(m.group(1))
        if p is not None and 0 <= p <= 100:
            out.append((p, m.start()))
    return sorted(out, key=lambda x: x[1])


def get_initial_and_final(content: str) -> tuple[float | None, float | None]:
    """Return (initial_prob, final_prob). Initial = last stated prob before Checklist; final = last Probability: X% in file."""
    checklist_markers = ["Checklist", "Probability Checklist", "**Checklist**"]
    split_pos = None
    for marker in checklist_markers:
        idx = content.find(marker)
        if idx != -1:
            split_pos = idx
            break
    if split_pos is None:
        # No checklist: take last Probability: X% as both initial and final
        finals = [m.group(1) for m in FINAL_PATTERN.finditer(content)]
        if finals:
            p = parse_prob(finals[-1])
            if p is not None:
                return (p, p)
        all_p = extract_probs_from_text(content)
        if all_p:
            return (all_p[-1][0], all_p[-1][0])
        return (None, None)

    before = content[:split_pos]

    # Initial: last probability stated BEFORE checklist (any of our patterns)
    before_matches = []
    for pat in INITIAL_PATTERNS:
        before_matches.extend(pat.finditer(before))
    before_matches.extend(FINAL_PATTERN.finditer(before))
    before_matches.sort(key=lambda m: m.start())
    initial = None
    for m in before_matches:
        g = m.group(1)
        p = parse_prob(g)
        if p is not None and 0 <= p <= 100:
            initial = p

    # Final: last "Probability: X%" in entire file
    final_matches = list(FINAL_PATTERN.finditer(content))
    final = parse_prob(final_matches[-1].group(1)) if final_matches else None

    if initial is None and final is not None:
        all_before = extract_probs_from_text(before)
        if all_before:
            initial = all_before[-1][0]
    if final is None and initial is not None:
        final = initial

    return (initial, final)


def main():
    files = sorted(DATA.glob("**/ensemble/forecaster_*_inside_view.md"))
    # Restrict to binary-style (we're looking for single probability); numeric/mc may have different format
    # Actually user said "forecast number" and example is % - we'll parse all and skip when we can't get two numbers

    results: list[
        tuple[str, int, float | None, float | None, str]
    ] = []  # path, forecaster_id, initial, final, status
    by_forecaster: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    same_count = 0
    diff_count = 0
    single_or_parse_fail = 0
    tol = 0.02  # treat as same if within 0.02 (e.g. 65 vs 65.0)

    for path in files:
        rel = path.relative_to(DATA)
        forecaster_num = int(path.stem.replace("forecaster_", "").replace("_inside_view", ""))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            results.append((str(rel), forecaster_num, None, None, f"read_error:{e}"))
            single_or_parse_fail += 1
            continue

        initial, final = get_initial_and_final(content)
        if initial is None or final is None:
            results.append((str(rel), forecaster_num, initial, final, "no_match"))
            single_or_parse_fail += 1
            continue
        if abs(initial - final) <= tol:
            same_count += 1
            status = "same"
            by_forecaster[forecaster_num].append(str(rel))
        else:
            diff_count += 1
            status = "different"
            by_forecaster[forecaster_num].append(str(rel))
        results.append((str(rel), forecaster_num, initial, final, status))

    # Summary
    print("=== Checklist: initial vs final probability ===\n")
    print(f"Total files parsed: {len(files)}")
    print(f"Same (initial == final): {same_count}")
    print(f"Different (checklist changed forecast): {diff_count}")
    print(f"No match / single number / parse fail: {single_or_parse_fail}")
    if same_count + diff_count:
        pct_diff = 100.0 * diff_count / (same_count + diff_count)
        print(f"\n% where checklist changed the forecast: {pct_diff:.1f}%")

    # Per forecaster (1+2 = Sonnet, 3 = GPT, 4+5 = o3)
    print("\n--- Per forecaster ---")
    for f in [1, 2, 3, 4, 5]:
        subs = [r for r in results if r[1] == f and r[4] in ("same", "different")]
        s = sum(1 for r in subs if r[4] == "same")
        d = sum(1 for r in subs if r[4] == "different")
        print(f"Forecaster {f}: same={s}, different={d} (total with pair={s + d})")
    print("\n--- By model group (1+2, 3, 4+5) ---")
    for name, ids in [("F1+F2 (Sonnet)", (1, 2)), ("F3 (GPT)", (3,)), ("F4+F5 (o3)", (4, 5))]:
        subs = [r for r in results if r[1] in ids and r[4] in ("same", "different")]
        s = sum(1 for r in subs if r[4] == "same")
        d = sum(1 for r in subs if r[4] == "different")
        print(f"{name}: same={s}, different={d}")

    # List files where different
    diffs = [r for r in results if r[4] == "different"]
    if diffs:
        print("\n--- Files where initial != final ---")
        for rel, fid, ini, fin, _ in diffs:
            print(f"  {rel} (F{fid}): {ini}% -> {fin}%")

    # List of files analyzed (for your verification)
    analyzed = [r for r in results if r[4] in ("same", "different")]
    out_dir = Path(__file__).resolve().parents[1] / "data"
    list_path = out_dir / "checklist_analysis_files.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("# Files with both initial and final probability extracted\n")
        for rel, fid, ini, fin, status in analyzed:
            f.write(f"{rel}\tF{fid}\t{ini}\t{fin}\t{status}\n")
    print(f"\n--- Full list of {len(analyzed)} analyzed files written to: {list_path} ---")
    print("Sample (first 30):")
    for rel, fid, ini, fin, status in analyzed[:30]:
        print(f"  {rel} F{fid} {ini}% {fin}% {status}")
    if len(analyzed) > 30:
        print(f"  ... and {len(analyzed) - 30} more in checklist_analysis_files.txt")


if __name__ == "__main__":
    main()
