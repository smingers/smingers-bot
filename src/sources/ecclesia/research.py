"""
Ecclesia Context Builder

Builds research context for business forecasting questions.
Unlike Metaculus (which uses web search), Ecclesia context comes from:
- Team description and history
- Resolved bets as reference classes
- Team calibration patterns
- The question's own description and success criteria
"""

import logging
from dataclasses import dataclass

from .client import EcclesiaBet, EcclesiaClient, EcclesiaTeam

logger = logging.getLogger(__name__)


@dataclass
class EcclesiaContext:
    """
    Context gathered for an Ecclesia business question.

    Unlike Metaculus (web search), this context is built from:
    - Team information
    - Question details
    - Historical resolved bets as reference classes
    - Team calibration data
    """

    # Team context
    team_description: str
    team_calibration_summary: str

    # Question context
    question_summary: str

    # Reference classes (similar resolved bets)
    reference_classes: list[dict]

    # Formatted context strings for prompts
    historical_context: str  # For outside view (reference classes)
    current_context: str  # For inside view (team-specific factors)


class EcclesiaContextBuilder:
    """
    Builds forecasting context from Ecclesia internal data.

    This replaces web search with internal business context:
    - Team history and performance patterns
    - Similar past questions and their outcomes
    - Team calibration insights
    """

    def __init__(self, client: EcclesiaClient):
        self.client = client

    async def build_context(
        self,
        bet: EcclesiaBet,
        team: EcclesiaTeam | None = None,
        max_reference_bets: int = 10,
    ) -> EcclesiaContext:
        """
        Build forecasting context for a bet.

        Args:
            bet: The bet to build context for
            team: Optional team object (fetched if not provided)
            max_reference_bets: Maximum number of resolved bets to include

        Returns:
            EcclesiaContext with all relevant context
        """
        # Get team if not provided
        if team is None:
            team = await self.client.get_team(bet.team_id)

        # Get resolved bets as reference classes
        resolved_bets = await self.client.get_resolved_bets(limit=max_reference_bets)

        # Get team calibration data
        try:
            calibration = await self.client.get_team_calibration(team.id)
        except Exception as e:
            logger.warning(f"Could not fetch calibration data: {e}")
            calibration = {}

        # Build question summary
        question_summary = self._build_question_summary(bet)

        # Build team description
        team_description = self._build_team_description(team)

        # Build calibration summary
        calibration_summary = self._build_calibration_summary(calibration)

        # Find similar reference bets
        reference_classes = self._find_reference_classes(bet, resolved_bets)

        # Format context strings for prompts
        historical_context = self._format_historical_context(
            team_description=team_description,
            reference_classes=reference_classes,
        )

        current_context = self._format_current_context(
            question_summary=question_summary,
            calibration_summary=calibration_summary,
            bet=bet,
        )

        return EcclesiaContext(
            team_description=team_description,
            team_calibration_summary=calibration_summary,
            question_summary=question_summary,
            reference_classes=reference_classes,
            historical_context=historical_context,
            current_context=current_context,
        )

    def _build_question_summary(self, bet: EcclesiaBet) -> str:
        """Build a summary of the question for prompts."""
        parts = [
            f"Question: {bet.name}",
            f"Type: {bet.bet_type}",
        ]

        if bet.description:
            parts.append(f"Description: {bet.description}")

        if bet.success_criteria:
            parts.append(f"Success Criteria: {bet.success_criteria}")

        if bet.deadline:
            parts.append(f"Deadline: {bet.deadline}")

        if bet.bet_type == "categorical" and bet.categories:
            parts.append(f"Categories: {', '.join(bet.categories)}")

        # Include current team consensus if available
        if bet.bet_type == "binary" and bet.team_probability is not None:
            parts.append(f"Current Team Consensus: {bet.team_probability:.0f}%")
        elif bet.bet_type == "numeric" and bet.team_numeric_consensus is not None:
            parts.append(f"Current Team Consensus: {bet.team_numeric_consensus:.2f}")
        elif bet.bet_type == "categorical" and bet.team_categorical_consensus:
            categories = bet.categories or []
            consensus_str = ", ".join(
                f"{cat}: {prob:.0f}%"
                for cat, prob in zip(categories, bet.team_categorical_consensus, strict=True)
            )
            parts.append(f"Current Team Consensus: {consensus_str}")

        return "\n".join(parts)

    def _build_team_description(self, team: EcclesiaTeam) -> str:
        """Build a description of the team for context."""
        parts = [f"Team: {team.name}"]

        if team.description:
            parts.append(f"About: {team.description}")

        if team.average_brier_score is not None:
            # Interpret Brier score
            brier = team.average_brier_score
            if brier < 0.1:
                quality = "excellent calibration"
            elif brier < 0.2:
                quality = "good calibration"
            elif brier < 0.3:
                quality = "moderate calibration"
            else:
                quality = "room for improvement in calibration"
            parts.append(f"Team Performance: Average Brier Score {brier:.3f} ({quality})")

        if team.score_count:
            parts.append(f"Resolved Questions: {team.score_count}")

        return "\n".join(parts)

    def _build_calibration_summary(self, calibration: dict) -> str:
        """Build a summary of team calibration patterns."""
        if not calibration:
            return "No calibration data available."

        parts = ["Team Calibration Patterns:"]

        # Check for overconfidence/underconfidence patterns
        bins = calibration.get("bins", [])
        if bins:
            overconfident_ranges = []
            underconfident_ranges = []

            for bin_data in bins:
                predicted = bin_data.get("binCenter", 0)
                actual = bin_data.get("actualFrequency", 0)
                count = bin_data.get("count", 0)

                if count < 3:  # Skip bins with too few samples
                    continue

                diff = actual - predicted
                if diff > 10:  # Underconfident: actual > predicted
                    underconfident_ranges.append(f"{predicted:.0f}%")
                elif diff < -10:  # Overconfident: predicted > actual
                    overconfident_ranges.append(f"{predicted:.0f}%")

            if overconfident_ranges:
                parts.append(
                    f"- Team tends to be OVERCONFIDENT around: {', '.join(overconfident_ranges)}"
                )
            if underconfident_ranges:
                parts.append(
                    f"- Team tends to be UNDERCONFIDENT around: {', '.join(underconfident_ranges)}"
                )

        # Overall calibration quality
        overall_bias = calibration.get("overallBias")
        if overall_bias is not None:
            if overall_bias > 5:
                parts.append("- Overall: Team tends to underestimate probabilities")
            elif overall_bias < -5:
                parts.append("- Overall: Team tends to overestimate probabilities")
            else:
                parts.append("- Overall: Team is reasonably well-calibrated")

        if len(parts) == 1:
            parts.append("- Insufficient data for detailed calibration analysis")

        return "\n".join(parts)

    def _find_reference_classes(
        self,
        bet: EcclesiaBet,
        resolved_bets: list[EcclesiaBet],
    ) -> list[dict]:
        """
        Find similar resolved bets as reference classes.

        Returns bets with similar characteristics:
        - Same bet type
        - Similar themes (based on keywords)
        """
        reference_classes = []

        # Filter to same bet type
        same_type_bets = [b for b in resolved_bets if b.bet_type == bet.bet_type]

        for resolved_bet in same_type_bets[:10]:  # Limit to 10 reference classes
            ref = {
                "name": resolved_bet.name,
                "description": resolved_bet.description[:200] if resolved_bet.description else "",
                "bet_type": resolved_bet.bet_type,
            }

            # Add outcome information
            if resolved_bet.bet_type == "binary":
                ref["outcome"] = "Yes" if resolved_bet.resolution_outcome else "No"
                ref["team_forecast"] = (
                    f"{resolved_bet.team_probability:.0f}%"
                    if resolved_bet.team_probability
                    else "N/A"
                )
            elif resolved_bet.bet_type == "numeric":
                ref["outcome"] = resolved_bet.numeric_outcome
                ref["team_forecast"] = resolved_bet.team_numeric_consensus
            elif resolved_bet.bet_type == "categorical":
                if resolved_bet.categorical_outcome is not None and resolved_bet.categories:
                    ref["outcome"] = resolved_bet.categories[resolved_bet.categorical_outcome]
                else:
                    ref["outcome"] = "Unknown"

            reference_classes.append(ref)

        return reference_classes

    def _format_historical_context(
        self,
        team_description: str,
        reference_classes: list[dict],
    ) -> str:
        """Format historical context for outside view prompt."""
        parts = [
            "=== TEAM CONTEXT ===",
            team_description,
            "",
            "=== REFERENCE CLASSES (Similar Past Questions) ===",
        ]

        if not reference_classes:
            parts.append("No similar resolved questions available for reference.")
        else:
            for i, ref in enumerate(reference_classes, 1):
                parts.append(f"\n{i}. {ref['name']}")
                if ref.get("description"):
                    parts.append(f"   Context: {ref['description']}")
                parts.append(f"   Type: {ref['bet_type']}")
                parts.append(f"   Team Forecast: {ref.get('team_forecast', 'N/A')}")
                parts.append(f"   Actual Outcome: {ref.get('outcome', 'N/A')}")

        return "\n".join(parts)

    def _format_current_context(
        self,
        question_summary: str,
        calibration_summary: str,
        bet: EcclesiaBet,
    ) -> str:
        """Format current context for inside view prompt."""
        parts = [
            "=== CURRENT QUESTION ===",
            question_summary,
            "",
            "=== CALIBRATION INSIGHTS ===",
            calibration_summary,
        ]

        # Add any existing reviews as additional context
        if bet.reviews:
            parts.append("")
            parts.append("=== EXISTING TEAM FORECASTS ===")
            for review in bet.reviews[:5]:  # Limit to 5 most recent
                reviewer = review.get("owner", {})
                reviewer_name = (
                    f"{reviewer.get('firstName', '')} {reviewer.get('lastName', '')}".strip()
                    or "Team member"
                )

                if bet.bet_type == "binary":
                    prob = review.get("probability")
                    if prob is not None:
                        parts.append(f"- {reviewer_name}: {prob:.0f}%")
                elif bet.bet_type == "numeric":
                    est = review.get("estimate")
                    if est is not None:
                        parts.append(f"- {reviewer_name}: {est:.2f}")

                comment = review.get("comments", "")
                if comment:
                    parts.append(f"  Reasoning: {comment[:100]}...")

        return "\n".join(parts)
