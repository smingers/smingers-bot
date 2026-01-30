"""
Tests for the shared runner module.

Tests RunResult, run_forecasts(), and format_prediction().
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.runner import RunResult, ForecastFailure, run_forecasts, format_prediction
from src.bot import ExtractionError


class TestRunResult:
    """Tests for RunResult dataclass."""

    def test_initial_state(self):
        """Test that RunResult starts with zeroed counts."""
        result = RunResult()

        assert result.success_count == 0
        assert result.error_count == 0
        assert result.extraction_error_count == 0
        assert result.failures == []
        assert result.successful_results == []

    def test_add_success(self):
        """Test recording a successful forecast."""
        result = RunResult()
        forecast_result = {"prediction": 0.75, "question": MagicMock()}

        result.add_success(forecast_result)

        assert result.success_count == 1
        assert result.error_count == 0
        assert len(result.successful_results) == 1
        assert result.successful_results[0] == forecast_result

    def test_add_failure_regular_error(self):
        """Test recording a regular (non-extraction) error."""
        result = RunResult()
        error = ValueError("Something went wrong")

        result.add_failure(question_id=123, question_title="Test Question", error=error)

        assert result.success_count == 0
        assert result.error_count == 1
        assert result.extraction_error_count == 0
        assert len(result.failures) == 1
        assert result.failures[0].question_id == 123
        assert result.failures[0].is_extraction_error is False

    def test_add_failure_extraction_error(self):
        """Test recording an extraction error."""
        result = RunResult()
        error = ExtractionError("Could not parse probability")

        result.add_failure(question_id=456, question_title="Another Question", error=error)

        assert result.error_count == 1
        assert result.extraction_error_count == 1
        assert result.failures[0].is_extraction_error is True

    def test_has_extraction_errors_property(self):
        """Test has_extraction_errors property."""
        result = RunResult()
        assert result.has_extraction_errors is False

        result.add_failure(123, "Q1", ValueError("error"))
        assert result.has_extraction_errors is False

        result.add_failure(456, "Q2", ExtractionError("extraction failed"))
        assert result.has_extraction_errors is True

    def test_total_count_property(self):
        """Test total_count property."""
        result = RunResult()
        assert result.total_count == 0

        result.add_success({"prediction": 0.5})
        assert result.total_count == 1

        result.add_failure(123, "Q1", ValueError("error"))
        assert result.total_count == 2

    def test_title_truncation(self):
        """Test that long titles are truncated to 60 chars."""
        result = RunResult()
        long_title = "A" * 100

        result.add_failure(123, long_title, ValueError("error"))

        assert len(result.failures[0].question_title) == 60

    def test_error_message_truncation(self):
        """Test that long error messages are truncated to 200 chars."""
        result = RunResult()
        long_error = ValueError("E" * 300)

        result.add_failure(123, "Test", long_error)

        assert len(result.failures[0].error_message) == 200


class TestForecastFailure:
    """Tests for ForecastFailure dataclass."""

    def test_default_is_extraction_error(self):
        """Test default value for is_extraction_error."""
        failure = ForecastFailure(
            question_id=123,
            question_title="Test",
            error_type="ValueError",
            error_message="error",
        )

        assert failure.is_extraction_error is False

    def test_extraction_error_flag(self):
        """Test setting is_extraction_error."""
        failure = ForecastFailure(
            question_id=123,
            question_title="Test",
            error_type="ExtractionError",
            error_message="could not parse",
            is_extraction_error=True,
        )

        assert failure.is_extraction_error is True


class TestRunForecasts:
    """Tests for run_forecasts() async function."""

    @pytest.fixture
    def mock_forecaster(self):
        """Create a mock forecaster."""
        forecaster = MagicMock()
        forecaster.forecast_question = AsyncMock()
        return forecaster

    @pytest.fixture
    def mock_questions(self):
        """Create mock questions."""
        q1 = MagicMock()
        q1.id = 1
        q1.title = "Question 1"
        q1.question_type = "binary"

        q2 = MagicMock()
        q2.id = 2
        q2.title = "Question 2"
        q2.question_type = "binary"

        return [q1, q2]

    @pytest.mark.asyncio
    async def test_all_success(self, mock_forecaster, mock_questions):
        """Test run with all successful forecasts."""
        mock_forecaster.forecast_question.return_value = {
            "prediction": 0.75,
            "question": mock_questions[0],
        }

        result = await run_forecasts(
            questions=mock_questions,
            forecaster=mock_forecaster,
        )

        assert result.success_count == 2
        assert result.error_count == 0
        assert mock_forecaster.forecast_question.call_count == 2

    @pytest.mark.asyncio
    async def test_mixed_results(self, mock_forecaster, mock_questions):
        """Test run with mixed success and failure."""
        mock_forecaster.forecast_question.side_effect = [
            {"prediction": 0.75, "question": mock_questions[0]},
            ValueError("Something failed"),
        ]

        result = await run_forecasts(
            questions=mock_questions,
            forecaster=mock_forecaster,
        )

        assert result.success_count == 1
        assert result.error_count == 1
        assert result.extraction_error_count == 0

    @pytest.mark.asyncio
    async def test_extraction_error(self, mock_forecaster, mock_questions):
        """Test run with extraction error."""
        mock_forecaster.forecast_question.side_effect = [
            {"prediction": 0.75, "question": mock_questions[0]},
            ExtractionError("Could not parse"),
        ]

        result = await run_forecasts(
            questions=mock_questions,
            forecaster=mock_forecaster,
        )

        assert result.success_count == 1
        assert result.error_count == 1
        assert result.extraction_error_count == 1
        assert result.has_extraction_errors is True

    @pytest.mark.asyncio
    async def test_callbacks_called(self, mock_forecaster, mock_questions):
        """Test that callbacks are called correctly."""
        mock_forecaster.forecast_question.return_value = {
            "prediction": 0.75,
            "question": mock_questions[0],
        }

        on_progress = MagicMock()
        on_success = MagicMock()
        on_error = MagicMock()

        await run_forecasts(
            questions=mock_questions[:1],  # Just one question
            forecaster=mock_forecaster,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
        )

        on_progress.assert_called_once()
        on_success.assert_called_once()
        on_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_callback_called(self, mock_forecaster, mock_questions):
        """Test that error callback is called on failure."""
        mock_forecaster.forecast_question.side_effect = ValueError("Failed")

        on_error = MagicMock()

        await run_forecasts(
            questions=mock_questions[:1],
            forecaster=mock_forecaster,
            on_error=on_error,
        )

        on_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_questions_list(self, mock_forecaster):
        """Test run with empty questions list."""
        result = await run_forecasts(
            questions=[],
            forecaster=mock_forecaster,
        )

        assert result.success_count == 0
        assert result.error_count == 0
        assert mock_forecaster.forecast_question.call_count == 0


class TestFormatPrediction:
    """Tests for format_prediction() helper."""

    def test_binary_prediction(self):
        """Test formatting binary prediction."""
        question = MagicMock()
        question.question_type = "binary"
        result = {"question": question, "prediction": 0.75}

        formatted = format_prediction(result)

        assert formatted == "75.0%"

    def test_numeric_prediction_with_median(self):
        """Test formatting numeric prediction with median."""
        question = MagicMock()
        question.question_type = "numeric"
        result = {"question": question, "prediction": {"50": 123.45, "10": 100, "90": 150}}

        formatted = format_prediction(result)

        assert "median" in formatted
        assert "123.45" in formatted

    def test_multiple_choice_prediction(self):
        """Test formatting multiple choice prediction."""
        question = MagicMock()
        question.question_type = "multiple_choice"
        result = {
            "question": question,
            "prediction": {"Option A": 0.6, "Option B": 0.3, "Option C": 0.1},
        }

        formatted = format_prediction(result)

        assert "Option A" in formatted
        assert "60.0%" in formatted

    def test_missing_question(self):
        """Test formatting when question is missing."""
        result = {"prediction": 0.5}

        formatted = format_prediction(result)

        assert formatted == "0.5"

    def test_missing_prediction(self):
        """Test formatting when prediction is missing."""
        result = {"question": MagicMock()}

        formatted = format_prediction(result)

        assert formatted == "None"


class TestRunResultWriteFailureLog:
    """Tests for RunResult.write_failure_log() method."""

    def test_no_failures_no_write(self, tmp_path):
        """Test that no file is written when there are no failures."""
        result = RunResult()

        with patch("src.runner.FAILURE_LOG_PATH", tmp_path / "test.log"):
            result.write_failure_log()

        assert not (tmp_path / "test.log").exists()

    def test_writes_failures_to_log(self, tmp_path):
        """Test that failures are written to log file."""
        result = RunResult()
        result.add_failure(123, "Test Question", ValueError("error"))

        log_path = tmp_path / "test.log"
        with patch("src.runner.FAILURE_LOG_PATH", log_path):
            result.write_failure_log(source="test", tournament_id="12345", strategy="new-only")

        assert log_path.exists()
        content = log_path.read_text()
        assert "Q123" in content
        assert "Test Question" in content
        assert "new-only" in content
        assert "12345" in content


class TestRunResultPrintSummary:
    """Tests for RunResult.print_summary() method."""

    def test_print_summary_no_failures(self, capsys):
        """Test printing summary with no failures."""
        result = RunResult()
        result.add_success({"prediction": 0.5})

        result.print_summary()

        captured = capsys.readouterr()
        assert "Successful: 1" in captured.out
        assert "Failed: 0" in captured.out

    def test_print_summary_with_failures(self, capsys):
        """Test printing summary with failures."""
        result = RunResult()
        result.add_failure(123, "Test Q", ValueError("error"))

        result.print_summary(tournament_id="12345", strategy="new-only")

        captured = capsys.readouterr()
        assert "Tournament: 12345" in captured.out
        assert "Strategy: new-only" in captured.out
        assert "Failed: 1" in captured.out

    def test_print_summary_with_extraction_errors(self, capsys):
        """Test printing summary highlights extraction errors."""
        result = RunResult()
        result.add_failure(123, "Test Q", ExtractionError("parse failed"))

        result.print_summary()

        captured = capsys.readouterr()
        assert "EXTRACTION ERRORS" in captured.out
        assert "EXTRACTION FAILURES" in captured.out
