#!/usr/bin/env python3
"""
Backfill the SQLite database from existing forecast artifact directories.

Scans data/ for artifact directories that are not in the database and inserts
forecast + agent_prediction records from the saved artifacts.

Usage:
    python scripts/backfill_database.py              # Dry run (default)
    python scripts/backfill_database.py --apply       # Actually insert into DB
    python scripts/backfill_database.py --apply --force  # Re-insert even if already in DB
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import AgentPredictionRecord, ForecastDatabase, ForecastRecord

logger = logging.getLogger(__name__)

DATA_DIR = Path("./data")
DB_PATH = DATA_DIR / "forecasts.db"


def find_artifact_dirs() -> list[Path]:
    """Find all valid forecast artifact directories."""
    dirs = []
    for entry in DATA_DIR.iterdir():
        if not entry.is_dir():
            continue
        # Match pattern: {question_id}_{YYYYMMDD}_{HHMMSS}
        if re.match(r"^\d+_\d{8}_\d{6}$", entry.name):
            dirs.append(entry)
    return sorted(dirs, key=lambda d: d.name)


def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if it doesn't exist or is invalid."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def parse_dir_name(dir_name: str) -> tuple[int, str]:
    """Parse '{question_id}_{YYYYMMDD}_{HHMMSS}' into (question_id, timestamp)."""
    parts = dir_name.rsplit("_", 2)
    question_id = int(parts[0])
    timestamp = f"{parts[1]}_{parts[2]}"
    return question_id, timestamp


def extract_question_info(forecast_dir: Path) -> dict | None:
    """Extract question type and title from question.json or 00_question.json."""
    # New format
    question_data = load_json(forecast_dir / "question.json")
    # Old format
    if question_data is None:
        question_data = load_json(forecast_dir / "00_question.json")

    if question_data is None:
        return None

    # The question type and title can be at top level or nested under 'question'
    q = question_data.get("question", question_data)
    question_type = q.get("type", "binary")
    title = question_data.get("title") or q.get("title", "")

    return {
        "question_type": question_type,
        "title": title,
        "raw": question_data,
    }


def extract_aggregation(forecast_dir: Path) -> dict | None:
    """Extract aggregation data from ensemble/ or 04_inside_view/."""
    # New format
    agg = load_json(forecast_dir / "ensemble" / "aggregation.json")
    # Old format
    if agg is None:
        agg = load_json(forecast_dir / "04_inside_view" / "aggregation.json")
    return agg


def extract_prediction(forecast_dir: Path) -> dict | None:
    """Extract the final prediction from prediction.json or 06_submission/final_prediction.json."""
    # New format
    pred = load_json(forecast_dir / "prediction.json")
    # Old format
    if pred is None:
        pred = load_json(forecast_dir / "06_submission" / "final_prediction.json")
    return pred


def extract_agent_predictions(forecast_dir: Path, metadata: dict | None) -> list[dict]:
    """Extract individual forecaster predictions from ensemble/ or 04_inside_view/."""
    agents = []

    # Get ensemble config from metadata for model names and weights
    ensemble_config = {}
    if metadata:
        config = metadata.get("config_snapshot", {})
        # Try _active_agents (old format) or active ensemble tier
        active_agents = config.get("_active_agents", [])
        if not active_agents:
            # New format: determine which tier was used based on mode
            mode = config.get("mode", "live")
            tier = "fast" if mode == "test" else "quality"
            # Also check old tier name "production"
            active_agents = config.get("ensemble", {}).get(
                tier, config.get("ensemble", {}).get("production", [])
            )
        for agent in active_agents:
            name = agent.get("name", "")
            ensemble_config[name] = {
                "model": agent.get("model", "unknown"),
                "weight": agent.get("weight", 1.0),
            }

    for i in range(1, 6):
        agent_id = f"forecaster_{i}"

        # New format: ensemble/forecaster_N.json
        agent_data = load_json(forecast_dir / "ensemble" / f"forecaster_{i}.json")
        # Old format: 04_inside_view/forecaster_N/extracted.json
        if agent_data is None:
            agent_data = load_json(
                forecast_dir / "04_inside_view" / f"forecaster_{i}" / "extracted.json"
            )

        if agent_data is None:
            continue

        # Get model and weight from ensemble config
        config_info = ensemble_config.get(agent_id, {})
        model = config_info.get("model", "unknown")
        weight = config_info.get("weight", 1.0)

        # Determine prediction value based on question type
        pred_value = None
        pred_data = "{}"

        if "probability" in agent_data and agent_data["probability"] is not None:
            # Binary: probability is stored as percentage (e.g. 13.0 = 13%)
            raw_prob = agent_data["probability"]
            # Normalize: if > 1, it's a percentage
            prob = raw_prob / 100.0 if raw_prob > 1 else raw_prob
            pred_value = prob
            pred_data = json.dumps({"probability": prob})
        elif "percentiles" in agent_data and agent_data["percentiles"]:
            percentiles = agent_data["percentiles"]
            # Use median (key 50 or "50")
            pred_value = percentiles.get(50, percentiles.get("50"))
            if pred_value is None:
                p40 = percentiles.get(40, percentiles.get("40"))
                p60 = percentiles.get(60, percentiles.get("60"))
                if p40 is not None and p60 is not None:
                    pred_value = (p40 + p60) / 2
            pred_data = json.dumps({"percentiles": percentiles})
        elif "probabilities" in agent_data and agent_data["probabilities"]:
            probs = agent_data["probabilities"]
            pred_value = max(probs) if probs else None
            pred_data = json.dumps({"probabilities": probs})

        # Get reasoning length from inside view markdown
        reasoning_length = 0
        for iv_path in [
            forecast_dir / "ensemble" / f"forecaster_{i}_inside_view.md",
            forecast_dir / "04_inside_view" / f"forecaster_{i}" / "response.md",
            # Old format step2
            forecast_dir / "04_inside_view" / f"forecaster_{i}_step2" / "response.md",
        ]:
            if iv_path.exists():
                reasoning_length = iv_path.stat().st_size
                break

        agents.append(
            {
                "agent_id": agent_id,
                "model": model,
                "weight": weight,
                "prediction": pred_value or 0.0,
                "reasoning_length": reasoning_length,
                "prediction_data": pred_data,
            }
        )

    return agents


def build_forecast_record(forecast_dir: Path) -> tuple[ForecastRecord, list[dict]] | None:
    """Build a ForecastRecord and agent predictions from an artifact directory."""
    question_id, timestamp = parse_dir_name(forecast_dir.name)
    forecast_id = f"{question_id}_{timestamp}"

    # Load metadata
    metadata = load_json(forecast_dir / "metadata.json")
    if metadata is None:
        logger.warning(f"Skipping {forecast_id}: no metadata.json")
        return None

    # Check for errors
    errors = metadata.get("errors", [])
    if errors:
        logger.info(f"Skipping {forecast_id}: has errors: {errors}")
        return None

    # Get question info
    question_info = extract_question_info(forecast_dir)
    if question_info is None:
        logger.warning(f"Skipping {forecast_id}: no question file")
        return None

    question_type = question_info["question_type"]
    title = question_info["title"]

    # Get aggregation
    aggregation = extract_aggregation(forecast_dir)

    # Get final prediction
    prediction = extract_prediction(forecast_dir)

    # Determine final_prediction value and prediction_data
    final_prediction = None
    prediction_data = "{}"

    if question_type == "binary":
        # Try aggregation first, then prediction file
        if aggregation and "final_probability" in aggregation:
            final_prediction = aggregation["final_probability"]
        elif prediction and "prediction" in prediction:
            final_prediction = prediction["prediction"]
        if final_prediction is not None:
            prediction_data = json.dumps({"probability": final_prediction})

    elif question_type in ("numeric", "discrete", "date"):
        # Try prediction file for percentiles
        if prediction and "percentiles" in prediction:
            percentiles = prediction["percentiles"]
            final_prediction = percentiles.get("50", percentiles.get(50))
            prediction_data = json.dumps({"percentiles": percentiles})
        elif aggregation:
            # Aggregation may not have percentiles for numeric
            final_prediction = 0.0
            prediction_data = json.dumps({"aggregation": aggregation})

    elif question_type == "multiple_choice":
        if prediction and "distribution" in prediction:
            probs = prediction["distribution"]
            if probs:
                final_prediction = max(probs.values())
                prediction_data = json.dumps({"probabilities": probs})
        elif aggregation and "final_probabilities" in aggregation:
            probs = aggregation["final_probabilities"]
            if probs:
                final_prediction = max(probs.values())
                prediction_data = json.dumps({"probabilities": probs})

    if final_prediction is None:
        logger.warning(f"Skipping {forecast_id}: could not determine final prediction")
        return None

    # Extract config info
    config = metadata.get("config_snapshot", {})
    mode = config.get("mode", "unknown")
    costs = metadata.get("costs", {})
    total_cost = costs.get("total_cost", 0.0)
    config_hash = metadata.get("config_hash", "")
    tournament_id = config.get("submission", {}).get("tournament_id")

    record = ForecastRecord(
        id=forecast_id,
        question_id=question_id,
        timestamp=timestamp,
        question_type=question_type,
        question_title=title,
        base_rate=None,
        final_prediction=final_prediction,
        total_cost=total_cost,
        config_hash=config_hash,
        tournament_id=tournament_id,
        mode=mode,
        prediction_data=prediction_data,
    )

    # Extract agent predictions
    agent_preds = extract_agent_predictions(forecast_dir, metadata)

    return record, agent_preds


async def backfill(apply: bool = False, force: bool = False):
    """Scan artifact directories and backfill the database."""
    db = ForecastDatabase(DB_PATH)
    await db.initialize()
    await db.migrate_schema()

    # Get existing forecast IDs
    existing_ids = set()
    if not force:
        import aiosqlite

        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute("SELECT id FROM forecasts")
            existing_ids = {row[0] for row in await cursor.fetchall()}

    artifact_dirs = find_artifact_dirs()
    logger.info(f"Found {len(artifact_dirs)} artifact directories")
    logger.info(f"Already in database: {len(existing_ids)}")

    inserted = 0
    skipped_existing = 0
    skipped_error = 0

    for forecast_dir in artifact_dirs:
        question_id, timestamp = parse_dir_name(forecast_dir.name)
        forecast_id = f"{question_id}_{timestamp}"

        if forecast_id in existing_ids:
            skipped_existing += 1
            continue

        result = build_forecast_record(forecast_dir)
        if result is None:
            skipped_error += 1
            continue

        record, agent_preds = result

        if apply:
            await db.insert_forecast(record)
            for ap in agent_preds:
                await db.insert_agent_prediction(
                    AgentPredictionRecord(
                        forecast_id=forecast_id,
                        agent_id=ap["agent_id"],
                        model=ap["model"],
                        weight=ap["weight"],
                        prediction=ap["prediction"],
                        reasoning_length=ap["reasoning_length"],
                        prediction_data=ap["prediction_data"],
                    )
                )
            logger.info(
                f"  Inserted: {forecast_id} ({record.question_type}, "
                f"pred={record.final_prediction:.4f}, "
                f"mode={record.mode}, agents={len(agent_preds)})"
            )
        else:
            logger.info(
                f"  Would insert: {forecast_id} ({record.question_type}, "
                f"pred={record.final_prediction:.4f}, "
                f"mode={record.mode}, agents={len(agent_preds)})"
            )

        inserted += 1

    print(f"\n{'=' * 60}")
    print(f"Backfill {'APPLIED' if apply else 'DRY RUN'}")
    print(f"{'=' * 60}")
    print(f"Total artifact dirs:  {len(artifact_dirs)}")
    print(f"Already in DB:        {skipped_existing}")
    print(f"Skipped (errors):     {skipped_error}")
    print(f"{'Inserted' if apply else 'Would insert'}:         {inserted}")

    if not apply and inserted > 0:
        print("\nRun with --apply to actually insert into the database.")


def main():
    parser = argparse.ArgumentParser(description="Backfill forecast database from artifacts")
    parser.add_argument(
        "--apply", action="store_true", help="Actually insert into database (default: dry run)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-insert even if forecast already exists in DB",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    asyncio.run(backfill(apply=args.apply, force=args.force))


if __name__ == "__main__":
    main()
