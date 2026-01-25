"""
Metaculus API Wrapper

Handles all interactions with the Metaculus API:
- Fetching questions from tournaments
- Submitting predictions
- Getting question details
"""

import os
import logging
from typing import Optional, Any, Literal
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

METACULUS_API_BASE = "https://www.metaculus.com/api2"


@dataclass
class MetaculusQuestion:
    """Parsed Metaculus question data."""
    id: int
    title: str
    description: str
    resolution_criteria: str
    fine_print: str
    question_type: Literal["binary", "numeric", "multiple_choice", "date"]
    created_at: str
    scheduled_close_time: Optional[str]
    scheduled_resolve_time: Optional[str]
    status: str  # open, closed, resolved, etc.

    # Type-specific fields
    possibilities: Optional[dict] = None  # For numeric: min, max, etc.
    options: Optional[list[dict]] = None  # For multiple choice

    # Community data
    community_prediction: Optional[float] = None
    num_forecasters: Optional[int] = None

    # Raw data for reference
    raw: dict = None

    @classmethod
    def from_api_response(cls, data: dict) -> "MetaculusQuestion":
        """Parse a question from the API response."""
        question_data = data.get("question", data)

        # Determine question type from nested question object
        q_type = question_data.get("type", "binary")
        if q_type == "multiple_choice":
            question_type = "multiple_choice"
        elif q_type == "numeric" or q_type == "continuous":
            question_type = "numeric"
        elif q_type == "date":
            question_type = "date"
        else:
            question_type = "binary"

        # Get status from nested question object if not at top level
        status = data.get("status") or question_data.get("status", "")

        # Try to get community prediction from aggregations
        community_pred = None
        aggregations = question_data.get("aggregations", {})
        if aggregations:
            recency = aggregations.get("recency_weighted", {})
            if recency:
                history = recency.get("history", [])
                if history:
                    # Get the latest forecast
                    latest = history[-1] if history else {}
                    centers = latest.get("centers", [])
                    if centers:
                        community_pred = centers[0]  # First center is median

        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description") or "",  # Handle None
            resolution_criteria=data.get("resolution_criteria") or "",
            fine_print=data.get("fine_print") or "",
            question_type=question_type,
            created_at=data.get("created_at", ""),
            scheduled_close_time=data.get("scheduled_close_time") or question_data.get("scheduled_close_time"),
            scheduled_resolve_time=data.get("scheduled_resolve_time") or question_data.get("scheduled_resolve_time"),
            status=status,
            possibilities=question_data.get("possibilities"),
            options=question_data.get("options"),
            community_prediction=community_pred,
            num_forecasters=data.get("nr_forecasters"),
            raw=data,
        )


@dataclass
class MyForecast:
    """Represents a forecast I've already made."""
    question_id: int
    timestamp: Optional[datetime] = None  # When the forecast was made


@dataclass
class PredictionSubmission:
    """A prediction to submit to Metaculus."""
    question_id: int
    prediction: float | dict | list  # float for binary, dict for MC, list for numeric CDF

    # For tracking
    submitted_at: Optional[str] = None
    api_response: Optional[dict] = None


