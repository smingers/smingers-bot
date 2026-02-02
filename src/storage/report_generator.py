"""
Report Generator

Generates human-readable markdown reports from forecast artifacts.
Used for creating detailed reasoning reports for individual forecasts
and summary reports across multiple forecasts (e.g., tournament reviews).

Note: The dataclasses here (DisplayAgentResult, ForecastData) are display-oriented
and differ from the pipeline's internal AgentResult in src/bot/extractors.py.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DisplayAgentResult:
    """Result from a single ensemble agent for display/report purposes.

    Note: This is distinct from src.bot.extractors.AgentResult which is
    used internally by the forecasting pipeline.
    """

    name: str  # Agent identifier (e.g., "forecaster_1")
    model: str  # Model name (e.g., "openrouter/anthropic/claude-sonnet-4.5")
    weight: float  # Ensemble weight (default: 1.0 for all agents)
    prediction: float  # Extracted prediction (probability for binary)
    reasoning: str  # Full reasoning text from agent output
    evidence_weights: dict | None = (
        None  # Categorized evidence (e.g., {"bullish": [...], "bearish": [...]})
    )


@dataclass
class ForecastData:
    """All data needed to generate a comprehensive forecast report.

    Aggregates data from multiple pipeline stages for report generation.
    """

    # Question metadata
    question_id: int  # Metaculus question ID
    question_title: str  # Question title
    question_text: str  # Full question description
    question_type: str  # "binary", "numeric", or "multiple_choice"
    resolution_criteria: str  # How the question resolves
    timestamp: str  # When the forecast was made (ISO format)

    # Research phase
    research_sources_count: int  # Number of sources consulted
    research_summary: str  # Aggregated research findings

    # Outside view (base rate analysis)
    base_rate: float  # Historical base rate estimate
    reference_classes: list[str]  # Reference classes considered
    outside_view_reasoning: str  # Reasoning for base rate

    # Inside view (ensemble predictions)
    agent_results: list[DisplayAgentResult]  # Individual agent predictions
    aggregation_method: str  # How predictions were combined (e.g., "weighted_average")
    final_prediction: float  # Final submitted prediction

    # Calibration
    calibration_checklist: dict  # Calibration checks performed

    # Cost tracking
    research_cost: float  # Research API costs
    llm_cost: float  # LLM inference costs
    total_cost: float  # Total forecast cost


def generate_reasoning_report(data: ForecastData) -> str:
    """
    Generate a comprehensive markdown report for a forecast.

    This is the primary artifact for human review - it should contain
    everything needed to understand and evaluate the forecast.
    """
    lines = []

    # Header
    lines.append(f"# Forecast: {data.question_title}")
    lines.append(f"**Question ID:** {data.question_id}")
    lines.append(f"**Submitted:** {data.timestamp}")
    lines.append(f"**Type:** {data.question_type}")
    lines.append(
        f"**Final Prediction:** {_format_prediction(data.final_prediction, data.question_type)}"
    )
    lines.append("")

    # Question Summary
    lines.append("## Question Summary")
    lines.append(
        data.question_text[:500] + "..." if len(data.question_text) > 500 else data.question_text
    )
    lines.append("")
    lines.append(
        f"**Resolution:** {data.resolution_criteria[:300]}..."
        if len(data.resolution_criteria) > 300
        else f"**Resolution:** {data.resolution_criteria}"
    )
    lines.append("")

    # Research Summary
    lines.append("## Research Summary")
    lines.append(f"- Consulted {data.research_sources_count} sources")
    lines.append("")
    if data.research_summary:
        # Truncate if very long, but preserve key findings
        summary = data.research_summary
        if len(summary) > 2000:
            summary = summary[:2000] + "\n\n*[Summary truncated - see full research artifacts]*"
        lines.append(summary)
    lines.append("")

    # Outside View
    lines.append("## Outside View (Base Rate)")
    lines.append("")
    lines.append("**Reference classes considered:**")
    for i, rc in enumerate(data.reference_classes[:5], 1):
        lines.append(f"{i}. {rc}")
    lines.append("")
    lines.append(f"**Base rate estimate:** {data.base_rate:.1%}")
    lines.append("")
    lines.append("**Reasoning:**")
    lines.append(data.outside_view_reasoning)
    lines.append("")

    # Inside View (Adjustments)
    lines.append("## Inside View (Adjustments)")
    lines.append("")

    for agent in data.agent_results:
        lines.append(f"### {agent.name} ({agent.model})")
        lines.append(f"**Prediction:** {agent.prediction:.1%}")
        lines.append(f"**Weight:** {agent.weight}")
        lines.append("")
        lines.append("**Reasoning:**")
        # Show full reasoning (maximum verbosity as per user preference)
        lines.append(agent.reasoning)
        lines.append("")

        if agent.evidence_weights:
            lines.append("**Evidence weighted:**")
            for category, items in agent.evidence_weights.items():
                if items:
                    lines.append(f"- {category.title()}: {', '.join(items[:3])}")
            lines.append("")

    # Ensemble Aggregation
    lines.append("## Ensemble Aggregation")
    lines.append("")
    lines.append("| Agent | Model | Weight | Prediction |")
    lines.append("|-------|-------|--------|------------|")
    for agent in data.agent_results:
        lines.append(f"| {agent.name} | {agent.model} | {agent.weight} | {agent.prediction:.1%} |")
    lines.append("")

    # Calculate weighted average for display
    total_weight = sum(a.weight for a in data.agent_results)
    weighted_sum = sum(a.prediction * a.weight for a in data.agent_results)
    weighted_avg = weighted_sum / total_weight if total_weight > 0 else data.final_prediction

    lines.append(f"**Aggregation method:** {data.aggregation_method}")
    lines.append(
        f"**Weighted average:** {weighted_avg:.2%} → **Submitted: {data.final_prediction:.1%}**"
    )
    lines.append("")

    # Calibration Checklist
    lines.append("## Calibration Checklist")
    lines.append("")
    for item_id, item_data in data.calibration_checklist.items():
        if isinstance(item_data, dict):
            checked = item_data.get("passed", False)
            response = item_data.get("response", "")
            marker = "[x]" if checked else "[ ]"
            lines.append(f"- {marker} **{item_id}:** {response[:100]}")
        else:
            lines.append(f"- [x] **{item_id}:** {item_data}")
    lines.append("")

    # Costs
    lines.append("## Costs")
    lines.append(f"- Research API calls: ${data.research_cost:.2f}")
    lines.append(f"- LLM calls: ${data.llm_cost:.2f}")
    lines.append(f"- **Total: ${data.total_cost:.2f}**")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated at {datetime.utcnow().isoformat()}Z*")

    return "\n".join(lines)


def _format_prediction(prediction: float, question_type: str) -> str:
    """Format a prediction for display based on question type."""
    if question_type == "binary":
        return f"{prediction:.1%}"
    elif question_type == "multiple_choice":
        return f"{prediction}"  # Would be a dict in practice
    elif question_type == "numeric":
        return f"Median: {prediction}"  # Would be CDF in practice
    return str(prediction)


def generate_summary_report(forecasts: list[dict]) -> str:
    """
    Generate a summary report across multiple forecasts.
    Useful for tournament reviews.
    """
    lines = []

    lines.append("# Forecast Summary Report")
    lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z")
    lines.append(f"**Total Forecasts:** {len(forecasts)}")
    lines.append("")

    # Group by question type
    by_type: dict[str, list] = {}
    for f in forecasts:
        qt = f.get("question_type", "unknown")
        if qt not in by_type:
            by_type[qt] = []
        by_type[qt].append(f)

    lines.append("## By Question Type")
    lines.append("")
    lines.append("| Type | Count | Avg Brier | Avg Cost |")
    lines.append("|------|-------|-----------|----------|")

    for qt, items in sorted(by_type.items()):
        count = len(items)
        brier_scores = [f.get("brier_score") for f in items if f.get("brier_score") is not None]
        avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else None
        costs = [f.get("total_cost", 0) for f in items]
        avg_cost = sum(costs) / len(costs) if costs else 0

        brier_str = f"{avg_brier:.4f}" if avg_brier else "N/A"
        lines.append(f"| {qt} | {count} | {brier_str} | ${avg_cost:.2f} |")

    lines.append("")

    # Recent forecasts
    lines.append("## Recent Forecasts")
    lines.append("")

    recent = sorted(forecasts, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
    for f in recent:
        qid = f.get("question_id", "?")
        title = f.get("question_title", "Unknown")[:50]
        pred = f.get("final_prediction", 0)
        outcome = f.get("actual_outcome")

        outcome_str = f" → Actual: {outcome:.1%}" if outcome is not None else " (pending)"
        lines.append(f"- **Q{qid}**: {title}... | Predicted: {pred:.1%}{outcome_str}")

    return "\n".join(lines)
