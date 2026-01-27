"""
Binary Question Handler - Port from Panshul42's tournament-winning implementation

5-agent ensemble pipeline:
1. Generate historical + current search queries (in parallel)
2. Execute searches (historical for outside view, current for inside view)
3. Run 5 agents on outside view prompt (Step 1)
4. Cross-pollinate context between agents
5. Run 5 agents on inside view prompt (Step 2)
6. Extract and aggregate probabilities with weights

Agent configuration:
- Forecasters 1-2: Claude (weight 1.0 each)
- Forecaster 3: GPT-4o-mini (weight 1.0)
- Forecasters 4-5: GPT-o3 (weight 2.0 each)
"""

import asyncio
import re
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

import numpy as np

from ..utils.llm import LLMClient, LLMResponse
from ..storage.artifact_store import ArtifactStore
from .prompts_panshul42 import (
    BINARY_PROMPT_HISTORICAL,
    BINARY_PROMPT_CURRENT,
    BINARY_PROMPT_1,
    BINARY_PROMPT_2,
    CLAUDE_CONTEXT,
    GPT_CONTEXT,
)
from .search_panshul42 import SearchPipeline, QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from a single forecasting agent."""
    agent_id: str
    model: str
    weight: float
    step1_output: str
    step2_output: str
    probability: Optional[float] = None
    error: Optional[str] = None


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


class BinaryForecaster:
    """
    Binary question forecaster using Panshul42's 5-agent ensemble.

    Pipeline:
    1. Generate historical and current search queries in parallel
    2. Execute searches to get context
    3. Run 5 agents on Step 1 (outside view with historical context)
    4. Cross-pollinate: each agent gets current context + another agent's step 1 output
    5. Run 5 agents on Step 2 (inside view)
    6. Extract probabilities and compute weighted average
    """

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        artifact_store: Optional[ArtifactStore] = None,
    ):
        """
        Initialize the binary forecaster.

        Args:
            config: Configuration dict with model and agent settings
            llm_client: Optional LLMClient instance
            artifact_store: Optional ArtifactStore for saving artifacts
        """
        self.config = config
        self.llm = llm_client or LLMClient()
        self.artifact_store = artifact_store

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
        today = datetime.now().strftime("%Y-%m-%d")

        # Build question details for search
        question_details = QuestionDetails(
            title=question_title,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            description=question_text,
        )

        # =========================================================================
        # STEP 1: Generate historical and current search queries
        # =========================================================================
        write("\n=== Step 1: Generating search queries ===")

        # Format prompts for query generation
        historical_prompt = BINARY_PROMPT_HISTORICAL.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
        )
        current_prompt = BINARY_PROMPT_CURRENT.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
        )

        # Get model for query generation
        query_model = self._get_model("query_generator", "openrouter/openai/o3")

        # Run both query generations in parallel
        historical_task = self._call_model(query_model, historical_prompt)
        current_task = self._call_model(query_model, current_prompt)
        historical_output, current_output = await asyncio.gather(historical_task, current_task)

        write(f"\nHistorical query output:\n{historical_output[:500]}...")
        write(f"\nCurrent query output:\n{current_output[:500]}...")

        # Save artifacts
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
                search.process_search_queries(
                    historical_output,
                    forecaster_id="-1",
                    question_details=question_details,
                ),
                search.process_search_queries(
                    current_output,
                    forecaster_id="0",
                    question_details=question_details,
                ),
            )

        write(f"\nHistorical context ({len(historical_context)} chars)")
        write(f"Current context ({len(current_context)} chars)")

        # Save search results
        if self.artifact_store:
            self.artifact_store.save_research_source("historical_search", {"context": historical_context})
            self.artifact_store.save_research_source("current_search", {"context": current_context})

        # =========================================================================
        # STEP 3: Run 5 agents on Step 1 (outside view)
        # =========================================================================
        write("\n=== Step 3: Running Step 1 (outside view) ===")

        # Get agent configurations
        agents = self._get_agents()

        # Format Step 1 prompt (same for all agents)
        step1_prompt = BINARY_PROMPT_1.format(
            title=question_title,
            today=today,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            context=historical_context,
        )

        # Run all agents in parallel
        step1_tasks = []
        for agent in agents:
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT
            step1_tasks.append(
                self._call_model(model, step1_prompt, system_prompt=system_prompt)
            )

        step1_outputs = await asyncio.gather(*step1_tasks, return_exceptions=True)

        # Log outputs
        for i, output in enumerate(step1_outputs):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i+1} step 1 ERROR: {output}")
                step1_outputs[i] = f"Error: {output}"
            else:
                write(f"\nForecaster_{i+1} step 1 output:\n{output[:300]}...")

        # Save step 1 artifacts
        if self.artifact_store:
            self.artifact_store.save_agent_prompt("step1_shared", step1_prompt)
            for i, output in enumerate(step1_outputs):
                if not isinstance(output, Exception):
                    self.artifact_store.save_agent_response(f"forecaster_{i+1}_step1", output)

        # =========================================================================
        # STEP 4: Cross-pollinate context
        # =========================================================================
        write("\n=== Step 4: Cross-pollinating context ===")

        # Panshul42's cross-pollination logic:
        # - Agent 1 gets agent 1's step1 output
        # - Agent 2 gets agent 3's step1 output
        # - Agent 3 gets agent 2's step1 output
        # - Agent 4 gets agent 4's step1 output
        # - Agent 5 gets agent 5's step1 output
        cross_pollination_map = {
            0: 0,  # Agent 1 <- Agent 1
            1: 2,  # Agent 2 <- Agent 3
            2: 1,  # Agent 3 <- Agent 2
            3: 3,  # Agent 4 <- Agent 4
            4: 4,  # Agent 5 <- Agent 5
        }

        context_map = {}
        for i in range(5):
            source_idx = cross_pollination_map[i]
            source_output = step1_outputs[source_idx] if not isinstance(step1_outputs[source_idx], Exception) else ""

            # First 3 agents get "Outside view prediction", last 2 get "Inside view prediction"
            label = "Outside view prediction" if i < 3 else "Inside view prediction"
            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # =========================================================================
        # STEP 5: Run 5 agents on Step 2 (inside view)
        # =========================================================================
        write("\n=== Step 5: Running Step 2 (inside view) ===")

        step2_tasks = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT

            step2_prompt = BINARY_PROMPT_2.format(
                title=question_title,
                today=today,
                resolution_criteria=resolution_criteria,
                fine_print=fine_print,
                context=context_map[i],
            )

            step2_tasks.append(
                self._call_model(model, step2_prompt, system_prompt=system_prompt)
            )

        step2_outputs = await asyncio.gather(*step2_tasks, return_exceptions=True)

        # =========================================================================
        # STEP 6: Extract probabilities and aggregate
        # =========================================================================
        write("\n=== Step 6: Extracting and aggregating probabilities ===")

        probabilities = []
        agent_results = []

        for i, (agent, output) in enumerate(zip(agents, step2_outputs)):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i+1} step 2 ERROR: {output}")
                prob = None
                error = str(output)
            else:
                write(f"\nForecaster_{i+1} step 2 output:\n{output[:300]}...")
                try:
                    prob = self._extract_probability(output)
                    write(f"Forecaster_{i+1} probability: {prob}%")
                    error = None
                except Exception as e:
                    write(f"Forecaster_{i+1} extraction error: {e}")
                    prob = None
                    error = str(e)

            probabilities.append(prob)
            agent_results.append(AgentResult(
                agent_id=f"forecaster_{i+1}",
                model=agent["model"],
                weight=agent["weight"],
                step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                step2_output=output if not isinstance(output, Exception) else "",
                probability=prob,
                error=error,
            ))

        # Save step 2 artifacts
        if self.artifact_store:
            for i, result in enumerate(agent_results):
                if result.step2_output:
                    self.artifact_store.save_agent_response(f"forecaster_{i+1}_step2", result.step2_output)
                self.artifact_store.save_agent_extracted(f"forecaster_{i+1}", {
                    "probability": result.probability,
                    "error": result.error,
                })

        # Compute weighted average
        weights = [agent["weight"] for agent in agents]
        valid_probs = [(p, w) for p, w in zip(probabilities, weights) if p is not None]

        if not valid_probs:
            error_msg = (
                f"All {len(agents)} agents failed to extract valid probabilities. "
                f"Probabilities: {probabilities}, Errors: {[r.error for r in agent_results]}"
            )
            logger.error(error_msg)
            write(f"FATAL ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        weighted_sum = sum(p * w for p, w in valid_probs)
        weight_sum = sum(w for _, w in valid_probs)
        final_prob_pct = weighted_sum / weight_sum
        # Normalize to [0.001, 0.999]
        final_prob = max(0.001, min(0.999, final_prob_pct / 100))

        write(f"\nProbabilities: {probabilities}")
        write(f"Weights: {weights}")
        write(f"Final probability: {final_prob:.3f} ({final_prob*100:.1f}%)")

        # Save aggregation
        if self.artifact_store:
            self.artifact_store.save_aggregation({
                "individual_probabilities": probabilities,
                "weights": weights,
                "method": "weighted_average",
                "final_probability": final_prob,
            })

        return BinaryForecastResult(
            final_probability=final_prob,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
            probabilities=probabilities,
            weights=weights,
        )

    def _get_agents(self) -> List[dict]:
        """Get agent configurations from config."""
        # Check for mode-aware agents
        agents = self.config.get("_active_agents", [])

        if not agents:
            # Fallback to ensemble.agents
            agents = self.config.get("ensemble", {}).get("agents", [])

        if not agents:
            # Default configuration with equal weights
            agents = [
                {"name": "forecaster_1", "model": "openrouter/anthropic/claude-sonnet-4.5", "weight": 1.0},
                {"name": "forecaster_2", "model": "openrouter/anthropic/claude-sonnet-4.5", "weight": 1.0},
                {"name": "forecaster_3", "model": "openrouter/openai/o3-mini-high", "weight": 1.0},
                {"name": "forecaster_4", "model": "openrouter/openai/o3", "weight": 1.0},
                {"name": "forecaster_5", "model": "openrouter/openai/o3", "weight": 1.0},
            ]

        return agents[:5]  # Ensure max 5 agents

    def _get_model(self, key: str, default: str) -> str:
        """Get model from config with fallback."""
        active_models = self.config.get("_active_models", {})
        return active_models.get(key, self.config.get("models", {}).get(key, default))

    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call a model via LLMClient."""
        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.complete(
                model=model,
                messages=messages,
                system=system_prompt,
                max_tokens=4000,
            )
            return response.content
        except Exception as e:
            logger.error(f"Model call failed ({model}): {e}")
            raise

    def _extract_probability(self, text: str) -> float:
        """
        Extract probability percentage from response.

        Looks for "Probability: X%" pattern first, then falls back to
        any percentage in the last 500 characters.

        Returns:
            Percentage value clamped to [1, 99]. Caller divides by 100
            to get final 0-1 probability.

        Raises:
            ValueError: If no probability can be extracted.
        """
        matches = re.findall(r"Probability:\s*([0-9]+(?:\.[0-9]+)?)%", text.strip())
        if matches:
            number = float(matches[-1])
            return min(99, max(1, number))

        # Fallback: look for any percentage near the end
        matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*%", text[-500:])
        if matches:
            number = float(matches[-1])
            return min(99, max(1, number))

        snippet = text[-200:] if len(text) > 200 else text
        raise ValueError(f"Could not extract probability from response. Last 200 chars: {snippet!r}")


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
