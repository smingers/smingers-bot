#!/usr/bin/env python3
"""
Supervisor Agent Evaluation Script

Runs the supervisor agent on a historical forecast and saves full output
as readable artifacts in the forecast's ensemble/ directory.

Usage:
    # Run supervisor on a specific forecast (primary usage)
    poetry run python scripts/evaluate_supervisor.py --forecast-dir data/36030_20260205_220335

    # Override the model used
    poetry run python scripts/evaluate_supervisor.py --forecast-dir data/36030_20260205_220335 \
        --model openrouter/anthropic/claude-3.5-haiku

    # Batch: scan all forecasts and show divergence (no LLM calls)
    poetry run python scripts/evaluate_supervisor.py --dry-run

    # Batch: run supervisor on up to N high-divergence forecasts
    poetry run python scripts/evaluate_supervisor.py --limit 5

    # Batch: filter by question type
    poetry run python scripts/evaluate_supervisor.py --question-type binary --limit 10

    # Batch: override divergence threshold (lower = more forecasts evaluated)
    poetry run python scripts/evaluate_supervisor.py --threshold-override 10.0
"""

import argparse
import asyncio
import json
import logging
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.divergence import (  # noqa: E402
    compute_binary_divergence,
    compute_multiple_choice_divergence,
    compute_numeric_divergence,
)
from src.bot.supervisor import SupervisorAgent, SupervisorInput, SupervisorResult  # noqa: E402
from src.utils.llm import LLMClient  # noqa: E402

logger = logging.getLogger(__name__)

DATA_DIR = Path("./data")


# =============================================================================
# Data Loading
# =============================================================================


