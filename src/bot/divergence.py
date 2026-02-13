"""
Divergence Metrics for Ensemble Predictions

Computes whether forecasters disagree enough to warrant supervisor review.
Each question type has its own metric:
- Binary: Standard deviation of probabilities (percentage points)
- Numeric: Coefficient of variation of median estimates
- Multiple Choice: Max per-option range across forecasters (percentage points)
"""

import logging
import statistics
from dataclasses import dataclass

from src.bot.extractors import AgentResult

logger = logging.getLogger(__name__)


@dataclass
class DivergenceMetrics:
    """Divergence analysis for an ensemble's predictions."""

    should_trigger_supervisor: bool
    metric_name: str  # "std_dev", "cv", "max_option_range"
    metric_value: float
    threshold: float
    detail: str  # Human-readable description


def compute_binary_divergence(
    probabilities: list[float | None],
    threshold: float = 15.0,
) -> DivergenceMetrics:
    """
    Standard deviation of forecaster probabilities (percentage points).

    Args:
        probabilities: List of probabilities as percentages (0-100).
            None values are excluded.
        threshold: Std dev threshold in percentage points to trigger supervisor.

    Returns:
        DivergenceMetrics with std_dev metric.
    """
    valid = [p for p in probabilities if p is not None]
    if len(valid) < 2:
        return DivergenceMetrics(
            should_trigger_supervisor=False,
            metric_name="std_dev",
            metric_value=0.0,
            threshold=threshold,
            detail=f"Too few valid predictions ({len(valid)})",
        )

    std_dev = statistics.stdev(valid)
    return DivergenceMetrics(
        should_trigger_supervisor=std_dev >= threshold,
        metric_name="std_dev",
        metric_value=round(std_dev, 2),
        threshold=threshold,
        detail=f"std_dev={std_dev:.1f}pp (threshold={threshold:.1f}pp)",
    )


def compute_numeric_divergence(
    percentile_dicts: list[dict[int, float] | None],
    threshold: float = 0.25,
) -> DivergenceMetrics:
    """
    Coefficient of variation (CV) of median estimates across forecasters.

    CV = std_dev(medians) / abs(mean(medians)).
    Uses percentile 50 if available, otherwise interpolates from nearest keys.

    Args:
        percentile_dicts: List of percentile dicts (key: percentile, value: estimate).
            None values are excluded.
        threshold: CV threshold to trigger supervisor.

    Returns:
        DivergenceMetrics with cv metric.
    """
    medians = []
    for pct_dict in percentile_dicts:
        if pct_dict is None:
            continue
        median = _extract_median(pct_dict)
        if median is not None:
            medians.append(median)

    if len(medians) < 2:
        return DivergenceMetrics(
            should_trigger_supervisor=False,
            metric_name="cv",
            metric_value=0.0,
            threshold=threshold,
            detail=f"Too few valid medians ({len(medians)})",
        )

    mean_val = statistics.mean(medians)
    if abs(mean_val) < 1e-10:
        return DivergenceMetrics(
            should_trigger_supervisor=False,
            metric_name="cv",
            metric_value=0.0,
            threshold=threshold,
            detail="Mean is near zero, CV undefined",
        )

    std_dev = statistics.stdev(medians)
    cv = std_dev / abs(mean_val)
    return DivergenceMetrics(
        should_trigger_supervisor=cv >= threshold,
        metric_name="cv",
        metric_value=round(cv, 4),
        threshold=threshold,
        detail=f"cv={cv:.3f} (threshold={threshold:.3f})",
    )


