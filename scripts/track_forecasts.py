#!/usr/bin/env python3
"""
Forecast Tracking Script

Compares your submitted forecasts against the community consensus for a specific tournament.
Tracks trends over time to identify systematic biases (over/under confidence, etc.).

Usage:
    poetry run python scripts/track_forecasts.py --tournament 32916
    poetry run python scripts/track_forecasts.py --tournament 32916 --output data/tracking/spring_aib_2026.json
"""

import argparse
import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

# Rate limit: Metaculus returns 429 if we go too fast.
REQUEST_DELAY_SECONDS = 2.5
POST_429_COOLDOWN_SECONDS = 6.0


@dataclass
class BinaryComparison:
    """Comparison for binary questions."""

    my_probability: float  # P(Yes)
    community_probability: float  # Community P(Yes)
    difference: float  # my - community (positive = more confident in Yes)


@dataclass
class NumericComparison:
    """Comparison for numeric/date questions."""

    my_median: float
    community_median: float
    my_lower_quartile: float
    my_upper_quartile: float
    community_lower_quartile: float
    community_upper_quartile: float
    median_difference: float  # my - community
    my_iqr: float  # Interquartile range (uncertainty)
    community_iqr: float
    uncertainty_ratio: float  # my_iqr / community_iqr (>1 = more uncertain)


@dataclass
class MultipleChoiceComparison:
    """Comparison for multiple choice questions."""

    my_probabilities: dict[str, float]
    community_probabilities: dict[str, float]
    differences: dict[str, float]  # my - community per option
    max_difference_option: str
    max_difference_value: float


@dataclass
class ForecastComparison:
    """A single forecast comparison record."""

    question_id: int
    question_title: str
    question_type: str
    question_url: str
    forecast_timestamp: str | None
    snapshot_timestamp: str
    num_forecasters: int

    # Type-specific comparison data
    comparison: BinaryComparison | NumericComparison | MultipleChoiceComparison | None = None

    # Resolution data (if resolved)
    resolved: bool = False
    resolution: Any = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        result = {
            "question_id": self.question_id,
            "question_title": self.question_title,
            "question_type": self.question_type,
            "question_url": self.question_url,
            "forecast_timestamp": self.forecast_timestamp,
            "snapshot_timestamp": self.snapshot_timestamp,
            "num_forecasters": self.num_forecasters,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

        if self.comparison:
            if isinstance(self.comparison, BinaryComparison):
                result["comparison"] = {
                    "type": "binary",
                    "my_probability": self.comparison.my_probability,
                    "community_probability": self.comparison.community_probability,
                    "difference": self.comparison.difference,
                }
            elif isinstance(self.comparison, NumericComparison):
                result["comparison"] = {
                    "type": "numeric",
                    "my_median": self.comparison.my_median,
                    "community_median": self.comparison.community_median,
                    "my_lower_quartile": self.comparison.my_lower_quartile,
                    "my_upper_quartile": self.comparison.my_upper_quartile,
                    "community_lower_quartile": self.comparison.community_lower_quartile,
                    "community_upper_quartile": self.comparison.community_upper_quartile,
                    "median_difference": self.comparison.median_difference,
                    "my_iqr": self.comparison.my_iqr,
                    "community_iqr": self.comparison.community_iqr,
                    "uncertainty_ratio": self.comparison.uncertainty_ratio,
                }
            elif isinstance(self.comparison, MultipleChoiceComparison):
                result["comparison"] = {
                    "type": "multiple_choice",
                    "my_probabilities": self.comparison.my_probabilities,
                    "community_probabilities": self.comparison.community_probabilities,
                    "differences": self.comparison.differences,
                    "max_difference_option": self.comparison.max_difference_option,
                    "max_difference_value": self.comparison.max_difference_value,
                }
        else:
            result["comparison"] = None

        return result


@dataclass
class TrackingData:
    """Aggregated tracking data for a tournament."""

    tournament_id: int | str
    tournament_name: str
    last_updated: str
    total_forecasts: int

    # Breakdown by type
    binary_count: int = 0
    numeric_count: int = 0
    multiple_choice_count: int = 0

    # Aggregate statistics
    binary_stats: dict = field(default_factory=dict)
    numeric_stats: dict = field(default_factory=dict)
    multiple_choice_stats: dict = field(default_factory=dict)

    # Individual forecasts
    forecasts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "last_updated": self.last_updated,
            "total_forecasts": self.total_forecasts,
            "binary_count": self.binary_count,
            "numeric_count": self.numeric_count,
            "multiple_choice_count": self.multiple_choice_count,
            "binary_stats": self.binary_stats,
            "numeric_stats": self.numeric_stats,
            "multiple_choice_stats": self.multiple_choice_stats,
            "forecasts": self.forecasts,
        }


