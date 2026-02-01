"""Custom exceptions for the forecasting pipeline

This module defines a hierarchy of exceptions for better error handling and debugging.
All forecasting-related errors inherit from ForecastingError.
"""


class ForecastingError(Exception):
    """Base exception for all forecasting-related errors."""

    pass


class ExtractionError(ForecastingError):
    """Failed to extract prediction from LLM response.

    Raised when the probability/percentile/option extraction logic
    cannot parse the agent's response.
    """

    pass


class InsufficientPredictionsError(ForecastingError):
    """Not enough agents produced valid predictions.

    Raised when the ensemble cannot aggregate because too many
    agents failed to produce extractable predictions.
    """

    def __init__(self, message: str, valid_count: int = 0, total_count: int = 0):
        super().__init__(message)
        self.valid_count = valid_count
        self.total_count = total_count


class CDFGenerationError(ForecastingError):
    """Failed to generate a valid CDF for numeric questions.

    Raised when percentile extraction or CDF interpolation fails.
    """

    pass


class LLMError(ForecastingError):
    """LLM API call failed after retries.

    Raised when the LLM client exhausts all retry attempts.
    """

    def __init__(self, message: str, attempts: int = 0, last_error: Exception | None = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class SearchError(ForecastingError):
    """Search pipeline encountered an error.

    Raised when Google, AskNews, or agentic search fails.
    """

    pass


class ConfigurationError(ForecastingError):
    """Invalid configuration provided.

    Raised when config validation fails or required fields are missing.
    """

    pass


class QuestionTypeError(ForecastingError):
    """Unsupported or unknown question type.

    Raised when the forecaster encounters a question type it cannot handle.
    """

    def __init__(self, message: str, question_type: str | None = None):
        super().__init__(message)
        self.question_type = question_type


class SubmissionError(ForecastingError):
    """Failed to submit prediction to Metaculus API.

    Raised when the API returns an error (4xx, 5xx) during submission.
    The forecast was generated but not successfully submitted.
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
