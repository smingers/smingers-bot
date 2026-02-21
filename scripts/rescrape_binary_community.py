#!/usr/bin/env python3
"""Re-scrape binary community predictions using Playwright.

Reads the tracking file, scrapes each binary question's current community P(Yes),
compares with stored values, and prints a diff. Pass --apply to update the file.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraping.community_prediction import (
    scrape_community_prediction,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tracking-file",
        default="data/tracking/32916.json",
        help="Path to tracking JSON file",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update tracking file with scraped values (default: dry-run)",
    )
    args = parser.parse_args()

    tracking_path = Path(args.tracking_file)
    with open(tracking_path) as f:
        data = json.load(f)

    binary_items = [
        item
        for item in data["forecasts"]
        if item.get("comparison", {}).get("type") == "binary"
        and item.get("comparison", {}).get("community_probability") is not None
    ]

    print(f"Found {len(binary_items)} binary questions with community data\n")

    changes = []
    errors = []

    for i, item in enumerate(binary_items):
        qid = item["question_id"]
        old_val = item["comparison"]["community_probability"]

        print(f"[{i + 1}/{len(binary_items)}] Q{qid}...", end=" ", flush=True)

        result = scrape_community_prediction(qid)
        if result is None:
            print("FAILED")
            errors.append(qid)
            continue

        new_val = result.p_yes
        if new_val is None:
            print("NO P(YES)")
            errors.append(qid)
            continue

        diff = new_val - old_val
        if abs(diff) < 0.005:
            print(f"{old_val:.2f} → {new_val:.2f} (OK)")
        else:
            print(f"{old_val:.2f} → {new_val:.2f} (DIFF: {diff:+.2f}) ⚠️")
            changes.append((qid, old_val, new_val))

        # Be nice to Metaculus
        time.sleep(1.5)

    print(f"\n{'=' * 60}")
    print(f"Total: {len(binary_items)}, Changes: {len(changes)}, Errors: {len(errors)}")

    if changes:
        print("\nChanges detected:")
        for qid, old, new in changes:
            print(f"  Q{qid}: {old:.0%} → {new:.0%} (diff: {new - old:+.0%})")

    if args.apply and changes:
        for item in data["forecasts"]:
            for qid, _old, new in changes:
                if item.get("question_id") == qid:
                    item["comparison"]["community_probability"] = new
                    item["comparison"]["difference"] = item["comparison"]["my_probability"] - new
        with open(tracking_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nUpdated {len(changes)} entries in {tracking_path}")
    elif changes:
        print("\nDry run — pass --apply to update the tracking file")


if __name__ == "__main__":
    main()
