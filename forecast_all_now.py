#!/usr/bin/env python3
"""
Emergency script: Forecast all NEW (unforecasted) questions in a tournament.

Usage:
    python forecast_all_now.py --tournament 32916
    python forecast_all_now.py --tournament 32916 --dry-run  # Test first
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from src.bot.forecaster import Forecaster
from src.bot import ExtractionError
from src.config import ResolvedConfig
from src.runner import run_forecasts, format_prediction
from src.utils.metaculus_api import MetaculusClient

logger = logging.getLogger(__name__)


async def forecast_all(
    tournament_id: str,
    dry_run: bool = False,
    limit: int = 100,
):
    """Forecast all NEW (unforecasted) questions."""
    resolved = ResolvedConfig.from_yaml("config.yaml", mode="production")

    # Override dry_run if requested
    if dry_run:
        resolved = ResolvedConfig.from_yaml("config.yaml", mode="dry_run_heavy")

    # Convert tournament_id to int if numeric
    tournament_id_parsed: int | str
    try:
        tournament_id_parsed = int(tournament_id)
    except ValueError:
        tournament_id_parsed = tournament_id

    async with MetaculusClient() as client:
        # Get ALL open questions
        questions = await client.get_tournament_questions(tournament_id_parsed)
        logger.info(f"Found {len(questions)} open questions in tournament {tournament_id}")

        if not questions:
            logger.info("No open questions found. Exiting.")
            return

        # Check what we've already forecasted
        my_forecasts = await client.get_my_forecasts(tournament_id_parsed)
        forecasted_ids = set(my_forecasts.keys()) if my_forecasts else set()
        logger.info(f"Already forecasted: {len(forecasted_ids)} questions")

        # Filter to NEW questions only
        new_questions = [q for q in questions if q.id not in forecasted_ids]
        logger.info(f"NEW questions to forecast: {len(new_questions)}")

        if not new_questions:
            logger.info("No new questions to forecast!")
            return

    # Forecast new questions
    questions_to_process = new_questions[:limit]
    logger.info(f"Processing {len(questions_to_process)} questions (limit: {limit})")

    def on_progress(i, total, question):
        logger.info(f"[{i}/{total}] {question.title[:60]}...")

    def on_success(question, result):
        logger.info(f"  ✓ Prediction: {format_prediction(result)}")

    def on_error(question, error):
        error_type = "EXTRACTION FAILED" if isinstance(error, ExtractionError) else "FAILED"
        logger.error(f"  ✗ {error_type}: {error}")

    async with Forecaster(resolved) as forecaster:
        result = await run_forecasts(
            questions=questions_to_process,
            forecaster=forecaster,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
        )

    # Print summary
    result.print_summary(tournament_id=tournament_id, mode="production" if not dry_run else "dry_run_heavy")
    result.write_failure_log(mode="production", source="forecast_all_now.py", tournament_id=tournament_id)

    if result.success_count == 0 and result.error_count > 0:
        logger.error("All forecasts failed!")
        sys.exit(1)
    elif result.has_extraction_errors:
        logger.error(f"{result.extraction_error_count} extraction error(s)")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Forecast all NEW questions in a tournament")
    parser.add_argument("--tournament", "-t", required=True, help="Tournament ID or slug")
    parser.add_argument("--dry-run", action="store_true", help="Don't submit (use production models but skip submission)")
    parser.add_argument("--limit", type=int, default=100, help="Max questions to forecast")

    args = parser.parse_args()

    load_dotenv(override=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

    print(f"\n{'='*60}")
    print("FORECAST ALL NEW QUESTIONS")
    print(f"{'='*60}")
    print(f"Tournament: {args.tournament}")
    print(f"Mode: {'DRY RUN (no submission)' if args.dry_run else 'PRODUCTION (will submit)'}")
    print(f"Limit: {args.limit}")
    print(f"{'='*60}\n")

    asyncio.run(forecast_all(
        tournament_id=args.tournament,
        dry_run=args.dry_run,
        limit=args.limit,
    ))


if __name__ == "__main__":
    main()
