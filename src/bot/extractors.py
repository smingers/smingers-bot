"""
Probability and percentile extraction from LLM responses.

This module consolidates extraction logic from the question handlers,
making it testable and reusable across all question types.
"""

import re
import logging
import unicodedata
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

# Valid percentile keys for numeric questions
VALID_PERCENTILE_KEYS: set[int] = {1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99}

# Regex for parsing percentile lines
NUM_PATTERN = re.compile(
    r"^(?:percentile\s*)?(\d{1,3})\s*[:\-]\s*([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*$",
    re.IGNORECASE
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
        ValueError: If no probability found
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
    raise ValueError(f"Could not extract probability from response. Last 200 chars: {snippet!r}")


# ============================================================================
# Multiple Choice Probability Extraction
# ============================================================================

def extract_multiple_choice_probabilities(
    text: str,
    num_options: int,
) -> List[float]:
    """
    Extract option probabilities from multiple choice forecast response.

    Looks for "Probabilities: [X, Y, Z]" pattern.

    Args:
        text: LLM response text
        num_options: Expected number of options

    Returns:
        List of probabilities as floats (raw values, not normalized)

    Raises:
        ValueError: If no probabilities found or wrong number
    """
    matches = re.findall(r"Probabilities:\s*\[([0-9.,\s]+)\]", text)
    if not matches:
        snippet = text[-200:] if len(text) > 200 else text
        raise ValueError(f"Could not extract 'Probabilities' list from response. Last 200 chars: {snippet!r}")

    last_match = matches[-1]
    numbers = [float(n.strip()) for n in last_match.split(",") if n.strip()]

    if len(numbers) != num_options:
        raise ValueError(f"Expected {num_options} probabilities, got {len(numbers)}: {numbers}")

    return numbers


def normalize_probabilities(probs: List[float]) -> List[float]:
    """
    Normalize probabilities to sum to 1.0.

    Clamps each probability to [1, 99] before normalizing. This is a Metaculus
    platform constraint - they don't accept 0% or 100% for any option.

    Args:
        probs: List of raw probability values (as percentages)

    Returns:
        List of normalized probabilities summing to 1.0
    """
    # Clamp to [1, 99] (Metaculus constraint: no 0% or 100%)
    probs = [max(min(p, 99), 1) for p in probs]

    # Normalize
    total = sum(probs)
    normed = [p / total for p in probs]

    # Fix rounding error
    normed[-1] += 1.0 - sum(normed)

    return normed


# ============================================================================
# Numeric Percentile Extraction
# ============================================================================

def clean_line(s: str) -> str:
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
    s = s.replace(",", "").replace("\u00A0", "")
    return s.lower()


def extract_percentiles_from_response(
    text: Union[str, List],
    verbose: bool = True
) -> Dict[int, float]:
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
        ValueError: If no valid percentiles extracted
    """
    lines = text if isinstance(text, list) else text.splitlines()
    percentiles = {}
    collecting = False

    for idx, raw in enumerate(lines, 1):
        line = clean_line(str(raw))

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
        raise ValueError(f"No valid percentiles extracted. Last 300 chars: {snippet!r}")

    return percentiles


def enforce_strict_increasing(pct_dict: Dict[int, float]) -> Dict[int, float]:
    """
    Ensure strictly increasing values by adding tiny jitter if necessary.

    This fixes cases where the LLM outputs flat or decreasing percentile values.

    Args:
        pct_dict: Dictionary mapping percentile keys to values

    Returns:
        New dictionary with strictly increasing values
    """
    sorted_items = sorted(pct_dict.items())
    last_val = -float('inf')
    new_pct_dict = {}

    for p, v in sorted_items:
        if v <= last_val:
            v = last_val + 1e-8  # Add a tiny epsilon
        new_pct_dict[p] = v
        last_val = v

    return new_pct_dict
