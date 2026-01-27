"""
Multiple Choice Question Handler - Port from Panshul42's tournament-winning implementation

5-agent ensemble pipeline:
1. Generate historical + current search queries
2. Execute searches
3. Run 5 agents on Step 1 (outside view)
4. Cross-pollinate context between agents
5. Run 5 agents on Step 2 (inside view)
6. Extract and aggregate probabilities across options

Output: Dict mapping option labels to probabilities that sum to 1.0
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

import numpy as np

from ..utils.llm import LLMClient
from ..storage.artifact_store import ArtifactStore
from .handler_mixin import ForecasterMixin
from .extractors import (
    extract_multiple_choice_probabilities,
    normalize_probabilities,
)
from .prompts import (
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_1,
    MULTIPLE_CHOICE_PROMPT_2,
    CLAUDE_CONTEXT,
    GPT_CONTEXT,
)
from .search import SearchPipeline, QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from a single forecasting agent."""
    agent_id: str
    model: str
    weight: float
    step1_output: str
    step2_output: str
    probabilities: Optional[List[float]] = None
    error: Optional[str] = None


@dataclass
class MultipleChoiceForecastResult:
    """Complete result from multiple choice forecasting pipeline."""
    final_probabilities: Dict[str, float]  # Option -> probability
    agent_results: List[AgentResult]
    historical_context: str
    current_context: str
    options: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MultipleChoiceForecaster(ForecasterMixin):
    """
    Multiple choice question forecaster using Panshul42's 5-agent ensemble.

    Returns probability distribution across options that sums to 1.0.
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
        options: List[str],
        write: callable = print,
    ) -> MultipleChoiceForecastResult:
        """
        Generate a forecast for a multiple choice question.

        Args:
            question_title: The question title
            question_text: Full question description/background
            resolution_criteria: How the question resolves
            fine_print: Additional resolution details
            options: List of option labels
            write: Logging function

        Returns:
            MultipleChoiceForecastResult with probabilities per option
        """
        today = datetime.now().strftime("%Y-%m-%d")
        num_options = len(options)

        # Question details for search
        question_details = QuestionDetails(
            title=question_title,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            description=question_text,
        )

        # Format options for prompts
        options_str = str(options)

        # =========================================================================
        # STEP 1: Generate historical and current search queries
        # =========================================================================
        write("\n=== Step 1: Generating search queries ===")

        historical_prompt = MULTIPLE_CHOICE_PROMPT_HISTORICAL.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            options=options_str,
        )
        current_prompt = MULTIPLE_CHOICE_PROMPT_CURRENT.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            options=options_str,
        )

        query_model = self._get_model("query_generator", "openrouter/openai/o3")

        historical_output, current_output = await asyncio.gather(
            self._call_model(query_model, historical_prompt),
            self._call_model(query_model, current_prompt),
        )

        write(f"\nHistorical query output:\n{historical_output[:500]}...")
        write(f"\nCurrent query output:\n{current_output[:500]}...")

        if self.artifact_store:
            self.artifact_store.save_agent_prompt("query_historical", historical_prompt)
            self.artifact_store.save_agent_response("query_historical", historical_output)
            self.artifact_store.save_agent_prompt("query_current", current_prompt)
            self.artifact_store.save_agent_response("query_current", current_output)

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
            self.artifact_store.save_research_source("historical_search", {"context": historical_context})
            self.artifact_store.save_research_source("current_search", {"context": current_context})

        # =========================================================================
        # STEP 3: Run 5 agents on Step 1 (outside view)
        # =========================================================================
        write("\n=== Step 3: Running Step 1 (outside view) ===")

        agents = self._get_agents()

        step1_prompt = MULTIPLE_CHOICE_PROMPT_1.format(
            title=question_title,
            today=today,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            context=historical_context,
            options=options_str,
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
            self.artifact_store.save_agent_prompt("step1_shared", step1_prompt)
            for i, output in enumerate(step1_outputs):
                if not isinstance(output, Exception):
                    self.artifact_store.save_agent_response(f"forecaster_{i + 1}_step1", output)

        # =========================================================================
        # STEP 4: Cross-pollinate context
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

            step2_prompt = MULTIPLE_CHOICE_PROMPT_2.format(
                title=question_title,
                today=today,
                resolution_criteria=resolution_criteria,
                fine_print=fine_print,
                context=context_map[i],
                options=options_str,
            )

            step2_tasks.append(self._call_model(model, step2_prompt, system_prompt=system_prompt))

        step2_outputs = await asyncio.gather(*step2_tasks, return_exceptions=True)

        # =========================================================================
        # STEP 6: Extract and aggregate probabilities
        # =========================================================================
        write("\n=== Step 6: Extracting and aggregating probabilities ===")

        all_probs = []
        all_weights = []
        agent_results = []
        valid_count = 0

        for i, (agent, output) in enumerate(zip(agents, step2_outputs)):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i + 1} step 2 ERROR: {output}")
                probs = None
                error = str(output)
            else:
                write(f"\nForecaster_{i + 1} step 2 output:\n{output[:300]}...")
                try:
                    probs = extract_multiple_choice_probabilities(output, num_options)
                    probs = normalize_probabilities(probs)
                    write(f"Forecaster_{i + 1} probabilities: {probs}")
                    error = None
                    valid_count += 1
                except Exception as e:
                    write(f"Forecaster_{i + 1} extraction error: {e}")
                    probs = None
                    error = str(e)

            # Only include valid probabilities in aggregation
            if probs is not None:
                all_probs.append(probs)
                all_weights.append(agent["weight"])

            agent_results.append(AgentResult(
                agent_id=f"forecaster_{i + 1}",
                model=agent["model"],
                weight=agent["weight"],
                step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                step2_output=output if not isinstance(output, Exception) else "",
                probabilities=probs if probs is not None else [],
                error=error,
            ))

        # Fail loudly if no valid extractions
        if valid_count == 0:
            error_msg = (
                f"All {len(agents)} agents failed to extract valid probabilities. "
                f"Errors: {[r.error for r in agent_results]}"
            )
            logger.error(error_msg)
            write(f"FATAL ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        # Save step 2 artifacts
        if self.artifact_store:
            for i, result in enumerate(agent_results):
                if result.step2_output:
                    self.artifact_store.save_agent_response(f"forecaster_{i + 1}_step2", result.step2_output)
                self.artifact_store.save_agent_extracted(f"forecaster_{i + 1}", {
                    "probabilities": result.probabilities,
                    "error": result.error,
                })

        # Compute weighted average across valid agents only
        probs_matrix = np.array(all_probs)
        weights = np.array(all_weights)

        write(f"\nAggregating {valid_count}/{len(agents)} valid agent predictions")

        # Weighted average
        weighted_probs = np.average(probs_matrix, axis=0, weights=weights)

        # Ensure sums to 1.0
        weighted_probs = weighted_probs / weighted_probs.sum()

        final_probabilities = {opt: float(p) for opt, p in zip(options, weighted_probs)}

        write(f"\nFinal probabilities: {json.dumps(final_probabilities, indent=2)}")

        if self.artifact_store:
            self.artifact_store.save_aggregation({
                "method": "weighted_average",
                "weights": weights.tolist(),
                "individual_probabilities": [r.probabilities for r in agent_results],
                "final_probabilities": final_probabilities,
            })

        return MultipleChoiceForecastResult(
            final_probabilities=final_probabilities,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
            options=options,
        )

# Convenience function
async def get_multiple_choice_forecast(
    question_details: dict,
    config: dict,
    llm_client: Optional[LLMClient] = None,
    artifact_store: Optional[ArtifactStore] = None,
    write: callable = print,
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
        write=write,
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
