"""
Metaculus source implementation.

Wraps the existing Metaculus forecasting infrastructure to conform to the
ForecastSource protocol. This is a thin adapter layer that delegates to
the existing handlers (binary.py, numeric.py, multiple_choice.py).
"""

import logging
from typing import Any

from ...bot.binary import BinaryForecaster
from ...bot.multiple_choice import MultipleChoiceForecaster
from ...bot.numeric import NumericForecaster
from ...bot.prompts import (
    BINARY_INSIDE_VIEW_PROMPT,
    BINARY_OUTSIDE_VIEW_PROMPT,
    BINARY_PROMPT_CURRENT,
    BINARY_PROMPT_HISTORICAL,
    CLAUDE_CONTEXT,
    GPT_CONTEXT,
    MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
    NUMERIC_INSIDE_VIEW_PROMPT,
    NUMERIC_OUTSIDE_VIEW_PROMPT,
    NUMERIC_PROMPT_CURRENT,
    NUMERIC_PROMPT_HISTORICAL,
)
from ...core.types import CoreForecast, PromptSet, Question, ResearchContext
from ...storage.artifact_store import ArtifactStore
from ...utils.llm import LLMClient
from ...utils.metaculus_api import MetaculusClient, MetaculusQuestion
from ..base import BaseSource, register_source

logger = logging.getLogger(__name__)