def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if it doesn't exist or fails."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_text(path: Path) -> str | None:
    """Load a text file, returning None if it doesn't exist."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return None


def load_forecast(forecast_dir: Path, allow_test_mode: bool = False) -> dict | None:
    """
    Load all data from a historical forecast directory.

    Returns a dict with question metadata, forecaster predictions, and aggregation,
    or None if the forecast is invalid/incomplete.
    """
    # Must have new-format ensemble/ directory
    ensemble_dir = forecast_dir / "ensemble"
    if not ensemble_dir.is_dir():
        return None

    # Load metadata
    metadata = load_json(forecast_dir / "metadata.json")
    if not metadata:
        return None

    # Skip errored forecasts
    if metadata.get("errors"):
        return None

    config = metadata.get("config_snapshot", {})
    mode = config.get("mode", "unknown")

    # Skip test-mode forecasts in batch mode (cheap models, not representative)
    if mode == "test" and not allow_test_mode:
        return None

    # Load question
    question_data = load_json(forecast_dir / "question.json")
    if not question_data:
        return None

    q = question_data.get("question", question_data)
    question_type = q.get("type", "binary")
    title = question_data.get("title") or q.get("title", "")

    # Load aggregation
    aggregation = load_json(ensemble_dir / "aggregation.json")
    if not aggregation:
        return None

    # Load ensemble agent config
    active_agents = config.get("_active_agents", [])
    if not active_agents:
        tier = "fast" if mode == "test" else "quality"
        active_agents = config.get("ensemble", {}).get(
            tier, config.get("ensemble", {}).get("production", [])
        )

    # Load individual forecaster data
    forecaster_predictions = []
    raw_predictions = []  # For divergence computation

    for i in range(1, 6):
        pred_json = load_json(ensemble_dir / f"forecaster_{i}.json")
        inside_view = load_text(ensemble_dir / f"forecaster_{i}_inside_view.md")

        agent_model = "unknown"
        if i - 1 < len(active_agents):
            agent_model = active_agents[i - 1].get("model", "unknown")

        prediction = None
        if pred_json:
            prediction = (
                pred_json.get("probability")
                or pred_json.get("percentiles")
                or pred_json.get("probabilities")
            )

        forecaster_predictions.append(
            {
                "agent_id": f"forecaster_{i}",
                "model": agent_model,
                "prediction": prediction,
                "reasoning": inside_view or "",
            }
        )

        raw_predictions.append(prediction)

    # Extract options for MC
    options = []
    if question_type == "multiple_choice":
        raw_options = q.get("options") or question_data.get("options", [])
        for opt in raw_options or []:
            if isinstance(opt, str):
                options.append(opt)
            elif isinstance(opt, dict):
                options.append(opt.get("label", "?"))

    # Get weighted average
    weighted_avg = None
    if question_type == "binary":
        weighted_avg = aggregation.get("final_probability")
    elif question_type == "multiple_choice":
        raw_final = aggregation.get("final_probabilities")
        if isinstance(raw_final, dict):
            weighted_avg = list(raw_final.values())
        elif isinstance(raw_final, list):
            weighted_avg = raw_final

    # Parse forecast timestamp from dir name
    dir_name = forecast_dir.name
    parts = dir_name.split("_", 1)
    question_id = int(parts[0]) if parts[0].isdigit() else 0

    return {
        "forecast_dir": str(forecast_dir),
        "question_id": question_id,
        "question_type": question_type,
        "question_title": title,
        "question_data": q,
        "forecaster_predictions": forecaster_predictions,
        "raw_predictions": raw_predictions,
        "weighted_average": weighted_avg,
        "aggregation": aggregation,
        "options": options,
        "mode": mode,
        "config": config,
        "metadata": metadata,
    }


# =============================================================================
# Divergence Computation
# =============================================================================


def compute_divergence_for_forecast(
    forecast: dict, threshold_override: float | None = None
) -> dict:
    """Compute divergence metrics for a loaded forecast."""
    qt = forecast["question_type"]
    raw = forecast["raw_predictions"]

    if qt == "binary":
        probabilities = [p for p in raw if isinstance(p, (int, float))]
        threshold = threshold_override or 15.0
        metrics = compute_binary_divergence(probabilities, threshold=threshold)
    elif qt == "numeric":
        pct_dicts = [p for p in raw if isinstance(p, dict)]
        threshold = threshold_override or 0.25
        metrics = compute_numeric_divergence(pct_dicts, threshold=threshold)
    elif qt == "multiple_choice":
        prob_lists = [p for p in raw if isinstance(p, list)]
        threshold = threshold_override or 20.0
        metrics = compute_multiple_choice_divergence(prob_lists, threshold=threshold)
    else:
        return {
            "metric_name": "unknown",
            "metric_value": 0.0,
            "threshold": 0.0,
            "triggered": False,
            "detail": f"Unknown type: {qt}",
        }

    return {
        "metric_name": metrics.metric_name,
        "metric_value": metrics.metric_value,
        "threshold": metrics.threshold,
        "triggered": metrics.should_trigger_supervisor,
        "detail": metrics.detail,
    }


def build_supervisor_input(forecast: dict) -> SupervisorInput:
    """Build a SupervisorInput from a loaded forecast."""
    q = forecast["question_data"]
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    return SupervisorInput(
        question_title=forecast["question_title"],
        question_type=forecast["question_type"],
        resolution_criteria=q.get("resolution_criteria", ""),
        fine_print=q.get("fine_print", ""),
        background=q.get("description", "") or q.get("background_info", ""),
        open_time=q.get("open_time", ""),
        scheduled_resolve_time=q.get("scheduled_resolve_time", "")
        or q.get("scheduled_resolve_time", ""),
        today=today,
        forecaster_predictions=forecast["forecaster_predictions"],
        weighted_average_prediction=forecast["weighted_average"],
        options=forecast.get("options"),
        num_options=len(forecast.get("options", [])) or None,
    )


def _serialize_prediction(pred: Any) -> Any:
    """Make prediction JSON-serializable."""
    if isinstance(pred, dict):
        return {str(k): v for k, v in pred.items()}
    if isinstance(pred, list):
        return pred
    if isinstance(pred, float):
        return round(pred, 4)
    return pred


# =============================================================================
# Single Forecast Mode: run supervisor on one forecast, save readable artifacts
# =============================================================================


def _save_supervisor_artifacts(
    forecast_dir: Path,
    forecast: dict,
    result: SupervisorResult,
    divergence: dict,
    config: dict,
) -> None:
    """Save supervisor output as readable files in the forecast's ensemble/ directory."""
    ensemble_dir = forecast_dir / "ensemble"

    # 1. Disagreement analysis (Stage 1 full output)
    analysis_path = ensemble_dir / "supervisor_analysis.md"
    analysis_path.write_text(result.disagreement_analysis or "(no analysis produced)")
    print(f"  Saved: {analysis_path}")

    # 2. Research context (what the supervisor found from its searches)
    research_path = ensemble_dir / "supervisor_research.md"
    if result.search_context:
        research_path.write_text(result.search_context)
    else:
        research_path.write_text("(no search conducted — 0 queries generated)")
    print(f"  Saved: {research_path}")

    # 3. Supervisor reasoning (Stage 2 full output — the updated forecast + justification)
    reasoning_path = ensemble_dir / "supervisor_reasoning.md"
    reasoning_path.write_text(result.reasoning or "(no reasoning produced)")
    print(f"  Saved: {reasoning_path}")

    # 4. Structured result (machine-readable summary)
    result_path = ensemble_dir / "supervisor_result.json"
    result_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "supervisor_model": config.get("supervisor", {}).get("model", {}),
        "question_id": forecast["question_id"],
        "question_type": forecast["question_type"],
        "question_title": forecast["question_title"],
        "divergence": divergence,
        "weighted_average": forecast["weighted_average"],
        "forecaster_predictions": forecast["raw_predictions"],
        "supervisor_prediction": _serialize_prediction(result.updated_prediction),
        "supervisor_confidence": result.confidence,
        "supervisor_override": result.should_override,
        "supervisor_cost": result.cost,
        "supervisor_error": result.error,
        "search_queries": result.search_queries,
    }
    result_path.write_text(json.dumps(result_data, indent=2, default=str))
    print(f"  Saved: {result_path}")


