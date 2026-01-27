"""Bot forecasting module - Panshul42 Integration."""


class ExtractionError(Exception):
    """Raised when probability/value extraction fails from LLM response."""
    pass


# The handlers are imported directly by forecaster.py
# from .binary, .numeric, .multiple_choice

__all__ = ["ExtractionError"]
