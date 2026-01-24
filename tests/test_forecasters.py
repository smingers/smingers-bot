"""
Tests for forecaster probability/percentile extraction.
"""

import pytest
from src.bot.binary import BinaryForecaster
from src.bot.numeric import NumericForecaster


class TestBinaryProbabilityExtraction:
    """Test probability extraction from LLM responses."""

    @pytest.fixture
    def forecaster(self):
        return BinaryForecaster(config={})

    def test_extract_probability_standard_format(self, forecaster):
        """Test standard 'Probability: X%' format."""
        text = """
        Based on my analysis...

        Probability: 75%

        This reflects the likelihood...
        """
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.75, abs=0.001)

    def test_extract_probability_markdown_bold(self, forecaster):
        """Test markdown bold format."""
        text = "After consideration, **Probability:** 42%"
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.42, abs=0.001)

    def test_extract_probability_base_rate(self, forecaster):
        """Test 'Base Rate Estimate' format."""
        text = "Base Rate Estimate: 30%"
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.30, abs=0.001)

    def test_extract_probability_final_estimate(self, forecaster):
        """Test 'Final Estimate' format."""
        text = "Final Estimate: 65%"
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.65, abs=0.001)

    def test_extract_probability_final_probability(self, forecaster):
        """Test 'Final Probability' format."""
        text = "Final Probability: 88%"
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.88, abs=0.001)

    def test_extract_probability_decimal(self, forecaster):
        """Test decimal percentage."""
        text = "Probability: 33.5%"
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.335, abs=0.001)

    def test_extract_probability_fallback_last_percentage(self, forecaster):
        """Test fallback to last percentage in text."""
        text = """
        Historical rate is about 20%.
        Current conditions suggest 35%.
        Adjusting for factors, I estimate 45%.
        """
        prob = forecaster._extract_probability(text)
        assert prob == pytest.approx(0.45, abs=0.001)

    def test_extract_probability_bounds_low(self, forecaster):
        """Test that probability is bounded above 0.001."""
        text = "Probability: 0%"
        prob = forecaster._extract_probability(text)
        assert prob >= 0.001

    def test_extract_probability_bounds_high(self, forecaster):
        """Test that probability is bounded below 0.999."""
        text = "Probability: 100%"
        prob = forecaster._extract_probability(text)
        assert prob <= 0.999

    def test_extract_probability_default(self, forecaster):
        """Test default when no probability found."""
        text = "No probability mentioned here at all."
        prob = forecaster._extract_probability(text)
        assert prob == 0.5  # Default

    def test_extract_reference_classes(self, forecaster):
        """Test reference class extraction."""
        # Test numbered format that the code looks for
        text = """
        Reference Class 1: Historical treaty negotiations
        Reference Class 2: UN resolutions on similar topics
        Reference Class 3: Previous diplomatic agreements
        """
        classes = forecaster._extract_reference_classes(text)
        assert len(classes) >= 1
        assert any("treaty" in c.lower() or "diplomatic" in c.lower() for c in classes)

    def test_extract_confidence(self, forecaster):
        """Test confidence extraction."""
        text = "Confidence Level: 7"
        conf = forecaster._extract_confidence(text)
        assert conf == 7

    def test_extract_confidence_with_ten(self, forecaster):
        """Test confidence extraction with /10 format."""
        text = "Confidence: 8/10"
        conf = forecaster._extract_confidence(text)
        assert conf == 8

    def test_extract_confidence_bounded(self, forecaster):
        """Test confidence is bounded 1-10."""
        text = "Confidence Level: 15"  # Too high
        conf = forecaster._extract_confidence(text)
        assert 1 <= conf <= 10


