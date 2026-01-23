"""
Report Generator

Generates human-readable markdown reports from forecast artifacts.
"""

from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class AgentResult:
    """Result from a single ensemble agent."""
    name: str
    model: str
    weight: float
    prediction: float
    reasoning: str
    evidence_weights: Optional[dict] = None


@dataclass
class ForecastData:
    """All data needed to generate a report."""
    question_id: int
    question_title: str
    question_text: str
    question_type: str
    resolution_criteria: str
    timestamp: str

    # Research
    research_sources_count: int
    research_summary: str

    # Outside view
    base_rate: float
    reference_classes: list[str]
    outside_view_reasoning: str

    # Inside view (ensemble)
    agent_results: list[AgentResult]
    aggregation_method: str
    final_prediction: float

    # Calibration
    calibration_checklist: dict

    # Costs
    research_cost: float
    llm_cost: float
    total_cost: float


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
    lines.append(f"**Final Prediction:** {_format_prediction(data.final_prediction, data.question_type)}")
    lines.append("")

    # Question Summary
    lines.append("## Question Summary")
    lines.append(data.question_text[:500] + "..." if len(data.question_text) > 500 else data.question_text)
    lines.append("")
    lines.append(f"**Resolution:** {data.resolution_criteria[:300]}..." if len(data.resolution_criteria) > 300 else f"**Resolution:** {data.resolution_criteria}")
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
    lines.append(f"**Weighted average:** {weighted_avg:.2%} → **Submitted: {data.final_prediction:.1%}**")
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
