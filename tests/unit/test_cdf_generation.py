"""
Tests for CDF generation in numeric forecasting.

Tests the functions in src/bot/cdf.py:
- generate_continuous_cdf()
- _safe_cdf_bounds()

And src/bot/extractors.py:
- enforce_strict_increasing()

These are critical for Metaculus submission validity.
"""

import pytest
import numpy as np
from typing import Dict

from src.bot.cdf import (
    generate_continuous_cdf,
    _safe_cdf_bounds,
)
from src.bot.extractors import enforce_strict_increasing
from src.bot.exceptions import CDFGenerationError


class TestGenerateContinuousCDF:
    """Tests for generate_continuous_cdf()"""

    @pytest.fixture
    def simple_percentiles(self) -> Dict[int, float]:
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
            assert cdf[i] <= cdf[i + 1], f"CDF not monotonic at index {i}: {cdf[i]} > {cdf[i+1]}"

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
        assert cdf[-1] == pytest.approx(1.0, abs=1e-9), f"Closed upper bound violated: {cdf[-1]} != 1"

    def test_max_step_constraint(self, simple_percentiles):
        """Test that no single step exceeds 0.59 (Metaculus requirement)."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
        )
        steps = np.diff(cdf)
        assert np.all(steps <= 0.59), f"Max step exceeded: {np.max(steps)} > 0.59"

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


class TestSafeCdfBounds:
    """Tests for _safe_cdf_bounds()"""

    def test_enforces_open_lower_bound(self):
        """Test that open lower bound pins first value to >= 0.001."""
        cdf = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
        result = _safe_cdf_bounds(cdf, open_lower=True, open_upper=False, step=5e-5)
        assert result[0] >= 0.001

    def test_enforces_open_upper_bound(self):
        """Test that open upper bound pins last value to <= 0.999."""
        cdf = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
        result = _safe_cdf_bounds(cdf, open_lower=False, open_upper=True, step=5e-5)
        assert result[-1] <= 0.999

    def test_fixes_large_jumps(self):
        """Test that jumps > 0.59 are corrected."""
        cdf = np.array([0.0, 0.1, 0.8, 0.85, 0.9])  # 0.1 -> 0.8 = 0.7 jump > 0.59
        result = _safe_cdf_bounds(cdf, open_lower=False, open_upper=False, step=5e-5)
        steps = np.diff(result)
        assert np.all(steps <= 0.59 + 1e-6), f"Large jump still present: {np.max(steps)}"

    def test_preserves_monotonicity(self):
        """Test that result is still monotonically increasing."""
        cdf = np.array([0.0, 0.1, 0.8, 0.85, 0.9, 0.95, 1.0])
        result = _safe_cdf_bounds(cdf, open_lower=False, open_upper=False, step=5e-5)
        assert np.all(np.diff(result) >= 0), "Monotonicity violated"


class TestEnforceStrictIncreasing:
    """Tests for enforce_strict_increasing()"""

    def test_already_increasing_unchanged(self):
        """Test that already increasing values are unchanged."""
        pct = {1: 10, 50: 50, 99: 100}
        result = enforce_strict_increasing(pct)
        assert result == {1: 10, 50: 50, 99: 100}

    def test_fixes_duplicate_values(self):
        """Test that duplicate values get small offset."""
        pct = {1: 10, 10: 10, 50: 50}
        result = enforce_strict_increasing(pct)
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
            enforce_strict_increasing(pct)

    def test_preserves_key_order(self):
        """Test that percentile keys are preserved."""
        pct = {1: 10, 50: 20, 99: 30}
        result = enforce_strict_increasing(pct)
        assert set(result.keys()) == {1, 50, 99}


class TestDiscreteCDF:
    """Tests for discrete question CDF generation (102 points instead of 201)."""

    @pytest.fixture
    def simple_percentiles(self) -> Dict[int, float]:
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
        """Test that no single step exceeds 0.59 with 102 points."""
        cdf = generate_continuous_cdf(
            percentile_values=simple_percentiles,
            open_upper_bound=True,
            open_lower_bound=True,
            upper_bound=120,
            lower_bound=0,
            num_points=102,
        )
        steps = np.diff(cdf)
        assert np.all(steps <= 0.59), f"Max step exceeded: {np.max(steps)} > 0.59"

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
        valid_keys = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99]
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
