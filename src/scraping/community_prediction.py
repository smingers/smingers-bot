"""
Community Prediction Scraper

Detects "community prediction" meta-questions, parses the underlying question ID,
scrapes the current community prediction from Metaculus using Playwright + Xvfb,
and formats the data for injection into the forecasting pipeline.

Meta-questions have the form:
  "Will the community prediction be higher than X% on DATE for the Metaculus question TITLE?"

The Metaculus API no longer returns community prediction data (aggregations → null),
so browser scraping is the only path to get this data.

Uses Playwright with headless=False + Xvfb to bypass Cloudflare bot detection.
The JS extractor parses the Next.js hydration payload to extract:
- Current community P(Yes)
- Forecaster count
- Full prediction history with trend data (7/14/30-day deltas)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

BASE_URL = "https://www.metaculus.com/questions"


# ---------------------------------------------------------------------------
# Meta-question details dataclass
# ---------------------------------------------------------------------------


@dataclass
class MetaQuestionDetails:
    """Parsed details from a community-prediction meta-question."""

    underlying_post_id: int
    underlying_question_id: int | None = None
    underlying_title: str | None = None
    last_cp: float | None = None  # CP at meta-question creation
    direction: str | None = None  # "higher" or "lower"
    threshold: float | None = None  # e.g. 0.82
    target_date: str | None = None  # e.g. "2026-02-14 16:20:16"


@dataclass
class ScrapedCommunityPrediction:
    """Data scraped from a Metaculus question page."""

    p_yes: float
    forecaster_count: int | None = None
    history_length: int | None = None
    resolution: str | None = None
    trend: dict = field(default_factory=dict)  # week_delta, two_week_delta, etc.


# ---------------------------------------------------------------------------
# Detection and parsing
# ---------------------------------------------------------------------------

# Regex for the JSON payload embedded at the end of the description field
_CP_PAYLOAD_RE = re.compile(r'`(\{"format"\s*:\s*"metaculus_binary_cp_rises"[^`]+\})`')

# Regex for title pattern
_CP_TITLE_RE = re.compile(r"Will the community prediction be (higher|lower) than ([\d.]+)%")

# Regex for underlying question URL in resolution_criteria
_UNDERLYING_URL_RE = re.compile(r"\[here\]\(https://www\.metaculus\.com/questions/(\d+)\)")

# Regex for target date in resolution_criteria
_TARGET_DATE_RE = re.compile(r"on (\d{4}-\d{2}-\d{2}[\s\d:]*?) is (higher|lower)")


def is_community_prediction_question(question: Any) -> bool:
    """Check if a MetaculusQuestion is a community-prediction meta-question.

    Uses two detection methods:
    1. Description contains the JSON payload with format "metaculus_binary_cp_rises"
    2. Title matches "Will the community prediction be higher/lower than X%..."

    Args:
        question: A MetaculusQuestion object (or any object with description and title attrs)

    Returns:
        True if this is a community-prediction meta-question
    """
    description = getattr(question, "description", "") or ""
    if _CP_PAYLOAD_RE.search(description):
        return True

    title = getattr(question, "title", "") or ""
    if _CP_TITLE_RE.search(title):
        return True

    return False


def parse_meta_question_details(question: Any) -> MetaQuestionDetails | None:
    """Parse a community-prediction meta-question to extract underlying question info.

    Extracts:
    - Underlying question post_id and question_id (from JSON payload in description)
    - CP at meta-question creation time (from JSON payload)
    - Direction ("higher"/"lower") and threshold (from title)
    - Target resolution date (from resolution_criteria)

    Args:
        question: A MetaculusQuestion object

    Returns:
        MetaQuestionDetails if parsing succeeds, None otherwise
    """
    description = getattr(question, "description", "") or ""
    title = getattr(question, "title", "") or ""
    resolution_criteria = getattr(question, "resolution_criteria", "") or ""

    # Try JSON payload first (most reliable)
    payload_match = _CP_PAYLOAD_RE.search(description)
    if payload_match:
        try:
            payload = json.loads(payload_match.group(1))
            info = payload.get("info", {})
            details = MetaQuestionDetails(
                underlying_post_id=info["post_id"],
                underlying_question_id=info.get("question_id"),
                last_cp=info.get("last_cp"),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("Failed to parse CP JSON payload from description")
            # Fallback to URL regex
            url_match = _UNDERLYING_URL_RE.search(resolution_criteria)
            if url_match:
                details = MetaQuestionDetails(underlying_post_id=int(url_match.group(1)))
            else:
                return None
    else:
        # Fallback: extract from resolution_criteria URL
        url_match = _UNDERLYING_URL_RE.search(resolution_criteria)
        if url_match:
            details = MetaQuestionDetails(underlying_post_id=int(url_match.group(1)))
        else:
            return None

    # Parse underlying question title from description
    title_match = re.search(r"- Original question title: (.+)", description)
    if title_match:
        details.underlying_title = title_match.group(1).strip()

    # Parse direction and threshold from title
    direction_match = _CP_TITLE_RE.search(title)
    if direction_match:
        details.direction = direction_match.group(1)  # "higher" or "lower"
        details.threshold = float(direction_match.group(2)) / 100.0

    # Parse target date from resolution_criteria
    date_match = _TARGET_DATE_RE.search(resolution_criteria)
    if date_match:
        details.target_date = date_match.group(1).strip()

    return details


# ---------------------------------------------------------------------------
# JS extractor (extracted from test_xvfb_scraper.py prototype)
# ---------------------------------------------------------------------------

# Production extractor: finds the community prediction history in the Next.js
# hydration payload and takes the last entry from the first contiguous block.
# The payload contains a long history array of {centers, forecaster_count}
# objects (one per daily snapshot). After the history block ends (~pos 254K),
# personal forecasts follow — the 50K gap detection separates them.
JS_EXTRACTOR = r"""
() => {
    const scripts=[...document.querySelectorAll('script')];
    let d='';
    for(const s of scripts) if(s.textContent.includes('self.__next_f')) d+=s.textContent;
    const r={};
    const pt=document.body.innerText;

    // Resolution from visible page text
    const rm=pt.match(/RESOLVED\s*\n\s*(.+)/);
    r.res=rm?rm[1].trim():null;

    // Question type
    const tm=d.match(/\\?"type\\?":\\?"(binary|numeric|multiple_choice|date|discrete)\\?"/);
    r.type=tm?tm[1]:null;

    // Collect ALL centers values with their positions.
    // The community prediction history is a long run of single-value centers
    // (e.g. 0.25, 0.30, etc.) in the first ~250K of the payload.
    // We want the LAST one in this history block.
    const centersAll = [];
    const cRe = /centers\\?"\s*:\s*\[([^\]]*)\]/g;
    let m;
    while ((m = cRe.exec(d)) !== null) {
        const v = m[1].trim();
        // History entries are single float values (e.g. "0.25")
        // Skip multi-value entries (those are from related questions)
        if (v && !v.includes(',')) {
            centersAll.push({value: parseFloat(v), position: m.index});
        }
    }

    // The history block is a contiguous run of single-value centers.
    // Find the last entry in the first contiguous block (before a gap).
    // A "gap" means the position jumps by more than 50K (related questions start later).
    if (centersAll.length > 0) {
        // Find end of the first contiguous block
        let lastHistoryIdx = 0;
        for (let i = 1; i < centersAll.length; i++) {
            if (centersAll[i].position - centersAll[i-1].position > 50000) break;
            lastHistoryIdx = i;
        }
        const histLen = lastHistoryIdx + 1;
        r.centers = String(centersAll[lastHistoryIdx].value);
        r.history_length = histLen;

        // Extract trend data: last 7, 14, 30 data points
        const histValues = centersAll.slice(0, histLen).map(c => c.value);
        r.current = histValues[histValues.length - 1];
        if (histValues.length >= 7) {
            r.week_ago = histValues[histValues.length - 7];
            r.week_delta = +(r.current - r.week_ago).toFixed(4);
        }
        if (histValues.length >= 14) {
            r.two_weeks_ago = histValues[histValues.length - 14];
            r.two_week_delta = +(r.current - r.two_weeks_ago).toFixed(4);
        }
        if (histValues.length >= 30) {
            r.month_ago = histValues[histValues.length - 30];
            r.month_delta = +(r.current - r.month_ago).toFixed(4);
        }

        // Min/max/range over full history
        r.history_min = Math.min(...histValues);
        r.history_max = Math.max(...histValues);
    }

    // Similarly, find the last forecaster_count in the history block.
    const fcAll = [];
    const fcRe = /forecaster_count\\?"\s*:\s*(\d+)/g;
    while ((m = fcRe.exec(d)) !== null) {
        fcAll.push({value: +m[1], position: m.index});
    }
    if (fcAll.length > 0) {
        let lastFcIdx = 0;
        for (let i = 1; i < fcAll.length; i++) {
            if (fcAll[i].position - fcAll[i-1].position > 50000) break;
            lastFcIdx = i;
        }
        r.fc = fcAll[lastFcIdx].value;
    }

    return JSON.stringify(r);
}
"""


# ---------------------------------------------------------------------------
# Xvfb management
# ---------------------------------------------------------------------------


def start_xvfb() -> subprocess.Popen:
    """Launch Xvfb on a free display number. Returns the process handle."""
    for display_num in range(99, 110):
        display = f":{display_num}"
        lock_file = f"/tmp/.X{display_num}-lock"
        if os.path.exists(lock_file):
            continue
        proc = subprocess.Popen(
            ["Xvfb", display, "-screen", "0", "1280x720x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.0)
        if proc.poll() is None:  # Still running
            os.environ["DISPLAY"] = display
            logger.info(f"Xvfb started on display {display} (pid {proc.pid})")
            return proc
        # Failed to start on this display, try next
    raise RuntimeError("Could not find a free display for Xvfb (tried :99 through :109)")


def stop_xvfb(proc: subprocess.Popen) -> None:
    """Terminate the Xvfb process."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Cloudflare detection