async def run_single_forecast(args: argparse.Namespace) -> None:
    """Run supervisor on a single forecast directory and save artifacts."""
    forecast_dir = Path(args.forecast_dir)
    if not forecast_dir.is_dir():
        print(f"ERROR: {forecast_dir} is not a directory")
        sys.exit(1)

    # Load config
    config_path = Path("config.yaml")
    config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    if args.model:
        config.setdefault("supervisor", {})["model"] = {"quality": args.model}

    # Load forecast (allow test mode for single-forecast evaluation)
    forecast = load_forecast(forecast_dir, allow_test_mode=True)
    if forecast is None:
        print(f"ERROR: Could not load forecast from {forecast_dir}")
        print("  (needs ensemble/ directory, metadata.json, question.json, aggregation.json)")
        sys.exit(1)

    qid = forecast["question_id"]
    qt = forecast["question_type"]
    title = forecast["question_title"]

    # Compute and show divergence
    divergence = compute_divergence_for_forecast(forecast)

    print(f"Question: {title}")
    print(f"  ID: {qid} | Type: {qt} | Mode: {forecast['mode']}")
    print(f"  Divergence: {divergence['detail']}")
    print(f"  Triggered: {'YES' if divergence['triggered'] else 'no'}")
    print(f"  Weighted average: {forecast['weighted_average']}")
    print(f"  Individual predictions: {forecast['raw_predictions']}")
    print()

    # Run supervisor
    print("Running supervisor...")
    llm_client = LLMClient()
    supervisor = SupervisorAgent(config, llm_client)
    supervisor_input = build_supervisor_input(forecast)

    result = await supervisor.evaluate(supervisor_input)

    # Print summary
    print()
    status = "OVERRIDE" if result.should_override else "deferred"
    print(f"Result: {status}")
    print(f"  Confidence: {result.confidence.upper()}")
    print(f"  Prediction: {_serialize_prediction(result.updated_prediction)}")
    print(f"  Search queries: {len(result.search_queries)}")
    for q in result.search_queries:
        print(f"    - {q}")
    print(f"  Cost: ${result.cost:.4f}")
    if result.error:
        print(f"  Error: {result.error}")
    print()

    # Save artifacts
    print("Saving artifacts...")
    _save_supervisor_artifacts(forecast_dir, forecast, result, divergence, config)

    print()
    print("Done. Open the files above to review the supervisor's full output.")


