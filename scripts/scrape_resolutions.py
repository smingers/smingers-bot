#!/usr/bin/env python3
"""
Scrape question resolutions from Metaculus in a browser.

Use when the API no longer returns resolution values (Metaculus locked down
their API in Feb 2026 — the resolution field now returns null). This script
opens each question page in a real browser and extracts the resolution from
the "Resolved" badge that Metaculus still renders in the UI.

Targets two categories of questions:
  1. Questions marked resolved=true but with resolution=null (API returned
     scores but not the actual outcome)
  2. Questions not yet marked resolved (newly resolved since last update)

Requires Playwright with Chromium:
    poetry add -G dev playwright
    poetry run playwright install chromium

Note: Cloudflare blocks headless browsers on Metaculus. This script launches
a visible (headed) browser so Cloudflare's JS challenge can pass. You may
need to solve a CAPTCHA on the first page load.

Usage:
    poetry run python scripts/scrape_resolutions.py                              # defaults to minibench
    poetry run python scripts/scrape_resolutions.py --tracking-file data/tracking/32916.json
"""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_TRACKING_FILE = Path("data/tracking/minibench.json")
BASE_URL = "https://www.metaculus.com/questions"


def get_questions_needing_resolution(tracking_file: Path) -> tuple[dict, list[tuple[int, str]]]:
    """Find questions that are resolved but missing a resolution value,
    or questions that haven't been marked resolved yet (may have resolved
    since the last API update).

    Returns (tracking_data, list_of_(question_id, question_type) tuples).
    """
    with open(tracking_file) as f:
        data = json.load(f)
    questions = [
        (f["question_id"], f["question_type"])
        for f in data["forecasts"]
        if f.get("resolution") is None  # covers both resolved=true/null and unresolved
    ]
    return data, questions


def extract_resolution_from_page(page) -> str | None:
    """Extract resolution value from the Metaculus question page DOM.

    Looks for the "Resolved" label element and reads the sibling element
    that contains the outcome (Yes/No for binary, option name for MC,
    numeric value for numeric questions).
    """
    return page.evaluate("""
        () => {
            const elems = document.querySelectorAll('span, div, p, h2, h3');
            for (const el of elems) {
                if (/^Resolved$/i.test(el.textContent.trim())) {
                    const parent = el.parentElement;
                    if (parent) {
                        for (const sib of parent.children) {
                            const t = sib.textContent.trim();
                            if (sib !== el && t && t !== 'Resolved') return t;
                        }
                    }
                }
            }
            return null;
        }
    """)


def parse_resolution_value(raw: str, question_type: str) -> str | float | None:
    """Convert raw resolution text to the appropriate type.

    Binary questions resolve to "Yes" or "No".
    Multiple choice questions resolve to the option name (e.g. "Doesn't change").
    Numeric questions resolve to a float (strip unit suffixes like "Index").
    """
    if not raw:
        return None

    if question_type == "binary":
        if raw in ("Yes", "No"):
            return raw
        return None

    if question_type == "multiple_choice":
        # Return as-is — the option name (e.g. "Increases", "Decreases", "Doesn't change")
        return raw

    if question_type in ("numeric", "date", "discrete"):
        # Strip unit suffixes: "117.5216 Index Jan 2006=100" -> 117.5216
        # Also handles "1880.37 Index", "11 Percent", and plain numbers
        m = re.match(r"([\d,]+(?:\.\d+)?)", raw.replace(",", ""))
        if m:
            return float(m.group(1))
        return None

    return raw


def scrape_with_playwright(questions: list[tuple[int, str]]) -> dict[int, dict]:
    """Open each question page in a headed browser and extract resolutions.

    Uses a headed (visible) browser because Cloudflare blocks headless
    requests to Metaculus. The browser stays open so any CAPTCHA challenges
    can be solved manually on the first page load.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as err:
        print(
            "Install playwright: poetry add -G dev playwright && poetry run playwright install chromium"
        )
        raise SystemExit(1) from err

    results = {}
    with sync_playwright() as p:
        # headed=True to avoid Cloudflare blocks
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        for i, (qid, qtype) in enumerate(questions):
            url = f"{BASE_URL}/{qid}/"
            print(f"  [{i + 1}/{len(questions)}] {qid} ({qtype})...", end=" ", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait for JS to render the resolution badge
                page.wait_for_timeout(5000)

                # Dismiss any modal (FutureEval popup, cookie banner, etc.)
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                except Exception:
                    pass

                raw = extract_resolution_from_page(page)
                resolution = parse_resolution_value(raw, qtype) if raw else None

                if resolution is not None:
                    results[qid] = {"resolution": resolution}
                    print(f"-> {resolution}")
                else:
                    print(f"-> (not found, raw={raw!r})")
            except Exception as e:
                print(f"-> error: {e}")
            page.wait_for_timeout(800)

        context.close()
        browser.close()

    return results


def merge_into_tracking(tracking: dict, resolutions: dict[int, dict], tracking_file: Path):
    """Write scraped resolution values back to the tracking file."""
    updated = 0
    for fc in tracking["forecasts"]:
        qid = fc["question_id"]
        if qid not in resolutions:
            continue
        r = resolutions[qid]
        fc["resolved"] = True
        fc["resolution"] = r["resolution"]
        fc["status"] = "resolved"
        updated += 1

    tracking["last_updated"] = datetime.now(tz=UTC).isoformat()

    with open(tracking_file, "w") as f:
        json.dump(tracking, f, indent=2)

    print(f"\nUpdated {updated} forecasts in {tracking_file}")


def main():
    parser = argparse.ArgumentParser(description="Scrape resolution values from Metaculus UI")
    parser.add_argument(
        "--tracking-file",
        type=Path,
        default=DEFAULT_TRACKING_FILE,
        help=f"Path to tracking JSON file (default: {DEFAULT_TRACKING_FILE})",
    )
    args = parser.parse_args()

    tracking, questions = get_questions_needing_resolution(args.tracking_file)
    if not questions:
        print("All questions already have resolution values.")
        return
    print(f"Scraping resolution for {len(questions)} questions from {args.tracking_file}...")
    results = scrape_with_playwright(questions)
    if results:
        merge_into_tracking(tracking, results, args.tracking_file)
    else:
        print("No resolutions extracted.")


if __name__ == "__main__":
    main()
