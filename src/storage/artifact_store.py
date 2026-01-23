"""
Artifact Storage System

Persists all intermediate outputs from the forecasting pipeline.
Nothing is ephemeral - every step produces a recorded artifact.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
import yaml
import shutil


@dataclass
class ForecastArtifacts:
    """Container for all artifacts from a single forecast."""
    question_id: int
    timestamp: str
    base_dir: Path

    # Paths to artifact directories
    question_path: Path = field(init=False)
    analysis_path: Path = field(init=False)
    research_dir: Path = field(init=False)
    outside_view_dir: Path = field(init=False)
    inside_view_dir: Path = field(init=False)
    calibration_dir: Path = field(init=False)
    submission_dir: Path = field(init=False)
    metadata_path: Path = field(init=False)

    def __post_init__(self):
        """Set up all artifact paths."""
        forecast_dir = self.base_dir / f"{self.question_id}_{self.timestamp}"
        forecast_dir.mkdir(parents=True, exist_ok=True)

        self.question_path = forecast_dir / "00_question.json"
        self.analysis_path = forecast_dir / "01_analysis.json"
        self.research_dir = forecast_dir / "02_research"
        self.outside_view_dir = forecast_dir / "03_outside_view"
        self.inside_view_dir = forecast_dir / "04_inside_view"
        self.calibration_dir = forecast_dir / "05_calibration"
        self.submission_dir = forecast_dir / "06_submission"
        self.metadata_path = forecast_dir / "metadata.json"

        # Create subdirectories
        for dir_path in [
            self.research_dir,
            self.outside_view_dir,
            self.inside_view_dir,
            self.calibration_dir,
            self.submission_dir,
        ]:
            dir_path.mkdir(exist_ok=True)


class ArtifactStore:
    """
    Manages storage of all forecasting artifacts.

    Directory structure per question:
    data/forecasts/{question_id}_{timestamp}/
        00_question.json
        01_analysis.json
        02_research/
            queries_generated.json
            google_search.json
            perplexity.json
            synthesis.md
        03_outside_view/
            prompt.md
            response.md
            extracted.json
        04_inside_view/
            agent_1/
                prompt.md
                response.md
                extracted.json
            agent_2/
                ...
            aggregation.json
        05_calibration/
            checklist.json
            adjustments.json
        06_submission/
            final_prediction.json
            api_response.json
            reasoning_report.md
        metadata.json
    """

    def __init__(self, base_dir: str | Path = "./data/forecasts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_forecast_artifacts(self, question_id: int) -> ForecastArtifacts:
        """Create a new artifact container for a forecast."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return ForecastArtifacts(
            question_id=question_id,
            timestamp=timestamp,
            base_dir=self.base_dir
        )

    # =========================================================================
    # Question & Analysis
    # =========================================================================

    def save_question(self, artifacts: ForecastArtifacts, question: dict) -> None:
        """Save the raw question from Metaculus API."""
        self._write_json(artifacts.question_path, question)

    def save_analysis(self, artifacts: ForecastArtifacts, analysis: dict) -> None:
        """Save question analysis (type, entities, timeframe, etc.)."""
        self._write_json(artifacts.analysis_path, analysis)

    # =========================================================================
    # Research
    # =========================================================================

    def save_research_queries(self, artifacts: ForecastArtifacts, queries: list[dict]) -> None:
        """Save the search queries that were generated."""
        self._write_json(artifacts.research_dir / "queries_generated.json", queries)

    def save_research_source(
        self,
        artifacts: ForecastArtifacts,
        source_name: str,
        results: dict | list
    ) -> None:
        """Save results from a research source (google, perplexity, etc.)."""
        self._write_json(artifacts.research_dir / f"{source_name}.json", results)

    def save_research_synthesis(self, artifacts: ForecastArtifacts, synthesis: str) -> None:
        """Save the combined research summary."""
        self._write_text(artifacts.research_dir / "synthesis.md", synthesis)

    # =========================================================================
    # Outside View
    # =========================================================================

    def save_outside_view_prompt(self, artifacts: ForecastArtifacts, prompt: str) -> None:
        """Save the exact prompt sent for outside view estimation."""
        self._write_text(artifacts.outside_view_dir / "prompt.md", prompt)

    def save_outside_view_response(self, artifacts: ForecastArtifacts, response: str) -> None:
        """Save the full LLM response for outside view."""
        self._write_text(artifacts.outside_view_dir / "response.md", response)

    def save_outside_view_extracted(self, artifacts: ForecastArtifacts, extracted: dict) -> None:
        """Save the parsed outside view data (base_rate, reference_classes, etc.)."""
        self._write_json(artifacts.outside_view_dir / "extracted.json", extracted)

    # =========================================================================
    # Inside View (Ensemble)
    # =========================================================================

    def save_agent_prompt(
        self,
        artifacts: ForecastArtifacts,
        agent_name: str,
        prompt: str
    ) -> None:
        """Save the prompt sent to a specific agent."""
        agent_dir = artifacts.inside_view_dir / agent_name
        agent_dir.mkdir(exist_ok=True)
        self._write_text(agent_dir / "prompt.md", prompt)

    def save_agent_response(
        self,
        artifacts: ForecastArtifacts,
        agent_name: str,
        response: str
    ) -> None:
        """Save the full response from a specific agent."""
        agent_dir = artifacts.inside_view_dir / agent_name
        agent_dir.mkdir(exist_ok=True)
        self._write_text(agent_dir / "response.md", response)

    def save_agent_extracted(
        self,
        artifacts: ForecastArtifacts,
        agent_name: str,
        extracted: dict
    ) -> None:
        """Save the parsed prediction from a specific agent."""
        agent_dir = artifacts.inside_view_dir / agent_name
        agent_dir.mkdir(exist_ok=True)
        self._write_json(agent_dir / "extracted.json", extracted)

    def save_aggregation(self, artifacts: ForecastArtifacts, aggregation: dict) -> None:
        """Save how individual forecasts were combined."""
        self._write_json(artifacts.inside_view_dir / "aggregation.json", aggregation)

    # =========================================================================
    # Calibration
    # =========================================================================

    def save_calibration_checklist(self, artifacts: ForecastArtifacts, checklist: dict) -> None:
        """Save the calibration checklist responses."""
        self._write_json(artifacts.calibration_dir / "checklist.json", checklist)

    def save_calibration_adjustments(self, artifacts: ForecastArtifacts, adjustments: dict) -> None:
        """Save any post-checklist adjustments."""
        self._write_json(artifacts.calibration_dir / "adjustments.json", adjustments)

    # =========================================================================
    # Submission
    # =========================================================================

    def save_final_prediction(self, artifacts: ForecastArtifacts, prediction: dict) -> None:
        """Save the final prediction that was submitted."""
        self._write_json(artifacts.submission_dir / "final_prediction.json", prediction)

    def save_api_response(self, artifacts: ForecastArtifacts, response: dict) -> None:
        """Save the Metaculus API response."""
        self._write_json(artifacts.submission_dir / "api_response.json", response)

    def save_reasoning_report(self, artifacts: ForecastArtifacts, report: str) -> None:
        """Save the human-readable reasoning report."""
        self._write_text(artifacts.submission_dir / "reasoning_report.md", report)

    # =========================================================================
    # Metadata
    # =========================================================================

    def save_metadata(
        self,
        artifacts: ForecastArtifacts,
        config: dict,
        costs: dict,
        timing: dict,
        errors: list[str] | None = None
    ) -> None:
        """Save forecast metadata including config, costs, and timing."""
        metadata = {
            "question_id": artifacts.question_id,
            "timestamp": artifacts.timestamp,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config_hash": self._hash_config(config),
            "config_snapshot": config,
            "costs": costs,
            "timing": timing,
            "errors": errors or [],
        }
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

    def load_artifacts(self, question_id: int, timestamp: str) -> Optional[dict]:
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

    def list_forecasts(self, question_id: Optional[int] = None) -> list[dict]:
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

                forecasts.append({
                    "question_id": qid,
                    "timestamp": timestamp,
                    "directory": str(forecast_dir),
                    "metadata": metadata,
                })
            except (ValueError, IndexError):
                continue

        return sorted(forecasts, key=lambda x: x["timestamp"], reverse=True)