def _compute_aggregate_stats_from_dicts(forecast_dicts: list[dict]) -> dict:
    """Compute aggregate statistics from a list of forecast dicts (e.g. after merge)."""
    binary_diffs = []
    numeric_median_diffs = []
    numeric_uncertainty_ratios = []
    mc_max_diffs = []

    for fc in forecast_dicts:
        comp = fc.get("comparison")
        if not comp:
            continue
        ctype = comp.get("type")
        if ctype == "binary" and "difference" in comp:
            binary_diffs.append(comp["difference"])
        elif ctype == "numeric":
            if "median_difference" in comp:
                numeric_median_diffs.append(comp["median_difference"])
            if "uncertainty_ratio" in comp:
                numeric_uncertainty_ratios.append(comp["uncertainty_ratio"])
        elif ctype == "multiple_choice" and "max_difference_value" in comp:
            mc_max_diffs.append(comp["max_difference_value"])

    stats = {}
    if binary_diffs:
        stats["binary"] = {
            "count": len(binary_diffs),
            "mean_difference": sum(binary_diffs) / len(binary_diffs),
            "abs_mean_difference": sum(abs(d) for d in binary_diffs) / len(binary_diffs),
            "more_confident_count": sum(1 for d in binary_diffs if d > 0.05),
            "less_confident_count": sum(1 for d in binary_diffs if d < -0.05),
            "aligned_count": sum(1 for d in binary_diffs if abs(d) <= 0.05),
        }
    if numeric_median_diffs:
        stats["numeric"] = {
            "count": len(numeric_median_diffs),
            "mean_median_difference": sum(numeric_median_diffs) / len(numeric_median_diffs),
            "mean_uncertainty_ratio": sum(numeric_uncertainty_ratios)
            / len(numeric_uncertainty_ratios),
            "more_uncertain_count": sum(1 for r in numeric_uncertainty_ratios if r > 1.1),
            "less_uncertain_count": sum(1 for r in numeric_uncertainty_ratios if r < 0.9),
        }
    if mc_max_diffs:
        stats["multiple_choice"] = {
            "count": len(mc_max_diffs),
            "mean_max_difference": sum(abs(d) for d in mc_max_diffs) / len(mc_max_diffs),
        }
    return stats


