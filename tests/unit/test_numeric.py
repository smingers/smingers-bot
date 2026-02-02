"""
Tests for Numeric forecaster and CDF generation.

Tests cover:
- Percentile extraction
- CDF generation from percentiles
- CDF aggregation
- Bound handling (open/closed)
"""

import pytest

from src.bot.cdf import generate_continuous_cdf
from src.bot.exceptions import ExtractionError, InsufficientPredictionsError
from src.bot.extractors import (
    AgentResult,
    enforce_monotonic_percentiles,
    extract_percentiles_from_response,
)
from src.bot.numeric import NumericForecaster, NumericForecastResult

# ============================================================================
# Percentile Extraction Tests
# ============================================================================


class TestPercentileExtraction:
    """Tests for percentile extraction from LLM responses."""

    def test_extracts_standard_format(self):
        """Extracts percentiles from standard format with Distribution anchor."""
        # The extractor requires "Distribution:" anchor before percentiles
        response = """
Based on my analysis:

Distribution:
Percentile 5: 100
Percentile 25: 200
Percentile 50: 350
Percentile 75: 500
Percentile 95: 800
"""
        percentiles = extract_percentiles_from_response(response)

        assert percentiles[5] == 100
        assert percentiles[25] == 200
        assert percentiles[50] == 350
        assert percentiles[75] == 500
        assert percentiles[95] == 800

    def test_extracts_with_units(self):
        """Extracts percentiles with units in response."""
        response = """
Distribution:
Percentile 5: 100
Percentile 25: 200
Percentile 50: 350
Percentile 75: 500
Percentile 95: 800
"""
        percentiles = extract_percentiles_from_response(response)

        assert percentiles[5] == 100
        assert percentiles[50] == 350
        assert percentiles[95] == 800

    def test_extracts_decimal_values(self):
        """Extracts percentiles with decimal values."""
        response = """
Distribution:
Percentile 5: 0.5
Percentile 25: 1.25
Percentile 50: 2.5
Percentile 75: 3.75
Percentile 95: 5.0
"""
        percentiles = extract_percentiles_from_response(response)

        assert percentiles[5] == 0.5
        assert percentiles[50] == 2.5
        assert percentiles[95] == 5.0

    def test_raises_for_no_percentiles(self):
        """Raises ExtractionError when no percentiles found."""
        response = "I cannot determine the percentiles for this question."

        with pytest.raises(ExtractionError):
            extract_percentiles_from_response(response)

    def test_raises_for_missing_distribution_anchor(self):
        """Raises ExtractionError when Distribution: anchor missing."""
        response = """
P5: 100
P25: 200
P50: 350
P75: 500
P95: 800
"""
        with pytest.raises(ExtractionError):
            extract_percentiles_from_response(response)


# ============================================================================
# Enforce Strict Increasing Tests
# ============================================================================


class TestEnforceStrictIncreasing:
    """Tests for enforce_monotonic_percentiles function."""

    def test_already_increasing(self):
        """Returns unchanged when already strictly increasing."""
        percentiles = {5: 100, 25: 200, 50: 300, 75: 400, 95: 500}

        result = enforce_monotonic_percentiles(percentiles)

        assert result == percentiles

    def test_fixes_equal_values(self):
        """Fixes equal consecutive values."""
        percentiles = {5: 100, 25: 100, 50: 100, 75: 100, 95: 100}

        result = enforce_monotonic_percentiles(percentiles)

        # Should be strictly increasing
        values = [result[k] for k in sorted(result.keys())]
        for i in range(1, len(values)):
            assert values[i] > values[i - 1]

    def test_raises_for_inverted_values(self):
        """Raises ExtractionError for severely inverted values."""
        percentiles = {5: 500, 25: 400, 50: 300, 75: 200, 95: 100}

        with pytest.raises(ExtractionError) as exc_info:
            enforce_monotonic_percentiles(percentiles)

        assert "inverted" in str(exc_info.value).lower()

    def test_handles_empty(self):
        """Handles empty percentiles dict."""
        result = enforce_monotonic_percentiles({})
        assert result == {}


# ============================================================================
# CDF Generation Tests
# ============================================================================


