"""
Quick analysis script for tool_usage.json files.

Usage:
    python3 analyze_tool_usage.py data/38697_20260128_005502/tool_usage.json
"""

import json
import sys
from collections import Counter
from pathlib import Path


def analyze_tool_usage(tool_usage_path: Path):
    """Analyze and print summary of tool usage."""
    with open(tool_usage_path) as f:
        data = json.load(f)

    print(f"\n{'=' * 70}")
    print(f"TOOL USAGE ANALYSIS: {tool_usage_path.parent.name}")
    print(f"{'=' * 70}\n")

    # Centralized Research Summary
    print("CENTRALIZED RESEARCH")
    print("-" * 70)

    for phase in ["historical", "current"]:
        phase_data = data["centralized_research"][phase]
        print(f"\n{phase.upper()} QUERIES ({phase_data['num_queries']} total):")

        if phase_data["searched"]:
            tools_counter = Counter()
            total_results = 0

            for query in phase_data["queries"]:
                tool = query["tool"]
                num_results = query["num_results"]
                tools_counter[tool] += 1
                total_results += num_results

                status = "✓" if query["success"] else "✗"
                print(
                    f"  {status} [{tool:15s}] {num_results:3d} results | {query['query'][:50]}..."
                )

            print(f"\n  Tools used: {', '.join(phase_data['tools_used'])}")
            print(f"  Total results: {total_results}")
        else:
            print("  No search performed")

    # Agent Summary
    print("\n\nAGENT EXECUTION")
    print("-" * 70)

    agents_searched_step1 = 0
    agents_searched_step2 = 0
    total_step1_cost = 0.0
    total_step2_cost = 0.0
    total_step1_tokens_in = 0
    total_step1_tokens_out = 0
    total_step2_tokens_in = 0
    total_step2_tokens_out = 0
    total_step1_time = 0.0
    total_step2_time = 0.0

    for _agent_name, agent_data in data["agents"].items():
        step1 = agent_data["step1"]
        step2 = agent_data["step2"]

        if step1.get("searched"):
            agents_searched_step1 += 1
        if step2.get("searched"):
            agents_searched_step2 += 1

        # Aggregate metrics (may be missing in backfilled data)
        if "cost" in step1:
            total_step1_cost += step1.get("cost", 0.0)
            total_step1_tokens_in += step1.get("token_input", 0)
            total_step1_tokens_out += step1.get("token_output", 0)
            total_step1_time += step1.get("duration_seconds", 0.0)

        if "cost" in step2:
            total_step2_cost += step2.get("cost", 0.0)
            total_step2_tokens_in += step2.get("token_input", 0)
            total_step2_tokens_out += step2.get("token_output", 0)
            total_step2_time += step2.get("duration_seconds", 0.0)

    print("\nAgent Lineup:")
    for agent_name, agent_data in data["agents"].items():
        print(f"  {agent_name}: {agent_data['model']} (weight: {agent_data['weight']})")

    print("\nSearch Activity:")
    print(f"  Agents that searched in Step 1: {agents_searched_step1}/5")
    print(f"  Agents that searched in Step 2: {agents_searched_step2}/5")

    # Show metrics if available
    if total_step1_cost > 0 or total_step2_cost > 0:
        print("\nResource Usage:")
        print("  Step 1 (Outside View):")
        print(f"    Total cost: ${total_step1_cost:.4f}")
        print(f"    Total tokens: {total_step1_tokens_in:,} in / {total_step1_tokens_out:,} out")
        print(f"    Total time: {total_step1_time:.1f}s")

        print("  Step 2 (Inside View):")
        print(f"    Total cost: ${total_step2_cost:.4f}")
        print(f"    Total tokens: {total_step2_tokens_in:,} in / {total_step2_tokens_out:,} out")
        print(f"    Total time: {total_step2_time:.1f}s")

        print("\n  TOTAL:")
        print(f"    Cost: ${total_step1_cost + total_step2_cost:.4f}")
        print(
            f"    Tokens: {total_step1_tokens_in + total_step2_tokens_in:,} in / {total_step1_tokens_out + total_step2_tokens_out:,} out"
        )
        print(f"    Time: {total_step1_time + total_step2_time:.1f}s")
    else:
        print("\n  (Token/cost/timing metrics not available - likely backfilled data)")

    print(f"\n{'=' * 70}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_tool_usage.py <path_to_tool_usage.json>")
        print("Example: python3 analyze_tool_usage.py data/38697_20260128_005502/tool_usage.json")
        sys.exit(1)

    tool_usage_path = Path(sys.argv[1])

    if not tool_usage_path.exists():
        print(f"Error: File not found: {tool_usage_path}")
        sys.exit(1)

    analyze_tool_usage(tool_usage_path)


if __name__ == "__main__":
    main()
