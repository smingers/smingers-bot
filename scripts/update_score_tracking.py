#!/usr/bin/env python3
"""
Update a tracking JSON file with latest score data from the Metaculus API.

Background:
    Metaculus locked down their API in Feb 2026 — aggregations (community predictions)
    and resolution values are now returned as null. However, score_data on my_forecasts
    is still available, giving us all 7 scoring fields per question:
        baseline_score, peer_score, coverage, relative_legacy_score,
        weighted_coverage, spot_peer_score, spot_baseline_score

    This script fetches that score data and updates the tracking file for any questions
    that have been newly resolved/scored since the last run.

Usage:
    poetry run python scripts/update_score_tracking.py                              # defaults to minibench
    poetry run python scripts/update_score_tracking.py --tracking-file data/tracking/32916.json
"""

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

DEFAULT_TRACKING_FILE = Path("data/tracking/minibench.json")

# Rate limit: Metaculus returns 429 if we go too fast. Use a conservative delay
# so we stay under their limit; override with --delay if needed.
DEFAULT_DELAY_SECONDS = 2.5
# After a 429, wait this long before the next request to let the limit window reset.
POST_429_COOLDOWN_SECONDS = 6.0


def fetch_score_data(
    token: str, question_ids: list[int], delay_seconds: float = DEFAULT_DELAY_SECONDS
) -> dict[int, dict]:
    """Fetch score data for each question from the Metaculus API.

    Uses the /posts/{id}/ endpoint which includes my_forecasts.score_data
    even though aggregations and resolution values are now null.
    """
    client = httpx.Client(
        base_url="https://www.metaculus.com/api",
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        timeout=30.0,
    )

    results = {}
    for i, qid in enumerate(question_ids):
        hit_429 = False
        for attempt in range(4):
            try:
                resp = client.get(f"/posts/{qid}/")
                if resp.status_code == 429:
                    hit_429 = True
                    # Prefer Retry-After if present, else exponential backoff
                    retry_after = resp.headers.get("Retry-After")
                    wait = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 2 ** (attempt + 2)
                    )
                    print(f"  Rate limited on {qid}, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                print(f"  Error on {qid} attempt {attempt}: {e}")
                time.sleep(3)
                continue
        else:
            print(f"  FAILED: {qid}")
            continue

        q = data.get("question", {})
        my_forecasts = q.get("my_forecasts", {})

        # score_data is a dict with 7 fields when scored, empty/None when not yet scored
        results[qid] = {
            "resolved": data.get("resolved", False),
            "resolution": q.get("resolution"),  # Currently always null due to API lockdown
            "score_data": my_forecasts.get("score_data") or {},
        }

        has_scores = bool(results[qid]["score_data"])
        print(
            f"  [{i + 1}/{len(question_ids)}] {qid}: resolved={data.get('resolved')}, scored={has_scores}"
        )
        time.sleep(delay_seconds)
        if hit_429:
            time.sleep(POST_429_COOLDOWN_SECONDS)

    client.close()
    return results


def update_tracking(tracking: dict, api_results: dict[int, dict]) -> tuple[int, int]:
    """Apply API results to the tracking data.

    Returns (newly_resolved, score_updates) for summary output.
    """
    newly_resolved = 0
    score_updates = 0

    for forecast in tracking["forecasts"]:
        qid = forecast["question_id"]
        api_q = api_results.get(qid)
        if not api_q:
            continue

        # Mark newly resolved questions
        if not forecast.get("resolved") and api_q.get("resolved"):
            forecast["resolved"] = True
            forecast["status"] = "resolved"
            newly_resolved += 1

        # Add or refresh score data — always overwrite with latest from API
        # in case Metaculus recalculates scores
        if api_q.get("score_data"):
            if not forecast.get("score_data"):
                score_updates += 1
            forecast["score_data"] = api_q["score_data"]

        # Resolution values are currently null from the API, but keep this
        # in case Metaculus re-enables them in the future
        if api_q.get("resolution") is not None and forecast.get("resolution") is None:
            forecast["resolution"] = api_q["resolution"]

    return newly_resolved, score_updates


def recompute_stats(tracking: dict):
    """Recompute all aggregate statistics from the forecast data.

    Called after every update to keep summary stats consistent with
    the individual forecast records.
    """
    forecasts = tracking["forecasts"]
    resolved = [f for f in forecasts if f.get("resolved")]
    unresolved = [f for f in forecasts if not f.get("resolved")]

    tracking["resolution_stats"] = {
        "total_resolved": len(resolved),
        "total_unresolved": len(unresolved),
        "binary_resolved": sum(1 for f in resolved if f.get("question_type") == "binary"),
        "numeric_resolved": sum(1 for f in resolved if f.get("question_type") == "numeric"),
        "multiple_choice_resolved": sum(
            1 for f in resolved if f.get("question_type") == "multiple_choice"
        ),
    }

    scored = [f for f in forecasts if f.get("score_data")]
    spot_scores = [
        f["score_data"]["spot_peer_score"]
        for f in scored
        if "spot_peer_score" in f.get("score_data", {})
    ]

    if spot_scores:
        sorted_scores = sorted(spot_scores)
        mid = len(sorted_scores) // 2
        median = (
            sorted_scores[mid]
            if len(sorted_scores) % 2
            else (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
        )

        tracking["score_stats"] = {
            "mean_spot_peer_score": sum(spot_scores) / len(spot_scores),
            "median_spot_peer_score": median,
            "total_scored": len(scored),
            "positive_scores": sum(1 for s in spot_scores if s > 0),
            "negative_scores": sum(1 for s in spot_scores if s < 0),
            "best_score": max(spot_scores),
            "worst_score": min(spot_scores),
            "total_spot_peer_score": sum(spot_scores),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Update tracking file with score data from Metaculus API"
    )
    parser.add_argument(
        "--tracking-file",
        type=Path,
        default=DEFAULT_TRACKING_FILE,
        help=f"Path to tracking JSON file (default: {DEFAULT_TRACKING_FILE})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        metavar="SECS",
        help=f"Seconds to wait between API requests (default: {DEFAULT_DELAY_SECONDS}). Increase if you hit 429s.",
    )
    args = parser.parse_args()

    load_dotenv()
    token = os.getenv("METACULUS_TOKEN")
    if not token:
        print("Error: METACULUS_TOKEN not set")
        return

    tracking_file = args.tracking_file
    with open(tracking_file) as f:
        tracking = json.load(f)

    # Only fetch unresolved questions; once resolved the question is scored and does not need re-checking.
    question_ids = [
        f["question_id"] for f in tracking["forecasts"] if f.get("resolved") is not True
    ]
    print(
        f"Fetching score data for {len(question_ids)} unresolved question(s) from {tracking_file}..."
    )
    print(f"  (delay between requests: {args.delay}s)")

    api_results = fetch_score_data(token, question_ids, delay_seconds=args.delay)
    newly_resolved, score_updates = update_tracking(tracking, api_results)
    recompute_stats(tracking)
    tracking["last_updated"] = datetime.now(tz=UTC).isoformat()

    with open(tracking_file, "w") as f:
        json.dump(tracking, f, indent=2)

    print(f"\nUpdated {tracking_file}")
    print(f"  Newly resolved: {newly_resolved}")
    print(f"  Score updates: {score_updates}")
    if tracking.get("score_stats"):
        print(f"  Total scored: {tracking['score_stats'].get('total_scored', 0)}")
        print(f"  Mean spot peer score: {tracking['score_stats']['mean_spot_peer_score']:.2f}")
    print(f"  Total resolved: {tracking['resolution_stats']['total_resolved']}")
    print(f"  Total unresolved: {tracking['resolution_stats']['total_unresolved']}")


if __name__ == "__main__":
    main()
