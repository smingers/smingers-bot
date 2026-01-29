"""
Tests for the question source abstractions.

Tests the base abstractions and Metaculus source implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from src.sources import get_source, list_sources, register_source
from src.sources.base import Question, Prediction, QuestionSource, QuestionType
from src.sources.metaculus import (
    MetaculusSource,
    metaculus_to_question,
    _extract_community_prediction,
    _extract_tournament_id,
    _safe_float,
)


# ============================================================================
# Base Abstractions Tests
# ============================================================================

class TestQuestion:
    """Tests for the Question dataclass."""

    def test_minimal_question(self):
        """Test creating a question with minimal required fields."""
        q = Question(
            id="123",
            source="test",
            title="Test Question",
            description="Test description",
            resolution_criteria="Test criteria",
        )
        assert q.id == "123"
        assert q.source == "test"
        assert q.question_type == "binary"  # default
        assert q.raw == {}  # default

    def test_binary_question(self):
        """Test creating a binary question."""
        q = Question(
            id="456",
            source="metaculus",
            title="Will X happen?",
            description="Background",
            resolution_criteria="Resolves YES if...",
            question_type="binary",
        )
        assert q.question_type == "binary"
        assert q.options is None

    def test_numeric_question(self):
        """Test creating a numeric question with bounds."""
        q = Question(
            id="789",
            source="metaculus",
            title="How many?",
            description="Background",
            resolution_criteria="Resolves to count",
            question_type="numeric",
            lower_bound=0,
            upper_bound=1000,
            unit_of_measure="units",
        )
        assert q.question_type == "numeric"
        assert q.lower_bound == 0
        assert q.upper_bound == 1000
        assert q.unit_of_measure == "units"

    def test_multiple_choice_question(self):
        """Test creating a multiple choice question."""
        q = Question(
            id="101",
            source="metaculus",
            title="Which option?",
            description="Background",
            resolution_criteria="Resolves to option",
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C"],
        )
        assert q.question_type == "multiple_choice"
        assert q.options == ["Option A", "Option B", "Option C"]

    def test_raw_data_preserved(self):
        """Test that raw source data is preserved."""
        raw = {"post_id": 123, "question_id": 456, "extra": "data"}
        q = Question(
            id="123",
            source="metaculus",
            title="Test",
            description="Test",
            resolution_criteria="Test",
            raw=raw,
        )
        assert q.raw == raw
        assert q.raw["post_id"] == 123


class TestPrediction:
    """Tests for the Prediction dataclass."""

    def test_binary_prediction(self):
        """Test creating a binary prediction."""
        p = Prediction(
            question_id="123",
            question_type="binary",
            value=0.75,
        )
        assert p.question_id == "123"
        assert p.question_type == "binary"
        assert p.value == 0.75
        assert p.timestamp is not None

    def test_numeric_prediction(self):
        """Test creating a numeric prediction with CDF."""
        cdf = [0.0] * 100 + [1.0] * 101  # Simple step CDF
        p = Prediction(
            question_id="456",
            question_type="numeric",
            value=cdf,
        )
        assert p.question_type == "numeric"
        assert len(p.value) == 201

    def test_multiple_choice_prediction(self):
        """Test creating a multiple choice prediction."""
        p = Prediction(
            question_id="789",
            question_type="multiple_choice",
            value={"Option A": 0.5, "Option B": 0.3, "Option C": 0.2},
        )
        assert p.question_type == "multiple_choice"
        assert p.value["Option A"] == 0.5


# ============================================================================
# Source Registry Tests
# ============================================================================

class TestSourceRegistry:
    """Tests for the source registry functions."""

    def test_list_sources(self):
        """Test listing available sources."""
        sources = list_sources()
        assert "metaculus" in sources
        assert isinstance(sources, list)

    def test_get_source_metaculus(self):
        """Test getting the Metaculus source."""
        with patch.dict("os.environ", {"METACULUS_TOKEN": "test-token"}):
            source = get_source("metaculus")
            assert source.name == "metaculus"
            assert isinstance(source, MetaculusSource)

    def test_get_source_unknown(self):
        """Test getting an unknown source raises ValueError."""
        with pytest.raises(ValueError, match="Unknown source"):
            get_source("unknown_source")


# ============================================================================
# Metaculus Source Tests
# ============================================================================

class TestMetaculusConversion:
    """Tests for Metaculus API response conversion."""

    def test_safe_float_valid(self):
        """Test _safe_float with valid values."""
        assert _safe_float(1.5) == 1.5
        assert _safe_float("2.5") == 2.5
        assert _safe_float(0) == 0.0
        assert _safe_float(100) == 100.0

    def test_safe_float_invalid(self):
        """Test _safe_float with invalid values."""
        assert _safe_float(None) is None
        assert _safe_float("invalid") is None
        assert _safe_float({}) is None

    def test_extract_community_prediction(self):
        """Test extracting community prediction from Metaculus data."""
        data = {
            "aggregations": {
                "recency_weighted": {
                    "history": [
                        {"centers": [0.65]}
                    ]
                }
            }
        }
        assert _extract_community_prediction(data) == 0.65

    def test_extract_community_prediction_empty(self):
        """Test extracting community prediction from empty data."""
        assert _extract_community_prediction({}) is None
        assert _extract_community_prediction({"aggregations": {}}) is None
        assert _extract_community_prediction({"aggregations": {"recency_weighted": {}}}) is None

    def test_extract_tournament_id(self):
        """Test extracting tournament ID from Metaculus data."""
        data = {
            "projects": {
                "default_project": {
                    "id": 32721
                }
            }
        }
        assert _extract_tournament_id(data) == "32721"

    def test_extract_tournament_id_missing(self):
        """Test extracting tournament ID when not present."""
        assert _extract_tournament_id({}) is None
        assert _extract_tournament_id({"projects": {}}) is None

    def test_metaculus_to_question_binary(self):
        """Test converting Metaculus binary question."""
        data = {
            "id": 12345,
            "title": "Will X happen?",
            "description": "Background info",
            "resolution_criteria": "Resolves YES if...",
            "fine_print": "Additional details",
            "status": "open",
            "created_at": "2024-01-01T00:00:00Z",
            "question": {
                "id": 67890,
                "type": "binary",
                "description": "Question background",
            }
        }
        q = metaculus_to_question(data)

        assert q.id == "12345"
        assert q.source == "metaculus"
        assert q.title == "Will X happen?"
        assert q.question_type == "binary"
        assert q.raw["post_id"] == 12345
        assert q.raw["question_id"] == 67890

    def test_metaculus_to_question_numeric(self):
        """Test converting Metaculus numeric question."""
        data = {
            "id": 12345,
            "title": "How many?",
            "description": "Background",
            "resolution_criteria": "Resolves to count",
            "question": {
                "id": 67890,
                "type": "numeric",
                "unit": "units",
                "scaling": {
                    "range_min": 0,
                    "range_max": 1000,
                    "zero_point": None,
                },
                "open_lower_bound": False,
                "open_upper_bound": True,
            }
        }
        q = metaculus_to_question(data)

        assert q.question_type == "numeric"
        assert q.lower_bound == 0
        assert q.upper_bound == 1000
        assert q.unit_of_measure == "units"
        assert q.open_lower_bound is False
        assert q.open_upper_bound is True

    def test_metaculus_to_question_multiple_choice(self):
        """Test converting Metaculus multiple choice question."""
        data = {
            "id": 12345,
            "title": "Which option?",
            "description": "Background",
            "resolution_criteria": "Resolves to option",
            "question": {
                "id": 67890,
                "type": "multiple_choice",
                "options": [
                    {"label": "Option A"},
                    {"label": "Option B"},
                    {"label": "Option C"},
                ],
            }
        }
        q = metaculus_to_question(data)

        assert q.question_type == "multiple_choice"
        assert q.options == ["Option A", "Option B", "Option C"]


class TestMetaculusSourceCDF:
    """Tests for Metaculus CDF validation."""

    @pytest.fixture
    def source(self):
        """Create a MetaculusSource for testing."""
        with patch.dict("os.environ", {"METACULUS_TOKEN": "test-token"}):
            return MetaculusSource()

    def test_validate_cdf_bounds(self, source):
        """Test that CDF values are bounded to [0.001, 0.999]."""
        cdf = [0.0] * 50 + [0.5] * 100 + [1.0] * 51
        validated = source._validate_cdf(cdf)

        assert all(0.001 <= v <= 0.999 for v in validated)

    def test_validate_cdf_monotonicity(self, source):
        """Test that CDF is monotonically increasing."""
        cdf = [0.5, 0.3, 0.4, 0.6, 0.5, 0.7]  # Non-monotonic
        validated = source._validate_cdf(cdf)

        for i in range(1, len(validated)):
            assert validated[i] >= validated[i - 1]

    def test_validate_cdf_max_step(self, source):
        """Test that no single step exceeds 0.59."""
        cdf = [0.1] + [0.9] * 200  # Big jump
        validated = source._validate_cdf(cdf)

        for i in range(1, len(validated)):
            assert validated[i] - validated[i - 1] <= 0.59


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility with old imports."""

    def test_metaculus_client_import(self):
        """Test that MetaculusClient can still be imported from metaculus_api."""
        from src.utils.metaculus_api import MetaculusClient
        assert MetaculusClient is not None

    def test_metaculus_question_import(self):
        """Test that MetaculusQuestion can still be imported from metaculus_api."""
        from src.utils.metaculus_api import MetaculusQuestion
        assert MetaculusQuestion is not None

    def test_metaculus_question_has_conversion_methods(self):
        """Test that MetaculusQuestion has conversion methods."""
        from src.utils.metaculus_api import MetaculusQuestion

        # Create a MetaculusQuestion with all required fields
        mq = MetaculusQuestion(
            id=123,
            question_id=456,
            title="Test Question",
            description="Test description",
            resolution_criteria="Test criteria",
            fine_print="Test fine print",
            background_info="Test background",
            question_type="binary",
            created_at="2024-01-01T00:00:00Z",
            open_time="2024-01-01T00:00:00Z",
            scheduled_close_time="2024-12-31T00:00:00Z",
            scheduled_resolve_time="2025-01-01T00:00:00Z",
            status="open",
        )

        # Test to_generic_question
        generic = mq.to_generic_question()
        assert generic.id == "123"
        assert generic.source == "metaculus"
        assert generic.title == "Test Question"
        assert generic.question_type == "binary"

        # Test from_generic_question
        back = MetaculusQuestion.from_generic_question(generic)
        assert back.id == 123
        assert back.title == "Test Question"
        assert back.question_type == "binary"
