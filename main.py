#!/usr/bin/env python3
"""
Metaculus AI Forecasting Bot - Main Entry Point

Usage:
    # Forecast a specific question by ID
    python main.py --question 12345

    # Forecast a question by URL
    python main.py --url "https://www.metaculus.com/questions/12345/..."

    # Run in dry-run mode (don't submit)
    python main.py --question 12345 --dry-run

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

from src.bot.forecaster import Forecaster, load_config
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


async def list_questions(tournament_id: int):
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
):
    """Forecast a single question."""
    config = load_config(config_path)

    if dry_run:
        config["submission"]["dry_run"] = True

    async with Forecaster(config) as forecaster:
        result = await forecaster.forecast_question(
            question_id=question_id,
            question_url=question_url,
        )

        print(f"\n{'='*60}")
        print(f"FORECAST COMPLETE")
        print(f"{'='*60}")
        print(f"Question: {result['question'].title}")
        print(f"Type: {result['question'].question_type}")
        print(f"Prediction: {result['prediction']:.1%}")
        print(f"Base Rate: {result['forecast_result']['base_rate']:.1%}")
        print(f"Cost: ${result['costs']['total_cost']:.4f}")
        print(f"Artifacts: {result['artifacts_dir']}")

        if result.get('submission', {}).get('success'):
            print("Status: SUBMITTED")
        elif dry_run:
            print("Status: DRY RUN (not submitted)")
        else:
            print(f"Status: FAILED - {result.get('submission', {}).get('error', 'Unknown error')}")

        return result


async def forecast_new_questions(
    tournament_id: int,
    config_path: str = "config.yaml",
    dry_run: bool = False,
    limit: int = 10,
):
    """Forecast all new questions in a tournament."""
    config = load_config(config_path)
    config["submission"]["tournament_id"] = tournament_id

    if dry_run:
        config["submission"]["dry_run"] = True

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

    # Forecast each new question
    async with Forecaster(config) as forecaster:
        for i, question in enumerate(new_questions[:limit]):
            print(f"\n[{i+1}/{min(len(new_questions), limit)}] Forecasting: {question.title}")

            try:
                result = await forecaster.forecast_question(question=question)
                print(f"  -> Prediction: {result['prediction']:.1%}")
            except Exception as e:
                print(f"  -> FAILED: {e}")


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
        type=int,
        help="Tournament ID"
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
        help="Don't actually submit predictions"
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

    # Load environment variables
    load_dotenv()

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
            limit=args.limit,
        ))

    elif args.question or args.url:
        asyncio.run(forecast_question(
            question_id=args.question,
            question_url=args.url,
            config_path=args.config,
            dry_run=args.dry_run,
        ))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
