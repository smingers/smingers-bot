"""
Shared forecast runner for batch forecasting operations.

Provides a unified forecast loop used by both main.py and run_bot.py,
ensuring consistent behavior for error handling, logging, and result tracking.

Usage:
    from src.runner import run_forecasts, RunResult

    result = await run_forecasts(
        questions=questions,
        forecaster=forecaster,
        on_progress=lambda i, total, q: print(f"[{i}/{total}] {q.title}"),
    )
    print(f"Success: {result.success_count}, Failed: {result.error_count}")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .bot import ExtractionError
from .bot.forecaster import Forecaster
from .utils.metaculus_api import MetaculusQuestion

logger = logging.getLogger(__name__)

FAILURE_LOG_PATH = Path("data/failed_forecasts.log")


@dataclass
class ForecastFailure:
    """Details about a failed forecast."""

    question_id: int
    question_title: str
    error_type: str
    error_message: str
    is_extraction_error: bool = False


@dataclass
class RunResult:
    """
    Result of a batch forecasting run.

    Tracks successes, failures, and provides methods for logging and summarization.
    """

    success_count: int = 0
    error_count: int = 0
    extraction_error_count: int = 0
    failures: list[ForecastFailure] = field(default_factory=list)
    successful_results: list[dict[str, Any]] = field(default_factory=list)

    def add_success(self, result: dict[str, Any]) -> None:
        """Record a successful forecast."""
        self.success_count += 1
        self.successful_results.append(result)

    def add_failure(self, question_id: int, question_title: str, error: Exception) -> None:
        """Record a failed forecast."""
        is_extraction = isinstance(error, ExtractionError)
        self.failures.append(
            ForecastFailure(
                question_id=question_id,
                question_title=question_title[:60],
                error_type=type(error).__name__,
                error_message=str(error)[:200],
                is_extraction_error=is_extraction,
            )
        )
        self.error_count += 1
        if is_extraction:
            self.extraction_error_count += 1

    @property
    def has_extraction_errors(self) -> bool:
        """Returns True if there are extraction errors (critical failures)."""
        return self.extraction_error_count > 0

    @property
    def total_count(self) -> int:
        """Total number of questions processed."""
        return self.success_count + self.error_count

    def write_failure_log(
        self,
        source: str = "runner",
        tournament_id: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> None:
        """
        Append failures to persistent log file.

        Args:
            source: Identifier for the calling entry point (e.g., "main.py", "run_bot.py")
            tournament_id: Optional tournament ID for context
            strategy: Optional run strategy (e.g., "new-only", "reforecast") - only for run_bot.py
        """
        if not self.failures:
            return

        FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(FAILURE_LOG_PATH, "a") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"RUN: {datetime.now(timezone.utc).isoformat()}\n")
            header_parts = []
            if tournament_id:
                header_parts.append(f"Tournament: {tournament_id}")
            if strategy:
                header_parts.append(f"Strategy: {strategy}")
            header_parts.append(f"Via: {source}")
            f.write(" | ".join(header_parts) + "\n")
            f.write(f"Success: {self.success_count} | Failed: {self.error_count}\n")
            f.write(f"{'='*70}\n")

            for failure in self.failures:
                marker = "🔴 EXTRACTION" if failure.is_extraction_error else "🟡 OTHER"
                f.write(f"\n{marker} Q{failure.question_id}: {failure.question_title}\n")
                f.write(f"  {failure.error_type}: {failure.error_message}\n")

        logger.info(f"Failures logged to: {FAILURE_LOG_PATH}")

    def print_summary(self, tournament_id: Optional[str] = None, strategy: Optional[str] = None) -> None:
        """
        Print a summary of the run to stdout.

        Args:
            tournament_id: Optional tournament ID to include in summary
            strategy: Optional strategy (e.g., "new-only", "reforecast") to include in summary
        """
        print("\n" + "=" * 70)
        print("FORECAST RUN SUMMARY")
        print("=" * 70)
        if tournament_id:
            print(f"Tournament: {tournament_id}")
        if strategy:
            print(f"Strategy: {strategy}")
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


# Type alias for progress callback
ProgressCallback = Callable[[int, int, MetaculusQuestion], None]
SuccessCallback = Callable[[MetaculusQuestion, dict[str, Any]], None]
ErrorCallback = Callable[[MetaculusQuestion, Exception], None]


async def run_forecasts(
    questions: list[MetaculusQuestion],
    forecaster: Forecaster,
    on_progress: Optional[ProgressCallback] = None,
    on_success: Optional[SuccessCallback] = None,
    on_error: Optional[ErrorCallback] = None,
) -> RunResult:
    """
    Run forecasts for a list of questions with unified error handling.

    This is the core forecast loop shared by both entry points. It handles:
    - Iterating through questions
    - Calling forecaster.forecast_question()
    - Tracking successes and failures (extraction vs other errors)
    - Progress callbacks for logging

    Args:
        questions: List of questions to forecast
        forecaster: Initialized Forecaster instance
        on_progress: Optional callback called before each forecast: (index, total, question)
        on_success: Optional callback called after successful forecast: (question, result)
        on_error: Optional callback called after failed forecast: (question, exception)

    Returns:
        RunResult with success/failure counts and details
    """
    result = RunResult()
    total = len(questions)

    for i, question in enumerate(questions):
        # Progress callback (1-indexed for display)
        if on_progress:
            on_progress(i + 1, total, question)

        try:
            forecast_result = await forecaster.forecast_question(question=question)
            result.add_success(forecast_result)

            if on_success:
                on_success(question, forecast_result)

        except ExtractionError as e:
            result.add_failure(question.id, question.title, e)
            logger.error(f"Extraction failed for Q{question.id}: {e}")

            if on_error:
                on_error(question, e)

        except Exception as e:
            result.add_failure(question.id, question.title, e)
            logger.error(f"Forecast failed for Q{question.id}: {e}")

            if on_error:
                on_error(question, e)

    return result


def format_prediction(result: dict[str, Any]) -> str:
    """
    Format a prediction result for display.

    Args:
        result: Forecast result dict containing 'question' and 'prediction'

    Returns:
        Human-readable string representation of the prediction
    """
    question = result.get("question")
    prediction = result.get("prediction")

    if question is None or prediction is None:
        return str(prediction)

    question_type = question.question_type

    if question_type == "binary":
        if isinstance(prediction, (int, float)):
            return f"{prediction:.1%}"
        return str(prediction)

    elif question_type == "numeric":
        if isinstance(prediction, dict):
            median = prediction.get("50", prediction.get(50, "N/A"))
            if isinstance(median, (int, float)):
                return f"median: {median:.2f}"
            return f"median: {median}"
        return str(prediction)

    elif question_type == "multiple_choice":
        if isinstance(prediction, dict) and prediction:
            best = max(prediction.items(), key=lambda x: x[1])
            return f"{best[0]} ({best[1]:.1%})"
        return str(prediction)

    return str(prediction)
