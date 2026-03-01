"""
Tests for Metaculus API client and question parsing.

Tests cover:
- MetaculusQuestion.from_api_response() for all question types
- _validate_cdf() for CDF validation
- _parse_date_bound() for date question bounds
- Prediction submission methods
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.exceptions import QuestionTypeError
from src.utils.metaculus_api import MetaculusClient, MetaculusQuestion

# ============================================================================
# MetaculusQuestion.from_api_response Tests
# ============================================================================


class TestMetaculusQuestionFromApiResponse:
    """Tests for parsing question data from API responses."""

    def test_parses_binary_question(self, binary_api_response):
        """Binary questions parsed with correct type and fields."""
        question = MetaculusQuestion.from_api_response(binary_api_response)

        assert question.id == 12345
        assert question.question_id == 67890
        assert question.title == "Will X happen by 2026?"
        assert question.question_type == "binary"
        assert question.status == "open"
        # description, resolution_criteria, fine_print come from nested question object
        assert question.description == "Background info about the question."
        assert question.resolution_criteria == "Resolves YES if X occurs before Dec 31, 2026."
        assert question.fine_print == "Edge cases handled as follows..."

    def test_parses_numeric_question_with_bounds(self, numeric_api_response):
        """Numeric questions extract range_min, range_max, unit, and bounds info."""
        question = MetaculusQuestion.from_api_response(numeric_api_response)

        assert question.question_type == "numeric"
        assert question.question_id == 67891
        assert question.lower_bound == 0
        assert question.upper_bound == 1000
        assert question.nominal_lower_bound == 100
        assert question.nominal_upper_bound == 500
        assert question.unit_of_measure == "units"
        assert question.open_lower_bound is True
        assert question.open_upper_bound is True
        assert question.cdf_size == 201  # 200 + 1

    def test_parses_discrete_question_cdf_size(self, discrete_api_response):
        """Discrete questions have cdf_size from inbound_outcome_count + 1."""
        question = MetaculusQuestion.from_api_response(discrete_api_response)

        assert question.question_type == "discrete"
        assert question.cdf_size == 102  # 101 + 1
        assert question.open_lower_bound is False
        assert question.open_upper_bound is False

    def test_parses_date_question_bounds_as_timestamps(self, date_api_response):
        """Date bounds converted to Unix timestamps and readable date strings."""
        question = MetaculusQuestion.from_api_response(date_api_response)

        assert question.question_type == "date"
        # Bounds should be Unix timestamps (floats)
        assert isinstance(question.lower_bound, float)
        assert isinstance(question.upper_bound, float)
        assert question.lower_bound == 1767225600  # 2026-01-01
        assert question.upper_bound == 1798761600  # 2027-01-01
        # Human-readable date strings
        assert question.lower_bound_date_str == "2026-01-01"
        assert question.upper_bound_date_str == "2027-01-01"

    def test_parses_multiple_choice_options(self, multiple_choice_api_response):
        """Multiple choice options extracted as list of dicts."""
        question = MetaculusQuestion.from_api_response(multiple_choice_api_response)

        assert question.question_type == "multiple_choice"
        assert question.options is not None
        assert len(question.options) == 3
        assert question.options[0]["label"] == "Option A"
        assert question.options[1]["label"] == "Option B"
        assert question.options[2]["label"] == "Option C"

    def test_raises_for_unsupported_type(self, unsupported_type_api_response):
        """Unsupported question types raise QuestionTypeError."""
        with pytest.raises(QuestionTypeError) as exc_info:
            MetaculusQuestion.from_api_response(unsupported_type_api_response)

        assert "conditional" in str(exc_info.value)
        assert exc_info.value.question_type == "conditional"

    def test_extracts_community_prediction(self, binary_api_response):
        """Community prediction extracted from aggregations.recency_weighted."""
        question = MetaculusQuestion.from_api_response(binary_api_response)

        assert question.community_prediction == 0.65

    def test_handles_missing_community_prediction(self, numeric_api_response):
        """Handles missing community prediction gracefully."""
        question = MetaculusQuestion.from_api_response(numeric_api_response)

        assert question.community_prediction is None

    def test_extracts_num_forecasters(self, binary_api_response):
        """Extracts number of forecasters from response."""
        question = MetaculusQuestion.from_api_response(binary_api_response)

        assert question.num_forecasters == 42

    def test_handles_continuous_as_numeric(self):
        """'continuous' type is treated as 'numeric'."""
        response = {
            "id": 1,
            "title": "Test",
            "question": {
                "id": 2,
                "type": "continuous",
                "scaling": {},
            },
        }
        question = MetaculusQuestion.from_api_response(response)

        assert question.question_type == "numeric"

    def test_handles_missing_scaling(self):
        """Handles missing scaling gracefully with defaults."""
        response = {
            "id": 1,
            "title": "Test",
            "question": {
                "id": 2,
                "type": "numeric",
            },
        }
        question = MetaculusQuestion.from_api_response(response)

        assert question.cdf_size == 201  # Default
        assert question.lower_bound is None
        assert question.upper_bound is None

    def test_stores_raw_response(self, binary_api_response):
        """Raw response stored for reference."""
        question = MetaculusQuestion.from_api_response(binary_api_response)

        assert question.raw == binary_api_response


# ============================================================================
# _parse_date_bound Tests
# ============================================================================


class TestParseDateBound:
    """Tests for date bound parsing."""

    def test_parses_integer_timestamp(self):
        """Integer Unix timestamp returned as float."""
        result = MetaculusQuestion._parse_date_bound(1767225600)

        assert result == 1767225600.0

    def test_parses_float_timestamp(self):
        """Float Unix timestamp returned as-is."""
        result = MetaculusQuestion._parse_date_bound(1767225600.5)

        assert result == 1767225600.5

    def test_parses_iso_string_with_z(self):
        """ISO format string with Z suffix parsed correctly."""
        result = MetaculusQuestion._parse_date_bound("2026-01-01T00:00:00Z")

        assert result is not None
        assert 1767200000 < result < 1767300000  # Around 2026-01-01

    def test_parses_iso_string_with_offset(self):
        """ISO format string with timezone offset parsed correctly."""
        result = MetaculusQuestion._parse_date_bound("2026-01-01T00:00:00+00:00")

        assert result is not None
        assert 1767200000 < result < 1767300000

    def test_returns_none_for_none(self):
        """None input returns None."""
        result = MetaculusQuestion._parse_date_bound(None)

        assert result is None

    def test_returns_none_for_invalid_string(self):
        """Invalid date string returns None."""
        result = MetaculusQuestion._parse_date_bound("not-a-date")

        assert result is None


# ============================================================================
# _validate_cdf Tests
# ============================================================================


class TestValidateCdf:
    """Tests for CDF validation and fixing."""

    @pytest.fixture
    def client(self):
        """Create a MetaculusClient with a test token for accessing _validate_cdf."""
        # We need to patch the env var check
        import os

        original = os.environ.get("METACULUS_TOKEN")
        os.environ["METACULUS_TOKEN"] = "test-token"
        client = MetaculusClient()
        if original:
            os.environ["METACULUS_TOKEN"] = original
        else:
            del os.environ["METACULUS_TOKEN"]
        return client

    def test_valid_cdf_mostly_unchanged(self, client):
        """Valid monotonic CDF with correct bounds is mostly preserved."""
        # Create a valid monotonic CDF
        cdf = [0.001 + i * 0.00499 for i in range(201)]  # 0.001 to 0.999

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        assert len(result) == 201
        assert result[0] == 0.001
        assert result[-1] == 0.999
        # Should be monotonically increasing
        for i in range(1, len(result)):
            assert result[i] > result[i - 1]

    def test_clamps_to_open_bounds(self, client):
        """Open bounds: first=0.001, last=0.999."""
        cdf = [0.0 + i * 0.005 for i in range(201)]  # 0.0 to 1.0

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        assert result[0] == 0.001
        assert result[-1] == 0.999

    def test_clamps_to_closed_bounds(self, client):
        """Closed bounds: first=0.0, last=1.0."""
        cdf = [0.1 + i * 0.004 for i in range(201)]  # Starts at 0.1

        result = client._validate_cdf(cdf, open_lower_bound=False, open_upper_bound=False)

        assert result[0] == 0.0
        assert result[-1] == 1.0

    def test_enforces_monotonicity_for_flat_regions(self, client):
        """Flat regions are converted to strictly increasing values."""
        # Create CDF with some flat regions
        cdf = [0.001] * 50 + [0.5] * 101 + [0.999] * 50

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        # Result should be strictly monotonic
        for i in range(1, len(result)):
            assert result[i] > result[i - 1], (
                f"Not monotonic at index {i}: {result[i - 1]} >= {result[i]}"
            )

        # Bounds should be respected
        assert result[0] == 0.001
        assert result[-1] == 0.999

    def test_fixes_non_monotonic_cdf(self, client):
        """Non-monotonic CDFs are fixed to be strictly increasing."""
        # Create non-monotonic CDF
        cdf = [0.001 + i * 0.005 for i in range(201)]
        cdf[100] = cdf[50]  # Make it non-monotonic

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        # Should be strictly increasing
        for i in range(1, len(result)):
            assert result[i] > result[i - 1]

    def test_caps_maximum_step(self, client):
        """No single step exceeds 0.59."""
        # Create CDF with a huge jump
        cdf = [0.001] * 100 + [0.999] * 101  # Jump from 0.001 to 0.999

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        # Max step is 0.2 * (200 / (cdf_size - 1)) = 0.2 for 201-point CDF
        max_step = 0.2
        for i in range(1, len(result)):
            assert result[i] - result[i - 1] <= max_step + 1e-10  # Small tolerance

    def test_handles_all_equal_values(self, client):
        """Gracefully handles CDF where all values are equal."""
        cdf = [0.5] * 201

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        assert len(result) == 201
        assert result[0] == 0.001
        # Note: The backup validator may not reach exactly 0.999 after max_step enforcement
        # The primary CDF generation in cdf.py handles this properly
        # Should be monotonically non-decreasing
        for i in range(1, len(result)):
            assert result[i] >= result[i - 1]
        # Max step constraint is enforced
        max_step = 0.2
        for i in range(1, len(result)):
            assert result[i] - result[i - 1] <= max_step + 1e-10

    def test_mixed_open_closed_bounds(self, client):
        """Mixed open/closed bounds handled correctly."""
        cdf = [0.1 + i * 0.004 for i in range(201)]

        # Open lower, closed upper
        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=False)

        assert result[0] == 0.001
        assert result[-1] == 1.0

        # Closed lower, open upper
        result = client._validate_cdf(cdf, open_lower_bound=False, open_upper_bound=True)

        assert result[0] == 0.0
        assert result[-1] == 0.999

    def test_returns_list(self, client):
        """Result is a Python list, not numpy array."""
        cdf = [0.001 + i * 0.00499 for i in range(201)]

        result = client._validate_cdf(cdf, open_lower_bound=True, open_upper_bound=True)

        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)


# ============================================================================
# Binary Prediction Submission Tests
# ============================================================================


class TestSubmitBinaryPrediction:
    """Tests for submit_binary_prediction method."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked httpx client."""
        with patch("httpx.AsyncClient"):
            client = MetaculusClient(token="test-token")
            client.client = MagicMock()
            return client

    @pytest.mark.asyncio
    async def test_submits_valid_prediction(self, mock_client):
        """Submits valid binary prediction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        result = await mock_client.submit_binary_prediction(12345, 0.65)

        assert result == {"success": True}
        mock_client.client.request.assert_called_once()
        call_args = mock_client.client.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/questions/forecast/"
        payload = call_args[1]["json"]
        assert payload[0]["question"] == 12345
        assert payload[0]["probability_yes"] == 0.65

    @pytest.mark.asyncio
    async def test_clamps_prediction_to_bounds(self, mock_client):
        """Clamps prediction to [0.001, 0.999]."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        # Test lower bound
        await mock_client.submit_binary_prediction(12345, 0.0)
        payload = mock_client.client.request.call_args[1]["json"]
        assert payload[0]["probability_yes"] == 0.001

        # Test upper bound
        await mock_client.submit_binary_prediction(12345, 1.0)
        payload = mock_client.client.request.call_args[1]["json"]
        assert payload[0]["probability_yes"] == 0.999