class TestNumericPercentileExtraction:
    """Test percentile extraction from LLM responses."""

    @pytest.fixture
    def forecaster(self):
        return NumericForecaster(config={})

    def test_extract_percentile_standard(self, forecaster):
        """Test standard 'Percentile X: Y' format."""
        text = """
        Percentile 50: 100
        Percentile 25: 80
        Percentile 75: 120
        """
        pcts = forecaster._extract_percentiles(text)
        assert pcts[50] == pytest.approx(100, abs=0.1)
        assert pcts[25] == pytest.approx(80, abs=0.1)
        assert pcts[75] == pytest.approx(120, abs=0.1)

    def test_extract_percentile_ordinal(self, forecaster):
        """Test ordinal format '50th percentile: Y'."""
        text = """
        1st percentile: 10
        50th percentile: 100
        99th percentile: 200
        """
        pcts = forecaster._extract_percentiles(text)
        assert pcts[1] == pytest.approx(10, abs=0.1)
        assert pcts[50] == pytest.approx(100, abs=0.1)
        assert pcts[99] == pytest.approx(200, abs=0.1)

    def test_extract_percentile_p_format(self, forecaster):
        """Test 'PX: Y' format."""
        text = """
        P1: 5
        P50: 50
        P99: 95
        """
        pcts = forecaster._extract_percentiles(text)
        assert pcts[1] == pytest.approx(5, abs=0.1)
        assert pcts[50] == pytest.approx(50, abs=0.1)
        assert pcts[99] == pytest.approx(95, abs=0.1)

    def test_extract_percentile_with_commas(self, forecaster):
        """Test number parsing with thousands separators."""
        text = "Percentile 50: 1,234,567"
        pcts = forecaster._extract_percentiles(text)
        assert pcts[50] == pytest.approx(1234567, abs=1)

    def test_extract_percentile_scientific(self, forecaster):
        """Test scientific notation."""
        text = "Percentile 50: 1.5e6"
        pcts = forecaster._extract_percentiles(text)
        assert pcts[50] == pytest.approx(1500000, abs=1)

    def test_extract_percentile_negative(self, forecaster):
        """Test negative values."""
        text = "Percentile 50: -25.5"
        pcts = forecaster._extract_percentiles(text)
        assert pcts[50] == pytest.approx(-25.5, abs=0.1)

    def test_extract_percentile_equals_sign(self, forecaster):
        """Test with equals sign instead of colon."""
        text = "Percentile 50 = 100"
        pcts = forecaster._extract_percentiles(text)
        assert pcts[50] == pytest.approx(100, abs=0.1)

    def test_only_standard_percentiles_extracted(self, forecaster):
        """Test that only standard percentiles are extracted."""
        text = """
        Percentile 50: 100
        Percentile 33: 80
        """
        pcts = forecaster._extract_percentiles(text)
        assert 50 in pcts
        assert 33 not in pcts  # 33 is not a standard percentile

    def test_format_bounds(self, forecaster):
        """Test bounds formatting for prompts."""
        bounds = forecaster._format_bounds(0, 100, "units")
        assert "Lower bound: 0" in bounds
        assert "Upper bound: 100" in bounds

    def test_format_bounds_none(self, forecaster):
        """Test bounds formatting with no bounds."""
        bounds = forecaster._format_bounds(None, None, "")
        assert "No explicit bounds" in bounds


