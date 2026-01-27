"""
CDF generation utilities for numeric question forecasting.

This module contains functions for generating 201-point CDFs that satisfy
Metaculus requirements for numeric question submissions.

Key constraints enforced:
- 201 exactly spaced points
- Monotonically increasing
- No single step exceeds 0.59
- Minimum step size enforced
- Open/closed bound handling
"""

import logging
from typing import Dict, List, Optional

import numpy as np
from scipy.interpolate import PchipInterpolator

from .exceptions import CDFGenerationError

logger = logging.getLogger(__name__)


def _safe_cdf_bounds(cdf: np.ndarray, open_lower: bool, open_upper: bool, step: float) -> np.ndarray:
    """
    Enforce Metaculus CDF requirements:
    - For open bounds: cdf[0] >= 0.001, cdf[-1] <= 0.999
    - No single step may exceed 0.59
    """
    # Pin tails to legal open-bound limits
    if open_lower:
        cdf[0] = max(cdf[0], 0.001)
    if open_upper:
        cdf[-1] = min(cdf[-1], 0.999)

    # Enforce the 0.59 maximum step rule
    big_jumps = np.where(np.diff(cdf) > 0.59)[0]
    for idx in big_jumps:
        excess = cdf[idx + 1] - cdf[idx] - 0.59
        # Spread the excess evenly over the remaining points
        span = len(cdf) - idx - 1
        cdf[idx + 1:] -= excess * np.linspace(1, 0, span)
        # Re-monotonise
        cdf[idx + 1:] = np.maximum.accumulate(cdf[idx + 1:])

    return cdf


