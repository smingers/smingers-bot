"""
Tests for prompt template formatting methods.

These tests verify that format methods don't raise KeyError due to mismatches
between what _get_bounds_explanation() returns and what prompt templates expect.

Also tests that unsupported question types raise QuestionTypeError.
"""

import pytest

from src.bot.binary import BinaryForecaster
from src.bot.exceptions import QuestionTypeError
from src.bot.multiple_choice import MultipleChoiceForecaster
from src.bot.numeric import NumericForecaster
from src.bot.prompts import (
    BINARY_PROMPT_1,
    BINARY_PROMPT_2,
    BINARY_PROMPT_CURRENT,
    BINARY_PROMPT_HISTORICAL,
    MULTIPLE_CHOICE_PROMPT_1,
    MULTIPLE_CHOICE_PROMPT_2,
    MULTIPLE_CHOICE_PROMPT_CURRENT,
    MULTIPLE_CHOICE_PROMPT_HISTORICAL,
    NUMERIC_PROMPT_1,
    NUMERIC_PROMPT_2,
    NUMERIC_PROMPT_CURRENT,
    NUMERIC_PROMPT_HISTORICAL,
)

# ============================================================================
# Test Fixtures - Minimal valid inputs for format methods
# ============================================================================


@pytest.fixture
def minimal_config():
    """Minimal config for instantiating forecasters (no LLM calls needed)."""
    return {
        "mode": "test",
        "_active_models": {
            "utility": "openrouter/anthropic/claude-3-5-haiku-latest",
            "summarization": "openrouter/anthropic/claude-3-5-haiku-latest",
        },
        "_active_agents": [
            {
                "name": "forecaster_1",
                "model": "openrouter/anthropic/claude-3-5-haiku-latest",
                "weight": 1.0,
            },
        ],
        "_should_submit": False,
    }


@pytest.fixture
def base_question_params():
    """Base question parameters shared across all question types."""
    return {
        "question_title": "Test Question Title",
        "question_text": "Test question text/background",
        "background_info": "Additional background information",
        "resolution_criteria": "Resolves YES if X happens by Y date",
        "fine_print": "Additional fine print details",
        "open_time": "2026-01-01",
        "scheduled_resolve_time": "2026-12-31",
        "today": "2026-02-01",
    }


@pytest.fixture
def numeric_question_params(base_question_params):
    """Parameters for numeric questions."""
    return {
        **base_question_params,
        "unit_of_measure": "USD",
        "open_lower_bound": True,
        "open_upper_bound": True,
        "lower_bound": 0,
        "upper_bound": 100,
        "zero_point": None,
    }


@pytest.fixture
def discrete_question_params(numeric_question_params):
    """Parameters for discrete questions (smaller CDF)."""
    return {
        **numeric_question_params,
        "cdf_size": 102,
    }


@pytest.fixture
def date_question_params(base_question_params):
    """Parameters for date questions."""
    return {
        **base_question_params,
        "unit_of_measure": "date",
        "open_lower_bound": False,
        "open_upper_bound": True,
        "lower_bound": 1704067200.0,  # 2024-01-01 timestamp
        "upper_bound": 1893456000.0,  # 2030-01-01 timestamp
        "is_date_question": True,
        "cdf_size": 201,
    }


@pytest.fixture
def mc_question_params(base_question_params):
    """Parameters for multiple choice questions."""
    return {
        **base_question_params,
        "options": ["Option A", "Option B", "Option C"],
    }


# ============================================================================
# Binary Forecaster Tests
# ============================================================================


