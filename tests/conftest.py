"""
Shared pytest fixtures for Metaculus bot tests.
"""

import pytest
from pathlib import Path

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ============================================================================
# Binary Probability Extraction Fixtures
# ============================================================================

@pytest.fixture
def binary_response_standard():
    """Standard binary response with 'Probability: X%' format."""
    return """
## Analysis

Based on the historical data and current trends, I've analyzed the key factors:

1. Historical base rate: approximately 40%
2. Recent momentum suggests slight increase
3. No major disruptions expected

## Calibration Checklist

1. Resolution: The question resolves YES if event X occurs by date Y.
2. Outside view base rate: 40%
3. Consistency check: 55 out of 100 times, this resolves YES.
4. Top evidence: Recent policy changes, historical patterns, expert consensus
5. Blind spot: Unexpected black swan events could shift dramatically
6. Status quo: Moderate stability expected

Probability: 55%
"""


@pytest.fixture
def binary_response_decimal():
    """Binary response with decimal probability."""
    return """
After careful analysis:

Probability: 72.5%
"""


@pytest.fixture
def binary_response_no_label():
    """Response without explicit 'Probability:' label, just percentage at end."""
    return """
Based on my analysis, considering all factors including historical precedent (30%)
and recent developments (increased to 45%), the final assessment suggests
a likelihood of 67.3% for this outcome.
"""


@pytest.fixture
def binary_response_multiple_percentages():
    """Response with multiple percentages throughout, final one is answer."""
    return """
Historical base rate: 30%
Adjusted for trends: 45%
Expert consensus: 60%
My calibrated estimate:

Probability: 52%
"""


@pytest.fixture
def binary_response_extreme_high():
    """Response with >99% probability (should clamp to 99)."""
    return "After analysis, this is virtually certain. Probability: 100%"


@pytest.fixture
def binary_response_extreme_low():
    """Response with <1% probability (should clamp to 1)."""
    return "This is nearly impossible. Probability: 0%"


@pytest.fixture
def binary_response_no_probability():
    """Response with no extractable probability."""
    return """
I have analyzed this question but cannot determine a specific probability.
The situation is too uncertain for a point estimate.
"""


# ============================================================================
# Multiple Choice Extraction Fixtures
# ============================================================================

@pytest.fixture
def mc_response_3_options():
    """Multiple choice response with 3 options."""
    return """
## Option Analysis

Option A (status quo): Most likely given current trajectory
Option B (moderate change): Possible but requires specific catalysts
Option C (dramatic change): Unlikely without major disruptions

Probabilities: [55, 30, 15]
"""


@pytest.fixture
def mc_response_5_options():
    """Multiple choice response with 5 options."""
    return """
Analysis of all options:

Probabilities: [10, 25, 35, 20, 10]
"""


@pytest.fixture
def mc_response_with_decimals():
    """Multiple choice with decimal probabilities."""
    return "After analysis: Probabilities: [33.3, 33.3, 33.4]"


@pytest.fixture
def mc_response_wrong_count():
    """Multiple choice with wrong number of probabilities."""
    return "Probabilities: [50, 50]"  # Only 2 when 3 expected


@pytest.fixture
def mc_response_no_bracket():
    """Multiple choice without proper bracket format."""
    return "The probabilities are 40%, 35%, and 25%."


# ============================================================================
# Numeric Percentile Extraction Fixtures
# ============================================================================

@pytest.fixture
def numeric_response_standard():
    """Standard numeric response with percentile distribution."""
    return """
## Analysis

Based on historical data and current trends:

Distribution:
Percentile 1: 10
Percentile 5: 15
Percentile 10: 20
Percentile 20: 30
Percentile 40: 50
Percentile 60: 70
Percentile 80: 90
Percentile 90: 100
Percentile 95: 110
Percentile 99: 120
"""


@pytest.fixture
def numeric_response_with_bullets():
    """Numeric response with bullet points in distribution."""
    return """
Distribution:
• Percentile 1: 5
• Percentile 10: 10
• Percentile 50: 25
• Percentile 90: 40
• Percentile 99: 50
"""


@pytest.fixture
def numeric_response_colon_format():
    """Numeric response with simple colon format."""
    return """
Distribution:
1: 100
5: 150
10: 200
50: 500
90: 800
99: 1000
"""


@pytest.fixture
def numeric_response_dash_format():
    """Numeric response with dash separators."""
    return """
Distribution:
Percentile 1 - 5.5
Percentile 10 - 10.2
Percentile 50 - 25.7
Percentile 90 - 45.3
Percentile 99 - 60.1
"""


@pytest.fixture
def numeric_response_no_distribution():
    """Numeric response without Distribution: anchor."""
    return """
I think the value will be around 50, with a range of 30-70.
"""


