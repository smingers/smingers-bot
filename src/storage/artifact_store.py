"""
Artifact Storage System

Persists all intermediate outputs from the forecasting pipeline.
Nothing is ephemeral - every step produces a recorded artifact.

Directory structure per question:
    data/{question_id}_{timestamp}/
        question.json              # Full raw question from Metaculus API
        research/
            query_historical.md        # LLM-generated historical search queries
            query_current.md           # LLM-generated current search queries
            search_historical.json     # Search results for outside view
            search_current.json        # Search results for inside view
        ensemble/
            outside_view_prompt.md     # Shared prompt for outside view prediction
            forecaster_{1-5}_outside_view.md   # Forecaster responses for outside view
            forecaster_{1-5}_inside_view.md    # Forecaster responses for inside view
            forecaster_{1-5}.json      # Extracted predictions per forecaster
            aggregation.json           # Final aggregation of all forecasters
        prediction.json            # Final prediction submitted to Metaculus
        metadata.json              # Config, costs, timing, analysis
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ForecastArtifactPaths:
    """Container for all artifacts from a single forecast."""

    question_id: int
    timestamp: str
    base_dir: Path

    # Paths to artifact files and directories
    forecast_dir: Path = field(init=False)
    question_path: Path = field(init=False)
    research_dir: Path = field(init=False)
    ensemble_dir: Path = field(init=False)
    prediction_path: Path = field(init=False)
    metadata_path: Path = field(init=False)

    def __post_init__(self):
        """Set up all artifact paths."""
        self.forecast_dir = self.base_dir / f"{self.question_id}_{self.timestamp}"
        self.forecast_dir.mkdir(parents=True, exist_ok=True)

        self.question_path = self.forecast_dir / "question.json"
        self.research_dir = self.forecast_dir / "research"
        self.ensemble_dir = self.forecast_dir / "ensemble"
        self.prediction_path = self.forecast_dir / "prediction.json"
        self.metadata_path = self.forecast_dir / "metadata.json"

        # Create subdirectories
        self.research_dir.mkdir(exist_ok=True)
        self.ensemble_dir.mkdir(exist_ok=True)


class ArtifactStore:
    """
    Manages storage of all forecasting artifacts.

    See module docstring for directory structure.
    """

    def __init__(self, base_dir: str | Path = "./data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_forecast_artifacts(self, question_id: int) -> ForecastArtifactPaths:
        """Create a new artifact container for a forecast."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return ForecastArtifactPaths(
            question_id=question_id, timestamp=timestamp, base_dir=self.base_dir
        )

    # =========================================================================
    # Question
    # =========================================================================

    def save_question(self, artifacts: ForecastArtifactPaths, question: dict) -> None:
        """Save the raw question from Metaculus API."""
        self._write_json(artifacts.question_path, question)

    # =========================================================================
    # Research
    # =========================================================================

    def save_query_generation(
        self,
        artifacts: ForecastArtifactPaths,
        search_phase: str,
        prompt: str,
        response: str,
    ) -> None:
        """
        Save query generation prompt and response.

        Args:
            artifacts: ForecastArtifactPaths container
            search_phase: "historical" or "current"
            prompt: The prompt sent to generate queries
            response: The LLM response with generated queries
        """
        self._write_text(
            artifacts.research_dir / f"query_{search_phase}_prompt.md",
            prompt,
        )
        self._write_text(
            artifacts.research_dir / f"query_{search_phase}.md",
            response,
        )

    def save_search_results(
        self,
        artifacts: ForecastArtifactPaths,
        search_phase: str,
        results: dict | list,
    ) -> None:
        """
        Save search results.

        Args:
            artifacts: ForecastArtifactPaths container
            search_phase: Phase name — "historical", "current", "question_urls",
                "community_prediction", or any other phase. Writes to
                research/search_{search_phase}.json.
            results: Search results data
        """
        self._write_json(artifacts.research_dir / f"search_{search_phase}.json", results)

    # =========================================================================
    # Ensemble
    # =========================================================================

    def save_outside_view_prompt(self, artifacts: ForecastArtifactPaths, prompt: str) -> None:
        """Save the shared outside view prompt."""
        self._write_text(artifacts.ensemble_dir / "outside_view_prompt.md", prompt)

    def save_forecaster_outside_view(
        self,
        artifacts: ForecastArtifactPaths,
        forecaster_num: int,
        response: str,
    ) -> None:
        """Save a forecaster's outside view response."""
        self._write_text(
            artifacts.ensemble_dir / f"forecaster_{forecaster_num}_outside_view.md", response
        )

    def save_forecaster_inside_view(
        self,
        artifacts: ForecastArtifactPaths,
        forecaster_num: int,
        response: str,
    ) -> None:
        """Save a forecaster's inside view response."""
        self._write_text(
            artifacts.ensemble_dir / f"forecaster_{forecaster_num}_inside_view.md", response
        )

    def save_forecaster_prediction(
        self,
        artifacts: ForecastArtifactPaths,
        forecaster_num: int,
        extracted: dict,
    ) -> None:
        """Save the parsed prediction from a specific forecaster."""
        self._write_json(artifacts.ensemble_dir / f"forecaster_{forecaster_num}.json", extracted)

    def save_aggregation(self, artifacts: ForecastArtifactPaths, aggregation: dict) -> None:
        """Save how individual forecasts were combined."""
        self._write_json(artifacts.ensemble_dir / "aggregation.json", aggregation)

    # =========================================================================
    # Supervisor
    # =========================================================================

    def save_supervisor_analysis(self, artifacts: ForecastArtifactPaths, analysis: str) -> None:
        """Save the supervisor's disagreement analysis (stage 1 output)."""
        self._write_text(artifacts.ensemble_dir / "supervisor_analysis.md", analysis)

    def save_supervisor_research(self, artifacts: ForecastArtifactPaths, research: str) -> None:
        """Save the supervisor's targeted research results."""
        self._write_text(artifacts.ensemble_dir / "supervisor_research.md", research)

    def save_supervisor_reasoning(self, artifacts: ForecastArtifactPaths, reasoning: str) -> None:
        """Save the supervisor's updated reasoning (stage 2 output)."""
        self._write_text(artifacts.ensemble_dir / "supervisor_reasoning.md", reasoning)

    def save_supervisor_result(self, artifacts: ForecastArtifactPaths, result: dict) -> None:
        """Save the supervisor's structured result."""
        self._write_json(artifacts.ensemble_dir / "supervisor_result.json", result)

    # =========================================================================
    # Tool Usage
    # =========================================================================

    def save_tool_usage(self, artifacts: ForecastArtifactPaths, tool_usage: dict) -> None:
        """
        Save tool usage tracking data.

        Args:
            artifacts: ForecastArtifactPaths container
            tool_usage: Dict containing centralized_research and agents sections
        """
        self._write_json(artifacts.forecast_dir / "tool_usage.json", tool_usage)

    # =========================================================================
    # Prediction
    # =========================================================================

    def save_prediction(self, artifacts: ForecastArtifactPaths, prediction: dict) -> None:
        """Save the final prediction."""
        self._write_json(artifacts.prediction_path, prediction)

    def save_api_response(self, artifacts: ForecastArtifactPaths, response: dict) -> None:
        """Save the Metaculus API response."""
        self._write_json(artifacts.forecast_dir / "api_response.json", response)

    # =========================================================================
    # Metadata
    # =========================================================================

    def save_metadata(
        self,
        artifacts: ForecastArtifactPaths,
        config: dict,
        costs: dict,
        timing: dict,
        analysis: dict | None = None,
        errors: list[str] | None = None,
        research_reuse: dict | None = None,
    ) -> None:
        """
        Save forecast metadata including config, costs, timing, and analysis.

        Args:
            artifacts: ForecastArtifactPaths container
            config: Configuration snapshot
            costs: Cost breakdown by component
            timing: Timing breakdown by component
            analysis: Question analysis (type, status, dates, community_prediction)
            errors: List of error messages encountered
            research_reuse: Info about reused research from previous runs
        """
        metadata = {
            "question_id": artifacts.question_id,
            "timestamp": artifacts.timestamp,
            "created_at": datetime.now(UTC).isoformat(),
            "config_hash": self._hash_config(config),
            "config_snapshot": config,
            "costs": costs,
            "timing": timing,
            "errors": errors or [],
        }

        # Include question analysis (previously separate 01_analysis.json)
        if analysis:
            metadata["analysis"] = analysis

        # Add research reuse info if applicable
        if research_reuse:
            metadata["research_reuse"] = research_reuse

        self._write_json(artifacts.metadata_path, metadata)

    # =========================================================================
    # Config Snapshots
    # =========================================================================

    def save_config_snapshot(self, config: dict, config_dir: str | Path = "./data/configs") -> str:
        """Save a config snapshot and return its hash."""
        config_dir = Path(config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)

        config_hash = self._hash_config(config)
        config_path = config_dir / f"{config_hash}.yaml"

        if not config_path.exists():
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)

        return config_hash

    # =========================================================================
    # Helpers
    # =========================================================================

    def _write_json(self, path: Path, data: Any) -> None:
        """Write data as JSON."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _write_text(self, path: Path, text: str) -> None:
        """Write text content."""
        with open(path, "w") as f:
            f.write(text)

    def _hash_config(self, config: dict) -> str:
        """Generate a hash of the config for reproducibility tracking."""
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:12]

    def load_artifacts(self, question_id: int, timestamp: str) -> dict | None:
        """Load all artifacts for a previous forecast."""
        forecast_dir = self.base_dir / f"{question_id}_{timestamp}"
        if not forecast_dir.exists():
            return None

        artifacts = {}

        # Load JSON files
        for json_file in forecast_dir.rglob("*.json"):
            relative_path = json_file.relative_to(forecast_dir)
            with open(json_file) as f:
                artifacts[str(relative_path)] = json.load(f)

        # Load markdown files
        for md_file in forecast_dir.rglob("*.md"):
            relative_path = md_file.relative_to(forecast_dir)
            with open(md_file) as f:
                artifacts[str(relative_path)] = f.read()

        return artifacts

    def list_forecasts(self, question_id: int | None = None) -> list[dict]:
        """List all forecasts, optionally filtered by question ID."""
        forecasts = []

        for forecast_dir in self.base_dir.iterdir():
            if not forecast_dir.is_dir():
                continue

            try:
                parts = forecast_dir.name.rsplit("_", 2)
                if len(parts) < 3:
                    continue

                qid = int(parts[0])
                timestamp = f"{parts[1]}_{parts[2]}"

                if question_id is not None and qid != question_id:
                    continue

                metadata_path = forecast_dir / "metadata.json"
                metadata = None
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)

                forecasts.append(
                    {
                        "question_id": qid,
                        "timestamp": timestamp,
                        "directory": str(forecast_dir),
                        "metadata": metadata,
                    }
                )
            except (ValueError, IndexError):
                continue

        return sorted(forecasts, key=lambda x: x["timestamp"], reverse=True)
