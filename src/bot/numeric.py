"""
Numeric Question Handler - Port from Panshul42's tournament-winning implementation

5-agent ensemble pipeline with CDF generation:
1. Generate historical + current search queries
2. Execute searches
3. Run 5 agents on Step 1 (percentile estimation with historical context)
4. Run 5 agents on Step 2 (refined percentiles with current context + step 1 output)
5. Extract percentiles, generate CDFs, and aggregate

Output: 201-point CDF for Metaculus submission
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Union
from dataclasses import dataclass, field

import numpy as np

from ..utils.llm import LLMClient
from ..storage.artifact_store import ArtifactStore
from .handler_mixin import ForecasterMixin
from .extractors import (
    extract_percentiles_from_response,
    enforce_strict_increasing,
    VALID_PERCENTILE_KEYS,
    AgentResult,
)
from .cdf import generate_continuous_cdf
from .exceptions import InsufficientPredictionsError
from .prompts import (
    NUMERIC_PROMPT_HISTORICAL,
    NUMERIC_PROMPT_CURRENT,
    NUMERIC_PROMPT_1,
    NUMERIC_PROMPT_2,
    CLAUDE_CONTEXT,
    GPT_CONTEXT,
)
from .search import SearchPipeline, QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class NumericForecastResult:
    """Complete result from numeric forecasting pipeline."""
    final_cdf: List[float]  # 201-point CDF
    agent_results: List[AgentResult]
    historical_context: str
    current_context: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class NumericForecaster(ForecasterMixin):
    """
    Numeric question forecaster using Panshul42's 5-agent ensemble.

    Generates a 201-point CDF for Metaculus submission.
    """

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        artifact_store: Optional[ArtifactStore] = None,
    ):
        self.config = config
        self.llm = llm_client or LLMClient()
        self.artifact_store = artifact_store

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

        Returns:
            NumericForecastResult with 201-point CDF and all agent outputs
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Question details for search
        question_details = QuestionDetails(
            title=question_title,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            description=question_text,
        )

        # Build bound messages and hint
        lower_bound_msg = "" if open_lower_bound else f"Cannot go below {lower_bound}."
        upper_bound_msg = "" if open_upper_bound else f"Cannot go above {upper_bound}."
        hint = f"The answer is expected to be above {lower_bound} and below {upper_bound}. Think carefully, and reconsider your sources, if your projections are outside this range."

        # =========================================================================
        # STEP 1: Generate historical and current search queries
        # =========================================================================
        write("\n=== Step 1: Generating search queries ===")

        historical_prompt = NUMERIC_PROMPT_HISTORICAL.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            lower_bound_message=lower_bound_msg,
            upper_bound_message=upper_bound_msg,
            units=unit,
            hint=hint,
        )
        current_prompt = NUMERIC_PROMPT_CURRENT.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            lower_bound_message=lower_bound_msg,
            upper_bound_message=upper_bound_msg,
            units=unit,
            hint=hint,
        )

        query_model = self._get_model("query_generator", "openrouter/openai/o3")

        historical_output, current_output = await asyncio.gather(
            self._call_model(query_model, historical_prompt),
            self._call_model(query_model, current_prompt),
        )

        write(f"\nHistorical query output:\n{historical_output[:500]}...")
        write(f"\nCurrent query output:\n{current_output[:500]}...")

        if self.artifact_store:
            self.artifact_store.save_query_generation("historical", historical_prompt, historical_output)
            self.artifact_store.save_query_generation("current", current_prompt, current_output)

        # =========================================================================
        # STEP 2: Execute searches
        # =========================================================================
        write("\n=== Step 2: Executing searches ===")

        async with SearchPipeline(self.config, self.llm) as search:
            historical_context, current_context = await asyncio.gather(
                search.process_search_queries(historical_output, "-1", question_details),
                search.process_search_queries(current_output, "0", question_details),
            )

        write(f"\nHistorical context ({len(historical_context)} chars)")
        write(f"Current context ({len(current_context)} chars)")

        if self.artifact_store:
            self.artifact_store.save_search_results("historical", {"context": historical_context})
            self.artifact_store.save_search_results("current", {"context": current_context})

        # =========================================================================
        # STEP 3: Run 5 agents on Step 1
        # =========================================================================
        write("\n=== Step 3: Running Step 1 ===")

        agents = self._get_agents()

        step1_prompt = NUMERIC_PROMPT_1.format(
            title=question_title,
            today=today,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            context=historical_context,
            units=unit,
            lower_bound_message=lower_bound_msg,
            upper_bound_message=upper_bound_msg,
            hint=hint,
        )

        step1_tasks = []
        for agent in agents:
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT
            step1_tasks.append(self._call_model(model, step1_prompt, system_prompt=system_prompt))

        step1_outputs = await asyncio.gather(*step1_tasks, return_exceptions=True)

        for i, output in enumerate(step1_outputs):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i + 1} step 1 ERROR: {output}")
                step1_outputs[i] = f"Error: {output}"
            else:
                write(f"\nForecaster_{i + 1} step 1 output:\n{output[:300]}...")

        if self.artifact_store:
            self.artifact_store.save_step1_prompt(step1_prompt)
            for i, output in enumerate(step1_outputs):
                if not isinstance(output, Exception):
                    self.artifact_store.save_agent_step1(i + 1, output)

        # =========================================================================
        # STEP 4: Cross-pollinate context between agents
        # =========================================================================
        write("\n=== Step 4: Cross-pollinating context ===")

        # Panshul42's cross-pollination:
        # - Agent 1 gets agent 1's step1 output (Outside view)
        # - Agent 2 gets agent 3's step1 output (Outside view)
        # - Agent 3 gets agent 2's step1 output (Outside view)
        # - Agent 4 gets agent 4's step1 output (Inside view)
        # - Agent 5 gets agent 5's step1 output (Inside view)
        cross_pollination_map = {
            0: (0, "Outside view prediction"),
            1: (2, "Outside view prediction"),
            2: (1, "Outside view prediction"),
            3: (3, "Inside view prediction"),
            4: (4, "Inside view prediction"),
        }

        context_map = {}
        for i in range(5):
            source_idx, label = cross_pollination_map[i]
            source_output = step1_outputs[source_idx] if not isinstance(step1_outputs[source_idx], Exception) else ""
            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # =========================================================================
        # STEP 5: Run 5 agents on Step 2 (inside view)
        # =========================================================================
        write("\n=== Step 5: Running Step 2 (inside view) ===")

        step2_tasks = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT

            ctx = context_map.get(i, f"Current context: {current_context}")

            step2_prompt = NUMERIC_PROMPT_2.format(
                title=question_title,
                today=today,
                resolution_criteria=resolution_criteria,
                fine_print=fine_print,
                context=ctx,
                units=unit,
                lower_bound_message=lower_bound_msg,
                upper_bound_message=upper_bound_msg,
                hint=hint,
            )

            step2_tasks.append(self._call_model(model, step2_prompt, system_prompt=system_prompt))

        step2_outputs = await asyncio.gather(*step2_tasks, return_exceptions=True)

        # =========================================================================
        # STEP 6: Extract percentiles and generate CDFs
        # =========================================================================
        write("\n=== Step 6: Extracting percentiles and generating CDFs ===")

        all_cdfs = []
        agent_results = []

        for i, (agent, output) in enumerate(zip(agents, step2_outputs)):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i + 1} step 2 ERROR: {output}")
                agent_results.append(AgentResult(
                    agent_id=f"forecaster_{i + 1}",
                    model=agent["model"],
                    weight=agent["weight"],
                    step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                    step2_output="",
                    error=str(output),
                ))
                continue

            write(f"\nForecaster_{i + 1} step 2 output:\n{output[:300]}...")

            try:
                percentiles = extract_percentiles_from_response(output, verbose=True)
                percentiles = enforce_strict_increasing(percentiles)

                cdf = generate_continuous_cdf(
                    percentiles,
                    open_upper_bound,
                    open_lower_bound,
                    upper_bound,
                    lower_bound,
                    zero_point,
                )

                write(f"Forecaster_{i + 1} CDF generated ({len(cdf)} points)")

                # Weight for o3 agents (indices 3, 4) is 2, others are 1
                weight = agent["weight"]
                all_cdfs.append((np.array(cdf), weight))

                agent_results.append(AgentResult(
                    agent_id=f"forecaster_{i + 1}",
                    model=agent["model"],
                    weight=weight,
                    step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                    step2_output=output,
                    percentiles=percentiles,
                    cdf=cdf,
                ))

            except Exception as e:
                write(f"Forecaster_{i + 1} CDF generation failed: {e}")
                agent_results.append(AgentResult(
                    agent_id=f"forecaster_{i + 1}",
                    model=agent["model"],
                    weight=agent["weight"],
                    step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                    step2_output=output,
                    error=str(e),
                ))

        # Save step 2 artifacts
        if self.artifact_store:
            for i, result in enumerate(agent_results):
                if result.step2_output:
                    self.artifact_store.save_agent_step2(i + 1, result.step2_output)
                self.artifact_store.save_agent_extracted(i + 1, {
                    "percentiles": result.percentiles,
                    "cdf_length": len(result.cdf) if result.cdf else 0,
                    "error": result.error,
                })

        # =========================================================================
        # STEP 7: Aggregate CDFs
        # =========================================================================
        write("\n=== Step 7: Aggregating CDFs ===")

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

        write(f"\nCombined CDF: {combined[:5]}...{combined[-5:]}")

        if self.artifact_store:
            self.artifact_store.save_aggregation({
                "num_valid_cdfs": len(all_cdfs),
                "method": "weighted_average",
                "final_cdf_length": len(combined),
                "final_cdf_sample": combined[:5] + combined[-5:],
            })

        return NumericForecastResult(
            final_cdf=combined,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
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