@pytest.fixture
def numeric_response_non_monotonic():
    """Numeric response with non-monotonic values (needs fixing)."""
    return """
Distribution:
Percentile 1: 10
Percentile 10: 10
Percentile 50: 10
Percentile 90: 20
Percentile 99: 30
"""


# ============================================================================
# Config Fixtures
# ============================================================================

# ============================================================================
# Date Percentile Extraction Fixtures
# ============================================================================

@pytest.fixture
def date_response_standard():
    """Standard date response with YYYY-MM-DD format."""
    return """
## Analysis

Based on historical data and current trends for this date-based question:

Distribution:
Percentile 1: 2026-03-01
Percentile 5: 2026-04-15
Percentile 10: 2026-06-01
Percentile 50: 2026-09-15
Percentile 90: 2027-03-01
Percentile 99: 2027-12-31
"""


@pytest.fixture
def date_response_iso_format():
    """Date response with full ISO format (YYYY-MM-DDTHH:MM:SSZ)."""
    return """
Distribution:
Percentile 10: 2026-06-01T12:00:00Z
Percentile 50: 2026-09-15T00:00:00Z
Percentile 90: 2027-03-01T18:30:00Z
"""


@pytest.fixture
def date_response_mixed_format():
    """Date response with mixed date formats."""
    return """
Distribution:
Percentile 10: 2026-06-01
Percentile 50: 2026-09-15T12:00:00Z
Percentile 90: 2027-03-01
"""


@pytest.fixture
def date_response_no_distribution():
    """Date response without Distribution: anchor."""
    return """
I think the event will occur around mid-2026, possibly 2026-06-15.
"""


# ============================================================================
# Config Fixtures
# ============================================================================

@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        "mode": "test",
        "models": {
            "cheap": {
                "utility": "openrouter/anthropic/claude-3-5-haiku-latest",
                "summarization": "openrouter/anthropic/claude-3-5-haiku-latest",
            },
            "production": {
                "utility": "openrouter/anthropic/claude-sonnet-4-20250514",
                "summarization": "openrouter/anthropic/claude-sonnet-4-20250514",
            }
        },
        "ensemble": {
            "cheap": [
                {"name": "forecaster_1", "model": "openrouter/anthropic/claude-3-5-haiku-latest", "weight": 1.0},
                {"name": "forecaster_2", "model": "openrouter/anthropic/claude-3-5-haiku-latest", "weight": 1.0},
            ],
            "production": [
                {"name": "forecaster_1", "model": "openrouter/anthropic/claude-sonnet-4.5", "weight": 1.0},
                {"name": "forecaster_2", "model": "openrouter/openai/o3", "weight": 1.0},
            ]
        }
    }


@pytest.fixture
def sample_config_with_active():
    """Config with active_* keys already set (post mode application)."""
    return {
        "mode": "test",
        "active_models": {
            "utility": "openrouter/anthropic/claude-3-5-haiku-latest",
            "summarization": "openrouter/anthropic/claude-3-5-haiku-latest",
        },
        "active_agents": [
            {"name": "forecaster_1", "model": "openrouter/anthropic/claude-3-5-haiku-latest", "weight": 1.0},
        ],
        "should_submit": False,
    }


# ============================================================================
# Metaculus API Response Fixtures
# ============================================================================

@pytest.fixture
def binary_api_response():
    """Sample binary question API response."""
    return {
        "id": 12345,
        "title": "Will X happen by 2026?",
        "description": "This question asks whether X will happen.",
        "resolution_criteria": "Resolves YES if X occurs before Dec 31, 2026.",
        "fine_print": "Edge cases handled as follows...",
        "created_at": "2025-01-01T00:00:00Z",
        "open_time": "2025-01-01T00:00:00Z",
        "scheduled_close_time": "2026-12-31T00:00:00Z",
        "scheduled_resolve_time": "2027-01-15T00:00:00Z",
        "status": "open",
        "nr_forecasters": 42,
        "question": {
            "id": 67890,
            "type": "binary",
            "description": "Background info about the question.",
            "aggregations": {
                "recency_weighted": {
                    "history": [
                        {"centers": [0.65]}
                    ]
                }
            }
        },
    }


@pytest.fixture
def numeric_api_response():
    """Sample numeric question with bounds."""
    return {
        "id": 12346,
        "title": "How many X will there be?",
        "description": "This question asks for a numeric estimate.",
        "resolution_criteria": "Resolves to the official count.",
        "status": "open",
        "question": {
            "id": 67891,
            "type": "numeric",
            "description": "Background info.",
            "unit": "units",
            "scaling": {
                "range_min": 0,
                "range_max": 1000,
                "nominal_min": 100,
                "nominal_max": 500,
                "zero_point": None,
                "inbound_outcome_count": 200,
            },
            "open_lower_bound": True,
            "open_upper_bound": True,
        },
    }