class TestBinaryFormatMethods:
    """Tests for BinaryForecaster format methods."""

    def test_binary_format_query_prompts_no_keyerror(self, minimal_config, base_question_params):
        """Verify _format_query_prompts() doesn't raise KeyError."""
        forecaster = BinaryForecaster(minimal_config)

        historical, current = forecaster._format_query_prompts(
            BINARY_PROMPT_HISTORICAL,
            BINARY_PROMPT_CURRENT,
            **base_question_params,
        )

        assert isinstance(historical, str)
        assert isinstance(current, str)
        assert len(historical) > 0
        assert len(current) > 0

    def test_binary_format_step1_prompt_no_keyerror(self, minimal_config, base_question_params):
        """Verify _format_step1_prompt() doesn't raise KeyError."""
        forecaster = BinaryForecaster(minimal_config)

        result = forecaster._format_step1_prompt(
            BINARY_PROMPT_1,
            historical_context="Some historical context from search",
            **base_question_params,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_binary_format_step2_prompt_no_keyerror(self, minimal_config, base_question_params):
        """Verify _format_step2_prompt() doesn't raise KeyError."""
        forecaster = BinaryForecaster(minimal_config)

        result = forecaster._format_step2_prompt(
            BINARY_PROMPT_2,
            context="Cross-pollinated context with current news",
            **base_question_params,
        )

        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# Numeric Forecaster Tests
# ============================================================================


class TestNumericFormatMethods:
    """Tests for NumericForecaster format methods (numeric, discrete, date)."""

    def test_numeric_format_query_prompts_no_keyerror(
        self, minimal_config, numeric_question_params
    ):
        """Verify _format_query_prompts() doesn't raise KeyError for numeric questions."""
        forecaster = NumericForecaster(minimal_config)

        historical, current = forecaster._format_query_prompts(
            NUMERIC_PROMPT_HISTORICAL,
            NUMERIC_PROMPT_CURRENT,
            **numeric_question_params,
        )

        assert isinstance(historical, str)
        assert isinstance(current, str)
        assert "bounds" in historical.lower() or "bound" in historical.lower()

    def test_numeric_format_step1_prompt_no_keyerror(self, minimal_config, numeric_question_params):
        """Verify _format_step1_prompt() doesn't raise KeyError for numeric questions."""
        forecaster = NumericForecaster(minimal_config)

        result = forecaster._format_step1_prompt(
            NUMERIC_PROMPT_1,
            historical_context="Historical research context",
            **numeric_question_params,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_numeric_format_step2_prompt_no_keyerror(self, minimal_config, numeric_question_params):
        """Verify _format_step2_prompt() doesn't raise KeyError for numeric questions."""
        forecaster = NumericForecaster(minimal_config)

        result = forecaster._format_step2_prompt(
            NUMERIC_PROMPT_2,
            context="Cross-pollinated context",
            **numeric_question_params,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_discrete_format_prompts_no_keyerror(self, minimal_config, discrete_question_params):
        """Verify format methods work for discrete questions (cdf_size=102)."""
        forecaster = NumericForecaster(minimal_config)

        # Query prompts
        historical, current = forecaster._format_query_prompts(
            NUMERIC_PROMPT_HISTORICAL,
            NUMERIC_PROMPT_CURRENT,
            **discrete_question_params,
        )
        assert isinstance(historical, str)
        assert isinstance(current, str)

        # Step 1
        step1 = forecaster._format_step1_prompt(
            NUMERIC_PROMPT_1,
            historical_context="Historical context",
            **discrete_question_params,
        )
        assert isinstance(step1, str)

        # Step 2
        step2 = forecaster._format_step2_prompt(
            NUMERIC_PROMPT_2,
            context="Cross-pollinated context",
            **discrete_question_params,
        )
        assert isinstance(step2, str)

    def test_date_format_prompts_no_keyerror(self, minimal_config, date_question_params):
        """Verify format methods work for date questions (is_date_question=True)."""
        forecaster = NumericForecaster(minimal_config)

        # Query prompts
        historical, current = forecaster._format_query_prompts(
            NUMERIC_PROMPT_HISTORICAL,
            NUMERIC_PROMPT_CURRENT,
            **date_question_params,
        )
        assert isinstance(historical, str)
        assert isinstance(current, str)

        # Step 1
        step1 = forecaster._format_step1_prompt(
            NUMERIC_PROMPT_1,
            historical_context="Historical context",
            **date_question_params,
        )
        assert isinstance(step1, str)

        # Step 2
        step2 = forecaster._format_step2_prompt(
            NUMERIC_PROMPT_2,
            context="Cross-pollinated context",
            **date_question_params,
        )
        assert isinstance(step2, str)

    def test_get_bounds_explanation_returns_bounds_info(self, numeric_question_params):
        """Verify _get_bounds_explanation() returns dict with 'bounds_info' key."""
        result = NumericForecaster._get_bounds_explanation(**numeric_question_params)

        assert isinstance(result, dict)
        assert "bounds_info" in result
        assert isinstance(result["bounds_info"], str)
        assert len(result["bounds_info"]) > 0

    def test_get_bounds_explanation_open_bounds(self):
        """Test bounds message for open bounds."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=True,
            open_upper_bound=True,
            lower_bound=0,
            upper_bound=100,
        )
        assert "OPEN" in result["bounds_info"]

    def test_get_bounds_explanation_closed_bounds(self):
        """Test bounds message for closed bounds."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=False,
            open_upper_bound=False,
            lower_bound=0,
            upper_bound=100,
        )
        assert "CLOSED" in result["bounds_info"]

    def test_get_bounds_explanation_with_zero_point(self):
        """Test bounds message includes zero_point when provided."""
        result = NumericForecaster._get_bounds_explanation(
            open_lower_bound=True,
            open_upper_bound=True,
            lower_bound=1,
            upper_bound=1000,
            zero_point=10,
        )
        assert "10" in result["bounds_info"]
        assert "logarithmic" in result["bounds_info"].lower()


# ============================================================================
# Multiple Choice Forecaster Tests
# ============================================================================


class TestMultipleChoiceFormatMethods:
    """Tests for MultipleChoiceForecaster format methods."""

    def test_mc_format_query_prompts_no_keyerror(self, minimal_config, mc_question_params):
        """Verify _format_query_prompts() doesn't raise KeyError."""
        forecaster = MultipleChoiceForecaster(minimal_config)

        historical, current = forecaster._format_query_prompts(
            MULTIPLE_CHOICE_PROMPT_HISTORICAL,
            MULTIPLE_CHOICE_PROMPT_CURRENT,
            **mc_question_params,
        )

        assert isinstance(historical, str)
        assert isinstance(current, str)
        # Options should appear in the prompt
        assert "Option A" in historical or "['Option A'" in historical

    def test_mc_format_step1_prompt_no_keyerror(self, minimal_config, mc_question_params):
        """Verify _format_step1_prompt() doesn't raise KeyError."""
        forecaster = MultipleChoiceForecaster(minimal_config)

        result = forecaster._format_step1_prompt(
            MULTIPLE_CHOICE_PROMPT_1,
            historical_context="Historical research context",
            **mc_question_params,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_mc_format_step2_prompt_no_keyerror(self, minimal_config, mc_question_params):
        """Verify _format_step2_prompt() doesn't raise KeyError."""
        forecaster = MultipleChoiceForecaster(minimal_config)

        result = forecaster._format_step2_prompt(
            MULTIPLE_CHOICE_PROMPT_2,
            context="Cross-pollinated context",
            **mc_question_params,
        )

        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# Unsupported Question Type Tests
# ============================================================================


class TestUnsupportedQuestionTypes:
    """Tests for unsupported question type handling."""

    def test_api_parsing_unsupported_type_raises_error(self):
        """Verify parsing unsupported question type raises QuestionTypeError."""
        from src.utils.metaculus_api import MetaculusQuestion

        # Simulate API response with unsupported question type
        mock_api_data = {
            "id": 12345,
            "title": "Test Question",
            "question": {
                "id": 67890,
                "type": "conditional",  # Unsupported type
                "title": "Test Question",
                "description": "Description",
                "resolution_criteria": "Criteria",
                "fine_print": "",
                "created_at": "2026-01-01T00:00:00Z",
                "scheduled_close_time": "2026-12-31T00:00:00Z",
                "scheduled_resolve_time": "2026-12-31T00:00:00Z",
            },
            "created_at": "2026-01-01T00:00:00Z",
        }

        with pytest.raises(QuestionTypeError) as exc_info:
            MetaculusQuestion.from_api_response(mock_api_data)

        assert "conditional" in str(exc_info.value)
        assert exc_info.value.question_type == "conditional"

    def test_api_parsing_group_type_raises_error(self):
        """Verify parsing 'group' question type raises QuestionTypeError."""
        from src.utils.metaculus_api import MetaculusQuestion

        mock_api_data = {
            "id": 12345,
            "title": "Test Group Question",
            "question": {
                "id": 67890,
                "type": "group",  # Unsupported type
                "title": "Test Group Question",
                "description": "Description",
                "resolution_criteria": "Criteria",
                "fine_print": "",
                "created_at": "2026-01-01T00:00:00Z",
                "scheduled_close_time": "2026-12-31T00:00:00Z",
                "scheduled_resolve_time": "2026-12-31T00:00:00Z",
            },
            "created_at": "2026-01-01T00:00:00Z",
        }

        with pytest.raises(QuestionTypeError) as exc_info:
            MetaculusQuestion.from_api_response(mock_api_data)

        assert "group" in str(exc_info.value)
        assert exc_info.value.question_type == "group"
