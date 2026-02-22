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
    outside_view_p20: float | None = None  # Numeric: P20 value
    outside_view_p80: float | None = None  # Numeric: P80 value
    inside_view_p20: float | None = None
    inside_view_p80: float | None = None
    outside_view_probs: list[float] | None = None  # MC only
    inside_view_probs: list[float] | None = None
    outside_view_text: str | None = None  # Raw markdown report text
    inside_view_text: str | None = None
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

    # From tracking data
    community_prediction: float | dict | None = None  # Binary: prob, Numeric: median, MC: dict
    community_p25: float | None = None  # Numeric only
    community_p75: float | None = None  # Numeric only
    resolved: bool = False
    resolution: str | float | None = None  # "Yes"/"No", numeric value, or option name
    score_data: dict | None = None  # 7-field score dict

    # Supervisor data (only present when supervisor triggered)
    supervisor_ran: bool = False
    supervisor_confidence: str | None = None  # "high"/"medium"/"low"
    supervisor_prediction: float | list | None = None  # Same shape as final_prediction
    supervisor_cost: float | None = None
    supervisor_divergence_metric: str | None = None  # e.g. "std_dev"
    supervisor_divergence_value: float | None = None
    supervisor_divergence_threshold: float | None = None
    supervisor_analysis_text: str | None = None  # Stage 1 markdown
    supervisor_reasoning_text: str | None = None  # Stage 2 markdown

    # Research context (formatted markdown from search artifacts)
    historical_research_text: str | None = None  # OV research: question URLs + historical search
    current_research_text: str | None = None  # IV research: current search

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


def _format_research_context(raw: str) -> str:
    """Convert XML-tagged research context into human-readable markdown."""
    if not raw or not raw.strip():
        return ""

    sections: list[str] = []

    # Extract <QuestionSource url="...">...</QuestionSource>
    for m in re.finditer(r'<QuestionSource\s+url="([^"]*)">(.*?)</QuestionSource>', raw, re.DOTALL):
        url, body = m.group(1), m.group(2).strip()
        sections.append(f"---\n### Question Source\n**URL:** [{url}]({url})\n\n{body}")

    # Extract <Summary source="...">...</Summary>
    for m in re.finditer(r'<Summary\s+source="([^"]*)">(.*?)</Summary>', raw, re.DOTALL):
        url, body = m.group(1), m.group(2).strip()
        sections.append(f"---\n### Search Result\n**Source:** [{url}]({url})\n\n{body}")

    # Extract <Asknews_articles>...</Asknews_articles>
    for m in re.finditer(r"<Asknews_articles>(.*?)</Asknews_articles>", raw, re.DOTALL):
        body = m.group(1).strip()
        sections.append(f"---\n### AskNews Articles\n\n{body}")

    # Extract <Agent_report>...</Agent_report>
    for m in re.finditer(r"<Agent_report>(.*?)</Agent_report>", raw, re.DOTALL):
        body = m.group(1).strip()
        sections.append(f"---\n### Agentic Research Report\n\n{body}")

    if not sections:
        # No recognized tags — return raw text as-is
        return raw.strip()

    return "\n\n".join(sections)


def _normalize_probability(val: float, has_percent: bool) -> float:
    """Convert extracted value to probability in [0, 1].

    When has_percent is True (the source text had a '%' sign), the value is
    always a percentage and we divide by 100.  When False, we fall back to a
    heuristic: values > 1 are assumed to be percentages.

    This fixes the edge case where "1%" was misinterpreted as 1.0 (100%)
    because the old ``val > 1`` check treated 1 as a decimal probability.
    """
    if has_percent:
        return val / 100
    return val / 100 if val > 1 else val


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
    # (regex requires %, so has_percent=True)
    m = re.search(
        r"(?:Outside|Inside)\s+View\s+Prediction[:\s]*\n?\s*"
        r"(?:(?:Yes|No)\s*[=:]\s*)?(\d+(?:\.\d+)?)\s*%",
        full_text,
    )
    if m:
        return _normalize_probability(float(m.group(1)), has_percent=True)

    # Pass 2: Look for "Probability: N%" at end of text (the canonical ending format)
    # (% is optional here, so capture it)
    m = re.search(r"[Pp]robability:\s*(\d+(?:\.\d+)?)\s*(%?)\s*$", full_text)
    if m:
        return _normalize_probability(float(m.group(1)), has_percent=bool(m.group(2)))

    # Pass 3: Search last 10 lines for tight patterns only
    for line in reversed(lines[-10:]):
        line = _strip_markdown(line.strip())

        # "Probability: 18%" or "Probability: 18" (colon required to avoid matching prose)
        # (% is optional, so capture it)
        m = re.search(r"[Pp]robability:\s*(\d+(?:\.\d+)?)\s*(%?)", line)
        if m:
            return _normalize_probability(float(m.group(1)), has_percent=bool(m.group(2)))

        # "Yes = 53%" or "Yes: 53%" (GPT-5.2 sometimes prefixes with Yes/No)
        # (regex requires %)
        m = re.search(r"(?:Yes|No)\s*[=:]\s*(\d+(?:\.\d+)?)\s*%", line)
        if m:
            return _normalize_probability(float(m.group(1)), has_percent=True)

        # Bare number as a prediction on its own line (e.g. "27%")
        # (regex requires %)
        m = re.match(r"^(\d+(?:\.\d+)?)\s*%$", line)
        if m:
            return _normalize_probability(float(m.group(1)), has_percent=True)

    # Pass 4: Loose pattern — "a 1.3% probability" but only on a short standalone line
    # (avoids matching prose like "96% probability of NO settlement")
    # (regex requires %)
    for line in reversed(lines[-10:]):
        line = _strip_markdown(line.strip())
        if len(line) < 60:  # short lines are more likely to be predictions
            m = re.match(r"^.*?(\d+(?:\.\d+)?)\s*%\s*probability\s*[.!]?\s*$", line)
            if m:
                return _normalize_probability(float(m.group(1)), has_percent=True)

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


def load_tracking_data(tracking_dir: Path) -> dict[int, dict]:
    """Load all tracking JSON files and build a question_id -> tracking entry lookup.

    When multiple files contain the same question_id, the entry with the more
    recent snapshot_timestamp wins.
    """
    lookup: dict[int, dict] = {}

    if not tracking_dir.is_dir():
        return lookup

    for path in tracking_dir.glob("*.json"):
        data = load_json(path)
        if not data or "forecasts" not in data:
            continue
        for entry in data["forecasts"]:
            qid = entry.get("question_id")
            if qid is None:
                continue
            # Keep the entry with the newer snapshot
            existing = lookup.get(qid)
            if existing is None:
                lookup[qid] = entry
            else:
                new_ts = entry.get("snapshot_timestamp", "")
                old_ts = existing.get("snapshot_timestamp", "")
                if new_ts > old_ts:
                    lookup[qid] = entry

    return lookup


