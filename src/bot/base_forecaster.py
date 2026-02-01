"""
Base forecaster class implementing the shared 5-agent ensemble pipeline.

This module provides the common pipeline structure used by all question type handlers:
1. Generate search queries (historical + current)
2. Execute searches
3. Run Step 1 (outside view) with 5 agents
4. Cross-pollinate context between agents
5. Run Step 2 (inside view) with 5 agents
6. Extract predictions and aggregate

Subclasses implement type-specific logic by overriding abstract methods.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..utils.llm import LLMClient, get_cost_tracker
from ..storage.artifact_store import ArtifactStore
from .handler_mixin import ForecasterMixin
from .extractors import AgentResult
from .search import SearchPipeline, QuestionDetails
from .prompts import CLAUDE_CONTEXT, GPT_CONTEXT

logger = logging.getLogger(__name__)


# Cross-pollination map
# Maps agent index -> source agent index for step 1 output
# Creates cross-model diversity: Sonnet 4.5 -> o3-mini-high -> o3 -> Sonnet 4.5
CROSS_POLLINATION_MAP = {
    0: (0, "Outside view prediction"),  # Agent 1 <- Agent 1 (Sonnet 4.5 <- Sonnet 4.5)
    1: (3, "Outside view prediction"),  # Agent 2 <- Agent 4 (Sonnet 4.5 <- o3)
    2: (1, "Outside view prediction"),  # Agent 3 <- Agent 2 (o3-mini-high <- Sonnet 4.5)
    3: (2, "Outside view prediction"),  # Agent 4 <- Agent 3 (o3 <- o3-mini-high)
    4: (4, "Outside view prediction"),  # Agent 5 <- Agent 5 (o3 <- o3)
}


class BaseForecaster(ForecasterMixin, ABC):
    """
    Abstract base class for all question type forecasters.

    Implements the shared 6-step ensemble pipeline. Subclasses must implement:
    - _get_prompt_templates(): Return the 4 prompt templates for this question type
    - _get_question_details(): Build QuestionDetails from question parameters
    - _format_step1_prompt(): Format the Step 1 (outside view) prompt
    - _format_step2_prompt(): Format the Step 2 (inside view) prompt for each agent
    - _extract_prediction(): Extract type-specific prediction from agent output
    - _aggregate_results(): Aggregate predictions into final result
    - _build_result(): Build the final result object
    """

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        artifact_store: Optional[ArtifactStore] = None,
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

    async def forecast(
        self,
        write: callable = print,
        **question_params,
    ) -> Any:
        """
        Run the full forecasting pipeline.

        Args:
            write: Logging function (default: print)
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
        prompt_historical, prompt_current, prompt_step1, prompt_step2 = self._get_prompt_templates()

        # =========================================================================
        # STEP 1: Generate historical and current search queries
        # =========================================================================
        write("\n=== Step 1: Generating search queries ===")

        historical_prompt, current_prompt = self._format_query_prompts(
            prompt_historical, prompt_current, **question_params
        )

        query_model = self._get_model("query_generator", "openrouter/openai/o3")

        historical_task = self._call_model(query_model, historical_prompt)
        current_task = self._call_model(query_model, current_prompt)
        historical_output, current_output = await asyncio.gather(historical_task, current_task)

        write(f"\nHistorical query output:\n{historical_output[:500]}...")
        write(f"\nCurrent query output:\n{current_output[:500]}...")

        step1_end_cost = snapshot_cost("step1_query_generation", pipeline_start_cost)

        if self.artifact_store:
            self.artifact_store.save_query_generation("historical", historical_prompt, historical_output)
            self.artifact_store.save_query_generation("current", current_prompt, current_output)

        # =========================================================================
        # STEP 2: Execute searches
        # =========================================================================
        write("\n=== Step 2: Executing searches ===")

        # Initialize tool usage tracking
        tool_usage = {
            "centralized_research": {
                "historical": {},
                "current": {},
            },
            "agents": {},
        }

        async with SearchPipeline(self.config, self.llm) as search:
            results = await asyncio.gather(
                search.process_search_queries(
                    historical_output,
                    forecaster_id="-1",
                    question_details=question_details,
                    include_asknews=False,
                ),
                search.process_search_queries(
                    current_output,
                    forecaster_id="0",
                    question_details=question_details,
                    include_asknews=True,
                ),
            )
            (historical_context, historical_metadata), (current_context, current_metadata) = results

        write(f"\nHistorical context ({len(historical_context)} chars)")
        write(f"Current context ({len(current_context)} chars)")

        step2_end_cost = snapshot_cost("step2_search", step1_end_cost)

        # Store metadata
        tool_usage["centralized_research"]["historical"] = historical_metadata
        tool_usage["centralized_research"]["current"] = current_metadata

        if self.artifact_store:
            self.artifact_store.save_search_results("historical", {"context": historical_context})
            self.artifact_store.save_search_results("current", {"context": current_context})

        # =========================================================================
        # STEP 3: Run 5 agents on Step 1 (outside view)
        # =========================================================================
        write("\n=== Step 3: Running Step 1 (outside view) ===")

        agents = self._get_agents()

        # Initialize agent tracking
        for i, agent in enumerate(agents):
            agent_name = f"forecaster_{i+1}"
            tool_usage["agents"][agent_name] = {
                "model": agent["model"],
                "weight": agent["weight"],
                "step1": {"searched": False, "queries": []},
                "step2": {"searched": False, "queries": []},
            }

        step1_prompt = self._format_step1_prompt(
            prompt_step1, historical_context, **question_params
        )

        step1_tasks = []
        step1_timings = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT

            # Record start time for this agent
            start_time = time.time()
            step1_timings.append(start_time)

            step1_tasks.append(
                self._call_model_with_metadata(model, step1_prompt, system_prompt=system_prompt)
            )

        step1_results = await asyncio.gather(*step1_tasks, return_exceptions=True)
        step1_outputs = []

        for i, result in enumerate(step1_results):
            agent_name = f"forecaster_{i+1}"
            duration = time.time() - step1_timings[i]

            if isinstance(result, Exception):
                write(f"\nForecaster_{i+1} step 1 ERROR: {result}")
                step1_outputs.append(f"Error: {result}")
                tool_usage["agents"][agent_name]["step1"]["error"] = str(result)
                tool_usage["agents"][agent_name]["step1"]["duration_seconds"] = duration
            else:
                output, response_metadata = result
                write(f"\nForecaster_{i+1} step 1 output:\n{output[:300]}...")
                step1_outputs.append(output)

                # Track LLM metrics
                tool_usage["agents"][agent_name]["step1"].update({
                    "token_input": response_metadata.get("input_tokens", 0),
                    "token_output": response_metadata.get("output_tokens", 0),
                    "cost": response_metadata.get("cost", 0.0),
                    "duration_seconds": duration,
                })

        if self.artifact_store:
            self.artifact_store.save_step1_prompt(step1_prompt)
            for i, output in enumerate(step1_outputs):
                if not isinstance(output, Exception) and not output.startswith("Error:"):
                    self.artifact_store.save_agent_step1(i + 1, output)

        step3_end_cost = snapshot_cost("step3_outside_view", step2_end_cost)

        # =========================================================================
        # STEP 4: Cross-pollinate context
        # =========================================================================
        write("\n=== Step 4: Cross-pollinating context ===")

        context_map = {}
        for i in range(5):
            source_idx, label = CROSS_POLLINATION_MAP[i]
            if isinstance(step1_outputs[source_idx], Exception):
                logger.warning(
                    f"Cross-pollination source agent {source_idx + 1} failed; "
                    f"agent {i + 1} will receive empty context"
                )
                source_output = ""
            else:
                source_output = step1_outputs[source_idx]
            context_map[i] = f"Current context: {current_context}\n{label}: {source_output}"

        # =========================================================================
        # STEP 5: Run 5 agents on Step 2 (inside view)
        # =========================================================================
        write("\n=== Step 5: Running Step 2 (inside view) ===")

        step2_tasks = []
        step2_timings = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT

            step2_prompt = self._format_step2_prompt(
                prompt_step2, context_map[i], **question_params
            )

            # Record start time for this agent
            start_time = time.time()
            step2_timings.append(start_time)

            step2_tasks.append(
                self._call_model_with_metadata(model, step2_prompt, system_prompt=system_prompt)
            )

        step2_results = await asyncio.gather(*step2_tasks, return_exceptions=True)
        step2_outputs = []

        for i, result in enumerate(step2_results):
            agent_name = f"forecaster_{i+1}"
            duration = time.time() - step2_timings[i]

            if isinstance(result, Exception):
                step2_outputs.append(result)
                tool_usage["agents"][agent_name]["step2"]["error"] = str(result)
                tool_usage["agents"][agent_name]["step2"]["duration_seconds"] = duration
            else:
                output, response_metadata = result
                step2_outputs.append(output)

                # Track LLM metrics
                tool_usage["agents"][agent_name]["step2"].update({
                    "token_input": response_metadata.get("input_tokens", 0),
                    "token_output": response_metadata.get("output_tokens", 0),
                    "cost": response_metadata.get("cost", 0.0),
                    "duration_seconds": duration,
                })

        step5_end_cost = snapshot_cost("step5_inside_view", step3_end_cost)

        # =========================================================================
        # STEP 6: Extract predictions and aggregate
        # =========================================================================
        write("\n=== Step 6: Extracting and aggregating predictions ===")

        agent_results = []

        for i, (agent, output) in enumerate(zip(agents, step2_outputs)):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i+1} step 2 ERROR: {output}")
                prediction = None
                error = str(output)
            else:
                write(f"\nForecaster_{i+1} step 2 output:\n{output[:300]}...")
                try:
                    prediction = self._extract_prediction(output, **question_params)
                    write(f"Forecaster_{i+1} prediction: {prediction}")
                    error = None
                except Exception as e:
                    write(f"Forecaster_{i+1} extraction error: {e}")
                    prediction = None
                    error = str(e)

            agent_result = self._build_agent_result(
                agent_id=f"forecaster_{i+1}",
                model=agent["model"],
                weight=agent["weight"],
                step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                step2_output=output if not isinstance(output, Exception) else "",
                prediction=prediction,
                error=error,
            )
            agent_results.append(agent_result)

        # Save step 2 artifacts
        if self.artifact_store:
            for i, result in enumerate(agent_results):
                if result.step2_output:
                    self.artifact_store.save_agent_step2(i + 1, result.step2_output)
                self.artifact_store.save_agent_extracted(i + 1, self._get_extracted_data(result))

        # Aggregate results
        final_prediction = self._aggregate_results(agent_results, agents, write)

        # Save aggregation
        if self.artifact_store:
            self.artifact_store.save_aggregation(
                self._get_aggregation_data(agent_results, agents, final_prediction)
            )
            # Save tool usage tracking with step costs
            tool_usage["step_costs"] = step_costs
            tool_usage["total_pipeline_cost"] = round(cost_tracker.total_cost - pipeline_start_cost, 4)
            self.artifact_store.save_tool_usage(tool_usage)

        # Log cost breakdown
        write("\n=== Cost Breakdown ===")
        for step_name, cost in step_costs.items():
            write(f"  {step_name}: ${cost:.4f}")

        # Show search cost breakdown
        search_hist = tool_usage["centralized_research"]["historical"]
        search_curr = tool_usage["centralized_research"]["current"]
        if search_hist.get("llm_cost") or search_curr.get("llm_cost"):
            write("    Search LLM breakdown:")
            if search_hist.get("llm_cost_summarization"):
                write(f"      historical summarization: ${search_hist['llm_cost_summarization']:.4f}")
            if search_hist.get("llm_cost_agentic"):
                write(f"      historical agentic: ${search_hist['llm_cost_agentic']:.4f}")
            if search_curr.get("llm_cost_summarization"):
                write(f"      current summarization: ${search_curr['llm_cost_summarization']:.4f}")
            if search_curr.get("llm_cost_agentic"):
                write(f"      current agentic: ${search_curr['llm_cost_agentic']:.4f}")

        # Show agent costs
        write("  Agent costs:")
        for agent_name, agent_data in tool_usage["agents"].items():
            s1_cost = agent_data.get("step1", {}).get("cost", 0)
            s2_cost = agent_data.get("step2", {}).get("cost", 0)
            write(f"    {agent_name}: S1=${s1_cost:.4f} S2=${s2_cost:.4f}")

        write(f"  TOTAL: ${tool_usage['total_pipeline_cost']:.4f}")

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
    ) -> Tuple[str, str]:
        """
        Format query generation prompts with question parameters.

        Default implementation uses common fields. Override for custom formatting.
        """
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
    def _get_prompt_templates(self) -> Tuple[str, str, str, str]:
        """
        Return the 4 prompt templates for this question type.

        Returns:
            Tuple of (prompt_historical, prompt_current, prompt_step1, prompt_step2)
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
    def _format_step1_prompt(
        self,
        prompt_template: str,
        historical_context: str,
        **question_params,
    ) -> str:
        """
        Format the Step 1 (outside view) prompt.

        Args:
            prompt_template: The step 1 prompt template
            historical_context: Search results for historical context
            **question_params: Question-specific parameters

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def _format_step2_prompt(
        self,
        prompt_template: str,
        context: str,
        **question_params,
    ) -> str:
        """
        Format the Step 2 (inside view) prompt for a single agent.

        Args:
            prompt_template: The step 2 prompt template
            context: Cross-pollinated context (current context + step 1 output)
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
        agent_results: List[AgentResult],
        agents: List[Dict],
        write: callable,
    ) -> Any:
        """
        Aggregate individual predictions into final result.

        Args:
            agent_results: List of AgentResult with predictions
            agents: Agent configurations with weights
            write: Logging function

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
        step1_output: str,
        step2_output: str,
        prediction: Any,
        error: Optional[str],
    ) -> AgentResult:
        """
        Build an AgentResult with type-specific prediction field.

        Args:
            agent_id: Agent identifier
            model: Model name
            weight: Agent weight
            step1_output: Step 1 output
            step2_output: Step 2 output
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
        agent_results: List[AgentResult],
        historical_context: str,
        current_context: str,
        agents: List[Dict],
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

    def _get_extracted_data(self, result: AgentResult) -> Dict:
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
        agent_results: List[AgentResult],
        agents: List[Dict],
        final_prediction: Any,
    ) -> Dict:
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
