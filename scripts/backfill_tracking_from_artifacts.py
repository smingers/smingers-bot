#!/usr/bin/env python3
"""
Backfill tracking JSON files with missing questions from forecast artifact directories.

Scans data/ for artifact dirs ({question_id}_{timestamp}), reads question.json and
metadata.json, and adds skeleton entries to data/tracking/32916.json, minibench.json, or
other.json for any question that is not already in the corresponding file. No API
calls—uses only local artifact data. Skips test-mode forecasts.

Usage:
    poetry run python scripts/backfill_tracking_from_artifacts.py              # dry run
    poetry run python scripts/backfill_tracking_from_artifacts.py --apply     # write files
"""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path("data")
TRACKING_DIR = Path("data/tracking")

# Which tracking file to use: keyed by tournament id (int) or slug (str)
TRACKING_FILE_BY_KEY = {
    32916: TRACKING_DIR / "32916.json",
    "minibench": TRACKING_DIR / "minibench.json",
    "other": TRACKING_DIR / "other.json",
}

TOURNAMENT_NAMES = {
    32916: "Tournament 32916",
    "minibench": "Tournament minibench",
    "other": "Other tournaments and standalone questions",
}


def get_tracking_key(question_data: dict) -> str | int:
    """Return which tracking file key this question belongs to (32916, 'minibench', or 'other')."""
    projects = question_data.get("projects") or {}
    tournament_list = projects.get("tournament") or []
    for t in tournament_list:
        if isinstance(t, dict):
            tid = t.get("id")
            slug = (t.get("slug") or "").strip().lower()
            if tid == 32916:
                return 32916
            if slug == "minibench":
                return "minibench"
    return "other"


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def build_skeleton(question_path: Path, metadata_path: Path) -> dict | None:
    """Build a tracking skeleton entry from question.json and metadata.json. Returns None if invalid."""
    q = load_json(question_path)
    if not q:
        return None
    post_id = q.get("id")
    title = q.get("title", "Unknown")
    resolved = q.get("resolved", False)
    inner = q.get("question") or {}
    q_type = inner.get("type", "unknown")
    resolution = inner.get("resolution")
    num_forecasters = (
        q.get("nr_forecasters") or q.get("forecasts_count") or inner.get("forecaster_count")
    )

    # forecast_timestamp from metadata (when we ran the forecast)
    forecast_ts = None
    snapshot_ts = datetime.now(tz=UTC).isoformat()
    if metadata_path.exists():
        meta = load_json(metadata_path)
        if meta:
            created = meta.get("created_at")
            if created:
                forecast_ts = created
                snapshot_ts = created

    return {
        "question_id": post_id,
        "question_title": title,
        "question_type": q_type,
        "question_url": f"https://www.metaculus.com/questions/{post_id}/",
        "forecast_timestamp": forecast_ts,
        "snapshot_timestamp": snapshot_ts,
        "num_forecasters": num_forecasters,
        "resolved": resolved,
        "resolution": resolution,
        "comparison": None,
        "score_data": None,
    }


def ensure_tracking_structure(data: dict, key: str | int) -> dict:
    """Ensure top-level keys exist so we can safely add forecasts and update counts."""
    if "forecasts" not in data:
        data["forecasts"] = []
    if "tournament_id" not in data:
        data["tournament_id"] = key
    if "tournament_name" not in data:
        data["tournament_name"] = TOURNAMENT_NAMES.get(key, f"Tournament {key}")
    if "last_updated" not in data:
        data["last_updated"] = datetime.now(tz=UTC).isoformat()
    if "total_forecasts" not in data:
        data["total_forecasts"] = 0
    return data


def recompute_type_counts(forecasts: list[dict]) -> dict[str, int]:
    """Recompute binary_count, numeric_count, multiple_choice_count, date_count from forecast list."""
    counts = {"binary_count": 0, "numeric_count": 0, "multiple_choice_count": 0, "date_count": 0}
    for f in forecasts:
        t = (f.get("question_type") or "").strip().lower()
        if t == "binary":
            counts["binary_count"] += 1
        elif t in ("numeric", "discrete"):
            counts["numeric_count"] += 1
        elif t == "multiple_choice":
            counts["multiple_choice_count"] += 1
        elif t == "date":
            counts["date_count"] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Backfill tracking files with questions from forecast artifact dirs"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updated tracking files (default: dry run)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing forecast artifact dirs",
    )
    parser.add_argument(
        "--tracking-dir",
        type=Path,
        default=TRACKING_DIR,
        help="Directory containing tracking JSON files",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    tracking_dir = args.tracking_dir
    if not data_dir.is_dir():
        print(f"Data directory not found: {data_dir}")
        return

    # Discover artifact dirs: {question_id}_{YYYYMMDD}_{HHMMSS}
    artifact_dirs = []
    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not re.match(r"^\d+_\d{8}_\d{6}$", entry.name):
            continue
        q_path = entry / "question.json"
        if not q_path.exists():
            continue
        # Skip test mode
        meta_path = entry / "metadata.json"
        if meta_path.exists():
            meta = load_json(meta_path)
            if meta:
                mode = (meta.get("config_snapshot") or {}).get("mode", "")
                if (mode or "").strip().lower() == "test":
                    continue
        artifact_dirs.append(entry)

    print(f"Found {len(artifact_dirs)} non-test forecast artifact dirs in {data_dir}")

    # Build skeleton per artifact and group by tracking key
    by_key: dict[str | int, list[tuple[int, dict]]] = {32916: [], "minibench": [], "other": []}
    for entry in artifact_dirs:
        meta_path = entry / "metadata.json"
        skel = build_skeleton(entry / "question.json", meta_path)
        if not skel or skel.get("question_id") is None:
            continue
        key = get_tracking_key(load_json(entry / "question.json") or {})
        if key not in by_key:
            by_key[key] = []
        by_key[key].append((skel["question_id"], skel))

    # Load each tracking file and add missing questions
    changes = []
    for key, items in by_key.items():
        path = TRACKING_FILE_BY_KEY.get(key)
        if not path:
            path = tracking_dir / f"{key}.json"
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        existing = load_json(path)
        if existing is None:
            existing = {}
        existing = ensure_tracking_structure(existing, key)
        existing_ids = {f["question_id"] for f in existing["forecasts"]}

        added = 0
        for qid, skel in items:
            if qid not in existing_ids:
                existing["forecasts"].append(skel)
                existing_ids.add(qid)
                added += 1
                changes.append((key, qid, skel.get("question_title", "")[:50]))

        if added > 0:
            # Recompute type counts
            for k, v in recompute_type_counts(existing["forecasts"]).items():
                existing[k] = v
            existing["total_forecasts"] = len(existing["forecasts"])
            existing["last_updated"] = datetime.now(tz=UTC).isoformat()

            if args.apply:
                with open(path, "w") as f:
                    json.dump(existing, f, indent=2)
                print(
                    f"  {path}: added {added} question(s), total now {existing['total_forecasts']}"
                )
            else:
                print(
                    f"  [dry run] {path}: would add {added} question(s), total would be {existing['total_forecasts']}"
                )

    if changes and not args.apply:
        print("\nWould add:")
        for key, qid, title in changes[:20]:
            print(f"  {key}: Q{qid} {title}...")
        if len(changes) > 20:
            print(f"  ... and {len(changes) - 20} more")
    elif changes and args.apply:
        print(f"\nAdded {len(changes)} question(s) across tracking files.")
    else:
        print("No missing questions to add.")


if __name__ == "__main__":
    main()
