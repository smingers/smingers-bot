#!/usr/bin/env python3
"""
GitHub Actions entry point for automated forecasting.

Question selection modes:
  - new-only: Forecast new questions only (skip already forecasted)
  - reforecast: Forecast new + re-forecast old questions

Usage:
  python run_bot.py --tournament 32916 --question-selection new-only
  python run_bot.py --tournament 32917 --question-selection reforecast --reforecast-threshold-days 7
"""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.bot import ExtractionError, SubmissionError
from src.bot.forecaster import Forecaster
from src.config import ResolvedConfig
from src.runner import format_prediction, run_forecasts
from src.sources import get_source, list_sources
from src.utils.metaculus_api import MetaculusClient

logger = logging.getLogger(__name__)


async def forecast_metaculus_questions(
    tournament_id: str,
    question_selection: str = "new-only",
    reforecast_threshold_days: int = 7,
    limit: int = 50,
    source_name: str = "metaculus",
):
    """
    Run automated forecasting for Metaculus questions from a tournament.

    Args:
        tournament_id: Tournament ID or slug (e.g., "32916", "minibench")
        question_selection: "new-only" (new questions only) or "reforecast" (new + old)
        reforecast_threshold_days: For reforecast mode, re-forecast questions older than this
        limit: Maximum questions to forecast per run
        source_name: Question source (default: "metaculus")

    Returns:
        Number of new/unforecasted questions that were available (0 if none or early exit).
        Used by CI to decide whether to run lower-priority tournaments.
    """
    resolved = ResolvedConfig.from_yaml("config.yaml", mode="live")

    # Get the source (defaults to Metaculus)
    source = get_source(source_name) if source_name else None

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
            return 0

        # Get my past forecasts
        my_forecasts = await client.get_my_forecasts(tournament_id_parsed)
        forecasted_ids = set(my_forecasts.keys()) if my_forecasts else set()
        logger.info(f"Already forecasted: {len(forecasted_ids)} questions")

        # Filter questions based on question_selection
        questions_to_forecast = []

        if question_selection == "new-only":
            # New-only mode: only forecast new questions (skip already forecasted)
            for q in questions:
                if q.id not in forecasted_ids:
                    questions_to_forecast.append(q)
            logger.info(f"new-only: {len(questions_to_forecast)} new questions to forecast")

        elif question_selection == "reforecast":
            # Reforecast mode: new questions + old forecasts needing update
            cutoff = datetime.now(UTC) - timedelta(days=reforecast_threshold_days)

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

            logger.info(
                f"reforecast: {len(questions_to_forecast)} questions "
                f"(new + older than {reforecast_threshold_days} days)"
            )

        if not questions_to_forecast:
            logger.info("No questions need forecasting. Exiting.")
            return 0

    # Forecast questions using shared runner
    questions_to_process = questions_to_forecast[:limit]
    logger.info(f"Processing {len(questions_to_process)} questions (limit: {limit})")

    def on_progress(i, total, question):
        logger.info(f"[{i}/{total}] {question.title[:60]}...")

    def on_success(question, result):
        logger.info(f"  ✓ Prediction: {format_prediction(result)}")

    def on_error(question, error):
        if isinstance(error, ExtractionError):
            error_type = "EXTRACTION FAILED"
        elif isinstance(error, SubmissionError):
            error_type = "SUBMISSION FAILED"
        else:
            error_type = "FAILED"
        logger.error(f"  ✗ {error_type}: {error}")

    async with Forecaster(resolved, source=source) as forecaster:
        result = await run_forecasts(
            questions=questions_to_process,
            forecaster=forecaster,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
        )

    # Print summary and log failures
    result.print_summary(tournament_id=tournament_id, question_selection=question_selection)
    result.write_failure_log(
        question_selection=question_selection, source="run_bot.py", tournament_id=tournament_id
    )

    # Exit codes:
    # 0 = all success
    # 1 = all failed OR any critical errors (extraction or submission)
    # (partial success with non-critical errors is considered OK)
    if result.success_count == 0 and result.error_count > 0:
        logger.error("All forecasts failed!")
        sys.exit(1)
    elif result.has_critical_errors:
        if result.has_extraction_errors:
            logger.error(
                f"{result.extraction_error_count} extraction error(s) - these questions need attention!"
            )
        if result.has_submission_errors:
            logger.error(
                f"{result.submission_error_count} submission error(s) - forecasts generated but NOT submitted!"
            )
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="GitHub Actions forecasting entry point")
    parser.add_argument(
        "--tournament",
        "-t",
        required=True,
        help="Tournament ID or slug (e.g., 32916, spring-aib-2026)",
    )
    parser.add_argument(
        "--question-selection",
        "-s",
        choices=["new-only", "reforecast"],
        default="new-only",
        help="new-only=forecast new questions only, reforecast=new+refresh old",
    )
    parser.add_argument(
        "--reforecast-threshold-days",
        type=int,
        default=7,
        help="Re-forecast questions older than this many days (reforecast mode only)",
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Maximum questions to forecast per run"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="metaculus",
        choices=list_sources(),
        help="Question source (default: metaculus)"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # Suppress noisy trafilatura warnings (failed scrapes are handled gracefully)
    logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

    asyncio.run(
        forecast_metaculus_questions(
            tournament_id=args.tournament,
            question_selection=args.question_selection,
            reforecast_threshold_days=args.reforecast_threshold_days,
            limit=args.limit,
            source_name=args.source,
        )
    )


if __name__ == "__main__":
    main()