# =============================================================================
# Batch Mode: scan all forecasts, compute divergence, optionally run supervisor
# =============================================================================


async def run_batch(args: argparse.Namespace) -> None:
    """Batch evaluation: scan forecasts, compute divergence, optionally run supervisor."""
    # Load config
    config_path = Path("config.yaml")
    config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
    if args.model:
        config.setdefault("supervisor", {})["model"] = {"quality": args.model}

    # Scan all forecast directories
    forecast_dirs = sorted(DATA_DIR.iterdir())
    forecast_dirs = [
        d for d in forecast_dirs if d.is_dir() and d.name[0].isdigit() and "_" in d.name
    ]

    print(f"Scanning {len(forecast_dirs)} forecast directories...")

    # Load and filter forecasts
    forecasts = []
    for d in forecast_dirs:
        forecast = load_forecast(d)
        if forecast is None:
            continue
        if args.question_type and forecast["question_type"] != args.question_type:
            continue
        forecasts.append(forecast)

    print(f"Loaded {len(forecasts)} valid forecasts (non-test, new-format)")

    # Compute divergence for all forecasts
    for forecast in forecasts:
        forecast["divergence"] = compute_divergence_for_forecast(
            forecast, threshold_override=args.threshold_override
        )

    # Sort by divergence (highest first) for more interesting evaluation
    forecasts.sort(key=lambda f: f["divergence"]["metric_value"], reverse=True)

    # Count above threshold
    above_threshold = [f for f in forecasts if f["divergence"]["triggered"]]
    print(f"Above divergence threshold: {len(above_threshold)} / {len(forecasts)}")

    if args.dry_run:
        _print_dry_run_summary(forecasts)
        return

    # Run supervisor on forecasts (either all above threshold, or up to limit)
    candidates = above_threshold if not args.threshold_override else forecasts
    if args.limit:
        candidates = candidates[: args.limit]

    if not candidates:
        print("No forecasts to evaluate (none above threshold).")
        return

    print(f"\nRunning supervisor on {len(candidates)} forecasts...")
    print("Artifacts will be saved into each forecast's ensemble/ directory.\n")

    llm_client = LLMClient()
    supervisor = SupervisorAgent(config, llm_client)

    total_cost = 0.0
    results_summary = []

    for i, forecast in enumerate(candidates):
        qid = forecast["question_id"]
        qt = forecast["question_type"]
        title = forecast["question_title"][:60]
        div_val = forecast["divergence"]["metric_value"]
        forecast_dir = Path(forecast["forecast_dir"])

        print(f"[{i + 1}/{len(candidates)}] Q{qid} ({qt}) div={div_val:.1f} — {title}")

        supervisor_input = build_supervisor_input(forecast)

        try:
            result = await supervisor.evaluate(supervisor_input)

            # Save artifacts into the forecast directory
            _save_supervisor_artifacts(
                forecast_dir, forecast, result, forecast["divergence"], config
            )

            total_cost += result.cost
            status = "OVERRIDE" if result.should_override else "deferred"
            print(
                f"  -> {status} (confidence={result.confidence}, "
                f"pred={_serialize_prediction(result.updated_prediction)}, "
                f"cost=${result.cost:.4f})"
            )

            results_summary.append(
                {
                    "question_id": qid,
                    "question_type": qt,
                    "confidence": result.confidence,
                    "override": result.should_override,
                    "cost": result.cost,
                }
            )

        except Exception as e:
            print(f"  -> ERROR: {e}")
            results_summary.append({"question_id": qid, "question_type": qt, "error": str(e)})

        print()

    # Print batch summary
    successful = [r for r in results_summary if "confidence" in r]
    errored = [r for r in results_summary if "error" in r]
    print("\n=== Batch Summary ===")
    print(f"Total: {len(results_summary)} | Successful: {len(successful)} | Errors: {len(errored)}")
    if successful:
        overrides = sum(1 for r in successful if r["override"])
        print(f"Overrides (HIGH confidence): {overrides}/{len(successful)}")
        print(f"Total cost: ${total_cost:.4f}")


