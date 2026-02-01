"""
Tests for artifact storage system.

Tests cover:
- Creating forecast artifact containers
- Saving and loading various artifact types
- Config hashing
- Listing forecasts
"""

import pytest
import json
from pathlib import Path

from src.storage.artifact_store import ArtifactStore, ForecastArtifacts


# ============================================================================
# ForecastArtifacts Tests
# ============================================================================

class TestForecastArtifacts:
    """Tests for ForecastArtifacts dataclass."""

    def test_creates_directory_structure(self, tmp_path):
        """Creates all required directories on init."""
        artifacts = ForecastArtifacts(
            question_id=12345,
            timestamp="20260101_120000",
            base_dir=tmp_path,
        )

        assert artifacts.forecast_dir.exists()
        assert artifacts.research_dir.exists()
        assert artifacts.ensemble_dir.exists()
        assert artifacts.forecast_dir == tmp_path / "12345_20260101_120000"

    def test_sets_correct_paths(self, tmp_path):
        """Sets all artifact paths correctly."""
        artifacts = ForecastArtifacts(
            question_id=12345,
            timestamp="20260101_120000",
            base_dir=tmp_path,
        )

        assert artifacts.question_path == artifacts.forecast_dir / "question.json"
        assert artifacts.prediction_path == artifacts.forecast_dir / "prediction.json"
        assert artifacts.metadata_path == artifacts.forecast_dir / "metadata.json"
        assert artifacts.research_dir == artifacts.forecast_dir / "research"
        assert artifacts.ensemble_dir == artifacts.forecast_dir / "ensemble"


# ============================================================================
# ArtifactStore Tests
# ============================================================================

