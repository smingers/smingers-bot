"""Tests for supervisor agent logic."""

from src.bot.supervisor import SupervisorAgent, SupervisorInput, SupervisorResult

# =============================================================================
# SupervisorInput Construction
# =============================================================================


def _make_input(**kwargs) -> SupervisorInput:
    """Create a SupervisorInput with sensible defaults."""
    defaults = {
        "question_title": "Will X happen before 2026?",
        "question_type": "binary",
        "resolution_criteria": "Resolves YES if X happens.",
        "fine_print": "",
        "background": "Background context.",
        "open_time": "2025-01-01",
        "scheduled_resolve_time": "2026-12-31",
        "today": "2026-02-13",
        "forecaster_predictions": [
            {
                "agent_id": f"forecaster_{i}",
                "model": f"model_{i}",
                "prediction": p,
                "reasoning": f"Reasoning for forecaster {i}",
            }
            for i, p in enumerate([20.0, 40.0, 60.0, 30.0, 50.0], 1)
        ],
        "weighted_average_prediction": 0.40,
    }
    defaults.update(kwargs)
    return SupervisorInput(**defaults)


# =============================================================================
# Formatting Tests
# =============================================================================


class TestFormatting:
    def test_format_forecaster_summaries(self):
        """Forecaster summaries should include all predictions."""
        agent = SupervisorAgent(config={})
        si = _make_input()
        result = agent._format_forecaster_summaries(si)

        assert "forecaster_1" in result
        assert "forecaster_5" in result
        assert "20.0%" in result
        assert "60.0%" in result

    def test_format_forecaster_summaries_truncates_reasoning(self):
        """Long reasoning should be truncated."""
        agent = SupervisorAgent(config={})
        si = _make_input(
            forecaster_predictions=[
                {
                    "agent_id": "forecaster_1",
                    "model": "test",
                    "prediction": 50.0,
                    "reasoning": "x" * 5000,
                }
            ]
        )
        result = agent._format_forecaster_summaries(si)
        # Truncated to ~2000 chars + prefix
        assert len(result) < 3000

    def test_format_weighted_average_binary(self):
        """Binary weighted average should display as percentage."""
        agent = SupervisorAgent(config={})
        si = _make_input(weighted_average_prediction=0.35)
        result = agent._format_weighted_average(si)
        assert "35.0%" in result

    def test_format_weighted_average_mc(self):
        """MC weighted average should display as list."""
        agent = SupervisorAgent(config={})
        si = _make_input(
            question_type="multiple_choice",
            weighted_average_prediction=[0.6, 0.3, 0.1],
        )
        result = agent._format_weighted_average(si)
        assert "60.0%" in result

    def test_format_type_specific_numeric(self):
        """Numeric section should include units and bounds."""
        agent = SupervisorAgent(config={})
        si = _make_input(
            question_type="numeric",
            units="USD",
            bounds_info="[0, 1000000]",
        )
        result = agent._format_type_specific_section(si)
        assert "USD" in result
        assert "[0, 1000000]" in result

    def test_format_type_specific_mc(self):
        """MC section should include options."""
        agent = SupervisorAgent(config={})
        si = _make_input(
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C"],
        )
        result = agent._format_type_specific_section(si)
        assert "Option A" in result

    def test_format_single_prediction_none(self):
        """None prediction should display as extraction failed."""
        agent = SupervisorAgent(config={})
        result = agent._format_single_prediction(None, "binary")
        assert "extraction failed" in result


# =============================================================================
# Extraction Tests
# =============================================================================


