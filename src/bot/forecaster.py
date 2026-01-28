"""
Main Forecaster Orchestration

Simplified pipeline that delegates to type-specific handlers:
1. Fetch question from Metaculus
2. Route to appropriate handler (binary/numeric/multiple_choice)
3. Handler does all research + forecasting internally
4. Save final prediction
5. Submit if not dry_run
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Optional, Union
from datetime import datetime, timezone

from ..config import ResolvedConfig
from ..utils.llm import LLMClient, get_cost_tracker, reset_cost_tracker
from ..utils.metaculus_api import MetaculusClient, MetaculusQuestion
from ..storage.artifact_store import ArtifactStore, ForecastArtifacts
from ..storage.database import ForecastDatabase, ForecastRecord, AgentPredictionRecord

from .binary import BinaryForecaster
from .numeric import NumericForecaster
from .multiple_choice import MultipleChoiceForecaster

logger = logging.getLogger(__name__)


class Forecaster:
    """
    Main forecaster that orchestrates the pipeline.

    Each handler (binary, numeric, multiple_choice) does its own:
    - Research query generation (historical + current)
    - Search execution
    - 5-agent ensemble forecasting
    - Probability extraction and aggregation

    Usage:
        config = load_config()
        forecaster = Forecaster(config)
        result = await forecaster.forecast_question(question_id=12345)
    """

    def __init__(self, config: Union[ResolvedConfig, dict]):
        """
        Initialize the Forecaster.

        Args:
            config: Either a ResolvedConfig object or a raw dict (for backward compatibility).
                    If a dict is passed, it will be wrapped in ResolvedConfig.

        Note:
            New code should pass ResolvedConfig directly. The dict option exists for
            backward compatibility with code that hasn't been migrated yet.

            Internally, we maintain both:
            - self.resolved_config: The rich ResolvedConfig object (preferred for new code)
            - self.config: A dict with _active_* keys for legacy handlers that expect them
        """
        # Accept either ResolvedConfig or dict for backward compatibility
        if isinstance(config, ResolvedConfig):
            self.resolved_config = config
            self.config = config.to_dict()
        else:
            # Dict passed - wrap in ResolvedConfig
            self.resolved_config = ResolvedConfig.from_dict(config)
            self.config = self.resolved_config.to_dict()

        # Initialize components
        self.metaculus = MetaculusClient()
        self.llm = LLMClient()
        self.artifact_store = ArtifactStore(
            base_dir=self.resolved_config.get("storage", {}).get("base_dir", "./data")
        )
        self.database = ForecastDatabase(
            db_path=self.resolved_config.get("storage", {}).get("database_path", "./data/forecasts.db")
        )

        # Configuration from resolved config
        self.dry_run = not self.resolved_config.should_submit

        # Log the mode
        logger.info(f"Forecaster initialized in '{self.resolved_config.mode}' mode")

    async def initialize(self):
        """Initialize database and other async resources."""
        await self.database.initialize()

    async def close(self):
        """Clean up resources."""
        await self.metaculus.close()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def forecast_question(
        self,
        question_id: Optional[int] = None,
        question_url: Optional[str] = None,
        question: Optional[MetaculusQuestion] = None,
    ) -> dict:
        """
        Run the full forecasting pipeline for a question.

        Provide either question_id, question_url, or question object.

        Returns dict with all results and artifacts.
        """
        # Reset cost tracker for this forecast
        reset_cost_tracker()
        start_time = datetime.now(timezone.utc)

        # Get question
        if question is None:
            if question_url:
                question = await self.metaculus.get_question_by_url(question_url)
            elif question_id:
                question = await self.metaculus.get_question(question_id)
            else:
                raise ValueError("Must provide question_id, question_url, or question object")

        logger.info(f"Forecasting: {question.title} (ID: {question.id}, Type: {question.question_type})")

        # Create artifact container
        artifacts = self.artifact_store.create_forecast_artifacts(question.id)

        # Create a scoped artifact store that saves to this forecast's directory
        scoped_store = ScopedArtifactStore(self.artifact_store, artifacts)

        try:
            # Step 1: Save question
            self.artifact_store.save_question(artifacts, question.raw)

            # Step 2: Analyze question (saved later in metadata)
            analysis = self._analyze_question(question)

            # Step 3: Run type-specific forecaster (does research + forecasting)
            if question.question_type == "binary":
                forecast_result = await self._forecast_binary(question, scoped_store)
            elif question.question_type == "multiple_choice":
                forecast_result = await self._forecast_multiple_choice(question, scoped_store)
            elif question.question_type == "numeric":
                forecast_result = await self._forecast_numeric(question, scoped_store)
            else:
                raise ValueError(f"Unknown question type: {question.question_type}")

            # Step 4: Submit prediction (unless dry run)
            submission_result = None
            if not self.dry_run:
                submission_result = await self._submit_prediction(
                    question=question,
                    forecast_result=forecast_result,
                    artifacts=artifacts,
                )
            else:
                self._log_dry_run(question, forecast_result, artifacts)

            # Step 5: Save metadata and database records
            end_time = datetime.now(timezone.utc)
            costs = get_cost_tracker().get_summary()

            self.artifact_store.save_metadata(
                artifacts,
                config=self.config,
                costs=costs,
                timing={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds(),
                },
                analysis=analysis,
            )

            # Save to database
            await self._save_to_database(
                question=question,
                forecast_result=forecast_result,
                artifacts=artifacts,
                costs=costs,
            )

            # Log completion
            self._log_completion(question, forecast_result, costs)

            # Build return value
            result = {
                "question": question,
                "forecast_result": forecast_result,
                "submission": submission_result,
                "costs": costs,
                "artifacts_dir": str(artifacts.forecast_dir),
            }

            # Add type-specific prediction summary
            if question.question_type == "binary":
                result["prediction"] = forecast_result["final_prediction"]
            elif question.question_type == "numeric":
                result["prediction"] = forecast_result["final_percentiles"]
                result["cdf"] = forecast_result["final_cdf"]
            elif question.question_type == "multiple_choice":
                result["prediction"] = forecast_result["final_probabilities"]

            return result

        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            self.artifact_store.save_metadata(
                artifacts,
                config=self.config,
                costs=get_cost_tracker().get_summary(),
                timing={"error": str(e)},
                errors=[str(e)],
            )
            raise

    def _analyze_question(self, question: MetaculusQuestion) -> dict:
        """Analyze and classify the question."""
        return {
            "id": question.id,
            "title": question.title,
            "type": question.question_type,
            "status": question.status,
            "scheduled_close": question.scheduled_close_time,
            "scheduled_resolve": question.scheduled_resolve_time,
            "community_prediction": question.community_prediction,
            "num_forecasters": question.num_forecasters,
        }

    async def _forecast_binary(
        self,
        question: MetaculusQuestion,
        scoped_store: "ScopedArtifactStore",
    ) -> dict:
        """Run binary forecasting pipeline with 5-agent ensemble."""
        forecaster = BinaryForecaster(
            config=self.config,
            llm_client=self.llm,
            artifact_store=scoped_store,
        )

        result = await forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            resolution_criteria=question.resolution_criteria or "",
            fine_print=question.raw.get("fine_print", ""),
            write=lambda msg: logger.info(msg),
        )

        return {
            "final_prediction": result.final_probability,
            "agent_results": result.agent_results,
            "historical_context": result.historical_context,
            "current_context": result.current_context,
        }

    async def _forecast_numeric(
        self,
        question: MetaculusQuestion,
        scoped_store: "ScopedArtifactStore",
    ) -> dict:
        """Run numeric forecasting pipeline with 5-agent ensemble."""
        # Extract bounds - can be at top level or in question.scaling
        scaling = question.raw.get("scaling") or question.raw.get("question", {}).get("scaling", {})
        lower_bound = scaling.get("range_min", 0)
        upper_bound = scaling.get("range_max", 100)
        open_lower_bound = scaling.get("open_lower_bound", False)
        open_upper_bound = scaling.get("open_upper_bound", False)
        zero_point = scaling.get("zero_point")

        forecaster = NumericForecaster(
            config=self.config,
            llm_client=self.llm,
            artifact_store=scoped_store,
        )

        result = await forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            resolution_criteria=question.resolution_criteria or "",
            fine_print=question.raw.get("fine_print", ""),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            open_lower_bound=open_lower_bound,
            open_upper_bound=open_upper_bound,
            zero_point=zero_point,
            write=lambda msg: logger.info(msg),
        )

        # Derive percentiles from CDF if needed (for logging/display)
        # The CDF is the primary output for Metaculus submission
        final_percentiles = {}
        if result.final_cdf and len(result.final_cdf) == 201:
            # CDF maps [0,1] to values - extract key percentiles
            for pct in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
                idx = int(pct * 2)  # 201 points from 0-100
                if idx < len(result.final_cdf):
                    # Approximate value from CDF position
                    final_percentiles[str(pct)] = result.final_cdf[idx]

        return {
            "final_percentiles": final_percentiles,
            "final_cdf": result.final_cdf,
            "agent_results": result.agent_results,
            "historical_context": result.historical_context,
            "current_context": result.current_context,
        }

    async def _forecast_multiple_choice(
        self,
        question: MetaculusQuestion,
        scoped_store: "ScopedArtifactStore",
    ) -> dict:
        """Run multiple choice forecasting pipeline with 5-agent ensemble."""
        # Extract options
        raw_options = question.options or question.raw.get("question", {}).get("options", [])

        options = []
        for i, opt in enumerate(raw_options):
            if isinstance(opt, str):
                options.append(opt)
            elif isinstance(opt, dict):
                options.append(opt.get("label", f"Option {i+1}"))
            else:
                options.append(f"Option {i+1}")

        if not options:
            options = [f"Option {i+1}" for i in range(4)]

        forecaster = MultipleChoiceForecaster(
            config=self.config,
            llm_client=self.llm,
            artifact_store=scoped_store,
        )

        result = await forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            resolution_criteria=question.resolution_criteria or "",
            fine_print=question.raw.get("fine_print", ""),
            options=options,
            write=lambda msg: logger.info(msg),
        )

        return {
            "final_probabilities": result.final_probabilities,
            "agent_results": result.agent_results,
            "historical_context": result.historical_context,
            "current_context": result.current_context,
            "options": result.options,
        }

    def _log_dry_run(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifacts,
    ):
        """Log dry run summary and save prediction artifact."""
        if question.question_type == "binary":
            pred = forecast_result["final_prediction"]
            logger.info(f"DRY RUN: Would submit {pred:.1%}")
            self.artifact_store.save_prediction(artifacts, {
                "prediction": pred,
                "dry_run": True,
            })

        elif question.question_type == "numeric":
            percentiles = forecast_result.get("final_percentiles", {})
            median = percentiles.get("50", percentiles.get(50, 0))
            logger.info(f"DRY RUN: Would submit CDF (median: {median})")
            self.artifact_store.save_prediction(artifacts, {
                "percentiles": percentiles,
                "cdf": forecast_result.get("final_cdf", []),
                "dry_run": True,
            })

        elif question.question_type == "multiple_choice":
            probs = forecast_result.get("final_probabilities", {})
            if probs:
                best = max(probs.items(), key=lambda x: x[1])
                logger.info(f"DRY RUN: Would submit distribution (most likely: {best[0]} at {best[1]:.1%})")
            self.artifact_store.save_prediction(artifacts, {
                "distribution": probs,
                "dry_run": True,
            })

    def _log_completion(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        costs: dict,
    ):
        """Log completion summary."""
        if question.question_type == "binary":
            logger.info(f"Forecast complete: {forecast_result['final_prediction']:.1%}")

        elif question.question_type == "numeric":
            percentiles = forecast_result.get("final_percentiles", {})
            median = percentiles.get("50", percentiles.get(50, 0))
            logger.info(f"Forecast complete: median = {median}")

        elif question.question_type == "multiple_choice":
            probs = forecast_result.get("final_probabilities", {})
            if probs:
                best = max(probs.items(), key=lambda x: x[1])
                logger.info(f"Forecast complete: most likely = {best[0]} ({best[1]:.1%})")

        logger.info(f"Total cost: ${costs.get('total_cost', 0):.4f}")

    async def _submit_prediction(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Submit prediction to Metaculus."""
        try:
            if question.question_type == "binary":
                prediction = forecast_result["final_prediction"]
                response = await self.metaculus.submit_prediction(question, prediction)
                self.artifact_store.save_prediction(artifacts, {
                    "prediction": prediction,
                    "submitted": True,
                })
                logger.info(f"Prediction submitted successfully: {prediction:.1%}")

            elif question.question_type == "numeric":
                cdf = forecast_result["final_cdf"]
                response = await self.metaculus.submit_numeric_prediction(question.id, cdf)
                percentiles = forecast_result.get("final_percentiles", {})
                median = percentiles.get("50", percentiles.get(50, 0))
                self.artifact_store.save_prediction(artifacts, {
                    "percentiles": percentiles,
                    "cdf": cdf,
                    "submitted": True,
                })
                logger.info(f"CDF submitted successfully (median: {median})")

            elif question.question_type == "multiple_choice":
                probs = forecast_result["final_probabilities"]
                response = await self.metaculus.submit_multiple_choice_prediction(question.id, probs)
                best = max(probs.items(), key=lambda x: x[1])
                self.artifact_store.save_prediction(artifacts, {
                    "distribution": probs,
                    "submitted": True,
                })
                logger.info(f"Distribution submitted successfully (most likely: {best[0]} at {best[1]:.1%})")

            else:
                raise ValueError(f"Unknown question type: {question.question_type}")

            self.artifact_store.save_api_response(artifacts, response)
            return {"success": True, "response": response}

        except Exception as e:
            logger.error(f"Failed to submit prediction: {e}")
            self.artifact_store.save_prediction(artifacts, {
                "forecast_result": forecast_result,
                "submitted": False,
                "error": str(e),
            })
            return {"success": False, "error": str(e)}

    async def _save_to_database(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifacts,
        costs: dict,
    ):
        """Save forecast data to database for analytics."""
        forecast_id = f"{artifacts.question_id}_{artifacts.timestamp}"

        # Extract prediction value based on question type
        if question.question_type == "binary":
            final_prediction = forecast_result.get("final_prediction")
        elif question.question_type == "numeric":
            percentiles = forecast_result.get("final_percentiles", {})
            final_prediction = percentiles.get("50", percentiles.get(50))
        elif question.question_type == "multiple_choice":
            probs = forecast_result.get("final_probabilities", {})
            final_prediction = max(probs.values()) if probs else None
        else:
            final_prediction = None

        # Save main forecast record
        record = ForecastRecord(
            id=forecast_id,
            question_id=question.id,
            timestamp=artifacts.timestamp,
            question_type=question.question_type,
            question_title=question.title,
            base_rate=None,
            final_prediction=final_prediction,
            total_cost=costs.get("total_cost", 0),
            config_hash=self.artifact_store._hash_config(self.config),
            tournament_id=self.config.get("submission", {}).get("tournament_id"),
        )
        await self.database.insert_forecast(record)

        # Save agent predictions
        for agent_result in forecast_result.get("agent_results", []):
            # Get prediction value based on question type
            # Binary: probability, Numeric: median from percentiles, Multiple Choice: max prob
            pred_value = None
            if hasattr(agent_result, 'probability') and agent_result.probability is not None:
                pred_value = agent_result.probability
            elif hasattr(agent_result, 'percentiles') and agent_result.percentiles:
                # Use median for numeric
                pred_value = agent_result.percentiles.get(50, agent_result.percentiles.get("50"))
            elif hasattr(agent_result, 'probabilities') and agent_result.probabilities:
                # Use max for multiple choice
                pred_value = max(agent_result.probabilities) if agent_result.probabilities else None

            agent_record = AgentPredictionRecord(
                forecast_id=forecast_id,
                agent_name=agent_result.agent_id,
                model=agent_result.model,
                weight=agent_result.weight,
                prediction=pred_value or 0.0,  # Default to 0 if no prediction
                reasoning_length=len(agent_result.step2_output) if agent_result.step2_output else 0,
            )
            await self.database.insert_agent_prediction(agent_record)


