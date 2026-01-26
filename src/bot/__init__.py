"""Bot forecasting module - Panshul42 Integration."""


class ExtractionError(Exception):
    """Raised when probability/value extraction fails from LLM response."""
    pass


# The Panshul42 handlers are imported directly by forecaster.py
# from .binary_panshul42, .numeric_panshul42, .multiple_choice_panshul42

__all__ = ["ExtractionError"]