class TestExtraction:
    def test_extract_confidence_high(self):
        agent = SupervisorAgent(config={})
        text = "Some analysis.\n\nConfidence: HIGH\n\nProbability: 45%"
        assert agent._extract_confidence(text) == "high"

    def test_extract_confidence_medium(self):
        agent = SupervisorAgent(config={})
        text = "Analysis.\nConfidence: MEDIUM\nProbability: 30%"
        assert agent._extract_confidence(text) == "medium"

    def test_extract_confidence_low(self):
        agent = SupervisorAgent(config={})
        text = "Analysis.\nConfidence: LOW\nProbability: 50%"
        assert agent._extract_confidence(text) == "low"

    def test_extract_confidence_missing(self):
        """Missing confidence should default to low."""
        agent = SupervisorAgent(config={})
        text = "Some text without confidence level.\nProbability: 50%"
        assert agent._extract_confidence(text) == "low"

    def test_extract_confidence_case_insensitive(self):
        agent = SupervisorAgent(config={})
        text = "Confidence: high"
        assert agent._extract_confidence(text) == "high"

    def test_extract_search_queries(self):
        """Should extract queries with source tags."""
        agent = SupervisorAgent(config={})
        text = """
Disagreement Analysis:
Forecasters disagree about X.

Search queries:
1. US Iran negotiations February 2026 (Google)
2. Iran nuclear deal latest news (Google News)
3. What is the current status of US-Iran diplomatic negotiations as of February 2026? (Agent)
"""
        queries = agent._extract_search_queries(text)
        assert len(queries) == 3
        assert "(Google)" in queries[0]
        assert "(Google News)" in queries[1]
        assert "(Agent)" in queries[2]

    def test_extract_search_queries_empty(self):
        """No search queries section should return empty list."""
        agent = SupervisorAgent(config={})
        text = "Analysis without any search queries section."
        queries = agent._extract_search_queries(text)
        assert queries == []

    def test_extract_search_queries_respects_max(self):
        """Should respect max_search_queries limit."""
        agent = SupervisorAgent(config={"supervisor": {"max_search_queries": 2}})
        text = """
Search queries:
1. query one (Google)
2. query two (Google News)
3. query three (Agent)
4. query four (Google)
"""
        queries = agent._extract_search_queries(text)
        assert len(queries) == 2

    def test_extract_binary_prediction(self):
        """Should extract binary probability from supervisor output."""
        agent = SupervisorAgent(config={})
        si = _make_input()
        text = "Updated Analysis: ...\n\nConfidence: HIGH\n\nProbability: 45%"
        result = agent._extract_prediction(text, si)
        assert result == 45.0

    def test_extract_mc_prediction(self):
        """Should extract MC probabilities from supervisor output."""
        agent = SupervisorAgent(config={})
        si = _make_input(
            question_type="multiple_choice",
            options=["A", "B", "C"],
            num_options=3,
        )
        text = "Analysis.\n\nConfidence: HIGH\n\nProbabilities: [60, 30, 10]"
        result = agent._extract_prediction(text, si)
        assert len(result) == 3
        assert result[0] == 60.0

    def test_extract_numeric_prediction(self):
        """Should extract percentiles from supervisor output."""
        agent = SupervisorAgent(config={})
        si = _make_input(question_type="numeric")
        text = """Analysis.

Confidence: HIGH

Percentile 10: 100
Percentile 20: 200
Percentile 40: 400
Percentile 60: 600
Percentile 80: 800
Percentile 90: 900
"""
        result = agent._extract_prediction(text, si)
        assert isinstance(result, dict)
        assert result[10] == 100
        assert result[90] == 900


# =============================================================================
# Model Resolution Tests
# =============================================================================


class TestModelResolution:
    def test_default_model(self):
        """Should use default model when no config."""
        agent = SupervisorAgent(config={})
        assert "claude-opus-4.6" in agent.model

    def test_config_model(self):
        """Should use model from config."""
        agent = SupervisorAgent(config={"supervisor": {"model": {"quality": "my-model"}}})
        assert agent.model == "my-model"

    def test_active_models_override(self):
        """Active models should override config."""
        agent = SupervisorAgent(
            config={
                "supervisor": {"model": {"quality": "config-model"}},
                "active_models": {"supervisor": "active-model"},
            }
        )
        assert agent.model == "active-model"

    def test_temperature_from_config(self):
        """Should use temperature from config."""
        agent = SupervisorAgent(config={"supervisor": {"temperature": 0.5}})
        assert agent.temperature == 0.5

    def test_default_temperature(self):
        """Should use default temperature."""
        agent = SupervisorAgent(config={})
        assert agent.temperature == 0.3


# =============================================================================
# SupervisorResult Tests
# =============================================================================


class TestSupervisorResult:
    def test_should_override_high(self):
        result = SupervisorResult(
            confidence="high",
            updated_prediction=0.45,
            reasoning="test",
            search_queries=[],
            search_context="",
            disagreement_analysis="",
            should_override=True,
        )
        assert result.should_override

    def test_should_not_override_medium(self):
        result = SupervisorResult(
            confidence="medium",
            updated_prediction=0.45,
            reasoning="test",
            search_queries=[],
            search_context="",
            disagreement_analysis="",
            should_override=False,
        )
        assert not result.should_override

    def test_should_not_override_low(self):
        result = SupervisorResult(
            confidence="low",
            updated_prediction=0.45,
            reasoning="test",
            search_queries=[],
            search_context="",
            disagreement_analysis="",
            should_override=False,
        )
        assert not result.should_override


# =============================================================================
# Prompt Template Tests
# =============================================================================


class TestPromptTemplates:
    def test_get_binary_prompt(self):
        agent = SupervisorAgent(config={})
        template = agent._get_update_prompt_template("binary")
        assert "Probability: ZZ%" in template

    def test_get_numeric_prompt(self):
        agent = SupervisorAgent(config={})
        template = agent._get_update_prompt_template("numeric")
        assert "Percentile 10" in template

    def test_get_mc_prompt(self):
        agent = SupervisorAgent(config={})
        template = agent._get_update_prompt_template("multiple_choice")
        assert "Probabilities:" in template

    def test_unknown_type_falls_back_to_binary(self):
        agent = SupervisorAgent(config={})
        template = agent._get_update_prompt_template("unknown")
        assert "Probability: ZZ%" in template
