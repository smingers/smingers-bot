"""
CDF generation utilities for numeric question forecasting.

This module contains functions for generating CDFs that satisfy
Metaculus requirements for numeric/discrete question submissions.

Key constraints enforced (matching Metaculus official implementation):
- Configurable number of points (201 for numeric, 102 for discrete)
- Monotonically increasing
- No single step exceeds max_pmf_value (0.2 * 200 / inbound_outcome_count)
- Minimum step size enforced (5e-5)
- Open/closed bound handling
"""

import logging

import numpy as np
from scipy.interpolate import PchipInterpolator

from .exceptions import CDFGenerationError

logger = logging.getLogger(__name__)

# Constants matching Metaculus official implementation
DEFAULT_CDF_SIZE = 201
DEFAULT_INBOUND_OUTCOME_COUNT = DEFAULT_CDF_SIZE - 1  # 200
MAX_NUMERIC_PMF_VALUE = 0.2


def get_max_pmf_value(cdf_size: int, include_wiggle_room: bool = True) -> float:
    """
    Calculate the maximum allowed PMF value (step size) for a given CDF size.

    Matches Metaculus official implementation:
    - Base cap is 0.2 for the default 200 inbound outcomes
    - Scales proportionally for different CDF sizes
    - Includes 5% wiggle room by default for safety margin

    Args:
        cdf_size: Number of points in the CDF (201 for numeric, varies for discrete)
        include_wiggle_room: If True, multiply by 0.95 for safety margin

    Returns:
        Maximum allowed step size between adjacent CDF points
    """
    inbound_outcome_count = cdf_size - 1
    normal_cap = MAX_NUMERIC_PMF_VALUE * (DEFAULT_INBOUND_OUTCOME_COUNT / inbound_outcome_count)

    if include_wiggle_room:
        return normal_cap * 0.95
    else:
        return normal_cap


def _standardize_cdf(
    cdf: list[float] | np.ndarray,
    open_lower_bound: bool,
    open_upper_bound: bool,
) -> list[float]:
    """
    Standardize a CDF to meet Metaculus requirements.

    Matches Metaculus official implementation from numeric_report.py:
    - Assigns no mass outside of closed bounds (scales accordingly)
    - Assigns at least a minimum amount of mass outside of open bounds
    - Ensures CDF is increasing by at least the minimum amount
    - Caps the maximum growth to max_pmf_value

    Args:
        cdf: Input CDF values
        open_lower_bound: Whether the lower bound is open
        open_upper_bound: Whether the upper bound is open

    Returns:
        Standardized CDF as a list of floats
    """
    cdf = np.array(cdf, dtype=float)
    cdf_size = len(cdf)

    # Apply lower bound & enforce boundary values
    scale_lower_to = 0 if open_lower_bound else cdf[0]
    scale_upper_to = 1.0 if open_upper_bound else cdf[-1]
    rescaled_inbound_mass = scale_upper_to - scale_lower_to

    # Avoid division by zero
    if rescaled_inbound_mass < 1e-10:
        rescaled_inbound_mass = 1e-10

    def apply_minimum(F: float, location: float) -> float:
        """Apply minimum probability mass outside bounds."""
        # F is the height of the cdf at location (in range [0, 1])
        # rescale
        rescaled_F = (F - scale_lower_to) / rescaled_inbound_mass
        # offset
        if open_lower_bound and open_upper_bound:
            return 0.988 * rescaled_F + 0.01 * location + 0.001
        elif open_lower_bound:
            return 0.989 * rescaled_F + 0.01 * location + 0.001
        elif open_upper_bound:
            return 0.989 * rescaled_F + 0.01 * location
        return 0.99 * rescaled_F + 0.01 * location

    for i, value in enumerate(cdf):
        cdf[i] = apply_minimum(value, i / (cdf_size - 1))

    # Apply upper bound - operate in PMF space
    pmf = np.diff(cdf, prepend=0, append=1)
    cap = get_max_pmf_value(cdf_size)

    def cap_pmf(scale: float) -> np.ndarray:
        return np.concatenate([pmf[:1], np.minimum(cap, scale * pmf[1:-1]), pmf[-1:]])

    def capped_sum(scale: float) -> float:
        return float(cap_pmf(scale).sum())

    # Find the appropriate scale search space
    lo = hi = scale = 1.0
    while capped_sum(hi) < 1.0:
        hi *= 1.2

    # Hone in on scale value that makes capped sum 1
    for _ in range(100):
        scale = 0.5 * (lo + hi)
        s = capped_sum(scale)
        if s < 1.0:
            lo = scale
        else:
            hi = scale
        if s == 1.0 or (hi - lo) < 2e-5:
            break

    # Apply scale and renormalize
    pmf = cap_pmf(scale)
    if pmf[1:-1].sum() > 1e-10:
        pmf[1:-1] *= (cdf[-1] - cdf[0]) / pmf[1:-1].sum()

    # Back to CDF space
    cdf = np.cumsum(pmf)[:-1]

    # Round to minimize floating point errors
    cdf = np.round(cdf, 10)
    return cdf.tolist()