@register_source("metaculus")
class MetaculusSource(BaseSource):
    """
    Metaculus forecast source.

    This source wraps the existing Metaculus infrastructure:
    - MetaculusClient for API interactions
    - BinaryForecaster, NumericForecaster, MultipleChoiceForecaster for forecasting
    - Web search pipeline (Google, AskNews) for research

    The source protocol methods delegate to these existing components,
    providing a consistent interface for the multi-source architecture.
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        super().__init__(config, llm_client, artifact_store)
        self._metaculus_client: MetaculusClient | None = None

    @property
    def name(self) -> str:
        return "metaculus"

    async def _get_client(self) -> MetaculusClient:
        """Get or create the Metaculus API client."""
        if self._metaculus_client is None:
            self._metaculus_client = MetaculusClient()
        return self._metaculus_client

    async def close(self):
        """Close the Metaculus client connection."""
        if self._metaculus_client is not None:
            await self._metaculus_client.close()
            self._metaculus_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def fetch_question(self, question_id: str) -> Question:
        """
        Fetch a question from Metaculus.

        Args:
            question_id: Metaculus post ID (numeric string or int)

        Returns:
            Question in the common format
        """
        client = await self._get_client()
        metaculus_q = await client.get_question(int(question_id))
        return self._convert_metaculus_question(metaculus_q)

    async def fetch_metaculus_question(self, question_id: str) -> MetaculusQuestion:
        """
        Fetch the raw MetaculusQuestion object.

        This is useful when you need the full Metaculus-specific data
        (e.g., for submission).
        """
        client = await self._get_client()
        return await client.get_question(int(question_id))

    def _convert_metaculus_question(self, mq: MetaculusQuestion) -> Question:
        """Convert MetaculusQuestion to common Question format."""
        # Map Metaculus question types to common types
        question_type = mq.question_type
        if question_type in ("discrete", "date"):
            question_type = "numeric"  # Treat discrete/date as numeric variants

        return Question(
            id=str(mq.question_id),  # Use question_id, not post id
            source="metaculus",
            title=mq.title,
            description=mq.description or mq.background_info or "",
            resolution_criteria=mq.resolution_criteria,
            fine_print=mq.fine_print,
            question_type=question_type,
            open_time=mq.open_time or "",
            scheduled_resolve_time=mq.scheduled_resolve_time or "",
            lower_bound=mq.lower_bound,
            upper_bound=mq.upper_bound,
            unit_of_measure=mq.unit_of_measure or "",
            options=[opt.get("text", "") for opt in (mq.options or [])],
            raw={
                "post_id": mq.id,
                "question_id": mq.question_id,
                "metaculus_type": mq.question_type,
                "cdf_size": mq.cdf_size,
                "community_prediction": mq.community_prediction,
            },
        )

    async def build_research_context(self, question: Question) -> ResearchContext:
        """
        Build research context for a Metaculus question.

        This method is not used directly when using the existing handlers,
        as they do their own research internally. It's provided for protocol
        conformance and potential future use.
        """
        # The existing handlers (BinaryForecaster, etc.) do their own research
        # This method returns an empty context as a placeholder
        # When using the existing handlers via run_forecast(), they handle research
        return ResearchContext()

    def get_prompts(self, question_type: str) -> PromptSet:
        """
        Get Metaculus prompt templates for a question type.

        Args:
            question_type: "binary", "numeric", or "multiple_choice"

        Returns:
            PromptSet with Metaculus-specific prompts
        """
        if question_type == "binary":
            return PromptSet(
                historical_query=BINARY_PROMPT_HISTORICAL,
                current_query=BINARY_PROMPT_CURRENT,
                outside_view=BINARY_OUTSIDE_VIEW_PROMPT,
                inside_view=BINARY_INSIDE_VIEW_PROMPT,
                system_claude=CLAUDE_CONTEXT,
                system_gpt=GPT_CONTEXT,
            )
        elif question_type in ("numeric", "discrete", "date"):
            return PromptSet(
                historical_query=NUMERIC_PROMPT_HISTORICAL,
                current_query=NUMERIC_PROMPT_CURRENT,
                outside_view=NUMERIC_OUTSIDE_VIEW_PROMPT,
                inside_view=NUMERIC_INSIDE_VIEW_PROMPT,
                system_claude=CLAUDE_CONTEXT,
                system_gpt=GPT_CONTEXT,
            )
        elif question_type == "multiple_choice":
            return PromptSet(
                historical_query=MULTIPLE_CHOICE_PROMPT_HISTORICAL,
                current_query=MULTIPLE_CHOICE_PROMPT_CURRENT,
                outside_view=MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
                inside_view=MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
                system_claude=CLAUDE_CONTEXT,
                system_gpt=GPT_CONTEXT,
            )
        else:
            raise ValueError(f"Unknown question type: {question_type}")

    def convert_forecast(self, forecast: CoreForecast) -> Any:
        """
        Convert core forecast to Metaculus submission format.

        Args:
            forecast: Core forecast result

        Returns:
            Metaculus-specific format:
            - Binary: float (0-1 probability)
            - Numeric: list (201-point CDF)
            - Multiple choice: dict mapping option IDs to probabilities
        """
        # For Metaculus, the prediction in CoreForecast is already in the right format
        # (handlers produce Metaculus-ready output)
        return forecast.prediction

    async def submit_forecast(self, question_id: str, forecast: Any) -> dict:
        """
        Submit a forecast to Metaculus.

        Args:
            question_id: Metaculus question ID
            forecast: Formatted forecast (from convert_forecast)

        Returns:
            Submission result dict
        """
        client = await self._get_client()
        mq = await client.get_question(int(question_id))
        response = await client.submit_prediction(mq, forecast)
        return {"success": True, "response": response}

    # =========================================================================
    # Convenience methods that use existing handlers directly
    # =========================================================================

    def get_binary_handler(self) -> BinaryForecaster:
        """Get a BinaryForecaster configured for this source."""
        return BinaryForecaster(self.config, self.llm, self.artifact_store)

    def get_numeric_handler(self) -> NumericForecaster:
        """Get a NumericForecaster configured for this source."""
        return NumericForecaster(self.config, self.llm, self.artifact_store)

    def get_multiple_choice_handler(self) -> MultipleChoiceForecaster:
        """Get a MultipleChoiceForecaster configured for this source."""
        return MultipleChoiceForecaster(self.config, self.llm, self.artifact_store)

    async def run_forecast(
        self,
        question_id: str,
        log=print,
    ) -> CoreForecast:
        """
        Run a full forecast using the existing handler infrastructure.

        This is a convenience method that delegates to the appropriate
        handler based on question type.

        Args:
            question_id: Metaculus post ID
            log: Logging callback

        Returns:
            CoreForecast with prediction and metadata
        """
        # Fetch the full Metaculus question for handler use
        mq = await self.fetch_metaculus_question(question_id)

        # Select and run appropriate handler
        if mq.question_type == "binary":
            handler = self.get_binary_handler()
            result = await handler.forecast(
                question_title=mq.title,
                question_text=mq.description or mq.background_info or "",
                background_info=mq.background_info,
                resolution_criteria=mq.resolution_criteria,
                fine_print=mq.fine_print,
                open_time=mq.open_time or "",
                scheduled_resolve_time=mq.scheduled_resolve_time or "",
                log=log,
            )
            return CoreForecast(
                prediction=result.final_probability,
                question_type="binary",
                agent_results=result.agent_results,
                historical_context=result.historical_context,
                current_context=result.current_context,
            )

        elif mq.question_type in ("numeric", "discrete", "date"):
            handler = self.get_numeric_handler()
            result = await handler.forecast(
                question_title=mq.title,
                question_text=mq.description or mq.background_info or "",
                background_info=mq.background_info,
                resolution_criteria=mq.resolution_criteria,
                fine_print=mq.fine_print,
                open_time=mq.open_time or "",
                scheduled_resolve_time=mq.scheduled_resolve_time or "",
                lower_bound=mq.lower_bound,
                upper_bound=mq.upper_bound,
                open_lower_bound=mq.open_lower_bound or False,
                open_upper_bound=mq.open_upper_bound or False,
                unit_of_measure=mq.unit_of_measure,
                zero_point=mq.zero_point,
                cdf_size=mq.cdf_size,
                lower_bound_date_str=mq.lower_bound_date_str,
                upper_bound_date_str=mq.upper_bound_date_str,
                question_type=mq.question_type,
                log=log,
            )
            return CoreForecast(
                prediction=result.cdf,  # 201-point CDF
                question_type="numeric",
                agent_results=result.agent_results,
                historical_context=result.historical_context,
                current_context=result.current_context,
            )

        elif mq.question_type == "multiple_choice":
            handler = self.get_multiple_choice_handler()
            result = await handler.forecast(
                question_title=mq.title,
                question_text=mq.description or mq.background_info or "",
                background_info=mq.background_info,
                resolution_criteria=mq.resolution_criteria,
                fine_print=mq.fine_print,
                open_time=mq.open_time or "",
                scheduled_resolve_time=mq.scheduled_resolve_time or "",
                options=mq.options or [],
                log=log,
            )
            return CoreForecast(
                prediction=result.probability_distribution,
                question_type="multiple_choice",
                agent_results=result.agent_results,
                historical_context=result.historical_context,
                current_context=result.current_context,
            )

        else:
            raise ValueError(f"Unsupported question type: {mq.question_type}")
