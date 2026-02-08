"""
Tests for CDF generation in numeric forecasting.

Tests the functions in src/bot/cdf.py:
- generate_continuous_cdf()
- get_max_pmf_value()
- percentiles_from_cdf()

And src/bot/extractors.py:
- enforce_monotonic_percentiles()

These are critical for Metaculus submission validity.
"""

import numpy as np
import pytest

from src.bot.cdf import (
    generate_continuous_cdf,
    get_max_pmf_value,
    percentiles_from_cdf,
)
from src.bot.exceptions import CDFGenerationError
from src.bot.extractors import enforce_monotonic_percentiles


class TestGenerateContinuousCDF:
    """Tests for generate_continuous_cdf()"""

    @pytest.fixture
    def simple_percentiles(self) -> dict[int, float]:
        """Simple increasing percentiles for testing."""
        return {
            1: 10,
            10: 20,
            50: 50,
            90: 80,
            99: 100,
        }

    def test_returns_201_points(self, simple_percentiles):
        """Test that output CDF has exactly 201 points."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
        )
        assert len(cdf) == 201

    def test_monotonically_increasing(self, simple_percentiles):
        """Test that CDF is strictly non-decreasing."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
        )
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}: {cdf[i]} > {cdf[i + 1]}"

    def test_values_in_valid_range(self, simple_percentiles):
        """Test that all CDF values are in [0, 1]."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
        )
        assert all(0 <= v <= 1 for v in cdf), "CDF values outside [0, 1]"

    def test_open_bounds_constraints(self, simple_percentiles):
        """Test that open bounds satisfy Metaculus requirements."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
        )
        # Open lower bound: first value >= 0.001
        assert cdf[0] >= 0.001, f"Open lower bound violated: {cdf[0]} < 0.001"
        # Open upper bound: last value <= 0.999
        assert cdf[-1] <= 0.999, f"Open upper bound violated: {cdf[-1]} > 0.999"

    def test_closed_bounds_constraints(self, simple_percentiles):
        """Test that closed bounds hit approximately 0 and 1."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=120,
            lower_bound=0,
        )
        # Closed lower bound: first value == 0
        assert cdf[0] == 0.0, f"Closed lower bound violated: {cdf[0]} != 0"
        # Closed upper bound: last value ≈ 1 (floating point tolerance)
        assert cdf[-1] == pytest.approx(1.0, abs=1e-9), (
            f"Closed upper bound violated: {cdf[-1]} != 1"
        )

    def test_max_step_constraint(self, simple_percentiles):
        """Test that no single step exceeds max_pmf_value (Metaculus requirement)."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
        )
        steps = np.diff(cdf)
        max_allowed = get_max_pmf_value(201, include_wiggle_room=False)
        assert np.all(steps <= max_allowed + 1e-10), (
            f"Max step exceeded: {np.max(steps)} > {max_allowed}"
        )

    def test_min_step_constraint(self, simple_percentiles):
        """Test that minimum step size is enforced."""
        min_step = 5.0e-5
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            min_step=min_step,
        )
        steps = np.diff(cdf)
        # Allow tiny numerical tolerance
        assert np.all(steps >= min_step - 1e-10), f"Min step violated: {np.min(steps)} < {min_step}"

    def test_empty_percentiles_raises(self):
        """Test that empty percentiles dict raises CDFGenerationError."""
        with pytest.raises(CDFGenerationError, match="Empty percentile"):
            generate_continuous_cdf(
                percentile_values={},
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
            )

    def test_single_percentile_raises(self):
        """Test that single percentile raises CDFGenerationError."""
        with pytest.raises(CDFGenerationError, match="at least 2"):
            generate_continuous_cdf(
                percentile_values={50: 50},
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
            )

    def test_invalid_bounds_raises(self):
        """Test that upper_bound <= lower_bound raises CDFGenerationError."""
        with pytest.raises(CDFGenerationError, match="must be greater than"):
            generate_continuous_cdf(
                percentile_values={10: 20, 90: 80},
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=50,  # upper < lower
                lower_bound=100,
            )

    def test_handles_negative_values(self):
        """Test CDF generation with negative value ranges."""
        percentiles = {10: -80, 50: -50, 90: -20}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=0,
            lower_bound=-100,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)

    def test_handles_large_values(self):
        """Test CDF generation with large numbers."""
        percentiles = {10: 1_000_000, 50: 5_000_000, 90: 9_000_000}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=10_000_000,
            lower_bound=0,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)

    def test_handles_small_values(self):
        """Test CDF generation with very small decimal ranges."""
        percentiles = {10: 0.001, 50: 0.005, 90: 0.009}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=0.01,
            lower_bound=0.0001,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)

    def test_percentiles_as_floats(self):
        """Test that percentile keys can be floats."""
        percentiles = {10.0: 20, 50.0: 50, 90.0: 80}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201

    def test_percentiles_as_strings(self):
        """Test that percentile keys can be numeric strings."""
        percentiles = {"10": 20, "50": 50, "90": 80}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201


