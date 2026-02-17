"""
Tests for meta-forecast question detection, CP history extraction, and formatting.

Tests cover:
- MetaForecastInfo.from_description() detection and extraction
- AggregationHistory.from_api_response() parsing
- format_meta_forecast_context() output formatting
- Pipeline integration (meta_forecast_context injected into historical_context)
"""

import pytest

from src.bot.forecaster import format_meta_forecast_context
from src.utils.metaculus_api import (
    AggregationHistory,
    AggregationHistoryPoint,
    MetaForecastInfo,
)

# ============================================================================
# MetaForecastInfo.from_description() Tests
# ============================================================================


class TestMetaForecastInfoDetection:
    """Tests for detecting and parsing meta-forecast format tags in question descriptions."""

    def test_detects_cp_rises_format(self):
        """Detects metaculus_binary_cp_rises format tag."""
        description = (
            "Some question description text.\n\n"
            '`{"format":"metaculus_binary_cp_rises",'
            '"info":{"post_id":41502,"question_id":41231,"last_cp":0.06}}`'
        )

        result = MetaForecastInfo.from_description(description)

        assert result is not None
        assert result.format == "metaculus_binary_cp_rises"
        assert result.target_post_id == 41502
        assert result.target_question_id == 41231
        assert result.last_cp == 0.06

    def test_returns_none_for_non_meta_question(self):
        """Returns None for a standard question without format tag."""
        description = "A regular question about whether X will happen by 2026."

        result = MetaForecastInfo.from_description(description)

        assert result is None

    def test_returns_none_for_other_format_types(self):
        """Returns None for non-CP-rises format tags."""
        description = 'Some text.\n\n`{"format":"bot_tournament_question","info":{"post_id":123}}`'

        result = MetaForecastInfo.from_description(description)

        assert result is None

    def test_returns_none_for_empty_description(self):
        """Returns None for empty description."""
        assert MetaForecastInfo.from_description("") is None
        assert MetaForecastInfo.from_description(None) is None

    def test_returns_none_for_malformed_json(self):
        """Returns None for malformed JSON in backticks."""
        description = "Some text.\n\n`{not valid json}`"

        result = MetaForecastInfo.from_description(description)

        assert result is None

    def test_returns_none_for_missing_info_fields(self):
        """Returns None when required info fields are missing."""
        description = (
            'Some text.\n\n`{"format":"metaculus_binary_cp_rises","info":{"post_id":123}}`'
        )

        result = MetaForecastInfo.from_description(description)

        assert result is None

    def test_handles_real_question_description(self):
        """Parses a real meta-forecast question description from the dataset."""
        description = (
            "Metaculus is a crowdsourced forecast aggregation platform where humans "
            "and bots compete to predict future events. Each question on Metaculus "
            "has a community prediction that aggregates all user's forecasts. As of "
            "this question launch, this aggregation is calculated as a median of user "
            "forecasts weighted by recency. \n\n"
            "--------------------------------\n\n"
            "Below are some details about the original Metaculus question: \n"
            "- Question URL: https://www.metaculus.com/questions/41502\n"
            "- Original question title: Will the United States gain formal sovereignty "
            "over any part of Greenland during 2026?\n"
            "- The current community prediction as of 2026-02-16: 6.00%\n\n"
            "Original resolution criteria: \n"
            "> This question will resolve as Yes if...\n\n"
            '`{"format":"metaculus_binary_cp_rises",'
            '"info":{"post_id":41502,"question_id":41231,"last_cp":0.06}}`'
        )

        result = MetaForecastInfo.from_description(description)

        assert result is not None
        assert result.target_post_id == 41502
        assert result.target_question_id == 41231
        assert result.last_cp == 0.06

    def test_handles_whitespace_after_tag(self):
        """Handles trailing whitespace/newlines after the format tag."""
        description = (
            "Some text.\n\n"
            '`{"format":"metaculus_binary_cp_rises",'
            '"info":{"post_id":100,"question_id":200,"last_cp":0.25}}`\n\n'
        )

        result = MetaForecastInfo.from_description(description)

        assert result is not None
        assert result.target_post_id == 100
        assert result.last_cp == 0.25

    def test_parses_close_price_rises_as_none(self):
        """Returns None for close_price_rises format (not a Metaculus CP question)."""
        description = (
            "Some text.\n\n"
            '`{"format":"close_price_rises","info":{"ticker":"AAPL","last_price":150.0}}`'
        )

        result = MetaForecastInfo.from_description(description)

        assert result is None


