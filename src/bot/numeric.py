"""
Numeric Question Handler

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
    extract_date_percentiles_from_response,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cdf_size = 201  # Default, updated per-question in _get_question_details
        self._is_date_question = False  # Default, updated per-question

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
        # Capture cdf_size and date mode for this question
        self._cdf_size = question_params.get("cdf_size", 201)
        self._is_date_question = question_params.get("is_date_question", False)
        return QuestionDetails(
            title=question_params.get("question_title", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            description=question_params.get("question_text", ""),
        )

    @staticmethod
    def _build_bound_messages(**question_params) -> Dict[str, str]:
        """Build bound-related strings for prompt formatting."""
        open_lower = question_params.get("open_lower_bound", True)
        open_upper = question_params.get("open_upper_bound", True)
        lower_bound = question_params.get("lower_bound", 0)
        upper_bound = question_params.get("upper_bound", 100)
        zero_point = question_params.get("zero_point")

        lines = [
            f"The lower bound is {lower_bound} and the upper bound is {upper_bound}.",
        ]

        # Explain what open/closed bounds mean for this specific question
        if open_lower and open_upper:
            lines.append(
                "Both bounds are OPEN: outcomes can fall below the lower bound or above the upper bound. "
                "Your percentile estimates may extend beyond this range if well-supported by evidence."
            )
        elif not open_lower and not open_upper:
            lines.append(
                "Both bounds are CLOSED: outcomes cannot fall outside this range. "
                "The true value will definitely be between the lower and upper bounds."
            )
        elif not open_lower and open_upper:
            lines.append(
                f"The lower bound is CLOSED (outcome cannot be below {lower_bound}), "
                f"but the upper bound is OPEN (outcome can exceed {upper_bound}). "
                "Your upper percentiles may extend beyond the upper bound if evidence supports it."
            )
        else:  # open_lower and not open_upper
            lines.append(
                f"The lower bound is OPEN (outcome can be below {lower_bound}), "
                f"but the upper bound is CLOSED (outcome cannot exceed {upper_bound}). "
                "Your lower percentiles may extend below the lower bound if evidence supports it."
            )

        if zero_point is not None:
            lines.append(
                f"Zero point: {zero_point} (logarithmic scale - think in terms of ratios/multipliers rather than absolute differences)."
            )

        return {
            "bounds_info": "\n".join(lines),
        }

    def _format_query_prompts(
        self,
        prompt_historical: str,
        prompt_current: str,
        **question_params,
    ) -> Tuple[str, str]:
        """Format query prompts with numeric-specific parameters."""
        bound_msgs = self._build_bound_messages(**question_params)
        # Support both old 'unit' key and new 'unit_of_measure' key
        unit = question_params.get("unit_of_measure") or question_params.get("unit", "(unknown)")
        # Use background_info if available, fall back to question_text
        background = question_params.get("background_info", "") or question_params.get("question_text", "")

        historical = prompt_historical.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=background,
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            bounds_info=bound_msgs["bounds_info"],
            units=unit,
        )
        current = prompt_current.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=background,
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            bounds_info=bound_msgs["bounds_info"],
            units=unit,
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
        # Support both old 'unit' key and new 'unit_of_measure' key
        unit = question_params.get("unit_of_measure") or question_params.get("unit", "(unknown)")
        return prompt_template.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            context=historical_context,
            units=unit,
            bounds_info=bound_msgs["bounds_info"],
        )

    def _format_step2_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """Format Step 2 prompt with cross-pollinated context."""
        bound_msgs = self._build_bound_messages(**question_params)
        # Support both old 'unit' key and new 'unit_of_measure' key
        unit = question_params.get("unit_of_measure") or question_params.get("unit", "(unknown)")
        return prompt_template.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            context=context,
            units=unit,
            bounds_info=bound_msgs["bounds_info"],
        )

    def _extract_prediction(self, output: str, **question_params) -> Dict[str, Any]:
        """
        Extract percentiles and generate CDF from agent output.

        For date questions, extracts date strings and converts to timestamps.
        For numeric questions, extracts numeric values directly.

        Returns dict with 'percentiles' and 'cdf' keys.
        """
        # Use date extractor for date questions, numeric extractor otherwise
        if self._is_date_question:
            percentiles = extract_date_percentiles_from_response(output, verbose=True)
        else:
            percentiles = extract_percentiles_from_response(output, verbose=True)

        percentiles = enforce_strict_increasing(percentiles)

        cdf = generate_continuous_cdf(
            percentiles,
            question_params.get("open_upper_bound", True),
            question_params.get("open_lower_bound", True),
            question_params.get("upper_bound", 100),
            question_params.get("lower_bound", 0),
            question_params.get("zero_point"),
            num_points=question_params.get("cdf_size", 201),
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
        expected_cdf_size = self._cdf_size
        all_cdfs = []

        for result, agent in zip(agent_results, agents):
            if result.cdf is not None and len(result.cdf) == expected_cdf_size:
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

        if len(combined) != expected_cdf_size:
            raise CDFGenerationError(f"Combined CDF malformed: {len(combined)} points (expected {expected_cdf_size})")

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
        background_info: str = "",
        resolution_criteria: str = "",
        fine_print: str = "",
        unit_of_measure: str = "",
        open_upper_bound: bool = False,
        open_lower_bound: bool = False,
        upper_bound: float = 100,
        lower_bound: float = 0,
        zero_point: Optional[float] = None,
        nominal_upper_bound: Optional[float] = None,
        nominal_lower_bound: Optional[float] = None,
        open_time: str = "",
        scheduled_resolve_time: str = "",
        cdf_size: int = 201,
        is_date_question: bool = False,
        write: callable = print,
    ) -> NumericForecastResult:
        """
        Generate a forecast for a numeric question.

        Args:
            question_title: The question title
            question_text: Full question description/background
            background_info: Additional background information
            resolution_criteria: How the question resolves
            fine_print: Additional resolution details
            unit_of_measure: Unit of measurement
            open_upper_bound: Whether upper bound is open (can exceed)
            open_lower_bound: Whether lower bound is open (can go below)
            upper_bound: Hard maximum value
            lower_bound: Hard minimum value
            zero_point: Reference point for non-linear scaling
            nominal_upper_bound: Suggested upper bound (may be tighter than hard bound)
            nominal_lower_bound: Suggested lower bound (may be tighter than hard bound)
            open_time: When the question opened for forecasting
            scheduled_resolve_time: When the question resolves
            cdf_size: Number of CDF points (201 for numeric, 102 for discrete)
            is_date_question: Whether this is a date question (uses date extraction)
            write: Logging function

        Returns:
            NumericForecastResult with CDF and all agent outputs
        """
        return await super().forecast(
            write=write,
            question_title=question_title,
            question_text=question_text,
            background_info=background_info,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            unit_of_measure=unit_of_measure,
            open_upper_bound=open_upper_bound,
            open_lower_bound=open_lower_bound,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            zero_point=zero_point,
            nominal_upper_bound=nominal_upper_bound,
            nominal_lower_bound=nominal_lower_bound,
            open_time=open_time,
            scheduled_resolve_time=scheduled_resolve_time,
            cdf_size=cdf_size,
            is_date_question=is_date_question,
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
