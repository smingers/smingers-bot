#!/usr/bin/env python3
"""
Migrate artifact data to populate missing database fields.

PURPOSE:
This is a one-time migration utility for backfilling database fields that were
added after some forecasts were already recorded. It reads JSON files from the
artifact directories (data/{question_id}_{timestamp}/) and updates the SQLite
database with any missing data.

Specifically, it:
1. Backfills the 'mode' field (test/preview/live) from metadata.json
2. Backfills 'prediction_data' JSON from prediction.json and aggregation.json

WHEN TO USE:
- Only needed if you have old forecast artifacts with incomplete database records
- New forecasts populate these fields automatically during the pipeline
- Safe to run multiple times (only updates rows with missing data)

Usage:
    python scripts/migrate_artifacts.py
    python scripts/migrate_artifacts.py --dry-run  # Preview changes without modifying DB
"""

import asyncio
import json
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import ForecastDatabase


def find_artifact_dirs(data_dir: Path) -> list[Path]:
    """Find all artifact directories matching {question_id}_{timestamp} pattern."""
    pattern = re.compile(r"^\d+_\d{8}_\d{6}$")
    dirs = []
    for item in data_dir.iterdir():
        if item.is_dir() and pattern.match(item.name):
            dirs.append(item)
    return sorted(dirs, key=lambda p: p.name)


def detect_artifact_format(forecast_dir: Path) -> str:
    """Detect whether artifact uses old or new format."""
    if (forecast_dir / "ensemble").exists():
        return "new"
    elif (forecast_dir / "04_inside_view").exists():
        return "old"
    return "unknown"


def extract_mode(forecast_dir: Path) -> str | None:
    """Extract mode from metadata.json."""
    metadata_path = forecast_dir / "metadata.json"
    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
        return metadata.get("config_snapshot", {}).get("mode")
    except (json.JSONDecodeError, KeyError):
        return None


def extract_question_type(forecast_dir: Path) -> str | None:
    """Extract question type from metadata.json or question.json."""
    # Try metadata.json first
    metadata_path = forecast_dir / "metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
            q_type = metadata.get("analysis", {}).get("type")
            if q_type:
                return q_type
        except (json.JSONDecodeError, KeyError):
            pass

    # Fall back to question.json
    for q_path in [
        forecast_dir / "question.json",
        forecast_dir / "00_question.json",
    ]:
        if q_path.exists():
            try:
                with open(q_path) as f:
                    question = json.load(f)
                return question.get("type") or question.get("question", {}).get("type")
            except (json.JSONDecodeError, KeyError):
                pass

    return None


def extract_final_prediction_data(forecast_dir: Path, question_type: str) -> str | None:
    """Extract full prediction data from prediction.json."""
    prediction_path = forecast_dir / "prediction.json"
    if not prediction_path.exists():
        return None

    try:
        with open(prediction_path) as f:
            prediction = json.load(f)

        if question_type == "binary":
            prob = prediction.get("probability")
            if prob is not None:
                return json.dumps({"probability": prob})

        elif question_type == "numeric":
            percentiles = prediction.get("percentiles")
            if percentiles:
                return json.dumps({"percentiles": percentiles})

        elif question_type == "multiple_choice":
            # MC can be stored in different formats
            # New format: prediction.json has forecast_result.final_probabilities
            probs = prediction.get("probabilities")
            if not probs:
                probs = prediction.get("forecast_result", {}).get("final_probabilities")
            if probs:
                # If it's a list, convert to dict with indices
                if isinstance(probs, list):
                    probs = {str(i): p for i, p in enumerate(probs)}
                return json.dumps({"probabilities": probs})

    except (json.JSONDecodeError, KeyError):
        pass

    return None


