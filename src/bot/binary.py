"""
Binary Question Handler - Port from Panshul42's tournament-winning implementation

Uses BaseForecaster for the shared 5-agent ensemble pipeline.
Implements binary-specific extraction and aggregation logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ..utils.llm import LLMClient
from ..storage.artifact_store import ArtifactStore
from .base_forecaster import BaseForecaster
from .extractors import extract_binary_probability_percent, AgentResult
from .exceptions import InsufficientPredictionsError
from .prompts import (
    BINARY_PROMPT_HISTORICAL,
    BINARY_PROMPT_CURRENT,
    BINARY_PROMPT_1,
    BINARY_PROMPT_2,
)
from .search import QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class BinaryForecastResult:
    """Complete result from binary forecasting pipeline."""
    final_probability: float
    agent_results: List[AgentResult]
    historical_context: str
    current_context: str
    probabilities: List[Optional[float]]
    weights: List[float]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BinaryForecaster(BaseForecaster):
    """
    Binary question forecaster using the shared 5-agent ensemble pipeline.

    Implements binary-specific:
    - Prompt templates (BINARY_PROMPT_*)
    - Probability extraction (extract_binary_probability_percent)
    - Weighted average aggregation
    """

    def _get_prompt_templates(self) -> Tuple[str, str, str, str]:
        """Return binary-specific prompt templates."""
        return (
            BINARY_PROMPT_HISTORICAL,
            BINARY_PROMPT_CURRENT,
            BINARY_PROMPT_1,
            BINARY_PROMPT_2,
        )

    def _get_question_details(self, **question_params) -> QuestionDetails:
        """Build QuestionDetails for search pipeline."""
        return QuestionDetails(
            title=question_params.get("question_title", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            description=question_params.get("question_text", ""),
        )

    def _format_step1_prompt(
        self,
        prompt_template: str,
        historical_context: str,
        **question_params,
    ) -> str:
        """Format Step 1 prompt with historical context."""
        return prompt_template.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            context=historical_context,
        )

    def _format_step2_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """Format Step 2 prompt with cross-pollinated context."""
        return prompt_template.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            context=context,
        )

    def _extract_prediction(self, output: str, **question_params) -> float:
        """Extract probability percentage from agent output."""
        return extract_binary_probability_percent(output)

    def _aggregate_results(
        self,
        agent_results: List[AgentResult],
        agents: List[Dict],
        write: callable,
    ) -> float:
        """Compute weighted average of probabilities."""
        probabilities = [r.probability for r in agent_results]
        weights = [a["weight"] for a in agents]
        valid_probs = [(p, w) for p, w in zip(probabilities, weights) if p is not None]

        if not valid_probs:
            error_msg = (
                f"All {len(agents)} agents failed to extract valid probabilities. "
                f"Probabilities: {probabilities}, Errors: {[r.error for r in agent_results]}"
            )
            logger.error(error_msg)
            write(f"FATAL ERROR: {error_msg}")
            raise InsufficientPredictionsError(
                error_msg, valid_count=0, total_count=len(agents)
            )

        weighted_sum = sum(p * w for p, w in valid_probs)
        weight_sum = sum(w for _, w in valid_probs)
        final_prob_pct = weighted_sum / weight_sum
        # Normalize to [0.001, 0.999]
        final_prob = max(0.001, min(0.999, final_prob_pct / 100))

        write(f"\nProbabilities: {probabilities}")
        write(f"Weights: {weights}")
        write(f"Final probability: {final_prob:.3f} ({final_prob*100:.1f}%)")

        return final_prob

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
        """Build AgentResult with probability field."""
        return AgentResult(
            agent_id=agent_id,
            model=model,
            weight=weight,
            step1_output=step1_output,
            step2_output=step2_output,
            probability=prediction,
            error=error,
        )

    def _build_result(
        self,
        final_prediction: float,
        agent_results: List[AgentResult],
        historical_context: str,
        current_context: str,
        agents: List[Dict],
        **question_params,
    ) -> BinaryForecastResult:
        """Build BinaryForecastResult."""
        return BinaryForecastResult(
            final_probability=final_prediction,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
            probabilities=[r.probability for r in agent_results],
            weights=[a["weight"] for a in agents],
        )

    def _get_extracted_data(self, result: AgentResult) -> Dict:
        """Get data for extracted prediction artifact."""
        return {
            "probability": result.probability,
            "error": result.error,
        }

    def _get_aggregation_data(
        self,
        agent_results: List[AgentResult],
        agents: List[Dict],
        final_prediction: float,
    ) -> Dict:
        """Get data for aggregation artifact."""
        return {
            "individual_probabilities": [r.probability for r in agent_results],
            "weights": [a["weight"] for a in agents],
            "method": "weighted_average",
            "final_probability": final_prediction,
        }

    # Convenience method matching old interface
    async def forecast(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        fine_print: str = "",
        write: callable = print,
    ) -> BinaryForecastResult:
        """
        Generate a forecast for a binary question.

        Args:
            question_title: The question title
            question_text: Full question description/background
            resolution_criteria: How the question resolves
            fine_print: Additional resolution details
            write: Logging function (default: print)

        Returns:
            BinaryForecastResult with final probability and all agent outputs
        """
        return await super().forecast(
            write=write,
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
        )


# Convenience function for direct use
async def get_binary_forecast(
    question_details: dict,
    config: dict,
    llm_client: Optional[LLMClient] = None,
    artifact_store: Optional[ArtifactStore] = None,
    write: callable = print,
) -> Tuple[float, str]:
    """
    Convenience function to get a binary forecast.

    Args:
        question_details: Dict with title, description, resolution_criteria, fine_print
        config: Configuration dict
        llm_client: Optional LLMClient
        artifact_store: Optional ArtifactStore
        write: Logging function

    Returns:
        Tuple of (final_probability, formatted_outputs)
    """
    forecaster = BinaryForecaster(config, llm_client, artifact_store)

    result = await forecaster.forecast(
        question_title=question_details.get("title", ""),
        question_text=question_details.get("description", ""),
        resolution_criteria=question_details.get("resolution_criteria", ""),
        fine_print=question_details.get("fine_print", ""),
        write=write,
    )

    # Format outputs for display
    formatted_outputs = "\n\n".join(
        f"=== Forecaster {i+1} ===\n"
        f"Model: {r.model}\n"
        f"Output:\n{r.step2_output[:1000]}...\n"
        f"Predicted Probability: {r.probability if r.probability is not None else 'N/A'}%"
        for i, r in enumerate(result.agent_results)
    )

    return result.final_probability, formatted_outputs
