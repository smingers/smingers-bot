#!/usr/bin/env python3
"""
GitHub Actions entry point for automated forecasting.

Modes:
  - aib: Forecast new questions only (skip already forecasted)
  - reforecast: Forecast new + re-forecast old questions

Usage:
  python run_bot.py --tournament 32916 --mode aib
  python run_bot.py --tournament 32917 --mode reforecast --reforecast-days 7
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.bot.forecaster import Forecaster, load_config
from src.utils.metaculus_api import MetaculusClient

logger = logging.getLogger(__name__)


async def run_forecast(
    tournament_id: str,
    mode: str = "aib",
    reforecast_days: int = 7,
    limit: int = 50,
):
    """
    Run automated forecasting for a tournament.

    Args:
        tournament_id: Tournament ID or slug (e.g., "32916", "minibench")
        mode: "aib" (new only) or "reforecast" (new + old)
        reforecast_days: For reforecast mode, re-forecast if older than this
        limit: Maximum questions to forecast per run
    """
    config = load_config("config.yaml")
    config["mode"] = "production"

    # Convert tournament_id to int if numeric
    tournament_id_parsed: int | str
    try:
        tournament_id_parsed = int(tournament_id)
    except ValueError:
        tournament_id_parsed = tournament_id  # Keep as string (e.g., "minibench")

    async with MetaculusClient() as client:
        # Get open questions
        questions = await client.get_tournament_questions(tournament_id_parsed)
        logger.info(f"Found {len(questions)} open questions in tournament {tournament_id}")

        if not questions:
            logger.info("No open questions found. Exiting.")
            return

        # Get my past forecasts
        my_forecasts = await client.get_my_forecasts(tournament_id_parsed)
        forecasted_ids = set(my_forecasts.keys()) if my_forecasts else set()
        logger.info(f"Already forecasted: {len(forecasted_ids)} questions")

        # Filter questions based on mode
        questions_to_forecast = []

        if mode == "aib":
            # AIB mode: only forecast new questions (skip already forecasted)
            for q in questions:
                if q.id not in forecasted_ids:
                    questions_to_forecast.append(q)
            logger.info(f"AIB mode: {len(questions_to_forecast)} new questions to forecast")

        elif mode == "reforecast":
            # Reforecast mode: new questions + old forecasts needing update
            cutoff = datetime.now(timezone.utc) - timedelta(days=reforecast_days)

            for q in questions:
                if q.id not in forecasted_ids:
                    # New question
                    questions_to_forecast.append(q)
                else:
                    # Check if forecast is old enough to refresh
                    my_forecast = my_forecasts.get(q.id)
                    if my_forecast and my_forecast.timestamp:
                        if my_forecast.timestamp < cutoff:
                            questions_to_forecast.append(q)
                    else:
                        # No timestamp available, include to be safe
                        questions_to_forecast.append(q)

            logger.info(f"Reforecast mode: {len(questions_to_forecast)} questions "
                       f"(new + older than {reforecast_days} days)")

        if not questions_to_forecast:
            logger.info("No questions need forecasting. Exiting.")
            return

    # Forecast questions
    questions_to_process = questions_to_forecast[:limit]
    logger.info(f"Processing {len(questions_to_process)} questions (limit: {limit})")

    success_count = 0
    error_count = 0
    errors = []

    async with Forecaster(config) as forecaster:
        for i, question in enumerate(questions_to_process):
            logger.info(f"[{i+1}/{len(questions_to_process)}] {question.title[:60]}...")

            try:
                result = await forecaster.forecast_question(question=question)
                success_count += 1

                # Log prediction based on type
                pred = result.get('prediction')
                if isinstance(pred, float):
                    logger.info(f"  -> Prediction: {pred:.1%}")
                else:
                    logger.info(f"  -> Prediction: {pred}")

            except Exception as e:
                error_count += 1
                errors.append((question.id, str(e)))
                logger.error(f"  -> FAILED: {e}")

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"FORECAST RUN COMPLETE")
    logger.info(f"  Tournament: {tournament_id}")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Errors: {error_count}")
    if errors:
        logger.info(f"  Failed questions:")
        for qid, err in errors:
            logger.info(f"    - Q{qid}: {err[:80]}")
    logger.info(f"{'='*60}")

    # Exit with error code if ALL questions failed (partial success is OK)
    if error_count > 0 and success_count == 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Actions forecasting entry point"
    )
    parser.add_argument(
        "--tournament", "-t",
        required=True,
        help="Tournament ID or slug (e.g., 32916, minibench, main-site)"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["aib", "reforecast"],
        default="aib",
        help="aib=new only, reforecast=new+refresh old"
    )
    parser.add_argument(
        "--reforecast-days",
        type=int,
        default=7,
        help="Re-forecast if older than this many days (reforecast mode only)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum questions to forecast per run"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(run_forecast(
        tournament_id=args.tournament,
        mode=args.mode,
        reforecast_days=args.reforecast_days,
        limit=args.limit,
    ))


if __name__ == "__main__":
    main()
