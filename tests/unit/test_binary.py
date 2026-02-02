"""
Tests for binary question handler.

Tests cover:
- _aggregate_results() for weighted averaging with partial failures
- Probability normalization to API bounds
"""

from unittest.mock import MagicMock

import pytest

from src.bot.binary import BinaryForecaster
from src.bot.exceptions import InsufficientPredictionsError
from src.bot.extractors import AgentResult

# ============================================================================
# Binary Aggregation Tests
# ============================================================================


class TestBinaryAggregation:
    """Tests for _aggregate_results() weighted averaging."""

    @pytest.fixture
    def forecaster(self):
        """Create a BinaryForecaster with minimal config."""
        config = {
            "_active_agents": [
                {"name": "forecaster_1", "model": "test", "weight": 1.0},
                {"name": "forecaster_2", "model": "test", "weight": 1.0},
                {"name": "forecaster_3", "model": "test", "weight": 1.0},
                {"name": "forecaster_4", "model": "test", "weight": 1.0},
                {"name": "forecaster_5", "model": "test", "weight": 1.0},
            ]
        }
        return BinaryForecaster(config=config)

    @pytest.fixture
    def agents(self):
        """Agent configs with weights."""
        return [
            {"name": "forecaster_1", "model": "test", "weight": 1.0},
            {"name": "forecaster_2", "model": "test", "weight": 1.0},
            {"name": "forecaster_3", "model": "test", "weight": 1.0},
            {"name": "forecaster_4", "model": "test", "weight": 1.0},
            {"name": "forecaster_5", "model": "test", "weight": 1.0},
        ]

    def test_aggregation_all_valid(self, forecaster, agents, forecaster_results_all_successful):
        """All 5 agents valid → weighted average."""
        write = MagicMock()

        result = forecaster._aggregate_results(forecaster_results_all_successful, agents, write)

        # Probabilities are 50, 55, 60, 65, 70 (percent)
        # Average = 60%, normalized to 0.60
        assert result == pytest.approx(0.60, rel=0.01)
        # Should have called write for logging
        assert write.called

    def test_aggregation_some_none(self, forecaster, agents, forecaster_results_partial_failures):
        """Agents with None probabilities are excluded from averaging."""
        write = MagicMock()

        result = forecaster._aggregate_results(forecaster_results_partial_failures, agents, write)

        # Only first 2 agents valid (both 55%), so average = 55%
        # Normalized to 0.55
        assert result == pytest.approx(0.55, rel=0.01)

    def test_aggregation_all_failed(self, forecaster, agents, forecaster_results_all_failed):
        """All agents failed → raises InsufficientPredictionsError."""
        write = MagicMock()

        with pytest.raises(InsufficientPredictionsError) as exc_info:
            forecaster._aggregate_results(forecaster_results_all_failed, agents, write)

        assert exc_info.value.valid_count == 0
        assert exc_info.value.total_count == 5

    def test_aggregation_normalizes_to_api_bounds(self, forecaster, agents):
        """Result clamped to [0.001, 0.999]."""
        write = MagicMock()

        # Agent results with extreme probabilities
        extreme_high_results = [
            AgentResult(
                agent_id=f"forecaster_{i + 1}",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                probability=99.5,
            )
            for i in range(5)
        ]

        result = forecaster._aggregate_results(extreme_high_results, agents, write)

        # 99.5% normalized = 0.995, but clamped to 0.999
        assert result <= 0.999

        # Agent results with very low probabilities
        extreme_low_results = [
            AgentResult(
                agent_id=f"forecaster_{i + 1}",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                probability=0.05,
            )
            for i in range(5)
        ]

        result = forecaster._aggregate_results(extreme_low_results, agents, write)

        # 0.05% normalized = 0.0005, but clamped to 0.001
        assert result >= 0.001

    def test_aggregation_weighted_by_weight(self, forecaster):
        """Weights are applied correctly in averaging."""
        write = MagicMock()

        # Different weights
        agents = [
            {"name": "forecaster_1", "model": "test", "weight": 2.0},  # Weight 2
            {"name": "forecaster_2", "model": "test", "weight": 1.0},  # Weight 1
        ]

        results = [
            AgentResult(
                agent_id="forecaster_1",
                model="test",
                weight=2.0,
                outside_view_output="",
                inside_view_output="",
                probability=60.0,
            ),  # 60%
            AgentResult(
                agent_id="forecaster_2",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                probability=30.0,
            ),  # 30%
        ]

        result = forecaster._aggregate_results(results, agents, write)

        # Weighted average: (60*2 + 30*1) / (2+1) = 150/3 = 50%
        # Normalized: 0.50
        assert result == pytest.approx(0.50, rel=0.01)

    def test_aggregation_single_valid(self, forecaster, agents):
        """Single valid agent still produces result."""
        write = MagicMock()

        results = [
            AgentResult(
                agent_id="forecaster_1",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                probability=75.0,
            ),
        ] + [
            AgentResult(
                agent_id=f"forecaster_{i + 2}",
                model="test",
                weight=1.0,
                outside_view_output="",
                inside_view_output="",
                probability=None,
                error="Failed",
            )
            for i in range(4)
        ]

        result = forecaster._aggregate_results(results, agents, write)

        # Only one valid at 75%, normalized to 0.75
        assert result == pytest.approx(0.75, rel=0.01)


