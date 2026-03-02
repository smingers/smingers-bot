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
from .pipeline_data import (
    CrossPollinatedContext,
    EnsembleResult,
    InsideViewResult,
    OutsideViewResult,
    ResearchContext,
)
from .prompts import SUPERFORECASTER_CONTEXT
from .research_planner import IterativeResearchPlanner
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
# The specific model assignments are configured in config.yaml. For the current
# spring-aib-2026 configuration, the cross-pollination mapping is:
# - Forecaster 1 (Sonnet 4.6) receives its OWN outside view output
# - Forecaster 2 (Sonnet 4.6) receives Forecaster 5's outside view output (o3)
# - Forecaster 3 (GPT-5.2) receives Forecaster 1's outside view output (Sonnet 4.6)
# - Forecaster 4 (o3) receives Forecaster 3's outside view output (GPT-5.2)
# - Forecaster 5 (o3) receives its OWN outside view output
#
# This creates a three-outside-view structure where only forecasters 1, 3, and 5
# produce distinct outside views, but all five forecasters still run inside view
# predictions with cross-pollinated context.
CROSS_POLLINATION_MAP: dict[int, tuple[int, str]] = {
    0: (0, "Outside view prediction"),  # Forecaster 1 <- Forecaster 1
    1: (4, "Outside view prediction"),  # Forecaster 2 <- Forecaster 5
    2: (0, "Outside view prediction"),  # Forecaster 3 <- Forecaster 1
    3: (2, "Outside view prediction"),  # Forecaster 4 <- Forecaster 3
    4: (4, "Outside view prediction"),  # Forecaster 5 <- Forecaster 5
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

        This is the top-level orchestrator that calls each pipeline step in sequence.
        Individual steps can also be called directly for testing or experimentation.

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
        step_costs: dict[str, float] = {}

        def snapshot_cost(step_name: str, start_cost: float) -> float:
            """Record cost for a step and return current total for next step."""
            current_cost = cost_tracker.total_cost
            step_costs[step_name] = round(current_cost - start_cost, 4)
            return current_cost

        pipeline_start_cost = cost_tracker.total_cost

        # Build question details for search
        question_details = self._get_question_details(**question_params)

        # Thread stock return context into QuestionDetails for agentic search
        stock_return_context_for_search = question_params.get("stock_return_context", "")
        if stock_return_context_for_search:
            question_details.stock_return_context = stock_return_context_for_search

        # Get prompt templates
        prompt_historical, prompt_current, prompt_outside_view, prompt_inside_view = (
            self._get_prompt_templates()
        )

        # Initialize pipeline metrics tracking
        metrics = PipelineMetrics.create_empty()

        # =====================================================================
        # Steps 1-2: Research
        # =====================================================================
        research = await self._run_research(
            question_details=question_details,
            question_params=question_params,
            prompt_historical=prompt_historical,
            prompt_current=prompt_current,
            metrics=metrics,
            log=log,
        )
        step2_end_cost = snapshot_cost(
            "steps1_2_research"
            if self.config.get("research", {}).get("iterative_planner_enabled", False)
            else "step2_search",
            pipeline_start_cost,
        )

        # Save research artifacts
        if self.artifact_store:
            self.artifact_store.save_search_results(
                "historical", {"context": research.historical_context}
            )
            self.artifact_store.save_search_results(
                "current", {"context": research.current_context}
            )

        # =====================================================================
        # Step 3: Outside view prediction
        # =====================================================================
        agents = self._get_agents()

        # Initialize agent metrics
        for i, agent in enumerate(agents):
            agent_id = f"forecaster_{i + 1}"
            metrics.agents[agent_id] = AgentMetrics(
                model=agent["model"],
                weight=agent["weight"],
            )

        outside_view_prompt = self._format_outside_view_prompt(
            prompt_outside_view, research.historical_context, **question_params
        )
        forecast_temp = self._get_temperature("forecasting")

        outside_view = await self._run_outside_view(
            agents=agents,
            outside_view_prompt=outside_view_prompt,
            forecast_temp=forecast_temp,
            metrics=metrics,
            log=log,
        )

        # Save outside view artifacts
        if self.artifact_store:
            self.artifact_store.save_outside_view_prompt(outside_view.prompt)
            for i, output in enumerate(outside_view.outputs):
                if not _is_failed_output(output):
                    self.artifact_store.save_forecaster_outside_view(i + 1, output)
                    if i in outside_view.reasoning:
                        self.artifact_store.save_forecaster_reasoning(
                            i + 1, "outside_view", outside_view.reasoning[i]
                        )

        step3_end_cost = snapshot_cost("step3_outside_view", step2_end_cost)

        # =====================================================================
        # Step 4: Cross-pollinate context
        # =====================================================================
        log("\n=== Step 4: Cross-pollinating context ===")

        cross_poll = self._cross_pollinate(
            outside_view_outputs=outside_view.outputs,
            current_context=research.current_context,
        )

        # =====================================================================
        # Step 5: Inside view prediction
        # =====================================================================
        inside_view = await self._run_inside_view(
            agents=agents,
            context_map=cross_poll.context_map,
            prompt_inside_view=prompt_inside_view,
            forecast_temp=forecast_temp,
            question_params=question_params,
            metrics=metrics,
            log=log,
        )

        snapshot_cost("step5_inside_view", step3_end_cost)

        # =====================================================================
        # Step 6: Extract predictions and aggregate
        # =====================================================================
        ensemble = self._extract_and_aggregate(
            agents=agents,
            outside_view_outputs=outside_view.outputs,
            inside_view_result=inside_view,
            question_params=question_params,
            log=log,
        )

        # Save inside view and extraction artifacts
        if self.artifact_store:
            for i, result in enumerate(ensemble.agent_results):
                if result.inside_view_output:
                    self.artifact_store.save_forecaster_inside_view(
                        i + 1, result.inside_view_output
                    )
                    if i in inside_view.reasoning:
                        self.artifact_store.save_forecaster_reasoning(
                            i + 1, "inside_view", inside_view.reasoning[i]
                        )
                self.artifact_store.save_forecaster_prediction(
                    i + 1, self._get_extracted_data(result)
                )
            self.artifact_store.save_aggregation(
                self._get_aggregation_data(
                    ensemble.agent_results, agents, ensemble.final_prediction
                )
            )

        step6_end_cost = snapshot_cost("step6_aggregation", step3_end_cost)

        # =====================================================================
        # Step 7: Optional supervisor review
        # =====================================================================
        final_prediction = ensemble.final_prediction
        supervisor_config = self.config.get("supervisor", {})
        if supervisor_config.get("enabled", False):
            final_prediction = await self._run_supervisor(
                agent_results=ensemble.agent_results,
                agents=agents,
                final_prediction=final_prediction,
                question_params=question_params,
                seed_context=research.seed_context,
                log=log,
            )
            snapshot_cost("step7_supervisor", step6_end_cost)

        # Save metrics (after supervisor so cost is included)
        if self.artifact_store:
            metrics.step_costs = step_costs
            metrics.total_pipeline_cost = round(cost_tracker.total_cost - pipeline_start_cost, 4)
            self.artifact_store.save_tool_usage(metrics.to_dict())

        # Log cost breakdown
        self._log_cost_breakdown(metrics, step_costs, log)

        return self._build_result(
            final_prediction=final_prediction,
            agent_results=ensemble.agent_results,
            historical_context=research.historical_context,
            current_context=research.current_context,
            agents=agents,
            **question_params,
        )

    # =========================================================================
    # Pipeline step methods — each can be called independently for testing
    # =========================================================================

    async def _run_research(
        self,
        question_details: QuestionDetails,
        question_params: dict,
        prompt_historical: str,
        prompt_current: str,
        metrics: PipelineMetrics,
        log: Callable[[str], Any] = print,
    ) -> ResearchContext:
        """
        Steps 1-2: Run research to gather historical and current context.

        Supports two modes controlled by config.research.iterative_planner_enabled:
        - Iterative planner: unified plan-execute-reflect-assemble pipeline
        - Legacy: independent historical + current query generation and search

        Args:
            question_details: Structured question metadata for search tools
            question_params: Raw question parameters dict
            prompt_historical: Historical query generation prompt template
            prompt_current: Current query generation prompt template
            metrics: PipelineMetrics to populate with research metadata
            log: Progress logging callback

        Returns:
            ResearchContext with historical_context, current_context, and metrics
        """
        use_planner = self.config.get("research", {}).get("iterative_planner_enabled", False)

        if use_planner:
            return await self._run_research_planner(question_details, question_params, metrics, log)
        else:
            return await self._run_research_legacy(
                question_details, question_params, prompt_historical, prompt_current, metrics, log
            )

    async def _run_research_planner(
        self,
        question_details: QuestionDetails,
        question_params: dict,
        metrics: PipelineMetrics,
        log: Callable[[str], Any],
    ) -> ResearchContext:
        """Steps 1-2 via iterative research planner."""
        log("\n=== Steps 1-2: Iterative Research Planner ===")

        planner = IterativeResearchPlanner(self.config, self.llm, self.artifact_store)
        plan_result = await planner.run(question_details, self.question_type, question_params, log)

        log(f"\nHistorical context ({len(plan_result.historical_context)} chars)")
        log(f"Current context ({len(plan_result.current_context)} chars)")

        # Populate metrics from planner metadata
        plan_meta = plan_result.metadata
        all_queries = plan_meta.get("query_details", [])
        hist_queries = [q for q in all_queries if q["temporal_role"] == "historical"]
        curr_queries = [q for q in all_queries if q["temporal_role"] == "current"]

        research_metrics = {
            "historical": ResearchMetrics(
                search_id="historical",
                searched=len(hist_queries) > 0,
                num_queries=len(hist_queries),
                queries=hist_queries,
                tools_used=list({q["tool"] for q in hist_queries}),
            ),
            "current": ResearchMetrics(
                search_id="current",
                searched=len(curr_queries) > 0,
                num_queries=len(curr_queries),
                queries=curr_queries,
                tools_used=list({q["tool"] for q in curr_queries}),
            ),
        }

        metrics.centralized_research.update(research_metrics)

        return ResearchContext(
            historical_context=plan_result.historical_context,
            current_context=plan_result.current_context,
            metrics=research_metrics,
            seed_context=plan_result.seed_context or "",
        )

    async def _run_research_legacy(
        self,
        question_details: QuestionDetails,
        question_params: dict,
        prompt_historical: str,
        prompt_current: str,
        metrics: PipelineMetrics,
        log: Callable[[str], Any],
    ) -> ResearchContext:
        """Steps 1-2 via legacy independent query generation + search."""
        # Step 1: Generate queries
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

        if self.artifact_store:
            self.artifact_store.save_query_generation(
                "historical", historical_prompt, historical_output
            )
            self.artifact_store.save_query_generation("current", current_prompt, current_output)

        # Step 2: Execute searches
        log("\n=== Step 2: Executing searches ===")

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
        if question_url_context:
            historical_context = question_url_context + "\n" + historical_context
            log(
                f"\nQuestion URL context ({len(question_url_context)} chars, "
                f"{question_url_metadata.get('urls_summarized', 0)} URLs summarized)"
            )

        # Prepend stock return distribution to both contexts
        stock_return_context = question_params.get("stock_return_context", "")
        if stock_return_context:
            historical_context = stock_return_context + "\n" + historical_context
            current_context = stock_return_context + "\n" + current_context
            log(f"\nStock return distribution context injected ({len(stock_return_context)} chars)")

        log(f"\nHistorical context ({len(historical_context)} chars)")
        log(f"Current context ({len(current_context)} chars)")

        # Populate research metrics
        research_metrics: dict[str, ResearchMetrics] = {}
        research_metrics["question_urls"] = ResearchMetrics(
            search_id="question_urls",
            searched=question_url_metadata.get("searched", False),
            num_queries=question_url_metadata.get("urls_found", 0),
            queries=[
                {
                    "query": u["url"],
                    "tool": "QuestionURLScrape",
                    "success": u.get("scraped", False),
                    "num_results": 1 if u.get("scraped") else 0,
                    "domain": u.get("domain"),
                    "method": u.get("method"),
                    "status_code": u.get("status_code"),
                    "content_words": u.get("content_words"),
                    "error": u.get("error"),
                }
                for u in question_url_metadata.get("urls", [])
            ],
            tools_used=question_url_metadata.get("tools_used", []),
        )
        research_metrics["historical"] = ResearchMetrics.from_search_metadata(historical_metadata)
        research_metrics["current"] = ResearchMetrics.from_search_metadata(current_metadata)

        metrics.centralized_research.update(research_metrics)

        # Save question URL context artifact (separate from historical/current)
        if self.artifact_store and question_url_context:
            self.artifact_store.save_search_results(
                "question_urls", {"context": question_url_context}
            )

        return ResearchContext(
            historical_context=historical_context,
            current_context=current_context,
            metrics=research_metrics,
            seed_context=question_url_context or "",
        )

    async def _run_outside_view(
        self,
        agents: list[dict],
        outside_view_prompt: str,
        forecast_temp: float,
        metrics: PipelineMetrics,
        log: Callable[[str], Any] = print,
    ) -> OutsideViewResult:
        """
        Step 3: Run outside view prediction with the forecaster ensemble.

        Only forecasters 1, 3, and 5 (indices 0, 2, 4) generate distinct outside views.
        Forecasters 2 and 4 (indices 1, 3) reuse outputs from 5 and 3 respectively.

        Args:
            agents: List of 5 agent config dicts (name, model, weight)
            outside_view_prompt: Formatted outside view prompt
            forecast_temp: Temperature for forecasting LLM calls
            metrics: PipelineMetrics to populate with agent step1 data
            log: Progress logging callback

        Returns:
            OutsideViewResult with 5 outputs, reasoning, and the prompt used
        """
        log("\n=== Step 3: Running outside view prediction ===")

        # Only forecasters 1, 3, and 5 generate distinct outside views
        outside_view_tasks: list[asyncio.Future] = []
        outside_view_timings: list[float] = []
        real_indices = [0, 2, 4]

        for idx in real_indices:
            agent = agents[idx]
            model = agent["model"]
            system_prompt = SUPERFORECASTER_CONTEXT

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

        outside_view_results_raw = await asyncio.gather(*outside_view_tasks, return_exceptions=True)

        # Initialize outputs for all 5 forecasters
        outside_view_outputs: list[str] = ["" for _ in range(len(agents))]
        outside_view_reasoning: dict[int, str] = {}

        # Populate results for the forecasters that actually ran
        for offset, idx in enumerate(real_indices):
            result = outside_view_results_raw[offset]
            agent_id = f"forecaster_{idx + 1}"
            duration = time.time() - outside_view_timings[offset]
            outside_view_metrics = metrics.agents[agent_id].step1

            if isinstance(result, Exception):
                log(f"\nForecaster_{idx + 1} outside view ERROR: {result}")
                outside_view_outputs[idx] = f"{_FAILED_OUTPUT_PREFIX}{result}"
                outside_view_metrics.error = str(result)
                outside_view_metrics.duration_seconds = duration
                self.pipeline_warnings.append(
                    f"forecaster_{idx + 1} outside view failed ({agents[idx]['model']}): {result}"
                )
            else:
                output, response_metadata = result
                reasoning_tokens = response_metadata.get("reasoning_tokens", 0)
                reasoning_label = (
                    f" [reasoning: {reasoning_tokens} tokens]" if reasoning_tokens else ""
                )
                log(
                    f"\nForecaster_{idx + 1} outside view output"
                    f"{reasoning_label}:\n{output[:300]}..."
                )
                outside_view_outputs[idx] = output

                outside_view_metrics.token_input = response_metadata.get("input_tokens", 0)
                outside_view_metrics.token_output = response_metadata.get("output_tokens", 0)
                outside_view_metrics.token_reasoning = reasoning_tokens
                outside_view_metrics.used_reasoning = response_metadata.get("used_reasoning", False)
                outside_view_metrics.cost = response_metadata.get("cost", 0.0)
                outside_view_metrics.duration_seconds = duration

                reasoning_content = response_metadata.get("reasoning_content")
                if reasoning_content:
                    outside_view_reasoning[idx] = reasoning_content

        # Assign reused outside views for forecasters 2 and 4
        reuse_mapping = {1: 4, 3: 2}
        for idx, source_idx in reuse_mapping.items():
            agent_id = f"forecaster_{idx + 1}"
            outside_view_metrics = metrics.agents[agent_id].step1

            source_output = outside_view_outputs[source_idx]
            if not source_output:
                msg = (
                    f"forecaster_{idx + 1} outside view reused from "
                    f"forecaster_{source_idx + 1}, but source output is empty"
                )
                log(f"\n{msg}")
                self.pipeline_warnings.append(msg)
                outside_view_outputs[idx] = f"{_FAILED_OUTPUT_PREFIX}{msg}"
                outside_view_metrics.error = msg
                outside_view_metrics.duration_seconds = 0.0
            else:
                outside_view_outputs[idx] = source_output

        return OutsideViewResult(
            outputs=outside_view_outputs,
            reasoning=outside_view_reasoning,
            prompt=outside_view_prompt,
        )

    def _cross_pollinate(
        self,
        outside_view_outputs: list[str],
        current_context: str,
    ) -> CrossPollinatedContext:
        """
        Step 4: Assemble cross-pollinated context for inside view.

        Each forecaster receives current_context combined with another forecaster's
        outside view output, per the CROSS_POLLINATION_MAP. Failed outputs trigger
        fallback to self or the first valid output.

        Args:
            outside_view_outputs: List of 5 outside view outputs (may contain failed sentinels)
            current_context: Current news/search context

        Returns:
            CrossPollinatedContext mapping each forecaster index to its enriched context
        """
        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            source_output = outside_view_outputs[source_idx]

            if _is_failed_output(source_output):
                fallback_idx = None
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
                        f"forecaster {i + 1} will receive forecaster "
                        f"{fallback_idx + 1}'s output instead"
                    )
                else:
                    logger.warning(
                        f"Cross-pollination source forecaster {source_idx + 1} failed; "
                        f"no valid outside views available; "
                        f"forecaster {i + 1} will receive empty context"
                    )
                    source_output = ""

            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        return CrossPollinatedContext(context_map=context_map)

    async def _run_inside_view(
        self,
        agents: list[dict],
        context_map: dict[int, str],
        prompt_inside_view: str,
        forecast_temp: float,
        question_params: dict,
        metrics: PipelineMetrics,
        log: Callable[[str], Any] = print,
    ) -> InsideViewResult:
        """
        Step 5: Run inside view prediction with all 5 forecasters.

        Each forecaster receives its cross-pollinated context (current context +
        another forecaster's outside view output).

        Args:
            agents: List of 5 agent config dicts
            context_map: Cross-pollinated context per forecaster (from _cross_pollinate)
            prompt_inside_view: Inside view prompt template
            forecast_temp: Temperature for forecasting LLM calls
            question_params: Question parameters for prompt formatting
            metrics: PipelineMetrics to populate with agent step2 data
            log: Progress logging callback

        Returns:
            InsideViewResult with 5 outputs and reasoning content
        """
        log("\n=== Step 5: Running inside view prediction ===")

        inside_view_tasks = []
        inside_view_timings = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = SUPERFORECASTER_CONTEXT

            inside_view_prompt = self._format_inside_view_prompt(
                prompt_inside_view, context_map[i], **question_params
            )

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
        inside_view_outputs: list[Any] = []
        inside_view_reasoning: dict[int, str] = {}

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

                reasoning_tokens = response_metadata.get("reasoning_tokens", 0)
                inside_view_metrics.token_input = response_metadata.get("input_tokens", 0)
                inside_view_metrics.token_output = response_metadata.get("output_tokens", 0)
                inside_view_metrics.token_reasoning = reasoning_tokens
                inside_view_metrics.used_reasoning = response_metadata.get("used_reasoning", False)
                inside_view_metrics.cost = response_metadata.get("cost", 0.0)
                inside_view_metrics.duration_seconds = duration

                reasoning_content = response_metadata.get("reasoning_content")
                if reasoning_content:
                    inside_view_reasoning[i] = reasoning_content

        return InsideViewResult(
            outputs=inside_view_outputs,
            reasoning=inside_view_reasoning,
        )

    def _extract_and_aggregate(
        self,
        agents: list[dict],
        outside_view_outputs: list[str],
        inside_view_result: InsideViewResult,
        question_params: dict,
        log: Callable[[str], Any] = print,
    ) -> EnsembleResult:
        """
        Step 6: Extract predictions from inside view outputs and aggregate.

        For each forecaster, extracts the type-specific prediction from its inside
        view output, then aggregates all valid predictions into a final prediction.

        Args:
            agents: List of 5 agent config dicts
            outside_view_outputs: Outside view outputs (for building AgentResults)
            inside_view_result: Inside view outputs from _run_inside_view
            question_params: Question parameters for extraction
            log: Progress logging callback

        Returns:
            EnsembleResult with per-forecaster AgentResults and final_prediction
        """
        log("\n=== Step 6: Extracting and aggregating predictions ===")

        agent_results = []

        for i, (agent, output) in enumerate(zip(agents, inside_view_result.outputs, strict=True)):
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

        final_prediction = self._aggregate_results(agent_results, agents, log)

        return EnsembleResult(
            agent_results=agent_results,
            final_prediction=final_prediction,
        )

    def _log_cost_breakdown(
        self,
        metrics: PipelineMetrics,
        step_costs: dict[str, float],
        log: Callable[[str], Any],
    ) -> None:
        """Log the cost breakdown for the pipeline run."""
        log("\n=== Cost Breakdown ===")
        for step_name, cost in step_costs.items():
            log(f"  {step_name}: ${cost:.4f}")

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

        log("  Agent costs:")
        for agent_id, agent_metrics in metrics.agents.items():
            s1 = agent_metrics.step1
            s2 = agent_metrics.step2
            reasoning_parts = []
            if s1.used_reasoning:
                reasoning_parts.append(f"S1={s1.token_reasoning}tok")
            if s2.used_reasoning:
                reasoning_parts.append(f"S2={s2.token_reasoning}tok")
            reasoning_info = f" reasoning[{', '.join(reasoning_parts)}]" if reasoning_parts else ""
            log(
                f"    {agent_id} ({agent_metrics.model}): "
                f"S1=${s1.cost:.4f} S2=${s2.cost:.4f}{reasoning_info}"
            )

        log(f"  TOTAL: ${metrics.total_pipeline_cost:.4f}")

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

    def _get_bounds_info(self, question_params: dict) -> str | None:
        """Compute bounds_info string for numeric questions.

        Returns None for non-numeric types. For numeric, uses the same
        static method as NumericForecaster so the supervisor sees identical
        bounds context.
        """
        if self.question_type != "numeric":
            return None

        from .numeric import NumericForecaster

        return NumericForecaster._get_bounds_explanation(**question_params)["bounds_info"]

    def _get_forecaster_prediction_value(self, result: AgentResult) -> Any:
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

    def _convert_supervisor_prediction(self, prediction: Any, question_params: dict) -> Any:
        """Convert supervisor prediction to the format expected by the pipeline.

        For binary and multiple choice, the supervisor output matches the pipeline
        format directly. Numeric subclass overrides this to convert percentiles → CDF.
        """
        return prediction

    async def _run_supervisor(
        self,
        agent_results: list[AgentResult],
        agents: list[dict],
        final_prediction: Any,
        question_params: dict,
        seed_context: str = "",
        log: Callable[[str], Any] = print,
    ) -> Any:
        """
        Run supervisor review if ensemble divergence exceeds threshold.

        Returns the (possibly updated) final_prediction.
        """
        # Compute divergence
        divergence = compute_divergence(
            question_type=self.question_type,
            agent_results=agent_results,
            config=self.config,
            range_min=question_params.get("lower_bound"),
            range_max=question_params.get("upper_bound"),
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
            pred = self._get_forecaster_prediction_value(result)
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
            pre_research_context=seed_context,
            options=question_params.get("options"),
            num_options=len(question_params.get("options", []) or []) or None,
            units=question_params.get("unit_of_measure"),
            bounds_info=self._get_bounds_info(question_params),
            is_date_question=question_params.get("is_date_question", False),
            stock_return_context=question_params.get("stock_return_context"),
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

            # Convert supervisor prediction to the format expected by the pipeline
            # (e.g., for numeric questions, convert percentiles dict → CDF list)
            converted = self._convert_supervisor_prediction(
                result.updated_prediction, question_params
            )

            log(f"  Using supervisor prediction: {result.updated_prediction}")
            return converted

        except Exception as e:
            logger.error(f"Supervisor failed: {e}")
            log(f"  Supervisor error: {e}")
            log("  Falling back to weighted average")
            self.pipeline_warnings.append(f"supervisor failed: {e}")
            return final_prediction
