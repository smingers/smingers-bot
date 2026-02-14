"""
Main Forecaster Orchestration

Simplified pipeline that delegates to type-specific handlers:
1. Fetch question from Metaculus
2. Route to appropriate handler (binary/numeric/multiple_choice)
3. Handler does all research + forecasting internally
4. Save final prediction
5. Submit if should_submit is True (based on mode: live submits, test/preview don't)
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from ..config import ResolvedConfig
from ..storage.artifact_store import ArtifactStore, ForecastArtifactPaths
from ..storage.database import AgentPredictionRecord, ForecastDatabase, ForecastRecord
from ..utils.llm import LLMClient, get_cost_tracker, reset_cost_tracker
from ..utils.metaculus_api import MetaculusClient, MetaculusQuestion
from .binary import BinaryForecaster
from .cdf import percentiles_from_cdf
from .exceptions import QuestionTypeError, SubmissionError
from .multiple_choice import MultipleChoiceForecaster
from .numeric import NumericForecaster

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

    def __init__(self, config: ResolvedConfig | dict):
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
        llm_timeout = self.resolved_config.get("llm", {}).get("timeout_seconds")
        self.llm = LLMClient(timeout_seconds=llm_timeout)
        self.artifact_store = ArtifactStore(
            base_dir=self.resolved_config.get("storage", {}).get("base_dir", "./data")
        )
        self.database = ForecastDatabase(
            db_path=self.resolved_config.get("storage", {}).get(
                "database_path", "./data/forecasts.db"
            )
        )

        # Log the mode
        logger.info(f"Forecaster initialized in '{self.resolved_config.mode}' mode")

    async def initialize(self):
        """Initialize database and other async resources."""
        await self.database.initialize()
        await self.database.migrate_schema()

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
        question_id: int | None = None,
        question_url: str | None = None,
        question: MetaculusQuestion | None = None,
    ) -> dict:
        """
        Run the full forecasting pipeline for a question.

        Provide either question_id, question_url, or question object.

        Returns dict with all results and artifacts.
        """
        # Reset cost tracker for this forecast
        reset_cost_tracker()
        start_time = datetime.now(UTC)

        # Get question
        if question is None:
            if question_url:
                question = await self.metaculus.get_question_by_url(question_url)
            elif question_id:
                question = await self.metaculus.get_question(question_id)
            else:
                raise ValueError("Must provide question_id, question_url, or question object")

        logger.info(
            f"Forecasting: {question.title} (ID: {question.id}, Type: {question.question_type})"
        )

        # Create artifact container
        artifacts = self.artifact_store.create_forecast_artifacts(question.id)

        # Create a scoped artifact store that saves to this forecast's directory
        scoped_store = ScopedArtifactStore(self.artifact_store, artifacts)

        try:
            # Step 1: Save question
            self.artifact_store.save_question(artifacts, question.raw)

            # Step 2: Extract question metadata (saved later in metadata.json)
            analysis = self._extract_question_metadata(question)

            # Step 3: Run type-specific forecaster (does research + forecasting)
            if question.question_type == "binary":
                forecast_result = await self._forecast_binary(question, scoped_store)
            elif question.question_type == "multiple_choice":
                forecast_result = await self._forecast_multiple_choice(question, scoped_store)
            elif question.question_type in ("numeric", "discrete", "date"):
                forecast_result = await self._forecast_numeric(question, scoped_store)
            else:
                raise QuestionTypeError(
                    f"Unknown question type: {question.question_type}",
                    question_type=question.question_type,
                )

            # Step 4: Submit prediction (if configured to submit)
            submission_result = None
            if self.resolved_config.should_submit:
                submission_result = await self._submit_prediction(
                    question=question,
                    forecast_result=forecast_result,
                    artifacts=artifacts,
                )
            else:
                self._save_without_submitting(question, forecast_result, artifacts)

            # Step 5: Save metadata and database records
            end_time = datetime.now(UTC)
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
                errors=forecast_result.get("pipeline_warnings"),
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
            elif question.question_type in ("numeric", "discrete", "date"):
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

    def _extract_question_metadata(self, question: MetaculusQuestion) -> dict:
        """Extract metadata fields from the question for artifact storage."""
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
            background_info=question.background_info or "",
            resolution_criteria=question.resolution_criteria or "",
            fine_print=question.raw.get("fine_print", ""),
            open_time=question.open_time or "",
            scheduled_resolve_time=question.scheduled_resolve_time or "",
            log=lambda msg: logger.info(msg),
        )

        return {
            "final_prediction": result.final_probability,
            "agent_results": result.agent_results,
            "historical_context": result.historical_context,
            "current_context": result.current_context,
            "pipeline_warnings": forecaster.pipeline_warnings,
        }

    async def _forecast_numeric(
        self,
        question: MetaculusQuestion,
        scoped_store: "ScopedArtifactStore",
    ) -> dict:
        """Run numeric forecasting pipeline with 5-agent ensemble.

        Also handles date questions (which use the same CDF submission format).
        """
        # Extract bounds - can be at top level or in question.scaling
        scaling = question.raw.get("scaling") or question.raw.get("question", {}).get("scaling", {})
        lower_bound = scaling.get("range_min", 0)
        upper_bound = scaling.get("range_max", 100)
        open_lower_bound = scaling.get("open_lower_bound", False)
        open_upper_bound = scaling.get("open_upper_bound", False)
        zero_point = scaling.get("zero_point")

        # For date questions, set units to indicate YYYY-MM-DD format
        # and include date bounds in the unit string for LLM context
        if question.question_type == "date":
            lower_str = question.lower_bound_date_str or "unknown"
            upper_str = question.upper_bound_date_str or "unknown"
            unit_of_measure = f"date (YYYY-MM-DD format, range: {lower_str} to {upper_str})"
            is_date_question = True
        else:
            unit_of_measure = question.unit_of_measure or ""
            is_date_question = False

        forecaster = NumericForecaster(
            config=self.config,
            llm_client=self.llm,
            artifact_store=scoped_store,
        )

        result = await forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            background_info=question.background_info or "",
            resolution_criteria=question.resolution_criteria or "",
            fine_print=question.raw.get("fine_print", ""),
            unit_of_measure=unit_of_measure,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            open_lower_bound=open_lower_bound,
            open_upper_bound=open_upper_bound,
            zero_point=zero_point,
            nominal_lower_bound=question.nominal_lower_bound,
            nominal_upper_bound=question.nominal_upper_bound,
            open_time=question.open_time or "",
            scheduled_resolve_time=question.scheduled_resolve_time or "",
            cdf_size=question.cdf_size,
            is_date_question=is_date_question,
            log=lambda msg: logger.info(msg),
        )

        # Derive percentiles from CDF for logging/display
        final_percentiles = {}
        if result.final_cdf and len(result.final_cdf) == question.cdf_size:
            final_percentiles = percentiles_from_cdf(
                cdf=result.final_cdf,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                zero_point=zero_point,
            )

        return {
            "final_percentiles": final_percentiles,
            "final_cdf": result.final_cdf,
            "agent_results": result.agent_results,
            "historical_context": result.historical_context,
            "current_context": result.current_context,
            "pipeline_warnings": forecaster.pipeline_warnings,
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
                options.append(opt.get("label", f"Option {i + 1}"))
            else:
                options.append(f"Option {i + 1}")

        if not options:
            options = [f"Option {i + 1}" for i in range(4)]

        forecaster = MultipleChoiceForecaster(
            config=self.config,
            llm_client=self.llm,
            artifact_store=scoped_store,
        )

        result = await forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            background_info=question.background_info or "",
            resolution_criteria=question.resolution_criteria or "",
            fine_print=question.raw.get("fine_print", ""),
            options=options,
            open_time=question.open_time or "",
            scheduled_resolve_time=question.scheduled_resolve_time or "",
            log=lambda msg: logger.info(msg),
        )

        return {
            "final_probabilities": result.final_probabilities,
            "agent_results": result.agent_results,
            "historical_context": result.historical_context,
            "current_context": result.current_context,
            "options": result.options,
            "pipeline_warnings": forecaster.pipeline_warnings,
        }

    def _save_without_submitting(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifactPaths,
    ):
        """Save prediction artifact without submitting (test/preview mode)."""
        mode_label = self.resolved_config.mode.upper()

        if question.question_type == "binary":
            pred = forecast_result["final_prediction"]
            logger.info(f"{mode_label}: Would submit {pred:.1%}")
            self.artifact_store.save_prediction(
                artifacts,
                {
                    "prediction": pred,
                    "submitted": False,
                },
            )

        elif question.question_type in ("numeric", "discrete", "date"):
            percentiles = forecast_result.get("final_percentiles", {})
            median = percentiles.get("50", percentiles.get(50, 0))
            logger.info(f"{mode_label}: Would submit CDF (median: {median})")
            self.artifact_store.save_prediction(
                artifacts,
                {
                    "percentiles": percentiles,
                    "cdf": forecast_result.get("final_cdf", []),
                    "submitted": False,
                },
            )

        elif question.question_type == "multiple_choice":
            probs = forecast_result.get("final_probabilities", {})
            if probs:
                best = max(probs.items(), key=lambda x: x[1])
                logger.info(
                    f"{mode_label}: Would submit distribution (most likely: {best[0]} at {best[1]:.1%})"
                )
            self.artifact_store.save_prediction(
                artifacts,
                {
                    "distribution": probs,
                    "submitted": False,
                },
            )

    def _log_completion(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        costs: dict,
    ):
        """Log completion summary."""
        if question.question_type == "binary":
            logger.info(f"Forecast complete: {forecast_result['final_prediction']:.1%}")

        elif question.question_type in ("numeric", "discrete", "date"):
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
        artifacts: ForecastArtifactPaths,
    ) -> dict:
        """Submit prediction to Metaculus.

        Raises:
            SubmissionError: If the API returns an error during submission.
            QuestionTypeError: If the question type is not supported.
        """
        import httpx

        try:
            if question.question_type == "binary":
                prediction = forecast_result["final_prediction"]
                response = await self.metaculus.submit_prediction(question, prediction)
                self.artifact_store.save_prediction(
                    artifacts,
                    {
                        "prediction": prediction,
                        "submitted": True,
                    },
                )
                logger.info(f"Prediction submitted successfully: {prediction:.1%}")

            elif question.question_type in ("numeric", "discrete", "date"):
                cdf = forecast_result["final_cdf"]
                response = await self.metaculus.submit_numeric_prediction(
                    question.question_id,
                    cdf,
                    open_lower_bound=question.open_lower_bound or False,
                    open_upper_bound=question.open_upper_bound or False,
                    expected_cdf_size=question.cdf_size,
                )
                percentiles = forecast_result.get("final_percentiles", {})
                median = percentiles.get("50", percentiles.get(50, 0))
                self.artifact_store.save_prediction(
                    artifacts,
                    {
                        "percentiles": percentiles,
                        "cdf": cdf,
                        "submitted": True,
                    },
                )
                logger.info(f"CDF submitted successfully (median: {median})")

            elif question.question_type == "multiple_choice":
                probs = forecast_result["final_probabilities"]
                response = await self.metaculus.submit_multiple_choice_prediction(
                    question.question_id, probs
                )
                best = max(probs.items(), key=lambda x: x[1])
                self.artifact_store.save_prediction(
                    artifacts,
                    {
                        "distribution": probs,
                        "submitted": True,
                    },
                )
                logger.info(
                    f"Distribution submitted successfully (most likely: {best[0]} at {best[1]:.1%})"
                )

            else:
                raise QuestionTypeError(
                    f"Unknown question type: {question.question_type}",
                    question_type=question.question_type,
                )

        except httpx.HTTPStatusError as e:
            self.artifact_store.save_prediction(
                artifacts,
                {
                    "forecast_result": forecast_result,
                    "submitted": False,
                    "error": str(e),
                },
            )
            raise SubmissionError(
                f"API returned {e.response.status_code}: {e}",
                status_code=e.response.status_code,
            ) from e

        self.artifact_store.save_api_response(artifacts, response)
        return {"success": True, "response": response}

    async def _save_to_database(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifactPaths,
        costs: dict,
    ):
        """Save forecast data to database for analytics."""
        forecast_id = f"{artifacts.question_id}_{artifacts.timestamp}"

        # Extract prediction value and full prediction data based on question type
        if question.question_type == "binary":
            final_prediction = forecast_result.get("final_prediction")
            prediction_data = json.dumps({"probability": final_prediction})
        elif question.question_type in ("numeric", "discrete", "date"):
            percentiles = forecast_result.get("final_percentiles", {})
            final_prediction = percentiles.get("50", percentiles.get(50))
            prediction_data = json.dumps({"percentiles": percentiles})
        elif question.question_type == "multiple_choice":
            probs = forecast_result.get("final_probabilities", {})
            final_prediction = max(probs.values()) if probs else None
            prediction_data = json.dumps({"probabilities": probs})
        else:
            final_prediction = None
            prediction_data = "{}"

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
            mode=self.resolved_config.mode,
            prediction_data=prediction_data,
        )
        await self.database.insert_forecast(record)

        # Save agent predictions
        for agent_result in forecast_result.get("agent_results", []):
            # Get prediction value and full data based on question type
            # Binary: probability, Numeric: median from percentiles, Multiple Choice: max prob
            pred_value = None
            agent_pred_data = "{}"

            if hasattr(agent_result, "probability") and agent_result.probability is not None:
                pred_value = agent_result.probability
                agent_pred_data = json.dumps({"probability": agent_result.probability})
            elif hasattr(agent_result, "percentiles") and agent_result.percentiles:
                # Use median (p50) for numeric, or interpolate from p40/p60 if p50 not available
                pred_value = agent_result.percentiles.get(50, agent_result.percentiles.get("50"))
                if pred_value is None:
                    p40 = agent_result.percentiles.get(40)
                    p60 = agent_result.percentiles.get(60)
                    if p40 is not None and p60 is not None:
                        pred_value = (p40 + p60) / 2
                agent_pred_data = json.dumps({"percentiles": agent_result.percentiles})
            elif hasattr(agent_result, "probabilities") and agent_result.probabilities:
                # Use max for multiple choice, store full distribution
                pred_value = max(agent_result.probabilities) if agent_result.probabilities else None
                agent_pred_data = json.dumps({"probabilities": agent_result.probabilities})

            agent_record = AgentPredictionRecord(
                forecast_id=forecast_id,
                agent_id=agent_result.agent_id,
                model=agent_result.model,
                weight=agent_result.weight,
                prediction=pred_value or 0.0,  # Default to 0 if no prediction
                reasoning_length=len(agent_result.inside_view_output)
                if agent_result.inside_view_output
                else 0,
                prediction_data=agent_pred_data,
            )
            await self.database.insert_agent_prediction(agent_record)


class ScopedArtifactStore:
    """
    Wraps ArtifactStore to automatically scope saves to a specific forecast.

    The handlers call methods like save_query_generation(type, prompt, response)
    without needing to know about ForecastArtifactPaths.
    """

    def __init__(self, store: ArtifactStore, artifacts: ForecastArtifactPaths):
        self.store = store
        self.artifacts = artifacts

    def save_query_generation(self, search_phase: str, prompt: str, response: str) -> None:
        """Save query generation prompt and response."""
        self.store.save_query_generation(self.artifacts, search_phase, prompt, response)

    def save_search_results(self, search_phase: str, results: dict) -> None:
        """Save search results."""
        self.store.save_search_results(self.artifacts, search_phase, results)

    def save_outside_view_prompt(self, prompt: str) -> None:
        """Save the shared outside view prompt."""
        self.store.save_outside_view_prompt(self.artifacts, prompt)

    def save_forecaster_outside_view(self, forecaster_num: int, response: str) -> None:
        """Save a forecaster's outside view response."""
        self.store.save_forecaster_outside_view(self.artifacts, forecaster_num, response)

    def save_forecaster_inside_view(self, forecaster_num: int, response: str) -> None:
        """Save a forecaster's inside view response."""
        self.store.save_forecaster_inside_view(self.artifacts, forecaster_num, response)

    def save_forecaster_prediction(self, forecaster_num: int, extracted: dict) -> None:
        """Save extracted prediction from forecaster."""
        self.store.save_forecaster_prediction(self.artifacts, forecaster_num, extracted)

    def save_aggregation(self, aggregation: dict) -> None:
        """Save aggregation result."""
        self.store.save_aggregation(self.artifacts, aggregation)

    def save_tool_usage(self, tool_usage: dict) -> None:
        """Save tool usage tracking data."""
        self.store.save_tool_usage(self.artifacts, tool_usage)

    def save_supervisor_analysis(self, analysis: str) -> None:
        """Save supervisor disagreement analysis."""
        self.store.save_supervisor_analysis(self.artifacts, analysis)

    def save_supervisor_research(self, research: str) -> None:
        """Save supervisor targeted research results."""
        self.store.save_supervisor_research(self.artifacts, research)

    def save_supervisor_reasoning(self, reasoning: str) -> None:
        """Save supervisor updated reasoning."""
        self.store.save_supervisor_reasoning(self.artifacts, reasoning)

    def save_supervisor_result(self, result: dict) -> None:
        """Save supervisor structured result."""
        self.store.save_supervisor_result(self.artifacts, result)


async def main():
    """CLI entry point for testing."""
    import sys

    from ..config import load_config

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

        print(f"\n{'=' * 60}")
        print("FORECAST COMPLETE")
        print(f"{'=' * 60}")
        print(f"Question: {result['question'].title}")
        if result["question"].question_type == "binary":
            print(f"Prediction: {result['prediction']:.1%}")
        elif result["question"].question_type in ("numeric", "discrete", "date"):
            print(f"Prediction (median): {result['prediction'].get(50, 'N/A')}")
        elif result["question"].question_type == "multiple_choice":
            print(f"Prediction: {result['prediction']}")
        print(f"Cost: ${result['costs']['total_cost']:.4f}")
        print(f"Artifacts: {result['artifacts_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
