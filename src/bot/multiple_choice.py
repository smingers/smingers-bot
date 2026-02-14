"""
Multiple Choice Question Handler

Uses BaseForecaster for the shared 5-agent ensemble pipeline.
Implements multiple choice-specific extraction and aggregation logic.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from ..storage.artifact_store import ArtifactStore
from ..utils.llm import LLMClient
from .base_forecaster import BaseForecaster
from .exceptions import InsufficientPredictionsError
from .extractors import (
    AgentResult,
    extract_multiple_choice_probabilities,
    normalize_probabilities,
)
from .prompts import (
    MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
)
from .search import QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class MultipleChoiceForecastResult:
    """Complete result from multiple choice forecasting pipeline."""

    final_probabilities: dict[str, float]  # Option -> probability
    agent_results: list[AgentResult]
    historical_context: str
    current_context: str
    options: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MultipleChoiceForecaster(BaseForecaster):
    """
    Multiple choice question forecaster using the shared 5-agent ensemble pipeline.

    Implements multiple choice-specific:
    - Prompt templates (MULTIPLE_CHOICE_PROMPT_*)
    - Probability extraction per option
    - Weighted average aggregation across options
    """

    question_type = "multiple_choice"

    def _get_prompt_templates(self) -> tuple[str, str, str, str]:
        """Return multiple choice-specific prompt templates."""
        return (
            MULTIPLE_CHOICE_PROMPT_HISTORICAL,
            MULTIPLE_CHOICE_PROMPT_CURRENT,
            MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
            MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
        )

    def _get_question_details(self, **question_params) -> QuestionDetails:
        """Build QuestionDetails for search pipeline."""
        return QuestionDetails(
            title=question_params.get("question_title", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            description=question_params.get("question_text", ""),
        )

    def _format_query_prompts(
        self,
        prompt_historical: str,
        prompt_current: str,
        **question_params,
    ) -> tuple[str, str]:
        """Format query prompts with options parameter."""
        params = self._get_common_prompt_params(**question_params)
        params["options"] = str(question_params.get("options", []))
        return prompt_historical.format(**params), prompt_current.format(**params)

    def _format_outside_view_prompt(
        self,
        prompt_template: str,
        historical_context: str,
        **question_params,
    ) -> str:
        """Format outside view prompt with options."""
        params = self._get_common_prompt_params(**question_params)
        params["context"] = historical_context
        params["options"] = str(question_params.get("options", []))
        return prompt_template.format(**params)

    def _format_inside_view_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """Format inside view prompt with cross-pollinated context and options."""
        params = self._get_common_prompt_params(**question_params)
        params["context"] = context
        params["options"] = str(question_params.get("options", []))
        return prompt_template.format(**params)

    def _extract_prediction(self, output: str, **question_params) -> list[float]:
        """Extract and normalize probabilities from agent output."""
        options = question_params.get("options", [])
        num_options = len(options)
        probs = extract_multiple_choice_probabilities(output, num_options)
        return normalize_probabilities(probs)

    def _aggregate_results(
        self,
        agent_results: list[AgentResult],
        agents: list[dict],
        log: Callable[[str], Any],
    ) -> dict[str, float]:
        """Compute weighted average of option probabilities."""
        # Collect valid predictions
        all_probs = []
        all_weights = []

        for result, agent in zip(agent_results, agents, strict=True):
            if result.probabilities is not None and len(result.probabilities) > 0:
                all_probs.append(result.probabilities)
                all_weights.append(agent["weight"])

        if not all_probs:
            error_msg = (
                f"All {len(agents)} agents failed to extract valid probabilities. "
                f"Errors: {[r.error for r in agent_results]}"
            )
            logger.error(error_msg)
            log(f"FATAL ERROR: {error_msg}")
            raise InsufficientPredictionsError(error_msg, valid_count=0, total_count=len(agents))

        # Weighted average across valid agents
        probs_matrix = np.array(all_probs)
        weights = np.array(all_weights)

        log(f"\nAggregating {len(all_probs)}/{len(agents)} valid agent predictions")

        weighted_probs = np.average(probs_matrix, axis=0, weights=weights)
        weighted_probs = weighted_probs / weighted_probs.sum()  # Ensure sums to 1.0

        log(f"Weights: {weights.tolist()}")
        log(f"Final weighted probabilities: {weighted_probs.tolist()}")

        # Return as list - will be converted to dict in _build_result
        return weighted_probs.tolist()

    def _build_agent_result(
        self,
        agent_id: str,
        model: str,
        weight: float,
        outside_view_output: str,
        inside_view_output: str,
        prediction: Any,
        error: str | None,
    ) -> AgentResult:
        """Build AgentResult with probabilities field."""
        return AgentResult(
            agent_id=agent_id,
            model=model,
            weight=weight,
            outside_view_output=outside_view_output,
            inside_view_output=inside_view_output,
            probabilities=prediction if prediction is not None else [],
            error=error,
        )

    def _build_result(
        self,
        final_prediction: Any,
        agent_results: list[AgentResult],
        historical_context: str,
        current_context: str,
        agents: list[dict],
        **question_params,
    ) -> MultipleChoiceForecastResult:
        """Build MultipleChoiceForecastResult with option -> probability mapping."""
        options = question_params.get("options", [])

        # Convert probability list to option -> probability dict
        if isinstance(final_prediction, list):
            final_probabilities = {
                opt: float(p) for opt, p in zip(options, final_prediction, strict=True)
            }
        else:
            final_probabilities = final_prediction

        return MultipleChoiceForecastResult(
            final_probabilities=final_probabilities,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
            options=options,
        )

    def _get_extracted_data(self, result: AgentResult) -> dict:
        """Get data for extracted prediction artifact."""
        return {
            "probabilities": result.probabilities,
            "error": result.error,
        }

    def _get_aggregation_data(
        self,
        agent_results: list[AgentResult],
        agents: list[dict],
        final_prediction: Any,
    ) -> dict:
        """Get data for aggregation artifact."""
        return {
            "individual_probabilities": [r.probabilities for r in agent_results],
            "weights": [a["weight"] for a in agents],
            "method": "weighted_average",
            "final_probabilities": final_prediction,
        }

    # Convenience method matching old interface
    async def forecast(
        self,
        question_title: str,
        question_text: str,
        background_info: str = "",
        resolution_criteria: str = "",
        fine_print: str = "",
        options: list[str] = None,
        open_time: str = "",
        scheduled_resolve_time: str = "",
        log: Callable[[str], Any] = print,
    ) -> MultipleChoiceForecastResult:
        """
        Generate a forecast for a multiple choice question.

        Args:
            question_title: The question title
            question_text: Full question description/background
            background_info: Additional background information
            resolution_criteria: How the question resolves
            fine_print: Additional resolution details
            options: List of option labels
            open_time: When the question opened for forecasting
            scheduled_resolve_time: When the question resolves
            log: Logging function

        Returns:
            MultipleChoiceForecastResult with probabilities per option
        """
        return await super().forecast(
            log=log,
            question_title=question_title,
            question_text=question_text,
            background_info=background_info,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            options=options or [],
            open_time=open_time,
            scheduled_resolve_time=scheduled_resolve_time,
        )


# Convenience function
async def get_multiple_choice_forecast(
    question_details: dict,
    config: dict,
    llm_client: LLMClient | None = None,
    artifact_store: ArtifactStore | None = None,
    log: Callable[[str], Any] = print,
) -> tuple[dict[str, float], str]:
    """
    Convenience function to get a multiple choice forecast.

    Returns:
        Tuple of (probabilities dict, formatted comment)
    """
    forecaster = MultipleChoiceForecaster(config, llm_client, artifact_store)

    result = await forecaster.forecast(
        question_title=question_details.get("title", ""),
        question_text=question_details.get("description", ""),
        resolution_criteria=question_details.get("resolution_criteria", ""),
        fine_print=question_details.get("fine_print", ""),
        options=question_details.get("options", []),
        log=log,
    )

    # Format comment
    comment_parts = [
        f"Average Probability Per Option: `{json.dumps(result.final_probabilities)}`\n",
    ]

    for agent_result in result.agent_results:
        comment_parts.append(
            f"=== {agent_result.agent_id} ({agent_result.model}) ===\n"
            f"Output:\n{agent_result.inside_view_output[:500]}...\n"
            f"Probabilities: {agent_result.probabilities}\n"
        )

    comment = "\n\n".join(comment_parts)

    return result.final_probabilities, comment
