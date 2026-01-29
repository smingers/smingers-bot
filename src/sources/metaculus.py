"""
Metaculus question source implementation.

Wraps the Metaculus API while implementing the generic QuestionSource interface.
"""

import os
import re
import logging
from typing import Any, Optional

import httpx

from .base import Question, Prediction, QuestionSource, QuestionType

logger = logging.getLogger(__name__)

METACULUS_API_BASE = "https://www.metaculus.com/api"


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_community_prediction(question_data: dict) -> Optional[float]:
    """Extract community prediction from Metaculus question data."""
    aggregations = question_data.get("aggregations", {})
    if not aggregations:
        return None

    recency = aggregations.get("recency_weighted", {})
    if not recency:
        return None

    history = recency.get("history", [])
    if not history:
        return None

    latest = history[-1] if history else {}
    centers = latest.get("centers", [])
    if centers:
        return centers[0]  # First center is median

    return None


def _extract_tournament_id(data: dict) -> Optional[str]:
    """Extract tournament ID from Metaculus question data."""
    default_project = data.get("projects", {}).get("default_project", {})
    project_id = default_project.get("id")
    return str(project_id) if project_id else None


def metaculus_to_question(data: dict) -> Question:
    """
    Convert Metaculus API response to generic Question.

    This is the central conversion function that maps Metaculus-specific
    field names and structures to the generic Question format.
    """
    question_data = data.get("question", data)

    # Determine question type
    q_type = question_data.get("type", "binary")
    if q_type == "multiple_choice":
        question_type: QuestionType = "multiple_choice"
    elif q_type in ("numeric", "continuous"):
        question_type = "numeric"
    elif q_type == "date":
        question_type = "date"
    else:
        question_type = "binary"

    # Get status from nested question object if not at top level
    status = data.get("status") or question_data.get("status", "")

    # Extract numeric bounds from scaling
    scaling = question_data.get("scaling", {}) or {}

    # Extract options for multiple choice
    raw_options = question_data.get("options", [])
    options = None
    if question_type == "multiple_choice" and raw_options:
        options = [
            opt.get("label", f"Option {i+1}") if isinstance(opt, dict) else str(opt)
            for i, opt in enumerate(raw_options)
        ]

    # Get both post ID (in URL) and question ID (for forecasting)
    post_id = data.get("id")
    question_id = question_data.get("id", post_id)

    return Question(
        id=str(post_id),
        source="metaculus",
        title=data.get("title", ""),
        description=data.get("description") or question_data.get("description") or "",
        resolution_criteria=data.get("resolution_criteria") or question_data.get("resolution_criteria") or "",
        fine_print=data.get("fine_print") or question_data.get("fine_print") or "",
        background_info=question_data.get("description") or "",
        question_type=question_type,
        created_at=data.get("created_at", ""),
        open_time=data.get("open_time") or question_data.get("open_time"),
        scheduled_close_time=data.get("scheduled_close_time") or question_data.get("scheduled_close_time"),
        scheduled_resolve_time=data.get("scheduled_resolve_time") or question_data.get("scheduled_resolve_time"),
        status=status,
        options=options,
        unit_of_measure=question_data.get("unit"),
        lower_bound=_safe_float(scaling.get("range_min")),
        upper_bound=_safe_float(scaling.get("range_max")),
        open_lower_bound=question_data.get("open_lower_bound", False),
        open_upper_bound=question_data.get("open_upper_bound", False),
        zero_point=_safe_float(scaling.get("zero_point")),
        nominal_lower_bound=_safe_float(scaling.get("nominal_min")),
        nominal_upper_bound=_safe_float(scaling.get("nominal_max")),
        community_prediction=_extract_community_prediction(question_data),
        num_forecasters=data.get("nr_forecasters"),
        raw={
            "post_id": post_id,
            "question_id": question_id,
            "full_response": data,
        },
        collection_id=_extract_tournament_id(data),
    )


