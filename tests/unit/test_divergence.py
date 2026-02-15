"""Tests for divergence metrics."""

from src.bot.divergence import (
    _extract_median,
    compute_binary_divergence,
    compute_divergence,
    compute_multiple_choice_divergence,
    compute_numeric_divergence,
)
from src.bot.extractors import AgentResult

# =============================================================================
# Binary Divergence
# =============================================================================


class TestBinaryDivergence:
    def test_low_divergence(self):
        """Tight cluster of predictions should NOT trigger."""
        result = compute_binary_divergence([50.0, 52.0, 48.0, 51.0, 49.0], threshold=15.0)
        assert not result.should_trigger_supervisor
        assert result.metric_name == "std_dev"
        assert result.metric_value < 15.0

    def test_high_divergence(self):
        """Wide spread of predictions should trigger."""
        result = compute_binary_divergence([10.0, 50.0, 80.0, 30.0, 70.0], threshold=15.0)
        assert result.should_trigger_supervisor
        assert result.metric_name == "std_dev"
        assert result.metric_value >= 15.0

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        probs = [40.0, 45.0, 50.0, 55.0, 60.0]
        # With threshold 15, this should NOT trigger
        result_high = compute_binary_divergence(probs, threshold=15.0)
        assert not result_high.should_trigger_supervisor

        # With lower threshold (5), this SHOULD trigger
        result_low = compute_binary_divergence(probs, threshold=5.0)
        assert result_low.should_trigger_supervisor

    def test_none_values_excluded(self):
        """None values should be filtered out."""
        result = compute_binary_divergence([50.0, None, 52.0, None, 48.0], threshold=15.0)
        assert not result.should_trigger_supervisor
        assert result.metric_value < 15.0

    def test_single_valid_prediction(self):
        """Single prediction should not trigger."""
        result = compute_binary_divergence([50.0, None, None, None, None], threshold=15.0)
        assert not result.should_trigger_supervisor
        assert result.metric_value == 0.0

    def test_all_none(self):
        """All None should not trigger."""
        result = compute_binary_divergence([None, None, None, None, None], threshold=15.0)
        assert not result.should_trigger_supervisor

    def test_identical_predictions(self):
        """Identical predictions should have zero divergence."""
        result = compute_binary_divergence([50.0, 50.0, 50.0, 50.0, 50.0], threshold=15.0)
        assert not result.should_trigger_supervisor
        assert result.metric_value == 0.0

    def test_extreme_spread(self):
        """1% to 99% spread should trigger."""
        result = compute_binary_divergence([1.0, 99.0, 50.0, 25.0, 75.0], threshold=15.0)
        assert result.should_trigger_supervisor

    def test_real_example(self):
        """Real forecast data: [23, 5, 30, 35, 60]."""
        result = compute_binary_divergence([23.0, 5.0, 30.0, 35.0, 60.0], threshold=15.0)
        # Std dev ≈ 19.7, should trigger at 15pp
        assert result.should_trigger_supervisor

    def test_threshold_stored(self):
        """Threshold should be stored in result."""
        result = compute_binary_divergence([50.0, 52.0], threshold=10.0)
        assert result.threshold == 10.0


# =============================================================================
# Numeric Divergence — Range-Normalized Spread
# =============================================================================


