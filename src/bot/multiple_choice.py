"""
Multiple Choice Question Handler

Uses BaseForecaster for the shared 5-agent ensemble pipeline.
Implements multiple choice-specific extraction and aggregation logic.
"""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

from ..utils.llm import LLMClient
from ..storage.artifact_store import ArtifactStore
from .base_forecaster import BaseForecaster
from .extractors import (
    extract_multiple_choice_probabilities,
    normalize_probabilities,
    AgentResult,
)
from .exceptions import InsufficientPredictionsError
from .prompts import (
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_1,
    MULTIPLE_CHOICE_PROMPT_2,
)
from .search import QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class MultipleChoiceForecastResult:
    """Complete result from multiple choice forecasting pipeline."""
    final_probabilities: Dict[str, float]  # Option -> probability
    agent_results: List[AgentResult]
    historical_context: str
    current_context: str
    options: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MultipleChoiceForecaster(BaseForecaster):
    """
    Multiple choice question forecaster using the shared 5-agent ensemble pipeline.

    Implements multiple choice-specific:
    - Prompt templates (MULTIPLE_CHOICE_PROMPT_*)
    - Probability extraction per option
    - Weighted average aggregation across options
    """

    def _get_prompt_templates(self) -> Tuple[str, str, str, str]:
        """Return multiple choice-specific prompt templates."""
        return (
            MULTIPLE_CHOICE_PROMPT_HISTORICAL,
            MULTIPLE_CHOICE_PROMPT_CURRENT,
            MULTIPLE_CHOICE_PROMPT_1,
            MULTIPLE_CHOICE_PROMPT_2,
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
    ) -> Tuple[str, str]:
        """Format query prompts with options parameter."""
        options = question_params.get("options", [])
        options_str = str(options)

        historical = prompt_historical.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=question_params.get("question_text", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            options=options_str,
        )
        current = prompt_current.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=question_params.get("question_text", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            options=options_str,
        )
        return historical, current

    def _format_step1_prompt(
        self,
        prompt_template: str,
        historical_context: str,
        **question_params,
    ) -> str:
        """Format Step 1 prompt with options."""
        params = self._get_common_prompt_params(**question_params)
        params["context"] = historical_context
        params["options"] = str(question_params.get("options", []))
        return prompt_template.format(**params)

    def _format_step2_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """Format Step 2 prompt with cross-pollinated context and options."""
        params = self._get_common_prompt_params(**question_params)
        params["context"] = context
        params["options"] = str(question_params.get("options", []))
        return prompt_template.format(**params)

    def _extract_prediction(self, output: str, **question_params) -> List[float]:
        """Extract and normalize probabilities from agent output."""
        options = question_params.get("options", [])
        num_options = len(options)
        probs = extract_multiple_choice_probabilities(output, num_options)
        return normalize_probabilities(probs)

    def _aggregate_results(
        self,
        agent_results: List[AgentResult],
        agents: List[Dict],
        log: Callable[[str], Any],
    ) -> Dict[str, float]:
        """Compute weighted average of option probabilities."""
        options = []  # Will be populated from question_params in _build_result

        # Collect valid predictions
        all_probs = []
        all_weights = []

        for result, agent in zip(agent_results, agents):
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
            raise InsufficientPredictionsError(
                error_msg, valid_count=0, total_count=len(agents)
            )

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
        step1_output: str,
        step2_output: str,
        prediction: Any,
        error: Optional[str],
    ) -> AgentResult:
        """Build AgentResult with probabilities field."""
        return AgentResult(
            agent_id=agent_id,
            model=model,
            weight=weight,
            step1_output=step1_output,
            step2_output=step2_output,
            probabilities=prediction if prediction is not None else [],
            error=error,
        )

    def _build_result(
        self,
        final_prediction: Any,
        agent_results: List[AgentResult],
        historical_context: str,
        current_context: str,
        agents: List[Dict],
        **question_params,
    ) -> MultipleChoiceForecastResult:
        """Build MultipleChoiceForecastResult with option -> probability mapping."""
        options = question_params.get("options", [])

        # Convert probability list to option -> probability dict
        if isinstance(final_prediction, list):
            final_probabilities = {opt: float(p) for opt, p in zip(options, final_prediction)}
        else:
            final_probabilities = final_prediction

        return MultipleChoiceForecastResult(
            final_probabilities=final_probabilities,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
            options=options,
        )

    def _get_extracted_data(self, result: AgentResult) -> Dict:
        """Get data for extracted prediction artifact."""
        return {
            "probabilities": result.probabilities,
            "error": result.error,
        }

    def _get_aggregation_data(
        self,
        agent_results: List[AgentResult],
        agents: List[Dict],
        final_prediction: Any,
    ) -> Dict:
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
        options: List[str] = None,
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
    llm_client: Optional[LLMClient] = None,
    artifact_store: Optional[ArtifactStore] = None,
    log: Callable[[str], Any] = print,
) -> Tuple[Dict[str, float], str]:
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
            f"Output:\n{agent_result.step2_output[:500]}...\n"
            f"Probabilities: {agent_result.probabilities}\n"
        )

    comment = "\n\n".join(comment_parts)

    return result.final_probabilities, comment
