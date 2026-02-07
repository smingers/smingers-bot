"""
Base forecaster class implementing the shared 5-agent ensemble pipeline.

This module provides the common pipeline structure used by all question type handlers:
1. Generate search queries (historical + current)
2. Execute searches
3. Run outside view prediction with 5 forecaster agents
4. Cross-pollinate context between agents
5. Run inside view prediction with 5 forecaster agents
6. Extract predictions and aggregate

Subclasses implement type-specific logic by overriding abstract methods.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ..storage.artifact_store import ArtifactStore
from ..utils.llm import LLMClient, get_cost_tracker
from .extractors import AgentResult
from .handler_mixin import ForecasterMixin
from .metrics import AgentMetrics, PipelineMetrics, ResearchMetrics
from .prompts import SUPERFORECASTER_CONTEXT
from .search import QuestionDetails, SearchPipeline

logger = logging.getLogger(__name__)


# Cross-pollination map: Controls how forecasters share context between outside view and inside view.
#
# PURPOSE: Create ensemble diversity by having forecasters receive outside view
# reasoning from forecasters using DIFFERENT model families. This prevents groupthink
# and ensures the ensemble benefits from multiple reasoning styles.
#
# HOW IT WORKS:
# - After outside view, each forecaster's output is shared with another forecaster for inside view
# - The mapping below defines: forecaster_index -> (source_forecaster_index, context_label)
# - The source forecaster's outside view output becomes part of this forecaster's inside view context
#
# MAPPING STRATEGY:
# The specific model assignments are configured in config.yaml. The key principle is:
# - Forecasters 1 & 5 receive their OWN outside view output (self-consistency anchors)
# - Forecasters 2, 3, 4 receive output from a DIFFERENT model family
#
# Example with typical production models (Claude + OpenAI mix):
#   - Forecaster 2 (Claude) <- Forecaster 4 (OpenAI): Claude sees OpenAI reasoning
#   - Forecaster 3 (OpenAI) <- Forecaster 2 (Claude): OpenAI sees Claude reasoning
#   - Forecaster 4 (OpenAI) <- Forecaster 3 (OpenAI): Cross-pollination within same family
#
# This creates a "reasoning exchange" where different model architectures
# critique and build upon each other's initial forecasts.
# See config.yaml ensemble.production.agents for actual model assignments.
CROSS_POLLINATION_MAP: dict[int, tuple[int, str]] = {
    0: (0, "Outside view prediction"),  # Forecaster 1 <- self
    1: (3, "Outside view prediction"),  # Forecaster 2 <- Forecaster 4
    2: (1, "Outside view prediction"),  # Forecaster 3 <- Forecaster 2
    3: (2, "Outside view prediction"),  # Forecaster 4 <- Forecaster 3
    4: (4, "Outside view prediction"),  # Forecaster 5 <- self
}


# Sentinel prefix for failed outside view outputs. Used at the creation point
# (error handling in step 3) and checked by _is_failed_output(). Using an
# explicit sentinel avoids relying on natural exception string formats.
_FAILED_OUTPUT_PREFIX = "[FAILED] "


def _is_failed_output(output: str) -> bool:
    """Check if an outside view output represents a failure (error or truncation)."""
    return output.startswith(_FAILED_OUTPUT_PREFIX)


class BaseForecaster(ForecasterMixin, ABC):
    """
    Abstract base class for all question type forecasters.

    Implements the shared 6-step ensemble pipeline. Subclasses must implement:
    - _get_prompt_templates(): Return the 4 prompt templates for this question type
    - _get_question_details(): Build QuestionDetails from question parameters
    - _format_outside_view_prompt(): Format the outside view prompt
    - _format_inside_view_prompt(): Format the inside view prompt for each forecaster
    - _extract_prediction(): Extract type-specific prediction from forecaster output
    - _aggregate_results(): Aggregate predictions into final result
    - _build_result(): Build the final result object
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        """
        Initialize the forecaster.

        Args:
            config: Configuration dict with model and agent settings
            llm_client: Optional LLMClient instance
            artifact_store: Optional ArtifactStore for saving artifacts
        """
        self.config = config
        if llm_client:
            self.llm = llm_client
        else:
            llm_timeout = config.get("llm", {}).get("timeout_seconds")
            self.llm = LLMClient(timeout_seconds=llm_timeout)
        self.artifact_store = artifact_store

    def _get_common_prompt_params(self, **question_params) -> dict[str, str]:
        """
        Extract common prompt parameters used across all question types.

        These 7 parameters are used in every prompt template. Subclasses can
        extend by adding type-specific params (e.g., options, units, bounds_info).

        Returns:
            Dict with title, today, background, resolution_criteria, fine_print,
            open_time, and scheduled_resolve_time.
        """
        # Use background_info if available, fall back to question_text
        background = question_params.get("background_info", "") or question_params.get(
            "question_text", ""
        )
        return {
            "title": question_params.get("question_title", ""),
            "today": question_params.get("today", ""),
            "background": background,
            "resolution_criteria": question_params.get("resolution_criteria", ""),
            "fine_print": question_params.get("fine_print", ""),
            "open_time": question_params.get("open_time", ""),
            "scheduled_resolve_time": question_params.get("scheduled_resolve_time", ""),
        }

    async def forecast(
        self,
        log: Callable[[str], Any] = print,
        **question_params,
    ) -> Any:
        """
        Run the full forecasting pipeline.

        Args:
            log: Progress logging callback (default: print). Called with status messages.
            **question_params: Question-specific parameters (title, text, criteria, etc.)

        Returns:
            Type-specific forecast result object
        """
        today = datetime.now().strftime("%Y-%m-%d")
        question_params["today"] = today

        # Cost tracking by step
        cost_tracker = get_cost_tracker()
        step_costs = {}

        def snapshot_cost(step_name: str, start_cost: float) -> float:
            """Record cost for a step and return current total for next step."""
            current_cost = cost_tracker.total_cost
            step_costs[step_name] = round(current_cost - start_cost, 4)
            return current_cost

        pipeline_start_cost = cost_tracker.total_cost

        # Build question details for search
        question_details = self._get_question_details(**question_params)

        # Get prompt templates
        prompt_historical, prompt_current, prompt_outside_view, prompt_inside_view = (
            self._get_prompt_templates()
        )

        # =========================================================================
        # STEP 1: Generate historical and current search queries
        # =========================================================================
        log("\n=== Step 1: Generating search queries ===")

        historical_prompt, current_prompt = self._format_query_prompts(
            prompt_historical, prompt_current, **question_params
        )

        query_model = self._resolve_model("query_generator", "openrouter/openai/o3")

        historical_task = self._call_model(query_model, historical_prompt)
        current_task = self._call_model(query_model, current_prompt)
        historical_output, current_output = await asyncio.gather(historical_task, current_task)

        log(f"\nHistorical query output:\n{historical_output[:500]}...")
        log(f"\nCurrent query output:\n{current_output[:500]}...")

        step1_end_cost = snapshot_cost("step1_query_generation", pipeline_start_cost)

        if self.artifact_store:
            self.artifact_store.save_query_generation(
                "historical", historical_prompt, historical_output
            )
            self.artifact_store.save_query_generation("current", current_prompt, current_output)

        # =========================================================================
        # STEP 2: Execute searches
        # =========================================================================
        log("\n=== Step 2: Executing searches ===")

        # Initialize pipeline metrics tracking
        metrics = PipelineMetrics.create_empty()

        async with SearchPipeline(self.config, self.llm) as search:
            results = await asyncio.gather(
                search.scrape_question_urls(question_details),
                search.execute_searches_from_response(
                    historical_output,
                    search_id="historical",
                    question_details=question_details,
                    include_asknews=False,
                ),
                search.execute_searches_from_response(
                    current_output,
                    search_id="current",
                    question_details=question_details,
                    include_asknews=True,
                ),
            )
            (question_url_context, question_url_metadata) = results[0]
            (historical_context, historical_metadata) = results[1]
            (current_context, current_metadata) = results[2]

        # Prepend question URL content to historical context
        # (resolution source data should appear first for forecasters)
        if question_url_context:
            historical_context = question_url_context + "\n" + historical_context
            log(
                f"\nQuestion URL context ({len(question_url_context)} chars, "
                f"{question_url_metadata.get('urls_summarized', 0)} URLs summarized)"
            )

        log(f"\nHistorical context ({len(historical_context)} chars)")
        log(f"Current context ({len(current_context)} chars)")

        step2_end_cost = snapshot_cost("step2_search", step1_end_cost)

        # Store research metadata
        metrics.centralized_research["question_urls"] = ResearchMetrics(
            search_id="question_urls",
            searched=question_url_metadata.get("searched", False),
            num_queries=question_url_metadata.get("urls_found", 0),
            queries=[
                {
                    "query": u["url"],
                    "tool": "QuestionURLScrape",
                    "success": u.get("scraped", False),
                    "num_results": 1 if u.get("scraped") else 0,
                }
                for u in question_url_metadata.get("urls", [])
            ],
            tools_used=question_url_metadata.get("tools_used", []),
        )
        metrics.centralized_research["historical"] = ResearchMetrics.from_search_metadata(
            historical_metadata
        )
        metrics.centralized_research["current"] = ResearchMetrics.from_search_metadata(
            current_metadata
        )

        if self.artifact_store:
            if question_url_context:
                self.artifact_store.save_search_results(
                    "question_urls", {"context": question_url_context}
                )
            self.artifact_store.save_search_results("historical", {"context": historical_context})
            self.artifact_store.save_search_results("current", {"context": current_context})

        # =========================================================================
        # STEP 3: Run 5 forecasters on outside view prediction
        # =========================================================================
        log("\n=== Step 3: Running outside view prediction ===")

        agents = self._get_agents()

        # Initialize agent metrics
        for i, agent in enumerate(agents):
            agent_id = f"forecaster_{i + 1}"
            metrics.agents[agent_id] = AgentMetrics(
                model=agent["model"],
                weight=agent["weight"],
            )

        outside_view_prompt = self._format_outside_view_prompt(
            prompt_outside_view, historical_context, **question_params
        )

        outside_view_tasks = []
        outside_view_timings = []
        for agent in agents:
            model = agent["model"]
            system_prompt = SUPERFORECASTER_CONTEXT

            # Record start time for this forecaster
            start_time = time.time()
            outside_view_timings.append(start_time)

            outside_view_tasks.append(
                self._call_model_with_metadata(
                    model, outside_view_prompt, system_prompt=system_prompt
                )
            )

        outside_view_results = await asyncio.gather(*outside_view_tasks, return_exceptions=True)
        outside_view_outputs = []

        for i, result in enumerate(outside_view_results):
            agent_id = f"forecaster_{i + 1}"
            duration = time.time() - outside_view_timings[i]
            outside_view_metrics = metrics.agents[agent_id].step1

            if isinstance(result, Exception):
                log(f"\nForecaster_{i + 1} outside view ERROR: {result}")
                outside_view_outputs.append(f"{_FAILED_OUTPUT_PREFIX}{result}")
                outside_view_metrics.error = str(result)
                outside_view_metrics.duration_seconds = duration
            else:
                output, response_metadata = result
                log(f"\nForecaster_{i + 1} outside view output:\n{output[:300]}...")
                outside_view_outputs.append(output)

                # Track LLM metrics
                outside_view_metrics.token_input = response_metadata.get("input_tokens", 0)
                outside_view_metrics.token_output = response_metadata.get("output_tokens", 0)
                outside_view_metrics.cost = response_metadata.get("cost", 0.0)
                outside_view_metrics.duration_seconds = duration

        if self.artifact_store:
            self.artifact_store.save_outside_view_prompt(outside_view_prompt)
            for i, output in enumerate(outside_view_outputs):
                if not _is_failed_output(output):
                    self.artifact_store.save_forecaster_outside_view(i + 1, output)

        step3_end_cost = snapshot_cost("step3_outside_view", step2_end_cost)

        # =========================================================================
        # STEP 4: Cross-pollinate context
        # =========================================================================
        log("\n=== Step 4: Cross-pollinating context ===")

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            # If the designated source failed, fall back to another valid outside view
            if _is_failed_output(source_output):
                fallback_idx = None
                # Try self first (preserves diversity), then scan for any valid output
                if not _is_failed_output(outside_view_outputs[i]):
                    fallback_idx = i
                else:
                    for j in range(5):
                        if not _is_failed_output(outside_view_outputs[j]):
                            fallback_idx = j
                            break

                if fallback_idx is not None:
                    source_output = outside_view_outputs[fallback_idx]
                    logger.warning(
                        f"Cross-pollination source forecaster {source_idx + 1} failed; "
                        f"forecaster {i + 1} will receive forecaster {fallback_idx + 1}'s output instead"
                    )
                else:
                    logger.warning(
                        f"Cross-pollination source forecaster {source_idx + 1} failed; "
                        f"no valid outside views available; forecaster {i + 1} will receive empty context"
                    )
                    source_output = ""

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # =========================================================================
        # STEP 5: Run 5 forecasters on inside view prediction
        # =========================================================================
        log("\n=== Step 5: Running inside view prediction ===")

        inside_view_tasks = []
        inside_view_timings = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = SUPERFORECASTER_CONTEXT

            inside_view_prompt = self._format_inside_view_prompt(
                prompt_inside_view, context_map[i], **question_params
            )

            # Record start time for this forecaster
            start_time = time.time()
            inside_view_timings.append(start_time)

            inside_view_tasks.append(
                self._call_model_with_metadata(
                    model, inside_view_prompt, system_prompt=system_prompt
                )
            )

        inside_view_results = await asyncio.gather(*inside_view_tasks, return_exceptions=True)
        inside_view_outputs = []

        for i, result in enumerate(inside_view_results):
            agent_id = f"forecaster_{i + 1}"
            duration = time.time() - inside_view_timings[i]
            inside_view_metrics = metrics.agents[agent_id].step2

            if isinstance(result, Exception):
                inside_view_outputs.append(result)
                inside_view_metrics.error = str(result)
                inside_view_metrics.duration_seconds = duration
            else:
                output, response_metadata = result
                inside_view_outputs.append(output)

                # Track LLM metrics
                inside_view_metrics.token_input = response_metadata.get("input_tokens", 0)
                inside_view_metrics.token_output = response_metadata.get("output_tokens", 0)
                inside_view_metrics.cost = response_metadata.get("cost", 0.0)
                inside_view_metrics.duration_seconds = duration

        snapshot_cost("step5_inside_view", step3_end_cost)

        # =========================================================================
        # STEP 6: Extract predictions and aggregate
        # =========================================================================
        log("\n=== Step 6: Extracting and aggregating predictions ===")

        agent_results = []

        for i, (agent, output) in enumerate(zip(agents, inside_view_outputs, strict=True)):
            if isinstance(output, Exception):
                log(f"\nForecaster_{i + 1} inside view ERROR: {output}")
                prediction = None
                error = str(output)
            else:
                log(f"\nForecaster_{i + 1} inside view output:\n{output[:300]}...")
                try:
                    prediction = self._extract_prediction(output, **question_params)
                    log(f"Forecaster_{i + 1} prediction: {prediction}")
                    error = None
                except Exception as e:
                    log(f"Forecaster_{i + 1} extraction error: {e}")
                    prediction = None
                    error = str(e)

            agent_result = self._build_agent_result(
                agent_id=f"forecaster_{i + 1}",
                model=agent["model"],
                weight=agent["weight"],
                outside_view_output=outside_view_outputs[i]
                if not _is_failed_output(outside_view_outputs[i])
                else "",
                inside_view_output=output if not isinstance(output, Exception) else "",
                prediction=prediction,
                error=error,
            )
            agent_results.append(agent_result)

        # Save inside view artifacts
        if self.artifact_store:
            for i, result in enumerate(agent_results):
                if result.inside_view_output:
                    self.artifact_store.save_forecaster_inside_view(
                        i + 1, result.inside_view_output
                    )
                self.artifact_store.save_forecaster_prediction(
                    i + 1, self._get_extracted_data(result)
                )

        # Aggregate results
        final_prediction = self._aggregate_results(agent_results, agents, log)

        # Save aggregation and metrics
        if self.artifact_store:
            self.artifact_store.save_aggregation(
                self._get_aggregation_data(agent_results, agents, final_prediction)
            )
            # Save pipeline metrics with step costs
            metrics.step_costs = step_costs
            metrics.total_pipeline_cost = round(cost_tracker.total_cost - pipeline_start_cost, 4)
            self.artifact_store.save_tool_usage(metrics.to_dict())

        # Log cost breakdown
        log("\n=== Cost Breakdown ===")
        for step_name, cost in step_costs.items():
            log(f"  {step_name}: ${cost:.4f}")

        # Show search cost breakdown
        search_hist = metrics.centralized_research["historical"]
        search_curr = metrics.centralized_research["current"]
        if search_hist.llm_cost or search_curr.llm_cost:
            log("    Search LLM breakdown:")
            if search_hist.llm_cost_summarization:
                log(f"      historical summarization: ${search_hist.llm_cost_summarization:.4f}")
            if search_hist.llm_cost_agentic:
                log(f"      historical agentic: ${search_hist.llm_cost_agentic:.4f}")
            if search_curr.llm_cost_summarization:
                log(f"      current summarization: ${search_curr.llm_cost_summarization:.4f}")
            if search_curr.llm_cost_agentic:
                log(f"      current agentic: ${search_curr.llm_cost_agentic:.4f}")

        # Show agent costs
        log("  Agent costs:")
        for agent_id, agent_metrics in metrics.agents.items():
            s1_cost = agent_metrics.step1.cost
            s2_cost = agent_metrics.step2.cost
            log(f"    {agent_id}: S1=${s1_cost:.4f} S2=${s2_cost:.4f}")

        log(f"  TOTAL: ${metrics.total_pipeline_cost:.4f}")

        return self._build_result(
            final_prediction=final_prediction,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
            agents=agents,
            **question_params,
        )

    def _format_query_prompts(
        self,
        prompt_historical: str,
        prompt_current: str,
        **question_params,
    ) -> tuple[str, str]:
        """
        Format query generation prompts with question parameters.

        Default implementation uses common fields. Override for custom formatting.
        """
        # Use background_info if available, fall back to question_text
        background = question_params.get("background_info", "") or question_params.get(
            "question_text", ""
        )

        historical = prompt_historical.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=background,
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
        )
        current = prompt_current.format(
            title=question_params.get("question_title", ""),
            today=question_params.get("today", ""),
            background=background,
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
        )
        return historical, current

    @abstractmethod
    def _get_prompt_templates(self) -> tuple[str, str, str, str]:
        """
        Return the 4 prompt templates for this question type.

        Returns:
            Tuple of (prompt_historical, prompt_current, prompt_outside_view, prompt_inside_view)
        """
        pass

    @abstractmethod
    def _get_question_details(self, **question_params) -> QuestionDetails:
        """
        Build QuestionDetails from question parameters.

        Args:
            **question_params: Question-specific parameters

        Returns:
            QuestionDetails instance for search pipeline
        """
        pass

    @abstractmethod
    def _format_outside_view_prompt(
        self,
        prompt_template: str,
        historical_context: str,
        **question_params,
    ) -> str:
        """
        Format the outside view prompt.

        Args:
            prompt_template: The outside view prompt template
            historical_context: Search results for historical context
            **question_params: Question-specific parameters

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def _format_inside_view_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """
        Format the inside view prompt for a single forecaster.

        Args:
            prompt_template: The inside view prompt template
            context: Cross-pollinated context (current context + outside view output)
            **question_params: Question-specific parameters

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def _extract_prediction(self, output: str, **question_params) -> Any:
        """
        Extract type-specific prediction from agent output.

        Args:
            output: Raw LLM output from Step 2
            **question_params: Question-specific parameters

        Returns:
            Extracted prediction (float for binary, dict for numeric, list for MC)

        Raises:
            ExtractionError: If prediction cannot be extracted
        """
        pass

    @abstractmethod
    def _aggregate_results(
        self,
        agent_results: list[AgentResult],
        agents: list[dict],
        log: Callable[[str], Any],
    ) -> Any:
        """
        Aggregate individual predictions into final result.

        Args:
            agent_results: List of AgentResult with predictions
            agents: Agent configurations with weights
            log: Progress logging callback

        Returns:
            Final aggregated prediction

        Raises:
            InsufficientPredictionsError: If not enough valid predictions
        """
        pass

    @abstractmethod
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
        """
        Build an AgentResult with type-specific prediction field.

        Args:
            agent_id: Forecaster identifier
            model: Model name
            weight: Forecaster weight
            outside_view_output: Outside view output
            inside_view_output: Inside view output
            prediction: Extracted prediction (type-specific)
            error: Error message if extraction failed

        Returns:
            AgentResult with appropriate fields populated
        """
        pass

    @abstractmethod
    def _build_result(
        self,
        final_prediction: Any,
        agent_results: list[AgentResult],
        historical_context: str,
        current_context: str,
        agents: list[dict],
        **question_params,
    ) -> Any:
        """
        Build the final result object.

        Args:
            final_prediction: Aggregated prediction
            agent_results: List of AgentResult
            historical_context: Historical search context
            current_context: Current search context
            agents: Agent configurations
            **question_params: Question-specific parameters

        Returns:
            Type-specific result object (BinaryForecastResult, etc.)
        """
        pass

    def _get_extracted_data(self, result: AgentResult) -> dict:
        """
        Get data to save for extracted prediction artifact.

        Default returns probability field. Override for other types.
        """
        return {
            "probability": result.probability,
            "error": result.error,
        }

    def _get_aggregation_data(
        self,
        agent_results: list[AgentResult],
        agents: list[dict],
        final_prediction: Any,
    ) -> dict:
        """
        Get data to save for aggregation artifact.

        Default implementation for binary. Override for other types.
        """
        return {
            "individual_probabilities": [r.probability for r in agent_results],
            "weights": [a["weight"] for a in agents],
            "method": "weighted_average",
            "final_prediction": final_prediction,
        }
