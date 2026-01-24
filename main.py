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


def apply_mode_to_config(config: dict, mode: str = None, dry_run: bool = False) -> dict:
    """
    Apply run mode to config, selecting appropriate models and submission settings.

    Modes:
    - dry_run: Cheap models, no submission
    - dry_run_heavy: Production models, no submission
    - production: Production models, submits to Metaculus
    """
    # Determine effective mode
    if mode:
        effective_mode = mode
    elif dry_run:
        effective_mode = "dry_run"
    else:
        effective_mode = config.get("mode", "dry_run")

    # Select model tier based on mode
    model_tier = "cheap" if effective_mode == "dry_run" else "production"

    # Apply models
    if "models" in config and model_tier in config["models"]:
        config["_active_models"] = config["models"][model_tier]
    else:
        # Fallback for old config format
        config["_active_models"] = config.get("models", {})

    # Apply ensemble agents
    if "ensemble" in config and model_tier in config["ensemble"]:
        config["_active_agents"] = config["ensemble"][model_tier]
    else:
        # Fallback for old config format
        config["_active_agents"] = config.get("ensemble", {}).get("agents", [])

    # Set submission behavior
    config["_should_submit"] = (effective_mode == "production")
    config["_effective_mode"] = effective_mode

    return config


async def forecast_question(
    question_id: int = None,
    question_url: str = None,
    config_path: str = "config.yaml",
    dry_run: bool = False,
    mode: str = None,
):
    """Forecast a single question."""
    config = load_config(config_path)
    config = apply_mode_to_config(config, mode=mode, dry_run=dry_run)

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

        # Format prediction based on question type
        question_type = result['question'].question_type
        if question_type == "binary":
            print(f"Prediction: {result['prediction']:.1%}")
            print(f"Base Rate: {result['forecast_result']['base_rate']:.1%}")
        elif question_type == "numeric":
            median = result['prediction'].get(50, 0)
            base_median = result['forecast_result'].get('base_percentiles', {}).get(50, 0)
            print(f"Prediction (median): {median:.2f}")
            print(f"Base Rate (median): {base_median:.2f}")
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
        effective_mode = config.get("_effective_mode", "dry_run")
        if submission.get('success'):
            print("Status: SUBMITTED")
        elif effective_mode in ("dry_run", "dry_run_heavy"):
            mode_label = "DRY RUN" if effective_mode == "dry_run" else "DRY RUN (heavy models)"
            print(f"Status: {mode_label} (not submitted)")
        else:
            print(f"Status: FAILED - {submission.get('error', 'Unknown error')}")

        return result


async def forecast_new_questions(
    tournament_id: int,
    config_path: str = "config.yaml",
    dry_run: bool = False,
    mode: str = None,
    limit: int = 10,
):
    """Forecast all new questions in a tournament."""
    config = load_config(config_path)
    config["submission"]["tournament_id"] = tournament_id
    config = apply_mode_to_config(config, mode=mode, dry_run=dry_run)

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
        help="Don't actually submit predictions (shortcut for --mode dry_run)"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["dry_run", "dry_run_heavy", "production"],
        help="Run mode: dry_run (cheap models, no submit), dry_run_heavy (production models, no submit), production (production models, submits)"
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
