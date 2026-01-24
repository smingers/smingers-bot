"""
Tests for the ensemble aggregator.
"""

import pytest
from src.ensemble.aggregator import (
    EnsembleAggregator,
    AgentPrediction,
    AggregationResult,
)


class TestBinaryAggregation:
    """Test binary prediction aggregation."""

    def test_weighted_average_basic(self):
        """Test basic weighted average."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=0.6,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.4,
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        assert result.final_prediction == pytest.approx(0.5, abs=0.001)

    def test_weighted_average_unequal_weights(self):
        """Test weighted average with different weights."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=2.0,
                prediction=0.8,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.2,
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        # (0.8 * 2 + 0.2 * 1) / 3 = 1.8 / 3 = 0.6
        assert result.final_prediction == pytest.approx(0.6, abs=0.001)

    def test_median_aggregation(self):
        """Test median aggregation ignores weights."""
        aggregator = EnsembleAggregator(method="median")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=10.0,  # High weight should be ignored
                prediction=0.9,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.5,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent3",
                model="test",
                weight=1.0,
                prediction=0.1,
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        assert result.final_prediction == pytest.approx(0.5, abs=0.001)

    def test_trimmed_mean(self):
        """Test trimmed mean removes outliers."""
        aggregator = EnsembleAggregator(method="trimmed_mean")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=0.99,  # Outlier high
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.5,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent3",
                model="test",
                weight=1.0,
                prediction=0.6,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent4",
                model="test",
                weight=1.0,
                prediction=0.01,  # Outlier low
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        # Should average 0.5 and 0.6 after removing 0.01 and 0.99
        assert result.final_prediction == pytest.approx(0.55, abs=0.001)

    def test_bounds_enforced(self):
        """Test that predictions are bounded to [0.001, 0.999]."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=1.0,  # Would exceed 0.999
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        assert result.final_prediction <= 0.999
        assert result.final_prediction >= 0.001

    def test_single_prediction(self):
        """Test with single prediction."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=0.75,
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        assert result.final_prediction == pytest.approx(0.75, abs=0.001)
        assert result.std_dev == 0.0  # Single prediction has no std dev

    def test_empty_predictions_raises(self):
        """Test that empty predictions raises ValueError."""
        aggregator = EnsembleAggregator(method="weighted_average")
        with pytest.raises(ValueError, match="No predictions"):
            aggregator.aggregate_binary([])

    def test_statistics_computed(self):
        """Test that ensemble statistics are computed correctly."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=0.3,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.5,
                reasoning="test",
            ),
            AgentPrediction(
                agent_name="agent3",
                model="test",
                weight=1.0,
                prediction=0.7,
                reasoning="test",
            ),
        ]
        result = aggregator.aggregate_binary(predictions)
        assert result.mean == pytest.approx(0.5, abs=0.001)
        assert result.median == pytest.approx(0.5, abs=0.001)
        assert result.min_prediction == pytest.approx(0.3, abs=0.001)
        assert result.max_prediction == pytest.approx(0.7, abs=0.001)
        assert result.std_dev > 0


class TestMultipleChoiceAggregation:
    """Test multiple choice prediction aggregation."""

    def test_basic_distribution_aggregation(self):
        """Test basic distribution aggregation."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=0.5,
                reasoning="test",
                prediction_distribution={"A": 0.5, "B": 0.3, "C": 0.2},
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.4,
                reasoning="test",
                prediction_distribution={"A": 0.3, "B": 0.5, "C": 0.2},
            ),
        ]
        result = aggregator.aggregate_multiple_choice(predictions)
        # Should average: A=(0.5+0.3)/2=0.4, B=(0.3+0.5)/2=0.4, C=(0.2+0.2)/2=0.2
        assert result.final_distribution is not None
        assert result.final_distribution["A"] == pytest.approx(0.4, abs=0.01)
        assert result.final_distribution["B"] == pytest.approx(0.4, abs=0.01)
        assert result.final_distribution["C"] == pytest.approx(0.2, abs=0.01)

    def test_distribution_normalized(self):
        """Test that final distribution sums to 1."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=0.5,
                reasoning="test",
                prediction_distribution={"A": 0.6, "B": 0.4},
            ),
        ]
        result = aggregator.aggregate_multiple_choice(predictions)
        total = sum(result.final_distribution.values())
        assert total == pytest.approx(1.0, abs=0.001)

    def test_weighted_distribution(self):
        """Test weighted distribution aggregation."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=2.0,  # Double weight
                prediction=0.8,
                reasoning="test",
                prediction_distribution={"A": 0.8, "B": 0.2},
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=0.5,
                reasoning="test",
                prediction_distribution={"A": 0.2, "B": 0.8},
            ),
        ]
        result = aggregator.aggregate_multiple_choice(predictions)
        # A = (0.8*2 + 0.2*1) / 3 = 1.8/3 = 0.6
        # B = (0.2*2 + 0.8*1) / 3 = 1.2/3 = 0.4
        assert result.final_distribution["A"] == pytest.approx(0.6, abs=0.01)
        assert result.final_distribution["B"] == pytest.approx(0.4, abs=0.01)


class TestNumericAggregation:
    """Test numeric prediction aggregation."""

    def test_percentile_aggregation(self):
        """Test percentile aggregation."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=100,
                reasoning="test",
                percentiles={50: 100, 25: 80, 75: 120},
            ),
            AgentPrediction(
                agent_name="agent2",
                model="test",
                weight=1.0,
                prediction=200,
                reasoning="test",
                percentiles={50: 200, 25: 180, 75: 220},
            ),
        ]
        result = aggregator.aggregate_numeric(predictions)
        # Median should be average of 100 and 200
        assert result.final_prediction == pytest.approx(150, abs=1)

    def test_cdf_generated(self):
        """Test that CDF is generated with correct length."""
        aggregator = EnsembleAggregator(method="weighted_average")
        predictions = [
            AgentPrediction(
                agent_name="agent1",
                model="test",
                weight=1.0,
                prediction=50,
                reasoning="test",
                percentiles={1: 10, 50: 50, 99: 90},
            ),
        ]
        result = aggregator.aggregate_numeric(predictions, num_points=201)
        assert result.final_cdf is not None
        assert len(result.final_cdf) == 201


class TestEnsembleStatistics:
    """Test ensemble statistics calculation."""

    def test_agreement_score(self):
        """Test agreement score calculation."""
        aggregator = EnsembleAggregator()

        # High agreement
        high_agreement = [
            AgentPrediction(agent_name="a1", model="t", weight=1.0, prediction=0.50, reasoning=""),
            AgentPrediction(agent_name="a2", model="t", weight=1.0, prediction=0.51, reasoning=""),
            AgentPrediction(agent_name="a3", model="t", weight=1.0, prediction=0.49, reasoning=""),
        ]
        stats_high = aggregator.get_ensemble_statistics(high_agreement)

        # Low agreement
        low_agreement = [
            AgentPrediction(agent_name="a1", model="t", weight=1.0, prediction=0.1, reasoning=""),
            AgentPrediction(agent_name="a2", model="t", weight=1.0, prediction=0.5, reasoning=""),
            AgentPrediction(agent_name="a3", model="t", weight=1.0, prediction=0.9, reasoning=""),
        ]
        stats_low = aggregator.get_ensemble_statistics(low_agreement)

        assert stats_high["agreement_score"] > stats_low["agreement_score"]
        assert stats_high["range"] < stats_low["range"]
