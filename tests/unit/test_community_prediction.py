"""
Tests for community prediction meta-question detection, parsing, and formatting.

These tests do NOT require a browser — they test the pure-logic functions for
detecting meta-questions, parsing underlying question details, and formatting
context for the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.scraping.community_prediction import (
    MetaQuestionDetails,
    ScrapedCommunityPrediction,
    format_community_prediction_context,
    is_community_prediction_question,
    parse_meta_question_details,
    parse_p_yes,
)

# ---------------------------------------------------------------------------
# Minimal question stub (avoids importing full MetaculusQuestion)
# ---------------------------------------------------------------------------


@dataclass
class FakeQuestion:
    """Minimal question object for testing detection/parsing."""

    title: str = ""
    description: str = ""
    resolution_criteria: str = ""
    fine_print: str = ""


# ---------------------------------------------------------------------------
# Sample data from actual meta-questions
# ---------------------------------------------------------------------------

SAMPLE_DESCRIPTION = (
    "Metaculus is a crowdsourced forecast aggregation platform where humans and bots "
    "compete to predict future events. Each question on Metaculus has a community "
    "prediction that aggregates all user's forecasts.\n\n"
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

SAMPLE_REGULAR_TITLE = "Will the United States attack Iran before April 2026?"
SAMPLE_REGULAR_DESCRIPTION = "Some background about geopolitical tensions."


# ---------------------------------------------------------------------------
# Tests: is_community_prediction_question
# ---------------------------------------------------------------------------


class TestIsCommunityPredictionQuestion:
    def test_detects_from_json_payload_in_description(self):
        q = FakeQuestion(description=SAMPLE_DESCRIPTION, title="Unrelated title")
        assert is_community_prediction_question(q) is True

    def test_detects_from_title_pattern(self):
        q = FakeQuestion(title=SAMPLE_TITLE, description="No payload here")
        assert is_community_prediction_question(q) is True

    def test_detects_lower_than_variant(self):
        q = FakeQuestion(
            title="Will the community prediction be lower than 50.00% on 2026-03-01 for...",
            description="",
        )
        assert is_community_prediction_question(q) is True

    def test_rejects_regular_binary_question(self):
        q = FakeQuestion(
            title=SAMPLE_REGULAR_TITLE,
            description=SAMPLE_REGULAR_DESCRIPTION,
        )
        assert is_community_prediction_question(q) is False

    def test_rejects_empty_question(self):
        q = FakeQuestion()
        assert is_community_prediction_question(q) is False

    def test_handles_none_fields(self):
        """Should not crash if description/title are None."""
        q = FakeQuestion(title=None, description=None)
        assert is_community_prediction_question(q) is False


# ---------------------------------------------------------------------------
# Tests: parse_meta_question_details
# ---------------------------------------------------------------------------


class TestParseMetaQuestionDetails:
    def test_parses_full_meta_question(self):
        q = FakeQuestion(
            title=SAMPLE_TITLE,
            description=SAMPLE_DESCRIPTION,
            resolution_criteria=SAMPLE_RESOLUTION_CRITERIA,
        )
        details = parse_meta_question_details(q)

        assert details is not None
        assert details.underlying_post_id == 41508
        assert details.underlying_question_id == 41255
        assert details.last_cp == 0.82
        assert details.direction == "higher"
        assert details.threshold == 0.82
        assert details.target_date == "2026-02-14 16:20:16"
        assert "Nathan Young" in details.underlying_title

    def test_parses_from_resolution_criteria_fallback(self):
        """When JSON payload is missing, falls back to URL in resolution_criteria."""
        q = FakeQuestion(
            title=SAMPLE_TITLE,
            description="No JSON payload here",
            resolution_criteria=SAMPLE_RESOLUTION_CRITERIA,
        )
        details = parse_meta_question_details(q)

        assert details is not None
        assert details.underlying_post_id == 41508
        assert details.underlying_question_id is None  # Only available from JSON
        assert details.last_cp is None
        assert details.direction == "higher"
        assert details.threshold == 0.82

    def test_returns_none_for_regular_question(self):
        q = FakeQuestion(
            title=SAMPLE_REGULAR_TITLE,
            description=SAMPLE_REGULAR_DESCRIPTION,
            resolution_criteria="Resolves Yes if something happens.",
        )
        details = parse_meta_question_details(q)
        assert details is None

    def test_parses_direction_lower(self):
        q = FakeQuestion(
            title="Will the community prediction be lower than 30.00% on 2026-03-01 for...",
            description=(
                '`{"format":"metaculus_binary_cp_rises","info":{"post_id":40972,'
                '"question_id":40001,"last_cp":0.30}}`'
            ),
            resolution_criteria=(
                "If the community prediction of the target question "
                "on 2026-03-01 12:00:00 is lower than 30.00%, ..."
            ),
        )
        details = parse_meta_question_details(q)

        assert details is not None
        assert details.direction == "lower"
        assert details.threshold == 0.30

    def test_handles_none_fields(self):
        q = FakeQuestion(title=None, description=None, resolution_criteria=None)
        details = parse_meta_question_details(q)
        assert details is None


# ---------------------------------------------------------------------------
# Tests: parse_p_yes
# ---------------------------------------------------------------------------


class TestParsePYes:
    def test_extracts_from_current(self):
        assert parse_p_yes({"current": 0.54}) == 0.54

    def test_extracts_from_current_string(self):
        assert parse_p_yes({"current": "0.73"}) == 0.73

    def test_falls_back_to_centers(self):
        assert parse_p_yes({"centers": "0.82"}) == 0.82

    def test_prefers_current_over_centers(self):
        assert parse_p_yes({"current": 0.54, "centers": "0.82"}) == 0.54

    def test_returns_none_for_empty(self):
        assert parse_p_yes({}) is None

    def test_returns_none_for_invalid(self):
        assert parse_p_yes({"current": "not_a_number"}) is None


# ---------------------------------------------------------------------------
# Tests: format_community_prediction_context
# ---------------------------------------------------------------------------


class TestFormatCommunityPredictionContext:
    def test_basic_format(self):
        scraped = ScrapedCommunityPrediction(
            p_yes=0.54,
            forecaster_count=72,
            history_length=179,
            trend={
                "week_delta": -0.02,
                "two_week_delta": -0.05,
                "history_min": 0.41,
                "history_max": 0.89,
            },
        )
        details = MetaQuestionDetails(
            underlying_post_id=41508,
            underlying_question_id=41255,
            underlying_title="Will the Community beat Nathan Young?",
            last_cp=0.82,
            direction="higher",
            threshold=0.82,
            target_date="2026-02-14",
        )

        context = format_community_prediction_context(scraped, details)

        # Check XML tags
        assert "<CommunityPrediction" in context
        assert "</CommunityPrediction>" in context
        assert 'underlying_question_id="41508"' in context

        # Check key data
        assert "54.0%" in context
        assert "72 forecasters" in context
        assert "82.00%" in context
        assert "HIGHER THAN" in context
        assert "28.0 percentage points" in context
        assert "BELOW" in context

        # Check trend
        assert "7-day change" in context
        assert "14-day change" in context
        assert "[0.41, 0.89]" in context

    def test_format_without_trend(self):
        """Should work even without trend data."""
        scraped = ScrapedCommunityPrediction(
            p_yes=0.15,
            forecaster_count=300,
        )
        details = MetaQuestionDetails(
            underlying_post_id=41594,
            direction="higher",
            threshold=0.10,
        )

        context = format_community_prediction_context(scraped, details)
        assert "15.0%" in context
        assert "300 forecasters" in context
        assert "ABOVE" in context  # 0.15 > 0.10 threshold

    def test_format_with_resolution(self):
        """Should include resolution if the underlying question has resolved."""
        scraped = ScrapedCommunityPrediction(
            p_yes=0.95,
            resolution="Yes",
        )
        details = MetaQuestionDetails(
            underlying_post_id=40001,
        )

        context = format_community_prediction_context(scraped, details)
        assert "resolution: Yes" in context

    def test_format_without_threshold(self):
        """Should not crash if threshold/direction are missing."""
        scraped = ScrapedCommunityPrediction(p_yes=0.50)
        details = MetaQuestionDetails(underlying_post_id=12345)

        context = format_community_prediction_context(scraped, details)
        assert "50.0%" in context
        assert "HIGHER THAN" not in context  # No threshold, so no comparison
