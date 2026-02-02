"""
Pipeline metrics dataclasses for tracking tool usage, costs, and timing.

These typed dataclasses replace the untyped nested dictionaries previously used
for tracking metrics throughout the forecasting pipeline. Benefits:
- Clear schema documentation
- IDE autocomplete support
- Type checking catches typos in field names
- Easier to understand and maintain
"""

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class StepMetrics:
    """
    Metrics for a single forecasting step (Step 1 or Step 2).

    Attributes:
        token_input: Number of input tokens used
        token_output: Number of output tokens generated
        cost: LLM cost in dollars
        duration_seconds: Wall-clock time for the step
        error: Error message if the step failed, None otherwise

    Note: `searched` and `queries` fields are kept for backward compatibility with
    the artifact JSON schema (tool_usage.json). They are always False/empty for
    forecasting steps but must be present for consistent serialization.
    """
    # Legacy fields for artifact schema compatibility (always False/empty for forecaster steps)
    searched: bool = False
    queries: list[str] = field(default_factory=list)
    token_input: int = 0
    token_output: int = 0
    cost: float = 0.0
    duration_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AgentMetrics:
    """
    Metrics for a single forecasting agent across both steps.

    Attributes:
        model: LLM model identifier (e.g., "openrouter/anthropic/claude-sonnet-4.5")
        weight: Agent weight for ensemble aggregation
        step1: Metrics for Step 1 (outside view)
        step2: Metrics for Step 2 (inside view)
    """
    model: str
    weight: float
    step1: StepMetrics = field(default_factory=StepMetrics)
    step2: StepMetrics = field(default_factory=StepMetrics)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "weight": self.weight,
            "step1": self.step1.to_dict(),
            "step2": self.step2.to_dict(),
        }


@dataclass
class ResearchMetrics:
    """
    Metrics from centralized research (search pipeline).

    These fields come from SearchPipeline.execute_searches_from_response() metadata.

    Attributes:
        search_id: Identifier for this search batch (e.g., "historical", "current")
        searched: Whether any searches were executed
        num_queries: Number of queries processed
        queries: List of query details (query text, tool, success, num_results)
        tools_used: List of search tools used (e.g., ["Google", "AskNews"])
        llm_cost: Total LLM cost for research (summarization + agentic)
        llm_cost_summarization: LLM cost for article summarization
        llm_cost_agentic: LLM cost for agentic search
        error: Error message if research failed
    """
    search_id: str = ""
    searched: bool = False
    num_queries: int = 0
    queries: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    llm_cost: float = 0.0
    llm_cost_summarization: float = 0.0
    llm_cost_agentic: float = 0.0
    error: str | None = None

    @classmethod
    def from_search_metadata(cls, metadata: dict[str, Any]) -> "ResearchMetrics":
        """Create from search pipeline metadata dictionary."""
        return cls(
            search_id=metadata.get("search_id", ""),
            searched=metadata.get("searched", False),
            num_queries=metadata.get("num_queries", 0),
            queries=metadata.get("queries", []),
            tools_used=metadata.get("tools_used", []),
            llm_cost=metadata.get("llm_cost", 0.0),
            llm_cost_summarization=metadata.get("llm_cost_summarization", 0.0),
            llm_cost_agentic=metadata.get("llm_cost_agentic", 0.0),
            error=metadata.get("error"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class PipelineMetrics:
    """
    Complete metrics for a forecasting pipeline run.

    Attributes:
        centralized_research: Research metrics keyed by search_id ("historical", "current")
        agents: Agent metrics keyed by agent_id ("forecaster_1", ..., "forecaster_5")
        step_costs: Cost breakdown by pipeline step
        total_pipeline_cost: Total cost for the entire pipeline run
    """
    centralized_research: dict[str, ResearchMetrics] = field(default_factory=dict)
    agents: dict[str, AgentMetrics] = field(default_factory=dict)
    step_costs: dict[str, float] = field(default_factory=dict)
    total_pipeline_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        This produces the same structure as the legacy untyped dict,
        ensuring backward compatibility with artifact storage.
        """
        return {
            "centralized_research": {
                k: v.to_dict() for k, v in self.centralized_research.items()
            },
            "agents": {
                k: v.to_dict() for k, v in self.agents.items()
            },
            "step_costs": self.step_costs,
            "total_pipeline_cost": self.total_pipeline_cost,
        }

    @classmethod
    def create_empty(cls) -> "PipelineMetrics":
        """Create an empty metrics object ready for population."""
        return cls(
            centralized_research={
                "historical": ResearchMetrics(search_id="historical"),
                "current": ResearchMetrics(search_id="current"),
            },
            agents={},
            step_costs={},
            total_pipeline_cost=0.0,
        )