class TestArtifactStore:
    """Tests for ArtifactStore class."""

    def test_create_forecast_artifacts(self, tmp_path):
        """Creates artifact container with unique timestamp."""
        store = ArtifactStore(base_dir=tmp_path)

        artifacts = store.create_forecast_artifacts(question_id=12345)

        assert artifacts.question_id == 12345
        assert artifacts.timestamp is not None
        assert artifacts.forecast_dir.exists()

    def test_save_question(self, tmp_path):
        """Saves question JSON to correct path."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        question_data = {"id": 12345, "title": "Test Question"}

        store.save_question(artifacts, question_data)

        assert artifacts.question_path.exists()
        with open(artifacts.question_path) as f:
            saved = json.load(f)
        assert saved == question_data

    def test_save_query_generation(self, tmp_path):
        """Saves prompt and response to separate files."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)

        store.save_query_generation(artifacts, "historical", "test prompt", "test response")

        prompt_path = artifacts.research_dir / "query_historical_prompt.md"
        response_path = artifacts.research_dir / "query_historical.md"

        assert prompt_path.exists()
        assert response_path.exists()
        assert prompt_path.read_text() == "test prompt"
        assert response_path.read_text() == "test response"

    def test_save_search_results(self, tmp_path):
        """Saves search results JSON."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        results = {"context": "search context", "sources": ["url1", "url2"]}

        store.save_search_results(artifacts, "current", results)

        path = artifacts.research_dir / "search_current.json"
        assert path.exists()
        with open(path) as f:
            saved = json.load(f)
        assert saved == results

    def test_save_step1_prompt(self, tmp_path):
        """Saves step 1 prompt to ensemble directory."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)

        store.save_step1_prompt(artifacts, "Step 1 prompt content")

        path = artifacts.ensemble_dir / "step1_prompt.md"
        assert path.exists()
        assert path.read_text() == "Step 1 prompt content"

    def test_save_agent_step1(self, tmp_path):
        """Saves agent step 1 response."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)

        store.save_agent_step1(artifacts, 1, "Agent 1 step 1 response")

        path = artifacts.ensemble_dir / "agent_1_step1.md"
        assert path.exists()
        assert path.read_text() == "Agent 1 step 1 response"

    def test_save_agent_step2(self, tmp_path):
        """Saves agent step 2 response."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)

        store.save_agent_step2(artifacts, 3, "Agent 3 step 2 response")

        path = artifacts.ensemble_dir / "agent_3_step2.md"
        assert path.exists()
        assert path.read_text() == "Agent 3 step 2 response"

    def test_save_agent_extracted(self, tmp_path):
        """Saves extracted prediction JSON."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        extracted = {"probability": 0.65, "error": None}

        store.save_agent_extracted(artifacts, 2, extracted)

        path = artifacts.ensemble_dir / "agent_2.json"
        assert path.exists()
        with open(path) as f:
            saved = json.load(f)
        assert saved == extracted

    def test_save_aggregation(self, tmp_path):
        """Saves aggregation result JSON."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        aggregation = {
            "individual_probabilities": [0.5, 0.6, 0.7],
            "weights": [1.0, 1.0, 1.0],
            "method": "weighted_average",
            "final_prediction": 0.6,
        }

        store.save_aggregation(artifacts, aggregation)

        path = artifacts.ensemble_dir / "aggregation.json"
        assert path.exists()
        with open(path) as f:
            saved = json.load(f)
        assert saved == aggregation

    def test_save_tool_usage(self, tmp_path):
        """Saves tool usage tracking JSON."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        tool_usage = {
            "centralized_research": {"historical": {}, "current": {}},
            "agents": {"forecaster_1": {"step1": {}, "step2": {}}},
        }

        store.save_tool_usage(artifacts, tool_usage)

        path = artifacts.forecast_dir / "tool_usage.json"
        assert path.exists()
        with open(path) as f:
            saved = json.load(f)
        assert saved == tool_usage

    def test_save_prediction(self, tmp_path):
        """Saves final prediction JSON."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        prediction = {"prediction": 0.65, "submitted": True}

        store.save_prediction(artifacts, prediction)

        assert artifacts.prediction_path.exists()
        with open(artifacts.prediction_path) as f:
            saved = json.load(f)
        assert saved == prediction

    def test_save_api_response(self, tmp_path):
        """Saves API response JSON."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        response = {"status": "success", "id": 123}

        store.save_api_response(artifacts, response)

        path = artifacts.forecast_dir / "api_response.json"
        assert path.exists()
        with open(path) as f:
            saved = json.load(f)
        assert saved == response

    def test_save_metadata(self, tmp_path):
        """Saves metadata with all fields."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        config = {"mode": "test"}
        costs = {"total_cost": 0.05}
        timing = {"duration_seconds": 30.0}
        analysis = {"type": "binary"}

        store.save_metadata(artifacts, config, costs, timing, analysis)

        assert artifacts.metadata_path.exists()
        with open(artifacts.metadata_path) as f:
            saved = json.load(f)
        assert saved["question_id"] == 12345
        assert saved["config_snapshot"] == config
        assert saved["costs"] == costs
        assert saved["timing"] == timing
        assert saved["analysis"] == analysis
        assert "config_hash" in saved

    def test_save_metadata_with_errors(self, tmp_path):
        """Saves metadata with error list."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)

        store.save_metadata(
            artifacts,
            config={},
            costs={},
            timing={},
            errors=["Error 1", "Error 2"],
        )

        with open(artifacts.metadata_path) as f:
            saved = json.load(f)
        assert saved["errors"] == ["Error 1", "Error 2"]


# ============================================================================
# Config Hash Tests
# ============================================================================

class TestConfigHash:
    """Tests for config hashing."""

    def test_config_hash_deterministic(self, tmp_path):
        """Same config produces same hash."""
        store = ArtifactStore(base_dir=tmp_path)
        config = {"mode": "test", "key": "value"}

        hash1 = store._hash_config(config)
        hash2 = store._hash_config(config)

        assert hash1 == hash2

    def test_config_hash_different_for_different_configs(self, tmp_path):
        """Different configs produce different hashes."""
        store = ArtifactStore(base_dir=tmp_path)
        config1 = {"mode": "test"}
        config2 = {"mode": "live"}

        hash1 = store._hash_config(config1)
        hash2 = store._hash_config(config2)

        assert hash1 != hash2

    def test_config_hash_is_12_chars(self, tmp_path):
        """Config hash is truncated to 12 characters."""
        store = ArtifactStore(base_dir=tmp_path)
        config = {"mode": "test"}

        hash_value = store._hash_config(config)

        assert len(hash_value) == 12


# ============================================================================
# Load Artifacts Tests
# ============================================================================

class TestLoadArtifacts:
    """Tests for loading artifacts."""

    def test_load_artifacts_returns_none_for_missing(self, tmp_path):
        """Returns None when forecast directory doesn't exist."""
        store = ArtifactStore(base_dir=tmp_path)

        result = store.load_artifacts(99999, "20260101_120000")

        assert result is None

    def test_load_artifacts_returns_all_files(self, tmp_path):
        """Returns all JSON and markdown files."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)

        # Save some files
        store.save_question(artifacts, {"id": 12345})
        store.save_step1_prompt(artifacts, "Prompt content")

        result = store.load_artifacts(artifacts.question_id, artifacts.timestamp)

        assert result is not None
        assert "question.json" in result
        assert result["question.json"] == {"id": 12345}
        assert "ensemble/step1_prompt.md" in result
        assert result["ensemble/step1_prompt.md"] == "Prompt content"


# ============================================================================
# List Forecasts Tests
# ============================================================================

class TestListForecasts:
    """Tests for listing forecasts."""

    def test_list_forecasts_empty(self, tmp_path):
        """Returns empty list when no forecasts exist."""
        store = ArtifactStore(base_dir=tmp_path)

        result = store.list_forecasts()

        assert result == []

    def test_list_forecasts_returns_all(self, tmp_path):
        """Returns all forecasts."""
        store = ArtifactStore(base_dir=tmp_path)

        # Create some forecasts
        artifacts1 = store.create_forecast_artifacts(12345)
        artifacts2 = store.create_forecast_artifacts(12346)
        store.save_metadata(artifacts1, {}, {}, {})
        store.save_metadata(artifacts2, {}, {}, {})

        result = store.list_forecasts()

        assert len(result) == 2
        question_ids = {f["question_id"] for f in result}
        assert question_ids == {12345, 12346}

    def test_list_forecasts_filters_by_question(self, tmp_path):
        """Filters by question_id when provided."""
        store = ArtifactStore(base_dir=tmp_path)

        # Create forecasts for different questions
        artifacts1 = store.create_forecast_artifacts(12345)
        artifacts2 = store.create_forecast_artifacts(12346)
        store.save_metadata(artifacts1, {}, {}, {})
        store.save_metadata(artifacts2, {}, {}, {})

        result = store.list_forecasts(question_id=12345)

        assert len(result) == 1
        assert result[0]["question_id"] == 12345

    def test_list_forecasts_includes_metadata(self, tmp_path):
        """Includes metadata when available."""
        store = ArtifactStore(base_dir=tmp_path)
        artifacts = store.create_forecast_artifacts(12345)
        store.save_metadata(artifacts, {"mode": "test"}, {"total_cost": 0.05}, {})

        result = store.list_forecasts()

        assert len(result) == 1
        assert result[0]["metadata"] is not None
        assert result[0]["metadata"]["config_snapshot"]["mode"] == "test"

    def test_list_forecasts_sorted_by_timestamp(self, tmp_path):
        """Results sorted by timestamp, newest first."""
        store = ArtifactStore(base_dir=tmp_path)

        # Create with explicit timestamps
        artifacts1 = ForecastArtifacts(12345, "20260101_100000", tmp_path)
        artifacts2 = ForecastArtifacts(12345, "20260101_120000", tmp_path)
        store.save_metadata(artifacts1, {}, {}, {})
        store.save_metadata(artifacts2, {}, {}, {})

        result = store.list_forecasts()

        assert len(result) == 2
        assert result[0]["timestamp"] == "20260101_120000"  # Newer first
        assert result[1]["timestamp"] == "20260101_100000"