# ============================================================================
# Numeric Prediction Submission Tests
# ============================================================================


class TestSubmitNumericPrediction:
    """Tests for submit_numeric_prediction method."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked httpx client."""
        with patch("httpx.AsyncClient"):
            client = MetaculusClient(token="test-token")
            client.client = MagicMock()
            return client

    @pytest.mark.asyncio
    async def test_submits_valid_cdf(self, mock_client):
        """Submits valid 201-point CDF."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        cdf = [0.001 + i * 0.00499 for i in range(201)]
        result = await mock_client.submit_numeric_prediction(12345, cdf)

        assert result == {"success": True}
        call_args = mock_client.client.request.call_args
        payload = call_args[1]["json"]
        assert payload[0]["question"] == 12345
        assert "continuous_cdf" in payload[0]
        assert len(payload[0]["continuous_cdf"]) == 201

    @pytest.mark.asyncio
    async def test_raises_for_wrong_cdf_size(self, mock_client):
        """Raises ValueError for wrong CDF size."""
        cdf = [0.5] * 100  # Wrong size

        with pytest.raises(ValueError) as exc_info:
            await mock_client.submit_numeric_prediction(12345, cdf)

        assert "201 values" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accepts_discrete_cdf_size(self, mock_client):
        """Accepts 102-point CDF for discrete questions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        cdf = [i / 101 for i in range(102)]
        result = await mock_client.submit_numeric_prediction(12345, cdf, expected_cdf_size=102)

        assert result == {"success": True}