# ---------------------------------------------------------------------------


def check_cloudflare_block(page: Any) -> bool:
    """Check if the current page is a Cloudflare challenge."""
    title = page.title().lower()
    cloudflare_titles = ["just a moment", "attention required", "access denied"]
    if any(t in title for t in cloudflare_titles):
        return True

    try:
        body_text = page.evaluate("() => document.body?.innerText?.substring(0, 1000) || ''")
        indicators = [
            "checking your browser",
            "cf-browser-verification",
            "enable javascript and cookies",
            "ray id:",
        ]
        body_lower = body_text.lower()
        if any(ind in body_lower for ind in indicators):
            return True
    except Exception:
        pass

    return False


# ---------------------------------------------------------------------------
# Extraction and parsing
# ---------------------------------------------------------------------------


def extract_community_data(page: Any) -> dict:
    """Run the JS extractor on a Metaculus question page and return parsed JSON."""
    raw = page.evaluate(JS_EXTRACTOR)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"_raw_string": raw}


def parse_p_yes(data: dict) -> float | None:
    """Extract community P(Yes) for a binary question.

    The extractor returns `current` as the last value in the community
    prediction history, and `centers` as a fallback string.
    For binary questions, this IS P(Yes) directly (the community median).
    """
    current = data.get("current")
    if current is not None:
        try:
            return float(current)
        except (ValueError, TypeError):
            pass

    centers_str = data.get("centers")
    if centers_str:
        try:
            return float(str(centers_str).strip())
        except (ValueError, TypeError):
            pass

    return None