class MetaculusSource(QuestionSource):
    """
    Metaculus implementation of QuestionSource.

    Handles fetching questions from Metaculus API and submitting predictions
    in Metaculus-specific format.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Metaculus source.

        Args:
            token: Metaculus API token. If not provided, uses METACULUS_TOKEN env var.
        """
        self.token = token or os.getenv("METACULUS_TOKEN")
        if not self.token:
            raise ValueError(
                "Metaculus token required. Set METACULUS_TOKEN env var or pass token parameter."
            )

        self._client = httpx.AsyncClient(
            base_url=METACULUS_API_BASE,
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json",
                "Accept-Language": "en",
            },
            timeout=30.0,
        )

    @property
    def name(self) -> str:
        return "metaculus"

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_question(self, question_id: str) -> Question:
        """Fetch a single question by ID (post ID)."""
        response = await self._client.get(f"/posts/{question_id}/")
        response.raise_for_status()
        data = response.json()
        return metaculus_to_question(data)

    async def get_question_by_url(self, url: str) -> Question:
        """Fetch a question from its URL."""
        match = re.search(r"/questions/(\d+)", url)
        if not match:
            raise ValueError(f"Could not extract question ID from URL: {url}")
        question_id = match.group(1)
        return await self.get_question(question_id)

    async def get_collection_questions(
        self,
        collection_id: str,
        status: Optional[str] = "open",
        limit: int = 100,
    ) -> list[Question]:
        """
        Get questions from a tournament.

        Args:
            collection_id: Tournament/project ID or slug
            status: Filter by status (open, closed, resolved, etc.)
            limit: Maximum questions to return

        Returns:
            List of Question objects
        """
        params = {
            "tournaments": collection_id,
            "limit": limit,
            "order_by": "-created_at",
        }
        if status:
            params["statuses"] = status

        response = await self._client.get("/posts/", params=params)
        response.raise_for_status()
        data = response.json()

        # Filter to only include questions where this tournament is the default_project
        questions = []
        for item in data.get("results", []):
            default_project = item.get("projects", {}).get("default_project", {})
            default_id = default_project.get("id")
            default_slug = default_project.get("slug")

            # Match by ID or slug
            is_primary = False
            try:
                if default_id == int(collection_id):
                    is_primary = True
            except ValueError:
                pass

            if default_slug == collection_id:
                is_primary = True

            if is_primary:
                try:
                    questions.append(metaculus_to_question(item))
                except Exception as e:
                    logger.warning(f"Failed to parse question: {e}")

        return questions

    async def get_my_forecasts(
        self,
        collection_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get questions the user has already forecasted.

        Args:
            collection_id: Optional tournament ID or slug to filter by

        Returns:
            Dict mapping question_id (as string) to forecast info
        """
        # Get current user ID
        user_response = await self._client.get("/users/me/")
        user_response.raise_for_status()
        user_id = user_response.json()["id"]

        params = {"forecaster_id": user_id, "limit": 500}
        if collection_id:
            params["tournaments"] = collection_id

        response = await self._client.get("/posts/", params=params)
        response.raise_for_status()
        data = response.json()

        forecasts = {}
        for item in data.get("results", []):
            question_id = item.get("id")
            if question_id:
                forecasts[str(question_id)] = {
                    "question_id": str(question_id),
                    "timestamp": None,  # Not available in list response
                }

        return forecasts

    async def submit_prediction(
        self,
        question: Question,
        prediction: Prediction,
    ) -> dict:
        """
        Submit a prediction to Metaculus.

        Converts the generic Prediction to Metaculus format and applies
        platform-specific constraints (probability bounds, CDF validation).
        """
        # Get the Metaculus question_id from raw data
        metaculus_question_id = question.raw.get("question_id", question.id)

        if prediction.question_type == "binary":
            return await self._submit_binary(metaculus_question_id, prediction.value)
        elif prediction.question_type == "numeric":
            return await self._submit_numeric(metaculus_question_id, prediction.value)
        elif prediction.question_type == "multiple_choice":
            return await self._submit_multiple_choice(metaculus_question_id, prediction.value)
        else:
            raise ValueError(f"Unsupported question type: {prediction.question_type}")

    async def _submit_binary(self, question_id: Any, probability: float) -> dict:
        """Submit a binary prediction."""
        # Metaculus constraint: probabilities must be in [0.001, 0.999]
        probability = max(0.001, min(0.999, probability))

        payload = [
            {
                "question": int(question_id),
                "source": "api",
                "probability_yes": probability,
            }
        ]

        response = await self._client.post("/questions/forecast/", json=payload)
        response.raise_for_status()
        return response.json()

    async def _submit_numeric(self, question_id: Any, cdf: list[float]) -> dict:
        """Submit a numeric prediction as a CDF."""
        if len(cdf) != 201:
            raise ValueError(f"CDF must have exactly 201 values, got {len(cdf)}")

        # Apply Metaculus CDF constraints
        cdf = self._validate_cdf(cdf)

        payload = [
            {
                "question": int(question_id),
                "source": "api",
                "continuous_cdf": cdf,
            }
        ]

        response = await self._client.post("/questions/forecast/", json=payload)
        response.raise_for_status()
        return response.json()

    async def _submit_multiple_choice(
        self,
        question_id: Any,
        probabilities: dict[str, float],
    ) -> dict:
        """Submit a multiple choice prediction."""
        # Apply Metaculus constraints: clamp to [0.01, 0.99] and normalize
        clamped = {k: max(0.01, min(0.99, v)) for k, v in probabilities.items()}
        total = sum(clamped.values())
        normalized = {k: v / total for k, v in clamped.items()}

        payload = [
            {
                "question": int(question_id),
                "source": "api",
                "probability_yes_per_category": normalized,
            }
        ]

        response = await self._client.post("/questions/forecast/", json=payload)
        response.raise_for_status()
        return response.json()

    def _validate_cdf(self, cdf: list[float]) -> list[float]:
        """
        Validate and fix a CDF to meet Metaculus requirements.

        Metaculus constraints:
        - Values must be in [0.001, 0.999]
        - Must be monotonically increasing
        - No single step > 0.59
        """
        # Ensure bounds
        cdf = [max(0.001, min(0.999, v)) for v in cdf]

        # Ensure monotonicity (each value >= previous)
        for i in range(1, len(cdf)):
            if cdf[i] < cdf[i - 1]:
                cdf[i] = cdf[i - 1]

        # Ensure no single step is too large (max 0.59)
        for i in range(1, len(cdf)):
            if cdf[i] - cdf[i - 1] > 0.59:
                cdf[i] = cdf[i - 1] + 0.59

        return cdf

    # =========================================================================
    # Additional Metaculus-specific methods (not part of QuestionSource interface)
    # =========================================================================

    async def get_tournament_info(self, tournament_id: str) -> dict:
        """Get information about a tournament."""
        response = await self._client.get(f"/projects/{tournament_id}/")
        response.raise_for_status()
        return response.json()

    async def get_leaderboard(self, tournament_id: str, limit: int = 50) -> list[dict]:
        """Get the tournament leaderboard."""
        response = await self._client.get(
            f"/projects/{tournament_id}/leaderboard/",
            params={"limit": limit},
        )
        response.raise_for_status()
        return response.json().get("results", [])
