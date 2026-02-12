#!/usr/bin/env python3
"""
Ensemble Diversity Analysis Report

Extracts outside view and inside view predictions from all forecasters across
all forecasts, then generates an HTML report showing:
- Per-forecast: 5 outside view predictions, 5 inside view predictions, final aggregation
- Cross-pollination aware: shifts computed against the OV each forecaster actually received
- Diversity metrics: range, std dev, coefficient of variation
- Anchoring analysis: how much each forecaster shifted from received OV to inside view
- Grouped by question type (binary, numeric, multiple choice, discrete)
- Excludes test mode forecasts and pre-refactor (pre Jan 27) artifacts

Usage:
    python scripts/ensemble_diversity_report.py
    python scripts/ensemble_diversity_report.py --output report.html
"""

import argparse
import json
import logging
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("./data")

# Cross-pollination map from base_forecaster.py (0-indexed)
# Maps: forecaster_index -> source_forecaster_index whose outside view they receive
# F1 receives F1's OV (self), F2 receives F4's OV, F3 receives F2's OV,
# F4 receives F3's OV, F5 receives F5's OV (self)
CROSS_POLLINATION_MAP: dict[int, int] = {
    0: 0,  # F1 ← F1 (self)
    1: 3,  # F2 ← F4
    2: 1,  # F3 ← F2
    3: 2,  # F4 ← F3
    4: 4,  # F5 ← F5 (self)
}


@dataclass
class ForecasterView:
    """One forecaster's outside and inside view predictions."""

    agent_id: str
    model: str
    outside_view: float | None = None  # Binary: probability, Numeric: median
    inside_view: float | None = None
    received_outside_view: float | None = (
        None  # The OV they actually received via cross-pollination
    )
    received_from: str | None = None  # Which forecaster's OV they received (e.g. "F4")
    outside_view_percentiles: dict | None = None  # Numeric only
    inside_view_percentiles: dict | None = None
    outside_view_probs: list[float] | None = None  # MC only
    inside_view_probs: list[float] | None = None
    shift: float | None = None  # inside view - received outside view (the actual anchoring signal)
    shift_pct: float | None = None  # shift as % of received outside view


@dataclass
class ForecastAnalysis:
    """Complete analysis for one forecast."""

    forecast_id: str
    question_id: int
    timestamp: str
    question_title: str
    question_type: str
    mode: str
    final_prediction: float | None = None
    forecasters: list[ForecasterView] = field(default_factory=list)
    options: list[str] = field(default_factory=list)  # MC option labels

    # Diversity metrics (computed)
    outside_view_range: float | None = None
    outside_view_std: float | None = None
    inside_view_range: float | None = None
    inside_view_std: float | None = None
    avg_shift: float | None = None
    avg_abs_shift: float | None = None


def _strip_markdown(text: str) -> str:
    """Strip markdown bold/italic markers from text."""
    # Remove **bold** and *italic* markers
    return re.sub(r"\*{1,3}", "", text)


def extract_binary_probability_from_text(text: str) -> float | None:
    """Extract a probability from the end of an outside/inside view markdown."""
    if not text:
        return None

    # Look for common patterns at the end of the text
    # GPT-5.2 wraps values in **bold** markdown, so we strip that first
    lines = text.strip().split("\n")
    full_text = _strip_markdown("\n".join(lines[-20:]))

    # Pass 1: Look for "Outside View Prediction:" or "Inside View Prediction:" label
    # then grab the number on the same line or next line
    m = re.search(
        r"(?:Outside|Inside)\s+View\s+Prediction[:\s]*\n?\s*"
        r"(?:(?:Yes|No)\s*[=:]\s*)?(\d+(?:\.\d+)?)\s*%",
        full_text,
    )
    if m:
        val = float(m.group(1))
        return val / 100 if val > 1 else val

    # Pass 2: Look for "Probability: N%" at end of text (the canonical ending format)
    m = re.search(r"[Pp]robability:\s*(\d+(?:\.\d+)?)\s*%?\s*$", full_text)
    if m:
        val = float(m.group(1))
        return val / 100 if val > 1 else val

    # Pass 3: Search last 10 lines for tight patterns only
    for line in reversed(lines[-10:]):
        line = _strip_markdown(line.strip())

        # "Probability: 18%" or "Probability: 18" (colon required to avoid matching prose)
        m = re.search(r"[Pp]robability:\s*(\d+(?:\.\d+)?)\s*%?", line)
        if m:
            val = float(m.group(1))
            return val / 100 if val > 1 else val

        # "Yes = 53%" or "Yes: 53%" (GPT-5.2 sometimes prefixes with Yes/No)
        m = re.search(r"(?:Yes|No)\s*[=:]\s*(\d+(?:\.\d+)?)\s*%", line)
        if m:
            val = float(m.group(1))
            return val / 100 if val > 1 else val

        # Bare number as a prediction on its own line (e.g. "27%")
        m = re.match(r"^(\d+(?:\.\d+)?)\s*%$", line)
        if m:
            val = float(m.group(1))
            return val / 100 if val > 1 else val

    # Pass 4: Loose pattern — "a 1.3% probability" but only on a short standalone line
    # (avoids matching prose like "96% probability of NO settlement")
    for line in reversed(lines[-10:]):
        line = _strip_markdown(line.strip())
        if len(line) < 60:  # short lines are more likely to be predictions
            m = re.match(r"^.*?(\d+(?:\.\d+)?)\s*%\s*probability\s*[.!]?\s*$", line)
            if m:
                val = float(m.group(1))
                return val / 100 if val > 1 else val

    return None


def _parse_date_to_timestamp(date_str: str) -> float | None:
    """Parse a YYYY-MM-DD date string to Unix timestamp (midnight UTC)."""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        dt = dt.replace(tzinfo=timezone.utc)  # noqa: UP017
        return dt.timestamp()
    except ValueError:
        return None