def enrich_with_tracking(analyses: list[ForecastAnalysis], tracking: dict[int, dict]):
    """Populate community prediction and resolution fields from tracking data."""
    for a in analyses:
        entry = tracking.get(a.question_id)
        if entry is None:
            continue

        comp = entry.get("comparison") or {}
        ctype = comp.get("type", "")

        if ctype == "binary":
            a.community_prediction = comp.get("community_probability")
        elif ctype == "numeric":
            a.community_prediction = comp.get("community_median")
            a.community_p25 = comp.get("community_lower_quartile")
            a.community_p75 = comp.get("community_upper_quartile")
        elif ctype == "multiple_choice":
            a.community_prediction = comp.get("community_probabilities")

        a.resolved = bool(entry.get("resolved"))
        a.resolution = entry.get("resolution")
        a.score_data = entry.get("score_data")


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
        elif question_type in ("numeric", "discrete", "date"):
            # prediction.json percentiles are CDF probabilities (0-1), not actual values.
            # Use the average of agent medians instead; computed later after forecaster
            # extraction, so set to None here.
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

        # Store raw report text for modal display
        fv.outside_view_text = ov_text
        fv.inside_view_text = iv_text

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
                fv.outside_view_p20 = p.get(20, p.get("20"))
                fv.outside_view_p80 = p.get(80, p.get("80"))

            if fv.inside_view_percentiles:
                p = fv.inside_view_percentiles
                fv.inside_view = p.get(50, p.get("50"))
                if fv.inside_view is None:
                    p40 = p.get(40, p.get("40"))
                    p60 = p.get(60, p.get("60"))
                    if p40 is not None and p60 is not None:
                        fv.inside_view = (p40 + p60) / 2
                fv.inside_view_p20 = p.get(20, p.get("20"))
                fv.inside_view_p80 = p.get(80, p.get("80"))

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
    if (
        question_type in ("numeric", "discrete", "date")
        and analysis.final_prediction is None
        and iv_vals
    ):
        analysis.final_prediction = statistics.mean(iv_vals)

    # Load supervisor data (if supervisor ran)
    supervisor_result = load_json(edir / "supervisor_result.json")
    if supervisor_result:
        analysis.supervisor_ran = True

        # Handle two schema versions:
        # Old format (Q41856): supervisor_confidence, supervisor_prediction, supervisor_cost
        # New format (all others): confidence, prediction, cost
        analysis.supervisor_confidence = supervisor_result.get(
            "confidence", supervisor_result.get("supervisor_confidence")
        )

        raw_pred = supervisor_result.get(
            "prediction", supervisor_result.get("supervisor_prediction")
        )

        # Normalize prediction to match final_prediction format
        if question_type == "binary" and isinstance(raw_pred, (int, float)):
            analysis.supervisor_prediction = raw_pred / 100 if raw_pred > 1 else raw_pred
        elif question_type in ("numeric", "discrete", "date") and isinstance(raw_pred, dict):
            # Extract median from percentile dict for display
            p50 = raw_pred.get(50, raw_pred.get("50"))
            if p50 is None:
                p40 = raw_pred.get(40, raw_pred.get("40"))
                p60 = raw_pred.get(60, raw_pred.get("60"))
                if p40 is not None and p60 is not None:
                    p50 = (p40 + p60) / 2
            analysis.supervisor_prediction = p50
        elif question_type == "multiple_choice" and isinstance(raw_pred, list):
            if any(p > 1 for p in raw_pred):
                analysis.supervisor_prediction = [p / 100 for p in raw_pred]
            else:
                analysis.supervisor_prediction = raw_pred

        analysis.supervisor_cost = supervisor_result.get(
            "cost", supervisor_result.get("supervisor_cost")
        )

        div_info = supervisor_result.get("divergence", {})
        analysis.supervisor_divergence_metric = div_info.get("metric_name")
        analysis.supervisor_divergence_value = div_info.get("metric_value")
        analysis.supervisor_divergence_threshold = div_info.get("threshold")

        analysis.supervisor_analysis_text = read_text(edir / "supervisor_analysis.md")
        analysis.supervisor_reasoning_text = read_text(edir / "supervisor_reasoning.md")

    # Load research context (new format only: research/ directory)
    research_dir = forecast_dir / "research"
    if research_dir.is_dir():
        # Historical research (outside view context)
        hist_data = load_json(research_dir / "search_historical.json")
        hist_context = hist_data.get("context", "") if hist_data else ""

        # Question URL scraping results (also fed into outside view)
        url_data = load_json(research_dir / "search_question_urls.json")
        url_context = url_data.get("context", "") if url_data else ""

        combined = (url_context + "\n" + hist_context).strip() if url_context else hist_context
        if combined:
            analysis.historical_research_text = _format_research_context(combined)

        # Current research (inside view context)
        curr_data = load_json(research_dir / "search_current.json")
        if curr_data and curr_data.get("context"):
            analysis.current_research_text = _format_research_context(curr_data["context"])

    return analysis