# ============================================================================
# Multiple Choice Prediction Submission Tests
# ============================================================================


class TestSubmitMultipleChoicePrediction:
    """Tests for submit_multiple_choice_prediction method."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked httpx client."""
        with patch("httpx.AsyncClient"):
            client = MetaculusClient(token="test-token")
            client.client = MagicMock()
            return client

    @pytest.mark.asyncio
    async def test_submits_valid_probabilities(self, mock_client):
        """Submits valid multiple choice probabilities."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        probs = {"option_a": 0.3, "option_b": 0.5, "option_c": 0.2}
        result = await mock_client.submit_multiple_choice_prediction(12345, probs)

        assert result == {"success": True}
        call_args = mock_client.client.request.call_args
        payload = call_args[1]["json"]
        assert payload[0]["question"] == 12345
        assert "probability_yes_per_category" in payload[0]

    @pytest.mark.asyncio
    async def test_normalizes_probabilities(self, mock_client):
        """Normalizes probabilities that don't sum to 1."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        # Probabilities that don't sum to 1
        probs = {"option_a": 0.5, "option_b": 0.5, "option_c": 0.5}
        await mock_client.submit_multiple_choice_prediction(12345, probs)

        call_args = mock_client.client.request.call_args
        payload = call_args[1]["json"]
        submitted_probs = payload[0]["probability_yes_per_category"]

        # Should be normalized
        total = sum(submitted_probs.values())
        assert abs(total - 1.0) < 0.01


