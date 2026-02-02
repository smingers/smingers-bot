"""
Probability and percentile extraction from LLM responses

This module consolidates extraction logic from the question handlers,
making it testable and reusable across all question types and sources.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime

from .exceptions import ExtractionError

logger = logging.getLogger(__name__)


# ============================================================================
# Unified Agent Result Type
# ============================================================================


@dataclass
class AgentResult:
    """
    Result from a single forecasting agent.

    This unified type supports all question types (binary, numeric, multiple choice).
    Each handler populates only the fields relevant to its question type.

    Common fields (always populated):
        agent_id: Identifier like "forecaster_1"
        model: LLM model used (e.g., "openrouter/anthropic/claude-sonnet-4")
        weight: Agent weight for ensemble aggregation
        outside_view_output: Raw LLM response from outside view prediction
        inside_view_output: Raw LLM response from inside view prediction
        error: Error message if extraction failed, None otherwise

    Type-specific fields (only one set populated per question type):
        probability: Binary question result (0-1 probability)
        probabilities: Multiple choice result (list of option probabilities)
        percentiles: Numeric question percentiles (dict mapping percentile -> value)
        cdf: Numeric question CDF (201-point list)
    """

    # Common fields
    agent_id: str
    model: str
    weight: float
    outside_view_output: str
    inside_view_output: str
    error: str | None = None

    # Binary-specific
    probability: float | None = None

    # Multiple choice-specific
    probabilities: list[float] | None = None

    # Numeric-specific
    percentiles: dict[int, float] | None = None
    cdf: list[float] | None = None


# ============================================================================
# Constants
# ============================================================================

# Valid percentile keys for numeric questions
VALID_PERCENTILE_KEYS: set[int] = {
    1,
    5,
    10,
    15,
    20,
    25,
    30,
    35,
    40,
    45,
    50,
    55,
    60,
    65,
    70,
    75,
    80,
    85,
    90,
    95,
    99,
}

# Regex for parsing percentile lines (numeric values)
NUM_PATTERN = re.compile(
    r"^(?:percentile\s*)?(\d{1,3})\s*[:\-]\s*([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*$", re.IGNORECASE
)

# Regex for parsing percentile lines with date values (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
# Note: normalize_percentile_line() lowercases input, so T/Z become t/z
DATE_PATTERN = re.compile(
    r"^(?:percentile\s*)?(\d{1,3})\s*[:\-]\s*(\d{4}-\d{2}-\d{2}(?:[tT]\d{2}:\d{2}:\d{2}[zZ]?)?)\s*$",
    re.IGNORECASE,
)

# Characters that can start bullet points
BULLET_CHARS: str = "•▪●‣–*-"

# Dash normalization pattern
DASH_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")


# ============================================================================
# Binary Probability Extraction
# ============================================================================


def extract_binary_probability_percent(text: str) -> float:
    """
    Extract probability percentage from binary forecast response.

    Looks for "Probability: X%" pattern first, then falls back to
    any percentage in the last 500 characters.

    Args:
        text: LLM response text

    Returns:
        Probability as percentage in range [1, 99] (not 0-1 probability).
        Caller should divide by 100 to get actual probability.

    Raises:
        ExtractionError: If no probability found
    """
    # Primary pattern: "Probability: X%"
    matches = re.findall(r"Probability:\s*([0-9]+(?:\.[0-9]+)?)%", text.strip())
    if matches:
        number = float(matches[-1])
        return min(99, max(1, number))

    # Fallback: look for any percentage near the end
    matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*%", text[-500:])
    if matches:
        number = float(matches[-1])
        return min(99, max(1, number))

    snippet = text[-200:] if len(text) > 200 else text
    raise ExtractionError(
        f"Could not extract probability from response. Last 200 chars: {snippet!r}"
    )


# ============================================================================
# Multiple Choice Probability Extraction
# ============================================================================


def extract_multiple_choice_probabilities(
    text: str,
    num_options: int,
) -> list[float]:
    """
    Extract option probabilities from multiple choice forecast response.

    Looks for "Probabilities: [X, Y, Z]" pattern.

    Args:
        text: LLM response text
        num_options: Expected number of options

    Returns:
        List of probabilities as floats (raw values, not normalized)

    Raises:
        ExtractionError: If no probabilities found or wrong number
    """
    matches = re.findall(r"Probabilities:\s*\[([0-9.,\s]+)\]", text)
    if not matches:
        snippet = text[-200:] if len(text) > 200 else text
        raise ExtractionError(
            f"Could not extract 'Probabilities' list from response. Last 200 chars: {snippet!r}"
        )

    last_match = matches[-1]
    numbers = [float(n.strip()) for n in last_match.split(",") if n.strip()]

    if len(numbers) != num_options:
        raise ExtractionError(
            f"Expected {num_options} probabilities, got {len(numbers)}: {numbers}"
        )

    return numbers


def normalize_probabilities(
    probs: list[float], min_prob: float = 1.0, max_prob: float = 99.0
) -> list[float]:
    """
    Normalize probabilities to sum to 1.0.

    Clamps each probability to [min_prob, max_prob] before normalizing.
    Default [1, 99] is a Metaculus constraint - they don't accept 0% or 100%.
    Other sources may have different constraints.

    Args:
        probs: List of raw probability values (as percentages)
        min_prob: Minimum allowed probability (default 1.0)
        max_prob: Maximum allowed probability (default 99.0)

    Returns:
        List of normalized probabilities summing to 1.0
    """
    # Clamp to allowed range
    probs = [max(min(p, max_prob), min_prob) for p in probs]

    # Normalize
    total = sum(probs)
    normed = [p / total for p in probs]

    # Fix rounding error
    normed[-1] += 1.0 - sum(normed)

    return normed


# ============================================================================
# Numeric Percentile Extraction
# ============================================================================


def normalize_percentile_line(s: str) -> str:
    """
    Clean and normalize a line of text for percentile parsing.

    - Normalizes Unicode to NFKC form
    - Replaces Unicode dashes with ASCII hyphen
    - Strips bullet characters from start
    - Removes thousands separators and NBSPs
    - Converts to lowercase
    """
    # Normalize compatibility forms
    s = unicodedata.normalize("NFKC", s)
    # Replace every dash-like char with ASCII hyphen
    s = DASH_RE.sub("-", s)
    # Strip bullets from the start, then strip any remaining whitespace
    s = s.strip().lstrip(BULLET_CHARS).strip()
    # Remove thousands-sep commas & NBSPs
    s = s.replace(",", "").replace("\u00a0", "")
    return s.lower()


def extract_percentiles_from_response(text: str | list, verbose: bool = True) -> dict[int, float]:
    """
    Extract percentiles from numeric forecast response.

    Looks for "Distribution:" anchor then parses lines like:
    - Percentile 1: 15
    - Percentile 5: 20
    - 10: 25 (percentile word optional)

    Args:
        text: LLM response text (or list of lines)
        verbose: Whether to log debug info

    Returns:
        Dictionary mapping percentile keys to values

    Raises:
        ExtractionError: If no valid percentiles extracted
    """
    lines = text if isinstance(text, list) else text.splitlines()
    percentiles = {}
    collecting = False

    for idx, raw in enumerate(lines, 1):
        line = normalize_percentile_line(str(raw))

        if not collecting and "distribution:" in line:
            collecting = True
            if verbose:
                logger.debug(f"Found 'Distribution:' anchor at line {idx}")
            continue

        if not collecting:
            continue

        match = NUM_PATTERN.match(line)
        if not match:
            if verbose:
                logger.debug(f"No match on line {idx}: {line}")
            continue

        key, val_text = match.groups()
        try:
            p = int(key)
            val = float(val_text)
            if p in VALID_PERCENTILE_KEYS:
                percentiles[p] = val
                if verbose:
                    logger.debug(f"Matched Percentile {p}: {val}")
        except Exception as e:
            logger.warning(f"Failed parsing line {idx}: {line} -> {e}")

    if not percentiles:
        snippet = str(text)[-300:] if len(str(text)) > 300 else str(text)
        raise ExtractionError(f"No valid percentiles extracted. Last 300 chars: {snippet!r}")

    return percentiles


def extract_date_percentiles_from_response(
    text: str | list, verbose: bool = True
) -> dict[int, float]:
    """
    Extract date percentiles from forecast response and convert to timestamps.

    Looks for "Distribution:" anchor then parses lines like:
    - Percentile 10: 2026-03-15
    - Percentile 50: 2026-06-01T12:00:00Z

    Args:
        text: LLM response text (or list of lines)
        verbose: Whether to log debug info

    Returns:
        Dictionary mapping percentile keys to Unix timestamps (float)

    Raises:
        ExtractionError: If no valid percentiles extracted
    """
    lines = text if isinstance(text, list) else text.splitlines()
    percentiles = {}
    collecting = False

    for idx, raw in enumerate(lines, 1):
        line = normalize_percentile_line(str(raw))

        if not collecting and "distribution:" in line:
            collecting = True
            if verbose:
                logger.debug(f"Found 'Distribution:' anchor at line {idx}")
            continue

        if not collecting:
            continue

        match = DATE_PATTERN.match(line)
        if not match:
            if verbose:
                logger.debug(f"No date match on line {idx}: {line}")
            continue

        key, date_text = match.groups()
        try:
            p = int(key)
            # Parse date string to timestamp
            timestamp = parse_date_to_timestamp(date_text)
            if p in VALID_PERCENTILE_KEYS and timestamp is not None:
                percentiles[p] = timestamp
                if verbose:
                    logger.debug(f"Matched Percentile {p}: {date_text} -> {timestamp}")
        except Exception as e:
            logger.warning(f"Failed parsing date line {idx}: {line} -> {e}")

    if not percentiles:
        snippet = str(text)[-300:] if len(str(text)) > 300 else str(text)
        raise ExtractionError(f"No valid date percentiles extracted. Last 300 chars: {snippet!r}")

    return percentiles


def parse_date_to_timestamp(date_str: str) -> float | None:
    """
    Parse a date string to Unix timestamp.

    Supports formats:
    - YYYY-MM-DD (assumes midnight UTC)
    - YYYY-MM-DDTHH:MM:SSZ (full ISO format, case-insensitive T/Z)

    Args:
        date_str: Date string to parse

    Returns:
        Unix timestamp as float, or None if parsing fails
    """
    date_str = date_str.strip()

    # Try full ISO format first (handle both uppercase and lowercase T/Z from normalize_percentile_line)
    if "T" in date_str or "t" in date_str:
        try:
            # Normalize to uppercase for parsing
            normalized = date_str.upper()
            # Handle with or without trailing Z
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.timestamp()
        except ValueError:
            pass

    # Try simple YYYY-MM-DD format
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError:
        pass

    return None


def enforce_monotonic_percentiles(pct_dict: dict[int, float]) -> dict[int, float]:
    """
    Ensure strictly increasing values by adding tiny jitter if necessary.

    This fixes cases where the LLM outputs flat percentile values (e.g., P40=10.0, P60=10.0).

    However, if the distribution is fully INVERTED (P1 > P99), this indicates the model
    misunderstood CDF semantics and we raise an error rather than silently corrupting the data.

    Args:
        pct_dict: Dictionary mapping percentile keys to values

    Returns:
        New dictionary with strictly increasing values

    Raises:
        ExtractionError: If percentiles are inverted (P1 > P99)
    """
    sorted_items = sorted(pct_dict.items())

    # Check for inverted distribution (model misunderstood percentile semantics)
    if len(sorted_items) >= 2:
        first_key, first_val = sorted_items[0]
        last_key, last_val = sorted_items[-1]

        if first_val > last_val:
            raise ExtractionError(
                f"Percentiles are inverted: P{first_key}={first_val} > P{last_key}={last_val}. "
                f"Percentile values must increase (P1 should be lowest, P99 highest)."
            )

    # Apply jitter for minor flat spots (e.g., P40=10.0, P60=10.0)
    last_val = -float("inf")
    new_pct_dict = {}

    for p, val in sorted_items:
        if val <= last_val:
            val = last_val + 1e-8  # Add a tiny epsilon
        new_pct_dict[p] = val
        last_val = val

    return new_pct_dict