class TestNumericDivergence:
    def test_low_rn_spread(self):
        """Similar medians relative to range should NOT trigger."""
        pcts = [
            {10: 100, 50: 500, 90: 900},
            {10: 110, 50: 510, 90: 910},
            {10: 90, 50: 490, 90: 890},
        ]
        result = compute_numeric_divergence(pcts, threshold=0.045, range_min=0, range_max=1000)
        assert not result.should_trigger_supervisor
        assert result.metric_name == "rn_spread"

    def test_high_rn_spread(self):
        """Large median spread relative to range should trigger."""
        pcts = [
            {10: 100, 50: 200, 90: 300},
            {10: 500, 50: 800, 90: 1100},
            {10: 50, 50: 100, 90: 150},
        ]
        # Medians: 200, 800, 100 -> std_dev ≈ 378, range=1000, rn_spread ≈ 0.378
        result = compute_numeric_divergence(pcts, threshold=0.045, range_min=0, range_max=1000)
        assert result.should_trigger_supervisor
        assert result.metric_name == "rn_spread"

    def test_tsa_scale_question(self):
        """TSA-style question: large values, moderate disagreement on narrow range.

        This is the exact scenario the old CV metric missed: medians around 17M
        with a 2M spread on a 12M-17M range should trigger.
        """
        pcts = [
            {50: 17_500_000},
            {50: 19_000_000},
            {50: 17_000_000},
            {50: 17_100_000},
            {50: 19_300_000},
        ]
        # std_dev ≈ 1.05M, range = 5M, rn_spread ≈ 0.21
        result = compute_numeric_divergence(
            pcts, threshold=0.045, range_min=12_000_000, range_max=17_000_000
        )
        assert result.should_trigger_supervisor
        assert result.metric_name == "rn_spread"
        assert result.metric_value > 0.1

    def test_none_values_excluded(self):
        """None percentile dicts should be filtered."""
        pcts = [{50: 500}, None, {50: 510}]
        result = compute_numeric_divergence(pcts, threshold=0.045, range_min=0, range_max=1000)
        assert not result.should_trigger_supervisor

    def test_single_valid(self):
        """Single prediction should not trigger."""
        result = compute_numeric_divergence(
            [{50: 500}, None, None], threshold=0.045, range_min=0, range_max=1000
        )
        assert not result.should_trigger_supervisor

    def test_interpolation_when_no_p50(self):
        """Should interpolate median from surrounding percentiles."""
        pcts = [
            {40: 400, 60: 600},  # Interpolated P50 = 500
            {40: 410, 60: 610},  # Interpolated P50 = 510
            {40: 390, 60: 590},  # Interpolated P50 = 490
        ]
        result = compute_numeric_divergence(pcts, threshold=0.045, range_min=0, range_max=1000)
        assert result.metric_name == "rn_spread"
        assert result.metric_value < 0.045

    def test_threshold_boundary(self):
        """Exact threshold value should trigger (>=)."""
        # std_dev(medians) / range = 0.045 exactly
        # std_dev([0, x]) = x/sqrt(2), so x/sqrt(2) / 1000 = 0.045
        # x = 0.045 * 1000 * sqrt(2) ≈ 63.64
        pcts = [{50: 500}, {50: 563.64}]
        result = compute_numeric_divergence(pcts, threshold=0.045, range_min=0, range_max=1000)
        assert result.should_trigger_supervisor
        assert result.metric_name == "rn_spread"

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        pcts = [{50: 500}, {50: 520}]
        # std_dev ≈ 14.14, range = 1000, rn_spread ≈ 0.014
        result_high = compute_numeric_divergence(pcts, threshold=0.10, range_min=0, range_max=1000)
        assert not result_high.should_trigger_supervisor

        result_low = compute_numeric_divergence(pcts, threshold=0.01, range_min=0, range_max=1000)
        assert result_low.should_trigger_supervisor


class TestNumericDivergenceFallback:
    """Tests for the CV fallback when range is not available."""

    def test_fallback_when_no_range(self):
        """Without range params, falls back to CV."""
        pcts = [
            {10: 100, 50: 500, 90: 900},
            {10: 110, 50: 510, 90: 910},
        ]
        result = compute_numeric_divergence(pcts, threshold=0.25)
        assert result.metric_name == "rn_spread_fallback_cv"

    def test_fallback_when_equal_range(self):
        """range_min == range_max should fall back to CV."""
        pcts = [{50: 500}, {50: 510}]
        result = compute_numeric_divergence(pcts, threshold=0.25, range_min=100, range_max=100)
        assert result.metric_name == "rn_spread_fallback_cv"

    def test_fallback_zero_mean(self):
        """Near-zero mean should not crash in fallback mode."""
        pcts = [{50: 0.0001}, {50: -0.0001}]
        result = compute_numeric_divergence(pcts, threshold=0.25)
        assert result.metric_name == "rn_spread"
        assert result.metric_value == 0.0

    def test_fallback_high_cv(self):
        """High CV should trigger in fallback mode."""
        pcts = [
            {50: 200},
            {50: 800},
            {50: 100},
        ]
        # mean=366.67, std_dev≈378.6, cv≈1.03 -> well above 0.25
        result = compute_numeric_divergence(pcts, threshold=0.25)
        assert result.metric_name == "rn_spread_fallback_cv"
        assert result.should_trigger_supervisor

    def test_fallback_low_cv(self):
        """Low CV should NOT trigger in fallback mode."""
        pcts = [{50: 500}, {50: 510}]
        # mean=505, std_dev≈7.07, cv≈0.014 -> below 0.25
        result = compute_numeric_divergence(pcts, threshold=0.25)
        assert result.metric_name == "rn_spread_fallback_cv"
        assert not result.should_trigger_supervisor


# =============================================================================
# Multiple Choice Divergence
# =============================================================================


class TestMultipleChoiceDivergence:
    def test_low_divergence(self):
        """Similar distributions should NOT trigger."""
        probs = [
            [60.0, 30.0, 10.0],
            [62.0, 28.0, 10.0],
            [58.0, 32.0, 10.0],
        ]
        result = compute_multiple_choice_divergence(probs, threshold=25.0)
        assert not result.should_trigger_supervisor
        assert result.metric_name == "max_option_range"

    def test_high_divergence(self):
        """Widely different option probabilities should trigger."""
        probs = [
            [80.0, 10.0, 10.0],
            [20.0, 50.0, 30.0],
            [40.0, 40.0, 20.0],
        ]
        result = compute_multiple_choice_divergence(probs, threshold=25.0)
        assert result.should_trigger_supervisor
        # Max range is on option A: 80 - 20 = 60pp
        assert result.metric_value >= 60.0

    def test_none_values_excluded(self):
        """None probability lists should be filtered."""
        probs = [[60.0, 30.0, 10.0], None, [62.0, 28.0, 10.0]]
        result = compute_multiple_choice_divergence(probs, threshold=25.0)
        assert not result.should_trigger_supervisor

    def test_single_valid(self):
        """Single prediction should not trigger."""
        result = compute_multiple_choice_divergence([[60.0, 30.0, 10.0], None], threshold=25.0)
        assert not result.should_trigger_supervisor

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        probs = [
            [50.0, 30.0, 20.0],
            [40.0, 35.0, 25.0],
        ]
        # Threshold 20 — max range = 10 — should NOT trigger
        result_high = compute_multiple_choice_divergence(probs, threshold=20.0)
        assert not result_high.should_trigger_supervisor

        # Lower threshold 5 — should trigger
        result_low = compute_multiple_choice_divergence(probs, threshold=5.0)
        assert result_low.should_trigger_supervisor


