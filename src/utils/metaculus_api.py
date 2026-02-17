"""
Metaculus API Wrapper

Handles all interactions with the Metaculus API:
- Fetching questions from tournaments
- Submitting predictions
- Getting question details
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from ..bot.exceptions import QuestionTypeError

logger = logging.getLogger(__name__)

METACULUS_API_BASE = "https://www.metaculus.com/api"


@dataclass
class MetaculusQuestion:
    """
    Parsed Metaculus question data.

    IMPORTANT: This class has two ID fields with distinct purposes:
    - id: The POST ID (appears in URLs like /questions/12345/)
    - question_id: The QUESTION ID (used in forecasting API calls)

    When they differ: These IDs are usually identical for standalone questions.
    They differ for grouped questions (e.g., conditional pairs, question groups)
    where multiple questions share a single post page. In these cases, the post
    ID identifies the page while each sub-question has its own question_id.
    Always use question_id for API calls to submit predictions.

    Attributes:
        id: Post ID (used in URLs, for display/navigation)
        question_id: Question ID (used for forecasting API calls)
        title: Question title
        description: Question background/context
        resolution_criteria: How the question will be resolved
        fine_print: Additional resolution details and edge cases
        background_info: Additional background information
        question_type: One of "binary", "numeric", "discrete", "multiple_choice", "date"
        created_at: ISO timestamp when question was created
        open_time: When question opened for forecasting (ISO timestamp)
        scheduled_close_time: When forecasting closes (ISO timestamp)
        scheduled_resolve_time: When question resolves (ISO timestamp)
        status: Question status (open, closed, resolved, etc.)

    Type-specific fields (only populated for relevant question types):
        possibilities: For numeric questions - min, max, scale info
        options: For multiple choice - list of option dicts
        unit_of_measure: Units for numeric questions (e.g., "USD", "people")
        upper_bound/lower_bound: Hard bounds for numeric questions
        open_upper_bound/open_lower_bound: Whether bounds can be exceeded
        zero_point: Reference point for log-scale questions
        cdf_size: Number of CDF points (201 for numeric, 102 for discrete)

    Additional metadata (stored but NOT passed to forecasting prompts):
        page_url: Direct URL to the question page
        published_time: When the question was published/visible
        actual_resolution_time: When the question actually resolved (if resolved)
        cp_reveal_time: When community prediction becomes visible
        close_time: When forecasting closes (alias for scheduled_close_time)
        num_predictions: Total number of predictions made
        already_forecasted: Whether we've already forecasted this question
        tournament_slugs: List of tournament slugs this question belongs to
        default_project_id: ID of the default project/tournament
        includes_bots_in_aggregates: Whether bot predictions count in aggregates
        question_weight: Weight of question in tournament scoring
        resolution_string: Raw resolution value (yes/no/number/annulled)
        categories: List of category dicts (id, name, slug, emoji)
        group_label: For group questions, the sub-question label
    """

    # === Core fields (used in forecasting pipeline) ===
    id: int
    question_id: int
    title: str
    description: str  # Question background/context
    resolution_criteria: str
    fine_print: str
    background_info: str  # Additional background information
    question_type: Literal["binary", "numeric", "discrete", "multiple_choice", "date"]
    created_at: str
    open_time: str | None  # When question opened for forecasting
    scheduled_close_time: str | None
    scheduled_resolve_time: str | None
    status: str  # open, closed, resolved, etc.

    # Type-specific fields
    possibilities: dict | None = None  # For numeric: min, max, etc.
    options: list[dict] | None = None  # For multiple choice

    # Numeric question bounds
    unit_of_measure: str | None = None  # Units for numeric questions
    upper_bound: float | None = None  # Hard upper bound
    lower_bound: float | None = None  # Hard lower bound
    open_upper_bound: bool | None = None  # True if upper bound is soft (can exceed)
    open_lower_bound: bool | None = None  # True if lower bound is soft (can go below)
    zero_point: float | None = None  # For log-scale questions
    nominal_upper_bound: float | None = None  # Suggested upper bound (may be tighter)
    nominal_lower_bound: float | None = None  # Suggested lower bound (may be tighter)
    cdf_size: int = 201  # CDF size: 201 for numeric, 102 for discrete

    # Date question fields (human-readable strings for prompts)
    upper_bound_date_str: str | None = None  # e.g., "2026-12-31"
    lower_bound_date_str: str | None = None  # e.g., "2025-01-01"

    # Community data
    community_prediction: float | None = None
    num_forecasters: int | None = None

    # === Additional metadata (NOT used in forecasting prompts) ===
    # These fields are stored for analytics/debugging but not passed to LLMs

    # URL and timing
    page_url: str | None = None  # e.g., "https://www.metaculus.com/questions/12345"
    published_time: str | None = None  # When question became visible
    actual_resolution_time: str | None = None  # When question resolved (if resolved)
    cp_reveal_time: str | None = None  # When CP becomes visible
    close_time: str | None = None  # When forecasting closes

    # Prediction metadata
    num_predictions: int | None = None  # Total predictions count
    already_forecasted: bool | None = None  # Have we forecasted this?

    # Tournament/project info
    tournament_slugs: list[str] | None = None  # e.g., ["spring-aib-2026", "minibench"]
    default_project_id: int | None = None  # Primary tournament ID
    includes_bots_in_aggregates: bool | None = None  # Do bot predictions count?
    question_weight: float | None = None  # Scoring weight in tournament

    # Resolution info
    resolution_string: str | None = None  # Raw resolution: "yes", "no", "0.5", "annulled"

    # Categorization
    categories: list[dict] | None = None  # [{id, name, slug, emoji, description}]
    group_label: str | None = None  # For group questions: "September 2024", etc.

    # Raw data for reference
    raw: dict = None

    @classmethod
    def from_api_response(cls, data: dict) -> "MetaculusQuestion":
        """Parse a question from the API response."""
        question_data = data.get("question", data)

        # Determine question type from nested question object
        # Supported types: binary, numeric, discrete, multiple_choice, date
        q_type = question_data.get("type", "binary")
        if q_type == "multiple_choice":
            question_type = "multiple_choice"
        elif q_type == "numeric" or q_type == "continuous":
            question_type = "numeric"
        elif q_type == "discrete":
            question_type = "discrete"
        elif q_type == "date":
            question_type = "date"
        elif q_type == "binary":
            question_type = "binary"
        else:
            raise QuestionTypeError(
                f"Unsupported question type: '{q_type}'. "
                f"Supported types: binary, numeric, discrete, multiple_choice, date",
                question_type=q_type,
            )

        # Get CDF size from inbound_outcome_count (201 for numeric, 102 for discrete)
        scaling = question_data.get("scaling", {}) or {}
        inbound_outcome_count = scaling.get("inbound_outcome_count")
        if inbound_outcome_count is not None:
            cdf_size = inbound_outcome_count + 1
        else:
            cdf_size = 201  # Default for numeric

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

        # Get both post ID (in URL) and question ID (for forecasting)
        post_id = data.get("id")
        question_id = question_data.get("id", post_id)  # Nested question has the actual question ID

        # Extract numeric question bounds from scaling object (scaling already defined above)
        upper_bound_raw = scaling.get("range_max")
        lower_bound_raw = scaling.get("range_min")
        nominal_upper_bound = scaling.get("nominal_max")
        nominal_lower_bound = scaling.get("nominal_min")
        zero_point = scaling.get("zero_point")

        # For date questions, bounds are Unix timestamps - also store human-readable strings
        upper_bound_date_str = None
        lower_bound_date_str = None

        if question_type == "date":
            # Date bounds: convert to float (timestamp) and store date strings
            upper_bound = cls._parse_date_bound(upper_bound_raw)
            lower_bound = cls._parse_date_bound(lower_bound_raw)
            if upper_bound is not None:
                upper_bound_date_str = datetime.fromtimestamp(upper_bound, tz=UTC).strftime(
                    "%Y-%m-%d"
                )
            if lower_bound is not None:
                lower_bound_date_str = datetime.fromtimestamp(lower_bound, tz=UTC).strftime(
                    "%Y-%m-%d"
                )
        else:
            # Numeric bounds: just convert to float
            upper_bound = None
            lower_bound = None
            if upper_bound_raw is not None:
                try:
                    upper_bound = float(upper_bound_raw)
                except (TypeError, ValueError):
                    pass
            if lower_bound_raw is not None:
                try:
                    lower_bound = float(lower_bound_raw)
                except (TypeError, ValueError):
                    pass

        # Convert nominal bounds to float if present
        if nominal_upper_bound is not None:
            try:
                nominal_upper_bound = float(nominal_upper_bound)
            except (TypeError, ValueError):
                nominal_upper_bound = None
        if nominal_lower_bound is not None:
            try:
                nominal_lower_bound = float(nominal_lower_bound)
            except (TypeError, ValueError):
                nominal_lower_bound = None

        # Extract tournament slugs from projects
        tournament_slugs = []
        projects = data.get("projects", {})
        if projects:
            # Try tournament list first
            tournaments = projects.get("tournament", [])
            if tournaments:
                tournament_slugs = [str(t.get("slug", "")) for t in tournaments if t.get("slug")]
            # Fall back to question_series
            if not tournament_slugs:
                question_series = projects.get("question_series", [])
                if question_series:
                    tournament_slugs = [
                        str(q.get("slug", "")) for q in question_series if q.get("slug")
                    ]

        # Extract default project ID
        default_project_id = None
        if projects and "default_project" in projects:
            default_project_id = projects["default_project"].get("id")

        # Extract categories
        categories = None
        if projects and "category" in projects:
            categories = projects.get("category", [])

        # Check if already forecasted
        already_forecasted = False
        try:
            my_forecasts = question_data.get("my_forecasts", {})
            history = my_forecasts.get("history") if my_forecasts else None
            already_forecasted = history is not None and len(history) > 0
        except Exception:
            pass

        # Get group label for group questions
        group_label = question_data.get("label")
        if group_label is not None and str(group_label).strip() == "":
            group_label = None

        return cls(
            # Core fields
            id=post_id,
            question_id=question_id,
            title=data.get("title", ""),
            description=data.get("description")
            or question_data.get("description")
            or "",  # Handle None, check nested
            resolution_criteria=data.get("resolution_criteria")
            or question_data.get("resolution_criteria")
            or "",
            fine_print=data.get("fine_print") or question_data.get("fine_print") or "",
            background_info=question_data.get("description")
            or "",  # Background is in nested question.description
            question_type=question_type,
            created_at=data.get("created_at", ""),
            open_time=data.get("open_time") or question_data.get("open_time"),
            scheduled_close_time=data.get("scheduled_close_time")
            or question_data.get("scheduled_close_time"),
            scheduled_resolve_time=data.get("scheduled_resolve_time")
            or question_data.get("scheduled_resolve_time"),
            status=status,
            possibilities=question_data.get("possibilities"),
            options=question_data.get("options"),
            # Numeric question fields
            unit_of_measure=question_data.get("unit") or None,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            open_upper_bound=question_data.get("open_upper_bound"),
            open_lower_bound=question_data.get("open_lower_bound"),
            zero_point=zero_point,
            nominal_upper_bound=nominal_upper_bound,
            nominal_lower_bound=nominal_lower_bound,
            cdf_size=cdf_size,
            # Date question fields
            upper_bound_date_str=upper_bound_date_str,
            lower_bound_date_str=lower_bound_date_str,
            # Community data
            community_prediction=community_pred,
            num_forecasters=data.get("nr_forecasters"),
            # Additional metadata (NOT used in forecasting prompts)
            page_url=f"https://www.metaculus.com/questions/{post_id}",
            published_time=data.get("published_at"),
            actual_resolution_time=question_data.get("actual_resolve_time"),
            cp_reveal_time=question_data.get("cp_reveal_time"),
            close_time=question_data.get("scheduled_close_time"),
            num_predictions=data.get("forecasts_count"),
            already_forecasted=already_forecasted,
            tournament_slugs=tournament_slugs if tournament_slugs else None,
            default_project_id=default_project_id,
            includes_bots_in_aggregates=question_data.get("include_bots_in_aggregates"),
            question_weight=question_data.get("question_weight"),
            resolution_string=question_data.get("resolution"),
            categories=categories,
            group_label=group_label,
            raw=data,
        )

    @classmethod
    def _parse_date_bound(cls, value: Any) -> float | None:
        """Parse a date bound value to Unix timestamp (float).

        Date bounds can be:
        - float/int: Already a Unix timestamp
        - str: ISO format date string (e.g., "2026-12-31T00:00:00Z")
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.timestamp()
            except ValueError:
                pass
        return None


