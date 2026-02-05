#!/usr/bin/env python3
"""
AI Forecasting Bot - Main Entry Point

Supports multiple forecast sources:
- metaculus (default): Forecast on Metaculus prediction questions
- ecclesia: Forecast on Ecclesia business questions
- local: Forecast on custom questions stored as YAML files

Usage:
    # Forecast a specific question by ID
    python main.py --question 12345

    # Forecast a question by URL
    python main.py --url "https://www.metaculus.com/questions/12345/..."

    # Specify source explicitly (default: metaculus)
    python main.py --source metaculus --question 12345

    # Forecast a local question (YAML file in data/local_questions/)
    python main.py --source local --question my_question --mode test

    # Run modes:
    #   test    - fast models (Haiku), no submission
    #   preview - quality models, no submission
    #   live    - quality models, submits to Metaculus
    python main.py --question 12345 --mode test
    python main.py --question 12345 --mode preview
    python main.py --question 12345 --mode live

    # List tournament questions
    python main.py --tournament 32721 --list

    # Forecast all unforecasted questions in a tournament
    python main.py --tournament 32721 --forecast-unforecasted

    # List available sources
    python main.py --list-sources
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import ExtractionError, SubmissionError
from src.bot.forecaster import Forecaster
from src.config import ResolvedConfig
from src.runner import format_prediction, run_forecasts
from src.sources import get_source, list_sources
from src.storage.artifact_store import ArtifactStore
from src.utils.llm import LLMClient
from src.utils.metaculus_api import MetaculusClient


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Suppress noisy third-party loggers
    logging.getLogger("trafilatura").setLevel(logging.CRITICAL)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)


async def list_questions(tournament_id: int | str):
    """List open questions in a tournament."""
    async with MetaculusClient() as client:
        questions = await client.get_tournament_questions(tournament_id)

        print(f"\nOpen questions in tournament {tournament_id}:")
        print("-" * 60)

        for q in questions:
            pred_str = (
                f"(Community: {q.community_prediction:.0%})" if q.community_prediction else ""
            )
            print(f"[{q.id}] {q.question_type:12} {q.title[:50]}... {pred_str}")

        print(f"\nTotal: {len(questions)} questions")


async def forecast_question(
    question_id: int = None,
    question_url: str = None,
    config_path: str = "config.yaml",
    mode: str = None,
):
    """Forecast a single question."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode)
    config = resolved.to_dict()

    try:
        async with Forecaster(resolved) as forecaster:
            result = await forecaster.forecast_question(
                question_id=question_id,
                question_url=question_url,
            )

            print(f"\n{'=' * 60}")
            print("FORECAST COMPLETE")
            print(f"{'=' * 60}")
            print(f"Question: {result['question'].title}")
            print(f"Type: {result['question'].question_type}")

            # Format prediction based on question type
            question_type = result["question"].question_type
            if question_type == "binary":
                print(f"Prediction: {result['prediction']:.1%}")
                agent_results = result.get("forecast_result", {}).get("agent_results", [])
                if agent_results:
                    probs = [
                        r.probability
                        for r in agent_results
                        if hasattr(r, "probability") and r.probability
                    ]
                    if probs:
                        print(f"Agent probabilities: {[f'{p:.0f}%' for p in probs]}")
            elif question_type == "numeric":
                percentiles = result.get("prediction", {})
                median = percentiles.get("50", percentiles.get(50, 0))
                print(f"Prediction (median): {median:.2f}")
                p10 = percentiles.get("10", percentiles.get(10, 0))
                p90 = percentiles.get("90", percentiles.get(90, 0))
                print(f"80% CI: [{p10:.2f}, {p90:.2f}]")
            elif question_type == "multiple_choice":
                dist = result["prediction"]
                best = max(dist.items(), key=lambda option_prob: option_prob[1])
                print(f"Prediction: {best[0]} ({best[1]:.1%})")
                print(f"Distribution: {dist}")
            else:
                print(f"Prediction: {result['prediction']}")

            print(f"Cost: ${result['costs']['total_cost']:.4f}")
            print(f"Artifacts: {result['artifacts_dir']}")

            submission = result.get("submission") or {}
            mode = config.get("mode", "test")
            if submission.get("success"):
                print("Status: SUBMITTED")
            elif mode in ("test", "preview"):
                mode_label = "TEST" if mode == "test" else "PREVIEW"
                print(f"Status: {mode_label} (not submitted)")
            else:
                print(f"Status: FAILED - {submission.get('error', 'Unknown error')}")

            return result

    except ExtractionError as e:
        print(f"\n{'!' * 60}")
        print("EXTRACTION ERROR - FORECAST FAILED")
        print(f"{'!' * 60}")
        print("\nThe LLM response could not be parsed into a valid distribution.")
        print("This means NO forecast was submitted.\n")
        print(f"Error: {e}")
        if e.agent_name:
            print(f"Failed agent: {e.agent_name}")
        if e.response_preview:
            print(f"\nResponse preview:\n{e.response_preview[:300]}...")
        print(f"\n{'!' * 60}")
        print("To debug: Check the artifacts directory for the full LLM response.")
        print("The prompts may need adjustment for this question type.")
        print(f"{'!' * 60}")
        sys.exit(1)

    except SubmissionError as e:
        print(f"\n{'!' * 60}")
        print("SUBMISSION ERROR - FORECAST GENERATED BUT NOT SUBMITTED")
        print(f"{'!' * 60}")
        print("\nThe forecast was generated but could not be submitted to Metaculus.")
        print(f"Error: {e}")
        if e.status_code:
            print(f"HTTP Status: {e.status_code}")
        print(f"\n{'!' * 60}")
        print("Check your METACULUS_TOKEN and network connectivity.")
        print(f"{'!' * 60}")
        sys.exit(1)