# =============================================================================
# Dispatch Function
# =============================================================================


class TestComputeDivergence:
    SAMPLE_CONFIG = {
        "supervisor": {
            "divergence_threshold": {
                "binary": 15.0,
                "numeric": 0.045,
                "multiple_choice": 25.0,
            }
        }
    }

    def _make_result(self, **kwargs) -> AgentResult:
        """Helper to create AgentResult with defaults."""
        defaults = {
            "agent_id": "test",
            "model": "test-model",
            "weight": 1.0,
            "outside_view_output": "",
            "inside_view_output": "",
        }
        defaults.update(kwargs)
        return AgentResult(**defaults)

    def test_binary_dispatch(self):
        """Should dispatch to binary divergence."""
        results = [
            self._make_result(probability=50.0),
            self._make_result(probability=52.0),
        ]
        metrics = compute_divergence("binary", results, config=self.SAMPLE_CONFIG)
        assert metrics.metric_name == "std_dev"

    def test_numeric_dispatch_with_range(self):
        """Should dispatch to numeric divergence with RN spread."""
        results = [
            self._make_result(percentiles={50: 100}),
            self._make_result(percentiles={50: 110}),
        ]
        metrics = compute_divergence(
            "numeric",
            results,
            config=self.SAMPLE_CONFIG,
            range_min=0,
            range_max=1000,
        )
        assert metrics.metric_name == "rn_spread"

    def test_numeric_dispatch_without_range(self):
        """Without range, should fall back to CV."""
        results = [
            self._make_result(percentiles={50: 100}),
            self._make_result(percentiles={50: 110}),
        ]
        metrics = compute_divergence("numeric", results, config=self.SAMPLE_CONFIG)
        assert metrics.metric_name == "rn_spread_fallback_cv"

    def test_multiple_choice_dispatch(self):
        """Should dispatch to multiple choice divergence."""
        results = [
            self._make_result(probabilities=[60.0, 30.0, 10.0]),
            self._make_result(probabilities=[62.0, 28.0, 10.0]),
        ]
        metrics = compute_divergence("multiple_choice", results, config=self.SAMPLE_CONFIG)
        assert metrics.metric_name == "max_option_range"

    def test_unknown_type(self):
        """Unknown question type should not trigger."""
        metrics = compute_divergence("unknown", [], config=self.SAMPLE_CONFIG)
        assert not metrics.should_trigger_supervisor
        assert metrics.metric_name == "unknown"

    def test_config_thresholds(self):
        """Config thresholds should be passed through."""
        config = {
            "supervisor": {
                "divergence_threshold": {
                    "binary": 5.0,
                    "numeric": 0.045,
                    "multiple_choice": 25.0,
                }
            }
        }
        results = [
            self._make_result(probability=50.0),
            self._make_result(probability=55.0),
            self._make_result(probability=60.0),
        ]
        metrics = compute_divergence("binary", results, config=config)
        assert metrics.threshold == 5.0
        assert metrics.should_trigger_supervisor  # std_dev ≈ 5.0, at threshold

    def test_missing_threshold_raises(self):
        """Missing threshold in config should raise KeyError."""
        config = {"supervisor": {"divergence_threshold": {}}}
        results = [
            self._make_result(probability=50.0),
            self._make_result(probability=52.0),
        ]
        import pytest

        with pytest.raises(KeyError):
            compute_divergence("binary", results, config=config)


# =============================================================================
# Median Extraction Helper
# =============================================================================


class TestExtractMedian:
    def test_direct_p50(self):
        assert _extract_median({50: 100.0}) == 100.0

    def test_interpolate(self):
        result = _extract_median({40: 80.0, 60: 120.0})
        assert result == 100.0  # Linear interpolation

    def test_closest_fallback(self):
        result = _extract_median({25: 50.0, 75: 150.0})
        # Interpolated: 50 + (50-25)/(75-25) * (150-50) = 50 + 50 = 100
        assert result == 100.0

    def test_empty_dict(self):
        assert _extract_median({}) is None

    def test_only_lower(self):
        result = _extract_median({10: 100.0, 25: 200.0})
        # Closest to 50 is 25
        assert result == 200.0

    def test_only_upper(self):
        result = _extract_median({75: 300.0, 90: 400.0})
        # Closest to 50 is 75
        assert result == 300.0