@dataclass
class MetaForecastInfo:
    """Parsed metadata from a meta-forecast question (community prediction movement).

    These are MiniBench-style questions that ask whether the community prediction
    on a target Metaculus question will rise above a threshold by a given date.

    Detected via the JSON format tag at the end of the question description:
    `{"format":"metaculus_binary_cp_rises","info":{"post_id":...,"question_id":...,"last_cp":...}}`
    """

    format: str  # e.g., "metaculus_binary_cp_rises"
    target_post_id: int  # Post ID of the target question (used in URLs)
    target_question_id: int  # Internal question ID of the target
    last_cp: float  # Community prediction at meta-question creation time (0-1 scale)

    @classmethod
    def from_description(cls, description: str | None) -> "MetaForecastInfo | None":
        """Extract meta-forecast info from a question description.

        Looks for the JSON format tag (backtick-wrapped) at the end of the description.
        Returns None if the question is not a meta-forecast question.
        """
        if not description:
            return None

        match = re.search(r"`(\{[^`]+\})`\s*$", description.strip())
        if not match:
            return None

        try:
            tag = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        if tag.get("format") != "metaculus_binary_cp_rises":
            return None

        info = tag.get("info", {})
        post_id = info.get("post_id")
        question_id = info.get("question_id")
        last_cp = info.get("last_cp")

        if post_id is None or question_id is None or last_cp is None:
            return None

        return cls(
            format=tag["format"],
            target_post_id=int(post_id),
            target_question_id=int(question_id),
            last_cp=float(last_cp),
        )


