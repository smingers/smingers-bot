"""
Kalshi prediction market source implementation.

Fetches events from Kalshi's public API and treats mutually exclusive
markets as multiple choice questions for the forecasting pipeline.

No purchases or submissions — predictions are saved locally only.

Usage:
    python main.py --source kalshi --question KXPRESNOMD-28 --mode test
"""

import logging
from datetime import datetime
from typing import Any

from ...bot.forecaster import ScopedArtifactStore
from ...bot.multiple_choice import MultipleChoiceForecaster
from ...bot.prompts import (
    CLAUDE_CONTEXT,
    GPT_CONTEXT,
    MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
)
from ...core.types import CoreForecast, PromptSet, Question, ResearchContext
from ...storage.artifact_store import ArtifactStore
from ...utils.llm import LLMClient
from ..base import BaseSource, register_source
from .client import KalshiClient, KalshiEvent

logger = logging.getLogger(__name__)


def _parse_event_ticker(question_id: str) -> str:
    """
    Extract event ticker from a question_id or Kalshi URL.

    Accepts:
        "KXPRESNOMD-28"
        "https://kalshi.com/markets/kxpresnomd/democratic-primary-winner/kxpresnomd-28"

    Raises:
        ValueError: If the input is empty or yields an empty ticker.
    """
    if not question_id or not question_id.strip():
        raise ValueError("Event ticker or URL must not be empty")

    # If it looks like a URL, extract the last path segment and uppercase it
    if "kalshi.com" in question_id:
        # URL format: .../markets/{series}/{slug}/{event_ticker}
        path = question_id.rstrip("/").split("/")
        ticker = path[-1].upper()
    else:
        # Direct event ticker
        ticker = question_id.strip().upper()

    if not ticker:
        raise ValueError(f"Could not extract event ticker from: {question_id}")

    return ticker


def _build_resolution_criteria(event: KalshiEvent) -> str:
    """Build resolution criteria from event metadata."""
    parts = []

    if event.mutually_exclusive:
        parts.append("This is a mutually exclusive event — exactly one option will resolve YES.")

    # Use the first market's rules as a template
    if event.markets:
        first_rules = event.markets[0].rules_primary
        if first_rules:
            # Generalize the template by removing the specific candidate name
            candidate = event.markets[0].yes_sub_title
            if candidate and candidate in first_rules:
                template = first_rules.replace(candidate, "[Candidate]")
                parts.append(f"Resolution rule: {template}")
            else:
                parts.append(f"Resolution rule: {first_rules}")

    # Add early close condition if present
    raw_market = event.markets[0].raw if event.markets else {}
    early_close = raw_market.get("early_close_condition", "")
    if early_close:
        parts.append(f"Early close: {early_close}")

    return "\n".join(parts)