class TestGetMaxPmfValue:
    """Tests for get_max_pmf_value()"""

    def test_default_201_points(self):
        """Test that 201 points gives max of 0.2 (without wiggle room)."""
        max_val = get_max_pmf_value(201, include_wiggle_room=False)
        assert max_val == pytest.approx(0.2, abs=1e-10)

    def test_default_201_with_wiggle_room(self):
        """Test that 201 points gives 0.19 with wiggle room."""
        max_val = get_max_pmf_value(201, include_wiggle_room=True)
        assert max_val == pytest.approx(0.19, abs=1e-10)

    def test_102_points_scales(self):
        """Test that 102 points scales the max appropriately."""
        max_val = get_max_pmf_value(102, include_wiggle_room=False)
        # 0.2 * (200 / 101) ≈ 0.396
        expected = 0.2 * (200 / 101)
        assert max_val == pytest.approx(expected, abs=1e-10)

    def test_smaller_cdf_allows_larger_steps(self):
        """Test that smaller CDFs allow larger steps."""
        max_201 = get_max_pmf_value(201, include_wiggle_room=False)
        max_102 = get_max_pmf_value(102, include_wiggle_room=False)
        assert max_102 > max_201


class TestEnforceStrictIncreasing:
    """Tests for enforce_monotonic_percentiles()"""

    def test_already_increasing_unchanged(self):
        """Test that already increasing values are unchanged."""
        pct = {1: 10, 50: 50, 99: 100}
        result = enforce_monotonic_percentiles(pct)
        assert result == {1: 10, 50: 50, 99: 100}

    def test_fixes_duplicate_values(self):
        """Test that duplicate values get small offset."""
        pct = {1: 10, 10: 10, 50: 50}
        result = enforce_monotonic_percentiles(pct)
        sorted_values = [result[k] for k in sorted(result.keys())]
        # Should be strictly increasing
        for i in range(len(sorted_values) - 1):
            assert sorted_values[i] < sorted_values[i + 1]

    def test_inverted_values_raises_error(self):
        """Test that fully inverted percentiles raise an error."""
        import pytest

        from src.bot.exceptions import ExtractionError

        pct = {1: 100, 50: 50, 99: 10}  # Inverted - P1 > P99
        with pytest.raises(ExtractionError, match="Percentiles are inverted"):
            enforce_monotonic_percentiles(pct)

    def test_preserves_key_order(self):
        """Test that percentile keys are preserved."""
        pct = {1: 10, 50: 20, 99: 30}
        result = enforce_monotonic_percentiles(pct)
        assert set(result.keys()) == {1, 50, 99}


