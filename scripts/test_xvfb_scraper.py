#!/usr/bin/env python3
"""
Prototype: Test Xvfb + Playwright scraping of Metaculus community predictions.

Tests whether Playwright headless=False + Xvfb (virtual framebuffer) can
bypass Cloudflare and reliably extract community prediction data from
Metaculus question pages. This determines if the approach is viable for
autonomous use in GitHub Actions CI.

All test questions are binary (the only type underlying community-prediction
meta-questions in MiniBench). The script extracts P(Yes) from each.

Usage:
    # Local (headed browser, requires display)
    poetry run python scripts/test_xvfb_scraper.py --no-xvfb

    # With Xvfb (headless Linux / CI)
    poetry run python scripts/test_xvfb_scraper.py --xvfb

    # Auto-detect: uses existing DISPLAY if set, otherwise launches Xvfb
    poetry run python scripts/test_xvfb_scraper.py

    # Via xvfb-run (alternative to --xvfb)
    xvfb-run poetry run python scripts/test_xvfb_scraper.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

# Import shared scraping utilities from the production module
from src.scraping.community_prediction import (
    BASE_URL,
    BROWSER_ARGS,
    JS_EXTRACTOR,  # noqa: F401 — imported for reference, used via extract_community_data
    USER_AGENT,
    check_cloudflare_block,
    extract_community_data,
    parse_p_yes,
    start_xvfb,
    stop_xvfb,
)

# ---------------------------------------------------------------------------
# Test questions: actual underlying questions referenced by MiniBench
# community-prediction meta-questions. All binary.
# ---------------------------------------------------------------------------


@dataclass
class TestQuestion:
    question_id: int
    description: str


TEST_QUESTIONS: list[TestQuestion] = [
    TestQuestion(41072, "Will the composition of the US Supreme Court change in 2026?"),
    TestQuestion(
        41502, "Will the US gain formal sovereignty over any part of Greenland during 2026?"
    ),
    TestQuestion(41594, "Will the United States attack Iran before April 2026?"),
    TestQuestion(40972, "Will Nvidia stock price close below $100 on any day in 2026?"),
    TestQuestion(41141, "Will OpenAI file for an IPO during 2026?"),
    TestQuestion(40965, "Will GTA VI be released during 2026?"),
    TestQuestion(41508, "Will the Community beat Nathan Young in the Metaculus Cup Spring 2026?"),
    TestQuestion(
        41138, "Will there be a bilateral ceasefire in the Russo-Ukrainian conflict before 2027?"
    ),
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ScrapeResult:
    question_id: int
    description: str

    # Timing
    load_time_s: float = 0.0
    extract_time_s: float = 0.0
    total_time_s: float = 0.0

    # Status
    success: bool = False
    cloudflare_blocked: bool = False
    error: str | None = None

    # Raw extractor output
    raw_output: dict = field(default_factory=dict)

    # Parsed fields
    detected_type: str | None = None
    community_p_yes: float | None = None
    forecaster_count: int | None = None
    resolution: str | None = None

    # History and trend
    history_length: int | None = None
    week_delta: float | None = None
    two_week_delta: float | None = None
    month_delta: float | None = None
    history_min: float | None = None
    history_max: float | None = None


# ---------------------------------------------------------------------------
# Display mode detection
# ---------------------------------------------------------------------------


def detect_display_mode(force_xvfb: bool, force_no_xvfb: bool) -> str:
    """Determine display mode.

    Returns: "xvfb_internal" | "headed" | "xvfb_external"
    """
    if force_xvfb:
        return "xvfb_internal"
    if force_no_xvfb:
        return "headed"
    # Auto-detect
    display = os.environ.get("DISPLAY", "")
    if display:
        return "headed"  # or xvfb_external if someone ran xvfb-run
    return "xvfb_internal"


# ---------------------------------------------------------------------------
# Per-question scraping
# ---------------------------------------------------------------------------


def scrape_question(page, question: TestQuestion, wait_seconds: float) -> ScrapeResult:
    """Scrape a single question page and return structured results."""
    result = ScrapeResult(
        question_id=question.question_id,
        description=question.description,
    )

    t_start = time.monotonic()

    try:
        url = f"{BASE_URL}/{question.question_id}/"
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        t_loaded = time.monotonic()
        result.load_time_s = t_loaded - t_start

        # Wait for JS hydration
        page.wait_for_timeout(int(wait_seconds * 1000))

        # Dismiss modals
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass

        # Check for Cloudflare
        if check_cloudflare_block(page):
            result.cloudflare_blocked = True
            result.error = "Cloudflare challenge detected"
            result.total_time_s = time.monotonic() - t_start
            return result

        # Run extractor
        t_extract_start = time.monotonic()
        data = extract_community_data(page)
        result.extract_time_s = time.monotonic() - t_extract_start
        result.raw_output = data

        # Parse fields
        result.detected_type = data.get("type")
        result.community_p_yes = parse_p_yes(data)
        result.forecaster_count = data.get("fc")
        result.resolution = data.get("res")

        # Trend data
        result.history_length = data.get("history_length")
        result.week_delta = data.get("week_delta")
        result.two_week_delta = data.get("two_week_delta")
        result.month_delta = data.get("month_delta")
        result.history_min = data.get("history_min")
        result.history_max = data.get("history_max")

        # Determine success
        result.success = result.detected_type == "binary" and result.community_p_yes is not None

    except Exception as e:
        result.error = str(e)

    result.total_time_s = time.monotonic() - t_start
    return result


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------


def run_all_tests(
    display_mode: str,
    questions: list[TestQuestion],
    wait_seconds: float,
    inter_request_delay: float,
) -> list[ScrapeResult]:
    """Run the full scraping test suite."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright not installed.")
        print("  Install: poetry add -G dev playwright && poetry run playwright install chromium")
        sys.exit(1)

    xvfb_proc = None
    if display_mode == "xvfb_internal":
        print("  Launching Xvfb...")
        try:
            xvfb_proc = start_xvfb()
        except RuntimeError as e:
            print(f"ERROR: {e}")
            print("  Install Xvfb: sudo apt-get install -y xvfb")
            sys.exit(1)

    results: list[ScrapeResult] = []

    try:
        with sync_playwright() as p:
            print("  Launching Chromium (headless=False)...")
            browser = p.chromium.launch(
                headless=False,
                args=BROWSER_ARGS,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=USER_AGENT,
            )
            page = context.new_page()

            for i, question in enumerate(questions):
                print(
                    f"\n  [{i + 1}/{len(questions)}] Q{question.question_id}: {question.description}"
                )

                result = scrape_question(page, question, wait_seconds)

                # If first question was Cloudflare-blocked, retry once after a wait
                if result.cloudflare_blocked and i == 0:
                    print("    Cloudflare block on first page — waiting 10s and retrying...")
                    page.wait_for_timeout(10_000)
                    result = scrape_question(page, question, wait_seconds)

                results.append(result)

                # Print inline status
                if result.success:
                    trend_str = ""
                    if result.week_delta is not None:
                        trend_str = f", 7d Δ={result.week_delta:+.3f}"
                    print(
                        f"    SUCCESS — P(Yes)={result.community_p_yes:.4f}, "
                        f"forecasters={result.forecaster_count}, "
                        f"history={result.history_length} pts"
                        f"{trend_str}, time={result.total_time_s:.1f}s"
                    )
                elif result.cloudflare_blocked:
                    print(f"    BLOCKED — Cloudflare challenge, time={result.total_time_s:.1f}s")
                else:
                    print(
                        f"    FAILED — {result.error or 'unknown'}, "
                        f"type={result.detected_type}, "
                        f"p_yes={result.community_p_yes}, "
                        f"time={result.total_time_s:.1f}s"
                    )

                # Inter-request delay (skip after last question)
                if i < len(questions) - 1:
                    time.sleep(inter_request_delay)

            context.close()
            browser.close()

    finally:
        if xvfb_proc is not None:
            print("\n  Stopping Xvfb...")
            stop_xvfb(xvfb_proc)

    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def print_report(results: list[ScrapeResult], display_mode: str) -> bool:
    """Print structured report. Returns True if overall verdict is PASS."""
    total = len(results)
    succeeded = sum(1 for r in results if r.success)
    cf_blocked = sum(1 for r in results if r.cloudflare_blocked)
    errors = sum(1 for r in results if not r.success and not r.cloudflare_blocked)
    avg_time = sum(r.total_time_s for r in results) / total if total else 0
    total_time = sum(r.total_time_s for r in results)

    # Field availability
    has_type = sum(1 for r in results if r.detected_type)
    has_p_yes = sum(1 for r in results if r.community_p_yes is not None)
    has_fc = sum(1 for r in results if r.forecaster_count is not None)
    has_res = sum(1 for r in results if r.resolution is not None)

    print("\n")
    print("=" * 64)
    print("XVFB + PLAYWRIGHT SCRAPER PROTOTYPE RESULTS")
    print("=" * 64)
    print(f"Display mode:  {display_mode}")
    print(f"Timestamp:     {datetime.now(tz=UTC).isoformat()}")
    print(f"Questions:     {total}")
    print()

    print("RESULTS PER QUESTION:")
    print("-" * 64)
    for i, r in enumerate(results):
        status = "SUCCESS" if r.success else ("BLOCKED" if r.cloudflare_blocked else "FAILED")
        print(f"[{i + 1}/{total}] Q{r.question_id} — {r.description}")
        print(f"  Status:           {status}")
        if r.cloudflare_blocked:
            print("  Cloudflare:       BLOCKED")
        if r.error and not r.cloudflare_blocked:
            print(f"  Error:            {r.error}")
        if r.detected_type:
            print(f"  Type detected:    {r.detected_type}")
        if r.community_p_yes is not None:
            print(f"  Community P(Yes): {r.community_p_yes:.4f} ({r.community_p_yes * 100:.1f}%)")
        if r.forecaster_count is not None:
            print(f"  Forecaster count: {r.forecaster_count}")
        if r.history_length is not None:
            print(f"  History:          {r.history_length} data points")
            if r.history_min is not None:
                print(f"  Range:            {r.history_min:.2f} — {r.history_max:.2f}")
            if r.week_delta is not None:
                print(f"  7-day change:     {r.week_delta:+.4f} ({r.week_delta * 100:+.1f}pp)")
            if r.two_week_delta is not None:
                print(
                    f"  14-day change:    {r.two_week_delta:+.4f} ({r.two_week_delta * 100:+.1f}pp)"
                )
            if r.month_delta is not None:
                print(f"  30-day change:    {r.month_delta:+.4f} ({r.month_delta * 100:+.1f}pp)")
        if r.resolution:
            print(f"  Resolution:       {r.resolution}")
        print(
            f"  Timing:           load={r.load_time_s:.1f}s, extract={r.extract_time_s:.2f}s, total={r.total_time_s:.1f}s"
        )
        print()

    print("SUMMARY:")
    print("-" * 64)
    print(f"  Successful:       {succeeded}/{total} ({succeeded / total * 100:.0f}%)")
    print(f"  Cloudflare blocked: {cf_blocked}")
    print(f"  Errors:           {errors}")
    print(f"  Avg time/question: {avg_time:.1f}s")
    print(f"  Total wall time:  {total_time:.1f}s")
    print()

    print("FIELD AVAILABILITY:")
    print(f"  type:             {has_type}/{total}")
    print(f"  community P(Yes): {has_p_yes}/{total}")
    print(f"  forecaster_count: {has_fc}/{total}")
    print(f"  resolution:       {has_res}/{total}")
    print()

    # Verdict
    passed = succeeded >= 6 and cf_blocked == 0
    verdict = "PASS" if passed else "FAIL"
    print(f"VERDICT: {verdict}")
    if passed:
        print(f"  {succeeded}+ questions succeeded, 0 Cloudflare blocks.")
        print("  Xvfb + headless=False appears viable for CI.")
    else:
        if cf_blocked > 0:
            print(f"  {cf_blocked} Cloudflare blocks detected.")
            print("  Consider: playwright-stealth, patchright, or persistent cookies.")
        if succeeded < 6:
            print(f"  Only {succeeded}/8 succeeded (need ≥6).")
            print("  Check raw_output in failed results for diagnostics.")
    print("=" * 64)

    # Dump raw output for failed questions
    failed = [r for r in results if not r.success]
    if failed:
        print("\nDIAGNOSTICS (failed questions):")
        print("-" * 64)
        for r in failed:
            print(f"Q{r.question_id}: raw_output = {json.dumps(r.raw_output, indent=2)}")
            print()

    # Always dump first question's raw output for sanity checking
    if results:
        print("\nRAW EXTRACTOR OUTPUT (first question, for sanity check):")
        print("-" * 64)
        print(f"Q{results[0].question_id}: {json.dumps(results[0].raw_output, indent=2)}")
        print()

    return passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Test Xvfb + Playwright scraping of Metaculus community predictions"
    )
    parser.add_argument(
        "--xvfb",
        action="store_true",
        help="Force Xvfb usage (launches Xvfb internally)",
    )
    parser.add_argument(
        "--no-xvfb",
        action="store_true",
        help="Force headed mode (requires a display server)",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=5.0,
        help="Seconds to wait for JS hydration per page (default: 5.0)",
    )
    parser.add_argument(
        "--inter-request-delay",
        type=float,
        default=1.5,
        help="Seconds between requests (default: 1.5)",
    )
    args = parser.parse_args()

    if args.xvfb and args.no_xvfb:
        print("ERROR: --xvfb and --no-xvfb are mutually exclusive")
        sys.exit(1)

    display_mode = detect_display_mode(args.xvfb, args.no_xvfb)
    print(f"Display mode: {display_mode}")
    print(f"Test questions: {len(TEST_QUESTIONS)}")
    print(f"JS wait: {args.wait_seconds}s, inter-request delay: {args.inter_request_delay}s")

    results = run_all_tests(
        display_mode=display_mode,
        questions=TEST_QUESTIONS,
        wait_seconds=args.wait_seconds,
        inter_request_delay=args.inter_request_delay,
    )

    passed = print_report(results, display_mode)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