class ForecastTracker:
    """Tracks and compares forecasts against community consensus."""

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("METACULUS_TOKEN")
        if not self.token:
            raise ValueError("METACULUS_TOKEN required")

        self.client = httpx.AsyncClient(
            base_url="https://www.metaculus.com/api",
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        self.user_id: int | None = None

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _request_with_retry(
        self, method: str, url: str, retry_count: int = 5, **kwargs
    ) -> httpx.Response:
        """Make an HTTP request with retry and exponential backoff on 429."""
        hit_429 = False
        for attempt in range(retry_count):
            try:
                resp = await self.client.request(method, url, **kwargs)
                if resp.status_code == 429 and attempt < retry_count - 1:
                    hit_429 = True
                    retry_after = resp.headers.get("Retry-After")
                    wait_time = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 2 ** (attempt + 1)
                    )
                    print(f"    Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                resp.raise_for_status()
                if hit_429:
                    await asyncio.sleep(POST_429_COOLDOWN_SECONDS)
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < retry_count - 1:
                    hit_429 = True
                    wait_time = 2 ** (attempt + 1)  # 2, 4, 8, 16 seconds
                    print(f"    Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def get_user_id(self) -> int:
        if self.user_id is None:
            resp = await self._request_with_retry("GET", "/users/me/")
            self.user_id = resp.json()["id"]
        return self.user_id

    async def get_tournament_info(self, tournament_id: int | str) -> dict:
        """Get tournament name and metadata."""
        resp = await self._request_with_retry("GET", f"/projects/{tournament_id}/")
        return resp.json()

    async def get_my_forecasted_questions(self, tournament_id: int | str) -> list[dict]:
        """Get all questions I've forecasted in a tournament."""
        user_id = await self.get_user_id()

        all_questions = []
        offset = 0
        limit = 100

        while True:
            resp = await self._request_with_retry(
                "GET",
                "/posts/",
                params={
                    "forecaster_id": user_id,
                    "tournaments": tournament_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            data = resp.json()

            results = data.get("results", [])
            all_questions.extend(results)

            if len(results) < limit:
                break
            offset += limit

        return all_questions

    async def get_question_details(self, post_id: int) -> dict:
        """Get full question details including my_forecasts and aggregations."""
        resp = await self._request_with_retry("GET", f"/posts/{post_id}/")
        return resp.json()

    def extract_binary_comparison(
        self, my_forecast: dict, community: dict
    ) -> BinaryComparison | None:
        """Extract binary comparison from forecast data."""
        if not my_forecast or not community:
            return None

        # My forecast: forecast_values is [P(No), P(Yes)] for binary
        my_values = my_forecast.get("forecast_values", [])
        if not my_values or len(my_values) < 2:
            return None
        my_prob_yes = my_values[1]  # Second value is P(Yes)

        # Community: similar structure
        comm_values = community.get("forecast_values", [])
        if not comm_values or len(comm_values) < 2:
            # Fallback to centers
            centers = community.get("centers", [])
            if centers and len(centers) >= 2:
                comm_prob_yes = centers[1]
            else:
                return None
        else:
            comm_prob_yes = comm_values[1]

        return BinaryComparison(
            my_probability=my_prob_yes,
            community_probability=comm_prob_yes,
            difference=my_prob_yes - comm_prob_yes,
        )

    @staticmethod
    def denormalize(
        value: float, range_min: float, range_max: float, zero_point: float | None
    ) -> float:
        """Convert a normalized 0-1 value to the actual question scale."""
        if zero_point is None:
            return range_min + (range_max - range_min) * value
        else:
            deriv_ratio = (range_max - zero_point) / (range_min - zero_point)
            return range_min + (range_max - range_min) * (deriv_ratio**value - 1) / (
                deriv_ratio - 1
            )

    def extract_numeric_comparison(
        self, my_forecast: dict, community: dict, scaling: dict
    ) -> NumericComparison | None:
        """Extract numeric comparison from forecast data."""
        if not my_forecast or not community:
            return None

        range_min = scaling.get("range_min", 0)
        range_max = scaling.get("range_max", 1)
        zero_point = scaling.get("zero_point")

        # My forecast
        my_centers = my_forecast.get("centers", [])
        my_lower = my_forecast.get("interval_lower_bounds", [])
        my_upper = my_forecast.get("interval_upper_bounds", [])

        if not my_centers:
            return None

        my_median = self.denormalize(my_centers[0], range_min, range_max, zero_point)
        my_lq = (
            self.denormalize(my_lower[0], range_min, range_max, zero_point)
            if my_lower
            else my_median
        )
        my_uq = (
            self.denormalize(my_upper[0], range_min, range_max, zero_point)
            if my_upper
            else my_median
        )

        # Community
        comm_centers = community.get("centers", [])
        comm_lower = community.get("interval_lower_bounds", [])
        comm_upper = community.get("interval_upper_bounds", [])

        if not comm_centers:
            return None

        comm_median = self.denormalize(comm_centers[0], range_min, range_max, zero_point)
        comm_lq = (
            self.denormalize(comm_lower[0], range_min, range_max, zero_point)
            if comm_lower
            else comm_median
        )
        comm_uq = (
            self.denormalize(comm_upper[0], range_min, range_max, zero_point)
            if comm_upper
            else comm_median
        )

        my_iqr = my_uq - my_lq
        comm_iqr = comm_uq - comm_lq

        return NumericComparison(
            my_median=my_median,
            community_median=comm_median,
            my_lower_quartile=my_lq,
            my_upper_quartile=my_uq,
            community_lower_quartile=comm_lq,
            community_upper_quartile=comm_uq,
            median_difference=my_median - comm_median,
            my_iqr=my_iqr,
            community_iqr=comm_iqr,
            uncertainty_ratio=my_iqr / comm_iqr if comm_iqr > 0 else 1.0,
        )

    def extract_mc_comparison(
        self, my_forecast: dict, community: dict, options: list
    ) -> MultipleChoiceComparison | None:
        """Extract multiple choice comparison from forecast data."""
        if not my_forecast or not community or not options:
            return None

        # Get option labels - handle both string options and dict options with "label" key
        option_labels = []
        for i, opt in enumerate(options):
            if isinstance(opt, str):
                option_labels.append(opt)
            elif isinstance(opt, dict):
                option_labels.append(opt.get("label", f"Option {i}"))
            else:
                option_labels.append(f"Option {i}")

        # My forecast values
        my_values = my_forecast.get("forecast_values", [])
        if not my_values or len(my_values) != len(options):
            return None

        # Community values
        comm_values = community.get("forecast_values", [])
        if not comm_values or len(comm_values) != len(options):
            return None

        my_probs = dict(zip(option_labels, my_values, strict=True))
        comm_probs = dict(zip(option_labels, comm_values, strict=True))

        differences = {label: my_probs[label] - comm_probs[label] for label in option_labels}

        max_option = max(differences.keys(), key=lambda k: abs(differences[k]))

        return MultipleChoiceComparison(
            my_probabilities=my_probs,
            community_probabilities=comm_probs,
            differences=differences,
            max_difference_option=max_option,
            max_difference_value=differences[max_option],
        )

    async def compare_forecast(self, post_data: dict) -> ForecastComparison | None:
        """Create a comparison for a single forecast."""
        if not post_data:
            return None
        post_id = post_data.get("id")
        title = post_data.get("title", "Unknown")
        question = post_data.get("question") or {}
        q_type = question.get("type", "unknown")

        # Get my forecast and community aggregation (may be missing under API lockdown)
        my_forecasts = question.get("my_forecasts") or {}
        my_latest = my_forecasts.get("latest") if my_forecasts else None

        snapshot_timestamp = datetime.now(tz=UTC).isoformat()

        # When API returns partial data (e.g. question null or no my_forecasts), still
        # emit a minimal record so the question stays in the tracking file and merge
        # can preserve existing score_data/resolution/comparison.
        if not my_latest:
            return ForecastComparison(
                question_id=post_id,
                question_title=title,
                question_type=q_type,
                question_url=f"https://www.metaculus.com/questions/{post_id}/",
                forecast_timestamp=None,
                snapshot_timestamp=snapshot_timestamp,
                num_forecasters=0,
                comparison=None,
                resolved=post_data.get("resolved", False),
                resolution=question.get("resolution"),
            )

        aggregations = question.get("aggregations") or {}
        # Prefer unweighted (includes all forecasters) for comparison
        community_data = aggregations.get("unweighted") or {}
        comm_latest = community_data.get("latest") if community_data else None

        # Fall back to recency_weighted if unweighted not available
        if not comm_latest:
            community_data = aggregations.get("recency_weighted") or {}
            if community_data:
                history = community_data.get("history") or []
                comm_latest = history[-1] if history else None

        # Extract timestamps
        forecast_time = my_latest.get("start_time")
        if forecast_time:
            forecast_timestamp = datetime.fromtimestamp(forecast_time, tz=UTC).isoformat()
        else:
            forecast_timestamp = None

        # Get forecaster count
        num_forecasters = comm_latest.get("forecaster_count", 0) if comm_latest else 0

        # Extract comparison based on type
        comparison = None
        if q_type == "binary":
            comparison = self.extract_binary_comparison(my_latest, comm_latest)
        elif q_type in ("numeric", "date"):
            scaling = question.get("scaling") or {}
            comparison = self.extract_numeric_comparison(my_latest, comm_latest, scaling)
        elif q_type == "multiple_choice":
            options = question.get("options") or []
            comparison = self.extract_mc_comparison(my_latest, comm_latest, options)

        return ForecastComparison(
            question_id=post_id,
            question_title=title,
            question_type=q_type,
            question_url=f"https://www.metaculus.com/questions/{post_id}/",
            forecast_timestamp=forecast_timestamp,
            snapshot_timestamp=snapshot_timestamp,
            num_forecasters=num_forecasters,
            comparison=comparison,
            resolved=post_data.get("resolved", False),
            resolution=question.get("resolution"),
        )

    def compute_aggregate_stats(self, forecasts: list[ForecastComparison]) -> dict:
        """Compute aggregate statistics across all forecasts."""
        binary_diffs = []
        numeric_median_diffs = []
        numeric_uncertainty_ratios = []
        mc_max_diffs = []

        for fc in forecasts:
            if fc.comparison is None:
                continue

            if isinstance(fc.comparison, BinaryComparison):
                binary_diffs.append(fc.comparison.difference)
            elif isinstance(fc.comparison, NumericComparison):
                numeric_median_diffs.append(fc.comparison.median_difference)
                numeric_uncertainty_ratios.append(fc.comparison.uncertainty_ratio)
            elif isinstance(fc.comparison, MultipleChoiceComparison):
                mc_max_diffs.append(fc.comparison.max_difference_value)

        stats = {}

        if binary_diffs:
            stats["binary"] = {
                "count": len(binary_diffs),
                "mean_difference": sum(binary_diffs) / len(binary_diffs),
                "abs_mean_difference": sum(abs(d) for d in binary_diffs) / len(binary_diffs),
                "more_confident_count": sum(1 for d in binary_diffs if d > 0.05),
                "less_confident_count": sum(1 for d in binary_diffs if d < -0.05),
                "aligned_count": sum(1 for d in binary_diffs if abs(d) <= 0.05),
            }

        if numeric_median_diffs:
            stats["numeric"] = {
                "count": len(numeric_median_diffs),
                "mean_median_difference": sum(numeric_median_diffs) / len(numeric_median_diffs),
                "mean_uncertainty_ratio": sum(numeric_uncertainty_ratios)
                / len(numeric_uncertainty_ratios),
                "more_uncertain_count": sum(1 for r in numeric_uncertainty_ratios if r > 1.1),
                "less_uncertain_count": sum(1 for r in numeric_uncertainty_ratios if r < 0.9),
            }

        if mc_max_diffs:
            stats["multiple_choice"] = {
                "count": len(mc_max_diffs),
                "mean_max_difference": sum(abs(d) for d in mc_max_diffs) / len(mc_max_diffs),
            }

        return stats

    async def track_tournament(
        self, tournament_id: int | str, existing_data: TrackingData | None = None
    ) -> TrackingData:
        """Track all forecasts in a tournament and compare to community.

        If existing_data is provided (e.g. from a previous run or from update_score_tracking
        / scrape_resolutions), merges preserved fields into the API result so we do not
        overwrite score_data, resolution, or comparison when the API no longer returns them.
        """
        # Get tournament info
        try:
            tournament_info = await self.get_tournament_info(tournament_id)
            tournament_name = tournament_info.get("name", f"Tournament {tournament_id}")
        except Exception:
            tournament_name = f"Tournament {tournament_id}"

        # Get all questions I've forecasted
        questions = await self.get_my_forecasted_questions(tournament_id)
        print(f"Found {len(questions)} forecasted questions in {tournament_name}")

        # Get full details and compare for each question
        forecasts = []
        for i, q in enumerate(questions):
            post_id = q["id"]

            print(
                f"  [{i + 1}/{len(questions)}] Processing {post_id}: {q.get('title', 'Unknown')[:50]}..."
            )

            try:
                # Get full details
                details = await self.get_question_details(post_id)

                # Compare
                comparison = await self.compare_forecast(details)
                if comparison:
                    forecasts.append(comparison)

                # Rate limiting: delay between requests to avoid 429 errors
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            except Exception as e:
                print(f"    Error: {e}")
                continue

        # Convert to dicts and merge with existing data (preserve score_data, resolution,
        # comparison when API no longer provides them)
        forecast_dicts = [f.to_dict() for f in forecasts]
        existing_by_id: dict[int, dict] = {}
        if existing_data and existing_data.forecasts:
            for prev in existing_data.forecasts:
                qid = prev.get("question_id")
                if qid is not None:
                    existing_by_id[qid] = prev

        for fc in forecast_dicts:
            qid = fc.get("question_id")
            existing = existing_by_id.get(qid) if qid is not None else None
            if not existing:
                continue
            # Preserve fields that other scripts or a previous API provided
            if existing.get("score_data"):
                fc["score_data"] = existing["score_data"]
            if fc.get("resolution") is None and existing.get("resolution") is not None:
                fc["resolution"] = existing["resolution"]
            if fc.get("comparison") is None and existing.get("comparison") is not None:
                fc["comparison"] = existing["comparison"]

        # Recompute statistics from merged list (so preserved comparisons are included)
        stats = _compute_aggregate_stats_from_dicts(forecast_dicts)

        # Create tracking data
        data = TrackingData(
            tournament_id=tournament_id,
            tournament_name=tournament_name,
            last_updated=datetime.now(tz=UTC).isoformat(),
            total_forecasts=len(forecast_dicts),
            binary_count=sum(1 for f in forecast_dicts if f.get("question_type") == "binary"),
            numeric_count=sum(
                1 for f in forecast_dicts if f.get("question_type") in ("numeric", "date")
            ),
            multiple_choice_count=sum(
                1 for f in forecast_dicts if f.get("question_type") == "multiple_choice"
            ),
            binary_stats=stats.get("binary", {}),
            numeric_stats=stats.get("numeric", {}),
            multiple_choice_stats=stats.get("multiple_choice", {}),
            forecasts=forecast_dicts,
        )

        return data


def load_existing_data(filepath: Path) -> TrackingData | None:
    """Load existing tracking data from file."""
    if not filepath.exists():
        return None

    try:
        with open(filepath) as f:
            data = json.load(f)

        return TrackingData(
            tournament_id=data["tournament_id"],
            tournament_name=data["tournament_name"],
            last_updated=data["last_updated"],
            total_forecasts=data["total_forecasts"],
            binary_count=data.get("binary_count", 0),
            numeric_count=data.get("numeric_count", 0),
            multiple_choice_count=data.get("multiple_choice_count", 0),
            binary_stats=data.get("binary_stats", {}),
            numeric_stats=data.get("numeric_stats", {}),
            multiple_choice_stats=data.get("multiple_choice_stats", {}),
            forecasts=data.get("forecasts", []),
        )
    except Exception as e:
        print(f"Warning: Could not load existing data: {e}")
        return None


def save_tracking_data(data: TrackingData, filepath: Path):
    """Save tracking data to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(data.to_dict(), f, indent=2)


def print_summary(data: TrackingData):
    """Print a summary of the tracking data."""
    print("\n" + "=" * 70)
    print(f"FORECAST TRACKING SUMMARY: {data.tournament_name}")
    print("=" * 70)
    print(f"Last updated: {data.last_updated}")
    print(f"Total forecasts: {data.total_forecasts}")
    print(f"  - Binary: {data.binary_count}")
    print(f"  - Numeric/Date: {data.numeric_count}")
    print(f"  - Multiple Choice: {data.multiple_choice_count}")

    if data.binary_stats:
        print("\n--- BINARY QUESTIONS ---")
        stats = data.binary_stats
        print(f"Mean difference (my - community): {stats['mean_difference']:+.1%}")
        print(f"Mean absolute difference: {stats['abs_mean_difference']:.1%}")
        print(f"More confident than community (>5%): {stats['more_confident_count']}")
        print(f"Less confident than community (<-5%): {stats['less_confident_count']}")
        print(f"Aligned with community (±5%): {stats['aligned_count']}")

        # Interpretation
        if stats["mean_difference"] > 0.03:
            print("\n  → You tend to predict YES more often than the community")
        elif stats["mean_difference"] < -0.03:
            print("\n  → You tend to predict NO more often than the community")
        else:
            print("\n  → You're generally aligned with community on binary questions")

    if data.numeric_stats:
        print("\n--- NUMERIC/DATE QUESTIONS ---")
        stats = data.numeric_stats
        print(f"Mean uncertainty ratio: {stats['mean_uncertainty_ratio']:.2f}")
        print(f"More uncertain than community: {stats['more_uncertain_count']}")
        print(f"Less uncertain than community: {stats['less_uncertain_count']}")

        if stats["mean_uncertainty_ratio"] > 1.1:
            print("\n  → You tend to have wider uncertainty ranges than community")
        elif stats["mean_uncertainty_ratio"] < 0.9:
            print("\n  → You tend to have narrower uncertainty ranges than community")
        else:
            print("\n  → Your uncertainty is similar to community")

    if data.multiple_choice_stats:
        print("\n--- MULTIPLE CHOICE QUESTIONS ---")
        stats = data.multiple_choice_stats
        print(f"Mean max difference per question: {stats['mean_max_difference']:.1%}")

    print("\n" + "=" * 70)

    # Show individual forecast details
    print("\nINDIVIDUAL FORECASTS:")
    print("-" * 70)

    for fc in data.forecasts:
        comp = fc.get("comparison")
        if not comp:
            print(f"\n{fc['question_title'][:60]}...")
            print(f"  URL: {fc['question_url']}")
            print(f"  Type: {fc['question_type']}")
            print("  (comparison data unavailable)")
            continue

        print(f"\n{fc['question_title'][:60]}...")
        print(f"  URL: {fc['question_url']}")
        print(f"  Type: {fc['question_type']}, Forecasters: {fc['num_forecasters']}")

        if comp["type"] == "binary":
            print(f"  My forecast: {comp['my_probability']:.1%}")
            print(f"  Community:   {comp['community_probability']:.1%}")
            print(f"  Difference:  {comp['difference']:+.1%}")
        elif comp["type"] == "numeric":
            print(
                f"  My median: {comp['my_median']:.2f} ({comp['my_lower_quartile']:.2f} - {comp['my_upper_quartile']:.2f})"
            )
            print(
                f"  Community: {comp['community_median']:.2f} ({comp['community_lower_quartile']:.2f} - {comp['community_upper_quartile']:.2f})"
            )
            print(f"  Uncertainty ratio: {comp['uncertainty_ratio']:.2f}")
        elif comp["type"] == "multiple_choice":
            for option in comp["my_probabilities"]:
                my_p = comp["my_probabilities"][option]
                comm_p = comp["community_probabilities"][option]
                diff = comp["differences"][option]
                print(f"  {option}: Me {my_p:.1%} vs Community {comm_p:.1%} ({diff:+.1%})")


async def main():
    parser = argparse.ArgumentParser(description="Track forecasts vs community consensus")
    parser.add_argument("--tournament", "-t", type=str, required=True, help="Tournament ID or slug")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: data/tracking/<tournament_id>.json)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress detailed output")

    args = parser.parse_args()

    # Parse tournament ID: use int if numeric, string slug otherwise
    try:
        tournament_id: int | str = int(args.tournament)
    except ValueError:
        tournament_id = args.tournament

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"data/tracking/{tournament_id}.json")

    # Load existing data
    existing = load_existing_data(output_path)
    if existing:
        print(f"Loaded existing tracking data from {output_path}")
        print(f"  Previous update: {existing.last_updated}")
        print(f"  Previous forecasts: {existing.total_forecasts}")

    # Track forecasts
    async with ForecastTracker() as tracker:
        data = await tracker.track_tournament(tournament_id, existing)

    # Save data
    save_tracking_data(data, output_path)
    print(f"\nSaved tracking data to {output_path}")

    # Print summary
    if not args.quiet:
        print_summary(data)


if __name__ == "__main__":
    asyncio.run(main())