def extract_numeric_percentiles_from_text(text: str) -> dict | None:
    """Extract percentile predictions from numeric forecast text.

    Handles:
    - Plain numbers: "Percentile 10: 2.65"
    - Comma-separated: "Percentile 10: 3,200,000,000"
    - Space-separated: "Percentile 10: 5 800 000 000"
    - Scientific notation: "Percentile 10: 1.5e+9"
    - Date values: "Percentile 10: 2026-02-28" (converted to Unix timestamps)
    """
    if not text:
        return None

    # Strip markdown bold markers (GPT-5.2 sometimes bolds values)
    clean = _strip_markdown(text)

    percentiles = {}

    # First try date pattern: "Percentile N: YYYY-MM-DD"
    for m in re.finditer(
        r"Percentile\s+(\d+)[:\s]+(\d{4}-\d{2}-\d{2})",
        clean,
    ):
        pct = int(m.group(1))
        ts = _parse_date_to_timestamp(m.group(2))
        if ts is not None:
            percentiles[pct] = ts

    if percentiles:
        return percentiles

    # Numeric pattern: handles comma-separated, space-separated, decimal, scientific notation
    for m in re.finditer(
        r"Percentile\s+(\d+)[:\s]+"
        r"([+-]?\d+(?:,\d{3})*(?:\.\d+)?(?:e[+-]?\d+)?(?:\s+\d{3})*)",
        clean,
    ):
        pct = int(m.group(1))
        raw = m.group(2).replace(",", "").replace(" ", "")
        val = float(raw)
        percentiles[pct] = val

    return percentiles if percentiles else None


def extract_mc_probabilities_from_text(text: str) -> list[float] | None:
    """Extract multiple choice probabilities from text."""
    if not text:
        return None

    # Strip markdown bold markers (GPT-5.2 sometimes bolds values)
    clean = _strip_markdown(text)

    # Look for "Probabilities: [12, 20, 68]" pattern
    m = re.search(r"Probabilities:\s*\[([^\]]+)\]", clean)
    if m:
        try:
            probs = [float(x.strip()) for x in m.group(1).split(",")]
            # Normalize to 0-1 if needed
            if any(p > 1 for p in probs):
                probs = [p / 100 for p in probs]
            return probs
        except ValueError:
            pass

    # Look for "Option: N%" patterns, but only AFTER the prediction header
    # to avoid picking up calibration/reasoning text that also contains ": N%" patterns
    search_text = clean[-500:]
    for header in ["Outside View Prediction:", "Inside View Prediction:", "Prediction:"]:
        idx = search_text.rfind(header)
        if idx != -1:
            search_text = search_text[idx:]
            break

    probs = []
    for m in re.finditer(r":\s*(\d+(?:\.\d+)?)\s*%", search_text):
        probs.append(float(m.group(1)) / 100)

    return probs if len(probs) >= 2 else None


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text()
    except OSError:
        return None


