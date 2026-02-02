"""
Ecclesia API Client

Handles authentication and API interactions with the Ecclesia backend.
Ecclesia is a SaaS platform for team forecasting on internal business questions.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default Ecclesia API base URL (can be overridden via env var)
ECCLESIA_API_BASE = os.getenv("ECCLESIA_API_BASE", "http://localhost:3000/api")


@dataclass
class EcclesiaBet:
    """
    Parsed Ecclesia bet (question) data.

    Attributes:
        id: MongoDB ObjectId as string
        name: Bet title/question
        description: Detailed question context
        success_criteria: How the bet will be resolved
        bet_type: One of "binary", "numeric", "categorical"
        status: "Active" or "Resolved"
        deadline: Optional deadline date (ISO string)
        categories: For categorical bets, list of category labels
        team_id: Team this bet belongs to
        team_probability: Current team consensus (binary)
        team_numeric_consensus: Current team consensus (numeric)
        team_categorical_consensus: Current team consensus (categorical)
        reviews: List of user forecasts
        resolution_outcome: For resolved binary bets
        numeric_outcome: For resolved numeric bets
        categorical_outcome: For resolved categorical bets (0-based index)
        raw: Full API response for reference
    """

    id: str
    name: str
    description: str
    success_criteria: str
    bet_type: str  # "binary", "numeric", "categorical"
    status: str  # "Active", "Resolved"
    deadline: str | None
    categories: list[str] | None  # For categorical bets
    team_id: str
    team_probability: float | None  # For binary
    team_numeric_consensus: float | None  # For numeric
    team_categorical_consensus: list[float] | None  # For categorical
    reviews: list[dict]
    resolution_outcome: bool | None  # For resolved binary
    numeric_outcome: float | None  # For resolved numeric
    categorical_outcome: int | None  # For resolved categorical
    raw: dict

    @classmethod
    def from_api_response(cls, data: dict) -> "EcclesiaBet":
        """Parse a bet from the API response."""
        bet_type = data.get("betType", "binary")

        # Extract categories for categorical bets
        categories = None
        if bet_type == "categorical" and data.get("categories"):
            categories = [cat.get("label", "") for cat in data.get("categories", [])]

        return cls(
            id=str(data.get("_id", "")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            success_criteria=data.get("successCriteria", ""),
            bet_type=bet_type,
            status=data.get("status", "Active"),
            deadline=data.get("deadline"),
            categories=categories,
            team_id=str(data.get("team", "")),
            team_probability=data.get("teamProbability") or data.get("teamAverageProbability"),
            team_numeric_consensus=data.get("teamNumericConsensus"),
            team_categorical_consensus=data.get("teamCategoricalConsensus"),
            reviews=data.get("reviews", []),
            resolution_outcome=data.get("resolutionOutcome"),
            numeric_outcome=data.get("numericOutcome"),
            categorical_outcome=data.get("categoricalOutcome"),
            raw=data,
        )


@dataclass
class EcclesiaTeam:
    """
    Parsed Ecclesia team data.

    Attributes:
        id: MongoDB ObjectId as string
        name: Team name
        description: Team description/context
        average_brier_score: Team's average Brier score across resolved bets
        score_count: Number of resolved bets scored
        raw: Full API response for reference
    """

    id: str
    name: str
    description: str
    average_brier_score: float | None
    score_count: int
    raw: dict

    @classmethod
    def from_api_response(cls, data: dict) -> "EcclesiaTeam":
        """Parse a team from the API response."""
        return cls(
            id=str(data.get("_id", "")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            average_brier_score=data.get("averageTeamBrierScore"),
            score_count=data.get("scoreCount", 0),
            raw=data,
        )


@dataclass
class AIForecast:
    """
    AI forecast to submit to Ecclesia.

    This represents the bot's forecast, which is stored separately
    from user reviews (doesn't affect team consensus).
    """

    # For binary bets
    probability: float | None = None  # 0-100

    # For numeric bets
    estimate: float | None = None

    # For categorical bets
    category_probabilities: list[float] | None = None  # Must sum to 100

    # Common fields
    reasoning: str = ""
    model_info: str = ""
    cost: float = 0.0


class EcclesiaClient:
    """
    Client for the Ecclesia API.

    Authentication uses JWT tokens. The client can authenticate via:
    1. Username/password login (stores token in cookie)
    2. Direct token (via ECCLESIA_TOKEN env var)

    Usage:
        # With environment variables
        client = EcclesiaClient()
        await client.login(email="user@example.com", password="secret")

        # Or with direct token
        client = EcclesiaClient(token="your_jwt_token")

        # Fetch bets
        bets = await client.get_team_bets()
        bet = await client.get_bet(bet_id="...")

        # Submit AI forecast
        await client.submit_ai_forecast(bet_id="...", forecast=AIForecast(...))
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
    ):
        """
        Initialize the Ecclesia client.

        Args:
            base_url: API base URL (defaults to ECCLESIA_API_BASE env var)
            token: JWT token (defaults to ECCLESIA_TOKEN env var)
        """
        self.base_url = base_url or ECCLESIA_API_BASE
        self._token = token or os.getenv("ECCLESIA_TOKEN")

        # Create client with cookie support
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            cookies=httpx.Cookies(),
        )

        # If we have a token, set it as Authorization header
        if self._token:
            self.client.headers["Authorization"] = f"Bearer {self._token}"

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # =========================================================================
    # Authentication
    # =========================================================================

    async def login(self, email: str, password: str) -> dict:
        """
        Authenticate with email and password.

        This sets the JWT token cookie for subsequent requests.

        Args:
            email: User email
            password: User password

        Returns:
            User data dict

        Raises:
            httpx.HTTPStatusError: If login fails
        """
        response = await self.client.post(
            "/users/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        data = response.json()

        # The token is set as an httpOnly cookie by the server
        # httpx automatically handles cookies
        logger.info(f"Logged in as {email}")

        return data.get("data", data)

    async def logout(self):
        """Log out and clear the session."""
        await self.client.post("/users/logout")
        logger.info("Logged out")

    # =========================================================================
    # Bets (Questions)
    # =========================================================================

    async def get_team_bets(self, status: str | None = None) -> list[EcclesiaBet]:
        """
        Get all bets for the authenticated user's team.

        Args:
            status: Optional filter by status ("Active" or "Resolved")

        Returns:
            List of EcclesiaBet objects
        """
        response = await self.client.get("/bets")
        response.raise_for_status()
        data = response.json()

        bets = [EcclesiaBet.from_api_response(item) for item in data.get("data", [])]

        if status:
            bets = [b for b in bets if b.status == status]

        return bets

    async def get_bet(self, bet_id: str) -> EcclesiaBet:
        """
        Get a single bet by ID.

        Args:
            bet_id: The bet's MongoDB ObjectId

        Returns:
            EcclesiaBet object
        """
        response = await self.client.get(f"/bets/{bet_id}")
        response.raise_for_status()
        data = response.json()
        return EcclesiaBet.from_api_response(data.get("data", data))

    async def get_resolved_bets(self, limit: int = 20) -> list[EcclesiaBet]:
        """
        Get resolved bets for use as reference classes.

        Args:
            limit: Maximum number of resolved bets to return

        Returns:
            List of resolved EcclesiaBet objects
        """
        bets = await self.get_team_bets(status="Resolved")
        return bets[:limit]

    # =========================================================================
    # Teams
    # =========================================================================

    async def get_team(self, team_id: str) -> EcclesiaTeam:
        """
        Get team details.

        Args:
            team_id: The team's MongoDB ObjectId

        Returns:
            EcclesiaTeam object
        """
        response = await self.client.get(f"/teams/{team_id}")
        response.raise_for_status()
        data = response.json()
        return EcclesiaTeam.from_api_response(data.get("data", data))

    async def get_team_calibration(self, team_id: str) -> dict:
        """
        Get team calibration metrics.

        Args:
            team_id: The team's MongoDB ObjectId

        Returns:
            Calibration data dict with bins, actual frequencies, etc.
        """
        response = await self.client.get(f"/teams/{team_id}/calibration")
        response.raise_for_status()
        data = response.json()
        return data.get("data", data)

    # =========================================================================
    # AI Forecasts
    # =========================================================================

    async def submit_ai_forecast(
        self,
        bet_id: str,
        forecast: AIForecast,
    ) -> dict:
        """
        Submit an AI forecast for a bet.

        Note: This submits to a dedicated AI forecast endpoint (to be created
        in Ecclesia backend), not the regular reviews endpoint. This keeps
        AI forecasts separate from human team consensus.

        Args:
            bet_id: The bet's MongoDB ObjectId
            forecast: AIForecast object with prediction and reasoning

        Returns:
            API response dict
        """
        # Build payload based on bet type
        payload: dict[str, Any] = {
            "reasoning": forecast.reasoning,
            "modelInfo": forecast.model_info,
            "cost": forecast.cost,
        }

        if forecast.probability is not None:
            payload["probability"] = forecast.probability
        if forecast.estimate is not None:
            payload["estimate"] = forecast.estimate
        if forecast.category_probabilities is not None:
            payload["categoryProbabilities"] = forecast.category_probabilities

        # Submit to AI forecast endpoint
        # NOTE: This endpoint needs to be created in Ecclesia backend
        response = await self.client.post(
            f"/bets/{bet_id}/ai-forecast",
            json=payload,
        )
        return self._handle_response(response, f"submitting AI forecast for bet {bet_id}")

    async def get_ai_forecast(self, bet_id: str) -> dict | None:
        """
        Get the existing AI forecast for a bet, if any.

        Args:
            bet_id: The bet's MongoDB ObjectId

        Returns:
            AI forecast dict or None if no forecast exists
        """
        try:
            response = await self.client.get(f"/bets/{bet_id}/ai-forecast")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def _handle_response(self, response: httpx.Response, context: str = "") -> dict:
        """Handle API response, logging detailed error info on failure."""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text
            except Exception:
                pass
            logger.error(f"API error {context}: {e.response.status_code} - {error_body}")
            raise


# Convenience function
def get_client(
    base_url: str | None = None,
    token: str | None = None,
) -> EcclesiaClient:
    """Get an Ecclesia client."""
    return EcclesiaClient(base_url=base_url, token=token)
