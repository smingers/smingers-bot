#!/usr/bin/env python3
"""
Metaculus AI Forecasting Bot - Main Entry Point

Usage:
    # Forecast a specific question by ID
    python main.py --question 12345

    # Forecast a question by URL
    python main.py --url "https://www.metaculus.com/questions/12345/..."

    # Run modes:
    #   test    - cheap models (Haiku), no submission
    #   preview - production models, no submission
    #   live    - production models, submits to Metaculus
    python main.py --question 12345 --mode test
    python main.py --question 12345 --mode preview
    python main.py --question 12345 --mode live

    # List tournament questions
    python main.py --tournament 32721 --list

    # Forecast all new questions in a tournament
    python main.py --tournament 32721 --forecast-new
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot.forecaster import Forecaster
from src.bot import ExtractionError
from src.config import ResolvedConfig
from src.runner import run_forecasts, format_prediction
from src.utils.metaculus_api import MetaculusClient


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    # Suppress noisy trafilatura warnings (failed scrapes are handled gracefully)
    logging.getLogger("trafilatura").setLevel(logging.CRITICAL)


async def list_questions(tournament_id: int | str):
    """List open questions in a tournament."""
    async with MetaculusClient() as client:
        questions = await client.get_tournament_questions(tournament_id)

        print(f"\nOpen questions in tournament {tournament_id}:")
        print("-" * 60)

        for q in questions:
            pred_str = f"(Community: {q.community_prediction:.0%})" if q.community_prediction else ""
            print(f"[{q.id}] {q.question_type:12} {q.title[:50]}... {pred_str}")

        print(f"\nTotal: {len(questions)} questions")


async def forecast_question(
    question_id: int = None,
    question_url: str = None,
    config_path: str = "config.yaml",
    dry_run: bool = False,
    mode: str = None,
):
    """Forecast a single question."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode, dry_run=dry_run)
    config = resolved.to_dict()

    try:
        async with Forecaster(resolved) as forecaster:
            result = await forecaster.forecast_question(
                question_id=question_id,
                question_url=question_url,
            )

            print(f"\n{'='*60}")
            print(f"FORECAST COMPLETE")
            print(f"{'='*60}")
            print(f"Question: {result['question'].title}")
            print(f"Type: {result['question'].question_type}")

            # Format prediction based on question type
            question_type = result['question'].question_type
            if question_type == "binary":
                print(f"Prediction: {result['prediction']:.1%}")
                agent_results = result.get('forecast_result', {}).get('agent_results', [])
                if agent_results:
                    probs = [r.probability for r in agent_results if hasattr(r, 'probability') and r.probability]
                    if probs:
                        print(f"Agent probabilities: {[f'{p:.0%}' for p in probs]}")
            elif question_type == "numeric":
                percentiles = result.get('prediction', {})
                median = percentiles.get("50", percentiles.get(50, 0))
                print(f"Prediction (median): {median:.2f}")
                p10 = percentiles.get("10", percentiles.get(10, 0))
                p90 = percentiles.get("90", percentiles.get(90, 0))
                print(f"80% CI: [{p10:.2f}, {p90:.2f}]")
            elif question_type == "multiple_choice":
                dist = result['prediction']
                best = max(dist.items(), key=lambda x: x[1])
                print(f"Prediction: {best[0]} ({best[1]:.1%})")
                print(f"Distribution: {dist}")
            else:
                print(f"Prediction: {result['prediction']}")

            print(f"Cost: ${result['costs']['total_cost']:.4f}")
            print(f"Artifacts: {result['artifacts_dir']}")

            submission = result.get('submission') or {}
            mode = config.get("mode", "test")
            if submission.get('success'):
                print("Status: SUBMITTED")
            elif mode in ("test", "preview"):
                mode_label = "TEST" if mode == "test" else "PREVIEW"
                print(f"Status: {mode_label} (not submitted)")
            else:
                print(f"Status: FAILED - {submission.get('error', 'Unknown error')}")

            return result

    except ExtractionError as e:
        print(f"\n{'!'*60}")
        print("EXTRACTION ERROR - FORECAST FAILED")
        print(f"{'!'*60}")
        print(f"\nThe LLM response could not be parsed into a valid distribution.")
        print(f"This means NO forecast was submitted.\n")
        print(f"Error: {e}")
        if e.agent_name:
            print(f"Failed agent: {e.agent_name}")
        if e.response_preview:
            print(f"\nResponse preview:\n{e.response_preview[:300]}...")
        print(f"\n{'!'*60}")
        print("To debug: Check the artifacts directory for the full LLM response.")
        print("The prompts may need adjustment for this question type.")
        print(f"{'!'*60}")
        sys.exit(1)