@dataclass
class AggregationHistoryPoint:
    """A single point in a community prediction history timeseries."""

    start_time: float  # Unix timestamp
    end_time: float  # Unix timestamp
    centers: list[float]  # Median values (0-1 scale)
    forecaster_count: int
    interval_lower_bounds: list[float] | None = None  # 25th percentile
    interval_upper_bounds: list[float] | None = None  # 75th percentile


@dataclass
class AggregationHistory:
    """Community prediction history for a Metaculus question."""

    question_title: str
    question_post_id: int
    history: list[AggregationHistoryPoint] = field(default_factory=list)
    latest_cp: float | None = None  # Most recent community prediction (0-1)
    aggregation_method: str | None = None  # "recency_weighted" or "unweighted"

    @classmethod
    def from_api_response(cls, data: dict) -> "AggregationHistory":
        """Parse aggregation history from a Metaculus API /posts/{id}/ response."""
        post_id = data.get("id", 0)
        title = data.get("title", "")
        question_data = data.get("question", {})
        aggregations = question_data.get("aggregations") or {}

        # Try recency_weighted first (standard questions), then unweighted (tournament)
        method = None
        agg_data = None
        for method_name in ("recency_weighted", "unweighted"):
            candidate = aggregations.get(method_name)
            if candidate and (candidate.get("history") or candidate.get("latest")):
                method = method_name
                agg_data = candidate
                break

        if not agg_data:
            return cls(
                question_title=title,
                question_post_id=post_id,
            )

        # Parse history points
        history_points = []
        for entry in agg_data.get("history") or []:
            centers = entry.get("centers", [])
            if not centers:
                continue
            history_points.append(
                AggregationHistoryPoint(
                    start_time=entry.get("start_time", 0),
                    end_time=entry.get("end_time", 0),
                    centers=centers,
                    forecaster_count=entry.get("forecaster_count", 0),
                    interval_lower_bounds=entry.get("interval_lower_bounds"),
                    interval_upper_bounds=entry.get("interval_upper_bounds"),
                )
            )

        # Get latest CP
        latest_cp = None
        latest = agg_data.get("latest")
        if latest:
            latest_centers = latest.get("centers", [])
            if latest_centers:
                latest_cp = latest_centers[0]
        elif history_points:
            latest_cp = history_points[-1].centers[0]

        return cls(
            question_title=title,
            question_post_id=post_id,
            history=history_points,
            latest_cp=latest_cp,
            aggregation_method=method,
        )