class MetaculusClient:
    """
    Client for the Metaculus API.

    Usage:
        client = MetaculusClient(token="your_token")
        questions = await client.get_tournament_questions(tournament_id=32721)
        await client.submit_prediction(question_id=12345, prediction=0.65)
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("METACULUS_TOKEN")
        if not self.token:
            raise ValueError(
                "Metaculus token required. Set METACULUS_TOKEN env var or pass token parameter."
            )

        self.client = httpx.AsyncClient(
            base_url=METACULUS_API_BASE,
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # =========================================================================
    # Questions
    # =========================================================================

    async def get_question(self, question_id: int) -> MetaculusQuestion:
        """Get a single question by ID."""
        response = await self.client.get(f"/questions/{question_id}/")
        response.raise_for_status()
        data = response.json()
        return MetaculusQuestion.from_api_response(data)

    async def get_question_by_url(self, url: str) -> MetaculusQuestion:
        """Get a question from its URL."""
        # Extract question ID from URL
        # URLs look like: https://www.metaculus.com/questions/12345/...
        import re
        match = re.search(r"/questions/(\d+)", url)
        if not match:
            raise ValueError(f"Could not extract question ID from URL: {url}")
        question_id = int(match.group(1))
        return await self.get_question(question_id)

    async def get_tournament_questions(
        self,
        tournament_id: int | str,
        status: Optional[str] = "open",
        limit: int = 100,
    ) -> list[MetaculusQuestion]:
        """
        Get questions from a tournament.

        Args:
            tournament_id: Tournament/project ID (int) or slug (str like "minibench")
            status: Filter by status (open, closed, resolved, etc.)
            limit: Maximum questions to return

        Returns:
            List of MetaculusQuestion objects
        """
        params = {
            "tournaments": tournament_id,
            "limit": limit,
            "order_by": "-created_at",
        }
        if status:
            params["status"] = status

        response = await self.client.get("/questions/", params=params)
        response.raise_for_status()
        data = response.json()

        # Filter to only include questions where this tournament is the default_project
        # The API returns all questions linked to the tournament, but we only want
        # questions that are primarily part of this tournament
        questions = []
        for item in data.get("results", []):
            # Check if this tournament is the default_project
            default_project = item.get("projects", {}).get("default_project", {})
            default_id = default_project.get("id")
            default_slug = default_project.get("slug")

            # Match by ID or slug
            is_primary = False
            if isinstance(tournament_id, int) and default_id == tournament_id:
                is_primary = True
            elif isinstance(tournament_id, str):
                # Try matching as slug, or as int if it's a numeric string
                if default_slug == tournament_id:
                    is_primary = True
                else:
                    try:
                        if default_id == int(tournament_id):
                            is_primary = True
                    except ValueError:
                        pass

            if is_primary:
                try:
                    questions.append(MetaculusQuestion.from_api_response(item))
                except Exception as e:
                    logger.warning(f"Failed to parse question: {e}")

        return questions

    async def get_my_forecasts(
        self,
        tournament_id: Optional[int | str] = None,
    ) -> dict[int, "MyForecast"]:
        """
        Get questions I've already forecasted on.

        Args:
            tournament_id: Optional tournament ID or slug to filter by

        Returns:
            Dict mapping question_id to MyForecast object with timestamp
        """
        params = {"forecast_by_me": True, "limit": 500}
        if tournament_id:
            params["tournaments"] = tournament_id

        response = await self.client.get("/questions/", params=params)
        response.raise_for_status()
        data = response.json()

        forecasts = {}
        for item in data.get("results", []):
            question_id = item.get("id")
            if question_id:
                # Try to get my latest forecast timestamp
                my_forecasts = item.get("my_forecasts", {})
                latest = my_forecasts.get("latest") if my_forecasts else None
                timestamp = None
                if latest:
                    timestamp_str = latest.get("start_time") or latest.get("created_at")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                forecasts[question_id] = MyForecast(
                    question_id=question_id,
                    timestamp=timestamp,
                )

        return forecasts

    # =========================================================================
    # Predictions
    # =========================================================================

    async def submit_binary_prediction(
        self,
        question_id: int,
        prediction: float,
    ) -> dict:
        """
        Submit a binary prediction.

        Args:
            question_id: Question ID
            prediction: Probability between 0.001 and 0.999

        Returns:
            API response dict
        """
        # Ensure bounds
        prediction = max(0.001, min(0.999, prediction))

        payload = {"prediction": prediction}

        response = await self.client.post(
            f"/questions/{question_id}/predict/",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def submit_numeric_prediction(
        self,
        question_id: int,
        cdf: list[float],
    ) -> dict:
        """
        Submit a numeric prediction as a CDF.

        Args:
            question_id: Question ID
            cdf: List of 201 CDF values (cumulative probabilities)

        Returns:
            API response dict
        """
        if len(cdf) != 201:
            raise ValueError(f"CDF must have exactly 201 values, got {len(cdf)}")

        # Ensure CDF is valid (monotonic, bounded)
        cdf = self._validate_cdf(cdf)

        payload = {"prediction": {"kind": "multi", "d": cdf}}

        response = await self.client.post(
            f"/questions/{question_id}/predict/",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def submit_multiple_choice_prediction(
        self,
        question_id: int,
        probabilities: dict[str, float],
    ) -> dict:
        """
        Submit a multiple choice prediction.

        Args:
            question_id: Question ID
            probabilities: Dict mapping option IDs to probabilities (must sum to 1)

        Returns:
            API response dict
        """
        # Normalize to sum to 1
        total = sum(probabilities.values())
        if abs(total - 1.0) > 0.01:
            probabilities = {k: v / total for k, v in probabilities.items()}

        payload = {"prediction": probabilities}

        response = await self.client.post(
            f"/questions/{question_id}/predict/",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def submit_prediction(
        self,
        question: MetaculusQuestion,
        prediction: float | dict | list,
    ) -> dict:
        """
        Submit a prediction, automatically handling the question type.

        Args:
            question: The question object
            prediction: The prediction value (format depends on question type)

        Returns:
            API response dict
        """
        if question.question_type == "binary":
            return await self.submit_binary_prediction(question.id, prediction)
        elif question.question_type == "numeric":
            return await self.submit_numeric_prediction(question.id, prediction)
        elif question.question_type == "multiple_choice":
            return await self.submit_multiple_choice_prediction(question.id, prediction)
        else:
            raise ValueError(f"Unsupported question type: {question.question_type}")

    def _validate_cdf(self, cdf: list[float]) -> list[float]:
        """Validate and fix a CDF to ensure it's monotonic and bounded."""
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
    # Tournaments
    # =========================================================================

    async def get_tournament_info(self, tournament_id: int) -> dict:
        """Get information about a tournament."""
        response = await self.client.get(f"/projects/{tournament_id}/")
        response.raise_for_status()
        return response.json()

    async def get_leaderboard(self, tournament_id: int, limit: int = 50) -> list[dict]:
        """Get the tournament leaderboard."""
        response = await self.client.get(
            f"/projects/{tournament_id}/leaderboard/",
            params={"limit": limit},
        )
        response.raise_for_status()
        return response.json().get("results", [])


# Convenience function for getting a configured client
def get_client(token: Optional[str] = None) -> MetaculusClient:
    """Get a Metaculus client, using env var if no token provided."""
    return MetaculusClient(token=token)