def _print_dry_run_summary(forecasts: list[dict]) -> None:
    """Print divergence distribution without running the supervisor."""
    print("\n=== Dry Run: Divergence Distribution ===\n")

    by_type: dict[str, list] = {}
    for f in forecasts:
        qt = f["question_type"]
        by_type.setdefault(qt, []).append(f)

    for qt, qt_forecasts in sorted(by_type.items()):
        values = [f["divergence"]["metric_value"] for f in qt_forecasts]
        triggered = sum(1 for f in qt_forecasts if f["divergence"]["triggered"])
        threshold = qt_forecasts[0]["divergence"]["threshold"] if qt_forecasts else 0

        print(f"{qt} ({len(qt_forecasts)} forecasts):")
        print(f"  Metric: {qt_forecasts[0]['divergence']['metric_name']}")
        print(f"  Threshold: {threshold}")
        print(f"  Above threshold: {triggered} ({100 * triggered / len(qt_forecasts):.0f}%)")
        if values:
            print(f"  Min: {min(values):.2f}")
            print(f"  Median: {statistics.median(values):.2f}")
            print(f"  Mean: {statistics.mean(values):.2f}")
            print(f"  Max: {max(values):.2f}")
            if len(values) >= 2:
                print(f"  Std: {statistics.stdev(values):.2f}")
        print()

    # Show top-10 most divergent forecasts
    all_sorted = sorted(forecasts, key=lambda f: f["divergence"]["metric_value"], reverse=True)
    print("Top 10 most divergent forecasts:")
    for f in all_sorted[:10]:
        qid = f["question_id"]
        qt = f["question_type"]
        div = f["divergence"]["metric_value"]
        triggered = "***" if f["divergence"]["triggered"] else "   "
        title = f["question_title"][:50]
        preds = f["raw_predictions"]
        print(f"  {triggered} Q{qid} ({qt}) div={div:.1f} | {title}")
        if qt == "binary":
            valid_preds = [p for p in preds if isinstance(p, (int, float))]
            print(f"       Predictions: {valid_preds}")


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Run the supervisor agent on historical forecasts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on a single forecast (primary usage):
  poetry run python scripts/evaluate_supervisor.py --forecast-dir data/36030_20260205_220335

  # See which forecasts have high divergence:
  poetry run python scripts/evaluate_supervisor.py --dry-run

  # Batch run on top 5 most divergent:
  poetry run python scripts/evaluate_supervisor.py --limit 5
""",
    )

    # Single forecast mode
    parser.add_argument(
        "--forecast-dir",
        type=str,
        default=None,
        help="Path to a specific forecast directory (e.g. data/36030_20260205_220335)",
    )

    # Batch mode options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute divergence metrics only, no LLM calls",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of forecasts to evaluate (batch mode)",
    )
    parser.add_argument(
        "--question-type",
        choices=["binary", "numeric", "multiple_choice"],
        default=None,
        help="Filter by question type (batch mode)",
    )
    parser.add_argument(
        "--threshold-override",
        type=float,
        default=None,
        help="Override divergence threshold (batch mode)",
    )

    # Shared options
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override supervisor model",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging output",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    if args.forecast_dir:
        asyncio.run(run_single_forecast(args))
    else:
        asyncio.run(run_batch(args))


if __name__ == "__main__":
    main()
