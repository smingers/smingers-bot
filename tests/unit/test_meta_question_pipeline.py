"""
Integration test: verify that _forecast_binary detects meta-questions,
scrapes community predictions, and threads the context through to the
BinaryForecaster.

Mocks:
- scrape_community_prediction (no browser needed)
- BinaryForecaster.forecast (no LLM calls)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scraping.community_prediction import (
    ScrapedCommunityPrediction,
)

# ---------------------------------------------------------------------------
# Fake question stub
# ---------------------------------------------------------------------------

SAMPLE_DESCRIPTION = (
    "Metaculus is a crowdsourced forecast aggregation platform...\n\n"
    "--------------------------------\n\n"
    "Below are some details about the original Metaculus question: \n"
    "- Question URL: https://www.metaculus.com/questions/41508\n"
    "- Original question title: Will the Community beat Nathan Young in the "
    "Metaculus Cup Spring 2026?\n"
    "- The current community prediction as of 2026-02-01: 82.00%\n\n"
    "Original resolution criteria: \n"
    "> This question will resolve as **Yes** if ...\n\n"
    '`{"format":"metaculus_binary_cp_rises","info":{"post_id":41508,'
    '"question_id":41255,"last_cp":0.82}}`'
)

SAMPLE_TITLE = (
    "Will the community prediction be higher than 82.00% on 2026-02-14 "
    'for the Metaculus question "Will the Community beat Nathan Young in '
    'the Metaculus Cup Spring 2026?"?'
)

SAMPLE_RESOLUTION_CRITERIA = (
    "This question will resolve based on the community prediction of the "
    "Metaculus question found [here](https://www.metaculus.com/questions/41508) "
    "(i.e. the 'target question'). If the community prediction of the target "
    "question on 2026-02-14 16:20:16 is higher than 82.00%, this question will "
    "resolve to 'Yes'. If it is lower or equal to 82.00%, this question will "
    "resolve to 'No'."
)


@dataclass
class FakeQuestion:
    """Minimal MetaculusQuestion stub for integration tests."""

    id: int = 42014
    title: str = SAMPLE_TITLE
    description: str = SAMPLE_DESCRIPTION
    resolution_criteria: str = SAMPLE_RESOLUTION_CRITERIA
    fine_print: str = ""
    background_info: str = ""
    question_type: str = "binary"
    status: str = "open"
    open_time: str = "2026-02-01"
    scheduled_close_time: str = "2026-02-14"
    scheduled_resolve_time: str = "2026-02-14"
    community_prediction: float | None = None
    num_forecasters: int | None = None


@dataclass
class FakeForecastResult:
    """Minimal return value from BinaryForecaster.forecast()."""

    final_probability: float = 0.35
    agent_results: list = field(default_factory=list)
    historical_context: str = ""
    current_context: str = ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMetaQuestionPipelineIntegration:
    """Test that _forecast_binary correctly handles meta-questions."""

    @pytest.mark.asyncio
    async def test_meta_question_scrapes_and_injects_context(self):
        """When a meta-question is detected, scrape_community_prediction is called
        and the formatted context is passed through to BinaryForecaster.forecast().
        """
        fake_scraped = ScrapedCommunityPrediction(
            p_yes=0.54,
            forecaster_count=72,
            history_length=179,
            trend={"week_delta": -0.02, "history_min": 0.41, "history_max": 0.89},
        )

        fake_result = FakeForecastResult()

        config = {
            "research": {
                "community_prediction_scraping_enabled": True,
                "community_prediction_wait_seconds": 1.0,
            },
            "models": {"fast": "test-model", "quality": "test-model"},
        }

        with (
            patch(
                "src.bot.forecaster.scrape_community_prediction",
                return_value=fake_scraped,
            ) as mock_scrape,
            patch(
                "src.bot.forecaster.BinaryForecaster",
            ) as MockBinaryForecaster,
        ):
            mock_forecaster_instance = MagicMock()
            mock_forecaster_instance.forecast = AsyncMock(return_value=fake_result)
            mock_forecaster_instance.pipeline_warnings = []
            MockBinaryForecaster.return_value = mock_forecaster_instance

            # Create the Forecaster and call _forecast_binary
            from src.bot.forecaster import Forecaster

            forecaster = Forecaster.__new__(Forecaster)
            forecaster.config = config
            forecaster.llm = MagicMock()

            question = FakeQuestion()
            scoped_store = MagicMock()

            result = await forecaster._forecast_binary(question, scoped_store)

            # Verify scraper was called with the underlying question ID
            mock_scrape.assert_called_once()
            call_args = mock_scrape.call_args
            assert call_args[0][0] == 41508  # underlying_post_id
            assert call_args[1]["wait_seconds"] == 1.0

            # Verify community_prediction_context was passed to forecast()
            forecast_call = mock_forecaster_instance.forecast.call_args
            cp_context = forecast_call[1].get("community_prediction_context", "")
            assert cp_context != "", "community_prediction_context should not be empty"
            assert "<CommunityPrediction" in cp_context
            assert "54.0%" in cp_context
            assert "72 forecasters" in cp_context
            assert "HIGHER THAN" in cp_context

            # Verify result structure
            assert result["final_prediction"] == 0.35

    @pytest.mark.asyncio
    async def test_meta_question_scrape_failure_continues(self):
        """When scraping fails (returns None), pipeline continues without context."""
        config = {
            "research": {
                "community_prediction_scraping_enabled": True,
                "community_prediction_wait_seconds": 1.0,
            },
        }

        fake_result = FakeForecastResult()

        with (
            patch(
                "src.bot.forecaster.scrape_community_prediction",
                return_value=None,  # Scraping failed
            ),
            patch(
                "src.bot.forecaster.BinaryForecaster",
            ) as MockBinaryForecaster,
        ):
            mock_forecaster_instance = MagicMock()
            mock_forecaster_instance.forecast = AsyncMock(return_value=fake_result)
            mock_forecaster_instance.pipeline_warnings = []
            MockBinaryForecaster.return_value = mock_forecaster_instance

            from src.bot.forecaster import Forecaster

            forecaster = Forecaster.__new__(Forecaster)
            forecaster.config = config
            forecaster.llm = MagicMock()

            question = FakeQuestion()
            result = await forecaster._forecast_binary(question, MagicMock())

            # Should pass empty context (no crash)
            forecast_call = mock_forecaster_instance.forecast.call_args
            cp_context = forecast_call[1].get("community_prediction_context", "")
            assert cp_context == ""
            assert result["final_prediction"] == 0.35

    @pytest.mark.asyncio
    async def test_config_disables_scraping(self):
        """When config flag is False, scraping is skipped entirely."""
        config = {
            "research": {
                "community_prediction_scraping_enabled": False,
            },
        }

        fake_result = FakeForecastResult()

        with (
            patch(
                "src.bot.forecaster.scrape_community_prediction",
            ) as mock_scrape,
            patch(
                "src.bot.forecaster.BinaryForecaster",
            ) as MockBinaryForecaster,
        ):
            mock_forecaster_instance = MagicMock()
            mock_forecaster_instance.forecast = AsyncMock(return_value=fake_result)
            mock_forecaster_instance.pipeline_warnings = []
            MockBinaryForecaster.return_value = mock_forecaster_instance

            from src.bot.forecaster import Forecaster

            forecaster = Forecaster.__new__(Forecaster)
            forecaster.config = config
            forecaster.llm = MagicMock()

            question = FakeQuestion()
            await forecaster._forecast_binary(question, MagicMock())

            # Scraper should NOT have been called
            mock_scrape.assert_not_called()

    @pytest.mark.asyncio
    async def test_regular_question_skips_scraping(self):
        """Non-meta-questions should not trigger scraping."""
        config = {
            "research": {
                "community_prediction_scraping_enabled": True,
            },
        }

        fake_result = FakeForecastResult()

        with (
            patch(
                "src.bot.forecaster.scrape_community_prediction",
            ) as mock_scrape,
            patch(
                "src.bot.forecaster.BinaryForecaster",
            ) as MockBinaryForecaster,
        ):
            mock_forecaster_instance = MagicMock()
            mock_forecaster_instance.forecast = AsyncMock(return_value=fake_result)
            mock_forecaster_instance.pipeline_warnings = []
            MockBinaryForecaster.return_value = mock_forecaster_instance

            from src.bot.forecaster import Forecaster

            forecaster = Forecaster.__new__(Forecaster)
            forecaster.config = config
            forecaster.llm = MagicMock()

            # Regular question — NOT a meta-question
            question = FakeQuestion(
                title="Will the United States attack Iran before April 2026?",
                description="Some background about geopolitical tensions.",
                resolution_criteria="Resolves Yes if the US attacks Iran.",
            )
            await forecaster._forecast_binary(question, MagicMock())

            mock_scrape.assert_not_called()