async def forecast_new_questions(
    tournament_id: int | str,
    config_path: str = "config.yaml",
    dry_run: bool = False,
    mode: str = None,
    limit: int = 10,
):
    """Forecast all new questions in a tournament."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode, dry_run=dry_run)
    # Modify raw config for tournament_id before converting to dict
    resolved.raw["submission"]["tournament_id"] = tournament_id

    async with MetaculusClient() as client:
        # Get all open questions
        questions = await client.get_tournament_questions(tournament_id)
        print(f"Found {len(questions)} open questions")

        # Get questions I've already forecasted
        my_forecasts = await client.get_my_forecasts(tournament_id)
        print(f"Already forecasted {len(my_forecasts)} questions")

        # Filter to new questions
        new_questions = [q for q in questions if q.id not in my_forecasts]
        print(f"New questions to forecast: {len(new_questions)}")

        if not new_questions:
            print("No new questions to forecast!")
            return

    # Use shared runner for forecast loop
    questions_to_process = new_questions[:limit]

    def on_progress(i, total, question):
        print(f"\n[{i}/{total}] Forecasting: {question.title}")

    def on_success(question, result):
        print(f"  ✓ Prediction: {format_prediction(result)}")

    def on_error(question, error):
        error_type = "EXTRACTION FAILED" if isinstance(error, ExtractionError) else "FAILED"
        print(f"  ✗ {error_type}: {error}")

    async with Forecaster(resolved) as forecaster:
        result = await run_forecasts(
            questions=questions_to_process,
            forecaster=forecaster,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
        )

    # Print summary and log failures
    result.print_summary(tournament_id=str(tournament_id))
    result.write_failure_log(strategy="batch", source="main.py", tournament_id=str(tournament_id))

    # Exit with error if any extraction errors occurred
    if result.has_extraction_errors:
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Metaculus AI Forecasting Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--question", "-q",
        type=int,
        help="Question ID to forecast"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="Question URL to forecast"
    )
    parser.add_argument(
        "--tournament", "-t",
        type=str,
        help="Tournament ID or slug (e.g., 32916, minibench)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List questions in tournament"
    )
    parser.add_argument(
        "--forecast-new",
        action="store_true",
        help="Forecast all new questions in tournament"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually submit predictions (shortcut for --mode test)"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["test", "preview", "live"],
        help="Run mode: test (cheap models, no submit), preview (production models, no submit), live (production models, submits)"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum questions to forecast with --forecast-new"
    )

    args = parser.parse_args()

    # Load environment variables (override=True ensures .env values take precedence)
    load_dotenv(override=True)

    # Setup logging
    setup_logging(args.verbose)

    # Validate arguments
    if not any([args.question, args.url, args.tournament]):
        parser.print_help()
        print("\nError: Must specify --question, --url, or --tournament")
        sys.exit(1)

    # Run appropriate command
    if args.list and args.tournament:
        asyncio.run(list_questions(args.tournament))

    elif args.forecast_new and args.tournament:
        asyncio.run(forecast_new_questions(
            tournament_id=args.tournament,
            config_path=args.config,
            dry_run=args.dry_run,
            mode=args.mode,
            limit=args.limit,
        ))

    elif args.question or args.url:
        asyncio.run(forecast_question(
            question_id=args.question,
            question_url=args.url,
            config_path=args.config,
            dry_run=args.dry_run,
            mode=args.mode,
        ))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