async def forecast_ecclesia_question(
    bet_id: str,
    config_path: str = "config.yaml",
    mode: str = None,
):
    """Forecast a single Ecclesia bet using the new source architecture."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode)
    source_config = resolved.to_dict()

    # Create shared components
    llm_client = LLMClient()
    artifact_store = ArtifactStore("data", source="ecclesia")

    source = get_source("ecclesia", source_config, llm_client, artifact_store)

    try:
        async with source:
            print(f"\n{'=' * 60}")
            print(f"FORECASTING ECCLESIA BET: {bet_id}")
            print(f"Mode: {resolved.mode}")
            print(f"{'=' * 60}\n")

            # Run the forecast
            forecast = await source.run_forecast(bet_id, log=print)

            print(f"\n{'=' * 60}")
            print("FORECAST COMPLETE")
            print(f"{'=' * 60}")
            print(f"Type: {forecast.question_type}")

            # Format prediction based on type
            if forecast.question_type == "binary":
                print(f"Prediction: {forecast.prediction:.0f}%")
                # Show individual agent results
                if forecast.agent_results:
                    probs = [
                        r.probability for r in forecast.agent_results if r.probability is not None
                    ]
                    if probs:
                        print(f"Agent probabilities: {[f'{p:.0f}%' for p in probs]}")
            elif forecast.question_type == "numeric":
                print(f"Prediction (median): {forecast.prediction}")
            elif forecast.question_type == "multiple_choice":
                print(f"Prediction: {forecast.prediction}")

            print(f"Cost: ${llm_client.get_session_costs()['cost']:.4f}")

            # Submit if live mode
            if resolved.should_submit:
                print("\nSubmitting to Ecclesia...")
                converted = source.convert_forecast(forecast)
                result = await source.submit_forecast(bet_id, converted)
                print("Status: SUBMITTED")
                print(f"Response: {result}")
            else:
                mode_label = "TEST" if resolved.mode == "test" else "PREVIEW"
                print(f"\nStatus: {mode_label} (not submitted)")

            return forecast

    except Exception as e:
        print(f"\n{'!' * 60}")
        print("FORECAST FAILED")
        print(f"{'!' * 60}")
        print(f"Error: {e}")
        print(f"{'!' * 60}")
        raise


async def forecast_local_question(
    question_id: str,
    config_path: str = "config.yaml",
    mode: str = None,
):
    """Forecast a local question stored as YAML file."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode)
    source_config = resolved.to_dict()

    # Create shared components
    llm_client = LLMClient()
    artifact_store = ArtifactStore("data", source="local")

    source = get_source("local", source_config, llm_client, artifact_store)

    try:
        async with source:
            # Fetch and display question info
            question = await source.fetch_question(question_id)

            print(f"\n{'=' * 60}")
            print(f"FORECASTING LOCAL QUESTION: {question_id}")
            print(f"Title: {question.title}")
            print(f"Type: {question.question_type}")
            print(f"Mode: {resolved.mode}")
            print(f"{'=' * 60}\n")

            # Run the forecast
            forecast = await source.run_forecast(question_id, log=print)

            print(f"\n{'=' * 60}")
            print("FORECAST COMPLETE")
            print(f"{'=' * 60}")
            print(f"Question: {question.title}")
            print(f"Type: {forecast.question_type}")

            # Format prediction based on type
            if forecast.question_type == "binary":
                print(f"Prediction: {forecast.prediction:.1%}")
                # Show individual agent results
                if forecast.agent_results:
                    probs = [
                        r.probability for r in forecast.agent_results if r.probability is not None
                    ]
                    if probs:
                        # Agent probabilities are already in percentage form (0-100)
                        print(f"Agent probabilities: {[f'{p:.1f}%' for p in probs]}")
            elif forecast.question_type == "numeric":
                # For numeric, prediction is a CDF list
                if isinstance(forecast.prediction, list):
                    # Extract approximate percentiles from 201-point CDF
                    cdf = forecast.prediction
                    n = len(cdf)
                    p10_idx = int(0.10 * (n - 1))
                    p50_idx = int(0.50 * (n - 1))
                    p90_idx = int(0.90 * (n - 1))
                    print(
                        f"Prediction (CDF points): p10={cdf[p10_idx]:.3f}, p50={cdf[p50_idx]:.3f}, p90={cdf[p90_idx]:.3f}"
                    )
                else:
                    print(f"Prediction: {forecast.prediction}")
            elif forecast.question_type == "multiple_choice":
                dist = forecast.prediction
                if isinstance(dist, dict):
                    best = max(dist.items(), key=lambda x: x[1])
                    print(f"Prediction: {best[0]} ({best[1]:.1%})")
                    print(f"Distribution: {dist}")
                else:
                    print(f"Prediction: {dist}")

            print(f"Cost: ${llm_client.get_session_costs()['cost']:.4f}")

            # For local source, always "save" but indicate mode
            converted = source.convert_forecast(forecast)
            result = await source.submit_forecast(question_id, converted)
            mode_label = (
                "TEST"
                if resolved.mode == "test"
                else ("PREVIEW" if resolved.mode == "preview" else "LIVE")
            )
            print(f"\nStatus: {mode_label} - {result['message']}")

            return forecast

    except FileNotFoundError as e:
        print(f"\n{'!' * 60}")
        print("QUESTION NOT FOUND")
        print(f"{'!' * 60}")
        print(f"{e}")
        print(f"{'!' * 60}")
        sys.exit(1)

    except Exception as e:
        print(f"\n{'!' * 60}")
        print("FORECAST FAILED")
        print(f"{'!' * 60}")
        print(f"Error: {e}")
        print(f"{'!' * 60}")
        raise