class TestCDFGeneration:
    """Tests for CDF generation from percentiles."""

    def test_generates_201_points(self):
        """Generates 201-point CDF by default."""
        percentiles = {5: 100, 25: 200, 50: 300, 75: 400, 95: 500}

        cdf = generate_continuous_cdf(
            percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=1000,
            lower_bound=0,
            zero_point=None,
        )

        assert len(cdf) == 201

    def test_generates_custom_size(self):
        """Generates CDF with custom size."""
        percentiles = {5: 10, 25: 30, 50: 50, 75: 70, 95: 90}

        cdf = generate_continuous_cdf(
            percentiles,
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100,
            lower_bound=0,
            zero_point=None,
            num_points=102,  # Discrete question size
        )

        assert len(cdf) == 102

    def test_cdf_is_monotonically_increasing(self):
        """Generated CDF is monotonically increasing."""
        percentiles = {5: 100, 25: 200, 50: 300, 75: 400, 95: 500}

        cdf = generate_continuous_cdf(
            percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=1000,
            lower_bound=0,
            zero_point=None,
        )

        for i in range(1, len(cdf)):
            assert cdf[i] >= cdf[i - 1], f"CDF not monotonic at index {i}"

    def test_cdf_bounded_0_to_1(self):
        """CDF values are between 0 and 1."""
        percentiles = {5: 100, 25: 200, 50: 300, 75: 400, 95: 500}

        cdf = generate_continuous_cdf(
            percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=1000,
            lower_bound=0,
            zero_point=None,
        )

        for val in cdf:
            assert 0 <= val <= 1, f"CDF value {val} out of bounds"

    def test_open_bounds_not_at_extremes(self):
        """Open bounds don't have 0.0 or 1.0 at edges."""
        percentiles = {5: 100, 25: 200, 50: 300, 75: 400, 95: 500}

        cdf = generate_continuous_cdf(
            percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=1000,
            lower_bound=0,
            zero_point=None,
        )

        assert cdf[0] > 0, "First CDF value should be > 0 for open lower bound"
        assert cdf[-1] < 1, "Last CDF value should be < 1 for open upper bound"


# ============================================================================
# NumericForecaster Tests
# ============================================================================


