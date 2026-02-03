"""
Ecclesia source implementation.

Handles forecasting on Ecclesia business questions using the same
ensemble approach as Metaculus, but with business-focused prompts
and internal context (team history) instead of web search.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from ...core.exceptions import InsufficientPredictionsError
from ...core.extractors import (
    AgentResult,
    extract_binary_probability_percent,
    extract_multiple_choice_probabilities,
    extract_percentiles_from_response,
)
from ...core.types import CoreForecast, PromptSet, Question, ResearchContext
from ...storage.artifact_store import ArtifactStore, ForecastArtifactPaths
from ...utils.llm import LLMClient
from ..base import BaseSource, register_source
from .client import AIForecast, EcclesiaBet, EcclesiaClient
from .prompts import (
    BINARY_INSIDE_VIEW_PROMPT,
    BINARY_OUTSIDE_VIEW_PROMPT,
    BUSINESS_FORECASTER_CONTEXT,
    CATEGORICAL_INSIDE_VIEW_PROMPT,
    CATEGORICAL_OUTSIDE_VIEW_PROMPT,
    NUMERIC_INSIDE_VIEW_PROMPT,
    NUMERIC_OUTSIDE_VIEW_PROMPT,
    format_options_for_prompt,
    format_options_probabilities,
)
from .research import EcclesiaContextBuilder

logger = logging.getLogger(__name__)


# Cross-pollination map (same as Metaculus - creates ensemble diversity)
CROSS_POLLINATION_MAP: dict[int, tuple[int, str]] = {
    0: (0, "Outside view prediction"),  # Forecaster 1 <- self
    1: (3, "Outside view prediction"),  # Forecaster 2 <- Forecaster 4
    2: (1, "Outside view prediction"),  # Forecaster 3 <- Forecaster 2
    3: (2, "Outside view prediction"),  # Forecaster 4 <- Forecaster 3
    4: (4, "Outside view prediction"),  # Forecaster 5 <- self
}


@register_source("ecclesia")
class EcclesiaSource(BaseSource):
    """
    Ecclesia forecast source for internal business questions.

    Key differences from Metaculus:
    - No web search (context from team history and resolved bets)
    - Business-focused prompts
    - Point estimates for numeric (not full CDFs)
    - Probabilities scale 0-100 (not 0-1)
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        super().__init__(config, llm_client, artifact_store)
        self._ecclesia_client: EcclesiaClient | None = None
        self._context_builder: EcclesiaContextBuilder | None = None

    @property
    def name(self) -> str:
        return "ecclesia"

    async def _get_client(self) -> EcclesiaClient:
        """Get or create the Ecclesia API client."""
        if self._ecclesia_client is None:
            self._ecclesia_client = EcclesiaClient()
        return self._ecclesia_client

    async def _get_context_builder(self) -> EcclesiaContextBuilder:
        """Get or create the context builder."""
        if self._context_builder is None:
            client = await self._get_client()
            self._context_builder = EcclesiaContextBuilder(client)
        return self._context_builder

    async def close(self):
        """Close the Ecclesia client connection."""
        if self._ecclesia_client is not None:
            await self._ecclesia_client.close()
            self._ecclesia_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def fetch_question(self, question_id: str) -> Question:
        """
        Fetch a bet from Ecclesia as a Question.

        Args:
            question_id: Ecclesia bet ID (MongoDB ObjectId)

        Returns:
            Question in the common format
        """
        client = await self._get_client()
        bet = await client.get_bet(question_id)
        return self._convert_bet_to_question(bet)

    async def fetch_ecclesia_bet(self, bet_id: str) -> EcclesiaBet:
        """Fetch the raw EcclesiaBet object."""
        client = await self._get_client()
        return await client.get_bet(bet_id)

    def _convert_bet_to_question(self, bet: EcclesiaBet) -> Question:
        """Convert EcclesiaBet to common Question format."""
        # Map Ecclesia bet types to common types
        question_type = bet.bet_type
        if question_type == "categorical":
            question_type = "multiple_choice"

        return Question(
            id=bet.id,
            source="ecclesia",
            title=bet.name,
            description=bet.description,
            resolution_criteria=bet.success_criteria,
            fine_print="",
            question_type=question_type,
            open_time="",
            scheduled_resolve_time=bet.deadline or "",
            options=bet.categories or [],
            raw={
                "bet_type": bet.bet_type,
                "team_id": bet.team_id,
                "status": bet.status,
                "team_probability": bet.team_probability,
            },
        )

    async def build_research_context(self, question: Question) -> ResearchContext:
        """
        Build research context for an Ecclesia question.

        Uses team history and resolved bets instead of web search.
        """
        builder = await self._get_context_builder()
        client = await self._get_client()

        # Get the full bet
        bet = await client.get_bet(question.id)

        # Build context
        context = await builder.build_context(bet)

        return ResearchContext(
            historical_context=context.historical_context,
            current_context=context.current_context,
            extra_context={
                "team_description": context.team_description,
                "calibration_summary": context.team_calibration_summary,
                "reference_classes": context.reference_classes,
            },
        )

    def get_prompts(self, question_type: str) -> PromptSet:
        """Get Ecclesia prompt templates for a question type."""
        if question_type == "binary":
            return PromptSet(
                historical_query="",  # No query generation for Ecclesia
                current_query="",
                outside_view=BINARY_OUTSIDE_VIEW_PROMPT,
                inside_view=BINARY_INSIDE_VIEW_PROMPT,
                system_claude=BUSINESS_FORECASTER_CONTEXT,
                system_gpt=BUSINESS_FORECASTER_CONTEXT,
            )
        elif question_type == "numeric":
            return PromptSet(
                historical_query="",
                current_query="",
                outside_view=NUMERIC_OUTSIDE_VIEW_PROMPT,
                inside_view=NUMERIC_INSIDE_VIEW_PROMPT,
                system_claude=BUSINESS_FORECASTER_CONTEXT,
                system_gpt=BUSINESS_FORECASTER_CONTEXT,
            )
        elif question_type in ("multiple_choice", "categorical"):
            return PromptSet(
                historical_query="",
                current_query="",
                outside_view=CATEGORICAL_OUTSIDE_VIEW_PROMPT,
                inside_view=CATEGORICAL_INSIDE_VIEW_PROMPT,
                system_claude=BUSINESS_FORECASTER_CONTEXT,
                system_gpt=BUSINESS_FORECASTER_CONTEXT,
            )
        else:
            raise ValueError(f"Unknown question type: {question_type}")

    def convert_forecast(self, forecast: CoreForecast) -> AIForecast:
        """
        Convert core forecast to Ecclesia submission format.

        Args:
            forecast: Core forecast result

        Returns:
            AIForecast for Ecclesia submission
        """
        ai_forecast = AIForecast(
            reasoning="Generated by AI ensemble forecaster",
            model_info="5-agent ensemble",
        )

        if forecast.question_type == "binary":
            # Convert 0-1 probability to 0-100
            prob = forecast.prediction
            if isinstance(prob, float) and prob <= 1.0:
                prob = prob * 100
            ai_forecast.probability = prob

        elif forecast.question_type == "numeric":
            # For Ecclesia, submit point estimate (median)
            if isinstance(forecast.prediction, dict):
                ai_forecast.estimate = forecast.prediction.get(50, forecast.prediction.get("50", 0))
            else:
                ai_forecast.estimate = forecast.prediction

        elif forecast.question_type in ("multiple_choice", "categorical"):
            # Convert to percentages summing to 100
            probs = forecast.prediction
            if isinstance(probs, list):
                # Ensure sums to 100
                total = sum(probs)
                if total != 100:
                    probs = [p * 100 / total for p in probs]
                ai_forecast.category_probabilities = probs

        return ai_forecast

    async def submit_forecast(self, question_id: str, forecast: AIForecast) -> dict:
        """
        Submit an AI forecast to Ecclesia.

        Args:
            question_id: Ecclesia bet ID
            forecast: AIForecast object

        Returns:
            Submission result dict
        """
        client = await self._get_client()
        return await client.submit_ai_forecast(question_id, forecast)

    # =========================================================================
    # Full forecast pipeline
    # =========================================================================

    async def run_forecast(
        self,
        bet_id: str,
        log: Callable[[str], Any] = print,
    ) -> CoreForecast:
        """
        Run a full forecast using the 5-agent ensemble pipeline.

        This is the main entry point for forecasting an Ecclesia question.

        Args:
            bet_id: Ecclesia bet ID
            log: Logging callback

        Returns:
            CoreForecast with prediction and metadata
        """
        # Create artifact paths if we have an artifact store
        artifacts = None
        if self.artifact_store:
            artifacts = self.artifact_store.create_forecast_artifacts(bet_id)

        # Fetch bet
        bet = await self.fetch_ecclesia_bet(bet_id)
        log(f"\nForecasting: {bet.name} (Type: {bet.bet_type})")

        # Save bet data as artifact
        if artifacts:
            self.artifact_store.save_question(artifacts, bet.raw)

        # Build context
        builder = await self._get_context_builder()
        context = await builder.build_context(bet)

        log(f"Historical context: {len(context.historical_context)} chars")
        log(f"Current context: {len(context.current_context)} chars")
        log(f"Reference classes: {len(context.reference_classes)} similar bets")

        # Save research context as artifacts
        if artifacts:
            self.artifact_store.save_search_results(
                artifacts, "historical", {"context": context.historical_context}
            )
            self.artifact_store.save_search_results(
                artifacts, "current", {"context": context.current_context}
            )

        # Get prompts
        prompts = self.get_prompts(bet.bet_type)

        # Run ensemble
        if bet.bet_type == "binary":
            return await self._run_binary_ensemble(bet, context, prompts, log, artifacts)
        elif bet.bet_type == "numeric":
            return await self._run_numeric_ensemble(bet, context, prompts, log, artifacts)
        elif bet.bet_type == "categorical":
            return await self._run_categorical_ensemble(bet, context, prompts, log, artifacts)
        else:
            raise ValueError(f"Unsupported bet type: {bet.bet_type}")

    async def _run_binary_ensemble(
        self,
        bet: EcclesiaBet,
        context: Any,
        prompts: PromptSet,
        log: Callable[[str], Any],
        artifacts: ForecastArtifactPaths | None = None,
    ) -> CoreForecast:
        """Run the 5-agent ensemble for a binary question."""
        agents = self._get_agents()

        # Format outside view prompt
        outside_view_prompt = prompts.outside_view.format(
            title=bet.name,
            success_criteria=bet.success_criteria,
            description=bet.description,
            deadline=bet.deadline or "Not specified",
            context=context.historical_context,
        )

        # Save outside view prompt
        if artifacts and self.artifact_store:
            self.artifact_store.save_outside_view_prompt(artifacts, outside_view_prompt)

        # Step 1: Run outside view predictions
        log("\n=== Running outside view predictions ===")
        outside_view_outputs = await self._run_agent_step(
            agents, outside_view_prompt, prompts.system_claude, log, "outside view"
        )

        # Save outside view outputs
        if artifacts and self.artifact_store:
            for i, output in enumerate(outside_view_outputs):
                if not isinstance(output, Exception):
                    self.artifact_store.save_forecaster_outside_view(artifacts, i + 1, output)

        # Step 2: Cross-pollinate and run inside view
        log("\n=== Running inside view predictions ===")
        agent_results = []

        inside_view_tasks = []
        for i, agent in enumerate(agents):
            # Build cross-pollinated context
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = (
                outside_view_outputs[source_idx]
                if not isinstance(outside_view_outputs[source_idx], Exception)
                else ""
            )
            cross_pollinated_context = f"{context.current_context}\n\n{label}:\n{source_output}"

            inside_view_prompt = prompts.inside_view.format(
                title=bet.name,
                success_criteria=bet.success_criteria,
                description=bet.description,
                deadline=bet.deadline or "Not specified",
                context=cross_pollinated_context,
            )

            inside_view_tasks.append(
                self._call_model(agent["model"], inside_view_prompt, prompts.system_claude)
            )

        inside_view_results = await asyncio.gather(*inside_view_tasks, return_exceptions=True)

        # Extract probabilities
        probabilities = []
        for i, (agent, result) in enumerate(zip(agents, inside_view_results, strict=True)):
            if isinstance(result, Exception):
                log(f"Forecaster {i + 1} ERROR: {result}")
                agent_results.append(
                    AgentResult(
                        agent_id=f"forecaster_{i + 1}",
                        model=agent["model"],
                        weight=agent["weight"],
                        outside_view_output=outside_view_outputs[i]
                        if not isinstance(outside_view_outputs[i], Exception)
                        else "",
                        inside_view_output="",
                        error=str(result),
                    )
                )
                probabilities.append(None)
            else:
                try:
                    prob = extract_binary_probability_percent(result)
                    log(f"Forecaster {i + 1}: {prob:.0f}%")
                    probabilities.append(prob)
                    agent_results.append(
                        AgentResult(
                            agent_id=f"forecaster_{i + 1}",
                            model=agent["model"],
                            weight=agent["weight"],
                            outside_view_output=outside_view_outputs[i]
                            if not isinstance(outside_view_outputs[i], Exception)
                            else "",
                            inside_view_output=result,
                            probability=prob,
                        )
                    )
                except Exception as e:
                    log(f"Forecaster {i + 1} extraction error: {e}")
                    agent_results.append(
                        AgentResult(
                            agent_id=f"forecaster_{i + 1}",
                            model=agent["model"],
                            weight=agent["weight"],
                            outside_view_output=outside_view_outputs[i]
                            if not isinstance(outside_view_outputs[i], Exception)
                            else "",
                            inside_view_output=result,
                            error=str(e),
                        )
                    )
                    probabilities.append(None)

        # Save inside view outputs and predictions
        if artifacts and self.artifact_store:
            for i, ar in enumerate(agent_results):
                if ar.inside_view_output:
                    self.artifact_store.save_forecaster_inside_view(
                        artifacts, i + 1, ar.inside_view_output
                    )
                self.artifact_store.save_forecaster_prediction(
                    artifacts,
                    i + 1,
                    {
                        "agent_id": ar.agent_id,
                        "model": ar.model,
                        "weight": ar.weight,
                        "probability": ar.probability,
                        "error": ar.error,
                    },
                )

        # Aggregate
        valid_probs = [
            (p, a["weight"]) for p, a in zip(probabilities, agents, strict=True) if p is not None
        ]
        if not valid_probs:
            raise InsufficientPredictionsError(
                "All agents failed to extract valid probabilities",
                valid_count=0,
                total_count=len(agents),
            )

        weighted_sum = sum(p * w for p, w in valid_probs)
        weight_sum = sum(w for _, w in valid_probs)
        final_prob = weighted_sum / weight_sum  # Keep as 0-100 for Ecclesia

        log(f"\nFinal probability: {final_prob:.0f}%")

        # Save aggregation
        if artifacts and self.artifact_store:
            self.artifact_store.save_aggregation(
                artifacts,
                {
                    "final_probability": final_prob,
                    "valid_forecasters": len(valid_probs),
                    "total_forecasters": len(agents),
                    "individual_probabilities": probabilities,
                    "weights": [a["weight"] for a in agents],
                },
            )

        return CoreForecast(
            prediction=final_prob,  # 0-100 for Ecclesia
            question_type="binary",
            agent_results=agent_results,
            historical_context=context.historical_context,
            current_context=context.current_context,
        )

    async def _run_numeric_ensemble(
        self,
        bet: EcclesiaBet,
        context: Any,
        prompts: PromptSet,
        log: Callable[[str], Any],
        artifacts: ForecastArtifactPaths | None = None,
    ) -> CoreForecast:
        """Run the 5-agent ensemble for a numeric question."""
        agents = self._get_agents()

        # Format outside view prompt
        outside_view_prompt = prompts.outside_view.format(
            title=bet.name,
            description=bet.description,
            success_criteria=bet.success_criteria,
            units="",  # Ecclesia doesn't have explicit units
            context=context.historical_context,
        )

        # Run outside view
        log("\n=== Running outside view predictions ===")
        outside_view_outputs = await self._run_agent_step(
            agents, outside_view_prompt, prompts.system_claude, log, "outside view"
        )

        # Run inside view with cross-pollination
        log("\n=== Running inside view predictions ===")
        agent_results = []
        estimates = []

        inside_view_tasks = []
        for i, agent in enumerate(agents):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = (
                outside_view_outputs[source_idx]
                if not isinstance(outside_view_outputs[source_idx], Exception)
                else ""
            )
            cross_pollinated_context = f"{context.current_context}\n\n{label}:\n{source_output}"

            inside_view_prompt = prompts.inside_view.format(
                title=bet.name,
                description=bet.description,
                success_criteria=bet.success_criteria,
                units="",
                context=cross_pollinated_context,
            )

            inside_view_tasks.append(
                self._call_model(agent["model"], inside_view_prompt, prompts.system_claude)
            )

        inside_view_results = await asyncio.gather(*inside_view_tasks, return_exceptions=True)

        for i, (agent, result) in enumerate(zip(agents, inside_view_results, strict=True)):
            if isinstance(result, Exception):
                log(f"Forecaster {i + 1} ERROR: {result}")
                agent_results.append(
                    AgentResult(
                        agent_id=f"forecaster_{i + 1}",
                        model=agent["model"],
                        weight=agent["weight"],
                        outside_view_output=outside_view_outputs[i]
                        if not isinstance(outside_view_outputs[i], Exception)
                        else "",
                        inside_view_output="",
                        error=str(result),
                    )
                )
                estimates.append(None)
            else:
                try:
                    percentiles = extract_percentiles_from_response(result, verbose=False)
                    median = percentiles.get(50, 0)
                    log(f"Forecaster {i + 1}: median = {median}")
                    estimates.append(median)
                    agent_results.append(
                        AgentResult(
                            agent_id=f"forecaster_{i + 1}",
                            model=agent["model"],
                            weight=agent["weight"],
                            outside_view_output=outside_view_outputs[i]
                            if not isinstance(outside_view_outputs[i], Exception)
                            else "",
                            inside_view_output=result,
                            percentiles=percentiles,
                        )
                    )
                except Exception as e:
                    log(f"Forecaster {i + 1} extraction error: {e}")
                    agent_results.append(
                        AgentResult(
                            agent_id=f"forecaster_{i + 1}",
                            model=agent["model"],
                            weight=agent["weight"],
                            outside_view_output=outside_view_outputs[i]
                            if not isinstance(outside_view_outputs[i], Exception)
                            else "",
                            inside_view_output=result,
                            error=str(e),
                        )
                    )
                    estimates.append(None)

        # Aggregate - weighted average of medians
        valid_estimates = [
            (e, a["weight"]) for e, a in zip(estimates, agents, strict=True) if e is not None
        ]
        if not valid_estimates:
            raise InsufficientPredictionsError(
                "All agents failed to extract valid estimates",
                valid_count=0,
                total_count=len(agents),
            )

        weighted_sum = sum(e * w for e, w in valid_estimates)
        weight_sum = sum(w for _, w in valid_estimates)
        final_estimate = weighted_sum / weight_sum

        log(f"\nFinal estimate: {final_estimate}")

        return CoreForecast(
            prediction={50: final_estimate},  # Return as dict with median
            question_type="numeric",
            agent_results=agent_results,
            historical_context=context.historical_context,
            current_context=context.current_context,
        )

    async def _run_categorical_ensemble(
        self,
        bet: EcclesiaBet,
        context: Any,
        prompts: PromptSet,
        log: Callable[[str], Any],
        artifacts: ForecastArtifactPaths | None = None,
    ) -> CoreForecast:
        """Run the 5-agent ensemble for a categorical question."""
        agents = self._get_agents()
        options = bet.categories or []
        num_options = len(options)

        options_str = format_options_for_prompt(options)
        options_probs_str = format_options_probabilities(options)

        # Format outside view prompt
        outside_view_prompt = prompts.outside_view.format(
            title=bet.name,
            description=bet.description,
            success_criteria=bet.success_criteria,
            options=options_str,
            options_format=options_probs_str,
            context=context.historical_context,
        )

        # Run outside view
        log("\n=== Running outside view predictions ===")
        outside_view_outputs = await self._run_agent_step(
            agents, outside_view_prompt, prompts.system_claude, log, "outside view"
        )

        # Run inside view
        log("\n=== Running inside view predictions ===")
        agent_results = []
        all_probs = []

        inside_view_tasks = []
        for i, agent in enumerate(agents):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = (
                outside_view_outputs[source_idx]
                if not isinstance(outside_view_outputs[source_idx], Exception)
                else ""
            )
            cross_pollinated_context = f"{context.current_context}\n\n{label}:\n{source_output}"

            inside_view_prompt = prompts.inside_view.format(
                title=bet.name,
                description=bet.description,
                success_criteria=bet.success_criteria,
                options=options_str,
                comma_separated_values=", ".join(["X"] * num_options),
                context=cross_pollinated_context,
            )

            inside_view_tasks.append(
                self._call_model(agent["model"], inside_view_prompt, prompts.system_claude)
            )

        inside_view_results = await asyncio.gather(*inside_view_tasks, return_exceptions=True)

        for i, (agent, result) in enumerate(zip(agents, inside_view_results, strict=True)):
            if isinstance(result, Exception):
                log(f"Forecaster {i + 1} ERROR: {result}")
                agent_results.append(
                    AgentResult(
                        agent_id=f"forecaster_{i + 1}",
                        model=agent["model"],
                        weight=agent["weight"],
                        outside_view_output=outside_view_outputs[i]
                        if not isinstance(outside_view_outputs[i], Exception)
                        else "",
                        inside_view_output="",
                        error=str(result),
                    )
                )
                all_probs.append(None)
            else:
                try:
                    probs = extract_multiple_choice_probabilities(result, num_options)
                    log(f"Forecaster {i + 1}: {probs}")
                    all_probs.append(probs)
                    agent_results.append(
                        AgentResult(
                            agent_id=f"forecaster_{i + 1}",
                            model=agent["model"],
                            weight=agent["weight"],
                            outside_view_output=outside_view_outputs[i]
                            if not isinstance(outside_view_outputs[i], Exception)
                            else "",
                            inside_view_output=result,
                            probabilities=probs,
                        )
                    )
                except Exception as e:
                    log(f"Forecaster {i + 1} extraction error: {e}")
                    agent_results.append(
                        AgentResult(
                            agent_id=f"forecaster_{i + 1}",
                            model=agent["model"],
                            weight=agent["weight"],
                            outside_view_output=outside_view_outputs[i]
                            if not isinstance(outside_view_outputs[i], Exception)
                            else "",
                            inside_view_output=result,
                            error=str(e),
                        )
                    )
                    all_probs.append(None)

        # Aggregate - weighted average per option
        valid_probs = [
            (p, a["weight"]) for p, a in zip(all_probs, agents, strict=True) if p is not None
        ]
        if not valid_probs:
            raise InsufficientPredictionsError(
                "All agents failed to extract valid probabilities",
                valid_count=0,
                total_count=len(agents),
            )

        # Average each option
        final_probs = []
        for opt_idx in range(num_options):
            weighted_sum = sum(p[opt_idx] * w for p, w in valid_probs)
            weight_sum = sum(w for _, w in valid_probs)
            final_probs.append(weighted_sum / weight_sum)

        # Normalize to sum to 100
        total = sum(final_probs)
        final_probs = [p * 100 / total for p in final_probs]

        log(f"\nFinal probabilities: {final_probs}")

        return CoreForecast(
            prediction=final_probs,
            question_type="multiple_choice",
            agent_results=agent_results,
            historical_context=context.historical_context,
            current_context=context.current_context,
        )

    async def _run_agent_step(
        self,
        agents: list[dict],
        prompt: str,
        system_prompt: str,
        log: Callable[[str], Any],
        step_name: str,
    ) -> list:
        """Run all agents on a single step (outside view or similar)."""
        tasks = []
        for agent in agents:
            tasks.append(self._call_model(agent["model"], prompt, system_prompt))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log(f"Forecaster {i + 1} {step_name} ERROR: {result}")
            else:
                log(f"Forecaster {i + 1} {step_name}: {len(result)} chars")

        return results

    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Call a model via LLM client."""
        messages = [{"role": "user", "content": prompt}]
        max_tokens = self.config.get("llm", {}).get("max_output_tokens", 4000)

        response = await self.llm.complete(
            model=model,
            messages=messages,
            system=system_prompt,
            max_tokens=max_tokens,
        )
        return response.content
