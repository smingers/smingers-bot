#!/usr/bin/env python3
"""
Streamlit Dashboard for Forecast Visualization

Run with: streamlit run scripts/dashboard.py
"""

import asyncio
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import ForecastDatabase

# Page config
st.set_page_config(
    page_title="Metaculus Bot Dashboard",
    page_icon="📊",
    layout="wide",
)


def run_async(coro):
    """Helper to run async functions in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =========================================================================
# Data Loaders
# =========================================================================


@st.cache_data(ttl=60)
def load_forecasts(_db_path: str, mode_filter: str | None, type_filter: str | None):
    """Load forecasts from database with caching."""

    async def _load():
        db = ForecastDatabase(_db_path)
        await db.migrate_schema()  # Ensure schema is up to date
        return await db.get_forecasts_with_agents(
            mode=mode_filter if mode_filter != "All" else None,
            question_type=type_filter if type_filter != "All" else None,
            limit=500,
        )

    return run_async(_load())


@st.cache_data(ttl=60)
def load_cost_summary(_db_path: str):
    """Load cost summary."""

    async def _load():
        db = ForecastDatabase(_db_path)
        return await db.get_cost_summary()

    return run_async(_load())


@st.cache_data(ttl=60)
def load_tracking_data(tracking_dir: str) -> dict[str, dict]:
    """Load all tracking JSON files. Returns {tournament_id_str: parsed_data}."""
    tracking_path = Path(tracking_dir)
    result = {}
    if not tracking_path.exists():
        return result
    for json_file in sorted(tracking_path.glob("*.json")):
        with open(json_file) as f:
            data = json.load(f)
        tournament_key = str(data.get("tournament_id", json_file.stem))
        result[tournament_key] = data
    return result


@st.cache_data(ttl=60)
def load_agent_predictions_for_questions(
    _db_path: str,
    question_ids: tuple[int, ...],
) -> dict[int, list[dict]]:
    """Load per-agent predictions from DB for given question_ids.

    Returns {question_id: [agent_pred_dicts]}.
    For questions with multiple forecasts, uses the most recent.
    """

    async def _load():
        import aiosqlite

        if not question_ids:
            return {}

        results: dict[int, list[dict]] = {}
        async with aiosqlite.connect(_db_path) as conn:
            conn.row_factory = aiosqlite.Row
            placeholders = ",".join("?" * len(question_ids))
            cursor = await conn.execute(
                f"""
                SELECT f.question_id, f.id as forecast_id,
                       ap.agent_id, ap.model, ap.prediction, ap.prediction_data
                FROM forecasts f
                JOIN agent_predictions ap ON f.id = ap.forecast_id
                WHERE f.question_id IN ({placeholders})
                  AND f.id = (
                      SELECT id FROM forecasts f2
                      WHERE f2.question_id = f.question_id
                      ORDER BY f2.timestamp DESC LIMIT 1
                  )
                ORDER BY f.question_id, ap.agent_id
            """,
                list(question_ids),
            )
            rows = await cursor.fetchall()

            for row in rows:
                qid = row["question_id"]
                if qid not in results:
                    results[qid] = []
                results[qid].append(dict(row))

        return results

    return run_async(_load())


# =========================================================================
# Scoring Helpers
# =========================================================================


def resolution_to_float(resolution: object, question_type: str) -> float | None:
    """Convert tracking JSON resolution to numeric value for scoring."""
    if resolution is None:
        return None
    if question_type == "binary":
        if isinstance(resolution, str):
            return 1.0 if resolution.lower() == "yes" else 0.0
        return float(resolution)
    if question_type in ("numeric", "date"):
        try:
            return float(resolution)
        except (TypeError, ValueError):
            return None
    return None


def compute_binary_brier(prediction: float, resolution: float) -> float:
    """Brier score: (prediction - outcome)^2. Lower is better."""
    return (prediction - resolution) ** 2


def build_binary_agent_performance(
    resolved_forecasts: list[dict],
    agent_predictions: dict[int, list[dict]],
) -> pd.DataFrame | None:
    """Build a DataFrame of per-agent Brier scores for resolved binary questions."""
    rows = []
    for fc in resolved_forecasts:
        if fc["question_type"] != "binary":
            continue

        qid = fc["question_id"]
        resolution = resolution_to_float(fc["resolution"], "binary")
        if resolution is None:
            continue

        agents = agent_predictions.get(qid, [])
        if not agents:
            continue

        comp = fc.get("comparison", {})
        ensemble_pred = comp.get("my_probability")
        if ensemble_pred is None:
            continue

        for agent in agents:
            pred_data = json.loads(agent["prediction_data"]) if agent.get("prediction_data") else {}
            agent_prob = pred_data.get("probability", agent["prediction"])

            # Normalize if in 0-100 range
            if agent_prob is not None and agent_prob > 1:
                agent_prob = agent_prob / 100

            if agent_prob is None:
                continue

            rows.append(
                {
                    "question_id": qid,
                    "agent_id": agent["agent_id"],
                    "model": agent["model"].split("/")[-1],
                    "agent_prediction": agent_prob,
                    "ensemble_prediction": ensemble_pred,
                    "resolution": resolution,
                    "agent_brier": compute_binary_brier(agent_prob, resolution),
                    "ensemble_brier": compute_binary_brier(ensemble_pred, resolution),
                }
            )

    if not rows:
        return None
    return pd.DataFrame(rows)


def build_numeric_agent_performance(
    resolved_forecasts: list[dict],
    agent_predictions: dict[int, list[dict]],
) -> pd.DataFrame | None:
    """Build a DataFrame of per-agent absolute errors for resolved numeric questions."""
    rows = []
    for fc in resolved_forecasts:
        if fc["question_type"] not in ("numeric", "date"):
            continue

        qid = fc["question_id"]
        resolution = resolution_to_float(fc.get("resolution"), "numeric")
        if resolution is None:
            continue

        agents = agent_predictions.get(qid, [])
        if not agents:
            continue

        comp = fc.get("comparison", {})
        ensemble_median = comp.get("my_median")
        if ensemble_median is None:
            continue

        for agent in agents:
            pred_data = json.loads(agent["prediction_data"]) if agent.get("prediction_data") else {}
            percentiles = pred_data.get("percentiles", {})
            agent_median = percentiles.get("50", percentiles.get(50))

            if agent_median is None:
                continue

            agent_median = float(agent_median)

            rows.append(
                {
                    "question_id": qid,
                    "agent_id": agent["agent_id"],
                    "model": agent["model"].split("/")[-1],
                    "agent_median": agent_median,
                    "ensemble_median": ensemble_median,
                    "resolution": resolution,
                    "agent_abs_error": abs(agent_median - resolution),
                    "ensemble_abs_error": abs(ensemble_median - resolution),
                }
            )

    if not rows:
        return None
    return pd.DataFrame(rows)


def build_mc_agent_performance(
    resolved_forecasts: list[dict],
    agent_predictions: dict[int, list[dict]],
) -> pd.DataFrame | None:
    """Build a DataFrame of per-agent P(correct) for resolved multiple choice questions."""
    rows = []
    for fc in resolved_forecasts:
        if fc["question_type"] != "multiple_choice":
            continue

        qid = fc["question_id"]
        resolution_label = fc.get("resolution")
        agents = agent_predictions.get(qid, [])

        if not agents or not resolution_label:
            continue

        comp = fc.get("comparison", {})
        option_labels = list(comp.get("my_probabilities", {}).keys())
        correct_idx = None
        for i, label in enumerate(option_labels):
            if label == resolution_label:
                correct_idx = i
                break

        if correct_idx is None:
            continue

        ensemble_prob_correct = comp.get("my_probabilities", {}).get(resolution_label)

        for agent in agents:
            pred_data = json.loads(agent["prediction_data"]) if agent.get("prediction_data") else {}
            probs = pred_data.get("probabilities", [])
            if not isinstance(probs, list) or correct_idx >= len(probs):
                continue

            rows.append(
                {
                    "question_id": qid,
                    "agent_id": agent["agent_id"],
                    "model": agent["model"].split("/")[-1],
                    "prob_on_correct": probs[correct_idx],
                    "ensemble_prob_on_correct": ensemble_prob_correct,
                }
            )

    if not rows:
        return None
    return pd.DataFrame(rows)


# =========================================================================
# Display Formatters
# =========================================================================


def parse_prediction_data(json_str: str | None) -> dict:
    """Parse prediction_data JSON string."""
    if not json_str:
        return {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def format_final_prediction(row: dict) -> str:
    """Format the final prediction based on question type, using prediction_data if available."""
    q_type = row.get("question_type")
    pred_data = parse_prediction_data(row.get("prediction_data"))

    if q_type == "binary":
        prob = pred_data.get("probability") or row.get("final_prediction")
        if prob is not None:
            if prob > 1:
                prob = prob / 100
            return f"{prob * 100:.1f}%"

    elif q_type == "numeric":
        percentiles = pred_data.get("percentiles", {})
        if percentiles:
            p10 = percentiles.get("10", percentiles.get(10, "?"))
            p50 = percentiles.get("50", percentiles.get(50, "?"))
            p90 = percentiles.get("90", percentiles.get(90, "?"))
            return f"{p10} | {p50} | {p90}"
        val = row.get("final_prediction")
        if val is not None:
            return f"{val:.2f}"

    elif q_type == "multiple_choice":
        probs = pred_data.get("probabilities", {})
        if probs:
            items = []
            for k, v in probs.items():
                if v > 1:
                    v = v / 100
                items.append(f"{k}:{v * 100:.0f}%")
            return " ".join(items)

    return "—"


def format_agent_prediction(row: dict, agent_num: int) -> str:
    """Format an agent's prediction based on question type."""
    q_type = row.get("question_type")
    pred_data = parse_prediction_data(row.get(f"agent_{agent_num}_data"))
    fallback_val = row.get(f"agent_{agent_num}")

    if q_type == "binary":
        prob = pred_data.get("probability") or fallback_val
        if prob is not None:
            if prob > 1:
                prob = prob / 100
            return f"{prob * 100:.0f}%"

    elif q_type == "numeric":
        percentiles = pred_data.get("percentiles", {})
        if percentiles:
            p50 = percentiles.get("50", percentiles.get(50))
            if p50 is not None:
                return f"{p50:.2f}"
        if fallback_val is not None:
            return f"{fallback_val:.2f}"

    elif q_type == "multiple_choice":
        probs = pred_data.get("probabilities", [])
        if probs:
            if isinstance(probs, list):
                return "|".join(f"{p * 100:.0f}" if p <= 1 else f"{p:.0f}" for p in probs)
            elif isinstance(probs, dict):
                return "|".join(f"{v * 100:.0f}" if v <= 1 else f"{v:.0f}" for v in probs.values())

    return "—"


