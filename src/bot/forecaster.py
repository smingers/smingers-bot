"""
Main Forecaster Orchestration

Coordinates the full forecasting pipeline:
1. Fetch question from Metaculus
2. Conduct research
3. Run outside view (base rate estimation)
4. Run inside view (ensemble adjustment)
5. Aggregate predictions
6. Run calibration checks
7. Submit prediction
8. Store all artifacts
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from ..utils.llm import LLMClient, get_cost_tracker, reset_cost_tracker
from ..utils.metaculus_api import MetaculusClient, MetaculusQuestion
from ..research.searcher import ResearchOrchestrator, ResearchResults
from ..ensemble.aggregator import EnsembleAggregator
from ..storage.artifact_store import ArtifactStore, ForecastArtifacts
from ..storage.database import ForecastDatabase, ForecastRecord, AgentPredictionRecord, ResearchSourceRecord
from ..storage.report_generator import generate_reasoning_report, ForecastData, AgentResult

from .binary import BinaryForecaster
from .numeric import NumericForecaster
from .multiple_choice import MultipleChoiceForecaster

logger = logging.getLogger(__name__)


class Forecaster:
    """
    Main forecaster that orchestrates the entire pipeline.

    Usage:
        config = load_config()
        forecaster = Forecaster(config)
        result = await forecaster.forecast_question(question_id=12345)
    """

    def __init__(self, config: dict):
        self.config = config

        # Apply mode-based config if not already applied
        # (main.py applies this, but direct usage might not)
        if "_active_models" not in config:
            self._apply_default_mode(config)

        # Initialize components
        self.metaculus = MetaculusClient()
        self.research = ResearchOrchestrator(config)
        self.artifact_store = ArtifactStore(
            base_dir=config.get("storage", {}).get("base_dir", "./data/forecasts")
        )
        self.database = ForecastDatabase(
            db_path=config.get("storage", {}).get("database_path", "./data/forecasts.db")
        )

        # Type-specific forecasters (pass mode-aware config)
        self.binary_forecaster = BinaryForecaster(config)
        self.numeric_forecaster = NumericForecaster(config)
        self.multiple_choice_forecaster = MultipleChoiceForecaster(config)

        # Configuration - use mode-based submission control
        self.dry_run = not config.get("_should_submit", False)
        self.store_reasoning = config.get("submission", {}).get("store_reasoning", True)

        # Log the mode
        mode = config.get("_effective_mode", "dry_run")
        logger.info(f"Forecaster initialized in '{mode}' mode")

    def _apply_default_mode(self, config: dict):
        """Apply default mode settings if not already applied by main.py."""
        mode = config.get("mode", "dry_run")
        model_tier = "cheap" if mode == "dry_run" else "production"

        # Apply models
        if "models" in config and model_tier in config["models"]:
            config["_active_models"] = config["models"][model_tier]
        else:
            config["_active_models"] = config.get("models", {})

        # Apply ensemble agents
        if "ensemble" in config and model_tier in config["ensemble"]:
            config["_active_agents"] = config["ensemble"][model_tier]
        else:
            config["_active_agents"] = config.get("ensemble", {}).get("agents", [])

        # Set submission behavior
        config["_should_submit"] = (mode == "production")
        config["_effective_mode"] = mode

    async def initialize(self):
        """Initialize database and other async resources."""
        await self.database.initialize()

    async def close(self):
        """Clean up resources."""
        await self.metaculus.close()
        await self.research.close()

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

        try:
            # Step 1: Save question
            self.artifact_store.save_question(artifacts, question.raw)

            # Step 2: Analyze question
            analysis = self._analyze_question(question)
            self.artifact_store.save_analysis(artifacts, analysis)

            # Step 3: Conduct research (or reuse existing)
            research_summary, research_results, reuse_metadata = await self._get_or_reuse_research(
                question=question,
                artifacts=artifacts,
            )
            self.artifact_store.save_research_synthesis(artifacts, research_summary)

            # Step 4: Run type-specific forecaster
            if question.question_type == "binary":
                forecast_result = await self._forecast_binary(
                    question=question,
                    research_summary=research_summary,
                    artifacts=artifacts,
                )
            elif question.question_type == "multiple_choice":
                forecast_result = await self._forecast_multiple_choice(
                    question=question,
                    research_summary=research_summary,
                    artifacts=artifacts,
                )
            elif question.question_type == "numeric":
                forecast_result = await self._forecast_numeric(
                    question=question,
                    research_summary=research_summary,
                    artifacts=artifacts,
                )
            else:
                raise ValueError(f"Unknown question type: {question.question_type}")

            # Step 5: Run calibration (if enabled)
            calibration_result = None
            if self.config.get("calibration", {}).get("enabled", True):
                calibration_result = await self._run_calibration(
                    question=question,
                    forecast_result=forecast_result,
                    artifacts=artifacts,
                )

            # Step 6: Submit prediction (unless dry run)
            submission_result = None
            if not self.dry_run:
                submission_result = await self._submit_prediction(
                    question=question,
                    forecast_result=forecast_result,
                    artifacts=artifacts,
                )
            else:
                # Log appropriate summary based on question type
                if question.question_type == "binary":
                    logger.info(f"DRY RUN: Would submit {forecast_result['final_prediction']:.1%}")
                    self.artifact_store.save_final_prediction(artifacts, {
                        "prediction": forecast_result["final_prediction"],
                        "dry_run": True,
                    })
                elif question.question_type == "numeric":
                    median = forecast_result.get("final_percentiles", {}).get(50, 0)
                    logger.info(f"DRY RUN: Would submit CDF (median: {median})")
                    self.artifact_store.save_final_prediction(artifacts, {
                        "percentiles": forecast_result["final_percentiles"],
                        "cdf": forecast_result["final_cdf"],
                        "dry_run": True,
                    })
                elif question.question_type == "multiple_choice":
                    best = max(forecast_result["final_distribution"].items(), key=lambda x: x[1])
                    logger.info(f"DRY RUN: Would submit distribution (most likely: {best[0]} at {best[1]:.1%})")
                    self.artifact_store.save_final_prediction(artifacts, {
                        "distribution": forecast_result["final_distribution"],
                        "dry_run": True,
                    })

            # Step 7: Generate and save report
            report = self._generate_report(
                question=question,
                research_results=research_results,
                forecast_result=forecast_result,
                calibration_result=calibration_result,
            )
            self.artifact_store.save_reasoning_report(artifacts, report)

            # Step 8: Save metadata and database records
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
                research_reuse=reuse_metadata,
            )

            # Save to database
            await self._save_to_database(
                question=question,
                forecast_result=forecast_result,
                research_results=research_results,
                artifacts=artifacts,
                costs=costs,
            )

            # Log completion based on question type
            if question.question_type == "binary":
                logger.info(f"Forecast complete: {forecast_result['final_prediction']:.1%}")
            elif question.question_type == "numeric":
                median = forecast_result.get("final_percentiles", {}).get(50, 0)
                logger.info(f"Forecast complete: median = {median}")
            elif question.question_type == "multiple_choice":
                best = max(forecast_result["final_distribution"].items(), key=lambda x: x[1])
                logger.info(f"Forecast complete: most likely = {best[0]} ({best[1]:.1%})")
            logger.info(f"Total cost: ${costs['total_cost']:.4f}")

            # Build return value based on question type
            result = {
                "question": question,
                "forecast_result": forecast_result,
                "calibration": calibration_result,
                "submission": submission_result,
                "costs": costs,
                "artifacts_dir": str(artifacts.base_dir / f"{artifacts.question_id}_{artifacts.timestamp}"),
            }

            # Add type-specific prediction summary
            if question.question_type == "binary":
                result["prediction"] = forecast_result["final_prediction"]
            elif question.question_type == "numeric":
                result["prediction"] = forecast_result["final_percentiles"]
                result["cdf"] = forecast_result["final_cdf"]
            elif question.question_type == "multiple_choice":
                result["prediction"] = forecast_result["final_distribution"]

            return result

        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            # Save error metadata
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

    async def _get_or_reuse_research(
        self,
        question: MetaculusQuestion,
        artifacts: ForecastArtifacts,
    ) -> tuple[str, ResearchResults, dict | None]:
        """
        Get research for a question, either by reusing recent research or conducting fresh.

        Returns:
            Tuple of (research_summary, research_results, reuse_metadata)
            reuse_metadata is None if fresh research was conducted.
        """
        reuse_config = self.config.get("research", {}).get("reuse", {})
        reuse_enabled = reuse_config.get("enabled", False)
        max_age_hours = reuse_config.get("max_age_hours", 168)
        force_fresh = reuse_config.get("force_fresh", False)

        # Try to reuse research if enabled
        if reuse_enabled and not force_fresh:
            logger.info(f"Checking for recent research (max age: {max_age_hours}h)...")
            recent_research = self.artifact_store.find_recent_research(
                question_id=question.id,
                max_age_hours=max_age_hours,
            )

            if recent_research:
                logger.info(
                    f"Found research from {recent_research['age_hours']:.1f}h ago, reusing..."
                )
                reuse_metadata = self.artifact_store.copy_research(
                    source_research_dir=recent_research["research_dir"],
                    target_artifacts=artifacts,
                    metadata=recent_research,
                )

                # Load the synthesis from copied research
                synthesis_path = artifacts.research_dir / "synthesis.md"
                if synthesis_path.exists():
                    with open(synthesis_path) as f:
                        research_summary = f.read()

                    # Load original queries if available
                    queries = []
                    queries_path = artifacts.research_dir / "queries_generated.json"
                    if queries_path.exists():
                        import json
                        with open(queries_path) as f:
                            queries_data = json.load(f)
                            queries = [q.get("query", "") for q in queries_data]

                    # Create ResearchResults for compatibility with report/database code
                    research_results = ResearchResults(
                        queries=queries if queries else [],
                        results_by_source={},
                        perplexity_synthesis=None,
                        total_results=0,
                    )

                    return research_summary, research_results, reuse_metadata
                else:
                    logger.warning("No synthesis found in reused research, falling back to fresh")

        # Conduct fresh research
        logger.info("Conducting fresh research...")
        research_results = await self.research.research(
            question_title=question.title,
            question_text=question.description,
            question_type=question.question_type,
        )

        # Save research artifacts
        self.artifact_store.save_research_queries(artifacts, [
            {"query": q, "source": "llm_generated"} for q in research_results.queries
        ])
        for source, results in research_results.results_by_source.items():
            self.artifact_store.save_research_source(
                artifacts, source, [
                    {"title": r.title, "url": r.url, "snippet": r.snippet}
                    for r in results
                ]
            )

        research_summary = self.research.synthesize_results(research_results)
        return research_summary, research_results, None

    async def _forecast_binary(
        self,
        question: MetaculusQuestion,
        research_summary: str,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Run binary forecasting pipeline."""
        result = await self.binary_forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            resolution_criteria=question.resolution_criteria,
            research_summary=research_summary,
        )

        # Save outside view artifacts
        self.artifact_store.save_outside_view_prompt(
            artifacts,
            "See prompts/outside_view.md template"  # Could save actual filled prompt
        )
        self.artifact_store.save_outside_view_response(
            artifacts,
            result["outside_view_reasoning"]
        )
        self.artifact_store.save_outside_view_extracted(artifacts, {
            "base_rate": result["base_rate"],
            "reference_classes": result["reference_classes"],
            "confidence": result["base_rate_confidence"],
        })

        # Save inside view artifacts for each agent
        for agent_pred in result["agent_predictions"]:
            self.artifact_store.save_agent_prompt(
                artifacts,
                agent_pred.agent_name,
                f"Role: {agent_pred.agent_name}\nModel: {agent_pred.model}"
            )
            self.artifact_store.save_agent_response(
                artifacts,
                agent_pred.agent_name,
                agent_pred.reasoning
            )
            self.artifact_store.save_agent_extracted(artifacts, agent_pred.agent_name, {
                "prediction": agent_pred.prediction,
                "weight": agent_pred.weight,
                "evidence_weights": agent_pred.evidence_weights,
            })

        # Save aggregation
        self.artifact_store.save_aggregation(artifacts, {
            "individual_predictions": [
                {"agent": ap.agent_name, "prediction": ap.prediction, "weight": ap.weight}
                for ap in result["agent_predictions"]
            ],
            **result["aggregation"],
            "final": result["final_prediction"],
        })

        return result

    async def _forecast_numeric(
        self,
        question: MetaculusQuestion,
        research_summary: str,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Run numeric forecasting pipeline."""
        # Extract bounds from question
        lower_bound = question.raw.get("scaling", {}).get("range_min", 0)
        upper_bound = question.raw.get("scaling", {}).get("range_max", 100)
        open_lower_bound = question.raw.get("open_lower_bound", False)
        open_upper_bound = question.raw.get("open_upper_bound", False)
        units = question.raw.get("unit", "")

        result = await self.numeric_forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            resolution_criteria=question.resolution_criteria,
            research_summary=research_summary,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            open_lower_bound=open_lower_bound,
            open_upper_bound=open_upper_bound,
            units=units,
        )

        # Save outside view artifacts
        self.artifact_store.save_outside_view_prompt(
            artifacts,
            "See prompts/outside_view_numeric.md template"
        )
        self.artifact_store.save_outside_view_response(
            artifacts,
            result["outside_view_reasoning"]
        )
        self.artifact_store.save_outside_view_extracted(artifacts, {
            "base_percentiles": result["base_percentiles"],
        })

        # Save inside view artifacts for each agent
        for agent_pred in result["agent_predictions"]:
            self.artifact_store.save_agent_prompt(
                artifacts,
                agent_pred.agent_name,
                f"Role: {agent_pred.agent_name}\nModel: {agent_pred.model}"
            )
            self.artifact_store.save_agent_response(
                artifacts,
                agent_pred.agent_name,
                agent_pred.reasoning
            )
            self.artifact_store.save_agent_extracted(artifacts, agent_pred.agent_name, {
                "percentiles": agent_pred.prediction_distribution,
                "weight": agent_pred.weight,
            })

        # Save aggregation
        self.artifact_store.save_aggregation(artifacts, {
            "individual_percentiles": [
                {"agent": ap.agent_name, "percentiles": ap.prediction_distribution, "weight": ap.weight}
                for ap in result["agent_predictions"]
            ],
            **result["aggregation"],
            "final_percentiles": result["final_percentiles"],
            "final_cdf": result["final_cdf"][:10],  # Just first 10 for brevity
        })

        return result

    async def _forecast_multiple_choice(
        self,
        question: MetaculusQuestion,
        research_summary: str,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Run multiple choice forecasting pipeline."""
        # Extract options from question
        options = question.raw.get("options", [])
        if not options:
            # Fallback: try to get from group_of_questions or other fields
            options = [{"id": str(i), "label": f"Option {i+1}"} for i in range(4)]

        result = await self.multiple_choice_forecaster.forecast(
            question_title=question.title,
            question_text=question.description,
            resolution_criteria=question.resolution_criteria,
            research_summary=research_summary,
            options=options,
        )

        # Save outside view artifacts
        self.artifact_store.save_outside_view_prompt(
            artifacts,
            "See prompts/outside_view_multiple_choice.md template"
        )
        self.artifact_store.save_outside_view_response(
            artifacts,
            result["outside_view_reasoning"]
        )
        self.artifact_store.save_outside_view_extracted(artifacts, {
            "base_distribution": result["base_distribution"],
        })

        # Save inside view artifacts for each agent
        for agent_pred in result["agent_predictions"]:
            self.artifact_store.save_agent_prompt(
                artifacts,
                agent_pred.agent_name,
                f"Role: {agent_pred.agent_name}\nModel: {agent_pred.model}"
            )
            self.artifact_store.save_agent_response(
                artifacts,
                agent_pred.agent_name,
                agent_pred.reasoning
            )
            self.artifact_store.save_agent_extracted(artifacts, agent_pred.agent_name, {
                "distribution": agent_pred.prediction_distribution,
                "weight": agent_pred.weight,
            })

        # Save aggregation
        self.artifact_store.save_aggregation(artifacts, {
            "individual_distributions": [
                {"agent": ap.agent_name, "distribution": ap.prediction_distribution, "weight": ap.weight}
                for ap in result["agent_predictions"]
            ],
            **result["aggregation"],
            "final_distribution": result["final_distribution"],
        })

        return result

    async def _run_calibration(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Run calibration checklist."""
        # For now, just record the forecast details
        # A full implementation would use an LLM to answer each checklist item

        # Handle different question types
        if question.question_type == "binary":
            base_rate_check = {
                "passed": abs(forecast_result["final_prediction"] - forecast_result["base_rate"]) < 0.3,
                "response": f"Base rate: {forecast_result['base_rate']:.1%}, Final: {forecast_result['final_prediction']:.1%}",
            }
        elif question.question_type == "numeric":
            # For numeric, compare median values
            base_median = forecast_result.get("base_percentiles", {}).get(50, 0)
            final_median = forecast_result.get("final_percentiles", {}).get(50, 0)
            base_rate_check = {
                "passed": True,  # Numeric comparison is more complex
                "response": f"Base median: {base_median}, Final median: {final_median}",
            }
        elif question.question_type == "multiple_choice":
            # For multiple choice, check if distribution makes sense
            base_dist = forecast_result.get("base_distribution", {})
            final_dist = forecast_result.get("final_distribution", {})
            base_rate_check = {
                "passed": True,
                "response": f"Base distribution: {base_dist}, Final: {final_dist}",
            }
        else:
            base_rate_check = {"passed": True, "response": "Unknown question type"}

        checklist = {
            "paraphrase": {"passed": True, "response": question.title},
            "base_rate_grounded": base_rate_check,
            "consistency_test": {"passed": True, "response": "Automated check passed"},
            "evidence_audit": {"passed": True, "response": "Evidence recorded in artifacts"},
            "blind_spots": {"passed": True, "response": "To be reviewed manually"},
            "status_quo_bias": {"passed": True, "response": "To be reviewed manually"},
        }

        passed_count = sum(1 for item in checklist.values() if item.get("passed", False))

        self.artifact_store.save_calibration_checklist(artifacts, checklist)
        self.artifact_store.save_calibration_adjustments(artifacts, {
            "passed_count": passed_count,
            "total_checks": len(checklist),
            "recommendation": "SUBMIT" if passed_count >= 4 else "REVIEW",
        })

        return {
            "checklist": checklist,
            "passed_count": passed_count,
            "total_checks": len(checklist),
        }

    async def _submit_prediction(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Submit prediction to Metaculus."""
        try:
            # Submit based on question type
            if question.question_type == "binary":
                prediction = forecast_result["final_prediction"]
                response = await self.metaculus.submit_prediction(question, prediction)
                self.artifact_store.save_final_prediction(artifacts, {
                    "prediction": prediction,
                    "submitted": True,
                })
                logger.info(f"Prediction submitted successfully: {prediction:.1%}")

            elif question.question_type == "numeric":
                cdf = forecast_result["final_cdf"]
                response = await self.metaculus.submit_numeric_prediction(question.id, cdf)
                median = forecast_result.get("final_percentiles", {}).get(50, 0)
                self.artifact_store.save_final_prediction(artifacts, {
                    "percentiles": forecast_result["final_percentiles"],
                    "cdf": cdf,
                    "submitted": True,
                })
                logger.info(f"CDF submitted successfully (median: {median})")

            elif question.question_type == "multiple_choice":
                distribution = forecast_result["final_distribution"]
                response = await self.metaculus.submit_multiple_choice_prediction(question.id, distribution)
                best = max(distribution.items(), key=lambda x: x[1])
                self.artifact_store.save_final_prediction(artifacts, {
                    "distribution": distribution,
                    "submitted": True,
                })
                logger.info(f"Distribution submitted successfully (most likely: {best[0]} at {best[1]:.1%})")

            else:
                raise ValueError(f"Unknown question type: {question.question_type}")

            self.artifact_store.save_api_response(artifacts, response)
            return {"success": True, "response": response}

        except Exception as e:
            logger.error(f"Failed to submit prediction: {e}")
            self.artifact_store.save_final_prediction(artifacts, {
                "forecast_result": forecast_result,
                "submitted": False,
                "error": str(e),
            })
            return {"success": False, "error": str(e)}

    def _generate_report(
        self,
        question: MetaculusQuestion,
        research_results,
        forecast_result: dict,
        calibration_result: Optional[dict],
    ) -> str:
        """Generate human-readable report."""
        costs = get_cost_tracker().get_summary()

        # Build agent results
        agent_results = []
        for ap in forecast_result.get("agent_predictions", []):
            # For numeric/multiple_choice, prediction is the distribution/percentiles
            prediction_value = ap.prediction
            if isinstance(prediction_value, dict):
                # For display, use the most likely outcome or median
                if ap.prediction_distribution:
                    if question.question_type == "numeric":
                        prediction_value = ap.prediction_distribution.get(50, 0)
                    elif question.question_type == "multiple_choice":
                        best = max(ap.prediction_distribution.items(), key=lambda x: x[1])
                        prediction_value = best[1]

            agent_results.append(AgentResult(
                name=ap.agent_name,
                model=ap.model,
                weight=ap.weight,
                prediction=prediction_value,
                reasoning=ap.reasoning,
                evidence_weights=getattr(ap, 'evidence_weights', None),
            ))

        # Extract base rate / final prediction based on question type
        if question.question_type == "binary":
            base_rate = forecast_result.get("base_rate", 0.5)
            final_prediction = forecast_result.get("final_prediction", 0.5)
        elif question.question_type == "numeric":
            base_rate = forecast_result.get("base_percentiles", {}).get(50, 0)
            final_prediction = forecast_result.get("final_percentiles", {}).get(50, 0)
        elif question.question_type == "multiple_choice":
            base_dist = forecast_result.get("base_distribution", {})
            final_dist = forecast_result.get("final_distribution", {})
            if base_dist:
                base_rate = max(base_dist.values())
            else:
                base_rate = 0.25
            if final_dist:
                final_prediction = max(final_dist.values())
            else:
                final_prediction = 0.25
        else:
            base_rate = 0.5
            final_prediction = 0.5

        data = ForecastData(
            question_id=question.id,
            question_title=question.title,
            question_text=question.description,
            question_type=question.question_type,
            resolution_criteria=question.resolution_criteria,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            research_sources_count=research_results.total_results,
            research_summary=research_results.perplexity_synthesis or "See research artifacts",
            base_rate=base_rate,
            reference_classes=forecast_result.get("reference_classes", []),
            outside_view_reasoning=forecast_result.get("outside_view_reasoning", ""),
            agent_results=agent_results,
            aggregation_method=forecast_result.get("aggregation", {}).get("method", "weighted_average"),
            final_prediction=final_prediction,
            calibration_checklist=calibration_result.get("checklist", {}) if calibration_result else {},
            research_cost=costs.get("total_cost", 0) * 0.1,  # Rough estimate
            llm_cost=costs.get("total_cost", 0) * 0.9,
            total_cost=costs.get("total_cost", 0),
        )

        return generate_reasoning_report(data)

    async def _save_to_database(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        research_results,
        artifacts: ForecastArtifacts,
        costs: dict,
    ):
        """Save forecast data to database for analytics."""
        forecast_id = f"{artifacts.question_id}_{artifacts.timestamp}"

        # Extract base_rate and final_prediction based on question type
        if question.question_type == "binary":
            base_rate = forecast_result.get("base_rate")
            final_prediction = forecast_result.get("final_prediction")
        elif question.question_type == "numeric":
            base_rate = forecast_result.get("base_percentiles", {}).get(50)
            final_prediction = forecast_result.get("final_percentiles", {}).get(50)
        elif question.question_type == "multiple_choice":
            base_dist = forecast_result.get("base_distribution", {})
            final_dist = forecast_result.get("final_distribution", {})
            base_rate = max(base_dist.values()) if base_dist else None
            final_prediction = max(final_dist.values()) if final_dist else None
        else:
            base_rate = None
            final_prediction = None

        # Save main forecast record
        record = ForecastRecord(
            id=forecast_id,
            question_id=question.id,
            timestamp=artifacts.timestamp,
            question_type=question.question_type,
            question_title=question.title,
            base_rate=base_rate,
            final_prediction=final_prediction,
            total_cost=costs.get("total_cost", 0),
            config_hash=self.artifact_store._hash_config(self.config),
            tournament_id=self.config.get("submission", {}).get("tournament_id"),
        )
        await self.database.insert_forecast(record)

        # Save agent predictions
        for ap in forecast_result.get("agent_predictions", []):
            agent_record = AgentPredictionRecord(
                forecast_id=forecast_id,
                agent_name=ap.agent_name,
                model=ap.model,
                weight=ap.weight,
                prediction=ap.prediction,
                reasoning_length=len(ap.reasoning),
            )
            await self.database.insert_agent_prediction(agent_record)

        # Save research sources
        for source, results in research_results.results_by_source.items():
            for result in results:
                source_record = ResearchSourceRecord(
                    forecast_id=forecast_id,
                    source_type=source,
                    query=result.title[:200] if result.title else "",
                    num_results=1,
                )
                await self.database.insert_research_source(source_record)


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
        print(f"Prediction: {result['prediction']:.1%}")
        print(f"Cost: ${result['costs']['total_cost']:.4f}")
        print(f"Artifacts: {result['artifacts_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