@dataclass
class MyForecast:
    """Represents a forecast I've already made."""

    question_id: int
    timestamp: datetime | None = None  # When the forecast was made


@dataclass
class PredictionSubmission:
    """A prediction to submit to Metaculus."""

    question_id: int
    prediction: float | dict | list  # float for binary, dict for MC, list for numeric CDF

    # For tracking
    submitted_at: str | None = None
    api_response: dict | None = None


class MetaculusClient:
    """
    Client for the Metaculus API.

    Usage:
        client = MetaculusClient(token="your_token")
        questions = await client.get_tournament_questions(tournament_id=32721)
        await client.submit_prediction(question_id=12345, prediction=0.65)
    """

    def __init__(self, token: str | None = None):
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
                "Accept-Language": "en",
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
        """Get a single question by ID (post ID)."""
        response = await self.client.get(f"/posts/{question_id}/")
        response.raise_for_status()
        data = response.json()
        return MetaculusQuestion.from_api_response(data)

    async def get_question_by_url(self, url: str) -> MetaculusQuestion:
        """Get a question from its URL."""
        # Extract question ID from URL
        # URLs look like: https://www.metaculus.com/questions/12345/...
        match = re.search(r"/questions/(\d+)", url)
        if not match:
            raise ValueError(f"Could not extract question ID from URL: {url}")
        question_id = int(match.group(1))
        return await self.get_question(question_id)

    async def get_aggregation_history(self, post_id: int) -> AggregationHistory:
        """Fetch the community prediction history for a question.

        Uses the /api2/ endpoint which returns aggregation data that the
        newer /api/posts/ endpoint omits for tournament questions.

        Args:
            post_id: The post ID (as used in Metaculus URLs: /questions/{post_id}/)

        Returns:
            AggregationHistory with the full timeseries of community predictions.
        """
        # The /api/posts/{id}/ endpoint returns aggregations: null for many
        # tournament questions even after cp_reveal_time. The legacy /api2/
        # endpoint reliably includes aggregation history.
        response = await self.client.get(f"https://www.metaculus.com/api2/questions/{post_id}/")
        response.raise_for_status()
        data = response.json()
        return AggregationHistory.from_api_response(data)

    async def get_tournament_questions(
        self,
        tournament_id: int | str,
        status: str | None = "open",
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
            "order_by": "scheduled_close_time",  # Prioritize questions closing soonest
        }
        if status:
            params["statuses"] = status

        response = await self.client.get("/posts/", params=params)
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

    async def get_current_user_id(self) -> int:
        """Get the current authenticated user's ID."""
        response = await self.client.get("/users/me/")
        response.raise_for_status()
        return response.json()["id"]

    async def get_my_forecasts(
        self,
        tournament_id: int | str | None = None,
    ) -> dict[int, "MyForecast"]:
        """
        Get questions I've already forecasted on.

        Uses forecaster_id parameter (matching official Metaculus library)
        rather than the undocumented forecast_by_me parameter.

        Args:
            tournament_id: Optional tournament ID or slug to filter by

        Returns:
            Dict mapping question_id to MyForecast object with timestamp
        """
        # Get current user ID (required for forecaster_id filter)
        user_id = await self.get_current_user_id()

        params = {"forecaster_id": user_id, "limit": 500}
        if tournament_id:
            params["tournaments"] = tournament_id

        response = await self.client.get("/posts/", params=params)
        response.raise_for_status()
        data = response.json()

        # With forecaster_id filter, all returned posts are ones we've forecasted
        # The my_forecasts field may be None in list responses, so we trust the filter
        forecasts = {}
        for item in data.get("results", []):
            question_id = item.get("id")
            if question_id:
                forecasts[question_id] = MyForecast(
                    question_id=question_id,
                    timestamp=None,  # Timestamp not available in list response
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

        # Use the batch forecast endpoint (same as metaculus-forecasting-tools)
        payload = [
            {
                "question": question_id,
                "source": "api",
                "probability_yes": prediction,
            }
        ]

        response = await self.client.post(
            "/questions/forecast/",
            json=payload,
        )
        return self._handle_response(response, f"submitting binary prediction for Q{question_id}")

    async def submit_numeric_prediction(
        self,
        question_id: int,
        cdf: list[float],
        open_lower_bound: bool = True,
        open_upper_bound: bool = True,
        expected_cdf_size: int = 201,
    ) -> dict:
        """
        Submit a numeric prediction as a CDF.

        Args:
            question_id: Question ID
            cdf: List of CDF values (cumulative probabilities)
            open_lower_bound: Whether the lower bound is open (can go below range)
            open_upper_bound: Whether the upper bound is open (can exceed range)
            expected_cdf_size: Expected CDF size (201 for numeric, 102 for discrete)

        Returns:
            API response dict
        """
        if len(cdf) != expected_cdf_size:
            raise ValueError(f"CDF must have exactly {expected_cdf_size} values, got {len(cdf)}")

        # Ensure CDF is valid (monotonic, bounded)
        cdf = self._validate_cdf(cdf, open_lower_bound, open_upper_bound)

        # Use the batch forecast endpoint (same as metaculus-forecasting-tools)
        payload = [
            {
                "question": question_id,
                "source": "api",
                "continuous_cdf": cdf,
            }
        ]

        response = await self.client.post(
            "/questions/forecast/",
            json=payload,
        )
        return self._handle_response(response, f"submitting numeric prediction for Q{question_id}")

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
        # Clamp probabilities to [0.001, 0.999] to avoid literal 0/1
        # (matches binary question floor; API verified to accept these values)
        clamped = {k: max(0.001, min(0.999, v)) for k, v in probabilities.items()}

        # Normalize to sum to 1
        total = sum(clamped.values())
        probabilities = {k: v / total for k, v in clamped.items()}

        # Use the batch forecast endpoint (same as metaculus-forecasting-tools)
        payload = [
            {
                "question": question_id,
                "source": "api",
                "probability_yes_per_category": probabilities,
            }
        ]

        response = await self.client.post(
            "/questions/forecast/",
            json=payload,
        )
        return self._handle_response(
            response, f"submitting multiple choice prediction for Q{question_id}"
        )

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
        # Use question_id (not post id) for the forecast API
        if question.question_type == "binary":
            return await self.submit_binary_prediction(question.question_id, prediction)
        elif question.question_type in ("numeric", "discrete", "date"):
            # Date questions use the same CDF submission as numeric
            return await self.submit_numeric_prediction(
                question.question_id,
                prediction,
                open_lower_bound=question.open_lower_bound or False,
                open_upper_bound=question.open_upper_bound or False,
                expected_cdf_size=question.cdf_size,
            )
        elif question.question_type == "multiple_choice":
            return await self.submit_multiple_choice_prediction(question.question_id, prediction)
        else:
            raise ValueError(f"Unsupported question type: {question.question_type}")

    def _handle_response(self, response: httpx.Response, context: str = "") -> dict:
        """Handle API response, logging detailed error info on failure."""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Log the actual response body from Metaculus
            error_body = ""
            try:
                error_body = e.response.text
            except Exception:
                pass
            logger.error(f"API error {context}: {e.response.status_code} - {error_body}")
            raise

    def _validate_cdf(
        self,
        cdf: list[float],
        open_lower_bound: bool = True,
        open_upper_bound: bool = True,
    ) -> list[float]:
        """
        Validate and fix a CDF to ensure it meets Metaculus requirements.

        This is a backup validator for CDFs already generated by cdf.py.
        The primary standardization happens in cdf._standardize_cdf().

        Requirements:
        - 201 values (or other CDF size), monotonically increasing
        - Minimum step of 5e-05 between consecutive values
        - For open bounds: first value >= 0.001, last value <= 0.999
        - For closed bounds: first value = 0.0 (closed lower), last value = 1.0 (closed upper)
        - No single step exceeds max PMF value (0.2 for 201-point CDF)
        """
        import numpy as np

        cdf = np.array(cdf, dtype=float)
        min_step = 5e-05

        # Determine boundary values based on open/closed bounds
        lower_val = 0.001 if open_lower_bound else 0.0
        upper_val = 0.999 if open_upper_bound else 1.0

        # Clamp interior values (not the boundaries yet)
        cdf[1:-1] = np.clip(cdf[1:-1], lower_val + min_step, upper_val - min_step)

        # Set boundary values
        cdf[0] = lower_val
        cdf[-1] = upper_val

        # Ensure monotonically increasing with minimum step size
        # Work forward, ensuring each value is at least min_step greater than previous
        for i in range(1, len(cdf)):
            min_allowed = cdf[i - 1] + min_step
            if cdf[i] < min_allowed:
                cdf[i] = min_allowed

        # If we exceeded upper_val, we need to redistribute
        if cdf[-1] > upper_val:
            # Calculate how much space we have
            available_range = upper_val - lower_val
            required_range = (len(cdf) - 1) * min_step

            if required_range > available_range:
                # This shouldn't happen with 201 points and 5e-05 step (requires 0.01 range)
                # but handle gracefully by using smaller steps
                actual_step = available_range / (len(cdf) - 1)
                cdf = np.array([lower_val + i * actual_step for i in range(len(cdf))])
            else:
                # Rescale to fit within bounds while maintaining relative distribution
                # Preserve the shape but compress to fit
                cdf_normalized = (cdf - cdf[0]) / (cdf[-1] - cdf[0])  # Normalize to [0, 1]
                cdf = lower_val + cdf_normalized * (upper_val - lower_val)

                # Re-enforce minimum steps after rescaling
                for i in range(1, len(cdf)):
                    if cdf[i] < cdf[i - 1] + min_step:
                        cdf[i] = cdf[i - 1] + min_step

            cdf[-1] = upper_val

        # Ensure no single step exceeds max PMF value (0.2 for 201-point CDF)
        # Formula: 0.2 * (200 / (cdf_size - 1))
        max_step = 0.2 * (200 / (len(cdf) - 1))
        for i in range(1, len(cdf)):
            if cdf[i] - cdf[i - 1] > max_step:
                cdf[i] = cdf[i - 1] + max_step

        return cdf.tolist()

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
def get_client(token: str | None = None) -> MetaculusClient:
    """Get a Metaculus client, using env var if no token provided."""
    return MetaculusClient(token=token)