@register_source("kalshi")
class KalshiSource(BaseSource):
    """
    Kalshi prediction market source.

    Fetches events from Kalshi's public API and converts mutually exclusive
    market sets into multiple choice questions for the forecasting pipeline.

    Key characteristics:
    - Read-only (no purchases or trading)
    - Unauthenticated (market data is public)
    - Market prices stored in artifacts but NOT shown to forecasters (no anchoring)
    - Web search via handlers (same as local/Metaculus sources)
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        super().__init__(config, llm_client, artifact_store)
        self._kalshi_client: KalshiClient | None = None

    @property
    def name(self) -> str:
        return "kalshi"

    async def _get_client(self) -> KalshiClient:
        """Get or create the Kalshi API client."""
        if self._kalshi_client is None:
            self._kalshi_client = KalshiClient()
        return self._kalshi_client

    async def close(self) -> None:
        """Close the Kalshi client connection."""
        if self._kalshi_client is not None:
            await self._kalshi_client.close()
            self._kalshi_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def fetch_question(self, question_id: str) -> Question:
        """
        Fetch a Kalshi event as a multiple choice Question.

        Args:
            question_id: Event ticker or Kalshi URL

        Returns:
            Question with markets as options
        """
        event_ticker = _parse_event_ticker(question_id)
        client = await self._get_client()
        event = await client.get_event(event_ticker, with_nested_markets=True)
        return self._convert_event_to_question(event)

    async def fetch_kalshi_event(self, question_id: str) -> KalshiEvent:
        """Fetch the raw KalshiEvent object."""
        event_ticker = _parse_event_ticker(question_id)
        client = await self._get_client()
        return await client.get_event(event_ticker, with_nested_markets=True)

    def _convert_event_to_question(self, event: KalshiEvent) -> Question:
        """Convert a Kalshi event with markets into a multiple choice Question."""
        if not event.markets:
            raise ValueError(f"Event {event.event_ticker} has no markets — cannot create question")

        # Sort markets by ask price descending for readability
        sorted_markets = sorted(event.markets, key=lambda m: m.yes_ask, reverse=True)

        # Extract candidate names as options
        options = [m.yes_sub_title or m.ticker for m in sorted_markets]

        # Build market price lookup (stored in raw, not shown to forecasters)
        market_prices = {
            m.yes_sub_title or m.ticker: {
                "ticker": m.ticker,
                "last_price": m.last_price,
                "yes_bid": m.yes_bid,
                "yes_ask": m.yes_ask,
                "implied_probability": m.implied_probability,
                "volume": m.volume,
                "open_interest": m.open_interest,
            }
            for m in sorted_markets
        }

        # Build title with subtitle if present
        title = event.title
        if event.sub_title:
            title = f"{event.title} ({event.sub_title})"

        return Question(
            id=event.event_ticker,
            source="kalshi",
            title=title,
            description=(
                f"Kalshi prediction market event: {event.title}\n"
                f"Category: {event.category}\n"
                f"Number of options: {len(options)}\n"
                f"Settlement type: {event.collateral_return_type}"
            ),
            resolution_criteria=_build_resolution_criteria(event),
            fine_print="",
            question_type="multiple_choice",
            open_time="",
            scheduled_resolve_time=sorted_markets[0].close_time if sorted_markets else "",
            options=options,
            raw={
                "event_ticker": event.event_ticker,
                "series_ticker": event.series_ticker,
                "category": event.category,
                "mutually_exclusive": event.mutually_exclusive,
                "collateral_return_type": event.collateral_return_type,
                "market_prices": market_prices,
                "market_tickers": {(m.yes_sub_title or m.ticker): m.ticker for m in sorted_markets},
            },
        )

    async def build_research_context(self, question: Question) -> ResearchContext:
        """
        Build research context for a Kalshi question.

        Returns empty — handlers do their own web search.
        Market prices are intentionally excluded to prevent anchoring.
        """
        return ResearchContext()

    def get_prompts(self, question_type: str) -> PromptSet:
        """
        Get prompt templates for a question type.

        Uses the same prompts as Metaculus/local sources.
        """
        if question_type == "multiple_choice":
            return PromptSet(
                historical_query=MULTIPLE_CHOICE_PROMPT_HISTORICAL,
                current_query=MULTIPLE_CHOICE_PROMPT_CURRENT,
                outside_view=MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
                inside_view=MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
                system_claude=CLAUDE_CONTEXT,
                system_gpt=GPT_CONTEXT,
            )
        else:
            raise ValueError(
                f"Kalshi source only supports multiple_choice questions, got: {question_type}"
            )

    def convert_forecast(self, forecast: CoreForecast) -> Any:
        """
        Convert core forecast to local storage format.

        Passthrough — no external submission format needed.
        """
        return forecast.prediction

    async def submit_forecast(self, question_id: str, forecast: Any) -> dict:
        """
        "Submit" a Kalshi prediction (saves locally only).

        No purchases or trading — results are saved to artifacts.
        """
        timestamp = datetime.now().isoformat()

        logger.info(f"Kalshi prediction saved for event: {question_id}")

        return {
            "status": "saved_locally",
            "submitted": False,
            "message": "Prediction saved to local artifacts (no Kalshi trading)",
            "question_id": question_id,
            "timestamp": timestamp,
        }

    # =========================================================================
    # Full forecast pipeline
    # =========================================================================

    async def run_forecast(
        self,
        question_id: str,
        log=print,
    ) -> tuple[CoreForecast, Question]:
        """
        Run a full forecast using the MultipleChoiceForecaster handler.

        Args:
            question_id: Event ticker or Kalshi URL
            log: Logging callback

        Returns:
            Tuple of (CoreForecast, Question) — forecast result and the fetched question
        """
        start_time = datetime.now()

        question = await self.fetch_question(question_id)

        # Set up artifact storage
        artifacts = None
        scoped_store = None
        if self.artifact_store:
            artifacts = self.artifact_store.create_forecast_artifacts(question.id)
            scoped_store = ScopedArtifactStore(self.artifact_store, artifacts)
            self.artifact_store.save_question(artifacts, question.raw)

        handler = MultipleChoiceForecaster(self.config, self.llm, scoped_store)
        result = await handler.forecast(
            question_title=question.title,
            question_text=question.description,
            background_info=question.description,
            resolution_criteria=question.resolution_criteria,
            fine_print=question.fine_print,
            open_time=question.open_time,
            scheduled_resolve_time=question.scheduled_resolve_time,
            options=question.options,
            log=log,
        )

        # Save prediction and metadata artifacts
        if self.artifact_store and artifacts:
            self.artifact_store.save_prediction(
                artifacts,
                {
                    "source": "kalshi",
                    "event_ticker": question.id,
                    "question_type": "multiple_choice",
                    "probability_distribution": result.final_probabilities,
                    "num_options": len(question.options),
                },
            )

            end_time = datetime.now()
            costs = self.llm.get_session_costs() if self.llm else {}
            self.artifact_store.save_metadata(
                artifacts,
                config=self.config,
                costs=costs,
                timing={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds(),
                },
                analysis={
                    "source": "kalshi",
                    "event_ticker": question.id,
                    "title": question.title,
                    "question_type": "multiple_choice",
                    "num_options": len(question.options),
                },
            )

        forecast = CoreForecast(
            prediction=result.final_probabilities,
            question_type="multiple_choice",
            agent_results=result.agent_results,
            historical_context=result.historical_context,
            current_context=result.current_context,
        )

        return forecast, question
