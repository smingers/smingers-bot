"""
Numeric Question Handler - Port from Panshul42's tournament-winning implementation

Uses BaseForecaster for the shared 5-agent ensemble pipeline.
Implements numeric-specific extraction (percentiles → CDF) and aggregation logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

from ..utils.llm import LLMClient
from ..storage.artifact_store import ArtifactStore
from .base_forecaster import BaseForecaster
from .extractors import (
    extract_percentiles_from_response,
    enforce_strict_increasing,
    AgentResult,
)
from .cdf import generate_continuous_cdf
from .exceptions import InsufficientPredictionsError, CDFGenerationError
from .prompts import (
    NUMERIC_PROMPT_HISTORICAL,
    NUMERIC_PROMPT_CURRENT,
    NUMERIC_PROMPT_1,
    NUMERIC_PROMPT_2,
)
from .search import QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class NumericForecastResult:
    """Complete result from numeric forecasting pipeline."""
    final_cdf: List[float]  # 201-point CDF
    agent_results: List[AgentResult]
    historical_context: str
    current_context: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class NumericForecaster(BaseForecaster):
    """
    Numeric question forecaster using the shared 5-agent ensemble pipeline.

    Implements numeric-specific:
    - Prompt templates (NUMERIC_PROMPT_*)
    - Percentile extraction and CDF generation
    - Weighted CDF aggregation
    """

    def _get_prompt_templates(self) -> Tuple[str, str, str, str]:
        """Return numeric-specific prompt templates."""
        return (
            NUMERIC_PROMPT_HISTORICAL,
            NUMERIC_PROMPT_CURRENT,
            NUMERIC_PROMPT_1,
            NUMERIC_PROMPT_2,
        )

    def _get_question_details(self, **question_params) -> QuestionDetails:
        """Build QuestionDetails for search pipeline."""
        return QuestionDetails(
            title=question_params.get("question_title", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            description=question_params.get("question_text", ""),
        )

    def _build_bound_messages(self, **question_params) -> Dict[str, str]:
        """Build bound-related strings for prompt formatting."""
        open_lower = question_params.get("open_lower_bound", True)
        open_upper = question_params.get("open_upper_bound", True)
        lower_bound = question_params.get("lower_bound", 0)
        upper_bound = question_params.get("upper_bound", 100)

        lower_bound_msg = "" if open_lower else f"Cannot go below {lower_bound}."
        upper_bound_msg = "" if open_upper else f"Cannot go above {upper_bound}."
        hint = f"The answer is expected to be above {lower_bound} and below {upper_bound}. Think carefully, and reconsider your sources, if your projections are outside this range."

        return {
            "lower_bound_message": lower_bound_msg,
            "upper_bound_message": upper_bound_msg,
            "hint": hint,
        }

    def _format_query_prompts(
        self,
        prompt_historical: str,
        prompt_current: str,
        **question_params,
    ) -> Tuple[str, str]:
        """Format query prompts with numeric-specific parameters."""
        bound_msgs = self._build_bound_messages(**question_params)
        unit = question_params.get("unit", "(unknown)")

        historical = prompt_historical.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=question_params.get("question_text", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            lower_bound_message=bound_msgs["lower_bound_message"],
            upper_bound_message=bound_msgs["upper_bound_message"],
            units=unit,
            hint=bound_msgs["hint"],
        )
        current = prompt_current.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=question_params.get("question_text", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            lower_bound_message=bound_msgs["lower_bound_message"],
            upper_bound_message=bound_msgs["upper_bound_message"],
            units=unit,
            hint=bound_msgs["hint"],
        )
        return historical, current

    def _format_step1_prompt(
        self,
        prompt_template: str,
        historical_context: str,
        **question_params,
    ) -> str:
        """Format Step 1 prompt with numeric-specific parameters."""
        bound_msgs = self._build_bound_messages(**question_params)
        return prompt_template.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            context=historical_context,
            units=question_params.get("unit", "(unknown)"),
            lower_bound_message=bound_msgs["lower_bound_message"],
            upper_bound_message=bound_msgs["upper_bound_message"],
            hint=bound_msgs["hint"],
        )

    def _format_step2_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """Format Step 2 prompt with cross-pollinated context."""
        bound_msgs = self._build_bound_messages(**question_params)
        return prompt_template.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            context=context,
            units=question_params.get("unit", "(unknown)"),
            lower_bound_message=bound_msgs["lower_bound_message"],
            upper_bound_message=bound_msgs["upper_bound_message"],
            hint=bound_msgs["hint"],
        )

    def _extract_prediction(self, output: str, **question_params) -> Dict[str, Any]:
        """
        Extract percentiles and generate CDF from agent output.

        Returns dict with 'percentiles' and 'cdf' keys.
        """
        percentiles = extract_percentiles_from_response(output, verbose=True)
        percentiles = enforce_strict_increasing(percentiles)

        cdf = generate_continuous_cdf(
            percentiles,
            question_params.get("open_upper_bound", True),
            question_params.get("open_lower_bound", True),
            question_params.get("upper_bound", 100),
            question_params.get("lower_bound", 0),
            question_params.get("zero_point"),
        )

        return {
            "percentiles": percentiles,
            "cdf": cdf,
        }

    def _aggregate_results(
        self,
        agent_results: List[AgentResult],
        agents: List[Dict],
        write: callable,
    ) -> List[float]:
        """Compute weighted average of CDFs."""
        all_cdfs = []

        for result, agent in zip(agent_results, agents):
            if result.cdf is not None and len(result.cdf) == 201:
                all_cdfs.append((np.array(result.cdf), agent["weight"]))

        if len(all_cdfs) < 3:
            raise InsufficientPredictionsError(
                f"Only {len(all_cdfs)} valid CDFs — need at least 3 to proceed",
                valid_count=len(all_cdfs),
                total_count=len(agents),
            )

        numer = sum(cdf * weight for cdf, weight in all_cdfs)
        denom = sum(weight for _, weight in all_cdfs)
        combined = (numer / denom).tolist()

        if len(combined) != 201:
            raise CDFGenerationError(f"Combined CDF malformed: {len(combined)} points")

        write(f"\nAggregating {len(all_cdfs)}/{len(agents)} valid CDFs")
        write(f"Combined CDF: {combined[:5]}...{combined[-5:]}")

        return combined

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
        """Build AgentResult with percentiles and cdf fields."""
        percentiles = None
        cdf = None

        if prediction is not None and isinstance(prediction, dict):
            percentiles = prediction.get("percentiles")
            cdf = prediction.get("cdf")

        return AgentResult(
            agent_id=agent_id,
            model=model,
            weight=weight,
            step1_output=step1_output,
            step2_output=step2_output,
            percentiles=percentiles,
            cdf=cdf,
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
    ) -> NumericForecastResult:
        """Build NumericForecastResult."""
        return NumericForecastResult(
            final_cdf=final_prediction,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
        )

    def _get_extracted_data(self, result: AgentResult) -> Dict:
        """Get data for extracted prediction artifact."""
        return {
            "percentiles": result.percentiles,
            "cdf_length": len(result.cdf) if result.cdf else 0,
            "error": result.error,
        }

    def _get_aggregation_data(
        self,
        agent_results: List[AgentResult],
        agents: List[Dict],
        final_prediction: Any,
    ) -> Dict:
        """Get data for aggregation artifact."""
        valid_count = sum(1 for r in agent_results if r.cdf is not None)
        return {
            "num_valid_cdfs": valid_count,
            "method": "weighted_average",
            "final_cdf_length": len(final_prediction) if final_prediction else 0,
            "final_cdf_sample": (final_prediction[:5] + final_prediction[-5:]) if final_prediction else [],
        }

    # Convenience method matching old interface
    async def forecast(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        fine_print: str,
        open_upper_bound: bool,
        open_lower_bound: bool,
        upper_bound: float,
        lower_bound: float,
        zero_point: Optional[float] = None,
        unit: str = "(unknown)",
        write: callable = print,
    ) -> NumericForecastResult:
        """
        Generate a forecast for a numeric question.

        Args:
            question_title: The question title
            question_text: Full question description/background
            resolution_criteria: How the question resolves
            fine_print: Additional resolution details
            open_upper_bound: Whether upper bound is open
            open_lower_bound: Whether lower bound is open
            upper_bound: Maximum possible value
            lower_bound: Minimum possible value
            zero_point: Reference point for non-linear scaling
            unit: Unit of measurement
            write: Logging function

        Returns:
            NumericForecastResult with 201-point CDF and all agent outputs
        """
        return await super().forecast(
            write=write,
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            open_upper_bound=open_upper_bound,
            open_lower_bound=open_lower_bound,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            zero_point=zero_point,
            unit=unit,
        )


# Convenience function
async def get_numeric_forecast(
    question_details: dict,
    config: dict,
    llm_client: Optional[LLMClient] = None,
    artifact_store: Optional[ArtifactStore] = None,
    write: callable = print,
) -> Tuple[List[float], str]:
    """
    Convenience function to get a numeric forecast.

    Returns:
        Tuple of (201-point CDF, formatted comment)
    """
    forecaster = NumericForecaster(config, llm_client, artifact_store)

    result = await forecaster.forecast(
        question_title=question_details.get("title", ""),
        question_text=question_details.get("description", ""),
        resolution_criteria=question_details.get("resolution_criteria", ""),
        fine_print=question_details.get("fine_print", ""),
        open_upper_bound=question_details.get("open_upper_bound", True),
        open_lower_bound=question_details.get("open_lower_bound", True),
        upper_bound=question_details.get("scaling", {}).get("range_max", 100),
        lower_bound=question_details.get("scaling", {}).get("range_min", 0),
        zero_point=question_details.get("scaling", {}).get("zero_point"),
        unit=question_details.get("unit", "(unknown)"),
        write=write,
    )

    # Format comment
    comment_parts = [
        f"Combined CDF: `{result.final_cdf[:5]}...{result.final_cdf[-5:]}`\n",
    ]

    for agent_result in result.agent_results:
        comment_parts.append(
            f"=== {agent_result.agent_id} ({agent_result.model}) ===\n"
            f"Output:\n{agent_result.step2_output[:500]}...\n"
        )

    comment = "\n\n".join(comment_parts)

    return result.final_cdf, comment
