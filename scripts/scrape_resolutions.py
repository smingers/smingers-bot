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
    """Find questions that are resolved (per API) but missing a resolution value.

    Uses the tracking file's resolved field (from the Metaculus API), not score_data.
    The API can return score_data for unresolved questions (e.g. zeros), so we must
    require resolved is True. Only then do we scrape to fill in resolution (which
    the API no longer returns).

    Returns (tracking_data, list_of_(question_id, question_type) tuples).
    """
    with open(tracking_file) as f:
        data = json.load(f)
    questions = [
        (f["question_id"], f["question_type"])
        for f in data["forecasts"]
        if f.get("resolved") is True and f.get("resolution") is None
    ]
    return data, questions


def extract_resolution_from_page(page) -> str | None:
    """Extract resolution value from the Metaculus question page DOM.

    Tries multiple strategies because layout differs by question type:
    - Numeric: page shows "Result X Points" or "RESOLVED X" (the value) but
      sidebar has "RESOLVED Feb 23, 2026" (the date). We must prefer the result value.
    - Binary: "Resolved" and "Yes"/"No" as siblings.
    - Multiple choice: resolved option name in sibling or parent text.
    """
    return page.evaluate("""
        () => {
            const trim = (s) => (s || '').trim();
            const looksLikeDate = (t) => /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2},?\\s*\\d{4}$/i.test(trim(t));
            const elems = document.querySelectorAll('span, div, p, h2, h3, td, th');
            // Strategy 0a: prefer "Result X" / "RESOLVED X" (actual result), not bare "X Points" (often community)
            for (const el of elems) {
                const text = trim(el.textContent);
                if (!text || text.length > 120) continue;
                const m = text.match(/\\b(?:Result|Resolved)\\s+([\\d.,]+)(?:\\s|$)/i);
                if (m) return m[1].trim();
            }
            // Strategy 0b: fallback "X Points" only when no Result/Resolved match; skip if near "Community"
            for (const el of elems) {
                const text = trim(el.textContent);
                if (!text || text.length > 50) continue;
                const parentText = el.parentElement ? trim(el.parentElement.textContent) : '';
                if (/Community/i.test(text) || /Community/i.test(parentText)) continue;
                const m = text.match(/^([\\d.,]+)\\s*Points?\\s*$/i);
                if (m) return m[1].trim();
            }
            for (const el of elems) {
                const text = trim(el.textContent);
                if (!text) continue;
                // Strategy 1: exact "Resolved" then first sibling (binary-style); skip if sibling is a date
                if (/^Resolved$/i.test(text)) {
                    const parent = el.parentElement;
                    if (parent) {
                        for (const sib of parent.children) {
                            const t = trim(sib.textContent);
                            if (sib !== el && t && t !== 'Resolved') {
                                if (looksLikeDate(t)) break;
                                return t;
                            }
                        }
                        const parentText = trim(parent.textContent);
                        if (parentText.length > 8 && !looksLikeDate(parentText)) {
                            const after = parentText.replace(/^Resolved\\s*:?\\s*/i, '').trim();
                            if (after && after !== parentText && !looksLikeDate(after)) return after;
                        }
                    }
                    let next = el.nextElementSibling;
                    for (let i = 0; i < 3 && next; i++, next = next.nextElementSibling) {
                        const t = trim(next.textContent);
                        if (t && t.length < 200 && !looksLikeDate(t)) return t;
                    }
                    continue;
                }
                if (/^Resolved\\s*:?\\s*.+$/i.test(text) && text.length < 150) {
                    const after = text.replace(/^Resolved\\s*:?\\s*/i, '').trim();
                    if (after && !looksLikeDate(after)) return after;
                }
            }
            return null;
        }
    """)


def _find_resolution_in_obj(obj: dict, depth: int = 0) -> str | int | float | None:
    """Recursively search a dict for resolution/outcome-like keys (e.g. in __NEXT_DATA__)."""
    if depth > 15:
        return None
    for key in ("resolution", "outcome", "resolved_value", "value", "resolved"):
        v = obj.get(key)
        if v is None:
            continue
        if isinstance(v, (str, int, float)) and (v != "" or key == "resolution"):
            return v
        if isinstance(v, dict) and depth < 10:
            found = _find_resolution_in_obj(v, depth + 1)
            if found is not None:
                return found
    for v in obj.values():
        if isinstance(v, dict) and depth < 8:
            found = _find_resolution_in_obj(v, depth + 1)
            if found is not None:
                return found
    return None


def extract_resolution_from_script(page, question_type: str) -> str | None:
    """Fallback: try to get resolution from page JSON (e.g. Next.js __NEXT_DATA__)."""
    try:
        script_json = page.evaluate("""
            () => {
                const el = document.getElementById('__NEXT_DATA__');
                if (!el || !el.textContent) return null;
                try { return JSON.parse(el.textContent); } catch (e) { return null; }
            }
        """)
        if not script_json:
            return None
        props = script_json.get("props", {}) or {}
        page_props = props.get("pageProps", {}) or {}
        found = _find_resolution_in_obj(page_props)
        if found is not None:
            return str(found).strip()
        return None
    except Exception:
        return None


def parse_resolution_value(raw: str, question_type: str) -> str | float | None:
    """Convert raw resolution text to the appropriate type.

    Binary questions resolve to "Yes" or "No".
    Multiple choice questions resolve to the option name (e.g. "Doesn't change").
    Numeric questions resolve to a float (strip unit suffixes like "Index").
    """
    if not raw:
        return None
    # Take first line and strip; DOM may return "2.48\\nIndex" or trailing whitespace
    raw = raw.split("\n")[0].strip()

    # Metaculus often shows resolution as to "value". or to "Option Name".
    if raw.startswith('to "') and (raw.endswith('".') or raw.endswith('"')):
        raw = raw[4 : (raw.rindex('"'))].strip()

    if question_type == "binary":
        lower = raw.lower()
        if lower == "yes":
            return "Yes"
        if lower == "no":
            return "No"
        return None

    if question_type == "multiple_choice":
        # Option name (e.g. "Green Party", "Doesn't change")
        return raw

    if question_type in ("numeric", "date", "discrete"):
        # Reject resolution-date text (e.g. "Feb 23, 2026") — that's when it resolved, not the value
        if re.search(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s*\d{4}\b", raw
        ):
            return None
        # Strip unit suffixes: "117.5216 Index Jan 2006=100" -> 117.5216
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
                # If DOM only gave us a date (e.g. "Feb 23, 2026") for numeric, try script for actual value
                if (
                    raw
                    and qtype in ("numeric", "date", "discrete")
                    and re.search(
                        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s*\d{4}\b",
                        raw,
                    )
                ):
                    script_raw = extract_resolution_from_script(page, qtype)
                    if script_raw:
                        raw = script_raw
                if not raw:
                    raw = extract_resolution_from_script(page, qtype)
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
        print(
            "No questions to scrape: every resolved question already has a resolution value, "
            "or there are no resolved questions missing one."
        )
        return
    print(f"Scraping resolution for {len(questions)} resolved question(s) missing resolution ...")
    results = scrape_with_playwright(questions)
    if results:
        merge_into_tracking(tracking, results, args.tracking_file)
    else:
        print("No resolutions extracted.")


if __name__ == "__main__":
    main()