def generate_continuous_cdf(
    percentile_values: Dict,
    open_upper_bound: bool,
    open_lower_bound: bool,
    upper_bound: float,
    lower_bound: float,
    zero_point: Optional[float] = None,
    *,
    min_step: float = 5.0e-5,
    num_points: int = 201,
) -> List[float]:
    """
    Generate a 201-point continuous CDF with strict enforcement of Metaculus requirements.

    Args:
        percentile_values: Dictionary mapping percentiles (1-99) to values
        open_upper_bound: Whether the upper bound is open
        open_lower_bound: Whether the lower bound is open
        upper_bound: Maximum possible value
        lower_bound: Minimum possible value
        zero_point: Reference point for non-linear scaling
        min_step: Minimum step size between adjacent CDF points
        num_points: Number of points in the output CDF (default: 201)

    Returns:
        List of CDF values (length 201)

    Raises:
        CDFGenerationError: If CDF cannot be generated with given constraints
    """
    # Validate inputs
    if not percentile_values:
        raise CDFGenerationError("Empty percentile values dictionary")

    if upper_bound <= lower_bound:
        raise CDFGenerationError(f"Upper bound ({upper_bound}) must be greater than lower bound ({lower_bound})")

    if zero_point is not None:
        if abs(zero_point - lower_bound) < 1e-6 or abs(zero_point - upper_bound) < 1e-6:
            raise CDFGenerationError(f"zero_point ({zero_point}) too close to bounds [{lower_bound}, {upper_bound}]")

    # Clean and validate percentile values
    pv = {}
    for k, v in percentile_values.items():
        try:
            k_float = float(k)
            v_float = float(v)

            if not (0 < k_float < 100):
                continue  # Skip invalid percentiles

            if not np.isfinite(v_float):
                continue  # Skip non-finite values

            pv[k_float] = v_float
        except (ValueError, TypeError):
            continue  # Skip non-numeric entries

    if len(pv) < 2:
        raise CDFGenerationError(f"Need at least 2 valid percentile points (got {len(pv)})")

    # Handle duplicate values by adding small offsets
    vals_seen = {}
    for k in sorted(pv):
        v = pv[k]
        if v in vals_seen:
            # Add progressively larger offsets for duplicate values
            v += (len(vals_seen[v]) + 1) * 1e-9
        vals_seen.setdefault(v, []).append(k)
        pv[k] = v

    # Create arrays of percentiles and values
    percentiles, values = zip(*sorted(pv.items()))
    percentiles = np.array(percentiles) / 100.0  # Convert to [0,1] range
    values = np.array(values)

    # Check if values are strictly increasing after de-duplication
    if np.any(np.diff(values) <= 0):
        raise CDFGenerationError("Percentile values must be strictly increasing after de-duplication")

    # Add boundary points if needed
    if not open_lower_bound and lower_bound < values[0] - 1e-9:
        percentiles = np.insert(percentiles, 0, 0.0)
        values = np.insert(values, 0, lower_bound)

    if not open_upper_bound and upper_bound > values[-1] + 1e-9:
        percentiles = np.append(percentiles, 1.0)
        values = np.append(values, upper_bound)

    # Determine if log scaling is appropriate (all values positive)
    use_log = np.all(values > 0)
    x_vals = np.log(values) if use_log else values

    # Create interpolator with fallback
    try:
        spline = PchipInterpolator(x_vals, percentiles, extrapolate=True)
    except Exception as e:
        # Fallback to linear interpolation
        logger.warning(f"PchipInterpolator failed ({e}), falling back to linear interpolation")
        def spline(x):
            return np.interp(x, x_vals, percentiles)

    # Generate evaluation grid based on zero_point
    def create_grid(num_pts):
        t = np.linspace(0, 1, num_pts)

        if zero_point is None:
            # Linear grid
            return lower_bound + (upper_bound - lower_bound) * t
        else:
            # Non-linear grid based on zero_point
            ratio = (upper_bound - zero_point) / (lower_bound - zero_point)
            # Handle potential numerical issues
            if abs(ratio - 1.0) < 1e-10:
                return lower_bound + (upper_bound - lower_bound) * t
            else:
                return np.array([
                    lower_bound + (upper_bound - lower_bound) *
                    ((ratio ** tt - 1) / (ratio - 1))
                    for tt in t
                ])

    # Generate the grid and evaluate
    cdf_x = create_grid(num_points)

    # Handle log transformation for evaluation
    eval_x = np.log(cdf_x) if use_log else cdf_x

    # Clamp values to avoid extrapolation issues
    eval_x_clamped = np.clip(eval_x, x_vals[0], x_vals[-1])

    # Generate initial CDF values and clamp to [0,1]
    cdf_y = spline(eval_x_clamped).clip(0.0, 1.0)

    # Ensure monotonicity (non-decreasing)
    cdf_y = np.maximum.accumulate(cdf_y)

    # Set boundary values if bounds are closed
    if not open_lower_bound:
        cdf_y[0] = 0.0
    if not open_upper_bound:
        cdf_y[-1] = 1.0

    # Strict enforcement of minimum step size
    def enforce_min_steps(y_values, min_step_size):
        """Enforce minimum step size between adjacent points."""
        result = y_values.copy()

        # First pass: enforce minimum steps
        for i in range(1, len(result)):
            if result[i] < result[i - 1] + min_step_size:
                result[i] = min(result[i - 1] + min_step_size, 1.0)

        # Second pass: ensure we don't exceed 1.0
        if result[-1] > 1.0:
            overflow_idx = np.where(result > 1.0)[0][0]
            steps_remaining = len(result) - overflow_idx

            for i in range(overflow_idx, len(result)):
                t = (i - overflow_idx) / max(1, steps_remaining - 1)
                result[i] = min(1.0, result[overflow_idx - 1] + (1.0 - result[overflow_idx - 1]) * t)

            # Final check for minimum steps
            for i in range(overflow_idx, len(result)):
                if i > overflow_idx and result[i] < result[i - 1] + min_step_size:
                    result[i] = result[i - 1] + min_step_size
                    if result[i] > 1.0:
                        result[i] = 1.0
                        for j in range(i - 1, overflow_idx - 1, -1):
                            max_allowed = result[j + 1] - min_step_size
                            if result[j] > max_allowed:
                                result[j] = max_allowed

        return result

    # Apply strict step enforcement
    cdf_y = enforce_min_steps(cdf_y, min_step)
    cdf_y = _safe_cdf_bounds(cdf_y, open_lower_bound, open_upper_bound, min_step)

    # Double-check minimum step size requirement
    steps = np.diff(cdf_y)
    if np.any(steps < min_step):
        logger.warning("Minimum step size still violated. Using aggressive step enforcement.")

        if not open_lower_bound:
            start_val = 0.0
        else:
            start_val = cdf_y[0]

        if not open_upper_bound:
            end_val = 1.0
        else:
            end_val = min(cdf_y[-1], 1.0)

        available_range = end_val - start_val
        required_range = (len(cdf_y) - 1) * min_step

        if required_range > available_range:
            raise CDFGenerationError(
                f"Cannot satisfy minimum step requirement: need {required_range:.6f} "
                f"but only have {available_range:.6f} available in CDF range"
            )

        # Create a new CDF with exactly min_step between points where needed
        new_cdf = np.zeros_like(cdf_y)
        new_cdf[0] = start_val

        if len(cdf_y) > 2:
            orig_shape = np.diff(cdf_y)
            orig_shape = np.maximum(orig_shape, min_step)
            orig_shape = orig_shape / np.sum(orig_shape)

            remaining = available_range - (len(cdf_y) - 1) * min_step
            extra_steps = remaining * orig_shape

            for i in range(1, len(new_cdf)):
                new_cdf[i] = new_cdf[i - 1] + min_step + extra_steps[i - 1]
        else:
            for i in range(1, len(new_cdf)):
                new_cdf[i] = new_cdf[i - 1] + (available_range / (len(new_cdf) - 1))

        cdf_y = new_cdf

    # Final validation
    if np.any(np.diff(cdf_y) < min_step - 1e-10):
        problematic_indices = np.where(np.diff(cdf_y) < min_step - 1e-10)[0]
        raise CDFGenerationError(f"Failed to enforce minimum step size at indices: {problematic_indices}")

    return cdf_y.tolist()