def analyze_forecast(forecast_dir: Path) -> ForecastAnalysis | None:
    """Analyze a single forecast directory."""
    parts = forecast_dir.name.rsplit("_", 2)
    if len(parts) < 3:
        return None

    question_id = int(parts[0])
    timestamp = f"{parts[1]}_{parts[2]}"
    forecast_id = forecast_dir.name

    # Load metadata
    metadata = load_json(forecast_dir / "metadata.json")
    if not metadata:
        return None

    # Skip errored forecasts
    if metadata.get("errors"):
        return None

    config = metadata.get("config_snapshot", {})
    mode = config.get("mode", "unknown")

    # Load question info
    question_data = load_json(forecast_dir / "question.json")
    if not question_data:
        return None

    q = question_data.get("question", question_data)
    question_type = q.get("type", "binary")
    title = question_data.get("title") or q.get("title", "")

    # Only new-format artifacts (ensemble/ directory)
    ensemble_dir = forecast_dir / "ensemble"
    if not ensemble_dir.is_dir():
        return None

    edir = ensemble_dir

    # Get ensemble config
    active_agents = config.get("_active_agents", [])
    if not active_agents:
        tier = "fast" if mode == "test" else "quality"
        active_agents = config.get("ensemble", {}).get(
            tier, config.get("ensemble", {}).get("production", [])
        )

    agent_config = {}
    for agent in active_agents:
        agent_config[agent.get("name", "")] = agent.get("model", "unknown")

    # Load aggregation
    aggregation = load_json(edir / "aggregation.json")

    # Get final prediction
    final_prediction = None
    if aggregation:
        if question_type == "binary":
            final_prediction = aggregation.get("final_probability")
        elif question_type in ("numeric", "discrete"):
            # aggregation has final_cdf but not easily summarizable as single number
            pred = load_json(forecast_dir / "prediction.json")
            if pred:
                pcts = pred.get("percentiles", {})
                final_prediction = pcts.get("50", pcts.get(50))
        elif question_type == "date":
            # For date questions, prediction.json percentiles are CDF probabilities (0-1),
            # not timestamps. Use the average of agent median timestamps instead;
            # this gets computed later after forecaster extraction, so set to None here.
            final_prediction = None
        elif question_type == "multiple_choice":
            raw_final = aggregation.get("final_probabilities")
            if isinstance(raw_final, dict):
                final_prediction = list(raw_final.values())
            elif isinstance(raw_final, list):
                final_prediction = raw_final
            else:
                final_prediction = None

    # Extract options for MC
    options = []
    if question_type == "multiple_choice":
        raw_options = q.get("options") or question_data.get("options", [])
        for opt in raw_options or []:
            if isinstance(opt, str):
                options.append(opt)
            elif isinstance(opt, dict):
                options.append(opt.get("label", "?"))

    analysis = ForecastAnalysis(
        forecast_id=forecast_id,
        question_id=question_id,
        timestamp=timestamp,
        question_title=title[:100],
        question_type=question_type,
        mode=mode,
        final_prediction=final_prediction,
        options=options,
    )

    # Extract per-forecaster data
    for i in range(1, 6):
        agent_id = f"forecaster_{i}"
        model = agent_config.get(agent_id, "unknown")

        fv = ForecasterView(agent_id=agent_id, model=model)

        # Load outside view text (try both naming conventions)
        ov_text = read_text(edir / f"forecaster_{i}_outside_view.md")
        if ov_text is None:
            ov_text = read_text(edir / f"agent_{i}_step1.md")  # older naming

        # Load inside view text (try both naming conventions)
        iv_text = read_text(edir / f"forecaster_{i}_inside_view.md")
        if iv_text is None:
            iv_text = read_text(edir / f"agent_{i}_step2.md")  # older naming

        # Load inside view JSON (final extracted prediction, try both naming conventions)
        iv_json = load_json(edir / f"forecaster_{i}.json")
        if iv_json is None:
            iv_json = load_json(edir / f"agent_{i}.json")  # older naming

        if question_type == "binary":
            # Extract outside view probability from text
            fv.outside_view = extract_binary_probability_from_text(ov_text or "")

            # Extract inside view from JSON first, then text
            # JSON stores probability as percentage (1-99, clamped by extractor)
            if iv_json and "probability" in iv_json and iv_json["probability"] is not None:
                raw = iv_json["probability"]
                fv.inside_view = raw / 100
            else:
                fv.inside_view = extract_binary_probability_from_text(iv_text or "")

        elif question_type in ("numeric", "discrete", "date"):
            # Extract percentiles
            fv.outside_view_percentiles = extract_numeric_percentiles_from_text(ov_text or "")
            if iv_json and "percentiles" in iv_json:
                fv.inside_view_percentiles = iv_json["percentiles"]
            else:
                fv.inside_view_percentiles = extract_numeric_percentiles_from_text(iv_text or "")

            # Use median (p50 or interpolated p40/p60) as summary stat
            if fv.outside_view_percentiles:
                p = fv.outside_view_percentiles
                fv.outside_view = p.get(50, p.get("50"))
                if fv.outside_view is None:
                    p40 = p.get(40, p.get("40"))
                    p60 = p.get(60, p.get("60"))
                    if p40 is not None and p60 is not None:
                        fv.outside_view = (p40 + p60) / 2

            if fv.inside_view_percentiles:
                p = fv.inside_view_percentiles
                fv.inside_view = p.get(50, p.get("50"))
                if fv.inside_view is None:
                    p40 = p.get(40, p.get("40"))
                    p60 = p.get(60, p.get("60"))
                    if p40 is not None and p60 is not None:
                        fv.inside_view = (p40 + p60) / 2

        elif question_type == "multiple_choice":
            fv.outside_view_probs = extract_mc_probabilities_from_text(ov_text or "")
            if iv_json and "probabilities" in iv_json and iv_json["probabilities"]:
                raw = iv_json["probabilities"]
                if any(p > 1 for p in raw):
                    fv.inside_view_probs = [p / 100 for p in raw]
                else:
                    fv.inside_view_probs = raw
            else:
                fv.inside_view_probs = extract_mc_probabilities_from_text(iv_text or "")

            # Use max probability as summary for diversity calculation
            if fv.outside_view_probs:
                fv.outside_view = max(fv.outside_view_probs)
            if fv.inside_view_probs:
                fv.inside_view = max(fv.inside_view_probs)

        analysis.forecasters.append(fv)

    # Apply cross-pollination mapping to compute shifts against the RECEIVED outside view
    # F1←F1(self), F2←F4, F3←F2, F4←F3, F5←F5(self)
    for i, fv in enumerate(analysis.forecasters):
        source_idx = CROSS_POLLINATION_MAP.get(i, i)
        source_fv = analysis.forecasters[source_idx]
        fv.received_outside_view = source_fv.outside_view
        fv.received_from = f"F{source_idx + 1}" + (" (self)" if source_idx == i else "")

        # Compute shift against the OV they actually received
        if fv.received_outside_view is not None and fv.inside_view is not None:
            fv.shift = fv.inside_view - fv.received_outside_view
            if abs(fv.received_outside_view) > 0.001:
                fv.shift_pct = fv.shift / abs(fv.received_outside_view) * 100

    # Compute diversity metrics
    ov_vals = [f.outside_view for f in analysis.forecasters if f.outside_view is not None]
    iv_vals = [f.inside_view for f in analysis.forecasters if f.inside_view is not None]
    shifts = [f.shift for f in analysis.forecasters if f.shift is not None]

    if len(ov_vals) >= 2:
        analysis.outside_view_range = max(ov_vals) - min(ov_vals)
        analysis.outside_view_std = statistics.stdev(ov_vals)

    if len(iv_vals) >= 2:
        analysis.inside_view_range = max(iv_vals) - min(iv_vals)
        analysis.inside_view_std = statistics.stdev(iv_vals)

    if shifts:
        analysis.avg_shift = statistics.mean(shifts)
        analysis.avg_abs_shift = statistics.mean(abs(s) for s in shifts)

    # For date questions, compute final prediction as average of agent median timestamps
    # (prediction.json percentiles are CDF probabilities, not timestamps)
    if question_type == "date" and analysis.final_prediction is None and iv_vals:
        analysis.final_prediction = statistics.mean(iv_vals)

    return analysis


