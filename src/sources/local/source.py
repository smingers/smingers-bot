"""
Local question source implementation.

Allows users to create and forecast on their own questions stored as YAML files.
Questions are not submitted to any external platform - predictions are saved locally.

Usage:
    # Create a YAML file in data/local_questions/my_question.yaml
    # Then run:
    python main.py --source local --question my_question --mode test

Question file format (YAML):
    id: "my_question_001"
    title: "Will X happen by Y date?"
    description: "Background context..."
    resolution_criteria: "Resolves YES if..."
    question_type: binary  # or: numeric, multiple_choice
    # See example files in data/local_questions/examples/
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ...bot.binary import BinaryForecaster
from ...bot.forecaster import ScopedArtifactStore
from ...bot.multiple_choice import MultipleChoiceForecaster
from ...bot.numeric import NumericForecaster
from ...bot.prompts import (
    BINARY_INSIDE_VIEW_PROMPT,
    BINARY_OUTSIDE_VIEW_PROMPT,
    BINARY_PROMPT_CURRENT,
    BINARY_PROMPT_HISTORICAL,
    MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
    NUMERIC_INSIDE_VIEW_PROMPT,
    NUMERIC_OUTSIDE_VIEW_PROMPT,
    NUMERIC_PROMPT_CURRENT,
    NUMERIC_PROMPT_HISTORICAL,
    SUPERFORECASTER_CONTEXT,
)
from ...core.types import CoreForecast, PromptSet, Question, ResearchContext
from ...storage.artifact_store import ArtifactStore
from ...utils.llm import LLMClient
from ..base import BaseSource, register_source

logger = logging.getLogger(__name__)

# Default directory for local questions
DEFAULT_QUESTIONS_DIR = Path("data/local_questions")


def _load_yaml_file(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _yaml_to_question(data: dict, file_path: Path | None = None) -> Question:
    """
    Convert a YAML question definition to a Question object.

    Args:
        data: Parsed YAML data
        file_path: Optional path to the source file (used for ID fallback)

    Returns:
        Question object
    """
    # Determine ID: explicit id field, or filename stem
    question_id = data.get("id")
    if not question_id and file_path:
        question_id = file_path.stem
    if not question_id:
        raise ValueError("Question must have an 'id' field or be loaded from a file")

    # Validate required fields
    title = data.get("title")
    if not title:
        raise ValueError(f"Question '{question_id}' missing required field: title")

    # Determine question type
    question_type = data.get("question_type", "binary")
    if question_type not in ("binary", "numeric", "multiple_choice", "date"):
        raise ValueError(
            f"Question '{question_id}' has invalid question_type: '{question_type}'. "
            f"Must be one of: binary, numeric, multiple_choice, date"
        )

    # Validate type-specific fields
    if question_type == "multiple_choice":
        options = data.get("options")
        if not options or not isinstance(options, list):
            raise ValueError(f"Multiple choice question '{question_id}' must have 'options' list")
    else:
        options = []

    if question_type == "numeric":
        # Numeric questions should have bounds
        if data.get("lower_bound") is None or data.get("upper_bound") is None:
            logger.warning(
                f"Numeric question '{question_id}' missing bounds. "
                f"Consider adding lower_bound and upper_bound."
            )

    return Question(
        id=str(question_id),
        source="local",
        title=title,
        description=data.get("description", ""),
        resolution_criteria=data.get("resolution_criteria", ""),
        fine_print=data.get("fine_print", ""),
        question_type=question_type,
        open_time=data.get("open_time", ""),
        scheduled_resolve_time=data.get("scheduled_resolve_time", ""),
        lower_bound=data.get("lower_bound"),
        upper_bound=data.get("upper_bound"),
        unit_of_measure=data.get("unit_of_measure", ""),
        options=options,
        raw={
            "file_path": str(file_path) if file_path else None,
            "original_data": data,
        },
    )


@register_source("local")
class LocalSource(BaseSource):
    """
    Local file-based question source.

    Questions are stored as YAML files in a configured directory.
    Predictions are saved locally via the artifact store (not submitted anywhere).

    Directory structure:
        data/local_questions/
            my_question.yaml         # Individual question
            work/                    # Collection (subdirectory)
                project_a.yaml
                project_b.yaml
            personal/                # Another collection
                question_1.yaml
    """

    def __init__(
        self,
        config: dict,
        llm_client: LLMClient | None = None,
        artifact_store: ArtifactStore | None = None,
    ):
        super().__init__(config, llm_client, artifact_store)
        questions_dir = config.get("local", {}).get("questions_dir")
        self.questions_dir = Path(questions_dir) if questions_dir else DEFAULT_QUESTIONS_DIR
        self._forecasts: dict[str, dict] = {}  # Track forecasts made this session

    @property
    def name(self) -> str:
        return "local"

    async def close(self) -> None:
        """No cleanup needed for file-based source."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    def _find_question_file(self, question_id: str) -> Path:
        """
        Find a question file by ID.

        Searches for:
        1. Exact path if question_id looks like a path
        2. {question_id}.yaml in questions_dir
        3. {question_id}.yml in questions_dir
        4. Recursively in subdirectories

        Args:
            question_id: Question ID or file path

        Returns:
            Path to the question file

        Raises:
            FileNotFoundError: If question file not found
        """
        # Check if it's already a path
        if "/" in question_id or question_id.endswith((".yaml", ".yml")):
            path = Path(question_id)
            if path.exists():
                return path
            # Try relative to questions_dir
            path = self.questions_dir / question_id
            if path.exists():
                return path

        # Search in questions_dir
        for ext in (".yaml", ".yml"):
            path = self.questions_dir / f"{question_id}{ext}"
            if path.exists():
                return path

        # Search recursively in subdirectories
        for path in self.questions_dir.rglob(f"{question_id}.yaml"):
            return path
        for path in self.questions_dir.rglob(f"{question_id}.yml"):
            return path

        raise FileNotFoundError(
            f"Question '{question_id}' not found. Searched in: {self.questions_dir}\n"
            f"Create a file like: {self.questions_dir}/{question_id}.yaml"
        )

    async def fetch_question(self, question_id: str) -> Question:
        """
        Fetch a question by ID or file path.

        Args:
            question_id: Question ID (filename stem) or path to YAML file

        Returns:
            Question object
        """
        file_path = self._find_question_file(question_id)
        data = _load_yaml_file(file_path)
        return _yaml_to_question(data, file_path)

    async def build_research_context(self, question: Question) -> ResearchContext:
        """
        Build research context for a local question.

        Local source uses the same web search as Metaculus.
        Research is handled internally by the handlers.

        Returns:
            Empty ResearchContext (handlers do their own research)
        """
        return ResearchContext()

    def get_prompts(self, question_type: str) -> PromptSet:
        """
        Get prompt templates for a question type.

        Uses the same prompts as Metaculus source since local questions
        follow the same format.

        Args:
            question_type: "binary", "numeric", or "multiple_choice"

        Returns:
            PromptSet with templates
        """
        if question_type == "binary":
            return PromptSet(
                historical_query=BINARY_PROMPT_HISTORICAL,
                current_query=BINARY_PROMPT_CURRENT,
                outside_view=BINARY_OUTSIDE_VIEW_PROMPT,
                inside_view=BINARY_INSIDE_VIEW_PROMPT,
                system_prompt=SUPERFORECASTER_CONTEXT,
            )
        elif question_type in ("numeric", "date"):
            return PromptSet(
                historical_query=NUMERIC_PROMPT_HISTORICAL,
                current_query=NUMERIC_PROMPT_CURRENT,
                outside_view=NUMERIC_OUTSIDE_VIEW_PROMPT,
                inside_view=NUMERIC_INSIDE_VIEW_PROMPT,
                system_prompt=SUPERFORECASTER_CONTEXT,
            )
        elif question_type == "multiple_choice":
            return PromptSet(
                historical_query=MULTIPLE_CHOICE_PROMPT_HISTORICAL,
                current_query=MULTIPLE_CHOICE_PROMPT_CURRENT,
                outside_view=MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT,
                inside_view=MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT,
                system_prompt=SUPERFORECASTER_CONTEXT,
            )
        else:
            raise ValueError(f"Unknown question type: {question_type}")

    def convert_forecast(self, forecast: CoreForecast) -> Any:
        """
        Convert core forecast to local storage format.

        For local source, we just pass through the prediction since
        there's no external submission format requirement.

        Args:
            forecast: Core forecast result

        Returns:
            The prediction value unchanged
        """
        return forecast.prediction

    async def submit_forecast(self, question_id: str, forecast: Any) -> dict:
        """
        "Submit" a local prediction.

        Since there's no external platform, this just:
        1. Records the forecast in the session tracker
        2. Returns a success response

        The actual prediction data is saved by the forecaster's artifact store.

        Args:
            question_id: Question ID
            forecast: The prediction value

        Returns:
            Dict with submission status
        """
        timestamp = datetime.now().isoformat()

        # Track this forecast
        self._forecasts[question_id] = {
            "question_id": question_id,
            "timestamp": timestamp,
            "value": forecast,
        }

        logger.info(f"Local prediction saved for question ID: {question_id}")

        return {
            "status": "saved_locally",
            "submitted": False,
            "message": "Prediction saved to local artifacts (not submitted to external platform)",
            "question_id": question_id,
            "timestamp": timestamp,
        }

    # =========================================================================
    # Convenience methods that use existing handlers
    # =========================================================================

    def _create_scoped_store(self, question_id: str) -> ScopedArtifactStore | None:
        """Create a scoped artifact store for a forecast, or None if no store configured."""
        if not self.artifact_store:
            return None
        artifacts = self.artifact_store.create_forecast_artifacts(question_id)
        return ScopedArtifactStore(self.artifact_store, artifacts)

    async def run_forecast(
        self,
        question_id: str,
        log=print,
    ) -> CoreForecast:
        """
        Run a full forecast using the existing handler infrastructure.

        Args:
            question_id: Local question ID or file path
            log: Logging callback

        Returns:
            CoreForecast with prediction and metadata
        """
        question = await self.fetch_question(question_id)
        scoped_store = self._create_scoped_store(question_id)

        if question.question_type == "binary":
            handler = BinaryForecaster(self.config, self.llm, scoped_store)
            result = await handler.forecast(
                question_title=question.title,
                question_text=question.description,
                background_info=question.description,
                resolution_criteria=question.resolution_criteria,
                fine_print=question.fine_print,
                open_time=question.open_time,
                scheduled_resolve_time=question.scheduled_resolve_time,
                log=log,
            )
            return CoreForecast(
                prediction=result.final_probability,
                question_type="binary",
                agent_results=result.agent_results,
                historical_context=result.historical_context,
                current_context=result.current_context,
            )

        elif question.question_type in ("numeric", "date"):
            handler = NumericForecaster(self.config, self.llm, scoped_store)
            raw_data = question.raw.get("original_data", {})
            result = await handler.forecast(
                question_title=question.title,
                question_text=question.description,
                background_info=question.description,
                resolution_criteria=question.resolution_criteria,
                fine_print=question.fine_print,
                open_time=question.open_time,
                scheduled_resolve_time=question.scheduled_resolve_time,
                lower_bound=question.lower_bound,
                upper_bound=question.upper_bound,
                open_lower_bound=raw_data.get("open_lower_bound", False),
                open_upper_bound=raw_data.get("open_upper_bound", False),
                unit_of_measure=question.unit_of_measure,
                zero_point=raw_data.get("zero_point"),
                cdf_size=201,  # Default CDF size
                question_type=question.question_type,
                log=log,
            )
            return CoreForecast(
                prediction=result.cdf,
                question_type="numeric",
                agent_results=result.agent_results,
                historical_context=result.historical_context,
                current_context=result.current_context,
            )

        elif question.question_type == "multiple_choice":
            scoped_store = self._create_scoped_store(question_id)
            handler = MultipleChoiceForecaster(self.config, self.llm, scoped_store)
            result = await handler.forecast(
                question_title=question.title,
                question_text=question.description,
                background_info=question.description,
                resolution_criteria=question.resolution_criteria,
                fine_print=question.fine_print,
                open_time=question.open_time,
                scheduled_resolve_time=question.scheduled_resolve_time,
                options=question.options,
                log=log,
            )
            return CoreForecast(
                prediction=result.final_probabilities,
                question_type="multiple_choice",
                agent_results=result.agent_results,
                historical_context=result.historical_context,
                current_context=result.current_context,
            )

        else:
            raise ValueError(f"Unsupported question type: {question.question_type}")

    # =========================================================================
    # Local-specific utility methods
    # =========================================================================

    def list_questions(self, collection_id: str | None = None) -> list[dict]:
        """
        List available questions (without loading full content).

        Args:
            collection_id: Optional subdirectory to list

        Returns:
            List of dicts with id, title, file_path
        """
        search_dir = self.questions_dir
        if collection_id:
            search_dir = self.questions_dir / collection_id

        if not search_dir.exists():
            return []

        questions = []
        pattern = "*.yaml" if collection_id else "**/*.yaml"

        for path in sorted(search_dir.glob(pattern)):
            # Skip examples directory unless explicitly requested
            if "examples" in path.parts and collection_id != "examples":
                continue
            try:
                data = _load_yaml_file(path)
                questions.append(
                    {
                        "id": data.get("id") or path.stem,
                        "title": data.get("title", "(no title)"),
                        "question_type": data.get("question_type", "binary"),
                        "file_path": str(path),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")

        # Also check .yml files
        pattern = "*.yml" if collection_id else "**/*.yml"
        for path in sorted(search_dir.glob(pattern)):
            if "examples" in path.parts and collection_id != "examples":
                continue
            try:
                data = _load_yaml_file(path)
                questions.append(
                    {
                        "id": data.get("id") or path.stem,
                        "title": data.get("title", "(no title)"),
                        "question_type": data.get("question_type", "binary"),
                        "file_path": str(path),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")

        return questions

    def list_collections(self) -> list[str]:
        """
        List available collections (subdirectories).

        Returns:
            List of collection names
        """
        if not self.questions_dir.exists():
            return []

        return [d.name for d in sorted(self.questions_dir.iterdir()) if d.is_dir()]