class TestDiscreteCDF:
    """Tests for discrete question CDF generation (102 points instead of 201)."""

    @pytest.fixture
    def simple_percentiles(self) -> dict[int, float]:
        """Simple increasing percentiles for testing."""
        return {
            1: 10,
            10: 20,
            50: 50,
            90: 80,
            99: 100,
        }

    def test_returns_102_points(self, simple_percentiles):
        """Test that output CDF has exactly 102 points for discrete questions."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            num_points=102,
        )
        assert len(cdf) == 102

    def test_monotonically_increasing(self, simple_percentiles):
        """Test that discrete CDF is strictly non-decreasing."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            num_points=102,
        )
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}"

    def test_values_in_valid_range(self, simple_percentiles):
        """Test that all discrete CDF values are in [0, 1]."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            num_points=102,
        )
        assert all(0 <= v <= 1 for v in cdf), "CDF values outside [0, 1]"

    def test_min_step_constraint_102(self, simple_percentiles):
        """Test that minimum step size is enforced with 102 points."""
        min_step = 5.0e-5
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            min_step=min_step,
            num_points=102,
        )
        steps = np.diff(cdf)
        assert np.all(steps >= min_step - 1e-10), f"Min step violated: {np.min(steps)} < {min_step}"

    def test_max_step_constraint_102(self, simple_percentiles):
        """Test that no single step exceeds max_pmf_value with 102 points."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            num_points=102,
        )
        steps = np.diff(cdf)
        max_allowed = get_max_pmf_value(102, include_wiggle_room=False)
        assert np.all(steps <= max_allowed + 1e-10), (
            f"Max step exceeded: {np.max(steps)} > {max_allowed}"
        )

    def test_open_bounds_constraints_102(self, simple_percentiles):
        """Test that open bounds satisfy Metaculus requirements for 102 points."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            num_points=102,
        )
        assert cdf[0] >= 0.001, f"Open lower bound violated: {cdf[0]} < 0.001"
        assert cdf[-1] <= 0.999, f"Open upper bound violated: {cdf[-1]} > 0.999"


class TestDateCDF:
    """Tests for date question CDF generation (using timestamps)."""

    def test_date_cdf_with_timestamps(self):
        """Test CDF generation with Unix timestamp percentiles (date questions)."""
        # Example timestamps for dates in 2026
        percentiles = {
            10: 1767225600,  # ~2026-01-01
            50: 1777660800,  # ~2026-06-01
            90: 1790697600,  # ~2026-10-01
        }
        # Bounds as timestamps
        lower_bound = 1735689600  # ~2025-01-01
        upper_bound = 1798761600  # ~2027-01-01

        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            num_points=201,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)

    def test_date_cdf_monotonicity(self):
        """Test that date CDFs are monotonically increasing."""
        percentiles = {
            1: 1767225600,
            50: 1777660800,
            99: 1798761600,
        }
        lower_bound = 1735689600
        upper_bound = 1830297600  # ~2028-01-01

        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
        )
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"Date CDF not monotonic at index {i}"


class TestCDFEdgeCases:
    """Tests for edge cases and real-world scenarios."""

    def test_tight_distribution(self):
        """Test with tightly clustered percentile values."""
        # All values very close together
        percentiles = {10: 49, 50: 50, 90: 51}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201
        # Should still be valid despite tight clustering
        assert all(0 <= v <= 1 for v in cdf)

    def test_wide_distribution(self):
        """Test with widely spread percentile values."""
        percentiles = {1: 1, 50: 50000, 99: 1_000_000}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=2_000_000,
            lower_bound=0,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)

    def test_scientific_notation_values(self):
        """Test with scientific notation values."""
        percentiles = {10: 1e-6, 50: 1e-4, 90: 1e-2}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=0.1,
            lower_bound=1e-8,
        )
        assert len(cdf) == 201

    def test_many_percentiles(self):
        """Test with many percentile points."""
        # Use all valid percentile keys
        valid_keys = [
            1,
            5,
            10,
            15,
            20,
            25,
            30,
            35,
            40,
            45,
            50,
            55,
            60,
            65,
            70,
            75,
            80,
            85,
            90,
            95,
            99,
        ]
        percentiles = {k: k for k in valid_keys}  # Linear distribution
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)

    def test_minimum_percentiles(self):
        """Test with minimum required percentiles (just 2)."""
        percentiles = {10: 20, 90: 80}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201

    def test_negative_bounds_positive_predictions_no_zero_point(self):
        """
        Regression test for Q41910 failure (Namibia inflation rate).

        When bounds include negative values (-2 to 15) but all forecaster
        predictions are positive (e.g., 2.5 to 5.2%), the CDF must still
        generate without NaN values.

        This failed when log scaling was incorrectly inferred from positive
        predictions instead of using zero_point=None to determine linear scaling.
        """
        # Exact scenario from Q41910: Namibia inflation rate
        # Bounds: -2.0 to 15.0, zero_point=None
        # Forecaster predictions were all positive (around 2.5-5.2%)
        percentiles = {
            1: 2.5,
            5: 2.9,
            10: 3.1,
            20: 3.3,
            40: 3.6,
            60: 3.8,
            80: 4.1,
            90: 4.4,
            95: 4.7,
            99: 5.2,
        }
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=15.0,
            lower_bound=-2.0,
            zero_point=None,  # No log scaling - this is the key!
        )

        # Must not contain NaN values
        assert len(cdf) == 201
        assert all(not np.isnan(v) for v in cdf), "CDF contains NaN values"
        assert all(0 <= v <= 1 for v in cdf), "CDF values outside [0, 1]"

        # Must be monotonically increasing
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}"


class TestValidationMethods:
    """Tests for validation methods in NumericDistributionGenerator."""

    def test_check_log_scaled_fields_zero_point_above_lower_bound(self):
        """Test that zero_point >= lower_bound raises error."""
        percentiles = {10: 20, 50: 50, 90: 80}
        with pytest.raises(CDFGenerationError, match="less than or equal to the zero point"):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=10,  # lower_bound = 10
                zero_point=10,  # zero_point = 10, violates lower_bound > zero_point
            )

    def test_check_log_scaled_fields_value_below_zero_point(self):
        """Test that percentile value < zero_point raises error."""
        percentiles = {10: 5, 50: 50, 90: 80}  # value 5 < zero_point 10
        with pytest.raises(CDFGenerationError, match="less than the zero point"):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=11,  # must be > zero_point
                zero_point=10,
            )

    def test_check_percentile_spacing_too_close(self):
        """Test that percentiles within 5e-5 of each other raise error.

        This validation triggers when adjacent percentiles (not values) are
        too close together (< 5e-5 apart). Since generate_continuous_cdf only
        accepts integer percentile keys, this can only be triggered by using
        NumericDistributionGenerator directly with crafted Percentile objects.
        """
        from src.bot.cdf import NumericDistributionGenerator, Percentile

        # Create percentiles that are too close: 0.10 and 0.10001 differ by 0.00001 < 5e-5
        too_close_percentiles = [
            Percentile(value=20, percentile=0.10),
            Percentile(value=30, percentile=0.10001),  # Only 0.00001 apart
            Percentile(value=80, percentile=0.90),
        ]
        with pytest.raises(CDFGenerationError, match="too close"):
            NumericDistributionGenerator(
                declared_percentiles=too_close_percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
                zero_point=None,
            )

    def test_check_too_far_from_bounds_no_values_in_range(self):
        """Test that all percentiles outside 25% wiggle room raises error."""
        # Bounds: 0-100, wiggle room: 25% = 25
        # So valid range with wiggle: -25 to 125
        # Put all percentiles WAY outside
        percentiles = {10: 500, 50: 600, 90: 700}  # All way above 125
        with pytest.raises(
            CDFGenerationError, match="No declared percentiles are within the range"
        ):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
            )

    def test_check_too_far_from_bounds_values_exceed_2x_range(self):
        """Test that percentiles exceeding 2x range buffer raise error."""
        # Bounds: 0-100, range = 100, 2x buffer = 200
        # So values must be within [-200, 300]
        # Put one value way outside
        percentiles = {10: 50, 50: 60, 90: 500}  # 500 > 300 (upper + 2x range)
        with pytest.raises(CDFGenerationError, match="far exceeding the bounds"):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
            )

    def test_check_too_far_from_bounds_below_2x_range(self):
        """Test that percentiles below lower - 2x range raise error."""
        # Bounds: 0-100, range = 100, 2x buffer = 200
        # So values must be within [-200, 300]
        percentiles = {10: -300, 50: 50, 90: 80}  # -300 < -200
        with pytest.raises(CDFGenerationError, match="far exceeding the bounds"):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
            )

    def test_check_percentiles_increasing_values_decreasing(self):
        """Test that decreasing values raise error."""
        percentiles = {10: 80, 50: 50, 90: 20}  # Values decrease as percentiles increase
        with pytest.raises(CDFGenerationError, match="strictly increasing order"):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=100,
                lower_bound=0,
            )

    def test_valid_percentiles_within_wiggle_room(self):
        """Test that percentiles within 25% wiggle room are accepted."""
        # Bounds: 0-100, wiggle room extends to -25 and 125
        percentiles = {10: -20, 50: 50, 90: 120}  # Within wiggle room
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201

    def test_valid_log_scaled_question(self):
        """Test that valid log-scaled question works."""
        # zero_point must be < lower_bound, and all values must be > zero_point
        percentiles = {10: 20, 50: 50, 90: 80}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=10,
            zero_point=5,  # zero_point < lower_bound, all values > zero_point
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)


class TestRepeatingValues:
    """Tests for handling duplicate/repeating percentile values."""

    def test_repeating_values_at_lower_bound(self):
        """Test that duplicate values at lower bound get proper epsilon offsets."""
        # Multiple percentiles with value at the lower bound
        percentiles = {10: 0, 50: 0, 90: 100}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201
        # CDF should still be strictly increasing
        for i in range(len(cdf) - 1):
            assert cdf[i] < cdf[i + 1], f"CDF not strictly increasing at index {i}"

    def test_repeating_values_at_upper_bound(self):
        """Test that duplicate values at upper bound get proper epsilon offsets."""
        # Multiple percentiles with value at the upper bound
        percentiles = {10: 0, 50: 100, 90: 100}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100,
            lower_bound=0,
        )
        assert len(cdf) == 201
        # CDF should still be strictly increasing
        for i in range(len(cdf) - 1):
            assert cdf[i] < cdf[i + 1], f"CDF not strictly increasing at index {i}"

    def test_repeating_values_in_middle(self):
        """Test that duplicate values in middle of distribution get properly separated."""
        # Many percentiles clustered at a single value in the middle
        percentiles = {10: 10, 20: 11, 40: 11, 60: 11, 80: 11, 90: 11}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=False,
            upper_bound=220,
            lower_bound=0,
        )
        assert len(cdf) == 201
        # CDF should still be monotonically increasing
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}"
        # All values should be valid
        assert all(0 <= v <= 1 for v in cdf)

    def test_all_same_value_concentrated_prediction(self):
        """Test when all percentiles have the same value (highly concentrated prediction)."""
        # All percentiles at value 12 - very concentrated prediction
        percentiles = {10: 12, 20: 12, 40: 12, 60: 12, 80: 12, 90: 12}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=False,
            upper_bound=20,
            lower_bound=0,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)
        # Should be monotonically increasing
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}"

    def test_edge_of_bin_probability_assignment(self):
        """
        Test that when all probability is at a single value (e.g., 12),
        the correct bin gets the probability for scoring.

        If question resolves to "12", probability should be assigned to
        the bucket containing 12, not the adjacent bucket.
        """
        # All percentiles at value 12 - highly concentrated prediction
        percentiles = {10: 12, 20: 12, 40: 12, 60: 12, 80: 12, 90: 12}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=False,
            upper_bound=20,
            lower_bound=0,
        )

        # Calculate PMF (probability mass function) from CDF
        pmf = np.diff([0] + list(cdf))

        # For a 201-point CDF over range [0, 20], each bin covers 0.1 units
        # Value 12 should be in bin 120 (12 / 20 * 200 = 120)
        # The bin containing 12 should have more probability than neighbors
        bin_for_12 = 120
        max_pmf = get_max_pmf_value(201, include_wiggle_room=True) * 0.95

        # The correct bin should have high probability
        assert pmf[bin_for_12] > max_pmf, (
            f"Bin {bin_for_12} (containing value 12) should have high probability, "
            f"got {pmf[bin_for_12]:.5f}, expected > {max_pmf:.5f}"
        )
        # Adjacent bins should have less probability
        assert pmf[bin_for_12] > pmf[bin_for_12 - 1], (
            f"Bin {bin_for_12} should have more probability than bin {bin_for_12 - 1}"
        )
        assert pmf[bin_for_12] > pmf[bin_for_12 + 1], (
            f"Bin {bin_for_12} should have more probability than bin {bin_for_12 + 1}"
        )


class TestDiscreteDistributions:
    """Tests for discrete question CDF generation (smaller point counts)."""

    def test_discrete_21_points_with_repeated_values(self):
        """Test 21-point CDF (discrete question) with repeated values."""
        percentiles = {10: 12, 20: 12, 40: 12, 60: 12, 80: 12, 90: 12}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=20,
            lower_bound=0,
            num_points=21,
        )
        assert len(cdf) == 21
        assert all(0 <= v <= 1 for v in cdf)
        # Most probability should be concentrated around the repeated value
        # The PMF at index 12 should be larger than neighbors
        pmf = np.diff([0] + list(cdf))
        assert pmf[12] > pmf[11], "Probability at value 12 should exceed value 11"
        assert pmf[12] > pmf[13], "Probability at value 12 should exceed value 13"


class TestLogScaleDistributions:
    """Tests for log-scaled questions (with zero_point)."""

    def test_log_scale_with_repeated_values(self):
        """Test log-scaled question with concentrated predictions."""
        percentiles = {10: 11, 20: 11, 40: 11, 60: 11, 80: 11, 90: 11}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100_000_000,
            lower_bound=1,
            zero_point=0,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)
        # Should not contain NaN
        assert all(not np.isnan(v) for v in cdf)
        # Should be monotonically increasing
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}"

    def test_log_scale_wide_range(self):
        """Test log-scaled question spanning many orders of magnitude."""
        percentiles = {10: 10, 50: 1000, 90: 1_000_000}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=False,
            upper_bound=1_000_000_000,
            lower_bound=1,
            zero_point=0,
        )
        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)


class TestDistributionVariations:
    """Parametrized tests covering various distribution shapes and configurations."""

    @pytest.mark.parametrize("orientation", ["far_left", "center", "far_right"])
    @pytest.mark.parametrize("spread", ["very_wide", "normal", "very_narrow"])
    def test_orientation_and_spread_variations(self, orientation, spread):
        """Test distributions with different orientations and spreads."""
        lower_bound, upper_bound = 0, 100
        range_size = upper_bound - lower_bound

        # Determine center based on orientation
        orientation_fractions = {
            "far_left": 0.02,
            "center": 0.5,
            "far_right": 0.98,
        }
        center = lower_bound + range_size * orientation_fractions[orientation]

        # Determine spread
        spread_fractions = {
            "very_wide": 0.99,
            "normal": 0.15,
            "very_narrow": 0.01,
        }
        half_spread = spread_fractions[spread] * range_size

        # Generate percentiles around center with given spread
        percentile_points = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        percentiles = {}
        for p in percentile_points:
            offset = (p - 0.5) * 2 * half_spread
            value = center + offset
            percentiles[int(p * 100)] = value

        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
        )

        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)
        # Check monotonicity
        for i in range(len(cdf) - 1):
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}"

    @pytest.mark.parametrize("cdf_size", [21, 102, 201])
    @pytest.mark.parametrize("open_upper", [True, False])
    @pytest.mark.parametrize("open_lower", [True, False])
    def test_bounds_and_size_variations(self, cdf_size, open_upper, open_lower):
        """Test different CDF sizes and bound configurations."""
        percentiles = {10: 20, 30: 40, 50: 50, 70: 60, 90: 80}
        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=open_upper,
            open_lower_bound=open_lower,
            upper_bound=100,
            lower_bound=0,
            num_points=cdf_size,
        )

        assert len(cdf) == cdf_size
        assert all(0 <= v <= 1 for v in cdf)

        # Check boundary constraints
        if open_lower:
            assert cdf[0] >= 0.001, "Open lower bound should have cdf[0] >= 0.001"
        else:
            assert cdf[0] == 0.0, "Closed lower bound should have cdf[0] == 0"

        if open_upper:
            assert cdf[-1] <= 0.999, "Open upper bound should have cdf[-1] <= 0.999"
        else:
            assert cdf[-1] == pytest.approx(1.0, abs=1e-9), (
                "Closed upper bound should have cdf[-1] ≈ 1"
            )

    @pytest.mark.parametrize(
        "bounds",
        [
            (-5, 5),
            (0, 100),
            (-30_000, 30_000),
        ],
    )
    def test_different_bound_ranges(self, bounds):
        """Test distributions with different bound ranges."""
        lower_bound, upper_bound = bounds
        center = (lower_bound + upper_bound) / 2
        spread = (upper_bound - lower_bound) * 0.2

        percentiles = {
            10: center - spread,
            50: center,
            90: center + spread,
        }

        cdf = generate_continuous_cdf(
            percentile_values=percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
        )

        assert len(cdf) == 201
        assert all(0 <= v <= 1 for v in cdf)


class TestTooLittleProbabilityInRange:
    """Tests for error when percentiles assign almost no probability within bounds."""

    def test_all_probability_outside_bounds(self):
        """Test error when all percentile values are far outside the question bounds."""
        # All percentiles are between 1.1 and 1.9, but bounds are 14-15
        percentiles = {
            10: 1.1,
            20: 1.2,
            30: 1.3,
            40: 1.4,
            50: 1.5,
            60: 1.6,
            70: 1.7,
            80: 1.8,
            90: 1.9,
        }
        # This should fail the _check_too_far_from_bounds validation
        with pytest.raises(
            CDFGenerationError, match="No declared percentiles are within the range"
        ):
            generate_continuous_cdf(
                percentile_values=percentiles,
                open_upper_bound=True,
                open_lower_bound=True,
                upper_bound=15,
                lower_bound=14,
            )


class TestAggregationEdgeCases:
    """Tests for CDF aggregation scenarios."""

    def test_aggregating_multiple_cdfs_produces_valid_output(self):
        """Test that averaging multiple CDFs produces a valid CDF."""
        # Generate three different CDFs
        cdf1 = generate_continuous_cdf(
            percentile_values={10: 10, 50: 20, 90: 30},
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100,
            lower_bound=0,
        )
        cdf2 = generate_continuous_cdf(
            percentile_values={10: 20, 50: 30, 90: 40},
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100,
            lower_bound=0,
        )
        cdf3 = generate_continuous_cdf(
            percentile_values={10: 30, 50: 40, 90: 50},
            open_upper_bound=False,
            open_lower_bound=False,
            upper_bound=100,
            lower_bound=0,
        )

        # Simple average (this is what numeric.py does)
        combined = [(c1 + c2 + c3) / 3 for c1, c2, c3 in zip(cdf1, cdf2, cdf3, strict=True)]

        assert len(combined) == 201
        assert all(0 <= v <= 1 for v in combined)
        # Should be monotonically increasing
        for i in range(len(combined) - 1):
            assert combined[i] <= combined[i + 1], f"Aggregated CDF not monotonic at index {i}"


class TestPercentilesFromCdf:
    """Tests for percentiles_from_cdf() — extracting real-world values from a CDF."""

    def _make_linear_cdf(self, lower_bound, upper_bound, num_points=201):
        """Generate a perfectly linear CDF (uniform distribution) for testing."""
        return [i / (num_points - 1) for i in range(num_points)]

    def test_linear_uniform_distribution(self):
        """A uniform CDF over [0, 100] should return percentile values matching the percentile."""
        cdf = self._make_linear_cdf(0, 100)
        result = percentiles_from_cdf(cdf, lower_bound=0, upper_bound=100)

        assert set(result.keys()) == {"10", "25", "50", "75", "90"}
        # For a uniform distribution on [0, 100], P10=10, P50=50, P90=90
        assert result["10"] == pytest.approx(10.0, abs=0.5)
        assert result["25"] == pytest.approx(25.0, abs=0.5)
        assert result["50"] == pytest.approx(50.0, abs=0.5)
        assert result["75"] == pytest.approx(75.0, abs=0.5)
        assert result["90"] == pytest.approx(90.0, abs=0.5)

    def test_linear_shifted_bounds(self):
        """Uniform CDF over [200, 300] should shift percentile values accordingly."""
        cdf = self._make_linear_cdf(200, 300)
        result = percentiles_from_cdf(cdf, lower_bound=200, upper_bound=300)

        assert result["50"] == pytest.approx(250.0, abs=0.5)
        assert result["10"] == pytest.approx(210.0, abs=0.5)
        assert result["90"] == pytest.approx(290.0, abs=0.5)

    def test_custom_target_percentiles(self):
        """Should support custom target percentile list."""
        cdf = self._make_linear_cdf(0, 100)
        result = percentiles_from_cdf(
            cdf, lower_bound=0, upper_bound=100, target_percentiles=[5, 50, 95]
        )

        assert set(result.keys()) == {"5", "50", "95"}
        assert result["5"] == pytest.approx(5.0, abs=0.5)
        assert result["95"] == pytest.approx(95.0, abs=0.5)

    def test_single_target_percentile(self):
        """Should work with a single target percentile."""
        cdf = self._make_linear_cdf(0, 100)
        result = percentiles_from_cdf(
            cdf, lower_bound=0, upper_bound=100, target_percentiles=[50]
        )

        assert result == {"50": pytest.approx(50.0, abs=0.5)}

    def test_log_scaled_question(self):
        """Log-scaled CDF should produce non-linear percentile spacing."""
        cdf = self._make_linear_cdf(1, 1000)
        result_linear = percentiles_from_cdf(cdf, lower_bound=1, upper_bound=1000)
        result_log = percentiles_from_cdf(
            cdf, lower_bound=1, upper_bound=1000, zero_point=0
        )

        # With log scaling, the same CDF location maps to a lower real-world value
        # because log compression concentrates CDF mass toward the lower bound.
        # The CDF midpoint maps to ~geometric mean: sqrt(1 * 1000) ≈ 31.6
        assert result_log["50"] == pytest.approx(31.6, rel=0.1)
        assert result_log["50"] < result_linear["50"]  # log compresses toward lower bound

    def test_log_scaling_monotonic(self):
        """Log-scaled percentile values should still be monotonically increasing."""
        cdf = self._make_linear_cdf(10, 10000)
        result = percentiles_from_cdf(
            cdf, lower_bound=10, upper_bound=10000, zero_point=0
        )

        values = [result[str(p)] for p in [10, 25, 50, 75, 90]]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], f"P{[10,25,50,75,90][i]} >= P{[10,25,50,75,90][i+1]}"

    def test_with_generated_cdf(self):
        """Round-trip: generate a CDF from percentiles, then extract percentiles back."""
        input_percentiles = {10: 20, 25: 35, 50: 50, 75: 65, 90: 80}
        cdf = generate_continuous_cdf(
            input_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=100,
            lower_bound=0,
        )

        result = percentiles_from_cdf(cdf, lower_bound=0, upper_bound=100)

        # Extracted percentiles should be close to the originals
        # (not exact due to CDF standardization/capping)
        assert result["50"] == pytest.approx(50.0, abs=5.0)
        assert result["10"] == pytest.approx(20.0, abs=5.0)
        assert result["90"] == pytest.approx(80.0, abs=5.0)

    def test_with_generated_cdf_log_scaled(self):
        """Round-trip with log scaling."""
        input_percentiles = {10: 20, 25: 50, 50: 100, 75: 300, 90: 700}
        cdf = generate_continuous_cdf(
            input_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=1000,
            lower_bound=10,
            zero_point=0,
        )

        result = percentiles_from_cdf(
            cdf, lower_bound=10, upper_bound=1000, zero_point=0
        )

        # Should recover approximate original values
        assert result["50"] == pytest.approx(100.0, rel=0.3)
        # Order should be preserved
        assert result["10"] < result["25"] < result["50"] < result["75"] < result["90"]

    def test_step_function_cdf(self):
        """CDF that jumps suddenly (concentrated distribution) should still work."""
        # CDF that is ~0 until midpoint, then jumps to ~1
        cdf = []
        for i in range(201):
            if i < 95:
                cdf.append(0.001 * i / 95)  # slowly rise to 0.001
            elif i < 105:
                cdf.append(0.001 + 0.998 * (i - 95) / 10)  # jump in the middle
            else:
                cdf.append(0.999 + 0.001 * (i - 105) / 95)  # slowly rise to ~1.0

        result = percentiles_from_cdf(cdf, lower_bound=0, upper_bound=100)

        # All percentiles should cluster near 50 (the midpoint)
        for key in ["10", "25", "50", "75", "90"]:
            assert 40 <= result[key] <= 60, f"P{key}={result[key]} not near midpoint"

    def test_empty_cdf(self):
        """Empty CDF returns empty dict (no crash)."""
        result = percentiles_from_cdf([], lower_bound=0, upper_bound=100)
        assert result == {}

    def test_small_cdf(self):
        """Very small CDF (e.g., 3 points) still works."""
        cdf = [0.0, 0.5, 1.0]
        result = percentiles_from_cdf(cdf, lower_bound=0, upper_bound=100)

        assert result["50"] == pytest.approx(50.0, abs=1.0)

    def test_discrete_cdf_size(self):
        """Should work with 102-point CDFs (discrete questions)."""
        cdf = [i / 101 for i in range(102)]
        result = percentiles_from_cdf(cdf, lower_bound=0, upper_bound=100)

        assert result["50"] == pytest.approx(50.0, abs=1.0)

    def test_default_percentiles(self):
        """Default target_percentiles should be [10, 25, 50, 75, 90]."""
        cdf = self._make_linear_cdf(0, 100)
        result = percentiles_from_cdf(cdf, lower_bound=0, upper_bound=100)
        assert set(result.keys()) == {"10", "25", "50", "75", "90"}