def generate_html(analyses: list[ForecastAnalysis], output_path: Path):
    """Generate interactive HTML report."""

    # Group by question type
    by_type: dict[str, list[ForecastAnalysis]] = {}
    for a in analyses:
        by_type.setdefault(a.question_type, []).append(a)

    # Compute aggregate stats per type
    type_stats = {}
    for qtype, forecasts in by_type.items():
        ov_stds = [f.outside_view_std for f in forecasts if f.outside_view_std is not None]
        iv_stds = [f.inside_view_std for f in forecasts if f.inside_view_std is not None]
        ov_ranges = [f.outside_view_range for f in forecasts if f.outside_view_range is not None]
        iv_ranges = [f.inside_view_range for f in forecasts if f.inside_view_range is not None]
        avg_shifts = [f.avg_shift for f in forecasts if f.avg_shift is not None]
        abs_shifts = [f.avg_abs_shift for f in forecasts if f.avg_abs_shift is not None]

        # For non-binary types, compute relative shifts (% of outside view)
        # so the summary stats are interpretable across different scales
        rel_abs_shifts = []
        for forecast in forecasts:
            for fc in forecast.forecasters:
                if fc.shift_pct is not None:
                    rel_abs_shifts.append(abs(fc.shift_pct))

        # For non-binary types, compute coefficient of variation (CV) per forecast
        # CV = stddev / |mean| — normalized metric comparable across scales
        ov_cvs = []
        iv_cvs = []
        for forecast in forecasts:
            ov_vals = [
                fc.outside_view for fc in forecast.forecasters if fc.outside_view is not None
            ]
            iv_vals = [fc.inside_view for fc in forecast.forecasters if fc.inside_view is not None]
            if len(ov_vals) >= 2:
                mean_ov = statistics.mean(ov_vals)
                if abs(mean_ov) > 0:
                    ov_cvs.append(statistics.stdev(ov_vals) / abs(mean_ov) * 100)
            if len(iv_vals) >= 2:
                mean_iv = statistics.mean(iv_vals)
                if abs(mean_iv) > 0:
                    iv_cvs.append(statistics.stdev(iv_vals) / abs(mean_iv) * 100)

        type_stats[qtype] = {
            "count": len(forecasts),
            "avg_ov_std": statistics.mean(ov_stds) if ov_stds else None,
            "avg_iv_std": statistics.mean(iv_stds) if iv_stds else None,
            "avg_ov_range": statistics.mean(ov_ranges) if ov_ranges else None,
            "avg_iv_range": statistics.mean(iv_ranges) if iv_ranges else None,
            "avg_shift": statistics.mean(avg_shifts) if avg_shifts else None,
            "avg_abs_shift": statistics.mean(abs_shifts) if abs_shifts else None,
            "avg_rel_abs_shift": statistics.mean(rel_abs_shifts) if rel_abs_shifts else None,
            "avg_ov_cv": statistics.mean(ov_cvs) if ov_cvs else None,
            "avg_iv_cv": statistics.mean(iv_cvs) if iv_cvs else None,
            "diversity_change": (
                (statistics.mean(iv_cvs) - statistics.mean(ov_cvs)) / statistics.mean(ov_cvs) * 100
                if ov_cvs and iv_cvs and statistics.mean(ov_cvs) > 0
                else (
                    (statistics.mean(iv_stds) - statistics.mean(ov_stds))
                    / statistics.mean(ov_stds)
                    * 100
                    if ov_stds and iv_stds and statistics.mean(ov_stds) > 0
                    else None
                )
            ),
        }

    html = _build_html(analyses, by_type, type_stats)

    output_path.write_text(html)
    logger.info(f"Report written to {output_path}")
    print(f"Report written to {output_path}")
    print(f"Total forecasts analyzed: {len(analyses)}")
    for qtype, stats in sorted(type_stats.items()):
        print(f"  {qtype}: {stats['count']} forecasts")


def _fmt(val, fmt_type="pct"):
    """Format a value for display."""
    if val is None:
        return "—"
    if isinstance(val, (list, dict)):
        return str(val)
    if fmt_type == "pct":
        return f"{val:.1%}"
    elif fmt_type == "pct_pts":
        return f"{val:+.1%}" if val != 0 else "0.0%"
    elif fmt_type == "date":
        # Unix timestamp -> readable date
        try:
            dt = datetime.fromtimestamp(val, tz=timezone.utc)  # noqa: UP017
            return dt.strftime("%Y-%m-%d")
        except (OSError, ValueError, OverflowError):
            return f"{val:,.0f}"
    elif fmt_type == "date_delta":
        # Duration in seconds -> readable days
        days = val / 86400
        if abs(days) < 1:
            return f"{val / 3600:+.1f}h"
        return f"{days:+.0f}d"
    elif fmt_type == "num":
        if abs(val) >= 1000:
            return f"{val:,.0f}"
        elif abs(val) >= 1:
            return f"{val:.2f}"
        else:
            return f"{val:.4f}"
    return str(val)


def _shift_color(shift: float | None) -> str:
    """Return a CSS color based on shift magnitude."""
    if shift is None:
        return "#888"
    abs_s = abs(shift)
    if abs_s < 0.02:
        return "#666"  # minimal shift
    elif abs_s < 0.05:
        return "#b8860b"  # moderate
    elif abs_s < 0.10:
        return "#e67700"  # notable
    else:
        return "#d63031"  # large


def _diversity_indicator(std: float | None, qtype: str) -> str:
    """Return an indicator of diversity level."""
    if std is None:
        return ""
    if qtype == "binary":
        if std < 0.03:
            return '<span class="badge low">Low</span>'
        elif std < 0.08:
            return '<span class="badge med">Med</span>'
        else:
            return '<span class="badge high">High</span>'
    else:
        # For numeric, use coefficient of variation thresholds
        return ""