class TestNumericForecasterBounds:
    """Tests for NumericForecaster bound handling."""

    def test_get_bounds_explanation_both_open(self):
        """Builds correct messages for both bounds open."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=True,
            open_upper_bound=True,
            lower_bound=0,
            upper_bound=100,
        )

        assert "Both bounds are OPEN" in result["bounds_info"]
        assert "lower bound is 0" in result["bounds_info"]
        assert "upper bound is 100" in result["bounds_info"]

    def test_get_bounds_explanation_both_closed(self):
        """Builds correct messages for both bounds closed."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=False,
            open_upper_bound=False,
            lower_bound=0,
            upper_bound=100,
        )

        assert "Both bounds are CLOSED" in result["bounds_info"]

    def test_get_bounds_explanation_lower_closed(self):
        """Builds correct messages for lower closed, upper open."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=False,
            open_upper_bound=True,
            lower_bound=0,
            upper_bound=100,
        )

        assert "lower bound is CLOSED" in result["bounds_info"]
        assert "upper bound is OPEN" in result["bounds_info"]

    def test_get_bounds_explanation_upper_closed(self):
        """Builds correct messages for lower open, upper closed."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=True,
            open_upper_bound=False,
            lower_bound=0,
            upper_bound=100,
        )

        assert "lower bound is OPEN" in result["bounds_info"]
        assert "upper bound is CLOSED" in result["bounds_info"]

    def test_get_bounds_explanation_with_zero_point(self):
        """Includes zero point when provided."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=True,
            open_upper_bound=True,
            lower_bound=0,
            upper_bound=100,
            zero_point=1.0,
        )

        assert "Zero point: 1.0" in result["bounds_info"]
        assert "logarithmic" in result["bounds_info"]


# ============================================================================
# CDF Aggregation Tests
# ============================================================================


class TestCDFAggregation:
    """Tests for NumericForecaster CDF aggregation."""

    @pytest.fixture
    def forecaster(self):
        """NumericForecaster with minimal config."""
        config = {
            "_active_agents": [],
            "_active_models": {},
        }
        return NumericForecaster(config)

    def test_aggregates_valid_cdfs(self, forecaster):
        """Aggregates multiple valid CDFs."""
        forecaster._cdf_size = 201

        # Create agent results with valid CDFs
        cdf1 = [i / 200 for i in range(201)]  # Linear
        cdf2 = [(i / 200) ** 2 for i in range(201)]  # Quadratic
        cdf3 = [1 - (1 - i / 200) ** 2 for i in range(201)]  # Inverse quadratic

        agent_results = [
            AgentResult(
                agent_id="agent_1",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf1,
            ),
            AgentResult(
                agent_id="agent_2",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf2,
            ),
            AgentResult(
                agent_id="agent_3",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf3,
            ),
        ]

        agents = [
            {"name": "agent_1", "weight": 1.0},
            {"name": "agent_2", "weight": 1.0},
            {"name": "agent_3", "weight": 1.0},
        ]

        result = forecaster._aggregate_results(agent_results, agents, lambda x: None)

        assert len(result) == 201
        # Should be weighted average
        for i in range(201):
            expected = (cdf1[i] + cdf2[i] + cdf3[i]) / 3
            assert abs(result[i] - expected) < 1e-10

    def test_respects_weights(self, forecaster):
        """Aggregation respects agent weights."""
        forecaster._cdf_size = 201

        cdf1 = [0.5] * 201  # All 0.5
        cdf2 = [0.9] * 201  # All 0.9

        agent_results = [
            AgentResult(
                agent_id="agent_1",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf1,
            ),
            AgentResult(
                agent_id="agent_2",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf2,
            ),
            AgentResult(
                agent_id="agent_3",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf2,
            ),  # 3rd with cdf2
        ]

        agents = [
            {"name": "agent_1", "weight": 3.0},  # Weight 3
            {"name": "agent_2", "weight": 1.0},  # Weight 1
            {"name": "agent_3", "weight": 1.0},  # Weight 1
        ]

        result = forecaster._aggregate_results(agent_results, agents, lambda x: None)

        # Weighted average: (0.5 * 3 + 0.9 * 1 + 0.9 * 1) / 5 = 3.3 / 5 = 0.66
        expected = (0.5 * 3 + 0.9 * 1 + 0.9 * 1) / 5
        assert abs(result[0] - expected) < 1e-10

    def test_raises_insufficient_predictions(self, forecaster):
        """Raises when fewer than 3 valid CDFs."""
        forecaster._cdf_size = 201

        cdf1 = [i / 200 for i in range(201)]

        agent_results = [
            AgentResult(
                agent_id="agent_1",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf1,
            ),
            AgentResult(
                agent_id="agent_2",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=None,
                error="Failed",
            ),
            AgentResult(
                agent_id="agent_3",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=None,
                error="Failed",
            ),
        ]

        agents = [
            {"name": "agent_1", "weight": 1.0},
            {"name": "agent_2", "weight": 1.0},
            {"name": "agent_3", "weight": 1.0},
        ]

        with pytest.raises(InsufficientPredictionsError) as exc_info:
            forecaster._aggregate_results(agent_results, agents, lambda x: None)

        assert exc_info.value.valid_count == 1
        assert exc_info.value.total_count == 3

    def test_skips_wrong_size_cdfs(self, forecaster):
        """Skips CDFs with wrong size."""
        forecaster._cdf_size = 201

        cdf_correct = [i / 200 for i in range(201)]
        cdf_wrong = [i / 100 for i in range(102)]  # Wrong size

        agent_results = [
            AgentResult(
                agent_id="agent_1",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf_correct,
            ),
            AgentResult(
                agent_id="agent_2",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf_correct,
            ),
            AgentResult(
                agent_id="agent_3",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf_correct,
            ),
            AgentResult(
                agent_id="agent_4",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                cdf=cdf_wrong,
            ),  # Wrong size
        ]

        agents = [
            {"name": "agent_1", "weight": 1.0},
            {"name": "agent_2", "weight": 1.0},
            {"name": "agent_3", "weight": 1.0},
            {"name": "agent_4", "weight": 1.0},
        ]

        # Should work - only uses correct-sized CDFs
        result = forecaster._aggregate_results(agent_results, agents, lambda x: None)
        assert len(result) == 201


# ============================================================================
# NumericForecastResult Tests
# ============================================================================


class TestNumericForecastResult:
    """Tests for NumericForecastResult dataclass."""

    def test_creates_with_all_fields(self):
        """Creates result with all fields."""
        result = NumericForecastResult(
            final_cdf=[0.5] * 201,
            agent_results=[],
            historical_context="Historical",
            current_context="Current",
        )

        assert len(result.final_cdf) == 201
        assert result.historical_context == "Historical"
        assert result.current_context == "Current"
        assert result.timestamp is not None

    def test_timestamp_auto_generated(self):
        """Timestamp is auto-generated."""
        result = NumericForecastResult(
            final_cdf=[],
            agent_results=[],
            historical_context="",
            current_context="",
        )

        assert result.timestamp is not None
        assert len(result.timestamp) > 0


# ============================================================================
# Extraction to CDF Integration Tests
# ============================================================================


class TestExtractionToCDFIntegration:
    """Integration tests for full extraction → CDF pipeline."""

    def test_full_pipeline(self):
        """Full pipeline from response to CDF."""
        response = """
Analysis of the question...

Distribution:
Percentile 5: 100
Percentile 25: 200
Percentile 50: 350
Percentile 75: 500
Percentile 95: 800
"""
        # Extract
        percentiles = extract_percentiles_from_response(response)
        percentiles = enforce_monotonic_percentiles(percentiles)

        # Generate CDF
        cdf = generate_continuous_cdf(
            percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=1000,
            lower_bound=0,
            zero_point=None,
        )

        # Verify
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)
        for i in range(1, len(cdf)):
            assert cdf[i] >= cdf[i - 1]
