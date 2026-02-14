"""
Base forecaster class implementing the shared 5-agent ensemble pipeline.

This module provides the common pipeline structure used by all question type handlers:
1. Generate search queries (historical + current)
2. Execute searches
3. Run outside view prediction with 5 forecaster agents
4. Cross-pollinate context between agents
5. Run inside view prediction with 5 forecaster agents
6. Extract predictions and aggregate
7. (Optional) Supervisor review when ensemble divergence is high

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
from .divergence import compute_divergence
from .extractors import AgentResult
from .handler_mixin import ForecasterMixin
from .metrics import AgentMetrics, PipelineMetrics, ResearchMetrics
from .prompts import SUPERFORECASTER_CONTEXT
from .search import QuestionDetails, SearchPipeline
from .supervisor import SupervisorAgent, SupervisorInput

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

    Implements the shared 7-step ensemble pipeline. Subclasses must implement:
    - question_type: Class-level string ("binary", "numeric", "multiple_choice")
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
        self.pipeline_warnings: list[str] = []

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

        query_temp = self._get_temperature("query_generation")
        historical_task = self._call_model(query_model, historical_prompt, temperature=query_temp)
        current_task = self._call_model(query_model, current_prompt, temperature=query_temp)
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

        forecast_temp = self._get_temperature("forecasting")
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
                    model,
                    outside_view_prompt,
                    system_prompt=system_prompt,
                    temperature=forecast_temp,
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
                self.pipeline_warnings.append(
                    f"forecaster_{i + 1} outside view failed ({agents[i]['model']}): {result}"
                )
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
                    model,
                    inside_view_prompt,
                    system_prompt=system_prompt,
                    temperature=forecast_temp,
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
                self.pipeline_warnings.append(
                    f"forecaster_{i + 1} inside view failed ({agents[i]['model']}): {result}"
                )
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
                    self.pipeline_warnings.append(
                        f"forecaster_{i + 1} extraction failed ({agent['model']}): {e}"
                    )

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

        # Save aggregation
        if self.artifact_store:
            self.artifact_store.save_aggregation(
                self._get_aggregation_data(agent_results, agents, final_prediction)
            )

        step6_end_cost = snapshot_cost("step6_aggregation", step3_end_cost)

        # =========================================================================
        # STEP 7: Optional supervisor review
        # =========================================================================
        supervisor_config = self.config.get("supervisor", {})
        if supervisor_config.get("enabled", False):
            final_prediction = await self._run_supervisor(
                agent_results=agent_results,
                agents=agents,
                final_prediction=final_prediction,
                question_params=question_params,
                log=log,
            )
            snapshot_cost("step7_supervisor", step6_end_cost)

        # Save metrics (after supervisor so cost is included)
        if self.artifact_store:
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
        params = self._get_common_prompt_params(**question_params)
        return prompt_historical.format(**params), prompt_current.format(**params)

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

    # -------------------------------------------------------------------------
    # Supervisor integration
    # -------------------------------------------------------------------------

    def _get_agent_prediction_value(self, result: AgentResult) -> Any:
        """Get the prediction value from an AgentResult for supervisor input.

        Returns the type-appropriate prediction: probability for binary,
        percentiles dict for numeric, probabilities list for multiple choice.
        """
        if self.question_type == "binary":
            return result.probability
        elif self.question_type == "numeric":
            return result.percentiles
        elif self.question_type == "multiple_choice":
            return result.probabilities
        return result.probability

    async def _run_supervisor(
        self,
        agent_results: list[AgentResult],
        agents: list[dict],
        final_prediction: Any,
        question_params: dict,
        log: Callable[[str], Any],
    ) -> Any:
        """
        Run supervisor review if ensemble divergence exceeds threshold.

        Returns the (possibly updated) final_prediction.
        """
        # Build per-forecaster prediction list for divergence check
        predictions = []
        for result in agent_results:
            pred = self._get_agent_prediction_value(result)
            predictions.append(pred)

        # Compute divergence
        divergence = compute_divergence(
            question_type=self.question_type,
            predictions=predictions,
            config=self.config,
        )

        if not divergence.should_trigger_supervisor:
            log(
                f"\n=== Step 7: Supervisor skipped "
                f"({divergence.metric_name}={divergence.metric_value:.2f}, "
                f"threshold={divergence.threshold:.2f}) ==="
            )
            return final_prediction

        log(
            f"\n=== Step 7: Running supervisor review "
            f"({divergence.metric_name}={divergence.metric_value:.2f}, "
            f"threshold={divergence.threshold:.2f}) ==="
        )

        # Build forecaster predictions for supervisor
        forecaster_predictions = []
        for result in agent_results:
            pred = self._get_agent_prediction_value(result)
            forecaster_predictions.append(
                {
                    "agent_id": result.agent_id,
                    "model": result.model,
                    "prediction": pred,
                    "reasoning": result.inside_view_output or "",
                }
            )

        supervisor_input = SupervisorInput(
            question_title=question_params.get("question_title", ""),
            question_type=self.question_type,
            resolution_criteria=question_params.get("resolution_criteria", ""),
            fine_print=question_params.get("fine_print", ""),
            background=question_params.get("background_info", "")
            or question_params.get("question_text", ""),
            open_time=question_params.get("open_time", ""),
            scheduled_resolve_time=question_params.get("scheduled_resolve_time", ""),
            today=question_params.get("today", ""),
            forecaster_predictions=forecaster_predictions,
            weighted_average_prediction=final_prediction,
            options=question_params.get("options"),
            num_options=len(question_params.get("options", []) or []) or None,
            units=question_params.get("unit_of_measure"),
            bounds_info=question_params.get("bounds_info"),
        )

        try:
            supervisor = SupervisorAgent(self.config, self.llm)
            result = await supervisor.evaluate(supervisor_input)

            log(f"  Supervisor confidence: {result.confidence.upper()}")
            log(f"  Supervisor prediction: {result.updated_prediction}")
            log(f"  Supervisor cost: ${result.cost:.4f}")

            if result.error:
                log(f"  Supervisor error: {result.error}")
                log("  Falling back to weighted average")
                return final_prediction

            # Save artifacts
            if self.artifact_store:
                self.artifact_store.save_supervisor_analysis(result.disagreement_analysis)
                if result.search_context:
                    self.artifact_store.save_supervisor_research(result.search_context)
                self.artifact_store.save_supervisor_reasoning(result.reasoning)
                self.artifact_store.save_supervisor_result(
                    {
                        "confidence": result.confidence,
                        "prediction": result.updated_prediction,
                        "search_queries": result.search_queries,
                        "cost": result.cost,
                        "divergence": {
                            "metric_name": divergence.metric_name,
                            "metric_value": divergence.metric_value,
                            "threshold": divergence.threshold,
                        },
                    }
                )

            log(f"  Using supervisor prediction: {result.updated_prediction}")
            return result.updated_prediction

        except Exception as e:
            logger.error(f"Supervisor failed: {e}")
            log(f"  Supervisor error: {e}")
            log("  Falling back to weighted average")
            self.pipeline_warnings.append(f"supervisor failed: {e}")
            return final_prediction