async def forecast_kalshi_question(
    question_id: str,
    config_path: str = "config.yaml",
    mode: str = None,
):
    """Forecast a Kalshi prediction market event."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode)
    source_config = resolved.to_dict()

    # Create shared components
    llm_client = LLMClient()
    artifact_store = ArtifactStore("data", source="kalshi")

    source = get_source("kalshi", source_config, llm_client, artifact_store)

    try:
        async with source:
            print(f"\n{'=' * 60}")
            print(f"FORECASTING KALSHI EVENT: {question_id}")
            print(f"Mode: {resolved.mode}")
            print(f"{'=' * 60}\n")

            # Run the forecast (also returns the fetched question)
            forecast, question = await source.run_forecast(question_id, log=print)
            market_prices = question.raw.get("market_prices", {})

            print(f"\n{'=' * 60}")
            print("FORECAST COMPLETE")
            print(f"{'=' * 60}")
            print(f"Question: {question.title}")
            print(f"Type: {forecast.question_type} ({len(question.options)} options)")

            # Display comparison table: Bot vs Kalshi market prices
            dist = forecast.prediction
            if isinstance(dist, dict):
                print(f"\n{'Candidate':<30s} {'Bot':>8s} {'Kalshi':>8s} {'Delta':>8s}")
                print("-" * 58)

                # Sort by bot probability descending
                sorted_options = sorted(dist.items(), key=lambda x: x[1], reverse=True)
                for option_name, bot_prob in sorted_options:
                    prices = market_prices.get(option_name, {})
                    kalshi_prob = prices.get("implied_probability", 0)
                    delta = bot_prob - kalshi_prob
                    print(f"{option_name:<30s} {bot_prob:>7.1%} {kalshi_prob:>7.1%} {delta:>+7.1%}")
            else:
                print(f"Prediction: {dist}")

            print(f"\nCost: ${llm_client.get_session_costs()['cost']:.4f}")

            # Save locally
            converted = source.convert_forecast(forecast)
            result = await source.submit_forecast(question_id, converted)
            mode_label = (
                "TEST"
                if resolved.mode == "test"
                else ("PREVIEW" if resolved.mode == "preview" else "LIVE")
            )
            print(f"\nStatus: {mode_label} - {result['message']}")

            return forecast

    except Exception as e:
        print(f"\n{'!' * 60}")
        print("FORECAST FAILED")
        print(f"{'!' * 60}")
        print(f"Error: {e}")
        print(f"{'!' * 60}")
        raise


async def forecast_unforecasted_questions(
    tournament_id: int | str,
    config_path: str = "config.yaml",
    mode: str = None,
    limit: int = 10,
):
    """Forecast questions in a tournament that I haven't forecasted yet."""
    resolved = ResolvedConfig.from_yaml(config_path, mode=mode)
    # Modify raw config for tournament_id before converting to dict
    resolved.source["submission"]["tournament_id"] = tournament_id

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
    result.write_failure_log(source="main.py", tournament_id=str(tournament_id))

    # Exit with error if any extraction errors occurred
    if result.has_extraction_errors:
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Metaculus AI Forecasting Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default="metaculus",
        help="Forecast source: metaculus (default), ecclesia, local, kalshi",
    )
    parser.add_argument(
        "--list-sources", action="store_true", help="List available forecast sources"
    )
    parser.add_argument("--question", "-q", type=str, help="Question/bet ID to forecast")
    parser.add_argument("--url", "-u", type=str, help="Question URL to forecast")
    parser.add_argument(
        "--tournament", "-t", type=str, help="Tournament ID or slug (e.g., 32916, minibench)"
    )
    parser.add_argument("--list", "-l", action="store_true", help="List questions in tournament")
    parser.add_argument(
        "--forecast-unforecasted",
        action="store_true",
        help="Forecast all unforecasted questions in tournament",
    )
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=["test", "preview", "live"],
        help="Run mode: test (fast models, no submit), preview (quality models, no submit), live (quality models, submits)",
    )
    parser.add_argument(
        "--config", "-c", type=str, default="config.yaml", help="Path to config file"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum questions to forecast with --forecast-unforecasted",
    )

    args = parser.parse_args()

    # Load environment variables (override=True ensures .env values take precedence)
    load_dotenv(override=True)

    # Setup logging
    setup_logging(args.verbose)

    # Handle --list-sources
    if args.list_sources:
        print("\nAvailable forecast sources:")
        for source_name in list_sources():
            default_marker = " (default)" if source_name == "metaculus" else ""
            print(f"  - {source_name}{default_marker}")
        sys.exit(0)

    # Validate arguments
    if not any([args.question, args.url, args.tournament]):
        parser.print_help()
        print("\nError: Must specify --question, --url, or --tournament")
        sys.exit(1)

    # Validate source
    available_sources = list_sources()
    if args.source not in available_sources:
        print(f"\nError: Unknown source '{args.source}'. Available: {', '.join(available_sources)}")
        sys.exit(1)

    # Run appropriate command
    if args.list and args.tournament:
        asyncio.run(list_questions(args.tournament))

    elif args.forecast_unforecasted and args.tournament:
        asyncio.run(
            forecast_unforecasted_questions(
                tournament_id=args.tournament,
                config_path=args.config,
                mode=args.mode,
                limit=args.limit,
            )
        )

    elif args.question or args.url:
        if args.source == "ecclesia":
            # Ecclesia uses bet IDs (strings), not integer question IDs
            bet_id = str(args.question) if args.question else args.url
            asyncio.run(
                forecast_ecclesia_question(
                    bet_id=bet_id,
                    config_path=args.config,
                    mode=args.mode,
                )
            )
        elif args.source == "local":
            # Local source uses string question IDs (filename or explicit id)
            question_id = str(args.question) if args.question else args.url
            asyncio.run(
                forecast_local_question(
                    question_id=question_id,
                    config_path=args.config,
                    mode=args.mode,
                )
            )
        elif args.source == "kalshi":
            # Kalshi uses event tickers or URLs
            question_id = str(args.question) if args.question else args.url
            asyncio.run(
                forecast_kalshi_question(
                    question_id=question_id,
                    config_path=args.config,
                    mode=args.mode,
                )
            )
        else:
            # Default: Metaculus source (expects integer question IDs)
            question_id = int(args.question) if args.question else None
            asyncio.run(
                forecast_question(
                    question_id=question_id,
                    question_url=args.url,
                    config_path=args.config,
                    mode=args.mode,
                )
            )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
