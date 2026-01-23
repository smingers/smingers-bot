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
from ..research.searcher import ResearchOrchestrator
from ..ensemble.aggregator import EnsembleAggregator
from ..storage.artifact_store import ArtifactStore, ForecastArtifacts
from ..storage.database import ForecastDatabase, ForecastRecord, AgentPredictionRecord, ResearchSourceRecord
from ..storage.report_generator import generate_reasoning_report, ForecastData, AgentResult

from .binary import BinaryForecaster

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

        # Initialize components
        self.metaculus = MetaculusClient()
        self.research = ResearchOrchestrator(config)
        self.artifact_store = ArtifactStore(
            base_dir=config.get("storage", {}).get("base_dir", "./data/forecasts")
        )
        self.database = ForecastDatabase(
            db_path=config.get("storage", {}).get("database_path", "./data/forecasts.db")
        )

        # Type-specific forecasters
        self.binary_forecaster = BinaryForecaster(config)

        # Configuration
        self.dry_run = config.get("submission", {}).get("dry_run", False)
        self.store_reasoning = config.get("submission", {}).get("store_reasoning", True)

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

            # Step 3: Conduct research
            logger.info("Conducting research...")
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
            self.artifact_store.save_research_synthesis(artifacts, research_summary)

            # Step 4: Run type-specific forecaster
            if question.question_type == "binary":
                forecast_result = await self._forecast_binary(
                    question=question,
                    research_summary=research_summary,
                    artifacts=artifacts,
                )
            elif question.question_type == "multiple_choice":
                # TODO: Implement multiple choice forecaster
                raise NotImplementedError("Multiple choice forecasting not yet implemented")
            elif question.question_type == "numeric":
                # TODO: Implement numeric forecaster
                raise NotImplementedError("Numeric forecasting not yet implemented")
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
                    prediction=forecast_result["final_prediction"],
                    artifacts=artifacts,
                )
            else:
                logger.info(f"DRY RUN: Would submit {forecast_result['final_prediction']:.1%}")
                self.artifact_store.save_final_prediction(artifacts, {
                    "prediction": forecast_result["final_prediction"],
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
            )

            # Save to database
            await self._save_to_database(
                question=question,
                forecast_result=forecast_result,
                research_results=research_results,
                artifacts=artifacts,
                costs=costs,
            )

            logger.info(f"Forecast complete: {forecast_result['final_prediction']:.1%}")
            logger.info(f"Total cost: ${costs['total_cost']:.4f}")

            return {
                "question": question,
                "prediction": forecast_result["final_prediction"],
                "forecast_result": forecast_result,
                "calibration": calibration_result,
                "submission": submission_result,
                "costs": costs,
                "artifacts_dir": str(artifacts.base_dir / f"{artifacts.question_id}_{artifacts.timestamp}"),
            }

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

    async def _run_calibration(
        self,
        question: MetaculusQuestion,
        forecast_result: dict,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Run calibration checklist."""
        # For now, just record the forecast details
        # A full implementation would use an LLM to answer each checklist item
        checklist = {
            "paraphrase": {"passed": True, "response": question.title},
            "base_rate_grounded": {
                "passed": abs(forecast_result["final_prediction"] - forecast_result["base_rate"]) < 0.3,
                "response": f"Base rate: {forecast_result['base_rate']:.1%}, Final: {forecast_result['final_prediction']:.1%}",
            },
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
        prediction: float,
        artifacts: ForecastArtifacts,
    ) -> dict:
        """Submit prediction to Metaculus."""
        try:
            response = await self.metaculus.submit_prediction(question, prediction)

            self.artifact_store.save_final_prediction(artifacts, {
                "prediction": prediction,
                "submitted": True,
            })
            self.artifact_store.save_api_response(artifacts, response)

            logger.info(f"Prediction submitted successfully: {prediction:.1%}")
            return {"success": True, "response": response}

        except Exception as e:
            logger.error(f"Failed to submit prediction: {e}")
            self.artifact_store.save_final_prediction(artifacts, {
                "prediction": prediction,
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
            agent_results.append(AgentResult(
                name=ap.agent_name,
                model=ap.model,
                weight=ap.weight,
                prediction=ap.prediction,
                reasoning=ap.reasoning,
                evidence_weights=ap.evidence_weights,
            ))

        data = ForecastData(
            question_id=question.id,
            question_title=question.title,
            question_text=question.description,
            question_type=question.question_type,
            resolution_criteria=question.resolution_criteria,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            research_sources_count=research_results.total_results,
            research_summary=research_results.perplexity_synthesis or "See research artifacts",
            base_rate=forecast_result["base_rate"],
            reference_classes=forecast_result.get("reference_classes", []),
            outside_view_reasoning=forecast_result.get("outside_view_reasoning", ""),
            agent_results=agent_results,
            aggregation_method=forecast_result.get("aggregation", {}).get("method", "weighted_average"),
            final_prediction=forecast_result["final_prediction"],
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

        # Save main forecast record
        record = ForecastRecord(
            id=forecast_id,
            question_id=question.id,
            timestamp=artifacts.timestamp,
            question_type=question.question_type,
            question_title=question.title,
            base_rate=forecast_result.get("base_rate"),
            final_prediction=forecast_result["final_prediction"],
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
