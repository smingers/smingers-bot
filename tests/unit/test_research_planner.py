"""
Tests for the Iterative Research Planner.

Tests cover:
- Query parsing (tagged and fallback)
- Context assembly (temporal partitioning, seed prepending, stock return injection)
- Prompt formatting (type-specific fields)
- Reflection parsing (SUFFICIENT vs GAPS_FOUND)
- Helper methods (days to resolution, type-specific fields)
"""

import pytest

from src.bot.research_planner import (
    _TAGGED_QUERY_PATTERN,
    IterativeResearchPlanner,
    QueryResult,
    ResearchQuery,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def base_config():
    """Minimal config for planner tests."""
    return {
        "research": {
            "iterative_planner_enabled": True,
            "planner": {
                "max_plan_queries": 10,
                "max_gap_queries": 3,
                "reflection_enabled": True,
            },
            "google_enabled": True,
            "asknews_enabled": True,
            "agentic_search_enabled": True,
            "fred_enabled": True,
            "yfinance_enabled": True,
            "google_trends_enabled": True,
        },
        "llm": {
            "temperature": {
                "research_planning": 0.3,
                "research_reflection": 0.2,
            },
            "max_output_tokens": 5000,
        },
        "active_models": {
            "query_generator": "test-model",
        },
    }


@pytest.fixture
def planner(base_config):
    """Planner instance with no LLM or artifact store (for unit testing parsers)."""
    return IterativeResearchPlanner(
        config=base_config,
        llm_client=None,  # Not needed for parsing tests
        artifact_store=None,
    )


@pytest.fixture
def sample_plan_response():
    """A well-formed research plan LLM response."""
    return """Analysis:
This question asks about the probability of a specific economic event. The pre-research
context from the question URLs provides the resolution criteria and data source.
We need base rate data, current metric values, and driver analysis.

Search queries:
1. [HISTORICAL] US unemployment rate 2020-2025 (Google) -- Intent: Historical base rate for labor market metric
2. [HISTORICAL] Federal Reserve unemployment projections 2026. What are the latest FOMC projections for unemployment, and how have past projections compared to outcomes? (Agent) -- Intent: Expert forecasts and calibration
3. [CURRENT] unemployment claims February 2026 (Google News) -- Intent: Latest weekly data
4. [CURRENT] US labor market outlook recession risk factors in early 2026, including consumer spending, manufacturing indices, and Fed policy signals (AskNews) -- Intent: Broader driver analysis
5. [HISTORICAL] UNRATE (FRED) -- Intent: Retrieve unemployment time series with statistics
6. [CURRENT] BLS jobs report February 2026 (Google News) -- Intent: Most recent employment data release
7. [HISTORICAL] recession probability indicators (Google) -- Intent: Contrarian check on downturn scenario
"""


@pytest.fixture
def sample_reflect_response_sufficient():
    """Reflection response indicating sufficient coverage."""
    return """Analysis:
1. Base rate: COVERED — We have 5-year historical FRED data and FOMC projections.
2. Resolution mechanism: COVERED — BLS data for Feb 2026 is available.
3. Key drivers: COVERED — Consumer spending, Fed policy, and manufacturing data covered.
4. Current state: COVERED — Latest weekly claims and jobs report found.
5. Contrarian: COVERED — Recession probability indicators provide downside scenario.

Coverage: SUFFICIENT
"""


@pytest.fixture
def sample_reflect_response_gaps():
    """Reflection response indicating gaps that need filling."""
    return """Analysis:
1. Base rate: COVERED — Historical FRED data provides good baseline.
2. Resolution mechanism: GAP — We don't have the most recent BLS release with actual numbers.
3. Key drivers: COVERED — Multiple driver sources found.
4. Current state: GAP — News results are from 2 weeks ago, nothing in last 7 days.
5. Contrarian: COVERED — Recession indicators covered.

Coverage: GAPS_FOUND

Search queries:
1. [CURRENT] BLS employment situation February 2026 (Google) -- Intent: Latest official release
2. [CURRENT] US economy latest developments this week (Google News) -- Intent: Fill 7-day news gap
"""


# =============================================================================
# Query Parsing Tests
# =============================================================================


class TestParseTaggedQueries:
    """Tests for _parse_tagged_queries method."""

    def test_parses_well_formed_queries(self, planner, sample_plan_response):
        queries = planner._parse_tagged_queries(sample_plan_response, phase="plan")
        assert len(queries) == 7

    def test_parses_temporal_roles(self, planner, sample_plan_response):
        queries = planner._parse_tagged_queries(sample_plan_response, phase="plan")
        historical = [q for q in queries if q.temporal_role == "historical"]
        current = [q for q in queries if q.temporal_role == "current"]
        assert len(historical) == 4
        assert len(current) == 3

    def test_parses_tools_correctly(self, planner, sample_plan_response):
        queries = planner._parse_tagged_queries(sample_plan_response, phase="plan")
        tools = [q.tool for q in queries]
        assert "Google" in tools
        assert "Google News" in tools
        assert "Agent" in tools
        assert "AskNews" in tools
        assert "FRED" in tools

    def test_parses_intent(self, planner, sample_plan_response):
        queries = planner._parse_tagged_queries(sample_plan_response, phase="plan")
        # First query should have intent
        assert queries[0].intent != ""
        assert "base rate" in queries[0].intent.lower()

    def test_sets_phase(self, planner, sample_plan_response):
        queries = planner._parse_tagged_queries(sample_plan_response, phase="reflect")
        for q in queries:
            assert q.phase == "reflect"

    def test_empty_response(self, planner):
        queries = planner._parse_tagged_queries("No queries here", phase="plan")
        assert len(queries) == 0

    def test_no_search_queries_section(self, planner):
        response = "Analysis:\nSome analysis text without a search queries section."
        queries = planner._parse_tagged_queries(response, phase="plan")
        assert len(queries) == 0

    def test_strips_quotes_from_query(self, planner):
        response = """Search queries:
1. [HISTORICAL] "US GDP growth rate" (Google) -- Intent: test
"""
        queries = planner._parse_tagged_queries(response, phase="plan")
        assert len(queries) == 1
        assert queries[0].query == "US GDP growth rate"

    def test_handles_all_tool_types(self, planner):
        response = """Search queries:
1. [HISTORICAL] test query (Google) -- Intent: test
2. [CURRENT] test query (Google News) -- Intent: test
3. [HISTORICAL] detailed multi-part query (Agent) -- Intent: test
4. [CURRENT] semantic news query (AskNews) -- Intent: test
5. [HISTORICAL] UNRATE (FRED) -- Intent: test
6. [HISTORICAL] AAPL (yFinance) -- Intent: test
7. [HISTORICAL] hospital (Google Trends) -- Intent: test
"""
        queries = planner._parse_tagged_queries(response, phase="plan")
        assert len(queries) == 7
        tools = {q.tool for q in queries}
        assert tools == {
            "Google",
            "Google News",
            "Agent",
            "AskNews",
            "FRED",
            "yFinance",
            "Google Trends",
        }

    def test_query_without_intent(self, planner):
        response = """Search queries:
1. [HISTORICAL] US unemployment rate (Google)
2. [CURRENT] latest jobs report (Google News) -- Intent: recent data
"""
        queries = planner._parse_tagged_queries(response, phase="plan")
        assert len(queries) == 2
        assert queries[0].intent == ""
        assert queries[1].intent == "recent data"


class TestParseUntaggedFallback:
    """Tests for _parse_untagged_queries_fallback method."""

    def test_parses_legacy_format(self, planner):
        response = """Search queries:
1. US unemployment rate history (Google)
2. latest jobs data 2026 (Google News)
3. detailed analysis of labor market (Agent)
"""
        queries = planner._parse_untagged_queries_fallback(response)
        assert len(queries) == 3

    def test_assigns_temporal_roles_heuristically(self, planner):
        response = """Search queries:
1. query one (Google)
2. query two (Google News)
3. query three (Agent)
4. query four (AskNews)
5. query five (Google)
"""
        queries = planner._parse_untagged_queries_fallback(response)
        # First ~60% should be historical, rest current
        assert queries[0].temporal_role == "historical"
        assert queries[1].temporal_role == "historical"
        assert queries[2].temporal_role == "historical"
        # AskNews always forced to current
        assert queries[3].temporal_role == "current"

    def test_empty_response(self, planner):
        queries = planner._parse_untagged_queries_fallback("No queries")
        assert len(queries) == 0


# =============================================================================
# Context Assembly Tests
# =============================================================================


class TestAssembleContexts:
    """Tests for _assemble_contexts method."""

    def test_partitions_by_temporal_role(self, planner):
        results = [
            QueryResult(
                query=ResearchQuery("q1", "Google", "historical", "test"),
                formatted_output="<Summary>historical result 1</Summary>",
                success=True,
            ),
            QueryResult(
                query=ResearchQuery("q2", "Google News", "current", "test"),
                formatted_output="<Summary>current result 1</Summary>",
                success=True,
            ),
            QueryResult(
                query=ResearchQuery("q3", "FRED", "historical", "test"),
                formatted_output="<FREDData>historical result 2</FREDData>",
                success=True,
            ),
        ]
        hist, curr = planner._assemble_contexts("", results, {})
        assert "historical result 1" in hist
        assert "historical result 2" in hist
        assert "current result 1" in curr
        assert "current result 1" not in hist
        assert "historical result 1" not in curr

    def test_prepends_seed_context(self, planner):
        results = [
            QueryResult(
                query=ResearchQuery("q1", "Google", "historical", "test"),
                formatted_output="<Summary>search result</Summary>",
                success=True,
            ),
        ]
        seed = "<QuestionSource>resolution data</QuestionSource>"
        hist, _curr = planner._assemble_contexts(seed, results, {})
        # Seed context should come first
        assert hist.index("resolution data") < hist.index("search result")

    def test_prepends_stock_return_context(self, planner):
        results = [
            QueryResult(
                query=ResearchQuery("q1", "Google", "historical", "test"),
                formatted_output="<Summary>hist</Summary>",
                success=True,
            ),
            QueryResult(
                query=ResearchQuery("q2", "Google News", "current", "test"),
                formatted_output="<Summary>curr</Summary>",
                success=True,
            ),
        ]
        params = {"stock_return_context": "STOCK_RETURN_DATA"}
        hist, curr = planner._assemble_contexts("", results, params)
        assert hist.startswith("STOCK_RETURN_DATA")
        assert curr.startswith("STOCK_RETURN_DATA")

    def test_empty_results(self, planner):
        hist, curr = planner._assemble_contexts("seed", [], {})
        assert "seed" in hist
        assert curr == ""

    def test_skips_empty_output(self, planner):
        results = [
            QueryResult(
                query=ResearchQuery("q1", "Google", "historical", "test"),
                formatted_output="",
                success=False,
            ),
            QueryResult(
                query=ResearchQuery("q2", "Google", "historical", "test"),
                formatted_output="<Summary>real content</Summary>",
                success=True,
            ),
        ]
        hist, _curr = planner._assemble_contexts("", results, {})
        assert "real content" in hist


# =============================================================================
# Reflection Parsing Tests
# =============================================================================


class TestReflectionParsing:
    """Tests for parsing reflection responses."""

    def test_parses_sufficient_coverage(self, planner, sample_reflect_response_sufficient):
        import re

        assert re.search(
            r"Coverage:\s*SUFFICIENT",
            sample_reflect_response_sufficient,
            re.IGNORECASE,
        )

    def test_parses_gaps_found(self, planner, sample_reflect_response_gaps):
        queries = planner._parse_tagged_queries(sample_reflect_response_gaps, phase="reflect")
        assert len(queries) == 2
        assert all(q.temporal_role == "current" for q in queries)
        assert all(q.phase == "reflect" for q in queries)


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestHelperMethods:
    """Tests for helper methods."""

    def test_compute_days_to_resolution(self, planner):
        params = {
            "today": "2026-02-26",
            "scheduled_resolve_time": "2026-03-15T00:00:00Z",
        }
        days = planner._compute_days_to_resolution(params)
        assert days == "17"

    def test_compute_days_to_resolution_past(self, planner):
        params = {
            "today": "2026-03-20",
            "scheduled_resolve_time": "2026-03-15",
        }
        days = planner._compute_days_to_resolution(params)
        assert days == "0"

    def test_compute_days_to_resolution_missing(self, planner):
        params = {"today": "2026-02-26"}
        days = planner._compute_days_to_resolution(params)
        assert days == "unknown"

    def test_build_type_specific_fields_binary(self, planner):
        fields = planner._build_type_specific_fields("binary", {})
        assert fields == ""

    def test_build_type_specific_fields_numeric(self, planner):
        params = {"units": "percent", "bounds_info": "Range: 0 to 100"}
        fields = planner._build_type_specific_fields("numeric", params)
        assert "Units: percent" in fields
        assert "Bounds: Range: 0 to 100" in fields

    def test_build_type_specific_fields_mc(self, planner):
        params = {"options": "Option A, Option B, Option C"}
        fields = planner._build_type_specific_fields("multiple_choice", params)
        assert "Options: Option A, Option B, Option C" in fields

    def test_extract_analysis(self, planner):
        response = """Analysis:
This is the analysis section with multiple lines.
It covers various aspects of the question.

Search queries:
1. [HISTORICAL] test (Google)
"""
        analysis = planner._extract_analysis(response)
        assert "analysis section" in analysis
        assert "Search queries" not in analysis

    def test_extract_analysis_with_coverage(self, planner):
        response = """Analysis:
Coverage evaluation text.

Coverage: SUFFICIENT
"""
        analysis = planner._extract_analysis(response)
        assert "Coverage evaluation" in analysis
        assert "SUFFICIENT" not in analysis

    def test_is_reflection_enabled(self, planner):
        assert planner._is_reflection_enabled() is True

    def test_is_reflection_disabled(self, base_config):
        base_config["research"]["planner"]["reflection_enabled"] = False
        p = IterativeResearchPlanner(base_config, None)
        assert p._is_reflection_enabled() is False

    def test_build_available_tools_all_enabled(self, planner):
        tools_text = planner._build_available_tools()
        assert "Google:" in tools_text
        assert "Google News:" in tools_text
        assert "Agent:" in tools_text
        assert "AskNews:" in tools_text
        assert "FRED:" in tools_text
        assert "yFinance:" in tools_text
        assert "Google Trends:" in tools_text

    def test_build_available_tools_some_disabled(self, base_config):
        base_config["research"]["asknews_enabled"] = False
        base_config["research"]["fred_enabled"] = False
        p = IterativeResearchPlanner(base_config, None)
        tools_text = p._build_available_tools()
        assert "Google:" in tools_text
        assert "Agent:" in tools_text
        assert "AskNews:" not in tools_text
        assert "FRED:" not in tools_text
        assert "yFinance:" in tools_text

    def test_build_available_tools_only_google(self, base_config):
        base_config["research"]["agentic_search_enabled"] = False
        base_config["research"]["asknews_enabled"] = False
        base_config["research"]["fred_enabled"] = False
        base_config["research"]["yfinance_enabled"] = False
        base_config["research"]["google_trends_enabled"] = False
        p = IterativeResearchPlanner(base_config, None)
        tools_text = p._build_available_tools()
        assert "Google:" in tools_text
        assert "Google News:" in tools_text
        assert "Agent:" not in tools_text
        assert "AskNews:" not in tools_text


# =============================================================================
# Results Summary Tests
# =============================================================================


class TestBuildResultsSummary:
    """Tests for _build_results_summary method."""

    def test_builds_summary_with_truncation(self, planner):
        long_content = "x" * 1000
        results = [
            QueryResult(
                query=ResearchQuery("q1", "Google", "historical", "test intent"),
                formatted_output=long_content,
                success=True,
            ),
        ]
        summary = planner._build_results_summary(results, max_chars_per_result=100)
        assert "[truncated]" in summary
        assert len(summary) < len(long_content)

    def test_includes_query_metadata(self, planner):
        results = [
            QueryResult(
                query=ResearchQuery("unemployment data", "FRED", "historical", "base rate"),
                formatted_output="<FREDData>data here</FREDData>",
                success=True,
            ),
        ]
        summary = planner._build_results_summary(results)
        assert "HISTORICAL" in summary
        assert "unemployment data" in summary
        assert "FRED" in summary
        assert "SUCCESS" in summary

    def test_shows_error_for_failed_queries(self, planner):
        results = [
            QueryResult(
                query=ResearchQuery("bad query", "Google", "current", "test"),
                formatted_output="",
                success=False,
                error="API timeout",
            ),
        ]
        summary = planner._build_results_summary(results)
        assert "FAILED" in summary
        assert "API timeout" in summary


# =============================================================================
# Error Output Formatting Tests
# =============================================================================


class TestFormatErrorOutput:
    """Tests for _format_error_output method."""

    def test_google_error_format(self, planner):
        rq = ResearchQuery("test query", "Google", "historical", "test")
        output = planner._format_error_output(rq, Exception("timeout"))
        assert "<Summary" in output
        assert "timeout" in output

    def test_agent_error_format(self, planner):
        rq = ResearchQuery("test query", "Agent", "historical", "test")
        output = planner._format_error_output(rq, Exception("model error"))
        assert "<Agent_report>" in output
        assert "model error" in output

    def test_asknews_error_format(self, planner):
        rq = ResearchQuery("test query", "AskNews", "current", "test")
        output = planner._format_error_output(rq, Exception("rate limit"))
        assert "<Asknews_articles>" in output
        assert "rate limit" in output

    def test_fred_error_format(self, planner):
        rq = ResearchQuery("UNRATE", "FRED", "historical", "test")
        output = planner._format_error_output(rq, Exception("series not found"))
        assert "<FREDData" in output

    def test_yfinance_error_format(self, planner):
        rq = ResearchQuery("AAPL", "yFinance", "historical", "test")
        output = planner._format_error_output(rq, Exception("ticker invalid"))
        assert "<YFinanceData" in output

    def test_google_trends_error_format(self, planner):
        rq = ResearchQuery("hospital", "Google Trends", "historical", "test")
        output = planner._format_error_output(rq, Exception("no data"))
        assert "<GoogleTrendsData" in output


# =============================================================================
# Regex Pattern Tests
# =============================================================================


class TestTaggedQueryRegex:
    """Direct tests for the compiled regex pattern."""

    def test_basic_match(self):
        line = "1. [HISTORICAL] US unemployment rate (Google) -- Intent: base rate"
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "HISTORICAL"
        assert match.group(2).strip() == "US unemployment rate"
        assert match.group(3) == "Google"
        assert match.group(4).strip() == "base rate"

    def test_current_tag(self):
        line = "3. [CURRENT] latest news about topic (Google News) -- Intent: recent events"
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "CURRENT"
        assert match.group(3) == "Google News"

    def test_no_intent(self):
        line = "2. [HISTORICAL] UNRATE (FRED)"
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "HISTORICAL"
        assert match.group(2).strip() == "UNRATE"
        assert match.group(3) == "FRED"

    def test_agent_with_long_query(self):
        line = (
            "4. [HISTORICAL] What is the historical base rate of unemployment exceeding 5% "
            "within a 3-month window? Compare FOMC projections to actual outcomes. (Agent) "
            "-- Intent: base rate computation"
        )
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(3) == "Agent"
        assert "base rate" in match.group(2)

    def test_asknews_semantic_query(self):
        line = (
            "5. [CURRENT] Recent developments in US labor market conditions including "
            "weekly jobless claims trends and employer hiring sentiment (AskNews) "
            "-- Intent: broad current context"
        )
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(3) == "AskNews"

    def test_no_match_without_tag(self):
        line = "1. US unemployment rate (Google) -- Intent: test"
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is None

    def test_yfinance_ticker(self):
        line = "6. [HISTORICAL] ^GSPC (yFinance) -- Intent: S&P 500 data"
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(2).strip() == "^GSPC"
        assert match.group(3) == "yFinance"

    def test_google_trends(self):
        line = "7. [HISTORICAL] hospital (Google Trends) -- Intent: search trend data"
        match = _TAGGED_QUERY_PATTERN.search(line)
        assert match is not None
        assert match.group(3) == "Google Trends"