# ============================================================================
# BinaryForecaster Method Tests
# ============================================================================


class TestBinaryForecasterMethods:
    """Tests for other BinaryForecaster methods."""

    @pytest.fixture
    def forecaster(self):
        """Create a BinaryForecaster with minimal config."""
        return BinaryForecaster(config={})

    def test_get_prompt_templates(self, forecaster):
        """Returns 4 prompt templates."""
        templates = forecaster._get_prompt_templates()

        assert len(templates) == 4
        # All should be non-empty strings
        for template in templates:
            assert isinstance(template, str)
            assert len(template) > 0

    def test_build_agent_result(self, forecaster):
        """Builds AgentResult with correct fields."""
        result = forecaster._build_agent_result(
            agent_id="forecaster_1",
            model="test-model",
            weight=1.5,
            outside_view_output="Step 1",
            inside_view_output="Step 2",
            prediction=55.0,
            error=None,
        )

        assert result.agent_id == "forecaster_1"
        assert result.model == "test-model"
        assert result.weight == 1.5
        assert result.outside_view_output == "Step 1"
        assert result.inside_view_output == "Step 2"
        assert result.probability == 55.0
        assert result.error is None

    def test_build_agent_result_with_error(self, forecaster):
        """Builds AgentResult with error field."""
        result = forecaster._build_agent_result(
            agent_id="forecaster_1",
            model="test-model",
            weight=1.0,
            outside_view_output="Step 1",
            inside_view_output="",
            prediction=None,
            error="Extraction failed",
        )

        assert result.probability is None
        assert result.error == "Extraction failed"

    def test_get_extracted_data(self, forecaster):
        """Returns dict with probability and error."""
        result = AgentResult(
            agent_id="forecaster_1",
            model="test",
            weight=1.0,
            outside_view_output="",
            inside_view_output="",
            probability=65.0,
            error=None,
        )

        data = forecaster._get_extracted_data(result)

        assert data == {"probability": 65.0, "error": None}

    def test_get_aggregation_data(self, forecaster, forecaster_results_all_successful):
        """Returns dict with aggregation info."""
        agents = [{"name": f"f{i + 1}", "model": "test", "weight": 1.0} for i in range(5)]

        data = forecaster._get_aggregation_data(forecaster_results_all_successful, agents, 0.60)

        assert data["method"] == "weighted_average"
        assert data["final_probability"] == 0.60
        assert len(data["individual_probabilities"]) == 5
        assert len(data["weights"]) == 5
