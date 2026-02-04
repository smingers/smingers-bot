"""
CDF generation utilities for numeric question forecasting.

This module contains functions for generating CDFs that satisfy
Metaculus requirements for numeric/discrete question submissions.

IMPORTANT: This implementation exactly matches the official Metaculus
implementation from metaculus-forecasting-tools/numeric_report.py.

Key constraints enforced (matching Metaculus official implementation):
- Configurable number of points (201 for numeric, 102 for discrete)
- Monotonically increasing
- No single step exceeds max_pmf_value (0.2 * 200 / inbound_outcome_count)
- Minimum step size enforced (5e-5)
- Open/closed bound handling
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

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


@dataclass
class Percentile:
    """A percentile point with a value and percentile (0-1)."""

    value: float
    percentile: float


class NumericDistributionGenerator:
    """
    Generates CDFs matching the official Metaculus implementation exactly.

    This class mirrors the NumericDistribution class from metaculus-forecasting-tools.
    """

    def __init__(
        self,
        declared_percentiles: list[Percentile],
        open_upper_bound: bool,
        open_lower_bound: bool,
        upper_bound: float,
        lower_bound: float,
        zero_point: float | None,
        cdf_size: int = DEFAULT_CDF_SIZE,
    ):
        self.declared_percentiles = declared_percentiles
        self.open_upper_bound = open_upper_bound
        self.open_lower_bound = open_lower_bound
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound
        self.zero_point = zero_point
        self.cdf_size = cdf_size

        # Run all validations matching official implementation order
        self._check_percentiles_increasing()
        self._check_log_scaled_fields()
        self._check_percentile_spacing()
        self._check_too_far_from_bounds()
        self.declared_percentiles = self._check_and_update_repeating_values(
            self.declared_percentiles
        )

    def _check_percentiles_increasing(self) -> None:
        """
        Ensure percentiles and values are strictly increasing.

        Matches official implementation exactly.
        """
        percentiles = self.declared_percentiles
        for i in range(len(percentiles) - 1):
            if percentiles[i].percentile >= percentiles[i + 1].percentile:
                raise CDFGenerationError("Percentiles must be in strictly increasing order")
            if percentiles[i].value > percentiles[i + 1].value:
                raise CDFGenerationError("Values must be in strictly increasing order")
        if len(percentiles) < 2:
            raise CDFGenerationError("NumericDistribution must have at least 2 percentiles")

    def _check_log_scaled_fields(self) -> None:
        """
        Validate log-scaled question constraints.

        Matches official implementation exactly.
        """
        if self.zero_point is not None and self.lower_bound <= self.zero_point:
            raise CDFGenerationError(
                f"Lower bound {self.lower_bound} is less than or equal to the zero point {self.zero_point}. "
                "Lower bound must be greater than the zero point."
            )

        for percentile in self.declared_percentiles:
            if self.zero_point is not None and percentile.value < self.zero_point:
                raise CDFGenerationError(
                    f"Percentile value {percentile.value} is less than the zero point {self.zero_point}. "
                    "Determining probability less than zero point is currently not supported."
                )

    def _check_percentile_spacing(self) -> None:
        """
        Ensure minimum spacing between percentiles.

        Matches official implementation exactly.
        """
        percentiles = self.declared_percentiles
        for i in range(len(percentiles) - 1):
            if abs(percentiles[i + 1].percentile - percentiles[i].percentile) < 5e-05:
                raise CDFGenerationError(
                    f"Percentiles at indices {i} and {i + 1} are too close. "
                    f"CDF must be increasing by at least 5e-05 at every step. "
                    f"{percentiles[i].percentile} and {percentiles[i + 1].percentile} "
                    f"at values {percentiles[i].value} and {percentiles[i + 1].value}. "
                    "One possible reason is that your prediction is mostly or completely out of the upper/lower "
                    "bound range thus assigning very little probability to any one x-axis value."
                )

    def _check_too_far_from_bounds(self) -> None:
        """
        Validate percentile values aren't too far from question bounds.

        Matches official implementation exactly.
        """
        percentiles = self.declared_percentiles
        max_to_min_range = self.upper_bound - self.lower_bound

        # Check that at least some percentiles are within 25% wiggle room
        wiggle_percent = 0.25
        wiggle_room = max_to_min_range * wiggle_percent
        upper_bound_plus_wiggle_room = self.upper_bound + wiggle_room
        lower_bound_minus_wiggle_room = self.lower_bound - wiggle_room
        percentiles_within_bounds_plus_wiggle_room = [
            p
            for p in percentiles
            if lower_bound_minus_wiggle_room <= p.value <= upper_bound_plus_wiggle_room
        ]
        if len(percentiles_within_bounds_plus_wiggle_room) == 0:
            raise CDFGenerationError(
                f"No declared percentiles are within the range of the question +/- {wiggle_percent * 100}%. "
                f"Lower bound: {self.lower_bound}, upper bound: {self.upper_bound}. "
                f"Percentiles: {[(p.percentile, p.value) for p in percentiles]}"
            )

        # Check that no percentiles are WAY outside bounds (2x the range)
        max_to_min_range_buffer = max_to_min_range * 2
        percentiles_far_exceeding_bounds = [
            p
            for p in percentiles
            if p.value < self.lower_bound - max_to_min_range_buffer
            or p.value > self.upper_bound + max_to_min_range_buffer
        ]
        if len(percentiles_far_exceeding_bounds) > 0:
            raise CDFGenerationError(
                "Some declared percentiles are far exceeding the bounds of the question. "
                f"Lower bound: {self.lower_bound}, upper bound: {self.upper_bound}. "
                f"Percentiles: {[(p.percentile, p.value) for p in percentiles_far_exceeding_bounds]}"
            )

    def _check_and_update_repeating_values(self, percentiles: list[Percentile]) -> list[Percentile]:
        """
        Handle duplicate values by adding small offsets.

        Matches official implementation exactly.
        """
        from collections import Counter

        unique_value_count = Counter(p.value for p in percentiles)
        final_percentiles = []

        for percentile in percentiles:
            value = percentile.value
            count = unique_value_count[value]
            repeated_value = count > 1
            value_in_bounds = self.lower_bound < value < self.upper_bound
            value_above_bound = value >= self.upper_bound
            value_below_bound = value <= self.lower_bound
            epsilon = 1e-10

            if not repeated_value:
                final_percentiles.append(percentile)
            elif value_in_bounds:
                # Official uses 1e-6 for in-bounds values
                greater_epsilon = 1e-6
                modification = (1 - percentile.percentile) * greater_epsilon
                final_percentiles.append(
                    Percentile(
                        value=value - modification,
                        percentile=percentile.percentile,
                    )
                )
            elif value_above_bound:
                modification = epsilon * percentile.percentile
                final_percentiles.append(
                    Percentile(
                        value=self.upper_bound + modification,
                        percentile=percentile.percentile,
                    )
                )
            elif value_below_bound:
                modification = epsilon * (1 - percentile.percentile)
                final_percentiles.append(
                    Percentile(
                        value=self.lower_bound - modification,
                        percentile=percentile.percentile,
                    )
                )
            else:
                raise CDFGenerationError(
                    f"Unexpected state: value {value} is repeated {count} times. "
                    f"Bounds are [{self.lower_bound}, {self.upper_bound}]"
                )

        return final_percentiles

    def _nominal_location_to_cdf_location(self, nominal_value: float) -> float:
        """
        Convert a real-world value to a CDF location (0-1).

        Matches official implementation exactly.
        """
        range_max = self.upper_bound
        range_min = self.lower_bound
        zero_point = self.zero_point

        if zero_point is not None:
            # logarithmically scaled question
            deriv_ratio = (range_max - zero_point) / (range_min - zero_point)
            if nominal_value == zero_point:
                # If nominal = zero point, add epsilon to avoid log(0)
                nominal_value += 1e-10
            unscaled_location = (
                np.log((nominal_value - range_min) * (deriv_ratio - 1) + (range_max - range_min))
                - np.log(range_max - range_min)
            ) / np.log(deriv_ratio)
        else:
            # linearly scaled question
            unscaled_location = (nominal_value - range_min) / (range_max - range_min)

        return float(unscaled_location)

    def _cdf_location_to_nominal_location(self, cdf_location: float) -> float:
        """
        Convert a CDF location (0-1) to a real-world value.

        Matches official implementation exactly.
        """
        range_max = self.upper_bound
        range_min = self.lower_bound
        zero_point = self.zero_point

        if zero_point is None:
            scaled_location = range_min + (range_max - range_min) * cdf_location
        else:
            deriv_ratio = (range_max - zero_point) / (range_min - zero_point)
            scaled_location = range_min + (range_max - range_min) * (
                deriv_ratio**cdf_location - 1
            ) / (deriv_ratio - 1)

        if np.isnan(scaled_location):
            raise CDFGenerationError(f"Scaled location is NaN for cdf location {cdf_location}")

        return float(scaled_location)

    def _add_explicit_upper_lower_bound_percentiles(
        self,
        input_percentiles: list[Percentile],
    ) -> list[Percentile]:
        """
        Add explicit boundary percentiles for interpolation.

        Matches official implementation exactly.
        """
        open_upper_bound = self.open_upper_bound
        open_lower_bound = self.open_lower_bound
        range_max = self.upper_bound
        range_min = self.lower_bound

        # Convert to dict with percentiles * 100 as keys
        return_percentiles: dict[float, float] = {
            p.percentile * 100: p.value for p in input_percentiles
        }

        percentile_max = max(return_percentiles.keys())
        percentile_min = min(return_percentiles.keys())
        range_size = abs(range_max - range_min)
        buffer = 1 if range_size > 100 else 0.01 * range_size

        # Adjust any values that are exactly at the bounds
        for percentile, value in list(return_percentiles.items()):
            if not open_lower_bound and value <= range_min + buffer:
                return_percentiles[percentile] = range_min + buffer
            if not open_upper_bound and value >= range_max - buffer:
                return_percentiles[percentile] = range_max - buffer

        # Set cdf values outside range for upper bound
        if open_upper_bound:
            if range_max > return_percentiles[percentile_max]:
                halfway_between_max_and_100th_percentile = 100 - (0.5 * (100 - percentile_max))
                return_percentiles[halfway_between_max_and_100th_percentile] = range_max
        else:
            return_percentiles[100] = range_max

        # Set cdf values outside range for lower bound
        if open_lower_bound:
            if range_min < return_percentiles[percentile_min]:
                halfway_between_min_and_0th_percentile = 0.5 * percentile_min
                return_percentiles[halfway_between_min_and_0th_percentile] = range_min
        else:
            return_percentiles[0] = range_min

        # Sort and convert back to list
        sorted_return_percentiles = dict(sorted(return_percentiles.items()))

        return [
            Percentile(percentile=p / 100, value=v) for p, v in sorted_return_percentiles.items()
        ]

    def _get_cdf_at(self, cdf_location: float) -> float:
        """
        Get the CDF height at a specific CDF location using linear interpolation.

        Matches official implementation exactly.
        """
        bounded_percentiles = self._add_explicit_upper_lower_bound_percentiles(
            self.declared_percentiles
        )

        # Build mapping of (cdf_location, height)
        cdf_location_to_percentile_mapping: list[tuple[float, float]] = []
        for percentile in bounded_percentiles:
            height = percentile.percentile
            location = self._nominal_location_to_cdf_location(percentile.value)
            cdf_location_to_percentile_mapping.append((location, height))

        # Linear interpolation
        previous = cdf_location_to_percentile_mapping[0]
        for i in range(1, len(cdf_location_to_percentile_mapping)):
            current = cdf_location_to_percentile_mapping[i]
            epsilon = 1e-10
            if previous[0] - epsilon <= cdf_location <= current[0] + epsilon:
                result = previous[1] + (current[1] - previous[1]) * (cdf_location - previous[0]) / (
                    current[0] - previous[0]
                )
                if np.isnan(result):
                    raise CDFGenerationError(f"Result is NaN for cdf location {cdf_location}")
                return float(result)
            previous = current

        raise CDFGenerationError(f"CDF location {cdf_location} cannot be found in mapping")

    def _standardize_cdf(self, cdf: list[float] | np.ndarray) -> list[float]:
        """
        Standardize a CDF to meet Metaculus requirements.

        Matches official implementation exactly from numeric_report.py.
        """
        cdf = list(cdf)  # Make mutable copy
        lower_open = self.open_lower_bound
        upper_open = self.open_upper_bound

        # Apply lower bound & enforce boundary values
        scale_lower_to = 0 if lower_open else cdf[0]
        scale_upper_to = 1.0 if upper_open else cdf[-1]
        rescaled_inbound_mass = scale_upper_to - scale_lower_to

        def apply_minimum(F: float, location: float) -> float:
            # F is the height of the cdf at location (in range [0, 1])
            # rescale
            rescaled_F = (F - scale_lower_to) / rescaled_inbound_mass
            # offset
            if lower_open and upper_open:
                return 0.988 * rescaled_F + 0.01 * location + 0.001
            elif lower_open:
                return 0.989 * rescaled_F + 0.01 * location + 0.001
            elif upper_open:
                return 0.989 * rescaled_F + 0.01 * location
            return 0.99 * rescaled_F + 0.01 * location

        for i, value in enumerate(cdf):
            cdf[i] = apply_minimum(value, i / (len(cdf) - 1))

        # Apply upper bound - operate in PMF space
        cdf_array = np.array(cdf)
        pmf = np.diff(cdf_array, prepend=0, append=1)
        cap = get_max_pmf_value(len(cdf))

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
        pmf[1:-1] *= (cdf_array[-1] - cdf_array[0]) / pmf[1:-1].sum()

        # Back to CDF space
        cdf_result = np.cumsum(pmf)[:-1]

        # Round to minimize floating point errors
        cdf_result = np.round(cdf_result, 10)
        return cdf_result.tolist()

    def get_cdf(self) -> list[float]:
        """
        Generate the full CDF matching Metaculus requirements.

        Returns a list of CDF values (probabilities) at evenly spaced locations.
        """
        cdf_size = self.cdf_size
        continuous_cdf: list[float] = []
        cdf_eval_locations = [i / (cdf_size - 1) for i in range(cdf_size)]

        for loc in cdf_eval_locations:
            continuous_cdf.append(self._get_cdf_at(loc))

        # Apply standardization
        continuous_cdf = self._standardize_cdf(continuous_cdf)

        return continuous_cdf


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
    Generate a continuous CDF matching the official Metaculus implementation exactly.

    Args:
        percentile_values: Dictionary mapping percentiles (1-99) to values
        open_upper_bound: Whether the upper bound is open
        open_lower_bound: Whether the lower bound is open
        upper_bound: Maximum possible value
        lower_bound: Minimum possible value
        zero_point: Reference point for non-linear (log) scaling
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

    # Clean percentile values (validation happens in NumericDistributionGenerator)
    cleaned_percentiles: list[Percentile] = []
    for k, v in percentile_values.items():
        try:
            k_float = float(k)
            v_float = float(v)

            if not (0 < k_float < 100):
                continue  # Skip invalid percentiles

            if not np.isfinite(v_float):
                continue  # Skip non-finite values

            cleaned_percentiles.append(Percentile(value=v_float, percentile=k_float / 100.0))
        except (ValueError, TypeError):
            continue  # Skip non-numeric entries

    if len(cleaned_percentiles) < 2:
        raise CDFGenerationError(
            f"Need at least 2 valid percentile points (got {len(cleaned_percentiles)})"
        )

    # Sort by percentile
    cleaned_percentiles.sort(key=lambda p: p.percentile)

    # Create generator and get CDF (all validation happens in NumericDistributionGenerator.__init__)
    generator = NumericDistributionGenerator(
        declared_percentiles=cleaned_percentiles,
        open_upper_bound=open_upper_bound,
        open_lower_bound=open_lower_bound,
        upper_bound=upper_bound,
        lower_bound=lower_bound,
        zero_point=zero_point,
        cdf_size=num_points,
    )

    cdf = generator.get_cdf()

    # Final validation
    steps = np.diff(cdf)
    max_allowed_step = get_max_pmf_value(num_points, include_wiggle_room=False)

    if np.any(steps < min_step - 1e-10):
        problematic_indices = np.where(np.array(steps) < min_step - 1e-10)[0]
        raise CDFGenerationError(
            f"Failed to enforce minimum step size at indices: {problematic_indices}"
        )

    if np.any(steps > max_allowed_step + 1e-10):
        problematic_indices = np.where(np.array(steps) > max_allowed_step + 1e-10)[0]
        max_step_found = steps[problematic_indices[0]]
        raise CDFGenerationError(
            f"Failed to enforce maximum step size: found {max_step_found:.4f} at index {problematic_indices[0]}, "
            f"max allowed is {max_allowed_step:.4f}"
        )

    return cdf