@pytest.fixture
def discrete_api_response():
    """Sample discrete question (CDF size 102)."""
    return {
        "id": 12347,
        "title": "How many discrete events?",
        "description": "Count of discrete events.",
        "status": "open",
        "question": {
            "id": 67892,
            "type": "discrete",
            "description": "Background info.",
            "scaling": {
                "range_min": 0,
                "range_max": 100,
                "inbound_outcome_count": 101,
            },
            "open_lower_bound": False,
            "open_upper_bound": False,
        },
    }


@pytest.fixture
def date_api_response():
    """Sample date question with timestamp bounds."""
    return {
        "id": 12348,
        "title": "When will X happen?",
        "description": "This question asks for a date.",
        "status": "open",
        "question": {
            "id": 67893,
            "type": "date",
            "description": "Background info.",
            "scaling": {
                "range_min": 1767225600,  # 2026-01-01 UTC
                "range_max": 1798761600,  # 2027-01-01 UTC
                "inbound_outcome_count": 200,
            },
            "open_lower_bound": False,
            "open_upper_bound": True,
        },
    }


@pytest.fixture
def multiple_choice_api_response():
    """Sample multiple choice with options."""
    return {
        "id": 12349,
        "title": "Which option will occur?",
        "description": "Choose the most likely option.",
        "status": "open",
        "question": {
            "id": 67894,
            "type": "multiple_choice",
            "description": "Background info.",
            "options": [
                {"label": "Option A"},
                {"label": "Option B"},
                {"label": "Option C"},
            ],
        },
    }


@pytest.fixture
def unsupported_type_api_response():
    """API response with unsupported question type."""
    return {
        "id": 12350,
        "title": "Unsupported question",
        "question": {
            "id": 67895,
            "type": "conditional",  # Not supported
        },
    }


# ============================================================================
# Agent Result Fixtures
# ============================================================================

@pytest.fixture
def valid_agent_results():
    """List of 5 AgentResult objects with valid probabilities."""
    from src.bot.extractors import AgentResult
    return [
        AgentResult(
            agent_id=f"forecaster_{i+1}",
            model="test-model",
            weight=1.0,
            step1_output="Step 1 analysis...",
            step2_output="Step 2 analysis...",
            probability=50.0 + i * 5,  # 50, 55, 60, 65, 70
        )
        for i in range(5)
    ]


@pytest.fixture
def partial_agent_results():
    """List with 2 valid, 3 None probabilities."""
    from src.bot.extractors import AgentResult
    results = []
    for i in range(5):
        prob = 55.0 if i < 2 else None
        error = None if i < 2 else "Extraction failed"
        results.append(AgentResult(
            agent_id=f"forecaster_{i+1}",
            model="test-model",
            weight=1.0,
            step1_output="Step 1 analysis...",
            step2_output="Step 2 analysis..." if i < 2 else "",
            probability=prob,
            error=error,
        ))
    return results


@pytest.fixture
def all_failed_agent_results():
    """List where all 5 agents failed to extract probabilities."""
    from src.bot.extractors import AgentResult
    return [
        AgentResult(
            agent_id=f"forecaster_{i+1}",
            model="test-model",
            weight=1.0,
            step1_output="Step 1 analysis...",
            step2_output="",
            probability=None,
            error="Extraction failed",
        )
        for i in range(5)
    ]


# ============================================================================
# Search Query Fixtures
# ============================================================================

@pytest.fixture
def llm_search_queries_response():
    """LLM response with Search queries: block."""
    return '''
Based on my analysis of the question, I need to gather more information.

Search queries:
1. "climate change policy 2026" (Google)
2. "renewable energy news January 2026" (Google News)
3. "energy transition deep analysis trends" (Agent)
'''


@pytest.fixture
def llm_search_queries_with_asknews():
    """LLM response including AskNews query for deep research."""
    return '''
I'll search for relevant information.

Search queries:
1. "policy update 2026" (Google)
2. "What are the latest developments in renewable energy policy?" (AskNews)
'''


@pytest.fixture
def llm_search_queries_empty():
    """LLM response with no search queries block."""
    return '''
I have enough information from the provided context to make my forecast.
No additional research is needed.
'''


@pytest.fixture
def llm_search_queries_malformed():
    """LLM response with malformed search queries."""
    return '''
Search queries:
1. Some query without parentheses
2. Another query (unknown source)
3. "valid query" (Google)
'''
