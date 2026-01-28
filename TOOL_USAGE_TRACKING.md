# Tool Usage Tracking Implementation

## Overview

Implemented comprehensive tool usage tracking to understand what research tools agents use during forecasting. Each forecast now generates a `tool_usage.json` file with detailed metrics.

## What's Tracked

### Centralized Research Phase
- **Historical queries**: Queries for outside view context
- **Current queries**: Queries for inside view context
- **For each query:**
  - Query text
  - Tool used (Google, Google News, Assistant/AskNews, Agent)
  - Success/failure status
  - Number of results returned

### Per-Agent Execution
- **Model and weight** for each of the 5 agents
- **Step 1 (Outside view):**
  - Whether agent searched
  - Queries generated (if any)
  - Token usage (input/output)
  - Cost
  - Duration in seconds
- **Step 2 (Inside view):**
  - Same metrics as Step 1

## File Structure

```json
{
  "centralized_research": {
    "historical": {
      "forecaster_id": "-1",
      "searched": true,
      "num_queries": 3,
      "queries": [
        {
          "query": "measles cases United States 2025 CDC",
          "tool": "Google",
          "success": true,
          "num_results": 6
        }
      ],
      "tools_used": ["Google", "Google News", "Agent"]
    },
    "current": {...}
  },
  "agents": {
    "forecaster_1": {
      "model": "openrouter/anthropic/claude-sonnet-4.5",
      "weight": 1.0,
      "step1": {
        "searched": false,
        "queries": [],
        "token_input": 5000,
        "token_output": 1200,
        "cost": 0.08,
        "duration_seconds": 12.3
      },
      "step2": {...}
    },
    ...
  }
}
```

## Key Insights from Question 38697

The backfilled data shows:

### Research Phase
- **Historical queries:** 3 total
  - 1 Google search: "measles cases United States 2025 CDC" (6 results)
  - 1 Google News: "measles outbreak United States 2024 cases" (6 results)
  - 1 Agent search: Historical table request (0 results - likely error)

- **Current queries:** 3 total
  - 1 Google search: "measles cases United States 2025" (6 results)
  - 1 Google News: "US measles outbreak January 2026" (6 results)
  - 1 AskNews (Assistant): CDC reports + vaccination coverage (98 results!)

### Agent Behavior
- **None of the 5 agents generated their own search queries** in either step 1 or step 2
- All agents relied entirely on the centralized research phase
- This confirms agents currently don't use their individual search capability

### Tool Usage
- **AskNews was heavily used** in the current research phase (98 articles)
- **Google and Google News** provided 6 results each per query
- **Agent (agentic search)** was attempted for historical context but returned 0 results

## Code Changes

### Modified Files

1. **`src/bot/search.py`**
   - Modified `process_search_queries()` to return `Tuple[str, Dict]` instead of just `str`
   - Tracks queries, tools used, results count, success/failure for each search

2. **`src/storage/artifact_store.py`**
   - Added `save_tool_usage(artifacts, tool_usage)` method

3. **`src/bot/base_forecaster.py`**
   - Added tool_usage tracking dict initialization
   - Captures metadata from centralized research phase
   - Added `_call_model_with_metadata()` wrapper for timing/cost tracking
   - Tracks per-agent metrics for step 1 and step 2
   - Saves tool_usage.json at end of forecast

4. **`src/bot/handler_mixin.py`**
   - Added `_call_model_with_metadata()` method that returns `(content, metadata)` tuple

5. **`src/bot/forecaster.py`**
   - Added `save_tool_usage()` to `ScopedArtifactStore`

### New Files

- **`backfill_tool_usage.py`** - Script to generate tool_usage.json for existing forecasts

## Usage

### For New Forecasts
Tool usage tracking is automatic - every forecast will generate `tool_usage.json`.

### For Existing Forecasts
Run the backfill script:

```bash
python3 backfill_tool_usage.py
```

Note: Backfilled data won't have per-agent token/cost/timing metrics since those weren't captured in the original run.

## Future Enhancements

Potential additions:
1. Track which articles agents actually referenced in their reasoning
2. Aggregate tool usage statistics across multiple forecasts
3. Correlate tool usage with forecast accuracy
4. Add database tables for queryable tool usage analytics
5. Visualize tool usage patterns over time

## Questions This Answers

1. ✅ **What tools are being used?** Google, Google News, AskNews, Agent searches
2. ✅ **Are agents searching individually?** No - currently only centralized research
3. ✅ **How many results per tool?** Varies - AskNews returns many more (98 vs 6)
4. ✅ **Which step is more expensive?** Can compare step1 vs step2 costs per agent
5. ✅ **How long do agents take?** Duration tracked per step per agent