# =========================================================================
# Main Dashboard
# =========================================================================


def main():
    st.title("📊 Metaculus Bot Dashboard")

    db_path = "./data/forecasts.db"

    # Sidebar filters
    st.sidebar.header("Filters")
    mode_options = ["All", "test", "preview", "live"]
    mode_filter = st.sidebar.selectbox("Mode", mode_options, index=0)
    type_options = ["All", "binary", "numeric", "multiple_choice"]
    type_filter = st.sidebar.selectbox("Question Type", type_options, index=0)

    # Performance tournament selector
    st.sidebar.header("Performance")
    tracking_data = load_tracking_data("./data/tracking")
    tournament_options = ["All Tournaments"] + [
        f"{tid} - {tdata.get('tournament_name', tid)}" for tid, tdata in tracking_data.items()
    ]
    selected_tournament = st.sidebar.selectbox("Tournament", tournament_options, index=0)

    # Load forecast data from database
    forecasts = []
    try:
        forecasts = load_forecasts(db_path, mode_filter, type_filter)
    except Exception as e:
        st.error(f"Error loading forecasts: {e}")
        st.info(
            "Make sure to run the migration script first: `python scripts/migrate_artifacts.py`"
        )

    if not forecasts:
        st.warning("No forecasts found matching the filters.")

    df = pd.DataFrame(forecasts) if forecasts else pd.DataFrame()

    # =====================================================================
    # FORECAST HISTORY (from database)
    # =====================================================================
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Forecasts", len(df))
        with col2:
            total_cost = df["total_cost"].sum() if "total_cost" in df else 0
            st.metric("Total Cost", f"${total_cost:.2f}")
        with col3:
            avg_cost = df["total_cost"].mean() if "total_cost" in df else 0
            st.metric("Avg Cost/Forecast", f"${avg_cost:.2f}")
        with col4:
            mode_counts = df["mode"].value_counts().to_dict() if "mode" in df else {}
            live_count = mode_counts.get("live", 0)
            test_count = mode_counts.get("test", 0)
            st.metric("Live / Test", f"{live_count} / {test_count}")

        st.divider()
        st.subheader("Forecast History")

        display_df = df.copy()
        if "timestamp" in display_df:
            display_df["date"] = display_df["timestamp"].apply(
                lambda x: f"{x[4:6]}-{x[6:8]} {x[9:11]}:{x[11:13]}" if pd.notna(x) else ""
            )
        if "question_title" in display_df:
            display_df["question"] = display_df["question_title"].apply(
                lambda x: x[:50] + "..." if x and len(x) > 50 else x
            )
        display_df["final_fmt"] = display_df.apply(
            lambda row: format_final_prediction(row.to_dict()), axis=1
        )
        for i in range(1, 6):
            display_df[f"agent_{i}_fmt"] = display_df.apply(
                lambda row, agent_num=i: format_agent_prediction(row.to_dict(), agent_num), axis=1
            )

        columns_to_show = {
            "date": "Date",
            "mode": "Mode",
            "question_type": "Type",
            "question": "Question",
            "agent_1_fmt": "A1",
            "agent_2_fmt": "A2",
            "agent_3_fmt": "A3",
            "agent_4_fmt": "A4",
            "agent_5_fmt": "A5",
            "final_fmt": "Final",
            "total_cost": "Cost",
        }
        available_cols = [c for c in columns_to_show.keys() if c in display_df.columns]
        final_df = display_df[available_cols].rename(
            columns={k: v for k, v in columns_to_show.items() if k in available_cols}
        )
        if "Cost" in final_df.columns:
            final_df["Cost"] = final_df["Cost"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")

        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mode": st.column_config.TextColumn(width="small"),
                "Type": st.column_config.TextColumn(width="small"),
                "Question": st.column_config.TextColumn(width="large"),
                "A1": st.column_config.TextColumn(width="small"),
                "A2": st.column_config.TextColumn(width="small"),
                "A3": st.column_config.TextColumn(width="small"),
                "A4": st.column_config.TextColumn(width="small"),
                "A5": st.column_config.TextColumn(width="small"),
                "Final": st.column_config.TextColumn(width="medium"),
                "Cost": st.column_config.TextColumn(width="small"),
            },
        )

        st.caption("""
        **Reading the predictions:**
        - **Binary**: Probability as percentage (e.g., 42%)
        - **Numeric**: P10 | P50 (median) | P90 percentiles
        - **Multiple Choice**: Option:Probability for each option (e.g., 0:38% 1:33% 2:19%)
        - **Agent columns (A1-A5)**: For MC, shows probabilities as pipe-separated values (e.g., 38|33|19|10)
        """)

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Forecasts by Mode")
            if "mode" in df.columns:
                st.bar_chart(df["mode"].value_counts())
        with col2:
            st.subheader("Forecasts by Type")
            if "question_type" in df.columns:
                st.bar_chart(df["question_type"].value_counts())

        # Agent agreement analysis (only for binary)
        binary_df = df[df["question_type"] == "binary"] if "question_type" in df.columns else df
        if len(binary_df) > 0:
            st.divider()
            st.subheader("Agent Agreement Analysis (Binary Questions)")
            agent_cols = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
            available_agent_cols = [c for c in agent_cols if c in binary_df.columns]
            if len(available_agent_cols) >= 2:
                agent_df = binary_df[available_agent_cols].copy()
                binary_df = binary_df.copy()
                binary_df["agent_std"] = agent_df.std(axis=1)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Avg Agent Disagreement (Std Dev)", f"{binary_df['agent_std'].mean():.3f}"
                    )
                with col2:
                    st.metric(
                        "High Disagreement Forecasts (>10%)", (binary_df["agent_std"] > 0.1).sum()
                    )

        with st.expander("Show Raw Data"):
            st.dataframe(df, use_container_width=True, hide_index=True)

    # =====================================================================
    # PERFORMANCE (from tracking JSONs + database agent predictions)
    # =====================================================================
    st.divider()
    st.header("Performance")

    if not tracking_data:
        st.info(
            "No tracking data found in `data/tracking/`. "
            "Run `python scripts/track_forecasts.py` first."
        )
    else:
        # Collect resolved forecasts based on tournament selection
        if selected_tournament == "All Tournaments":
            all_resolved = []
            for tdata in tracking_data.values():
                for fc in tdata.get("forecasts", []):
                    if fc.get("resolved") and fc.get("score_data"):
                        all_resolved.append(fc)
            section_label = "All Tournaments"
        else:
            tournament_id = selected_tournament.split(" - ")[0]
            tdata = tracking_data[tournament_id]
            all_resolved = [
                fc
                for fc in tdata.get("forecasts", [])
                if fc.get("resolved") and fc.get("score_data")
            ]
            section_label = tdata.get("tournament_name", tournament_id)

        if not all_resolved:
            st.warning(f"No resolved and scored questions yet for {section_label}.")
        else:
            # --- AGGREGATE SCORES ---
            st.subheader(f"Aggregate Scores — {section_label}")
            peer_scores = [fc["score_data"]["peer_score"] for fc in all_resolved]
            baseline_scores = [fc["score_data"]["baseline_score"] for fc in all_resolved]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Resolved Questions", len(all_resolved))
            with col2:
                st.metric("Avg Peer Score", f"{sum(peer_scores) / len(peer_scores):.1f}")
            with col3:
                st.metric(
                    "Avg Baseline Score", f"{sum(baseline_scores) / len(baseline_scores):.1f}"
                )
            with col4:
                positive_peer = sum(1 for s in peer_scores if s > 0)
                st.metric("Positive Peer Score", f"{positive_peer}/{len(all_resolved)}")

            # Scores by question type
            st.subheader("Scores by Question Type")
            type_groups: dict[str, list[dict]] = {}
            for fc in all_resolved:
                type_groups.setdefault(fc["question_type"], []).append(fc)

            type_rows = []
            for qt, fcs in sorted(type_groups.items()):
                peers = [fc["score_data"]["peer_score"] for fc in fcs]
                baselines = [fc["score_data"]["baseline_score"] for fc in fcs]
                type_rows.append(
                    {
                        "Type": qt,
                        "Count": len(fcs),
                        "Avg Peer": round(sum(peers) / len(peers), 1),
                        "Avg Baseline": round(sum(baselines) / len(baselines), 1),
                        "Best Peer": round(max(peers), 1),
                        "Worst Peer": round(min(peers), 1),
                    }
                )
            st.dataframe(pd.DataFrame(type_rows), use_container_width=True, hide_index=True)

            # Per-question peer score bar chart
            st.subheader("Peer Score by Question")
            chart_data = pd.DataFrame(
                [
                    {
                        "question": fc["question_title"][:40],
                        "Peer Score": fc["score_data"]["peer_score"],
                    }
                    for fc in all_resolved
                ]
            ).set_index("question")
            st.bar_chart(chart_data)

            # Cumulative peer score
            st.subheader("Cumulative Peer Score")
            sorted_resolved = sorted(
                all_resolved, key=lambda fc: fc.get("forecast_timestamp") or ""
            )
            running_sum = 0.0
            cumulative = []
            for i, fc in enumerate(sorted_resolved):
                running_sum += fc["score_data"]["peer_score"]
                cumulative.append({"Question #": i + 1, "Cumulative Peer Score": running_sum})
            st.line_chart(pd.DataFrame(cumulative).set_index("Question #"))

            # --- PER-AGENT SCORING ---
            st.divider()
            resolved_qids = tuple(fc["question_id"] for fc in all_resolved)
            agent_preds = load_agent_predictions_for_questions(db_path, resolved_qids)

            binary_perf_df = build_binary_agent_performance(all_resolved, agent_preds)
            numeric_perf_df = build_numeric_agent_performance(all_resolved, agent_preds)
            mc_perf_df = build_mc_agent_performance(all_resolved, agent_preds)

            has_any_agent_data = any(
                x is not None and not x.empty for x in [binary_perf_df, numeric_perf_df, mc_perf_df]
            )

            if not has_any_agent_data:
                st.info("No resolved questions with agent prediction data available for scoring.")
            else:
                # === UNIFIED SUMMARY TABLE ===
                st.subheader("Per-Agent Summary — All Question Types")

                unified_rows: dict[str, dict] = {}

                if binary_perf_df is not None and not binary_perf_df.empty:
                    for _, r in (
                        binary_perf_df.groupby(["agent_id", "model"])
                        .agg(avg_brier=("agent_brier", "mean"), n=("question_id", "nunique"))
                        .reset_index()
                        .iterrows()
                    ):
                        aid = r["agent_id"]
                        unified_rows.setdefault(aid, {"Agent": aid, "Model": r["model"]})
                        unified_rows[aid]["Brier ↓"] = r["avg_brier"]
                        unified_rows[aid]["_bn"] = int(r["n"])
                    ens_brier = (
                        binary_perf_df.groupby("question_id")["ensemble_brier"].first().mean()
                    )
                    unified_rows.setdefault(
                        "ENSEMBLE", {"Agent": "ENSEMBLE", "Model": "(weighted avg)"}
                    )
                    unified_rows["ENSEMBLE"]["Brier ↓"] = ens_brier
                    unified_rows["ENSEMBLE"]["_bn"] = binary_perf_df["question_id"].nunique()

                if mc_perf_df is not None and not mc_perf_df.empty:
                    for _, r in (
                        mc_perf_df.groupby(["agent_id", "model"])
                        .agg(avg_p=("prob_on_correct", "mean"), n=("question_id", "nunique"))
                        .reset_index()
                        .iterrows()
                    ):
                        aid = r["agent_id"]
                        unified_rows.setdefault(aid, {"Agent": aid, "Model": r["model"]})
                        unified_rows[aid]["P(Correct) ↑"] = r["avg_p"]
                        unified_rows[aid]["_mn"] = int(r["n"])
                    ens_mc = (
                        mc_perf_df.groupby("question_id")["ensemble_prob_on_correct"].first().mean()
                    )
                    unified_rows.setdefault(
                        "ENSEMBLE", {"Agent": "ENSEMBLE", "Model": "(weighted avg)"}
                    )
                    unified_rows["ENSEMBLE"]["P(Correct) ↑"] = ens_mc
                    unified_rows["ENSEMBLE"]["_mn"] = mc_perf_df["question_id"].nunique()

                if numeric_perf_df is not None and not numeric_perf_df.empty:
                    for _, r in (
                        numeric_perf_df.groupby(["agent_id", "model"])
                        .agg(avg_err=("agent_abs_error", "mean"), n=("question_id", "nunique"))
                        .reset_index()
                        .iterrows()
                    ):
                        aid = r["agent_id"]
                        unified_rows.setdefault(aid, {"Agent": aid, "Model": r["model"]})
                        unified_rows[aid]["Abs Error ↓"] = r["avg_err"]
                        unified_rows[aid]["_nn"] = int(r["n"])
                    ens_err = (
                        numeric_perf_df.groupby("question_id")["ensemble_abs_error"].first().mean()
                    )
                    unified_rows.setdefault(
                        "ENSEMBLE", {"Agent": "ENSEMBLE", "Model": "(weighted avg)"}
                    )
                    unified_rows["ENSEMBLE"]["Abs Error ↓"] = ens_err
                    unified_rows["ENSEMBLE"]["_nn"] = numeric_perf_df["question_id"].nunique()

                for row in unified_rows.values():
                    row["Questions"] = row.pop("_bn", 0) + row.pop("_mn", 0) + row.pop("_nn", 0)

                unified_df = pd.DataFrame(list(unified_rows.values()))
                unified_df["_sort"] = unified_df["Agent"].apply(
                    lambda x: "zzz" if x == "ENSEMBLE" else x
                )
                unified_df = unified_df.sort_values("_sort").drop(columns=["_sort"])

                unified_display = unified_df.copy()
                if "Brier ↓" in unified_display.columns:
                    unified_display["Brier ↓"] = unified_display["Brier ↓"].apply(
                        lambda x: f"{x:.4f}" if pd.notna(x) else "—"
                    )
                if "P(Correct) ↑" in unified_display.columns:
                    unified_display["P(Correct) ↑"] = unified_display["P(Correct) ↑"].apply(
                        lambda x: f"{x:.1%}" if pd.notna(x) else "—"
                    )
                if "Abs Error ↓" in unified_display.columns:
                    unified_display["Abs Error ↓"] = unified_display["Abs Error ↓"].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else "—"
                    )
                unified_display["Questions"] = unified_display["Questions"].astype(int)
                st.dataframe(unified_display, use_container_width=True, hide_index=True)
                st.caption(
                    "**Brier ↓** = Brier score on binary (lower is better) · "
                    "**P(Correct) ↑** = probability on correct MC outcome (higher is better) · "
                    "**Abs Error ↓** = |median − resolution| on numeric (lower is better)"
                )

                # === TYPE-SPECIFIC DRILL-DOWNS ===

                if binary_perf_df is not None and not binary_perf_df.empty:
                    with st.expander("Binary — Per-Agent Detail"):
                        bsm = (
                            binary_perf_df.groupby(["agent_id", "model"])
                            .agg(
                                avg_brier=("agent_brier", "mean"),
                                num_questions=("question_id", "nunique"),
                                min_brier=("agent_brier", "min"),
                                max_brier=("agent_brier", "max"),
                            )
                            .reset_index()
                        )
                        ea = binary_perf_df.groupby("question_id")["ensemble_brier"].first()
                        bsm = pd.concat(
                            [
                                bsm,
                                pd.DataFrame(
                                    [
                                        {
                                            "agent_id": "ENSEMBLE",
                                            "model": "(weighted avg)",
                                            "avg_brier": ea.mean(),
                                            "num_questions": ea.count(),
                                            "min_brier": ea.min(),
                                            "max_brier": ea.max(),
                                        }
                                    ]
                                ),
                            ],
                            ignore_index=True,
                        ).sort_values("avg_brier")
                        bd = bsm.rename(
                            columns={
                                "agent_id": "Agent",
                                "model": "Model",
                                "avg_brier": "Avg Brier",
                                "num_questions": "Questions",
                                "min_brier": "Best",
                                "max_brier": "Worst",
                            }
                        )
                        for c in ["Avg Brier", "Best", "Worst"]:
                            bd[c] = bd[c].apply(lambda x: f"{x:.4f}")
                        bd["Questions"] = bd["Questions"].astype(int)
                        st.dataframe(bd, use_container_width=True, hide_index=True)

                        st.caption("Agent Brier Scores (lower is better)")
                        st.bar_chart(
                            bsm[["agent_id", "avg_brier"]]
                            .set_index("agent_id")
                            .rename(columns={"avg_brier": "Avg Brier Score"})
                        )

                        pivot = binary_perf_df.pivot_table(
                            index="question_id",
                            columns="agent_id",
                            values="agent_brier",
                            aggfunc="first",
                        )
                        qtt = {
                            fc["question_id"]: fc["question_title"][:50]
                            for fc in all_resolved
                            if fc["question_type"] == "binary"
                        }
                        qte = {}
                        for fc in all_resolved:
                            if fc["question_type"] == "binary" and fc.get("resolution") is not None:
                                res = resolution_to_float(fc["resolution"], "binary")
                                if res is not None:
                                    qte[fc["question_id"]] = compute_binary_brier(
                                        fc["comparison"]["my_probability"], res
                                    )
                        pivot["ENSEMBLE"] = pivot.index.map(lambda q: qte.get(q))
                        pivot.insert(0, "Question", pivot.index.map(lambda q: qtt.get(q, str(q))))
                        nc = [c for c in pivot.columns if c != "Question"]
                        st.dataframe(
                            pivot.style.format("{:.4f}", subset=nc, na_rep="—"),
                            use_container_width=True,
                        )

                if mc_perf_df is not None and not mc_perf_df.empty:
                    with st.expander("Multiple Choice — Per-Agent Detail"):
                        msm = (
                            mc_perf_df.groupby(["agent_id", "model"])
                            .agg(
                                avg_prob_correct=("prob_on_correct", "mean"),
                                num_questions=("question_id", "nunique"),
                            )
                            .reset_index()
                        )
                        emc = (
                            mc_perf_df.groupby("question_id")["ensemble_prob_on_correct"]
                            .first()
                            .mean()
                        )
                        msm = pd.concat(
                            [
                                msm,
                                pd.DataFrame(
                                    [
                                        {
                                            "agent_id": "ENSEMBLE",
                                            "model": "(weighted avg)",
                                            "avg_prob_correct": emc,
                                            "num_questions": mc_perf_df["question_id"].nunique(),
                                        }
                                    ]
                                ),
                            ],
                            ignore_index=True,
                        ).sort_values("avg_prob_correct", ascending=False)
                        md = msm.rename(
                            columns={
                                "agent_id": "Agent",
                                "model": "Model",
                                "avg_prob_correct": "Avg P(Correct)",
                                "num_questions": "Questions",
                            }
                        )
                        md["Avg P(Correct)"] = md["Avg P(Correct)"].apply(lambda x: f"{x:.1%}")
                        md["Questions"] = md["Questions"].astype(int)
                        st.dataframe(md, use_container_width=True, hide_index=True)

                if numeric_perf_df is not None and not numeric_perf_df.empty:
                    with st.expander("Numeric — Per-Agent Detail"):
                        st.caption(
                            "Absolute error from median vs actual resolution (lower is better)"
                        )
                        nsm = (
                            numeric_perf_df.groupby(["agent_id", "model"])
                            .agg(
                                avg_abs_error=("agent_abs_error", "mean"),
                                num_questions=("question_id", "nunique"),
                                min_abs_error=("agent_abs_error", "min"),
                                max_abs_error=("agent_abs_error", "max"),
                            )
                            .reset_index()
                        )
                        ene = numeric_perf_df.groupby("question_id")["ensemble_abs_error"].first()
                        nsm = pd.concat(
                            [
                                nsm,
                                pd.DataFrame(
                                    [
                                        {
                                            "agent_id": "ENSEMBLE",
                                            "model": "(weighted avg)",
                                            "avg_abs_error": ene.mean(),
                                            "num_questions": ene.count(),
                                            "min_abs_error": ene.min(),
                                            "max_abs_error": ene.max(),
                                        }
                                    ]
                                ),
                            ],
                            ignore_index=True,
                        ).sort_values("avg_abs_error")
                        nd = nsm.rename(
                            columns={
                                "agent_id": "Agent",
                                "model": "Model",
                                "avg_abs_error": "Avg Abs Error",
                                "num_questions": "Questions",
                                "min_abs_error": "Best",
                                "max_abs_error": "Worst",
                            }
                        )
                        for c in ["Avg Abs Error", "Best", "Worst"]:
                            nd[c] = nd[c].apply(lambda x: f"{x:.2f}")
                        nd["Questions"] = nd["Questions"].astype(int)
                        st.dataframe(nd, use_container_width=True, hide_index=True)

                        st.caption("Agent Absolute Error (lower is better)")
                        st.bar_chart(
                            nsm[["agent_id", "avg_abs_error"]]
                            .set_index("agent_id")
                            .rename(columns={"avg_abs_error": "Avg Abs Error"})
                        )

                        npv = numeric_perf_df.pivot_table(
                            index="question_id",
                            columns="agent_id",
                            values="agent_abs_error",
                            aggfunc="first",
                        )
                        qnt = {
                            fc["question_id"]: fc["question_title"][:50]
                            for fc in all_resolved
                            if fc["question_type"] in ("numeric", "date")
                        }
                        qne = {
                            r["question_id"]: r["ensemble_abs_error"]
                            for _, r in numeric_perf_df.drop_duplicates("question_id").iterrows()
                        }
                        npv["ENSEMBLE"] = npv.index.map(lambda q: qne.get(q))
                        npv.insert(0, "Question", npv.index.map(lambda q: qnt.get(q, str(q))))
                        nnc = [c for c in npv.columns if c != "Question"]
                        st.dataframe(
                            npv.style.format("{:.2f}", subset=nnc, na_rep="—"),
                            use_container_width=True,
                        )

            # --- ALL RESOLVED FORECASTS ---
            with st.expander("All Resolved Forecasts"):
                resolved_rows = []
                for fc in all_resolved:
                    resolved_rows.append(
                        {
                            "Question": fc["question_title"][:50],
                            "Type": fc["question_type"],
                            "Resolution": str(fc.get("resolution", ""))[:30],
                            "Peer Score": round(fc["score_data"]["peer_score"], 1),
                            "Baseline Score": round(fc["score_data"]["baseline_score"], 1),
                            "Coverage": round(fc["score_data"].get("coverage", 0), 2),
                        }
                    )
                st.dataframe(pd.DataFrame(resolved_rows), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