def extract_agent_predictions_data(forecast_dir: Path, fmt: str) -> list[dict]:
    """Extract agent prediction data from artifacts."""
    predictions = []

    if fmt == "new":
        # New format: ensemble/agent_X.json
        ensemble_dir = forecast_dir / "ensemble"
        for i in range(1, 6):
            agent_path = ensemble_dir / f"agent_{i}.json"
            if agent_path.exists():
                try:
                    with open(agent_path) as f:
                        data = json.load(f)
                    pred_data = {}
                    if "probability" in data and data["probability"] is not None:
                        pred_data = {"probability": data["probability"]}
                    elif "percentiles" in data and data["percentiles"]:
                        pred_data = {"percentiles": data["percentiles"]}
                    elif "probabilities" in data and data["probabilities"]:
                        pred_data = {"probabilities": data["probabilities"]}

                    predictions.append(
                        {
                            "agent_id": f"forecaster_{i}",
                            "prediction_data": json.dumps(pred_data) if pred_data else None,
                        }
                    )
                except json.JSONDecodeError:
                    continue

    elif fmt == "old":
        # Old format: 04_inside_view/forecaster_X/extracted.json
        inside_view = forecast_dir / "04_inside_view"
        for i in range(1, 6):
            extracted_path = inside_view / f"forecaster_{i}" / "extracted.json"
            if extracted_path.exists():
                try:
                    with open(extracted_path) as f:
                        data = json.load(f)
                    pred_data = {}
                    if "probability" in data and data["probability"] is not None:
                        pred_data = {"probability": data["probability"]}
                    elif "percentiles" in data and data["percentiles"]:
                        pred_data = {"percentiles": data["percentiles"]}
                    elif "probabilities" in data and data["probabilities"]:
                        pred_data = {"probabilities": data["probabilities"]}

                    predictions.append(
                        {
                            "agent_id": f"forecaster_{i}",
                            "prediction_data": json.dumps(pred_data) if pred_data else None,
                        }
                    )
                except json.JSONDecodeError:
                    continue

    return predictions


def parse_forecast_id(dir_name: str) -> tuple[int, str]:
    """Parse question_id and timestamp from directory name."""
    parts = dir_name.split("_", 1)
    question_id = int(parts[0])
    timestamp = parts[1]
    return question_id, timestamp


async def migrate(dry_run: bool = False):
    """Run the migration."""
    data_dir = Path("./data")
    db = ForecastDatabase(data_dir / "forecasts.db")

    # Run schema migration first
    print("Running schema migration...")
    if not dry_run:
        await db.migrate_schema()
    print("Schema migration complete.")

    # Find all artifact directories
    artifact_dirs = find_artifact_dirs(data_dir)
    print(f"Found {len(artifact_dirs)} artifact directories")

    # Track statistics
    stats = {
        "total": len(artifact_dirs),
        "mode_updated": 0,
        "prediction_data_updated": 0,
        "agent_data_updated": 0,
        "not_in_db": 0,
        "skipped": 0,
    }

    for artifact_dir in artifact_dirs:
        forecast_id = artifact_dir.name
        question_id, timestamp = parse_forecast_id(forecast_id)

        # Check if forecast exists in database
        forecast = await db.get_forecast(forecast_id)
        if not forecast:
            stats["not_in_db"] += 1
            print(f"  SKIP {forecast_id}: Not in database")
            continue

        updates = []

        # Update mode if needed
        current_mode = forecast.get("mode")
        if not current_mode or current_mode == "unknown":
            mode = extract_mode(artifact_dir)
            if mode:
                if not dry_run:
                    await db.update_forecast_mode(forecast_id, mode)
                stats["mode_updated"] += 1
                updates.append(f"mode={mode}")

        # Update prediction_data if needed
        current_pred_data = forecast.get("prediction_data")
        if not current_pred_data:
            question_type = forecast.get("question_type") or extract_question_type(artifact_dir)
            if question_type:
                pred_data = extract_final_prediction_data(artifact_dir, question_type)
                if pred_data:
                    if not dry_run:
                        await db.update_forecast_prediction_data(forecast_id, pred_data)
                    stats["prediction_data_updated"] += 1
                    # Truncate for display
                    display_data = pred_data[:50] + "..." if len(pred_data) > 50 else pred_data
                    updates.append(f"prediction_data={display_data}")

        # Update agent prediction_data
        fmt = detect_artifact_format(artifact_dir)
        if fmt != "unknown":
            agent_predictions = extract_agent_predictions_data(artifact_dir, fmt)
            for agent_pred in agent_predictions:
                if agent_pred["prediction_data"]:
                    if not dry_run:
                        await db.update_agent_prediction_data(
                            forecast_id, agent_pred["agent_id"], agent_pred["prediction_data"]
                        )
                    stats["agent_data_updated"] += 1

        if updates:
            print(f"  UPDATE {forecast_id}: {', '.join(updates)}")
        else:
            stats["skipped"] += 1

    # Print summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total artifact directories: {stats['total']}")
    print(f"Mode updated: {stats['mode_updated']}")
    print(f"Prediction data updated: {stats['prediction_data_updated']}")
    print(f"Agent prediction data records updated: {stats['agent_data_updated']}")
    print(f"Not in database: {stats['not_in_db']}")
    print(f"Skipped (no updates needed): {stats['skipped']}")

    if dry_run:
        print("\n[DRY RUN - No changes made]")


def main():
    dry_run = "--dry-run" in sys.argv
    asyncio.run(migrate(dry_run=dry_run))


if __name__ == "__main__":
    main()