def compute_multiple_choice_divergence(
    probability_lists: list[list[float] | None],
    threshold: float = 20.0,
) -> DivergenceMetrics:
    """
    Maximum per-option range across forecasters (percentage points).

    For each option, compute max(forecaster_probs) - min(forecaster_probs),
    then take the maximum range across all options.

    Args:
        probability_lists: List of per-forecaster probability lists.
            None values are excluded. Each inner list has one entry per option.
        threshold: Max option range threshold in pp to trigger supervisor.

    Returns:
        DivergenceMetrics with max_option_range metric.
    """
    valid = [p for p in probability_lists if p is not None]
    if len(valid) < 2:
        return DivergenceMetrics(
            should_trigger_supervisor=False,
            metric_name="max_option_range",
            metric_value=0.0,
            threshold=threshold,
            detail=f"Too few valid predictions ({len(valid)})",
        )

    # All lists should have the same length (number of options)
    num_options = len(valid[0])

    # Detect scale: if all values are <= 1.0, they're 0-1 normalized; convert to pp
    all_values = [v for p in valid for v in p]
    scale = 100.0 if all_values and max(all_values) <= 1.0 else 1.0

    max_range = 0.0
    for option_idx in range(num_options):
        option_values = [p[option_idx] * scale for p in valid if option_idx < len(p)]
        if len(option_values) >= 2:
            option_range = max(option_values) - min(option_values)
            max_range = max(max_range, option_range)

    return DivergenceMetrics(
        should_trigger_supervisor=max_range >= threshold,
        metric_name="max_option_range",
        metric_value=round(max_range, 2),
        threshold=threshold,
        detail=f"max_option_range={max_range:.1f}pp (threshold={threshold:.1f}pp)",
    )


def compute_divergence(
    question_type: str,
    agent_results: list[AgentResult],
    config: dict | None = None,
) -> DivergenceMetrics:
    """
    Dispatch to type-specific divergence computation.

    Args:
        question_type: "binary", "numeric", or "multiple_choice"
        agent_results: List of AgentResult from the ensemble
        config: Optional config dict with supervisor.divergence_threshold settings

    Returns:
        DivergenceMetrics for the given question type
    """
    thresholds = {}
    if config:
        thresholds = config.get("supervisor", {}).get("divergence_threshold", {})

    if question_type == "binary":
        probabilities = [r.probability for r in agent_results]
        threshold = thresholds.get("binary", 15.0)
        return compute_binary_divergence(probabilities, threshold=threshold)

    elif question_type == "numeric":
        percentile_dicts = [r.percentiles for r in agent_results]
        threshold = thresholds.get("numeric", 0.25)
        return compute_numeric_divergence(percentile_dicts, threshold=threshold)

    elif question_type == "multiple_choice":
        probability_lists = [r.probabilities for r in agent_results]
        threshold = thresholds.get("multiple_choice", 20.0)
        return compute_multiple_choice_divergence(probability_lists, threshold=threshold)

    else:
        return DivergenceMetrics(
            should_trigger_supervisor=False,
            metric_name="unknown",
            metric_value=0.0,
            threshold=0.0,
            detail=f"Unknown question type: {question_type}",
        )


def _extract_median(pct_dict: dict[int, float]) -> float | None:
    """Extract median (P50) from percentile dict, interpolating if needed.

    Handles both int and string keys (JSON deserialization produces string keys).
    """
    # Normalize keys to int
    normalized = {}
    for k, v in pct_dict.items():
        try:
            normalized[int(k)] = float(v)
        except (ValueError, TypeError):
            continue

    if not normalized:
        return None

    if 50 in normalized:
        return normalized[50]

    # Interpolate from nearest surrounding percentiles
    keys = sorted(normalized.keys())
    lower = [k for k in keys if k < 50]
    upper = [k for k in keys if k > 50]

    if lower and upper:
        lo_key = lower[-1]
        hi_key = upper[0]
        lo_val = normalized[lo_key]
        hi_val = normalized[hi_key]
        # Linear interpolation
        frac = (50 - lo_key) / (hi_key - lo_key)
        return lo_val + frac * (hi_val - lo_val)

    # Fall back to closest available
    if keys:
        closest = min(keys, key=lambda k: abs(k - 50))
        return normalized[closest]

    return None