class TestCDFGeneration:
    """Test CDF generation for numeric questions."""

    @pytest.fixture
    def forecaster(self):
        return NumericForecaster(config={})

    def test_cdf_length(self, forecaster):
        """Test CDF has correct length (201 points)."""
        percentiles = {1: 10, 25: 40, 50: 50, 75: 60, 99: 90}
        cdf = forecaster._generate_cdf(
            percentiles=percentiles,
            lower_bound=0,
            upper_bound=100,
            open_lower_bound=True,
            open_upper_bound=True,
        )
        assert len(cdf) == 201

    def test_cdf_monotonicity(self, forecaster):
        """Test CDF is monotonically non-decreasing."""
        percentiles = {1: 10, 25: 40, 50: 50, 75: 60, 99: 90}
        cdf = forecaster._generate_cdf(
            percentiles=percentiles,
            lower_bound=0,
            upper_bound=100,
            open_lower_bound=True,
            open_upper_bound=True,
        )
        for i in range(1, len(cdf)):
            assert cdf[i] >= cdf[i - 1], f"CDF not monotonic at index {i}"

    def test_cdf_bounds_open(self, forecaster):
        """Test CDF bounds with open bounds."""
        percentiles = {1: 10, 50: 50, 99: 90}
        cdf = forecaster._generate_cdf(
            percentiles=percentiles,
            lower_bound=0,
            upper_bound=100,
            open_lower_bound=True,
            open_upper_bound=True,
        )
        assert cdf[0] >= 0.001
        assert cdf[-1] <= 0.999

    def test_cdf_bounds_closed(self, forecaster):
        """Test CDF bounds with closed bounds."""
        percentiles = {1: 10, 50: 50, 99: 90}
        cdf = forecaster._generate_cdf(
            percentiles=percentiles,
            lower_bound=0,
            upper_bound=100,
            open_lower_bound=False,
            open_upper_bound=False,
        )
        assert cdf[0] >= 0.0
        assert cdf[-1] <= 1.0

    def test_cdf_max_step_size(self, forecaster):
        """Test CDF respects max step size of 0.59."""
        percentiles = {1: 10, 50: 50, 99: 90}
        cdf = forecaster._generate_cdf(
            percentiles=percentiles,
            lower_bound=0,
            upper_bound=100,
            open_lower_bound=True,
            open_upper_bound=True,
        )
        for i in range(1, len(cdf)):
            step = cdf[i] - cdf[i - 1]
            assert step <= 0.59 + 0.001, f"Step size {step} exceeds 0.59 at index {i}"

    def test_cdf_empty_percentiles_fallback(self, forecaster):
        """Test CDF with empty percentiles uses uniform fallback."""
        cdf = forecaster._generate_cdf(
            percentiles={},
            lower_bound=0,
            upper_bound=100,
            open_lower_bound=True,
            open_upper_bound=True,
        )
        assert len(cdf) == 201
        # Should be roughly uniform
        assert cdf[0] < 0.1
        assert cdf[-1] > 0.9


class TestPercentileAggregation:
    """Test percentile aggregation across agents."""

    @pytest.fixture
    def forecaster(self):
        return NumericForecaster(config={})

    def test_aggregate_percentiles_basic(self, forecaster):
        """Test basic percentile aggregation."""
        from src.ensemble.aggregator import AgentPrediction

        predictions = [
            AgentPrediction(
                agent_name="a1",
                model="test",
                weight=1.0,
                prediction=100,
                reasoning="",
                percentiles={50: 100, 25: 80},
            ),
            AgentPrediction(
                agent_name="a2",
                model="test",
                weight=1.0,
                prediction=200,
                reasoning="",
                percentiles={50: 200, 25: 180},
            ),
        ]
        result = forecaster._aggregate_percentiles(predictions)
        assert result[50] == pytest.approx(150, abs=1)
        assert result[25] == pytest.approx(130, abs=1)

    def test_aggregate_percentiles_weighted(self, forecaster):
        """Test weighted percentile aggregation."""
        from src.ensemble.aggregator import AgentPrediction

        predictions = [
            AgentPrediction(
                agent_name="a1",
                model="test",
                weight=2.0,  # Double weight
                prediction=100,
                reasoning="",
                percentiles={50: 100},
            ),
            AgentPrediction(
                agent_name="a2",
                model="test",
                weight=1.0,
                prediction=200,
                reasoning="",
                percentiles={50: 200},
            ),
        ]
        result = forecaster._aggregate_percentiles(predictions)
        # (100*2 + 200*1) / 3 = 400/3 ≈ 133.33
        assert result[50] == pytest.approx(133.33, abs=1)
