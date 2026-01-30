#!/usr/bin/env python3
"""
Streamlit Dashboard for Forecast Visualization

Run with: streamlit run scripts/dashboard.py
"""

import asyncio
import json
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

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
            # Handle both 0-1 and 0-100 formats
            if prob > 1:
                prob = prob / 100
            return f"{prob * 100:.1f}%"

    elif q_type == "numeric":
        percentiles = pred_data.get("percentiles", {})
        if percentiles:
            # Show P10 | P50 | P90
            p10 = percentiles.get("10", percentiles.get(10, "?"))
            p50 = percentiles.get("50", percentiles.get(50, "?"))
            p90 = percentiles.get("90", percentiles.get(90, "?"))
            return f"{p10} | {p50} | {p90}"
        # Fallback to final_prediction (median)
        val = row.get("final_prediction")
        if val is not None:
            return f"{val:.2f}"

    elif q_type == "multiple_choice":
        probs = pred_data.get("probabilities", {})
        if probs:
            # Show as "A:30% B:40% C:30%"
            items = []
            for k, v in probs.items():
                if v > 1:
                    v = v / 100
                items.append(f"{k}:{v*100:.0f}%")
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
            # Handle both 0-1 and 0-100 formats
            if prob > 1:
                prob = prob / 100
            return f"{prob * 100:.0f}%"

    elif q_type == "numeric":
        percentiles = pred_data.get("percentiles", {})
        if percentiles:
            # Show just the median for agents
            p50 = percentiles.get("50", percentiles.get(50))
            if p50 is not None:
                return f"{p50:.2f}"
        # Fallback
        if fallback_val is not None:
            return f"{fallback_val:.2f}"

    elif q_type == "multiple_choice":
        probs = pred_data.get("probabilities", [])
        if probs:
            # If it's a list, show as compact percentages
            if isinstance(probs, list):
                return "|".join(f"{p*100:.0f}" if p <= 1 else f"{p:.0f}" for p in probs)
            # If it's a dict
            elif isinstance(probs, dict):
                return "|".join(f"{v*100:.0f}" if v <= 1 else f"{v:.0f}" for v in probs.values())

    return "—"


def main():
    st.title("📊 Metaculus Bot Dashboard")

    # Database path
    db_path = "./data/forecasts.db"

    # Sidebar filters
    st.sidebar.header("Filters")

    mode_options = ["All", "test", "preview", "live"]
    mode_filter = st.sidebar.selectbox("Mode", mode_options, index=0)

    type_options = ["All", "binary", "numeric", "multiple_choice"]
    type_filter = st.sidebar.selectbox("Question Type", type_options, index=0)

    # Load data
    try:
        forecasts = load_forecasts(db_path, mode_filter, type_filter)
    except Exception as e:
        st.error(f"Error loading forecasts: {e}")
        st.info("Make sure to run the migration script first: `python scripts/migrate_artifacts.py`")
        return

    if not forecasts:
        st.warning("No forecasts found matching the filters.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(forecasts)

    # Summary metrics
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

    # Main table
    st.subheader("Forecast History")

    # Prepare display DataFrame
    display_df = df.copy()

    # Format timestamp for display
    if "timestamp" in display_df:
        display_df["date"] = display_df["timestamp"].apply(
            lambda x: f"{x[4:6]}-{x[6:8]} {x[9:11]}:{x[11:13]}" if pd.notna(x) else ""
        )

    # Truncate question title
    if "question_title" in display_df:
        display_df["question"] = display_df["question_title"].apply(
            lambda x: x[:50] + "..." if x and len(x) > 50 else x
        )

    # Format predictions using prediction_data
    display_df["final_fmt"] = display_df.apply(
        lambda row: format_final_prediction(row.to_dict()), axis=1
    )

    for i in range(1, 6):
        display_df[f"agent_{i}_fmt"] = display_df.apply(
            lambda row, agent_num=i: format_agent_prediction(row.to_dict(), agent_num), axis=1
        )

    # Select and rename columns for display
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

    # Filter to available columns
    available_cols = [c for c in columns_to_show.keys() if c in display_df.columns]
    final_df = display_df[available_cols].rename(
        columns={k: v for k, v in columns_to_show.items() if k in available_cols}
    )

    # Format cost column
    if "Cost" in final_df.columns:
        final_df["Cost"] = final_df["Cost"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")

    # Display with styling
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

    # Legend for question types
    st.caption("""
    **Reading the predictions:**
    - **Binary**: Probability as percentage (e.g., 42%)
    - **Numeric**: P10 | P50 (median) | P90 percentiles
    - **Multiple Choice**: Option:Probability for each option (e.g., 0:38% 1:33% 2:19%)
    - **Agent columns (A1-A5)**: For MC, shows probabilities as pipe-separated values (e.g., 38|33|19|10)
    """)

    # Mode distribution chart
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Forecasts by Mode")
        if "mode" in df.columns:
            mode_counts = df["mode"].value_counts()
            st.bar_chart(mode_counts)

    with col2:
        st.subheader("Forecasts by Type")
        if "question_type" in df.columns:
            type_counts = df["question_type"].value_counts()
            st.bar_chart(type_counts)

    # Agent agreement analysis (only for binary)
    binary_df = df[df["question_type"] == "binary"] if "question_type" in df.columns else df
    if len(binary_df) > 0:
        st.divider()
        st.subheader("Agent Agreement Analysis (Binary Questions)")

        agent_cols = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
        available_agent_cols = [c for c in agent_cols if c in binary_df.columns]

        if len(available_agent_cols) >= 2:
            # Calculate standard deviation across agents for each forecast
            agent_df = binary_df[available_agent_cols].copy()
            binary_df = binary_df.copy()
            binary_df["agent_std"] = agent_df.std(axis=1)

            col1, col2 = st.columns(2)
            with col1:
                avg_std = binary_df["agent_std"].mean()
                st.metric("Avg Agent Disagreement (Std Dev)", f"{avg_std:.3f}")

            with col2:
                high_disagreement = (binary_df["agent_std"] > 0.1).sum()
                st.metric("High Disagreement Forecasts (>10%)", high_disagreement)

    # Raw data expander
    with st.expander("Show Raw Data"):
        st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