class ScopedArtifactStore:
    """
    Wraps ArtifactStore to automatically scope saves to a specific forecast.

    The handlers call methods like save_query_generation(type, prompt, response)
    without needing to know about ForecastArtifacts.
    """

    def __init__(self, store: ArtifactStore, artifacts: ForecastArtifacts):
        self.store = store
        self.artifacts = artifacts

    def save_query_generation(self, query_type: str, prompt: str, response: str) -> None:
        """Save query generation prompt and response."""
        self.store.save_query_generation(self.artifacts, query_type, prompt, response)

    def save_search_results(self, search_type: str, results: dict) -> None:
        """Save search results."""
        self.store.save_search_results(self.artifacts, search_type, results)

    def save_step1_prompt(self, prompt: str) -> None:
        """Save the shared step 1 (outside view) prompt."""
        self.store.save_step1_prompt(self.artifacts, prompt)

    def save_agent_step1(self, agent_num: int, response: str) -> None:
        """Save an agent's step 1 (outside view) response."""
        self.store.save_agent_step1(self.artifacts, agent_num, response)

    def save_agent_step2(self, agent_num: int, response: str) -> None:
        """Save an agent's step 2 (inside view) response."""
        self.store.save_agent_step2(self.artifacts, agent_num, response)

    def save_agent_extracted(self, agent_num: int, extracted: dict) -> None:
        """Save extracted prediction from agent."""
        self.store.save_agent_extracted(self.artifacts, agent_num, extracted)

    def save_aggregation(self, aggregation: dict) -> None:
        """Save aggregation result."""
        self.store.save_aggregation(self.artifacts, aggregation)

    def save_tool_usage(self, tool_usage: dict) -> None:
        """Save tool usage tracking data."""
        self.store.save_tool_usage(self.artifacts, tool_usage)


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


async def main():
    """CLI entry point for testing."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m src.bot.forecaster <question_id_or_url>")
        sys.exit(1)

    input_arg = sys.argv[1]
    config = load_config()

    async with Forecaster(config) as forecaster:
        if input_arg.startswith("http"):
            result = await forecaster.forecast_question(question_url=input_arg)
        else:
            result = await forecaster.forecast_question(question_id=int(input_arg))

        print(f"\n{'='*60}")
        print(f"FORECAST COMPLETE")
        print(f"{'='*60}")
        print(f"Question: {result['question'].title}")
        if result['question'].question_type == "binary":
            print(f"Prediction: {result['prediction']:.1%}")
        elif result['question'].question_type == "numeric":
            print(f"Prediction (median): {result['prediction'].get(50, 'N/A')}")
        elif result['question'].question_type == "multiple_choice":
            print(f"Prediction: {result['prediction']}")
        print(f"Cost: ${result['costs']['total_cost']:.4f}")
        print(f"Artifacts: {result['artifacts_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