# ---------------------------------------------------------------------------
# Browser launch configuration
# ---------------------------------------------------------------------------

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
]

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Main scraping function
# ---------------------------------------------------------------------------


def scrape_community_prediction(
    question_id: int,
    wait_seconds: float = 5.0,
) -> ScrapedCommunityPrediction | None:
    """Scrape the current community prediction for a Metaculus question.

    Launches Playwright with headless=False (required to bypass Cloudflare),
    manages Xvfb automatically if no display is available, navigates to
    the question page, and extracts community prediction data.

    Args:
        question_id: The Metaculus post ID of the question to scrape
        wait_seconds: Seconds to wait for JS hydration after page load

    Returns:
        ScrapedCommunityPrediction with the scraped data, or None if scraping fails.
        Failures are logged as warnings — the pipeline should continue without this data.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(
            "Playwright not installed — cannot scrape community prediction. "
            "Install: poetry add playwright && poetry run playwright install chromium"
        )
        return None

    xvfb_proc = None
    needs_xvfb = not os.environ.get("DISPLAY")

    try:
        # Start Xvfb if no display is available (CI/headless environment)
        if needs_xvfb:
            try:
                xvfb_proc = start_xvfb()
            except RuntimeError as e:
                logger.warning(f"Could not start Xvfb: {e}")
                return None

        url = f"{BASE_URL}/{question_id}/"
        logger.info(f"Scraping community prediction from {url}")

        t_start = time.monotonic()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=BROWSER_ARGS,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=USER_AGENT,
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(int(wait_seconds * 1000))

                # Dismiss modals
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                except Exception:
                    pass

                # Check for Cloudflare
                if check_cloudflare_block(page):
                    # Retry once after waiting
                    logger.warning(f"Cloudflare challenge on Q{question_id} — retrying after 10s")
                    page.wait_for_timeout(10_000)
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    page.wait_for_timeout(int(wait_seconds * 1000))

                    if check_cloudflare_block(page):
                        logger.warning(f"Cloudflare blocked Q{question_id} after retry — giving up")
                        return None

                # Extract data
                data = extract_community_data(page)

            finally:
                context.close()
                browser.close()

        elapsed = time.monotonic() - t_start
        logger.info(f"Scrape completed in {elapsed:.1f}s for Q{question_id}")

        if not data:
            logger.warning(f"No data extracted from Q{question_id}")
            return None

        # Parse P(Yes)
        p_yes = parse_p_yes(data)
        if p_yes is None:
            logger.warning(f"Could not extract P(Yes) from Q{question_id} data: {data}")
            return None

        # Build result
        trend = {}
        for key in [
            "week_delta",
            "two_week_delta",
            "month_delta",
            "week_ago",
            "two_weeks_ago",
            "month_ago",
            "history_min",
            "history_max",
        ]:
            if key in data:
                trend[key] = data[key]

        return ScrapedCommunityPrediction(
            p_yes=p_yes,
            forecaster_count=data.get("fc"),
            history_length=data.get("history_length"),
            resolution=data.get("res"),
            trend=trend,
        )

    except Exception as e:
        logger.warning(
            f"Failed to scrape community prediction for Q{question_id}: {e}",
            exc_info=True,
        )
        return None

    finally:
        if xvfb_proc is not None:
            stop_xvfb(xvfb_proc)


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------


def format_community_prediction_context(
    scraped: ScrapedCommunityPrediction,
    details: MetaQuestionDetails,
) -> str:
    """Format scraped community prediction data as an XML-tagged context block.

    This block is injected into the research context for the forecasting pipeline,
    following the same pattern as <QuestionSource>, <Summary>, etc.

    Args:
        scraped: The scraped community prediction data
        details: Parsed meta-question details (threshold, direction, etc.)

    Returns:
        Formatted context string ready for injection into historical/current context
    """
    lines = [
        f'<CommunityPrediction source="metaculus_browser_scrape" '
        f'underlying_question_id="{details.underlying_post_id}">',
        "This is a meta-question about community forecaster behavior on Metaculus. "
        "The data below was scraped directly from the Metaculus question page.",
        "",
    ]

    # Underlying question info
    if details.underlying_title:
        lines.append(f'Underlying question: "{details.underlying_title}"')
    else:
        lines.append(f"Underlying question ID: {details.underlying_post_id}")

    # Current community prediction
    p_pct = scraped.p_yes * 100
    fc_str = (
        f" (based on {scraped.forecaster_count} forecasters)" if scraped.forecaster_count else ""
    )
    lines.append(f"Current community P(Yes): {p_pct:.1f}%{fc_str}")
    lines.append("")

    # Meta-question parameters
    if details.threshold is not None and details.direction:
        t_pct = details.threshold * 100
        lines.append(f"Meta-question threshold: {t_pct:.2f}% (direction: {details.direction} than)")
    if details.target_date:
        lines.append(f"Meta-question target date: {details.target_date}")
    if details.last_cp is not None:
        lines.append(
            f"Community prediction at meta-question creation: {details.last_cp * 100:.2f}%"
        )
    lines.append("")

    # Trend data
    trend = scraped.trend
    has_trend = any(k in trend for k in ["week_delta", "two_week_delta", "month_delta"])
    if has_trend:
        lines.append("Trend data:")
        if "week_delta" in trend:
            delta = trend["week_delta"]
            lines.append(f"- 7-day change: {delta:+.4f} ({delta * 100:+.1f} percentage points)")
        if "two_week_delta" in trend:
            delta = trend["two_week_delta"]
            lines.append(f"- 14-day change: {delta:+.4f} ({delta * 100:+.1f} percentage points)")
        if "month_delta" in trend:
            delta = trend["month_delta"]
            lines.append(f"- 30-day change: {delta:+.4f} ({delta * 100:+.1f} percentage points)")

    if "history_min" in trend and "history_max" in trend:
        h_min = trend["history_min"]
        h_max = trend["history_max"]
        h_len = scraped.history_length or "unknown"
        lines.append(f"- History range: [{h_min:.2f}, {h_max:.2f}] over {h_len} data points")

    lines.append("")

    # Key resolution logic
    if details.threshold is not None and details.direction:
        t_pct = details.threshold * 100
        direction_upper = details.direction.upper()
        lines.append(
            f"To resolve YES, the community prediction must be "
            f"{direction_upper} THAN {t_pct:.2f}% on the target date."
        )

        diff = scraped.p_yes - details.threshold
        diff_pp = abs(diff) * 100
        position = "ABOVE" if diff > 0 else "BELOW"

        lines.append(
            f"The current community prediction is {p_pct:.1f}%, "
            f"which is {diff_pp:.1f} percentage points {position} the threshold."
        )

    # Resolution status
    if scraped.resolution:
        lines.append(f"\nUnderlying question resolution: {scraped.resolution}")

    lines.append("</CommunityPrediction>")
    return "\n".join(lines)
