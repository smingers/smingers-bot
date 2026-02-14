"""
Resume a completed forecast run and execute only the supervisor step.

Loads all artifacts from a previous run (question metadata, forecaster predictions,
reasoning, aggregation) and runs the supervisor agent to produce an updated forecast,
then submits the result to Metaculus.

Usage:
    python scripts/resume_supervisor.py data/42035_20260214_020230 --mode live
    python scripts/resume_supervisor.py data/42035_20260214_020230 --mode preview  # no submit
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.cdf import generate_continuous_cdf  # noqa: E402
from src.bot.supervisor import SupervisorAgent, SupervisorInput  # noqa: E402
from src.config import load_config  # noqa: E402
from src.utils.llm import LLMClient, get_cost_tracker  # noqa: E402
from src.utils.metaculus_api import MetaculusClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def load_artifacts(artifact_dir: str) -> dict:
    """Load all relevant artifacts from a previous forecast run."""
    artifact_path = Path(artifact_dir)

    # Load question metadata
    question_path = artifact_path / "question.json"
    if not question_path.exists():
        raise FileNotFoundError(f"No question.json found in {artifact_dir}")
    with open(question_path) as f:
        question_data = json.load(f)

    # Load forecaster predictions and reasoning
    ensemble_dir = artifact_path / "ensemble"
    forecasters = []
    for i in range(1, 6):
        pred_path = ensemble_dir / f"forecaster_{i}.json"
        reasoning_path = ensemble_dir / f"forecaster_{i}_inside_view.md"

        if not pred_path.exists():
            logger.warning(f"Missing forecaster_{i}.json, skipping")
            continue

        with open(pred_path) as f:
            pred_data = json.load(f)

        reasoning = ""
        if reasoning_path.exists():
            with open(reasoning_path) as f:
                reasoning = f.read()

        forecasters.append(
            {
                "agent_id": f"forecaster_{i}",
                "model": f"forecaster_{i}",  # We don't have the model name in artifacts
                "prediction": pred_data.get("percentiles")
                or pred_data.get("probability")
                or pred_data.get("probabilities"),
                "reasoning": reasoning,
            }
        )

    # Load aggregation
    agg_path = ensemble_dir / "aggregation.json"
    if not agg_path.exists():
        raise FileNotFoundError(f"No aggregation.json found in {ensemble_dir}")
    with open(agg_path) as f:
        aggregation_data = json.load(f)

    return {
        "question": question_data,
        "forecasters": forecasters,
        "aggregation": aggregation_data,
    }


def build_supervisor_input(artifacts: dict) -> SupervisorInput:
    """Build a SupervisorInput from loaded artifacts."""
    question = artifacts["question"]
    q = question.get("question", {})

    # Determine question type
    question_type = q.get("type", "numeric")

    # Build weighted average prediction (the current final prediction)
    # For numeric, this is the full CDF or percentiles
    agg = artifacts["aggregation"]
    weighted_avg = agg.get("final_prediction") or agg.get("final_cdf_sample")

    # Get question scaling info
    scaling = q.get("scaling", {})

    # Build bounds info string
    bounds_info = (
        f"Range: {scaling.get('range_min')} to {scaling.get('range_max')}, "
        f"Open lower bound: {scaling.get('open_lower_bound', True)}, "
        f"Open upper bound: {scaling.get('open_upper_bound', True)}"
    )
    if scaling.get("zero_point") is not None:
        bounds_info += f", Zero point: {scaling['zero_point']}"

    return SupervisorInput(
        question_title=question.get("title", q.get("title", "")),
        question_type=question_type,
        resolution_criteria=q.get("resolution_criteria", ""),
        fine_print=q.get("fine_print", ""),
        background=q.get("description", ""),
        open_time=q.get("open_time", ""),
        scheduled_resolve_time=q.get("scheduled_resolve_time", ""),
        today=str(asyncio.get_event_loop().time()),  # Will be replaced
        forecaster_predictions=artifacts["forecasters"],
        weighted_average_prediction=weighted_avg,
        options=q.get("options"),
        num_options=len(q.get("options") or []) or None,
        units=q.get("unit"),
        bounds_info=bounds_info,
    )


async def run_supervisor_and_submit(
    artifact_dir: str,
    mode: str = "preview",
) -> None:
    """Load artifacts, run supervisor, optionally submit."""
    logger.info(f"Loading artifacts from {artifact_dir}")
    artifacts = load_artifacts(artifact_dir)

    question = artifacts["question"]
    q = question.get("question", {})
    question_type = q.get("type", "numeric")

    logger.info(f"Question: {question.get('title', q.get('title', 'Unknown'))}")
    logger.info(f"Type: {question_type}")
    logger.info(f"Forecasters loaded: {len(artifacts['forecasters'])}")

    # Load config
    config = load_config()
    # Set the mode so supervisor resolves the right model
    config["mode"] = mode
    supervisor_config = config.get("supervisor", {})
    model_config = supervisor_config.get("model", {})
    if mode in ("preview", "live"):
        supervisor_model = model_config.get("quality", "openrouter/anthropic/claude-opus-4.6")
    else:
        supervisor_model = model_config.get("fast", "openrouter/anthropic/claude-3.5-haiku")
    logger.info(f"Supervisor model: {supervisor_model}")

    # Build supervisor input
    from datetime import datetime

    supervisor_input = build_supervisor_input(artifacts)
    # Fix the today field
    supervisor_input.today = datetime.now(UTC).strftime("%Y-%m-%d")

    logger.info("\nForecaster predictions:")
    for fp in artifacts["forecasters"]:
        logger.info(f"  {fp['agent_id']}: {fp['prediction']}")

    # Run supervisor
    logger.info("\n=== Running Supervisor ===")
    cost_tracker = get_cost_tracker()
    llm = LLMClient(cost_tracker)
    supervisor = SupervisorAgent(config, llm)
    result = await supervisor.evaluate(supervisor_input)

    logger.info("\nSupervisor Results:")
    logger.info(f"  Confidence: {result.confidence}")
    logger.info(f"  Prediction: {result.updated_prediction}")
    logger.info(f"  Cost: ${result.cost:.4f}")

    if result.error:
        logger.error(f"  Error: {result.error}")
        return

    # Save supervisor artifacts
    ensemble_dir = Path(artifact_dir) / "ensemble"
    with open(ensemble_dir / "supervisor_analysis.md", "w") as f:
        f.write(result.disagreement_analysis)
    if result.search_context:
        with open(ensemble_dir / "supervisor_research.md", "w") as f:
            f.write(result.search_context)
    with open(ensemble_dir / "supervisor_reasoning.md", "w") as f:
        f.write(result.reasoning)
    with open(ensemble_dir / "supervisor_result.json", "w") as f:
        json.dump(
            {
                "confidence": result.confidence,
                "prediction": result.updated_prediction,
                "search_queries": result.search_queries,
                "cost": result.cost,
            },
            f,
            indent=2,
        )

    logger.info(f"\nSupervisor artifacts saved to {ensemble_dir}")

    # For numeric questions, convert percentiles to CDF
    if question_type == "numeric":
        scaling = q.get("scaling", {})
        percentiles = result.updated_prediction

        if not isinstance(percentiles, dict):
            logger.error(f"Expected percentiles dict, got {type(percentiles)}: {percentiles}")
            return

        logger.info("\nConverting percentiles to CDF:")
        logger.info(f"  Percentiles: {percentiles}")
        logger.info(f"  Range: [{scaling.get('range_min')}, {scaling.get('range_max')}]")
        logger.info(
            f"  Open bounds: lower={scaling.get('open_lower_bound')}, upper={scaling.get('open_upper_bound')}"
        )

        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=scaling.get("open_upper_bound", True),
            open_lower_bound=scaling.get("open_lower_bound", True),
            upper_bound=scaling.get("range_max"),
            lower_bound=scaling.get("range_min"),
            zero_point=scaling.get("zero_point"),
            num_points=201,
        )

        logger.info(f"  CDF generated: {len(cdf)} points")
        logger.info(f"  CDF range: [{cdf[0]:.6f}, {cdf[-1]:.6f}]")
        submission_prediction = cdf
    else:
        submission_prediction = result.updated_prediction

    # Submit if live mode
    if mode == "live":
        logger.info("\n=== Submitting to Metaculus ===")
        api = MetaculusClient()

        question_id = q.get("id")  # This is the question ID (not post ID)
        if not question_id:
            logger.error("No question ID found in question data")
            return

        logger.info(f"  Question ID: {question_id}")

        if question_type == "numeric":
            response = await api.submit_numeric_prediction(
                question_id=question_id,
                cdf=submission_prediction,
                open_lower_bound=scaling.get("open_lower_bound", True),
                open_upper_bound=scaling.get("open_upper_bound", True),
                expected_cdf_size=201,
            )
        elif question_type == "binary":
            response = await api.submit_binary_prediction(
                question_id=question_id,
                probability=submission_prediction,
            )
        else:
            logger.error(f"Submission for {question_type} not yet supported in this script")
            return

        logger.info(f"  Submission response: {response}")
        logger.info("  ✓ Submitted successfully!")
    else:
        logger.info(f"\n[{mode} mode] Skipping submission. Use --mode live to submit.")


def main():
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Resume supervisor from existing artifacts")
    parser.add_argument(
        "artifact_dir", help="Path to the artifact directory (e.g., data/42035_20260214_020230)"
    )
    parser.add_argument(
        "--mode",
        choices=["test", "preview", "live"],
        default="preview",
        help="Mode: test (cheap model), preview (quality, no submit), live (quality + submit)",
    )
    args = parser.parse_args()

    asyncio.run(run_supervisor_and_submit(args.artifact_dir, args.mode))


if __name__ == "__main__":
    main()