def generate_continuous_cdf(
    percentile_values: dict,
    open_upper_bound: bool,
    open_lower_bound: bool,
    upper_bound: float,
    lower_bound: float,
    zero_point: float | None = None,
    *,
    min_step: float = 5.0e-5,
    num_points: int = 201,
) -> list[float]:
    """
    Generate a continuous CDF with strict enforcement of Metaculus requirements.

    Args:
        percentile_values: Dictionary mapping percentiles (1-99) to values
        open_upper_bound: Whether the upper bound is open
        open_lower_bound: Whether the lower bound is open
        upper_bound: Maximum possible value
        lower_bound: Minimum possible value
        zero_point: Reference point for non-linear scaling
        min_step: Minimum step size between adjacent CDF points
        num_points: Number of points in the output CDF (201 for numeric, 102 for discrete)

    Returns:
        List of CDF values (length num_points)

    Raises:
        CDFGenerationError: If CDF cannot be generated with given constraints
    """
    # Validate inputs
    if not percentile_values:
        raise CDFGenerationError("Empty percentile values dictionary")

    if upper_bound <= lower_bound:
        raise CDFGenerationError(
            f"Upper bound ({upper_bound}) must be greater than lower bound ({lower_bound})"
        )

    if zero_point is not None:
        if abs(zero_point - lower_bound) < 1e-6 or abs(zero_point - upper_bound) < 1e-6:
            raise CDFGenerationError(
                f"zero_point ({zero_point}) too close to bounds [{lower_bound}, {upper_bound}]"
            )

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
    percentiles, values = zip(*sorted(pv.items()), strict=True)
    percentiles = np.array(percentiles) / 100.0  # Convert to [0,1] range
    values = np.array(values)

    # Check if values are strictly increasing after de-duplication
    if np.any(np.diff(values) <= 0):
        raise CDFGenerationError(
            "Percentile values must be strictly increasing after de-duplication"
        )

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
                return np.array(
                    [
                        lower_bound + (upper_bound - lower_bound) * ((ratio**tt - 1) / (ratio - 1))
                        for tt in t
                    ]
                )

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

    # Apply Metaculus standardization (handles both min and max step enforcement)
    cdf_y = _standardize_cdf(cdf_y, open_lower_bound, open_upper_bound)

    # Final validation
    steps = np.diff(cdf_y)
    max_allowed_step = get_max_pmf_value(num_points, include_wiggle_room=False)

    if np.any(steps < min_step - 1e-10):
        problematic_indices = np.where(np.diff(cdf_y) < min_step - 1e-10)[0]
        raise CDFGenerationError(
            f"Failed to enforce minimum step size at indices: {problematic_indices}"
        )

    if np.any(steps > max_allowed_step + 1e-10):
        problematic_indices = np.where(steps > max_allowed_step + 1e-10)[0]
        max_step_found = steps[problematic_indices[0]]
        raise CDFGenerationError(
            f"Failed to enforce maximum step size: found {max_step_found:.4f} at index {problematic_indices[0]}, "
            f"max allowed is {max_allowed_step:.4f}"
        )

    return cdf_y
