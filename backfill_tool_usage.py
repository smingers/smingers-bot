"""
Backfill tool_usage.json for existing forecast data.

This script parses existing forecast artifacts to reconstruct tool usage metadata.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


def count_results_in_context(context: str, source_type: str) -> int:
    """Count number of results in a search context string."""
    if source_type == "Assistant":
        # Count AskNews articles by counting "**" in titles
        return context.count("**") // 2  # Each article has 2 ** for bold title
    elif source_type == "Agent":
        # Agent search returns synthesized analyses in <Agent_report> tags
        # Count non-error reports with substantial content
        agent_reports = context.split("<Agent_report>")[1:]  # Skip first empty split
        count = 0
        for report in agent_reports:
            # Check if it's not an error and has substantial content (>500 chars)
            if "Error:" not in report[:100] and len(report) > 500:
                count += 1
        return count
    else:
        return context.count("<Summary")


def extract_queries_from_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Extract search queries from a query generation response.

    Returns list of dicts with {query, tool, success, num_results}.
    """
    queries = []

    # Find the "Search queries:" section
    search_queries_block = re.search(
        r'Search queries:(.*?)(?:\n\n|\Z)',
        response_text,
        re.DOTALL | re.IGNORECASE
    )

    if not search_queries_block:
        return queries

    queries_text = search_queries_block.group(1).strip()

    # Parse queries: "1. query text (Source)"
    matches = re.findall(
        r'\d+\.\s*(.+?)\s*\((Google|Google News|Assistant|Agent|Perplexity)\)',
        queries_text
    )

    for query_text, source in matches:
        query = query_text.strip()
        # Map Perplexity to Agent
        if source == "Perplexity":
            source = "Agent"

        queries.append({
            "query": query,
            "tool": source,
            "success": True,  # We'll update this when we check results
            "num_results": 0,  # We'll update this from search results
        })

    return queries


def backfill_forecast(forecast_dir: Path) -> Dict[str, Any]:
    """
    Generate tool_usage.json for a forecast directory.

    Args:
        forecast_dir: Path to forecast directory (e.g., data/38697_20260128_005502)

    Returns:
        tool_usage dict
    """
    tool_usage = {
        "centralized_research": {
            "historical": {
                "forecaster_id": "-1",
                "searched": False,
                "num_queries": 0,
                "queries": [],
                "tools_used": [],
            },
            "current": {
                "forecaster_id": "0",
                "searched": False,
                "num_queries": 0,
                "queries": [],
                "tools_used": [],
            },
        },
        "agents": {},
    }

    research_dir = forecast_dir / "research"
    ensemble_dir = forecast_dir / "ensemble"

    # Process historical queries
    historical_query_file = research_dir / "query_historical.md"
    historical_search_file = research_dir / "search_historical.json"

    if historical_query_file.exists() and historical_search_file.exists():
        with open(historical_query_file, 'r') as f:
            historical_response = f.read()
        with open(historical_search_file, 'r') as f:
            historical_search = json.load(f)

        queries = extract_queries_from_response(historical_response)
        if queries:
            tool_usage["centralized_research"]["historical"]["searched"] = True
            tool_usage["centralized_research"]["historical"]["num_queries"] = len(queries)
            tool_usage["centralized_research"]["historical"]["queries"] = queries

            tools = set(q["tool"] for q in queries)
            tool_usage["centralized_research"]["historical"]["tools_used"] = list(tools)

            # Count results from search context
            context = historical_search.get("context", "")
            for query in queries:
                query["num_results"] = count_results_in_context(context, query["tool"])

    # Process current queries
    current_query_file = research_dir / "query_current.md"
    current_search_file = research_dir / "search_current.json"

    if current_query_file.exists() and current_search_file.exists():
        with open(current_query_file, 'r') as f:
            current_response = f.read()
        with open(current_search_file, 'r') as f:
            current_search = json.load(f)

        queries = extract_queries_from_response(current_response)
        if queries:
            tool_usage["centralized_research"]["current"]["searched"] = True
            tool_usage["centralized_research"]["current"]["num_queries"] = len(queries)
            tool_usage["centralized_research"]["current"]["queries"] = queries

            tools = set(q["tool"] for q in queries)
            tool_usage["centralized_research"]["current"]["tools_used"] = list(tools)

            # Count results from search context
            context = current_search.get("context", "")
            for query in queries:
                query["num_results"] = count_results_in_context(context, query["tool"])

    # Process agents
    for i in range(1, 6):
        agent_name = f"forecaster_{i}"

        # Read metadata.json to get model and weight
        metadata_file = forecast_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                active_agents = metadata.get("config_snapshot", {}).get("_active_agents", [])
                if i - 1 < len(active_agents):
                    agent = active_agents[i - 1]
                    model = agent.get("model", "unknown")
                    weight = agent.get("weight", 1.0)
                else:
                    model = "unknown"
                    weight = 1.0
        else:
            model = "unknown"
            weight = 1.0

        tool_usage["agents"][agent_name] = {
            "model": model,
            "weight": weight,
            "step1": {
                "searched": False,
                "queries": [],
                # Note: We don't have token/cost/timing data from old runs
            },
            "step2": {
                "searched": False,
                "queries": [],
            },
        }

    return tool_usage


def main():
    """Backfill tool_usage.json for specified forecast."""
    forecast_dir = Path("data/38697_20260128_005502")

    if not forecast_dir.exists():
        print(f"Error: Forecast directory not found: {forecast_dir}")
        return

    print(f"Backfilling tool usage for: {forecast_dir}")

    tool_usage = backfill_forecast(forecast_dir)

    # Save to file
    output_file = forecast_dir / "tool_usage.json"
    with open(output_file, 'w') as f:
        json.dump(tool_usage, f, indent=2)

    print(f"✓ Saved tool_usage.json to: {output_file}")
    print(f"\nSummary:")
    print(f"  Historical queries: {tool_usage['centralized_research']['historical']['num_queries']}")
    print(f"  Current queries: {tool_usage['centralized_research']['current']['num_queries']}")
    print(f"  Historical tools: {tool_usage['centralized_research']['historical']['tools_used']}")
    print(f"  Current tools: {tool_usage['centralized_research']['current']['tools_used']}")

    # Show query details
    if tool_usage['centralized_research']['current']['queries']:
        print(f"\nCurrent queries:")
        for q in tool_usage['centralized_research']['current']['queries']:
            print(f"  - [{q['tool']}] {q['query'][:60]}... ({q['num_results']} results)")


if __name__ == "__main__":
    main()
