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
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))

from src.bot.forecaster import Forecaster, load_config
from src.bot.multiple_choice import ExtractionError
from src.utils.metaculus_api import MetaculusClient

logger = logging.getLogger(__name__)


@dataclass
class ForecastFailure:
    """Details about a failed forecast."""
    question_id: int
    question_title: str
    error_type: str
    error_message: str
    is_extraction_error: bool = False


FAILURE_LOG_PATH = Path("data/failed_forecasts.log")


@dataclass
class RunSummary:
    """Summary of a forecasting run."""
    tournament_id: str
    mode: str
    success_count: int = 0
    error_count: int = 0
    extraction_error_count: int = 0
    failures: list[ForecastFailure] = field(default_factory=list)

    def add_failure(self, question_id: int, question_title: str, error: Exception):
        is_extraction = isinstance(error, ExtractionError)
        self.failures.append(ForecastFailure(
            question_id=question_id,
            question_title=question_title[:60],
            error_type=type(error).__name__,
            error_message=str(error)[:200],
            is_extraction_error=is_extraction,
        ))
        self.error_count += 1
        if is_extraction:
            self.extraction_error_count += 1

    def write_failure_log(self):
        """Append failures to persistent log file."""
        if not self.failures:
            return

        FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(FAILURE_LOG_PATH, "a") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"RUN: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"Tournament: {self.tournament_id} | Mode: {self.mode}\n")
            f.write(f"Success: {self.success_count} | Failed: {self.error_count}\n")
            f.write(f"{'='*70}\n")

            for failure in self.failures:
                marker = "🔴 EXTRACTION" if failure.is_extraction_error else "🟡 OTHER"
                f.write(f"\n{marker} Q{failure.question_id}: {failure.question_title}\n")
                f.write(f"  {failure.error_type}: {failure.error_message}\n")

        logger.info(f"Failures logged to: {FAILURE_LOG_PATH}")

    def print_summary(self):
        """Print a prominent summary of the run."""
        print("\n" + "=" * 70)
        print("FORECAST RUN SUMMARY")
        print("=" * 70)
        print(f"Tournament: {self.tournament_id}")
        print(f"Mode: {self.mode}")
        print(f"Successful: {self.success_count}")
        print(f"Failed: {self.error_count}")

        if self.extraction_error_count > 0:
            print()
            print("!" * 70)
            print(f"⚠️  EXTRACTION ERRORS: {self.extraction_error_count}")
            print("These forecasts could not be completed because the LLM response")
            print("could not be parsed. The question was SKIPPED (not submitted).")
            print("!" * 70)

        if self.failures:
            print()
            print("-" * 70)
            print("FAILED QUESTIONS (re-run with --question <ID> to retry):")
            print("-" * 70)

            # Show extraction errors first (most important)
            extraction_failures = [f for f in self.failures if f.is_extraction_error]
            other_failures = [f for f in self.failures if not f.is_extraction_error]

            if extraction_failures:
                print("\n🔴 EXTRACTION FAILURES (LLM output parsing failed):")
                for f in extraction_failures:
                    print(f"  Q{f.question_id}: {f.question_title}")
                    print(f"    Error: {f.error_message[:100]}...")

            if other_failures:
                print("\n🟡 OTHER FAILURES:")
                for f in other_failures:
                    print(f"  Q{f.question_id}: {f.question_title}")
                    print(f"    {f.error_type}: {f.error_message[:80]}")

        print("=" * 70)

    @property
    def has_critical_failures(self) -> bool:
        """Returns True if there are extraction errors (critical failures)."""
        return self.extraction_error_count > 0


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

    summary = RunSummary(tournament_id=tournament_id, mode=mode)

    async with Forecaster(config) as forecaster:
        for i, question in enumerate(questions_to_process):
            logger.info(f"[{i+1}/{len(questions_to_process)}] {question.title[:60]}...")

            try:
                result = await forecaster.forecast_question(question=question)
                summary.success_count += 1

                # Log prediction based on type
                pred = result.get('prediction')
                if isinstance(pred, float):
                    logger.info(f"  ✓ Prediction: {pred:.1%}")
                else:
                    logger.info(f"  ✓ Prediction: {pred}")

            except ExtractionError as e:
                # Critical error - extraction failed
                summary.add_failure(question.id, question.title, e)
                logger.error(f"  ✗ EXTRACTION FAILED: {e}")

            except Exception as e:
                # Other errors
                summary.add_failure(question.id, question.title, e)
                logger.error(f"  ✗ FAILED: {e}")

    # Print prominent summary
    summary.print_summary()

    # Write failures to persistent log file
    summary.write_failure_log()

    # Exit codes:
    # 0 = all success
    # 1 = all failed OR any extraction errors (critical)
    # (partial success with non-extraction errors is considered OK)
    if summary.success_count == 0 and summary.error_count > 0:
        logger.error("All forecasts failed!")
        sys.exit(1)
    elif summary.has_critical_failures:
        logger.error(f"{summary.extraction_error_count} extraction error(s) - these questions need attention!")
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
