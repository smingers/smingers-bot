"""
Supervisor Agent

Reviews ensemble forecaster disagreements, conducts targeted research to
resolve factual disputes, and produces an updated forecast.
Based on the AIA Forecaster paper (arxiv 2511.07678v1).

The supervisor operates in two stages:
1. Analyze disagreements and generate search queries
2. After research, produce an updated forecast with confidence level
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.bot.exceptions import ExtractionError
from src.bot.extractors import (
    extract_binary_probability_percent,
    extract_date_percentiles_from_response,
    extract_multiple_choice_probabilities,
    extract_percentiles_from_response,
    normalize_probabilities,
)
from src.bot.prompts import (
    BINARY_SUPERVISOR_UPDATE_PROMPT,
    MULTIPLE_CHOICE_SUPERVISOR_UPDATE_PROMPT,
    NUMERIC_SUPERVISOR_UPDATE_PROMPT,
    SUPERVISOR_ANALYSIS_PROMPT,
)
from src.bot.search import QuestionDetails, SearchPipeline
from src.utils.llm import LLMClient, get_cost_tracker

logger = logging.getLogger(__name__)


@dataclass
class SupervisorInput:
    """All data needed by the supervisor agent."""

    question_title: str
    question_type: str  # "binary", "numeric", "multiple_choice"
    resolution_criteria: str
    fine_print: str
    background: str
    open_time: str
    scheduled_resolve_time: str
    today: str

    # Per-forecaster data: list of dicts with agent_id, model, prediction, reasoning
    forecaster_predictions: list[dict]

    # The current aggregated result (probability for binary, etc.)
    weighted_average_prediction: Any

    # Pre-research: scraped/summarized content from links in the question (e.g. resolution URL).
    # Treat as primary-source evidence for "current state" when the question resolves from that source.
    pre_research_context: str = ""

    # Optional type-specific fields
    options: list[str] | None = None  # Multiple choice options
    units: str | None = None  # Numeric units
    is_date_question: bool = False  # Whether this is a date question
    bounds_info: str | None = None  # Numeric bounds
    num_options: int | None = None  # Number of MC options
    stock_return_context: str | None = None  # Programmatic stock return distribution


@dataclass
class SupervisorResult:
    """Output from the supervisor agent."""

    confidence: str  # "high", "medium", "low"
    updated_prediction: Any  # Same type as weighted_average_prediction
    reasoning: str  # Full supervisor reasoning trace (stage 2 output)
    search_queries: list[str]  # Queries the supervisor generated
    search_context: str  # Research results obtained
    disagreement_analysis: str  # Stage 1 analysis output
    cost: float = 0.0  # Total LLM + search cost for supervisor
    error: str | None = None


class SupervisorAgent:
    """
    Supervisor agent that reviews ensemble disagreements and overrides with
    a research-informed forecast.

    Follows the AIA Forecaster paper:
    1. Receives all 5 forecasters' reasoning + predictions
    2. Identifies disagreements and their root causes
    3. Generates targeted search queries to resolve disagreements
    4. Conducts research using those queries
    5. Produces updated forecast that replaces the weighted average
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
    ):
        self.config = config
        self.llm = llm_client or LLMClient()

        # Resolve supervisor model
        supervisor_config = config.get("supervisor", {})
        model_config = supervisor_config.get("model", {})
        active_models = config.get("active_models", {})

        # Use active_models.supervisor if set (mode-resolved), else model.quality
        self.model = active_models.get(
            "supervisor",
            model_config.get("quality", "openrouter/anthropic/claude-opus-4.6"),
        )
        self.temperature = supervisor_config.get("temperature", 0.3)
        self.max_search_queries = supervisor_config.get("max_search_queries", 4)

        # LLM settings
        llm_config = config.get("llm", {})
        self.max_tokens = llm_config.get("max_output_tokens", 5000)

    async def evaluate(self, supervisor_input: SupervisorInput) -> SupervisorResult:
        """
        Run the full supervisor pipeline.

        Args:
            supervisor_input: All data needed for the supervisor evaluation.

        Returns:
            SupervisorResult with confidence, updated prediction, and reasoning.
        """
        cost_tracker = get_cost_tracker()
        start_cost = cost_tracker.total_cost

        try:
            # Stage 1: Analyze disagreements and generate search queries
            analysis, search_queries = await self._stage1_analyze_disagreements(supervisor_input)

            # Stage 2: Conduct targeted research (if queries were generated)
            search_context = ""
            if search_queries:
                search_context = await self._execute_searches(supervisor_input, search_queries)

            # Stage 3: Produce updated forecast with confidence
            result = await self._stage2_research_and_update(
                supervisor_input, analysis, search_context
            )

            result.cost = round(cost_tracker.total_cost - start_cost, 4)
            return result

        except Exception as e:
            logger.error(f"Supervisor evaluation failed: {e}")
            cost = round(cost_tracker.total_cost - start_cost, 4)
            return SupervisorResult(
                confidence="low",
                updated_prediction=supervisor_input.weighted_average_prediction,
                reasoning="",
                search_queries=[],
                search_context="",
                disagreement_analysis="",
                cost=cost,
                error=str(e),
            )

    async def _stage1_analyze_disagreements(
        self, supervisor_input: SupervisorInput
    ) -> tuple[str, list[str]]:
        """
        Analyze forecaster outputs, identify disagreements, generate search queries.

        Returns:
            Tuple of (analysis_text, search_queries).
        """
        forecaster_summaries = self._format_forecaster_summaries(supervisor_input)
        weighted_avg_display = self._format_weighted_average(supervisor_input)
        type_section = self._format_type_specific_section(supervisor_input)
        pre_research_section = self._format_pre_research_section(supervisor_input)

        prompt = SUPERVISOR_ANALYSIS_PROMPT.format(
            title=supervisor_input.question_title,
            background=supervisor_input.background,
            resolution_criteria=supervisor_input.resolution_criteria,
            fine_print=supervisor_input.fine_print,
            open_time=supervisor_input.open_time,
            scheduled_resolve_time=supervisor_input.scheduled_resolve_time,
            today=supervisor_input.today,
            type_specific_section=type_section,
            pre_research_section=pre_research_section,
            forecaster_summaries=forecaster_summaries,
            weighted_average_display=weighted_avg_display,
        )

        messages = [{"role": "user", "content": prompt}]
        response = await self.llm.complete(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        analysis_text = response.content

        # Extract search queries from the analysis
        search_queries = self._extract_search_queries(analysis_text)

        return analysis_text, search_queries

    async def _execute_searches(
        self,
        supervisor_input: SupervisorInput,
        search_queries: list[str],
    ) -> str:
        """
        Execute targeted searches using the search pipeline.

        Args:
            supervisor_input: Question context for search.
            search_queries: List of query strings with source tags.

        Returns:
            Formatted search results string.
        """
        # Build a formatted response that the SearchPipeline can parse
        queries_block = "Search queries:\n"
        for i, q in enumerate(search_queries, 1):
            queries_block += f"{i}. {q}\n"

        question_details = QuestionDetails(
            title=supervisor_input.question_title,
            resolution_criteria=supervisor_input.resolution_criteria,
            fine_print=supervisor_input.fine_print,
            description=supervisor_input.background,
        )

        async with SearchPipeline(self.config, self.llm) as search:
            results_str, _metadata = await search.execute_searches_from_response(
                response=queries_block,
                search_id="supervisor",
                question_details=question_details,
                include_asknews=False,
            )

        return results_str

    async def _stage2_research_and_update(
        self,
        supervisor_input: SupervisorInput,
        analysis: str,
        search_context: str,
    ) -> SupervisorResult:
        """
        Given disagreement analysis and research results, produce updated forecast.

        Returns:
            SupervisorResult with confidence, prediction, and reasoning.
        """
        forecaster_summaries = self._format_forecaster_summaries(supervisor_input)
        weighted_avg_display = self._format_weighted_average(supervisor_input)

        # Select type-specific update prompt
        prompt_template = self._get_update_prompt_template(supervisor_input.question_type)

        format_kwargs = {
            "title": supervisor_input.question_title,
            "background": supervisor_input.background,
            "resolution_criteria": supervisor_input.resolution_criteria,
            "fine_print": supervisor_input.fine_print,
            "open_time": supervisor_input.open_time,
            "scheduled_resolve_time": supervisor_input.scheduled_resolve_time,
            "today": supervisor_input.today,
            "forecaster_summaries": forecaster_summaries,
            "disagreement_analysis": analysis,
            "research_results": search_context or "(No targeted research conducted)",
            "weighted_average_display": weighted_avg_display,
            "pre_research_section": self._format_pre_research_section(supervisor_input),
        }

        # Add type-specific fields
        if supervisor_input.question_type == "numeric":
            format_kwargs["type_specific_section"] = self._format_type_specific_section(
                supervisor_input
            )
        elif supervisor_input.question_type == "multiple_choice":
            format_kwargs["options"] = ", ".join(supervisor_input.options or [])

        prompt = prompt_template.format(**format_kwargs)

        messages = [{"role": "user", "content": prompt}]
        response = await self.llm.complete(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        update_text = response.content

        # Extract confidence level
        confidence = self._extract_confidence(update_text)

        # Extract updated prediction
        search_queries = self._extract_search_queries(analysis)
        try:
            prediction = self._extract_prediction(update_text, supervisor_input)
        except (ExtractionError, Exception) as e:
            logger.warning(f"Supervisor prediction extraction failed: {e}")
            prediction = supervisor_input.weighted_average_prediction
            confidence = "low"

        return SupervisorResult(
            confidence=confidence,
            updated_prediction=prediction,
            reasoning=update_text,
            search_queries=search_queries,
            search_context=search_context,
            disagreement_analysis=analysis,
        )

    # -------------------------------------------------------------------------
    # Formatting helpers
    # -------------------------------------------------------------------------

    def _format_forecaster_summaries(self, supervisor_input: SupervisorInput) -> str:
        """Format all forecasters' predictions and reasoning for the prompt."""
        parts = []
        for fp in supervisor_input.forecaster_predictions:
            agent_id = fp.get("agent_id", "unknown")
            model = fp.get("model", "unknown")
            prediction = fp.get("prediction")
            reasoning = fp.get("reasoning", "")

            pred_display = self._format_single_prediction(
                prediction, supervisor_input.question_type
            )

            parts.append(
                f"--- {agent_id} ({model}) ---\n"
                f"Prediction: {pred_display}\n\n"
                f"Reasoning:\n{reasoning}\n"
            )

        return "\n".join(parts)

    def _format_single_prediction(self, prediction: Any, question_type: str) -> str:
        """Format a single prediction value for display."""
        if prediction is None:
            return "(extraction failed)"

        if question_type == "binary":
            return f"{prediction:.1f}%"
        elif question_type == "numeric":
            if isinstance(prediction, dict):
                items = sorted(prediction.items())
                return ", ".join(f"P{k}: {v}" for k, v in items)
            return str(prediction)
        elif question_type == "multiple_choice":
            if isinstance(prediction, list):
                return str([f"{p * 100:.1f}%" for p in prediction])
            return str(prediction)
        return str(prediction)

    def _format_weighted_average(self, supervisor_input: SupervisorInput) -> str:
        """Format the current weighted average for display."""
        wa = supervisor_input.weighted_average_prediction
        qt = supervisor_input.question_type

        if qt == "binary":
            if isinstance(wa, float) and wa <= 1.0:
                return f"{wa * 100:.1f}%"
            return f"{wa}%"
        elif qt == "numeric":
            return str(wa)
        elif qt == "multiple_choice":
            if isinstance(wa, list):
                # MC probabilities are 0-1 normalized
                return str([f"{p * 100:.1f}%" for p in wa])
            return str(wa)
        return str(wa)

    def _format_pre_research_section(self, supervisor_input: SupervisorInput) -> str:
        """Format pre-research (question URL scrape) for supervisor prompts."""
        pre = (supervisor_input.pre_research_context or "").strip()
        if not pre:
            return (
                "=== PRE-RESEARCH (primary source) ===\n"
                "(No pre-research context — no links were scraped from the question fields.)"
            )
        return (
            "=== PRE-RESEARCH (primary source) ===\n"
            "The following was scraped and summarized from links in the question (e.g. resolution URL). "
            "Treat it as the primary-source snapshot for 'current state' when the question resolves from that source. "
            "Do not override it with third-party or search results unless they explicitly update or supersede it.\n\n"
            f"{pre}"
        )

    def _format_type_specific_section(self, supervisor_input: SupervisorInput) -> str:
        """Format type-specific context for prompts."""
        parts = []

        if supervisor_input.question_type == "numeric":
            if supervisor_input.units:
                parts.append(f"Units: {supervisor_input.units}")
            if supervisor_input.bounds_info:
                parts.append(f"Bounds: {supervisor_input.bounds_info}")
        elif supervisor_input.question_type == "multiple_choice":
            if supervisor_input.options:
                parts.append(f"Options: {', '.join(supervisor_input.options)}")

        # Stock return context applies to any type (typically binary)
        if supervisor_input.stock_return_context:
            parts.append(supervisor_input.stock_return_context)

        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # Extraction helpers
    # -------------------------------------------------------------------------

    def _extract_search_queries(self, text: str) -> list[str]:
        """Extract search queries from supervisor analysis output."""
        block = re.search(r"(?:Search queries:)(.*)", text, re.DOTALL | re.IGNORECASE)
        if not block:
            return []

        queries_text = block.group(1).strip()

        # Parse queries with sources (same format as SearchPipeline)
        queries = re.findall(
            r"(?:\d+\.\s*)?(.+?)\s*[\(\[](Google|Google News|Agent)[\)\]]",
            queries_text,
        )

        result = []
        for match in queries:
            query = match[0].strip().strip("\"'")
            source = match[1]
            result.append(f"{query} ({source})")
            if len(result) >= self.max_search_queries:
                break

        return result

    def _extract_confidence(self, text: str) -> str:
        """Extract confidence level from supervisor update output."""
        # Look for "Confidence: HIGH/MEDIUM/LOW"
        match = re.search(r"Confidence:\s*(HIGH|MEDIUM|LOW)", text, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return "low"  # Default to low if not found

    def _extract_prediction(self, text: str, supervisor_input: SupervisorInput) -> Any:
        """Extract prediction from supervisor update output using existing extractors."""
        qt = supervisor_input.question_type

        if qt == "binary":
            pct = extract_binary_probability_percent(text)
            return max(0.001, min(0.999, pct / 100))
        elif qt == "numeric":
            if supervisor_input.is_date_question:
                return extract_date_percentiles_from_response(text, verbose=False)
            return extract_percentiles_from_response(text, verbose=False)
        elif qt == "multiple_choice":
            num_options = supervisor_input.num_options or len(supervisor_input.options or [])
            probs = extract_multiple_choice_probabilities(text, num_options)
            return normalize_probabilities(probs)
        else:
            raise ValueError(f"Unknown question type: {qt}")

    def _get_update_prompt_template(self, question_type: str) -> str:
        """Get the appropriate update prompt template for the question type."""
        if question_type == "binary":
            return BINARY_SUPERVISOR_UPDATE_PROMPT
        elif question_type == "numeric":
            return NUMERIC_SUPERVISOR_UPDATE_PROMPT
        elif question_type == "multiple_choice":
            return MULTIPLE_CHOICE_SUPERVISOR_UPDATE_PROMPT
        else:
            # Default to binary format
            return BINARY_SUPERVISOR_UPDATE_PROMPT