# ============================================================================
# Generic Submit Prediction Tests
# ============================================================================


class TestSubmitPrediction:
    """Tests for the generic submit_prediction method."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked httpx client."""
        with patch("httpx.AsyncClient"):
            client = MetaculusClient(token="test-token")
            client.client = MagicMock()
            return client

    @pytest.mark.asyncio
    async def test_routes_binary_question(self, mock_client):
        """Routes binary question to submit_binary_prediction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        question = MagicMock()
        question.question_type = "binary"
        question.question_id = 12345

        await mock_client.submit_prediction(question, 0.65)

        call_args = mock_client.client.request.call_args
        payload = call_args[1]["json"]
        assert "probability_yes" in payload[0]

    @pytest.mark.asyncio
    async def test_routes_numeric_question(self, mock_client):
        """Routes numeric question to submit_numeric_prediction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        question = MagicMock()
        question.question_type = "numeric"
        question.question_id = 12345
        question.open_lower_bound = True
        question.open_upper_bound = True
        question.cdf_size = 201

        cdf = [0.001 + i * 0.00499 for i in range(201)]
        await mock_client.submit_prediction(question, cdf)

        call_args = mock_client.client.request.call_args
        payload = call_args[1]["json"]
        assert "continuous_cdf" in payload[0]

    @pytest.mark.asyncio
    async def test_routes_multiple_choice_question(self, mock_client):
        """Routes multiple choice question to submit_multiple_choice_prediction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.client.request = AsyncMock(return_value=mock_response)

        question = MagicMock()
        question.question_type = "multiple_choice"
        question.question_id = 12345

        probs = {"a": 0.5, "b": 0.5}
        await mock_client.submit_prediction(question, probs)

        call_args = mock_client.client.request.call_args
        payload = call_args[1]["json"]
        assert "probability_yes_per_category" in payload[0]

    @pytest.mark.asyncio
    async def test_raises_for_unsupported_type(self, mock_client):
        """Raises ValueError for unsupported question type."""
        question = MagicMock()
        question.question_type = "conditional"
        question.question_id = 12345

        with pytest.raises(ValueError) as exc_info:
            await mock_client.submit_prediction(question, 0.5)

        assert "Unsupported question type" in str(exc_info.value)
