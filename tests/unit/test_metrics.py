"""
Tests for src/bot/metrics.py - Pipeline metrics dataclasses.
"""

import pytest
from src.bot.metrics import (
    StepMetrics,
    AgentMetrics,
    ResearchMetrics,
    PipelineMetrics,
)


# ============================================================================
# StepMetrics Tests
# ============================================================================

class TestStepMetrics:
    """Tests for StepMetrics dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        metrics = StepMetrics()
        assert metrics.searched is False
        assert metrics.queries == []
        assert metrics.token_input == 0
        assert metrics.token_output == 0
        assert metrics.cost == 0.0
        assert metrics.duration_seconds == 0.0
        assert metrics.error is None

    def test_to_dict(self):
        """to_dict produces correct structure."""
        metrics = StepMetrics(
            token_input=100,
            token_output=50,
            cost=0.01,
            duration_seconds=1.5,
        )
        result = metrics.to_dict()

        assert result["token_input"] == 100
        assert result["token_output"] == 50
        assert result["cost"] == 0.01
        assert result["duration_seconds"] == 1.5
        assert result["error"] is None
        # Legacy fields present
        assert result["searched"] is False
        assert result["queries"] == []

    def test_to_dict_with_error(self):
        """to_dict includes error when present."""
        metrics = StepMetrics(error="Model call failed")
        result = metrics.to_dict()
        assert result["error"] == "Model call failed"

    def test_mutable_default(self):
        """Queries list is not shared between instances."""
        m1 = StepMetrics()
        m2 = StepMetrics()
        m1.queries.append("test")
        assert m2.queries == []  # Should not be affected


# ============================================================================
# AgentMetrics Tests
# ============================================================================

class TestAgentMetrics:
    """Tests for AgentMetrics dataclass."""

    def test_initialization(self):
        """Required fields must be provided."""
        metrics = AgentMetrics(model="test-model", weight=1.0)
        assert metrics.model == "test-model"
        assert metrics.weight == 1.0
        assert isinstance(metrics.step1, StepMetrics)
        assert isinstance(metrics.step2, StepMetrics)

    def test_to_dict(self):
        """to_dict produces nested structure."""
        metrics = AgentMetrics(model="test-model", weight=0.5)
        metrics.step1.token_input = 100
        metrics.step2.cost = 0.02

        result = metrics.to_dict()

        assert result["model"] == "test-model"
        assert result["weight"] == 0.5
        assert result["step1"]["token_input"] == 100
        assert result["step2"]["cost"] == 0.02

    def test_step_metrics_are_independent(self):
        """step1 and step2 are separate instances."""
        metrics = AgentMetrics(model="test", weight=1.0)
        metrics.step1.cost = 0.01
        assert metrics.step2.cost == 0.0  # Should not be affected


# ============================================================================
# ResearchMetrics Tests
# ============================================================================

class TestResearchMetrics:
    """Tests for ResearchMetrics dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        metrics = ResearchMetrics()
        assert metrics.search_id == ""
        assert metrics.searched is False
        assert metrics.num_queries == 0
        assert metrics.queries == []
        assert metrics.tools_used == []
        assert metrics.llm_cost == 0.0
        assert metrics.llm_cost_summarization == 0.0
        assert metrics.llm_cost_agentic == 0.0
        assert metrics.error is None

    def test_from_search_metadata_complete(self):
        """from_search_metadata populates all fields."""
        metadata = {
            "search_id": "historical",
            "searched": True,
            "num_queries": 3,
            "queries": [{"query": "test", "tool": "Google"}],
            "tools_used": ["Google", "AskNews"],
            "llm_cost": 0.05,
            "llm_cost_summarization": 0.03,
            "llm_cost_agentic": 0.02,
            "error": None,
        }

        metrics = ResearchMetrics.from_search_metadata(metadata)

        assert metrics.search_id == "historical"
        assert metrics.searched is True
        assert metrics.num_queries == 3
        assert metrics.queries == [{"query": "test", "tool": "Google"}]
        assert metrics.tools_used == ["Google", "AskNews"]
        assert metrics.llm_cost == 0.05
        assert metrics.llm_cost_summarization == 0.03
        assert metrics.llm_cost_agentic == 0.02
        assert metrics.error is None

    def test_from_search_metadata_partial(self):
        """from_search_metadata handles missing fields with defaults."""
        metadata = {"search_id": "current", "searched": True}

        metrics = ResearchMetrics.from_search_metadata(metadata)

        assert metrics.search_id == "current"
        assert metrics.searched is True
        assert metrics.num_queries == 0  # Default
        assert metrics.queries == []  # Default
        assert metrics.tools_used == []  # Default

    def test_from_search_metadata_empty(self):
        """from_search_metadata handles empty dict."""
        metrics = ResearchMetrics.from_search_metadata({})

        assert metrics.search_id == ""
        assert metrics.searched is False

    def test_to_dict(self):
        """to_dict produces correct structure."""
        metrics = ResearchMetrics(
            search_id="historical",
            searched=True,
            num_queries=2,
            llm_cost=0.01,
        )
        result = metrics.to_dict()

        assert result["search_id"] == "historical"
        assert result["searched"] is True
        assert result["num_queries"] == 2
        assert result["llm_cost"] == 0.01


# ============================================================================
# PipelineMetrics Tests
# ============================================================================

class TestPipelineMetrics:
    """Tests for PipelineMetrics dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        metrics = PipelineMetrics()
        assert metrics.centralized_research == {}
        assert metrics.agents == {}
        assert metrics.step_costs == {}
        assert metrics.total_pipeline_cost == 0.0

    def test_create_empty(self):
        """create_empty initializes with historical and current research."""
        metrics = PipelineMetrics.create_empty()

        assert "historical" in metrics.centralized_research
        assert "current" in metrics.centralized_research
        assert metrics.centralized_research["historical"].search_id == "historical"
        assert metrics.centralized_research["current"].search_id == "current"
        assert metrics.agents == {}
        assert metrics.step_costs == {}

    def test_to_dict_structure(self):
        """to_dict produces correct nested structure."""
        metrics = PipelineMetrics.create_empty()
        metrics.agents["forecaster_1"] = AgentMetrics(model="test", weight=1.0)
        metrics.step_costs["step1"] = 0.05
        metrics.total_pipeline_cost = 0.10

        result = metrics.to_dict()

        # Check top-level keys
        assert "centralized_research" in result
        assert "agents" in result
        assert "step_costs" in result
        assert "total_pipeline_cost" in result

        # Check nested research
        assert "historical" in result["centralized_research"]
        assert result["centralized_research"]["historical"]["search_id"] == "historical"

        # Check nested agents
        assert "forecaster_1" in result["agents"]
        assert result["agents"]["forecaster_1"]["model"] == "test"
        assert "step1" in result["agents"]["forecaster_1"]
        assert "step2" in result["agents"]["forecaster_1"]

        # Check costs
        assert result["step_costs"]["step1"] == 0.05
        assert result["total_pipeline_cost"] == 0.10

    def test_to_dict_is_json_serializable(self):
        """to_dict output can be serialized to JSON."""
        import json

        metrics = PipelineMetrics.create_empty()
        metrics.agents["forecaster_1"] = AgentMetrics(model="test", weight=1.0)
        metrics.agents["forecaster_1"].step1.token_input = 100
        metrics.step_costs["query_gen"] = 0.01

        result = metrics.to_dict()

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["agents"]["forecaster_1"]["step1"]["token_input"] == 100