def _compute_range_distribution(
    forecasts: list[ForecastAnalysis], qtype: str
) -> tuple[list[tuple[str, int, int]], list[tuple[str, int, int]]]:
    """Compute range distribution tables for outside and inside view.

    For binary: buckets are raw percentage-point ranges (0-9, 10-19, ..., 60+).
    For numeric/discrete/date: ranges are normalized as % of the P50 median value,
        so different scales are comparable. Buckets: 0-4%, 5-9%, 10-19%, 20-29%, 30+%.
    For multiple_choice: uses the max-probability summary stat (already 0-1 scale),
        converted to percentage-point buckets like binary.

    Returns (ov_distribution, iv_distribution) where each is a list of
    (bucket_label, count, total) tuples.
    """
    if qtype in ("binary", "multiple_choice"):
        # Use raw percentage-point ranges
        buckets = [
            ("0–9pp", 0, 0.09),
            ("10–19pp", 0.10, 0.19),
            ("20–29pp", 0.20, 0.29),
            ("30–39pp", 0.30, 0.39),
            ("40–49pp", 0.40, 0.49),
            ("50+pp", 0.50, float("inf")),
        ]

        ov_ranges = [f.outside_view_range for f in forecasts if f.outside_view_range is not None]
        iv_ranges = [f.inside_view_range for f in forecasts if f.inside_view_range is not None]

        def _bucket_counts(ranges, buckets):
            result = []
            total = len(ranges)
            for label, lo, hi in buckets:
                count = sum(1 for r in ranges if lo <= r <= hi)
                result.append((label, count, total))
            return result

        return _bucket_counts(ov_ranges, buckets), _bucket_counts(iv_ranges, buckets)

    else:
        # Numeric/discrete/date: normalize range as percentage of median (P50)
        buckets = [
            ("0–4%", 0, 4),
            ("5–9%", 5, 9),
            ("10–19%", 10, 19),
            ("20–29%", 20, 29),
            ("30+%", 30, float("inf")),
        ]

        def _get_relative_ranges(forecasts, view="outside"):
            """Compute range as % of median for each forecast."""
            relative = []
            for f in forecasts:
                vals = []
                for fc in f.forecasters:
                    v = fc.outside_view if view == "outside" else fc.inside_view
                    if v is not None:
                        vals.append(v)
                if len(vals) >= 2:
                    median = sorted(vals)[len(vals) // 2]
                    if abs(median) > 0:
                        rng = max(vals) - min(vals)
                        relative.append(rng / abs(median) * 100)
            return relative

        ov_rel = _get_relative_ranges(forecasts, "outside")
        iv_rel = _get_relative_ranges(forecasts, "inside")

        def _bucket_counts(ranges, buckets):
            result = []
            total = len(ranges)
            for label, lo, hi in buckets:
                count = sum(1 for r in ranges if lo <= r <= hi)
                result.append((label, count, total))
            return result

        return _bucket_counts(ov_rel, buckets), _bucket_counts(iv_rel, buckets)


def _build_range_distribution_html(
    ov_dist: list[tuple[str, int, int]],
    iv_dist: list[tuple[str, int, int]],
    qtype: str,
) -> str:
    """Build side-by-side range distribution tables HTML."""
    title_suffix = (
        "(percentage points)" if qtype in ("binary", "multiple_choice") else "(% of median)"
    )

    def _table(title, dist):
        rows = ""
        for label, count, total in dist:
            pct = f"{count / total * 100:.0f}%" if total > 0 else "—"
            # Bar width proportional to count
            bar_width = count / total * 100 if total > 0 else 0
            rows += (
                f"<tr>"
                f"<td>{label}</td>"
                f'<td style="text-align:right; font-family:monospace;">{count}</td>'
                f'<td style="text-align:right; font-family:monospace; color:var(--text-dim);">{pct}</td>'
                f'<td style="width:40%;"><div style="background:var(--accent); height:12px; '
                f'border-radius:2px; width:{bar_width}%; opacity:0.6;"></div></td>'
                f"</tr>"
            )
        return (
            f'<div class="range-dist-table">'
            f'<div class="range-dist-title">{title}</div>'
            f"<table>"
            f"<thead><tr>"
            f'<th style="text-align:left;">Range</th>'
            f'<th style="text-align:right;">Count</th>'
            f'<th style="text-align:right;">%</th>'
            f"<th></th>"
            f"</tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"</table></div>"
        )

    ov_table = _table(f"Outside View Spread {title_suffix}", ov_dist)
    iv_table = _table(f"Inside View Spread {title_suffix}", iv_dist)

    return f'<div class="range-dist-row">{ov_table}{iv_table}</div>'


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


def _build_resolved_section(resolved: list[ForecastAnalysis]) -> str:
    """Build the Resolved Questions section with scores."""

    # Compute summary stats
    peer_scores = [
        a.score_data["peer_score"] for a in resolved if a.score_data.get("peer_score") is not None
    ]
    baseline_scores = [
        a.score_data["baseline_score"]
        for a in resolved
        if a.score_data.get("baseline_score") is not None
    ]
    coverages = [
        a.score_data["coverage"] for a in resolved if a.score_data.get("coverage") is not None
    ]
    beat_community = sum(1 for s in peer_scores if s > 0)

    avg_peer = statistics.mean(peer_scores) if peer_scores else None
    avg_baseline = statistics.mean(baseline_scores) if baseline_scores else None
    avg_coverage = statistics.mean(coverages) if coverages else None

    summary = (
        f"""
    <div class="type-summary">
        <div class="stat-card">
            <div class="stat-value">{len(resolved)}</div>
            <div class="stat-label">Resolved</div>
        </div>
        <div class="stat-card {"score-positive" if avg_peer and avg_peer > 0 else "score-negative" if avg_peer and avg_peer < 0 else ""}">
            <div class="stat-value">{avg_peer:+.1f}</div>
            <div class="stat-label">Avg Peer Score<br><span class="stat-sublabel">positive = beat community</span></div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_baseline:.1f}</div>
            <div class="stat-label">Avg Baseline Score</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_coverage:.0%}</div>
            <div class="stat-label">Avg Coverage</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{beat_community}/{len(peer_scores)}</div>
            <div class="stat-label">Beat Community<br><span class="stat-sublabel">peer score &gt; 0</span></div>
        </div>
    </div>
    """
        if avg_peer is not None
        else ""
    )

    # Build per-question cards sorted by peer_score (best first)
    sorted_resolved = sorted(
        resolved,
        key=lambda a: a.score_data.get("peer_score", 0) if a.score_data else 0,
        reverse=True,
    )

    cards = []
    for a in sorted_resolved:
        sd = a.score_data or {}
        peer = sd.get("peer_score")
        score_class = (
            "score-positive" if peer and peer > 0 else "score-negative" if peer and peer < 0 else ""
        )

        # Format resolution value
        if a.resolution is not None:
            if a.question_type == "binary":
                res_display = str(a.resolution)
            elif a.question_type == "numeric":
                res_display = (
                    _fmt(a.resolution, "num")
                    if isinstance(a.resolution, (int, float))
                    else str(a.resolution)
                )
            else:
                res_display = str(a.resolution)
        else:
            res_display = "—"

        # Format prediction comparison
        if a.question_type == "binary":
            my_display = _fmt(a.final_prediction, "pct") if a.final_prediction is not None else "—"
            comm_display = (
                _fmt(a.community_prediction, "pct") if a.community_prediction is not None else "—"
            )
        elif a.question_type in ("numeric", "discrete", "date"):
            fmt = "date" if a.question_type == "date" else "num"
            my_display = _fmt(a.final_prediction, fmt) if a.final_prediction is not None else "—"
            comm_display = (
                _fmt(a.community_prediction, fmt) if a.community_prediction is not None else "—"
            )
        elif (
            a.question_type == "multiple_choice"
            and isinstance(a.final_prediction, list)
            and a.options
        ):
            parts = [
                f"{a.options[i]}: {p:.0%}"
                for i, p in enumerate(a.final_prediction)
                if i < len(a.options)
            ]
            my_display = " | ".join(parts)
            if isinstance(a.community_prediction, dict):
                comm_parts = [
                    f"{opt}: {a.community_prediction.get(opt, 0):.0%}" for opt in a.options
                ]
                comm_display = " | ".join(comm_parts)
            else:
                comm_display = "—"
        else:
            my_display = str(a.final_prediction) if a.final_prediction is not None else "—"
            comm_display = "—"

        # Score rows
        score_rows = ""
        score_fields = [
            ("Peer Score", "peer_score", True),
            ("Baseline Score", "baseline_score", False),
            ("Spot Peer Score", "spot_peer_score", True),
            ("Spot Baseline Score", "spot_baseline_score", False),
            ("Coverage", "coverage", False),
            ("Weighted Coverage", "weighted_coverage", False),
            ("Relative Legacy Score", "relative_legacy_score", True),
        ]
        for label, key, is_peer in score_fields:
            val = sd.get(key)
            if val is None:
                continue
            if key in ("coverage", "weighted_coverage"):
                val_display = f"{val:.1%}"
            else:
                val_display = f"{val:+.2f}" if is_peer else f"{val:.2f}"
            val_class = ""
            if is_peer:
                val_class = "score-positive" if val > 0 else "score-negative"
            score_rows += f"""
                <tr>
                    <td class="score-label">{label}</td>
                    <td class="score-value {val_class}">{val_display}</td>
                </tr>"""

        cards.append(f"""
        <div class="resolved-card {score_class}">
            <div class="resolved-header">
                <div class="forecast-title">
                    <a href="https://www.metaculus.com/questions/{a.question_id}" target="_blank">Q{a.question_id}</a>
                    — {a.question_title}
                </div>
                <div class="forecast-meta">
                    <span class="badge mode-{a.question_type}">{a.question_type.replace("_", " ")}</span>
                </div>
            </div>
            <div class="resolved-comparison">
                <div class="comparison-item">
                    <span class="comparison-label">Resolution</span>
                    <span class="comparison-value resolution-value">{res_display}</span>
                </div>
                <div class="comparison-item">
                    <span class="comparison-label">My Forecast</span>
                    <span class="comparison-value my-value">{my_display}</span>
                </div>
                <div class="comparison-item">
                    <span class="comparison-label">Community</span>
                    <span class="comparison-value community-value">{comm_display}</span>
                </div>
            </div>
            <table class="score-table">
                <tbody>{score_rows}</tbody>
            </table>
        </div>
        """)

    return f"""
    <section class="type-section" id="resolved">
        <h2>Resolved Questions</h2>
        {summary}
        <div class="forecast-list">
            {"".join(cards)}
        </div>
    </section>
    """


def _build_html(
    analyses: list[ForecastAnalysis],
    by_type: dict[str, list[ForecastAnalysis]],
    type_stats: dict,
) -> str:
    sections = []
    # Collect report texts for modal display — each entry is {title, text}
    report_entries: list[dict[str, str]] = []

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
            is_numeric_type = qtype in ("numeric", "discrete", "date")
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

                # For numeric types, format P20 and P80
                ov_p20_display = ""
                ov_p80_display = ""
                iv_p20_display = ""
                iv_p80_display = ""
                if is_numeric_type:
                    ov_p20_display = (
                        _fmt(f.outside_view_p20, fmt) if f.outside_view_p20 is not None else "—"
                    )
                    ov_p80_display = (
                        _fmt(f.outside_view_p80, fmt) if f.outside_view_p80 is not None else "—"
                    )
                    iv_p20_display = (
                        _fmt(f.inside_view_p20, fmt) if f.inside_view_p20 is not None else "—"
                    )
                    iv_p80_display = (
                        _fmt(f.inside_view_p80, fmt) if f.inside_view_p80 is not None else "—"
                    )

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
                f_label = f.agent_id.replace("forecaster_", "F")

                # Build clickable OV/IV cells linking to report modals
                ov_onclick = ""
                if f.outside_view_text:
                    ov_idx = len(report_entries)
                    report_entries.append(
                        {
                            "title": f"{f_label} ({model_short}) — Outside View",
                            "text": f.outside_view_text,
                        }
                    )
                    ov_onclick = f' onclick="openReport({ov_idx})"'

                iv_onclick = ""
                if f.inside_view_text:
                    iv_idx = len(report_entries)
                    report_entries.append(
                        {
                            "title": f"{f_label} ({model_short}) — Inside View",
                            "text": f.inside_view_text,
                        }
                    )
                    iv_onclick = f' onclick="openReport({iv_idx})"'

                ov_cls = "val ov" + (" report-link" if ov_onclick else "")
                iv_cls = "val iv" + (" report-link" if iv_onclick else "")

                if is_numeric_type:
                    fc_rows.append(f"""
                    <tr>
                        <td class="agent">{f_label}</td>
                        <td class="model">{model_short}</td>
                        <td class="val ov p20">{ov_p20_display}</td>
                        <td class="{ov_cls}"{ov_onclick}>{ov_display}</td>
                        <td class="val ov p80">{ov_p80_display}</td>
                        <td class="val iv p20">{iv_p20_display}</td>
                        <td class="{iv_cls}"{iv_onclick}>{iv_display}</td>
                        <td class="val iv p80">{iv_p80_display}</td>
                        <td class="val shift" style="{shift_style}">{shift_display}</td>
                    </tr>
                    """)
                else:
                    fc_rows.append(f"""
                    <tr>
                        <td class="agent">{f_label}</td>
                        <td class="model">{model_short}</td>
                        <td class="{ov_cls}"{ov_onclick}>{ov_display}</td>
                        <td class="{iv_cls}"{iv_onclick}>{iv_display}</td>
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

            # Final label: "Ensemble" when supervisor ran, "Final" otherwise
            final_label = "Ensemble" if a.supervisor_ran else "Final"

            # Format final prediction display
            if a.final_prediction is not None and isinstance(a.final_prediction, list):
                final_display = " / ".join(f"{p:.0%}" for p in a.final_prediction)
            elif a.final_prediction is not None:
                final_display = _fmt(a.final_prediction, fmt)
            else:
                final_display = "—"

            # Build visual range bar
            range_bar = ""
            if qtype == "binary":
                ov_vals = [f.outside_view for f in a.forecasters if f.outside_view is not None]
                iv_vals = [f.inside_view for f in a.forecasters if f.inside_view is not None]
                if ov_vals and iv_vals:
                    sup_val = a.supervisor_prediction if a.supervisor_ran else None
                    range_bar = _build_range_bar(ov_vals, iv_vals, a.final_prediction, sup_val)
            elif is_numeric_type:
                ov_vals = [f.outside_view for f in a.forecasters if f.outside_view is not None]
                iv_vals = [f.inside_view for f in a.forecasters if f.inside_view is not None]
                if ov_vals and iv_vals:
                    sup_val = a.supervisor_prediction if a.supervisor_ran else None
                    res_val = None
                    if a.resolution is not None:
                        try:
                            res_val = float(a.resolution)
                        except (ValueError, TypeError):
                            pass
                    range_bar = _build_numeric_range_bar(
                        ov_vals,
                        iv_vals,
                        a.final_prediction,
                        fmt,
                        resolution=res_val,
                        supervisor=sup_val,
                    )

            # For MC, add option labels subtitle and skip misleading avg/range/std
            options_subtitle = ""
            if is_mc and a.options:
                options_subtitle = (
                    f'<div class="mc-options-label">Options: {" / ".join(a.options)}</div>'
                )

            # Build community prediction row (if tracking data available)
            community_row = ""
            if a.community_prediction is not None:
                if is_mc and isinstance(a.community_prediction, dict):
                    # MC: show per-option community probabilities
                    if a.options:
                        comm_probs = [a.community_prediction.get(opt, 0) for opt in a.options]
                    else:
                        comm_probs = list(a.community_prediction.values())
                    comm_display = " / ".join(f"{p:.0%}" for p in comm_probs)
                    community_row = f"""
                        <tr class="community-row">
                            <td colspan="2" class="summary-label community-label">Community</td>
                            <td class="val community"></td>
                            <td class="val community">{comm_display}</td>
                            <td></td>
                        </tr>"""
                elif is_numeric_type:
                    comm_median = _fmt(a.community_prediction, fmt)
                    comm_p25 = _fmt(a.community_p25, fmt) if a.community_p25 is not None else "—"
                    comm_p75 = _fmt(a.community_p75, fmt) if a.community_p75 is not None else "—"
                    community_row = f"""
                        <tr class="community-row">
                            <td colspan="2" class="summary-label community-label">Community</td>
                            <td class="val community p20"></td>
                            <td class="val community"></td>
                            <td class="val community p80"></td>
                            <td class="val community p20">{comm_p25}</td>
                            <td class="val community">{comm_median}</td>
                            <td class="val community p80">{comm_p75}</td>
                            <td></td>
                        </tr>"""
                else:
                    # Binary / default
                    comm_display = _fmt(a.community_prediction, fmt)
                    community_row = f"""
                        <tr class="community-row">
                            <td colspan="2" class="summary-label community-label">Community</td>
                            <td class="val community"></td>
                            <td class="val community">{comm_display}</td>
                            <td></td>
                        </tr>"""

            # Build resolution row (if resolved)
            resolution_row = ""
            if a.resolved and a.resolution is not None:
                if is_mc and a.options:
                    # MC: show checkmark for winning option, x for others
                    marks = []
                    for opt in a.options:
                        if opt == a.resolution:
                            marks.append("\u2713")
                        else:
                            marks.append("\u2717")
                    res_display = " / ".join(marks)
                elif a.question_type == "binary":
                    res_display = str(a.resolution)
                elif is_numeric_type:
                    res_val = a.resolution
                    # Resolution may be stored as a numeric string
                    if isinstance(res_val, str):
                        try:
                            res_val = float(res_val)
                        except ValueError:
                            pass
                    res_display = (
                        _fmt(res_val, fmt)
                        if isinstance(res_val, (int, float))
                        else str(a.resolution)
                    )
                else:
                    res_display = str(a.resolution)

                if is_numeric_type:
                    resolution_row = f"""
                        <tr class="resolution-row">
                            <td colspan="2" class="summary-label resolution-label">Resolution</td>
                            <td class="val resolution p20"></td>
                            <td class="val resolution"></td>
                            <td class="val resolution p80"></td>
                            <td class="val resolution p20"></td>
                            <td class="val resolution">{res_display}</td>
                            <td class="val resolution p80"></td>
                            <td></td>
                        </tr>"""
                else:
                    resolution_row = f"""
                        <tr class="resolution-row">
                            <td colspan="2" class="summary-label resolution-label">Resolution</td>
                            <td class="val resolution"></td>
                            <td class="val resolution">{res_display}</td>
                            <td></td>
                        </tr>"""

            # Build peer score row (if score data available)
            peer_score_row = ""
            if a.score_data and a.score_data.get("peer_score") is not None:
                peer_val = a.score_data["peer_score"]
                peer_display = f"{peer_val:+.2f}"
                peer_class = "score-positive" if peer_val > 0 else "score-negative"
                if is_numeric_type:
                    peer_score_row = f"""
                        <tr class="peer-score-row">
                            <td colspan="2" class="summary-label peer-score-label">Peer Score</td>
                            <td class="val p20"></td>
                            <td class="val"></td>
                            <td class="val p80"></td>
                            <td class="val p20"></td>
                            <td class="val {peer_class}">{peer_display}</td>
                            <td class="val p80"></td>
                            <td></td>
                        </tr>"""
                else:
                    peer_score_row = f"""
                        <tr class="peer-score-row">
                            <td colspan="2" class="summary-label peer-score-label">Peer Score</td>
                            <td class="val"></td>
                            <td class="val {peer_class}">{peer_display}</td>
                            <td></td>
                        </tr>"""

            # Build supervisor row (if supervisor ran)
            supervisor_row = ""
            if a.supervisor_ran and a.supervisor_prediction is not None:
                # Format supervisor prediction display
                if isinstance(a.supervisor_prediction, list):
                    sup_display = " / ".join(f"{p:.0%}" for p in a.supervisor_prediction)
                else:
                    sup_display = _fmt(a.supervisor_prediction, fmt)

                # Confidence badge
                conf_lower = (a.supervisor_confidence or "medium").lower()
                conf_badge = (
                    f'<span class="sup-conf-badge sup-conf-{conf_lower}">'
                    f"{(a.supervisor_confidence or '?').upper()}</span>"
                )

                # Divergence trigger subtitle
                div_trigger = ""
                if a.supervisor_divergence_metric:
                    metric_label = {
                        "std_dev": "StdDev",
                        "cv": "CV",
                        "rn_spread": "RN Spread",
                        "max_option_range": "Max Option Range",
                    }.get(a.supervisor_divergence_metric, a.supervisor_divergence_metric)
                    # Use .3f for small values (rn_spread, cv), .1f for large (std_dev, max_option_range)
                    val_fmt = (
                        f"{a.supervisor_divergence_value:.3f}"
                        if a.supervisor_divergence_value < 1
                        else f"{a.supervisor_divergence_value:.1f}"
                    )
                    thr_fmt = (
                        f"{a.supervisor_divergence_threshold:.3f}"
                        if a.supervisor_divergence_threshold < 1
                        else f"{a.supervisor_divergence_threshold:.1f}"
                    )
                    div_trigger = (
                        f'<div class="supervisor-trigger">'
                        f"{metric_label}: {val_fmt} "
                        f"(threshold: {thr_fmt})"
                        f"</div>"
                    )

                # Build clickable cell linking to supervisor modal
                sup_onclick = ""
                combined_text = ""
                if a.supervisor_analysis_text:
                    combined_text += "# Disagreement Analysis\n\n" + a.supervisor_analysis_text
                if a.supervisor_reasoning_text:
                    combined_text += (
                        "\n\n---\n\n# Updated Forecast\n\n" + a.supervisor_reasoning_text
                    )

                if combined_text:
                    sup_idx = len(report_entries)
                    report_entries.append(
                        {
                            "title": f"Supervisor — Q{a.question_id}",
                            "text": combined_text,
                        }
                    )
                    sup_onclick = f' onclick="openReport({sup_idx})"'

                sup_cls = "val iv supervisor-val" + (" report-link" if sup_onclick else "")

                if is_numeric_type:
                    supervisor_row = f"""
                        <tr class="supervisor-row">
                            <td colspan="2" class="summary-label supervisor-label">Supervisor {conf_badge}{div_trigger}</td>
                            <td class="val ov p20"></td>
                            <td class="val ov"></td>
                            <td class="val ov p80"></td>
                            <td class="val iv p20"></td>
                            <td class="{sup_cls}"{sup_onclick}>{sup_display}</td>
                            <td class="val iv p80"></td>
                            <td></td>
                        </tr>"""
                else:
                    supervisor_row = f"""
                        <tr class="supervisor-row">
                            <td colspan="2" class="summary-label supervisor-label">Supervisor {conf_badge}{div_trigger}</td>
                            <td class="val ov"></td>
                            <td class="{sup_cls}"{sup_onclick}>{sup_display}</td>
                            <td></td>
                        </tr>"""

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
                            <td colspan="2" class="summary-label">{final_label}</td>
                            <td class="val ov"></td>
                            <td class="val iv final">{final_display}</td>
                            <td></td>
                        </tr>
                        {supervisor_row}
                        {community_row}
                        {resolution_row}
                        {peer_score_row}
                """
            elif is_numeric_type:
                # Numeric/discrete/date: wider table with P20/P80 columns
                # Compute average P20 and P80 across forecasters
                ov_p20_vals = [
                    f.outside_view_p20 for f in a.forecasters if f.outside_view_p20 is not None
                ]
                ov_p80_vals = [
                    f.outside_view_p80 for f in a.forecasters if f.outside_view_p80 is not None
                ]
                iv_p20_vals = [
                    f.inside_view_p20 for f in a.forecasters if f.inside_view_p20 is not None
                ]
                iv_p80_vals = [
                    f.inside_view_p80 for f in a.forecasters if f.inside_view_p80 is not None
                ]
                ov_p20_avg = _fmt(statistics.mean(ov_p20_vals), fmt) if ov_p20_vals else "—"
                ov_p80_avg = _fmt(statistics.mean(ov_p80_vals), fmt) if ov_p80_vals else "—"
                iv_p20_avg = _fmt(statistics.mean(iv_p20_vals), fmt) if iv_p20_vals else "—"
                iv_p80_avg = _fmt(statistics.mean(iv_p80_vals), fmt) if iv_p80_vals else "—"

                tfoot_rows = f"""
                        <tr>
                            <td colspan="2" class="summary-label">Average</td>
                            <td class="val ov p20">{ov_p20_avg}</td>
                            <td class="val ov">{ov_avg_display}</td>
                            <td class="val ov p80">{ov_p80_avg}</td>
                            <td class="val iv p20">{iv_p20_avg}</td>
                            <td class="val iv">{iv_avg_display}</td>
                            <td class="val iv p80">{iv_p80_avg}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td colspan="2" class="summary-label">Range</td>
                            <td class="val ov p20"></td>
                            <td class="val ov">{ov_range_display}</td>
                            <td class="val ov p80"></td>
                            <td class="val iv p20"></td>
                            <td class="val iv">{iv_range_display}</td>
                            <td class="val iv p80"></td>
                            <td></td>
                        </tr>
                        <tr>
                            <td colspan="2" class="summary-label">Std Dev</td>
                            <td class="val ov p20"></td>
                            <td class="val ov">{ov_std_display}</td>
                            <td class="val ov p80"></td>
                            <td class="val iv p20"></td>
                            <td class="val iv">{iv_std_display}</td>
                            <td class="val iv p80"></td>
                            <td></td>
                        </tr>
                        <tr class="final-row">
                            <td colspan="2" class="summary-label">{final_label}</td>
                            <td class="val ov p20"></td>
                            <td class="val ov"></td>
                            <td class="val ov p80"></td>
                            <td class="val iv p20"></td>
                            <td class="val iv final">{final_display}</td>
                            <td class="val iv p80"></td>
                            <td></td>
                        </tr>
                        {supervisor_row}
                        {community_row}
                        {resolution_row}
                        {peer_score_row}
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
                            <td colspan="2" class="summary-label">{final_label}</td>
                            <td class="val ov"></td>
                            <td class="val iv final">{final_display}</td>
                            <td></td>
                        </tr>
                        {supervisor_row}
                        {community_row}
                        {resolution_row}
                        {peer_score_row}
                """

            # Build clickable research headers (OV → historical, IV → current)
            ov_header_onclick = ""
            if a.historical_research_text:
                ov_research_idx = len(report_entries)
                report_entries.append(
                    {
                        "title": f"Q{a.question_id} — Historical Research (Outside View)",
                        "text": a.historical_research_text,
                    }
                )
                ov_header_onclick = f' onclick="openReport({ov_research_idx})"'

            iv_header_onclick = ""
            if a.current_research_text:
                iv_research_idx = len(report_entries)
                report_entries.append(
                    {
                        "title": f"Q{a.question_id} — Current Research (Inside View)",
                        "text": a.current_research_text,
                    }
                )
                iv_header_onclick = f' onclick="openReport({iv_research_idx})"'

            ov_header_cls = ' class="ov report-link"' if ov_header_onclick else ' class="ov"'
            iv_header_cls = ' class="iv report-link"' if iv_header_onclick else ' class="iv"'

            # Build table header based on question type
            if is_numeric_type:
                thead_html = f"""
                    <thead>
                        <tr>
                            <th rowspan="2">Agent</th>
                            <th rowspan="2">Model</th>
                            <th colspan="3"{ov_header_cls} style="text-align:center; border-bottom:1px solid var(--border);"{ov_header_onclick}>Outside View</th>
                            <th colspan="3"{iv_header_cls} style="text-align:center; border-bottom:1px solid var(--border);"{iv_header_onclick}>Inside View</th>
                            <th rowspan="2" class="shift">Shift</th>
                        </tr>
                        <tr>
                            <th class="ov" style="font-size:0.65rem;">P20</th>
                            <th class="ov" style="font-size:0.65rem;">Median</th>
                            <th class="ov" style="font-size:0.65rem;">P80</th>
                            <th class="iv" style="font-size:0.65rem;">P20</th>
                            <th class="iv" style="font-size:0.65rem;">Median</th>
                            <th class="iv" style="font-size:0.65rem;">P80</th>
                        </tr>
                    </thead>"""
            else:
                thead_html = f"""
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Model</th>
                            <th{ov_header_cls}{ov_header_onclick}>Outside View</th>
                            <th{iv_header_cls}{iv_header_onclick}>Inside View</th>
                            <th class="shift">Shift</th>
                        </tr>
                    </thead>"""

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
                    {thead_html}
                    <tbody>
                        {"".join(fc_rows)}
                    </tbody>
                    <tfoot>
                        {tfoot_rows}
                    </tfoot>
                </table>
            </div>
            """)

        # Compute range distribution tables
        ov_dist, iv_dist = _compute_range_distribution(forecasts, qtype)
        dist_html = _build_range_distribution_html(ov_dist, iv_dist, qtype)

        sections.append(f"""
        <section class="type-section" id="type-{qtype}">
            <h2>{qtype.replace("_", " ").title()}</h2>
            {summary_html}
            {dist_html}
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

    # Count supervisor triggers
    supervisor_count = sum(1 for a in analyses if a.supervisor_ran)

    # Build resolved questions section
    resolved_analyses = [a for a in analyses if a.resolved and a.score_data]
    resolved_section = ""
    if resolved_analyses:
        resolved_section = _build_resolved_section(resolved_analyses)

    nav_links = " | ".join(
        f'<a href="#type-{qt}">{qt.replace("_", " ").title()} ({len(by_type[qt])})</a>'
        for qt in ["binary", "numeric", "multiple_choice", "discrete", "date"]
        if qt in by_type
    )
    if resolved_analyses:
        nav_links += f' | <a href="#resolved">Resolved ({len(resolved_analyses)})</a>'

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
    .fc-table .val.p20, .fc-table .val.p80 {{ opacity: 0.6; font-size: 0.8rem; }}
    .fc-table .val.shift {{ font-weight: 500; }}
    .fc-table .val.final {{ color: #fff; font-weight: 700; text-align: right; font-size: 1rem; }}
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

    .range-dist-row {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 20px;
    }}
    .range-dist-table {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
    }}
    .range-dist-title {{
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-dim);
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    .range-dist-table table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
    }}
    .range-dist-table th {{
        padding: 4px 6px;
        color: var(--text-dim);
        font-weight: 500;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        border-bottom: 1px solid var(--border);
    }}
    .range-dist-table td {{
        padding: 3px 6px;
        border-bottom: 1px solid rgba(48, 54, 61, 0.3);
    }}

    /* Community prediction row */
    .fc-table .val.community {{ color: var(--purple); }}
    .fc-table .community-label {{ color: var(--purple); }}
    .community-row td {{ border-top: 1px solid var(--border); }}

    /* Resolution row */
    .fc-table .val.resolution {{ color: #fff; font-weight: 600; }}
    .fc-table .resolution-label {{ color: var(--text-dim); }}

    /* Peer score row */
    .fc-table .peer-score-label {{ color: var(--text-dim); }}
    .fc-table .val.score-positive {{ color: var(--green); font-weight: 600; }}
    .fc-table .val.score-negative {{ color: var(--red); font-weight: 600; }}

    /* Supervisor row in forecast table */
    .supervisor-row td {{
        border-top: 2px solid var(--orange);
    }}
    .fc-table .supervisor-label {{
        color: var(--orange);
        font-weight: 600;
        font-style: normal;
    }}
    .fc-table .val.supervisor-val {{
        color: var(--orange);
        font-weight: 700;
        font-size: 1rem;
    }}
    .sup-conf-badge {{
        display: inline-block;
        padding: 1px 6px;
        border-radius: 8px;
        font-size: 0.6rem;
        font-weight: 700;
        margin-left: 6px;
        vertical-align: middle;
        letter-spacing: 0.5px;
    }}
    .sup-conf-high {{
        background: rgba(63, 185, 80, 0.2);
        color: var(--green);
    }}
    .sup-conf-medium {{
        background: rgba(210, 153, 34, 0.2);
        color: var(--orange);
    }}
    .sup-conf-low {{
        background: rgba(248, 81, 73, 0.2);
        color: var(--red);
    }}
    .supervisor-trigger {{
        font-size: 0.7rem;
        color: var(--text-dim);
        font-family: monospace;
        margin-top: 2px;
    }}

    /* Supervisor dot on range bar */
    .range-bar .dot.supervisor {{
        background: var(--orange);
        width: 3px;
        height: 100%;
        border-radius: 1px;
        top: 0;
        transform: translateX(-50%);
    }}
    .range-bar-legend .sup-legend::before {{
        content: '';
        display: inline-block;
        width: 3px;
        height: 10px;
        background: var(--orange);
        border-radius: 1px;
        margin-right: 4px;
        vertical-align: middle;
    }}

    /* Supervisor stat card */
    .stat-card.supervisor-stat {{ border-color: var(--orange); }}

    /* Resolution dot on range bar */
    .range-bar .dot.resolution {{
        background: var(--red);
        width: 3px;
        height: 100%;
        border-radius: 1px;
        top: 0;
        transform: translateX(-50%);
    }}
    .range-bar-legend .res-legend::before {{
        content: '';
        display: inline-block;
        width: 3px;
        height: 10px;
        background: var(--red);
        border-radius: 1px;
        margin-right: 4px;
        vertical-align: middle;
    }}

    /* Resolved questions section */
    .resolved-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }}
    .resolved-card.score-positive {{ border-left: 3px solid var(--green); }}
    .resolved-card.score-negative {{ border-left: 3px solid var(--red); }}
    .resolved-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
        gap: 12px;
        flex-wrap: wrap;
    }}
    .resolved-comparison {{
        display: flex;
        gap: 24px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }}
    .comparison-item {{
        display: flex;
        flex-direction: column;
        gap: 2px;
    }}
    .comparison-label {{
        font-size: 0.7rem;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .comparison-value {{
        font-family: monospace;
        font-size: 0.95rem;
        font-weight: 600;
    }}
    .resolution-value {{ color: #fff; }}
    .my-value {{ color: var(--accent); }}
    .community-value {{ color: var(--purple); }}
    .score-table {{
        width: auto;
        border-collapse: collapse;
        font-size: 0.8rem;
    }}
    .score-table td {{
        padding: 3px 12px 3px 0;
    }}
    .score-label {{
        color: var(--text-dim);
    }}
    .score-value {{
        font-family: monospace;
        text-align: right;
    }}
    .score-value.score-positive {{ color: var(--green); }}
    .score-value.score-negative {{ color: var(--red); }}
    .stat-card.score-positive {{ border-color: var(--green); }}
    .stat-card.score-negative {{ border-color: var(--red); }}
    .badge.mode-binary {{ background: rgba(88, 166, 255, 0.15); color: var(--accent); }}
    .badge.mode-numeric {{ background: rgba(63, 185, 80, 0.15); color: var(--green); }}
    .badge.mode-multiple_choice {{ background: rgba(210, 153, 34, 0.15); color: var(--orange); }}
    .badge.mode-discrete {{ background: rgba(188, 140, 255, 0.15); color: var(--purple); }}
    .badge.mode-date {{ background: rgba(139, 148, 158, 0.15); color: var(--text-dim); }}

    /* Clickable report links */
    .report-link {{
        cursor: pointer;
        text-decoration: underline;
        text-decoration-style: dotted;
        text-underline-offset: 3px;
    }}
    .report-link:hover {{
        text-decoration-style: solid;
        filter: brightness(1.3);
    }}

    /* Report modal */
    .report-modal-backdrop {{
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 1000;
        backdrop-filter: blur(4px);
    }}
    .report-modal-backdrop.open {{ display: flex; align-items: center; justify-content: center; }}
    .report-modal {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        width: min(90vw, 800px);
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }}
    .report-modal-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid var(--border);
        flex-shrink: 0;
    }}
    .report-modal-header h3 {{
        font-size: 1rem;
        color: #fff;
        margin: 0;
    }}
    .report-modal-close {{
        background: none;
        border: none;
        color: var(--text-dim);
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0 4px;
        line-height: 1;
    }}
    .report-modal-close:hover {{ color: #fff; }}
    .report-modal-body {{
        overflow-y: auto;
        padding: 20px;
        font-size: 0.9rem;
        line-height: 1.7;
    }}
    .report-modal-body h1, .report-modal-body h2, .report-modal-body h3,
    .report-modal-body h4, .report-modal-body h5 {{
        color: #fff;
        margin-top: 1.2em;
        margin-bottom: 0.4em;
    }}
    .report-modal-body h1 {{ font-size: 1.3rem; }}
    .report-modal-body h2 {{ font-size: 1.15rem; border-bottom: none; padding-bottom: 0; }}
    .report-modal-body h3 {{ font-size: 1.05rem; }}
    .report-modal-body p {{ margin-bottom: 0.8em; }}
    .report-modal-body ul, .report-modal-body ol {{ margin-bottom: 0.8em; padding-left: 1.5em; }}
    .report-modal-body li {{ margin-bottom: 0.3em; }}
    .report-modal-body code {{
        background: var(--surface2);
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 0.85em;
    }}
    .report-modal-body pre {{
        background: var(--surface2);
        padding: 12px;
        border-radius: 6px;
        overflow-x: auto;
        margin-bottom: 0.8em;
    }}
    .report-modal-body pre code {{ background: none; padding: 0; }}
    .report-modal-body blockquote {{
        border-left: 3px solid var(--border);
        margin-left: 0;
        padding-left: 12px;
        color: var(--text-dim);
    }}
    .report-modal-body strong {{ color: #fff; }}
    .report-modal-body a {{ color: #5bb8f5; text-decoration: underline; }}
    .report-modal-body a:visited {{ color: #a78bfa; }}
    .report-modal-body a:hover {{ color: #93d5ff; }}
    .report-modal-body hr {{
        border: none;
        border-top: 1px solid var(--border);
        margin: 1em 0;
    }}
    .report-modal-body table {{
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 1em;
    }}
    .report-modal-body th, .report-modal-body td {{
        border: 1px solid var(--border);
        padding: 6px 10px;
        text-align: left;
    }}
    .report-modal-body th {{ background: var(--surface2); color: #fff; }}
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
    <div class="stat-card supervisor-stat">
        <div class="stat-value">{supervisor_count}</div>
        <div class="stat-label">Supervisor<br><span class="stat-sublabel">high divergence triggered supervisor review</span></div>
    </div>
</div>

{"".join(sections)}

{resolved_section}

<!-- Report modal -->
<div class="report-modal-backdrop" id="reportBackdrop">
    <div class="report-modal">
        <div class="report-modal-header">
            <h3 id="reportTitle"></h3>
            <button class="report-modal-close" onclick="closeReport()">&times;</button>
        </div>
        <div class="report-modal-body" id="reportBody"></div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
// Report data for modal display
const REPORTS = {json.dumps(report_entries)};

// Markdown rendering (with fallback to plain text if marked.js fails to load)
function renderMarkdown(text) {{
    if (typeof marked !== 'undefined') {{
        return marked.parse(text);
    }}
    // Fallback: basic escaping and newline handling
    return '<pre style="white-space: pre-wrap;">' +
        text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') +
        '</pre>';
}}

function openReport(idx) {{
    const entry = REPORTS[idx];
    if (!entry) return;
    document.getElementById('reportTitle').textContent = entry.title;
    document.getElementById('reportBody').innerHTML = renderMarkdown(entry.text);
    document.getElementById('reportBackdrop').classList.add('open');
    document.body.style.overflow = 'hidden';
}}

function closeReport() {{
    document.getElementById('reportBackdrop').classList.remove('open');
    document.body.style.overflow = '';
}}

// Close on backdrop click
document.getElementById('reportBackdrop').addEventListener('click', function(e) {{
    if (e.target === this) closeReport();
}});

// Close on Escape key
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeReport();
}});

</script>

</body>
</html>"""


def _build_range_bar(
    ov_vals: list[float],
    iv_vals: list[float],
    final: float | None,
    supervisor: float | None = None,
) -> str:
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
    if supervisor is not None:
        dots += f'<div class="dot supervisor" style="left: {pct(supervisor)}%"></div>'

    sup_legend = ""
    if supervisor is not None:
        sup_legend = '<span class="sup-legend">Supervisor</span>'

    return f"""
    <div class="range-bar-legend">
        <span class="ov-legend">Outside View</span>
        <span class="iv-legend">Inside View</span>
        <span class="final-legend">Aggregated</span>
        {sup_legend}
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


def _build_numeric_range_bar(
    ov_vals: list[float],
    iv_vals: list[float],
    final: float | None,
    fmt_type: str = "num",
    resolution: float | None = None,
    supervisor: float | None = None,
) -> str:
    """Build a visual range bar for numeric forecasts (auto-scaled)."""
    # Collect all values to determine scale
    all_vals = list(ov_vals) + list(iv_vals)
    if final is not None:
        all_vals.append(final)
    if resolution is not None:
        all_vals.append(resolution)
    if supervisor is not None:
        all_vals.append(supervisor)

    if len(all_vals) < 2:
        return ""

    data_min = min(all_vals)
    data_max = max(all_vals)
    data_range = data_max - data_min

    if data_range == 0:
        return ""

    # Add 10% padding on each side
    padding = data_range * 0.10
    scale_min = data_min - padding
    scale_max = data_max + padding
    scale_range = scale_max - scale_min

    def pct(v):
        return max(0, min(100, (v - scale_min) / scale_range * 100))

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
    if supervisor is not None:
        dots += f'<div class="dot supervisor" style="left: {pct(supervisor)}%"></div>'
    if resolution is not None:
        dots += f'<div class="dot resolution" style="left: {pct(resolution)}%"></div>'

    sup_legend = ""
    if supervisor is not None:
        sup_legend = '<span class="sup-legend">Supervisor</span>'
    res_legend = ""
    if resolution is not None:
        res_legend = '<span class="res-legend">Resolution</span>'

    # Generate 5 evenly-spaced axis labels
    labels = ""
    for i in range(5):
        tick_val = scale_min + (scale_range * i / 4)
        labels += f"<span>{_fmt(tick_val, fmt_type)}</span>"

    return f"""
    <div class="range-bar-legend">
        <span class="ov-legend">Outside View</span>
        <span class="iv-legend">Inside View</span>
        <span class="final-legend">Aggregated</span>
        {sup_legend}
        {res_legend}
    </div>
    <div class="range-bar">
        <div class="ov-range" style="left: {ov_min_pct}%; width: {ov_max_pct - ov_min_pct}%"></div>
        <div class="iv-range" style="left: {iv_min_pct}%; width: {iv_max_pct - iv_min_pct}%"></div>
        {dots}
    </div>
    <div class="range-bar-labels">
        {labels}
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
    parser.add_argument(
        "--tracking-dir",
        default="data/tracking",
        help="Directory containing tracking JSON files (default: data/tracking)",
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

    # Enrich with community predictions, resolutions, and scores
    tracking = load_tracking_data(Path(args.tracking_dir))
    if tracking:
        enrich_with_tracking(analyses, tracking)
        matched = sum(1 for a in analyses if a.community_prediction is not None)
        resolved = sum(1 for a in analyses if a.resolved)
        print(f"Tracking data: {matched} matched, {resolved} resolved")

    generate_html(analyses, Path(args.output))


if __name__ == "__main__":
    main()