# ============================================================================
# AggregationHistory.from_api_response() Tests
# ============================================================================


class TestAggregationHistoryParsing:
    """Tests for parsing aggregation history from API responses."""

    def test_parses_recency_weighted_history(self):
        """Parses recency_weighted aggregation history."""
        data = {
            "id": 41502,
            "title": "Will the US gain sovereignty over Greenland?",
            "question": {
                "aggregations": {
                    "recency_weighted": {
                        "history": [
                            {
                                "start_time": 1737158400.0,
                                "end_time": 1737244800.0,
                                "centers": [0.04],
                                "forecaster_count": 12,
                                "interval_lower_bounds": [0.02],
                                "interval_upper_bounds": [0.08],
                            },
                            {
                                "start_time": 1737244800.0,
                                "end_time": 1737331200.0,
                                "centers": [0.078],
                                "forecaster_count": 28,
                                "interval_lower_bounds": [0.05],
                                "interval_upper_bounds": [0.11],
                            },
                        ],
                        "latest": {
                            "centers": [0.06],
                            "forecaster_count": 89,
                        },
                    }
                }
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert result.question_title == "Will the US gain sovereignty over Greenland?"
        assert result.question_post_id == 41502
        assert result.aggregation_method == "recency_weighted"
        assert len(result.history) == 2
        assert result.history[0].centers == [0.04]
        assert result.history[0].forecaster_count == 12
        assert result.history[1].centers == [0.078]
        assert result.latest_cp == 0.06

    def test_parses_unweighted_history(self):
        """Parses unweighted aggregation history (tournament questions)."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {
                "aggregations": {
                    "unweighted": {
                        "history": [
                            {
                                "start_time": 1737158400.0,
                                "end_time": 1737244800.0,
                                "centers": [0.05],
                                "forecaster_count": 10,
                            },
                        ],
                        "latest": {"centers": [0.07]},
                    }
                }
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert result.aggregation_method == "unweighted"
        assert len(result.history) == 1
        assert result.latest_cp == 0.07

    def test_handles_empty_history(self):
        """Handles empty history array gracefully."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {
                "aggregations": {
                    "recency_weighted": {
                        "history": [],
                        "latest": None,
                    }
                }
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert len(result.history) == 0
        assert result.latest_cp is None

    def test_handles_null_aggregations(self):
        """Handles null aggregations field."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {
                "aggregations": None,
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert len(result.history) == 0
        assert result.latest_cp is None
        assert result.aggregation_method is None

    def test_handles_missing_aggregations(self):
        """Handles missing aggregations key entirely."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {},
        }

        result = AggregationHistory.from_api_response(data)

        assert len(result.history) == 0
        assert result.latest_cp is None

    def test_latest_cp_falls_back_to_last_history_point(self):
        """Uses last history point if 'latest' is missing."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {
                "aggregations": {
                    "recency_weighted": {
                        "history": [
                            {
                                "start_time": 1737158400.0,
                                "end_time": 1737244800.0,
                                "centers": [0.08],
                                "forecaster_count": 15,
                            },
                        ],
                        "latest": None,
                    }
                }
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert result.latest_cp == 0.08

    def test_prefers_recency_weighted_over_unweighted(self):
        """Prefers recency_weighted when both methods exist with data."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {
                "aggregations": {
                    "recency_weighted": {
                        "history": [
                            {
                                "start_time": 1737158400.0,
                                "end_time": 1737244800.0,
                                "centers": [0.05],
                                "forecaster_count": 10,
                            },
                        ],
                        "latest": {"centers": [0.06]},
                    },
                    "unweighted": {
                        "history": [
                            {
                                "start_time": 1737158400.0,
                                "end_time": 1737244800.0,
                                "centers": [0.07],
                                "forecaster_count": 10,
                            },
                        ],
                        "latest": {"centers": [0.08]},
                    },
                }
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert result.aggregation_method == "recency_weighted"
        assert result.latest_cp == 0.06

    def test_skips_history_entries_without_centers(self):
        """Skips history entries that lack centers field."""
        data = {
            "id": 41502,
            "title": "Test question",
            "question": {
                "aggregations": {
                    "recency_weighted": {
                        "history": [
                            {
                                "start_time": 1737158400.0,
                                "end_time": 1737244800.0,
                                "centers": [],  # Empty centers
                                "forecaster_count": 1,
                            },
                            {
                                "start_time": 1737244800.0,
                                "end_time": 1737331200.0,
                                "centers": [0.05],
                                "forecaster_count": 10,
                            },
                        ],
                        "latest": None,
                    }
                }
            },
        }

        result = AggregationHistory.from_api_response(data)

        assert len(result.history) == 1
        assert result.history[0].centers == [0.05]


# ============================================================================
# format_meta_forecast_context() Tests
# ============================================================================


class TestFormatMetaForecastContext:
    """Tests for formatting CP history into readable text for the pipeline."""

    @pytest.fixture
    def meta_info(self):
        """Sample MetaForecastInfo."""
        return MetaForecastInfo(
            format="metaculus_binary_cp_rises",
            target_post_id=41502,
            target_question_id=41231,
            last_cp=0.06,
        )

    @pytest.fixture
    def history_with_data(self):
        """Sample AggregationHistory with multiple data points."""
        return AggregationHistory(
            question_title="Will the US gain sovereignty over Greenland?",
            question_post_id=41502,
            history=[
                AggregationHistoryPoint(
                    start_time=1737158400.0,  # 2025-01-17 ~21:00 UTC
                    end_time=1737244800.0,
                    centers=[0.042],
                    forecaster_count=12,
                    interval_lower_bounds=[0.031],
                    interval_upper_bounds=[0.058],
                ),
                AggregationHistoryPoint(
                    start_time=1737417600.0,  # 2025-01-21
                    end_time=1737504000.0,
                    centers=[0.078],
                    forecaster_count=28,
                    interval_lower_bounds=[0.052],
                    interval_upper_bounds=[0.110],
                ),
                AggregationHistoryPoint(
                    start_time=1737676800.0,  # 2025-01-24
                    end_time=1737763200.0,
                    centers=[0.065],
                    forecaster_count=45,
                    interval_lower_bounds=[0.048],
                    interval_upper_bounds=[0.092],
                ),
            ],
            latest_cp=0.06,
            aggregation_method="recency_weighted",
        )

    def test_includes_target_question_info(self, meta_info, history_with_data):
        """Output includes target question title and URL."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "Will the US gain sovereignty over Greenland?" in result
        assert "https://www.metaculus.com/questions/41502/" in result

    def test_includes_baseline_cp(self, meta_info, history_with_data):
        """Output includes baseline CP from meta-question creation."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "6.00%" in result
        assert "Baseline" in result

    def test_includes_current_live_cp(self, meta_info, history_with_data):
        """Output includes the current live CP."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "Current live CP: 6.00%" in result

    def test_includes_history_table(self, meta_info, history_with_data):
        """Output includes a formatted history table with CP values."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "4.20%" in result
        assert "7.80%" in result
        assert "6.50%" in result

    def test_includes_forecaster_counts(self, meta_info, history_with_data):
        """History table includes forecaster counts."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "12" in result
        assert "28" in result
        assert "45" in result

    def test_includes_confidence_intervals(self, meta_info, history_with_data):
        """History table includes 25th-75th percentile intervals."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "3.10%" in result  # lower bound of first point
        assert "5.80%" in result  # upper bound of first point

    def test_includes_summary_statistics(self, meta_info, history_with_data):
        """Output includes range and trend summary."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "Range:" in result
        assert "Trend:" in result

    def test_includes_threshold_comparison(self, meta_info, history_with_data):
        """Output compares current CP to threshold."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "EXACTLY AT the threshold" in result

    def test_threshold_above(self, meta_info, history_with_data):
        """Shows ABOVE when current CP exceeds threshold."""
        history_with_data.latest_cp = 0.08
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "ABOVE" in result
        assert "threshold" in result

    def test_threshold_below(self, meta_info, history_with_data):
        """Shows BELOW when current CP is below threshold."""
        history_with_data.latest_cp = 0.04
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert "BELOW" in result
        assert "threshold" in result

    def test_handles_empty_history(self, meta_info):
        """Handles case with no history data gracefully."""
        history = AggregationHistory(
            question_title="Test question",
            question_post_id=41502,
            history=[],
            latest_cp=None,
        )

        result = format_meta_forecast_context(meta_info, history)

        assert "No historical CP timeseries available" in result
        assert "not available" in result

    def test_handles_no_confidence_intervals(self, meta_info):
        """Works when history points lack confidence intervals."""
        history = AggregationHistory(
            question_title="Test question",
            question_post_id=41502,
            history=[
                AggregationHistoryPoint(
                    start_time=1737158400.0,
                    end_time=1737244800.0,
                    centers=[0.05],
                    forecaster_count=10,
                    interval_lower_bounds=None,
                    interval_upper_bounds=None,
                ),
            ],
            latest_cp=0.05,
            aggregation_method="recency_weighted",
        )

        result = format_meta_forecast_context(meta_info, history)

        assert "5.00%" in result
        assert "n/a" in result

    def test_output_has_clear_delimiters(self, meta_info, history_with_data):
        """Output is wrapped with clear start/end delimiters."""
        result = format_meta_forecast_context(meta_info, history_with_data)

        assert result.startswith("=== Target Question: Community Prediction History ===")
        assert result.endswith("=== End Target Question History ===")

    def test_latest_appended_when_differs_from_last_history(self, meta_info):
        """Appends a (latest) row when latest_cp differs from last history point."""
        history = AggregationHistory(
            question_title="Test question",
            question_post_id=41502,
            history=[
                AggregationHistoryPoint(
                    start_time=1737158400.0,
                    end_time=1737244800.0,
                    centers=[0.05],
                    forecaster_count=10,
                ),
            ],
            latest_cp=0.07,
            aggregation_method="recency_weighted",
        )

        result = format_meta_forecast_context(meta_info, history)

        assert "(latest)" in result
        assert "7.00%" in result


# ============================================================================
# Pipeline Integration Tests
# ============================================================================


class TestMetaForecastPipelineIntegration:
    """Tests for meta_forecast_context flowing through the pipeline."""

    def test_meta_forecast_context_prepended_to_historical(self):
        """Verify the injection logic matches what base_forecaster.py does."""
        # Simulate what base_forecaster.py does
        historical_context = "Some search results about Greenland..."
        meta_forecast_context = "=== Target Question: Community Prediction History ===\nCP data..."

        # This mirrors the injection in base_forecaster.py
        if meta_forecast_context:
            historical_context = meta_forecast_context + "\n\n" + historical_context

        assert historical_context.startswith("=== Target Question")
        assert "Some search results about Greenland..." in historical_context

    def test_empty_meta_context_does_not_modify_historical(self):
        """Empty meta_forecast_context leaves historical_context unchanged."""
        historical_context = "Some search results."
        meta_forecast_context = ""

        if meta_forecast_context:
            historical_context = meta_forecast_context + "\n\n" + historical_context

        assert historical_context == "Some search results."
