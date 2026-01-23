"""
Ensemble Aggregator

Combines predictions from multiple agents using various aggregation methods.
"""

import statistics
from typing import Optional, Literal
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentPrediction:
    """A prediction from a single agent."""
    agent_name: str
    model: str
    weight: float
    prediction: float  # For binary, this is the probability
    reasoning: str
    evidence_weights: Optional[dict] = None

    # For multiple choice, prediction is the full distribution
    prediction_distribution: Optional[dict[str, float]] = None

    # For numeric, prediction is the median + percentiles
    percentiles: Optional[dict[int, float]] = None


@dataclass
class AggregationResult:
    """Result of aggregating multiple predictions."""
    final_prediction: float
    method: str
    individual_predictions: list[AgentPrediction]
    weights_used: list[float]

    # Statistics about the ensemble
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    min_prediction: float = 0.0
    max_prediction: float = 0.0

    # For multiple choice
    final_distribution: Optional[dict[str, float]] = None

    # For numeric
    final_cdf: Optional[list[float]] = None


class EnsembleAggregator:
    """
    Aggregates predictions from multiple agents.

    Supports multiple aggregation methods:
    - weighted_average: Sum of (prediction * weight) / sum of weights
    - median: Middle value (ignores weights)
    - trimmed_mean: Average after removing outliers
    """

    def __init__(self, method: str = "weighted_average"):
        self.method = method

    def aggregate_binary(
        self,
        predictions: list[AgentPrediction],
    ) -> AggregationResult:
        """
        Aggregate binary predictions.

        Args:
            predictions: List of agent predictions

        Returns:
            AggregationResult with final prediction
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")

        pred_values = [p.prediction for p in predictions]
        weights = [p.weight for p in predictions]

        # Calculate statistics
        mean_pred = statistics.mean(pred_values)
        median_pred = statistics.median(pred_values)
        std_dev = statistics.stdev(pred_values) if len(pred_values) > 1 else 0.0

        # Calculate final prediction based on method
        if self.method == "weighted_average":
            total_weight = sum(weights)
            final_pred = sum(p * w for p, w in zip(pred_values, weights)) / total_weight

        elif self.method == "median":
            final_pred = median_pred

        elif self.method == "trimmed_mean":
            # Remove highest and lowest, then average
            if len(pred_values) > 2:
                sorted_preds = sorted(pred_values)
                trimmed = sorted_preds[1:-1]
                final_pred = statistics.mean(trimmed)
            else:
                final_pred = mean_pred

        else:
            logger.warning(f"Unknown aggregation method: {self.method}, using weighted_average")
            total_weight = sum(weights)
            final_pred = sum(p * w for p, w in zip(pred_values, weights)) / total_weight

        # Ensure bounds
        final_pred = max(0.001, min(0.999, final_pred))

        return AggregationResult(
            final_prediction=final_pred,
            method=self.method,
            individual_predictions=predictions,
            weights_used=weights,
            mean=mean_pred,
            median=median_pred,
            std_dev=std_dev,
            min_prediction=min(pred_values),
            max_prediction=max(pred_values),
        )

    def aggregate_multiple_choice(
        self,
        predictions: list[AgentPrediction],
    ) -> AggregationResult:
        """
        Aggregate multiple choice predictions.

        Each agent provides a probability distribution over options.
        We combine these using weighted averaging.
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")

        # Get all option keys
        all_options = set()
        for p in predictions:
            if p.prediction_distribution:
                all_options.update(p.prediction_distribution.keys())

        # Aggregate by option
        final_distribution: dict[str, float] = {}
        total_weight = sum(p.weight for p in predictions)

        for option in all_options:
            weighted_sum = 0.0
            for p in predictions:
                if p.prediction_distribution:
                    prob = p.prediction_distribution.get(option, 0.0)
                    weighted_sum += prob * p.weight
            final_distribution[option] = weighted_sum / total_weight

        # Normalize to sum to 1
        total_prob = sum(final_distribution.values())
        if total_prob > 0:
            final_distribution = {k: v / total_prob for k, v in final_distribution.items()}

        # Get the most likely option as the "prediction"
        best_option = max(final_distribution.items(), key=lambda x: x[1])
        final_pred = best_option[1]

        return AggregationResult(
            final_prediction=final_pred,
            method=self.method,
            individual_predictions=predictions,
            weights_used=[p.weight for p in predictions],
            mean=final_pred,
            median=final_pred,
            std_dev=0.0,
            min_prediction=min(final_distribution.values()),
            max_prediction=max(final_distribution.values()),
            final_distribution=final_distribution,
        )

    def aggregate_numeric(
        self,
        predictions: list[AgentPrediction],
        num_points: int = 201,
    ) -> AggregationResult:
        """
        Aggregate numeric predictions (CDFs).

        Each agent provides percentile estimates.
        We combine these into a final CDF.
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")

        # Standard percentiles we expect
        standard_percentiles = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
                                55, 60, 65, 70, 75, 80, 85, 90, 95, 99]

        # Aggregate each percentile
        aggregated_percentiles: dict[int, float] = {}
        total_weight = sum(p.weight for p in predictions)

        for pct in standard_percentiles:
            weighted_sum = 0.0
            for p in predictions:
                if p.percentiles and pct in p.percentiles:
                    weighted_sum += p.percentiles[pct] * p.weight
            aggregated_percentiles[pct] = weighted_sum / total_weight

        # Interpolate to full CDF
        final_cdf = self._interpolate_cdf(aggregated_percentiles, num_points)

        # Median as the "prediction"
        median_pred = aggregated_percentiles.get(50, 0.5)

        return AggregationResult(
            final_prediction=median_pred,
            method=self.method,
            individual_predictions=predictions,
            weights_used=[p.weight for p in predictions],
            mean=median_pred,
            median=median_pred,
            std_dev=0.0,
            min_prediction=aggregated_percentiles.get(1, 0.0),
            max_prediction=aggregated_percentiles.get(99, 1.0),
            final_cdf=final_cdf,
        )

    def _interpolate_cdf(
        self,
        percentiles: dict[int, float],
        num_points: int = 201,
    ) -> list[float]:
        """
        Interpolate percentile estimates to a full CDF.

        Uses linear interpolation between known percentiles.
        """
        # Sort percentiles
        sorted_pcts = sorted(percentiles.items())

        # Create full CDF
        cdf = []
        for i in range(num_points):
            # Map index to percentile (0-100)
            target_pct = (i / (num_points - 1)) * 100

            # Find surrounding percentiles
            lower_pct = None
            upper_pct = None
            for pct, val in sorted_pcts:
                if pct <= target_pct:
                    lower_pct = (pct, val)
                if pct >= target_pct and upper_pct is None:
                    upper_pct = (pct, val)

            # Interpolate
            if lower_pct is None:
                cdf.append(sorted_pcts[0][1] if sorted_pcts else 0.0)
            elif upper_pct is None:
                cdf.append(sorted_pcts[-1][1] if sorted_pcts else 1.0)
            elif lower_pct[0] == upper_pct[0]:
                cdf.append(lower_pct[1])
            else:
                # Linear interpolation
                t = (target_pct - lower_pct[0]) / (upper_pct[0] - lower_pct[0])
                cdf.append(lower_pct[1] + t * (upper_pct[1] - lower_pct[1]))

        # Ensure monotonicity
        for i in range(1, len(cdf)):
            if cdf[i] < cdf[i - 1]:
                cdf[i] = cdf[i - 1]

        # Ensure bounds
        cdf[0] = max(0.001, cdf[0])
        cdf[-1] = min(0.999, cdf[-1])

        return cdf

    def get_ensemble_statistics(
        self,
        predictions: list[AgentPrediction],
    ) -> dict:
        """
        Get statistics about ensemble agreement.

        Useful for deciding whether to submit (high disagreement might indicate uncertainty).
        """
        if not predictions:
            return {}

        pred_values = [p.prediction for p in predictions]

        return {
            "num_agents": len(predictions),
            "mean": statistics.mean(pred_values),
            "median": statistics.median(pred_values),
            "std_dev": statistics.stdev(pred_values) if len(pred_values) > 1 else 0.0,
            "range": max(pred_values) - min(pred_values),
            "min": min(pred_values),
            "max": max(pred_values),
            "agreement_score": 1.0 - (statistics.stdev(pred_values) if len(pred_values) > 1 else 0.0),
        }