def _build_html(
    analyses: list[ForecastAnalysis],
    by_type: dict[str, list[ForecastAnalysis]],
    type_stats: dict,
) -> str:
    sections = []

    for qtype in ["binary", "numeric", "multiple_choice", "discrete", "date"]:
        if qtype not in by_type:
            continue

        forecasts = by_type[qtype]
        stats = type_stats[qtype]

        # Summary cards — for binary use raw stddev/range; for others use CV (normalized)
        is_binary = qtype == "binary"
        if is_binary:
            spread_label_ov = "Avg Outside View StdDev"
            spread_label_iv = "Avg Inside View StdDev"
            spread_value_ov = _fmt(stats["avg_ov_std"], "pct")
            spread_value_iv = _fmt(stats["avg_iv_std"], "pct")
            move_value = _fmt(stats["avg_abs_shift"], "pct")
        else:
            spread_label_ov = "Avg Outside View CV"
            spread_label_iv = "Avg Inside View CV"
            spread_value_ov = (
                f"{stats['avg_ov_cv']:.1f}%" if stats.get("avg_ov_cv") is not None else "—"
            )
            spread_value_iv = (
                f"{stats['avg_iv_cv']:.1f}%" if stats.get("avg_iv_cv") is not None else "—"
            )
            move_value = (
                f"{stats['avg_rel_abs_shift']:.1f}%"
                if stats.get("avg_rel_abs_shift") is not None
                else "—"
            )

        div_change = stats.get("diversity_change")
        div_class = (
            "convergence"
            if div_change and div_change < 0
            else ("divergence" if div_change and div_change > 0 else "")
        )
        div_value = f"{div_change:+.0f}%" if div_change is not None else "—"
        div_direction = (
            "converge"
            if div_change and div_change < 0
            else ("diverge" if div_change and div_change > 0 else "stay same")
        )
        div_sign = (
            "−" if div_change and div_change < 0 else ("+" if div_change and div_change > 0 else "")
        )

        summary_html = f"""
        <div class="type-summary">
            <div class="stat-card">
                <div class="stat-value">{stats["count"]}</div>
                <div class="stat-label">Forecasts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{spread_value_ov}</div>
                <div class="stat-label">{spread_label_ov}<br><span class="stat-sublabel">{"std dev of forecaster predictions" if is_binary else "coefficient of variation, normalized across scales"}</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{spread_value_iv}</div>
                <div class="stat-label">{spread_label_iv}<br><span class="stat-sublabel">{"std dev of forecaster predictions" if is_binary else "coefficient of variation, normalized across scales"}</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{move_value}</div>
                <div class="stat-label">Avg Prediction Move<br><span class="stat-sublabel">per forecaster, outside view → inside view</span></div>
            </div>
            <div class="stat-card {div_class}">
                <div class="stat-value">{div_value}</div>
                <div class="stat-label">Ensemble Spread Change<br><span class="stat-sublabel">{div_sign}= forecasters {div_direction} after inside view</span></div>
            </div>
        </div>
        """

        # Per-forecast rows
        rows_html = []
        for a in sorted(forecasts, key=lambda x: x.timestamp, reverse=True):
            is_pct = qtype == "binary"
            is_date = qtype == "date"
            fmt = "pct" if is_pct else ("date" if is_date else "num")
            fmt_shift = "pct_pts" if is_pct else "num"

            # Build forecaster cells
            is_mc = qtype == "multiple_choice"
            fc_rows = []
            for f in a.forecasters:
                # For MC, show compact probability distribution; for others, single value
                if is_mc and f.outside_view_probs:
                    ov_display = " / ".join(f"{p:.0%}" for p in f.outside_view_probs)
                else:
                    ov_display = _fmt(f.outside_view, fmt) if f.outside_view is not None else "—"
                if is_mc and f.inside_view_probs:
                    iv_display = " / ".join(f"{p:.0%}" for p in f.inside_view_probs)
                else:
                    iv_display = _fmt(f.inside_view, fmt) if f.inside_view is not None else "—"

                # For binary, show absolute shift in pp; for others, show relative %
                if is_pct:
                    shift_display = _fmt(f.shift, fmt_shift) if f.shift is not None else "—"
                    shift_style = f"color: {_shift_color(f.shift)}"
                else:
                    if f.shift_pct is not None:
                        shift_display = f"{f.shift_pct:+.1f}%"
                        # Color based on relative magnitude
                        abs_rel = abs(f.shift_pct)
                        color = (
                            "#666"
                            if abs_rel < 5
                            else "#b8860b"
                            if abs_rel < 15
                            else "#e67700"
                            if abs_rel < 30
                            else "#d63031"
                        )
                        shift_style = f"color: {color}"
                    else:
                        shift_display = "—"
                        shift_style = "color: #888"

                model_short = f.model.split("/")[-1] if "/" in f.model else f.model

                fc_rows.append(f"""
                    <tr>
                        <td class="agent">{f.agent_id.replace("forecaster_", "F")}</td>
                        <td class="model">{model_short}</td>
                        <td class="val ov">{ov_display}</td>
                        <td class="val iv">{iv_display}</td>
                        <td class="val shift" style="{shift_style}">{shift_display}</td>
                    </tr>
                """)

            # Summary row
            ov_vals = [f.outside_view for f in a.forecasters if f.outside_view is not None]
            iv_vals = [f.inside_view for f in a.forecasters if f.inside_view is not None]
            ov_avg_display = _fmt(statistics.mean(ov_vals), fmt) if ov_vals else "—"
            iv_avg_display = _fmt(statistics.mean(iv_vals), fmt) if iv_vals else "—"
            # Range and std dev are differences/spreads, not absolute values —
            # for dates, format as durations (days) rather than as timestamps
            fmt_spread = "date_delta" if is_date else fmt
            ov_range_display = (
                _fmt(a.outside_view_range, fmt_spread) if a.outside_view_range is not None else "—"
            )
            iv_range_display = (
                _fmt(a.inside_view_range, fmt_spread) if a.inside_view_range is not None else "—"
            )
            ov_std_display = (
                _fmt(a.outside_view_std, fmt_spread) if a.outside_view_std is not None else "—"
            )
            iv_std_display = (
                _fmt(a.inside_view_std, fmt_spread) if a.inside_view_std is not None else "—"
            )

            # Convergence/divergence indicator
            if a.outside_view_std and a.inside_view_std:
                if a.inside_view_std < a.outside_view_std * 0.8:
                    convergence_class = "converged"
                    convergence_label = "Converged"
                elif a.inside_view_std > a.outside_view_std * 1.2:
                    convergence_class = "diverged"
                    convergence_label = "Diverged"
                else:
                    convergence_class = "stable"
                    convergence_label = "Stable"
            else:
                convergence_class = ""
                convergence_label = "—"

            # Format final prediction display
            if (
                a.final_prediction is not None
                and isinstance(a.final_prediction, list)
                and a.options
            ):
                # MC: show option labels with probabilities
                parts = []
                for i, prob in enumerate(a.final_prediction):
                    label = a.options[i] if i < len(a.options) else f"Opt {i + 1}"
                    parts.append(f"{label}: {prob:.0%}")
                final_display = " &nbsp;|&nbsp; ".join(parts)
            elif a.final_prediction is not None and isinstance(a.final_prediction, list):
                final_display = ", ".join(f"{p:.0%}" for p in a.final_prediction)
            elif a.final_prediction is not None:
                final_display = _fmt(a.final_prediction, fmt)
            else:
                final_display = "—"

            # Build visual range bar for binary
            range_bar = ""
            if qtype == "binary":
                ov_vals = [f.outside_view for f in a.forecasters if f.outside_view is not None]
                iv_vals = [f.inside_view for f in a.forecasters if f.inside_view is not None]
                if ov_vals and iv_vals:
                    range_bar = _build_range_bar(ov_vals, iv_vals, a.final_prediction)

            # For MC, add option labels subtitle and skip misleading avg/range/std
            options_subtitle = ""
            if is_mc and a.options:
                options_subtitle = (
                    f'<div class="mc-options-label">Options: {" / ".join(a.options)}</div>'
                )

            if is_mc:
                # Compute per-option averages across forecasters
                ov_probs_lists = [
                    f.outside_view_probs for f in a.forecasters if f.outside_view_probs
                ]
                iv_probs_lists = [f.inside_view_probs for f in a.forecasters if f.inside_view_probs]
                # Only average if option counts are consistent
                if ov_probs_lists and len(set(len(p) for p in ov_probs_lists)) == 1:
                    n_opts = len(ov_probs_lists[0])
                    ov_avg_probs = [
                        statistics.mean(p[i] for p in ov_probs_lists) for i in range(n_opts)
                    ]
                    mc_ov_avg = " / ".join(f"{p:.0%}" for p in ov_avg_probs)
                else:
                    mc_ov_avg = "—"
                if iv_probs_lists and len(set(len(p) for p in iv_probs_lists)) == 1:
                    n_opts = len(iv_probs_lists[0])
                    iv_avg_probs = [
                        statistics.mean(p[i] for p in iv_probs_lists) for i in range(n_opts)
                    ]
                    mc_iv_avg = " / ".join(f"{p:.0%}" for p in iv_avg_probs)
                else:
                    mc_iv_avg = "—"

                tfoot_rows = f"""
                        <tr>
                            <td colspan="2" class="summary-label">Average</td>
                            <td class="val ov">{mc_ov_avg}</td>
                            <td class="val iv">{mc_iv_avg}</td>
                            <td></td>
                        </tr>
                        <tr class="final-row">
                            <td colspan="2" class="summary-label">Final</td>
                            <td colspan="3" class="val final">{final_display}</td>
                        </tr>
                """
            else:
                tfoot_rows = f"""
                        <tr>
                            <td colspan="2" class="summary-label">Average</td>
                            <td class="val ov">{ov_avg_display}</td>
                            <td class="val iv">{iv_avg_display}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td colspan="2" class="summary-label">Range</td>
                            <td class="val ov">{ov_range_display}</td>
                            <td class="val iv">{iv_range_display}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td colspan="2" class="summary-label">Std Dev</td>
                            <td class="val ov">{ov_std_display}</td>
                            <td class="val iv">{iv_std_display}</td>
                            <td></td>
                        </tr>
                        <tr class="final-row">
                            <td colspan="2" class="summary-label">Final</td>
                            <td colspan="3" class="val final">{final_display}</td>
                        </tr>
                """

            rows_html.append(f"""
            <div class="forecast-card">
                <div class="forecast-header">
                    <div class="forecast-title">
                        <a href="https://www.metaculus.com/questions/{a.question_id}" target="_blank">Q{a.question_id}</a>
                        — {a.question_title}
                    </div>
                    <div class="forecast-meta">
                        <span class="badge mode-{a.mode}">{a.mode}</span>
                        <span class="badge {convergence_class}">{convergence_label}</span>
                        <span class="timestamp">{a.timestamp}</span>
                    </div>
                </div>
                {options_subtitle}
                {range_bar}
                <table class="fc-table">
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Model</th>
                            <th class="ov">Outside View</th>
                            <th class="iv">Inside View</th>
                            <th class="shift">Shift</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(fc_rows)}
                    </tbody>
                    <tfoot>
                        {tfoot_rows}
                    </tfoot>
                </table>
            </div>
            """)

        sections.append(f"""
        <section class="type-section" id="type-{qtype}">
            <h2>{qtype.replace("_", " ").title()}</h2>
            {summary_html}
            <div class="forecast-list">
                {"".join(rows_html)}
            </div>
        </section>
        """)

    # Global stats
    total = len(analyses)
    with_both = sum(
        1 for a in analyses if a.outside_view_std is not None and a.inside_view_std is not None
    )

    # Compute binary-only shift stats (only type where shifts are on a comparable 0-1 scale)
    binary_shifts = []
    binary_abs_shifts = []
    for a in analyses:
        if a.question_type != "binary":
            continue
        for f in a.forecasters:
            if f.shift is not None:
                binary_shifts.append(f.shift)
                binary_abs_shifts.append(abs(f.shift))

    # Count total shifts across all types
    total_shifts = sum(1 for a in analyses for f in a.forecasters if f.shift is not None)

    # Compute per-type convergence rates
    convergence_counts = {"converged": 0, "diverged": 0, "stable": 0}
    for a in analyses:
        if a.outside_view_std and a.inside_view_std:
            if a.inside_view_std < a.outside_view_std * 0.8:
                convergence_counts["converged"] += 1
            elif a.inside_view_std > a.outside_view_std * 1.2:
                convergence_counts["diverged"] += 1
            else:
                convergence_counts["stable"] += 1

    nav_links = " | ".join(
        f'<a href="#type-{qt}">{qt.replace("_", " ").title()} ({len(by_type[qt])})</a>'
        for qt in ["binary", "numeric", "multiple_choice", "discrete", "date"]
        if qt in by_type
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ensemble Diversity Analysis</title>
<style>
    :root {{
        --bg: #0d1117;
        --surface: #161b22;
        --surface2: #1c2333;
        --border: #30363d;
        --text: #c9d1d9;
        --text-dim: #8b949e;
        --accent: #58a6ff;
        --green: #3fb950;
        --orange: #d29922;
        --red: #f85149;
        --purple: #bc8cff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.5;
        padding: 24px;
        max-width: 1200px;
        margin: 0 auto;
    }}
    h1 {{ color: #fff; margin-bottom: 8px; font-size: 1.5rem; }}
    h2 {{
        color: var(--accent);
        font-size: 1.25rem;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border);
    }}
    .subtitle {{ color: var(--text-dim); margin-bottom: 20px; font-size: 0.9rem; }}
    nav {{ margin-bottom: 24px; font-size: 0.9rem; }}
    nav a {{ color: var(--accent); text-decoration: none; }}
    nav a:hover {{ text-decoration: underline; }}

    .global-stats {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-bottom: 32px;
    }}
    .type-summary {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 10px;
        margin-bottom: 20px;
    }}
    .stat-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }}
    .stat-card.convergence {{ border-color: var(--green); }}
    .stat-card.divergence {{ border-color: var(--red); }}
    .stat-value {{ font-size: 1.3rem; font-weight: 600; color: #fff; }}
    .stat-label {{ font-size: 0.75rem; color: var(--text-dim); margin-top: 4px; }}
    .stat-sublabel {{ font-size: 0.65rem; color: var(--text-dim); opacity: 0.7; }}

    .type-section {{ margin-bottom: 48px; }}

    .forecast-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }}
    .forecast-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
        gap: 12px;
        flex-wrap: wrap;
    }}
    .forecast-title {{
        font-weight: 600;
        font-size: 0.9rem;
    }}
    .forecast-title a {{ color: var(--accent); text-decoration: none; }}
    .forecast-title a:hover {{ text-decoration: underline; }}
    .forecast-meta {{
        display: flex;
        gap: 6px;
        align-items: center;
        flex-shrink: 0;
    }}
    .timestamp {{ color: var(--text-dim); font-size: 0.75rem; font-family: monospace; }}
    .mc-options-label {{ color: var(--text-dim); font-size: 0.75rem; margin-bottom: 8px; font-family: monospace; }}

    .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
    }}
    .badge.mode-live {{ background: rgba(63, 185, 80, 0.15); color: var(--green); }}
    .badge.mode-test {{ background: rgba(139, 148, 158, 0.15); color: var(--text-dim); }}
    .badge.mode-preview {{ background: rgba(188, 140, 255, 0.15); color: var(--purple); }}
    .badge.converged {{ background: rgba(63, 185, 80, 0.15); color: var(--green); }}
    .badge.diverged {{ background: rgba(248, 81, 73, 0.15); color: var(--red); }}
    .badge.stable {{ background: rgba(210, 153, 34, 0.15); color: var(--orange); }}
    .badge.low {{ background: rgba(139, 148, 158, 0.15); color: var(--text-dim); }}
    .badge.med {{ background: rgba(210, 153, 34, 0.15); color: var(--orange); }}
    .badge.high {{ background: rgba(248, 81, 73, 0.15); color: var(--red); }}

    .range-bar {{
        position: relative;
        height: 32px;
        background: var(--surface2);
        border-radius: 4px;
        margin-bottom: 12px;
        overflow: hidden;
    }}
    .range-bar .ov-range {{
        position: absolute;
        height: 10px;
        top: 4px;
        background: rgba(88, 166, 255, 0.3);
        border-radius: 2px;
    }}
    .range-bar .iv-range {{
        position: absolute;
        height: 10px;
        top: 18px;
        background: rgba(63, 185, 80, 0.3);
        border-radius: 2px;
    }}
    .range-bar .dot {{
        position: absolute;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
    }}
    .range-bar .dot.ov {{ background: var(--accent); top: 9px; }}
    .range-bar .dot.iv {{ background: var(--green); top: 23px; }}
    .range-bar .dot.final {{ background: #fff; width: 3px; height: 100%; border-radius: 1px; top: 0; transform: translateX(-50%); }}
    .range-bar-labels {{
        display: flex;
        justify-content: space-between;
        font-size: 0.65rem;
        color: var(--text-dim);
        margin-top: -4px;
        margin-bottom: 8px;
    }}
    .range-bar-legend {{
        display: flex;
        gap: 12px;
        font-size: 0.65rem;
        color: var(--text-dim);
        margin-bottom: 8px;
    }}
    .range-bar-legend span::before {{
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 4px;
        vertical-align: middle;
    }}
    .range-bar-legend .ov-legend::before {{ background: var(--accent); }}
    .range-bar-legend .iv-legend::before {{ background: var(--green); }}
    .range-bar-legend .final-legend::before {{ background: #fff; width: 3px; border-radius: 1px; }}

    .fc-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }}
    .fc-table th {{
        text-align: left;
        padding: 6px 8px;
        color: var(--text-dim);
        font-weight: 500;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid var(--border);
    }}
    .fc-table td {{
        padding: 5px 8px;
        border-bottom: 1px solid rgba(48, 54, 61, 0.5);
    }}
    .fc-table .agent {{ font-weight: 600; width: 40px; }}
    .fc-table .model {{ color: var(--text-dim); font-size: 0.8rem; font-family: monospace; }}
    .fc-table th.ov,
    .fc-table th.iv,
    .fc-table th.shift {{ text-align: right; }}
    .fc-table .val {{ text-align: right; font-family: monospace; }}
    .fc-table .val.ov {{ color: var(--accent); }}
    .fc-table .val.iv {{ color: var(--green); }}
    .fc-table .val.shift {{ font-weight: 500; }}
    .fc-table .val.final {{ color: #fff; font-weight: 700; text-align: center; font-size: 1rem; }}
    .fc-table tfoot td {{
        border-top: 1px solid var(--border);
        font-size: 0.8rem;
    }}
    .fc-table .summary-label {{
        color: var(--text-dim);
        font-style: italic;
    }}
    .fc-table .final-row td {{
        border-top: 2px solid var(--border);
        padding-top: 8px;
    }}

    .filter-bar {{
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }}
    .filter-bar button {{
        background: var(--surface);
        border: 1px solid var(--border);
        color: var(--text);
        padding: 6px 14px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.85rem;
    }}
    .filter-bar button:hover {{ border-color: var(--accent); }}
    .filter-bar button.active {{ background: var(--accent); color: #000; border-color: var(--accent); }}
</style>
</head>
<body>

<h1>Ensemble Diversity Analysis</h1>
<p class="subtitle">
    {total} forecasts analyzed ({with_both} with full outside+inside view data)
    &bull; Generated from artifact data
</p>

<nav>{nav_links}</nav>

<div class="global-stats">
    <div class="stat-card">
        <div class="stat-value">{total}</div>
        <div class="stat-label">Total Forecasts</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{total_shifts}</div>
        <div class="stat-label">Forecaster-Level Shifts<br><span class="stat-sublabel">outside view → inside view pairs</span></div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{_fmt(statistics.mean(binary_abs_shifts), "pct") if binary_abs_shifts else "—"}</div>
        <div class="stat-label">Avg Prediction Move<br><span class="stat-sublabel">binary only, per forecaster</span></div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{_fmt(statistics.mean(binary_shifts), "pct_pts") if binary_shifts else "—"}</div>
        <div class="stat-label">Avg Shift Direction<br><span class="stat-sublabel">binary, + = inside view higher than outside view</span></div>
    </div>
    <div class="stat-card convergence">
        <div class="stat-value">{convergence_counts["converged"]}</div>
        <div class="stat-label">Converged<br><span class="stat-sublabel">inside view spread &lt; 80% of outside view spread</span></div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{convergence_counts["stable"]}</div>
        <div class="stat-label">Stable<br><span class="stat-sublabel">inside view spread ≈ outside view spread</span></div>
    </div>
    <div class="stat-card divergence">
        <div class="stat-value">{convergence_counts["diverged"]}</div>
        <div class="stat-label">Diverged<br><span class="stat-sublabel">inside view spread &gt; 120% of outside view spread</span></div>
    </div>
</div>

{"".join(sections)}

<script>
// Collapse/expand forecast cards on click
document.querySelectorAll('.forecast-header').forEach(header => {{
    header.style.cursor = 'pointer';
    header.addEventListener('click', () => {{
        const card = header.parentElement;
        const table = card.querySelector('.fc-table');
        const bar = card.querySelector('.range-bar');
        const barLabels = card.querySelector('.range-bar-labels');
        const barLegend = card.querySelector('.range-bar-legend');
        if (table) table.style.display = table.style.display === 'none' ? '' : 'none';
        if (bar) bar.style.display = bar.style.display === 'none' ? '' : 'none';
        if (barLabels) barLabels.style.display = barLabels.style.display === 'none' ? '' : 'none';
        if (barLegend) barLegend.style.display = barLegend.style.display === 'none' ? '' : 'none';
    }});
}});
</script>

</body>
</html>"""


def _build_range_bar(ov_vals: list[float], iv_vals: list[float], final: float | None) -> str:
    """Build a visual range bar for binary forecasts (0-1 scale)."""

    def pct(v):
        return max(0, min(100, v * 100))

    ov_min_pct = pct(min(ov_vals))
    ov_max_pct = pct(max(ov_vals))
    iv_min_pct = pct(min(iv_vals))
    iv_max_pct = pct(max(iv_vals))

    dots = ""
    for v in ov_vals:
        dots += f'<div class="dot ov" style="left: {pct(v)}%"></div>'
    for v in iv_vals:
        dots += f'<div class="dot iv" style="left: {pct(v)}%"></div>'
    if final is not None:
        dots += f'<div class="dot final" style="left: {pct(final)}%"></div>'

    return f"""
    <div class="range-bar-legend">
        <span class="ov-legend">Outside View</span>
        <span class="iv-legend">Inside View</span>
        <span class="final-legend">Aggregated</span>
    </div>
    <div class="range-bar">
        <div class="ov-range" style="left: {ov_min_pct}%; width: {ov_max_pct - ov_min_pct}%"></div>
        <div class="iv-range" style="left: {iv_min_pct}%; width: {iv_max_pct - iv_min_pct}%"></div>
        {dots}
    </div>
    <div class="range-bar-labels">
        <span>0%</span>
        <span>25%</span>
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
    </div>
    """


def main():
    parser = argparse.ArgumentParser(description="Ensemble Diversity Analysis Report")
    parser.add_argument(
        "--output",
        "-o",
        default="data/ensemble_diversity_report.html",
        help="Output HTML file path",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Scan all artifact directories
    analyses = []
    for entry in sorted(DATA_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if not re.match(r"^\d+_\d{8}_\d{6}$", entry.name):
            continue

        # Skip old-format artifacts (pre BaseForecaster refactor, pre Jan 27)
        # These don't have cross-pollination and use a different pipeline
        if not (entry / "ensemble").is_dir():
            continue

        result = analyze_forecast(entry)
        if result is None:
            continue

        # Exclude test forecasts
        if result.mode == "test":
            continue

        # Only include forecasts that have at least some forecaster data
        has_data = any(
            f.outside_view is not None or f.inside_view is not None for f in result.forecasters
        )
        if not has_data:
            continue

        analyses.append(result)

    if not analyses:
        print("No forecasts found with ensemble data.")
        return

    generate_html(analyses, Path(args.output))


if __name__ == "__main__":
    main()
