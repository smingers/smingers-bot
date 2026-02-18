#!/usr/bin/env python3
"""
Plot score scatter plot matching the Metaculus UI style.

Reads from a tracking file (no API calls needed). Run the update script
first if you want fresh data:
    poetry run python scripts/update_score_tracking.py --tracking-file <file>

Requires matplotlib (dev dependency):
    poetry add matplotlib --group dev

Usage:
    poetry run python scripts/plot_score_scatter.py                              # defaults to minibench
    poetry run python scripts/plot_score_scatter.py --tracking-file data/tracking/32916.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_TRACKING_FILE = Path("data/tracking/minibench.json")


def main():
    parser = argparse.ArgumentParser(description="Plot score scatter plot from tracking file")
    parser.add_argument(
        "--tracking-file",
        type=Path,
        default=DEFAULT_TRACKING_FILE,
        help=f"Path to tracking JSON file (default: {DEFAULT_TRACKING_FILE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output PNG path (default: derived from tracking file name)",
    )
    args = parser.parse_args()

    tracking_file = args.tracking_file
    # Derive output filename from tracking file: minibench.json -> minibench_scores.png
    if args.output:
        output_file = args.output
    else:
        output_file = tracking_file.with_name(tracking_file.stem + "_scores.png")

    with open(tracking_file) as f:
        tracking = json.load(f)

    tournament_name = tracking.get("tournament_name", tracking_file.stem)

    # Collect scored forecasts — use forecast_timestamp as x-axis since
    # the tracking file doesn't store scheduled_close_time
    close_times = []
    spot_scores = []
    for fc in tracking["forecasts"]:
        sd = fc.get("score_data")
        if not sd or "spot_peer_score" not in sd:
            continue
        ts = fc.get("forecast_timestamp")
        if not ts:
            continue
        dt = datetime.fromisoformat(ts)
        close_times.append(dt)
        spot_scores.append(sd["spot_peer_score"])

    if not spot_scores:
        print("No scored forecasts found.")
        return

    avg_score = np.mean(spot_scores)
    n = len(spot_scores)

    # Sort chronologically for the running average line
    sorted_pairs = sorted(zip(close_times, spot_scores, strict=True))
    sorted_times = [p[0] for p in sorted_pairs]
    sorted_scores = [p[1] for p in sorted_pairs]

    # Cumulative running average — same as what Metaculus shows as the white line
    running_avg = []
    cumsum = 0
    for i, s in enumerate(sorted_scores):
        cumsum += s
        running_avg.append(cumsum / (i + 1))

    # Dark theme to match the Metaculus tournament dashboard
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(16, 7.2))
    fig.patch.set_facecolor("#1a2332")
    ax.set_facecolor("#1a2332")

    # Hollow orange circles — matches Metaculus style
    ax.scatter(
        close_times,
        spot_scores,
        s=80,
        facecolors="none",
        edgecolors="#e8a838",
        linewidths=1.5,
        zorder=3,
    )

    # Running average line in white
    ax.plot(sorted_times, running_avg, color="#ffffff", linewidth=1.2, alpha=0.7, zorder=2)

    # Title and subtitle with count + average
    fig.suptitle(
        f"Score Scatter Plot — {tournament_name}",
        fontsize=20,
        fontweight="bold",
        color="white",
        y=0.97,
    )
    ax.set_title(
        f"Total questions: {n}   Average score: {avg_score:.2f}",
        fontsize=13,
        color="#e8a838",
        pad=15,
    )

    ax.set_xlabel("forecast time", fontsize=12, color="#8899aa")
    ax.set_ylabel("Spot Peer Score", fontsize=12, color="#8899aa")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=0, color="#8899aa")
    plt.yticks(color="#8899aa")

    ax.grid(True, alpha=0.15, color="#ffffff")
    ax.axhline(y=0, color="#ffffff", linewidth=0.5, alpha=0.3)

    for spine in ax.spines.values():
        spine.set_color("#334455")
    ax.tick_params(colors="#8899aa")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(output_file, dpi=120, facecolor="#1a2332", bbox_inches="tight")
    print(f"Saved plot: {output_file}")
    print(f"Total scored: {n}, Average: {avg_score:.2f}")


if __name__ == "__main__":
    main()
