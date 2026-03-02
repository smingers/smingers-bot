"""
Typed intermediate data structures for the forecasting pipeline.

These dataclasses define the "contract" between pipeline steps, making each step
independently callable and testable. Instead of data flowing as local variables
inside a single monolithic method, each step produces a typed output that the
next step consumes.

Pipeline flow:
    ResearchContext → OutsideViewResult → CrossPollinatedContext → InsideViewResult → EnsembleResult
"""

from dataclasses import dataclass, field
from typing import Any

from .extractors import AgentResult
from .metrics import ResearchMetrics


@dataclass
class ResearchContext:
    """
    Output of the research phase (steps 1-2).

    Contains the formatted search results split into historical and current context,
    plus metrics about the research queries and tools used. pre_research_context is
    the standalone pre-research (scraped/summarized content from links in the question
    fields); it is also prepended to historical_context, but kept separate so the
    supervisor can receive it as primary-source evidence.
    """

    historical_context: str
    current_context: str
    metrics: dict[str, ResearchMetrics] = field(default_factory=dict)
    pre_research_context: str = ""


@dataclass
class OutsideViewResult:
    """
    Output of the outside view phase (step 3).

    Contains one output per forecaster (5 total). Forecasters that reuse another's
    output will have the same string. Failed outputs are marked with the
    _FAILED_OUTPUT_PREFIX sentinel.
    """

    outputs: list[str]
    reasoning: dict[int, str] = field(default_factory=dict)
    prompt: str = ""


@dataclass
class CrossPollinatedContext:
    """
    Output of the cross-pollination phase (step 4).

    Maps each forecaster index to its enriched context string, which combines
    current_context with another forecaster's outside view output per the
    CROSS_POLLINATION_MAP.
    """

    context_map: dict[int, str] = field(default_factory=dict)


@dataclass
class InsideViewResult:
    """
    Output of the inside view phase (step 5).

    Contains one output per forecaster. Outputs may be strings (success) or
    Exceptions (failure). Reasoning content is tracked separately by index.
    """

    outputs: list[str | Exception] = field(default_factory=list)
    reasoning: dict[int, str] = field(default_factory=dict)


@dataclass
class EnsembleResult:
    """
    Output of extraction + aggregation (step 6).

    Contains per-forecaster AgentResult objects (with extracted predictions and
    errors) plus the aggregated final prediction.
    """

    agent_results: list[AgentResult] = field(default_factory=list)
    final_prediction: Any = None
