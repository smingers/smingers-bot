"""
Local question source implementation.

Allows users to create and forecast on their own questions stored as YAML files.
Questions are not submitted to any external platform - predictions are saved locally.

Usage:
    # Create a YAML file in data/local_questions/my_question.yaml
    # Then run:
    python main.py --source local --question my_question

Question file format (YAML):
    id: "my_question_001"
    title: "Will X happen by Y date?"
    description: "Background context..."
    resolution_criteria: "Resolves YES if..."
    question_type: binary  # or: numeric, multiple_choice
    # See example files for full options
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from .base import Prediction, Question, QuestionSource, QuestionType

logger = logging.getLogger(__name__)

# Default directory for local questions
DEFAULT_QUESTIONS_DIR = "data/local_questions"


def _load_yaml_file(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _yaml_to_question(data: dict, file_path: Optional[Path] = None) -> Question:
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
    q_type = data.get("question_type", "binary")
    if q_type not in ("binary", "numeric", "multiple_choice", "date"):
        raise ValueError(
            f"Question '{question_id}' has invalid question_type: '{q_type}'. "
            f"Must be one of: binary, numeric, multiple_choice, date"
        )
    question_type: QuestionType = q_type

    # Validate type-specific fields
    if question_type == "multiple_choice":
        options = data.get("options")
        if not options or not isinstance(options, list):
            raise ValueError(
                f"Multiple choice question '{question_id}' must have 'options' list"
            )
    else:
        options = None

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
        background_info=data.get("background_info", ""),
        question_type=question_type,
        created_at=data.get("created_at") or datetime.now(UTC).isoformat(),
        open_time=data.get("open_time"),
        scheduled_close_time=data.get("scheduled_close_time"),
        scheduled_resolve_time=data.get("scheduled_resolve_time"),
        status=data.get("status", "open"),
        options=options,
        unit_of_measure=data.get("unit_of_measure"),
        lower_bound=data.get("lower_bound"),
        upper_bound=data.get("upper_bound"),
        open_lower_bound=data.get("open_lower_bound", False),
        open_upper_bound=data.get("open_upper_bound", False),
        zero_point=data.get("zero_point"),
        nominal_lower_bound=data.get("nominal_lower_bound"),
        nominal_upper_bound=data.get("nominal_upper_bound"),
        community_prediction=data.get("community_prediction"),
        num_forecasters=data.get("num_forecasters"),
        raw={"file_path": str(file_path) if file_path else None, "original_data": data},
        collection_id=data.get("collection_id") or data.get("collection"),
    )


class LocalSource(QuestionSource):
    """
    Local file-based question source.

    Questions are stored as YAML files in a configured directory.
    Predictions are not submitted anywhere - they're saved locally via the artifact store.

    Directory structure:
        data/local_questions/
            my_question.yaml         # Individual question
            work/                    # Collection (subdirectory)
                project_a.yaml
                project_b.yaml
            personal/                # Another collection
                question_1.yaml
    """

    def __init__(self, questions_dir: Optional[str] = None):
        """
        Initialize the local source.

        Args:
            questions_dir: Directory containing question YAML files.
                          Defaults to data/local_questions/
        """
        self.questions_dir = Path(questions_dir or DEFAULT_QUESTIONS_DIR)
        self._forecasts: dict[str, dict] = {}  # Track forecasts made this session

    @property
    def name(self) -> str:
        return "local"

    async def close(self) -> None:
        """No cleanup needed for file-based source."""
        pass

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

    async def get_question(self, question_id: str) -> Question:
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

    async def get_question_by_url(self, url: str) -> Question:
        """
        For local source, URL is treated as a file path.

        Args:
            url: File path (absolute or relative to questions_dir)

        Returns:
            Question object
        """
        # Strip file:// prefix if present
        if url.startswith("file://"):
            url = url[7:]

        return await self.get_question(url)

    async def get_collection_questions(
        self,
        collection_id: str,
        status: Optional[str] = "open",
        limit: int = 100,
    ) -> list[Question]:
        """
        Get questions from a collection (subdirectory).

        Args:
            collection_id: Subdirectory name under questions_dir
            status: Filter by status (only "open" supported for local)
            limit: Maximum questions to return

        Returns:
            List of Question objects
        """
        collection_dir = self.questions_dir / collection_id

        if not collection_dir.exists():
            logger.warning(f"Collection directory not found: {collection_dir}")
            return []

        if not collection_dir.is_dir():
            raise ValueError(f"Collection '{collection_id}' is not a directory")

        questions = []
        for path in sorted(collection_dir.glob("*.yaml")) + sorted(
            collection_dir.glob("*.yml")
        ):
            try:
                data = _load_yaml_file(path)
                question = _yaml_to_question(data, path)

                # Filter by status if specified
                if status and question.status != status:
                    continue

                questions.append(question)

                if len(questions) >= limit:
                    break
            except Exception as e:
                logger.warning(f"Failed to load question from {path}: {e}")

        return questions

    async def get_my_forecasts(
        self,
        collection_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get questions forecasted in this session.

        For local source, this returns forecasts made during the current session.
        Persistent tracking would require additional storage.

        Args:
            collection_id: Optional collection to filter by (not used for local)

        Returns:
            Dict mapping question_id to forecast info
        """
        # Return forecasts tracked during this session
        return self._forecasts

    async def submit_prediction(
        self,
        question: Question,
        prediction: Prediction,
    ) -> dict:
        """
        "Submit" a local prediction.

        Since there's no external platform, this just:
        1. Records the forecast in the session tracker
        2. Returns a success response

        The actual prediction data is saved by the forecaster's artifact store.

        Args:
            question: The question being forecasted
            prediction: The prediction

        Returns:
            Dict with submission status
        """
        # Track this forecast
        self._forecasts[question.id] = {
            "question_id": question.id,
            "question_type": prediction.question_type,
            "timestamp": prediction.timestamp,
            "value": prediction.value,
        }

        logger.info(
            f"Local prediction saved for '{question.title}' (ID: {question.id})"
        )

        return {
            "status": "saved_locally",
            "submitted": False,
            "message": "Prediction saved to local artifacts (not submitted to external platform)",
            "question_id": question.id,
            "timestamp": prediction.timestamp,
        }

    # =========================================================================
    # Additional local-specific methods
    # =========================================================================

    def list_questions(self, collection_id: Optional[str] = None) -> list[dict]:
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

        return [
            d.name for d in sorted(self.questions_dir.iterdir()) if d.is_dir()
        ]
