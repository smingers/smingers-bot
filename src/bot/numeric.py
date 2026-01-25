"""
Numeric Question Handler

Handles forecasting for numeric/continuous questions.
Produces a 201-point CDF (cumulative distribution function).

Key concepts:
- Percentiles: LLM outputs estimates at key percentiles (1, 5, 10, ..., 95, 99)
- CDF: Cumulative distribution where CDF[i] = P(outcome <= value_i)
- PCHIP interpolation: Smooth monotonic interpolation between percentiles
- Metaculus constraints: CDF[0] >= 0.001, CDF[-1] <= 0.999, max step 0.59
"""

import re
import asyncio
import logging
from typing import Optional
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from ..utils.llm import LLMClient
from ..ensemble.aggregator import EnsembleAggregator, AgentPrediction
from .multiple_choice import ExtractionError

logger = logging.getLogger(__name__)

# Minimum percentiles required for a valid extraction
MIN_REQUIRED_PERCENTILES = 5

# Standard percentiles we ask the LLM to estimate
STANDARD_PERCENTILES = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99]


class NumericForecaster:
    """
    Forecaster for numeric/continuous questions.

    Implements the two-stage process:
    1. Outside view: Establish baseline distribution from reference classes
    2. Inside view: Adjust percentiles based on current evidence (via ensemble)

    Output: 201-point CDF suitable for Metaculus submission.
    """

    def __init__(self, config: dict):
        self.config = config
        self.llm = LLMClient()
        self.aggregator = EnsembleAggregator(
            method=config.get("ensemble", {}).get("aggregation", "weighted_average")
        )
        self.prompts_dir = Path(__file__).parent / "prompts"

    async def forecast(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
        # Numeric-specific parameters
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
        open_lower_bound: bool = True,
        open_upper_bound: bool = True,
        units: str = "",
    ) -> dict:
        """
        Generate a forecast for a numeric question.

        Returns dict with:
        - final_cdf: list[float] (201 values)
        - final_percentiles: dict[int, float]
        - base_percentiles: dict[int, float]
        - agent_predictions: list[AgentPrediction]
        - aggregation: dict
        - outside_view_reasoning: str
        - inside_view_reasoning: dict[agent_name, str]
        """
        # Stage 1: Outside View
        logger.info("Stage 1: Establishing baseline distribution (outside view)")
        base_result = await self._estimate_base_distribution(
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            units=units,
        )

        base_percentiles = base_result["percentiles"]
        outside_view_reasoning = base_result["reasoning"]

        if base_percentiles:
            median = base_percentiles.get(50, "N/A")
            logger.info(f"Base distribution established: median = {median}")
        else:
            logger.warning("Could not extract base percentiles")

        # Stage 2: Inside View (Ensemble)
        logger.info("Stage 2: Adjusting with evidence (inside view)")
        agent_predictions = await self._run_ensemble(
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            research_summary=research_summary,
            base_percentiles=base_percentiles,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            units=units,
        )

        # Stage 3: Aggregate percentiles
        logger.info("Stage 3: Aggregating predictions")
        final_percentiles = self._aggregate_percentiles(agent_predictions)

        # Stage 4: Generate CDF
        logger.info("Stage 4: Generating CDF")
        final_cdf = self._generate_cdf(
            percentiles=final_percentiles,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            open_lower_bound=open_lower_bound,
            open_upper_bound=open_upper_bound,
        )

        median = final_percentiles.get(50, 0)
        logger.info(f"Final prediction: median = {median}")

        # Compile inside view reasoning
        inside_view_reasoning = {
            ap.agent_name: ap.reasoning for ap in agent_predictions
        }

        return {
            "final_cdf": final_cdf,
            "final_percentiles": final_percentiles,
            "base_percentiles": base_percentiles,
            "agent_predictions": agent_predictions,
            "aggregation": {
                "method": self.aggregator.method,
                "num_agents": len(agent_predictions),
            },
            "outside_view_reasoning": outside_view_reasoning,
            "inside_view_reasoning": inside_view_reasoning,
        }

    async def _estimate_base_distribution(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        lower_bound: Optional[float],
        upper_bound: Optional[float],
        units: str,
    ) -> dict:
        """Estimate the base distribution using outside view reasoning."""
        template_path = self.prompts_dir / "outside_view_numeric.md"
        with open(template_path) as f:
            template = f.read()

        # Format bounds for display
        bounds_str = self._format_bounds(lower_bound, upper_bound, units)

        prompt = template.format(
            question_title=question_title,
            question_text=question_text[:3000],
            resolution_criteria=resolution_criteria[:1000],
            bounds=bounds_str,
            units=units or "units",
            percentiles=", ".join(str(p) for p in STANDARD_PERCENTILES),
        )

        # Get model from config (mode-aware)
        active_models = self.config.get("_active_models", {})
        model = active_models.get(
            "base_rate_estimator",
            self.config.get("models", {}).get("base_rate_estimator", "claude-sonnet-4-5-20250929")
        )

        response = await self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
        )

        reasoning = response.content
        percentiles = self._extract_percentiles(reasoning)

        try:
            percentiles = self._validate_percentiles(
                percentiles, "Base rate estimation (outside view)", reasoning
            )
        except ExtractionError as e:
            raise ExtractionError(
                str(e),
                agent_name="base_rate_estimator",
                response_preview=e.response_preview
            ) from e

        return {
            "percentiles": percentiles,
            "reasoning": reasoning,
            "prompt": prompt,
        }

    async def _run_ensemble(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
        base_percentiles: dict[int, float],
        lower_bound: Optional[float],
        upper_bound: Optional[float],
        units: str,
    ) -> list[AgentPrediction]:
        """Run all ensemble agents in parallel."""
        # Get agents from mode-aware config
        agents_config = self.config.get("_active_agents", [])

        if not agents_config:
            # Fallback to old config format
            agents_config = self.config.get("ensemble", {}).get("agents", [])

        if not agents_config:
            agents_config = [{
                "name": "default",
                "model": "claude-sonnet-4-5-20250929",
                "weight": 1.0,
                "role_description": "You are a balanced forecaster.",
            }]

        template_path = self.prompts_dir / "inside_view_numeric.md"
        with open(template_path) as f:
            template = f.read()

        bounds_str = self._format_bounds(lower_bound, upper_bound, units)
        base_dist_str = self._format_percentiles(base_percentiles)

        tasks = []
        for agent in agents_config:
            task = self._run_single_agent(
                agent=agent,
                template=template,
                question_title=question_title,
                question_text=question_text,
                resolution_criteria=resolution_criteria,
                research_summary=research_summary,
                base_distribution=base_dist_str,
                bounds=bounds_str,
                units=units,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        predictions = []
        extraction_errors = []

        for result, agent in zip(results, agents_config):
            if isinstance(result, ExtractionError):
                # Extraction errors are fatal - collect them and fail
                extraction_errors.append(result)
                logger.error(f"EXTRACTION FAILED for agent {agent['name']}: {result}")
            elif isinstance(result, Exception):
                # Other errors (network, API, etc.) - log and skip agent
                logger.error(f"Agent {agent['name']} failed: {result}")
                continue
            else:
                predictions.append(result)

        # If ANY extraction failed, fail the entire forecast
        if extraction_errors:
            failed_agents = [e.agent_name for e in extraction_errors]
            raise ExtractionError(
                f"Percentile extraction failed for {len(extraction_errors)} agent(s): {failed_agents}. "
                f"Cannot produce reliable forecast. First error: {extraction_errors[0]}",
                agent_name=", ".join(failed_agents)
            )

        return predictions

    async def _run_single_agent(
        self,
        agent: dict,
        template: str,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
        base_distribution: str,
        bounds: str,
        units: str,
    ) -> AgentPrediction:
        """Run a single ensemble agent."""
        agent_name = agent.get("name", "unnamed")
        model = agent.get("model", "claude-sonnet-4-5-20250929")
        weight = agent.get("weight", 1.0)
        role_description = agent.get("role_description", "You are a forecaster.")

        prompt = template.format(
            agent_role=agent_name,
            role_description=role_description,
            question_title=question_title,
            question_text=question_text[:3000],
            resolution_criteria=resolution_criteria[:1000],
            base_distribution=base_distribution,
            bounds=bounds,
            units=units or "units",
            research_summary=research_summary[:5000],
            percentiles=", ".join(str(p) for p in STANDARD_PERCENTILES),
        )

        response = await self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
        )

        reasoning = response.content
        percentiles = self._extract_percentiles(reasoning)

        try:
            percentiles = self._validate_percentiles(
                percentiles, f"Agent '{agent_name}' ({model})", reasoning
            )
        except ExtractionError as e:
            raise ExtractionError(
                str(e),
                agent_name=agent_name,
                response_preview=e.response_preview
            ) from e

        return AgentPrediction(
            agent_name=agent_name,
            model=model,
            weight=weight,
            prediction=percentiles.get(50, 0),  # Median as scalar prediction
            reasoning=reasoning,
            percentiles=percentiles,
        )

    def _extract_percentiles(self, text: str) -> dict[int, float]:
        """
        Extract percentile values from LLM response.

        Looks for patterns like:
        - "Percentile 50: 1234.5"
        - "50th percentile: 1234.5"
        - "P50: 1234.5"
        - Distribution table format
        """
        percentiles = {}

        # Clean the text - normalize unicode, remove thousands separators
        text = self._clean_text(text)

        # Pattern 1: "Percentile X: Y" or "Percentile X = Y"
        pattern1 = re.findall(
            r"percentile\s*(\d{1,2})\s*[:=]\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?(?:e[+-]?\d+)?)",
            text,
            re.IGNORECASE
        )
        for pct, val in pattern1:
            pct = int(pct)
            if pct in STANDARD_PERCENTILES:
                percentiles[pct] = self._parse_number(val)

        # Pattern 2: "Xth percentile: Y"
        pattern2 = re.findall(
            r"(\d{1,2})(?:st|nd|rd|th)\s*percentile\s*[:=]\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?(?:e[+-]?\d+)?)",
            text,
            re.IGNORECASE
        )
        for pct, val in pattern2:
            pct = int(pct)
            if pct in STANDARD_PERCENTILES:
                percentiles[pct] = self._parse_number(val)

        # Pattern 3: "PX: Y" or "P(X): Y"
        pattern3 = re.findall(
            r"P\(?(\d{1,2})\)?\s*[:=]\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?(?:e[+-]?\d+)?)",
            text,
            re.IGNORECASE
        )
        for pct, val in pattern3:
            pct = int(pct)
            if pct in STANDARD_PERCENTILES:
                percentiles[pct] = self._parse_number(val)

        # Pattern 4: Look for "Distribution:" section with tabular data
        dist_match = re.search(
            r"distribution:?\s*\n((?:[-\s\d.:,eE+]+\n?)+)",
            text,
            re.IGNORECASE
        )
        if dist_match:
            lines = dist_match.group(1).strip().split("\n")
            for line in lines:
                # Try to extract "X: Y" or "X - Y" patterns
                match = re.search(r"(\d{1,2})\s*[:|-]\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?(?:e[+-]?\d+)?)", line)
                if match:
                    pct = int(match.group(1))
                    if pct in STANDARD_PERCENTILES:
                        percentiles[pct] = self._parse_number(match.group(2))

        return percentiles

    def _validate_percentiles(self, percentiles: dict[int, float], context: str, text: str) -> dict[int, float]:
        """
        Validate extracted percentiles - raise ExtractionError if insufficient.

        Args:
            percentiles: The extracted percentiles
            context: Description of where this came from (for error messages)
            text: Original response text (for error preview)
        """
        if len(percentiles) < MIN_REQUIRED_PERCENTILES:
            response_preview = text[:500] + "..." if len(text) > 500 else text
            raise ExtractionError(
                f"{context}: Could not extract sufficient percentiles from response. "
                f"Got {len(percentiles)} percentiles, need at least {MIN_REQUIRED_PERCENTILES}. "
                f"Extracted: {list(percentiles.keys())}",
                response_preview=response_preview
            )
        return percentiles

    def _aggregate_percentiles(
        self,
        predictions: list[AgentPrediction],
    ) -> dict[int, float]:
        """Aggregate percentiles from multiple agents using weighted average."""
        if not predictions:
            return {}

        total_weight = sum(p.weight for p in predictions if p.percentiles)

        aggregated = {}
        for pct in STANDARD_PERCENTILES:
            weighted_sum = 0.0
            weight_sum = 0.0
            for p in predictions:
                if p.percentiles and pct in p.percentiles:
                    weighted_sum += p.percentiles[pct] * p.weight
                    weight_sum += p.weight
            if weight_sum > 0:
                aggregated[pct] = weighted_sum / weight_sum

        return aggregated

    def _generate_cdf(
        self,
        percentiles: dict[int, float],
        lower_bound: Optional[float],
        upper_bound: Optional[float],
        open_lower_bound: bool,
        open_upper_bound: bool,
        num_points: int = 201,
    ) -> list[float]:
        """
        Generate a 201-point CDF from percentile estimates.

        Uses PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) for
        smooth, monotonic interpolation.
        """
        if not percentiles or len(percentiles) < MIN_REQUIRED_PERCENTILES:
            # This should not happen if validation is working, but fail loudly if it does
            raise ExtractionError(
                f"Cannot generate CDF: insufficient percentiles. "
                f"Got {len(percentiles)}, need at least {MIN_REQUIRED_PERCENTILES}.",
                agent_name="cdf_generator"
            )

        # Sort percentiles by percentile value
        sorted_pcts = sorted(percentiles.items())
        x_vals = np.array([p for p, _ in sorted_pcts])  # percentiles (0-100 scale)
        y_vals = np.array([v for _, v in sorted_pcts])  # values

        # Handle duplicate y values (add small epsilon to maintain strict monotonicity)
        for i in range(1, len(y_vals)):
            if y_vals[i] <= y_vals[i - 1]:
                y_vals[i] = y_vals[i - 1] + 1e-9

        # Create interpolator
        # x_vals are percentiles (1, 5, 10, ...), y_vals are the actual values
        # We want to invert this: given a value, what's the percentile (CDF)?
        try:
            # First, create a mapping from values to percentiles
            value_to_pct = PchipInterpolator(y_vals, x_vals / 100.0, extrapolate=True)

            # Determine the range of values for the CDF
            min_val = lower_bound if lower_bound is not None else y_vals[0] - (y_vals[-1] - y_vals[0]) * 0.1
            max_val = upper_bound if upper_bound is not None else y_vals[-1] + (y_vals[-1] - y_vals[0]) * 0.1

            # Create evenly spaced values
            values = np.linspace(min_val, max_val, num_points)

            # Get CDF values
            cdf = value_to_pct(values)

        except Exception as e:
            logger.warning(f"PCHIP interpolation failed: {e}, using linear")
            # Fallback to linear interpolation
            cdf = np.interp(
                np.linspace(0, 100, num_points),
                x_vals,
                np.linspace(0, 1, len(x_vals))
            )

        # Convert to list and enforce constraints
        cdf = cdf.tolist()

        # Ensure monotonicity
        for i in range(1, len(cdf)):
            if cdf[i] < cdf[i - 1]:
                cdf[i] = cdf[i - 1]

        # Enforce bounds based on open/closed
        min_cdf = 0.001 if open_lower_bound else 0.0
        max_cdf = 0.999 if open_upper_bound else 1.0

        cdf = [max(min_cdf, min(max_cdf, v)) for v in cdf]

        # Ensure first and last values
        cdf[0] = max(cdf[0], min_cdf)
        cdf[-1] = min(cdf[-1], max_cdf)

        # Enforce max step size (Metaculus requires no single step > 0.59)
        for i in range(1, len(cdf)):
            if cdf[i] - cdf[i - 1] > 0.59:
                cdf[i] = cdf[i - 1] + 0.59

        # Final monotonicity pass
        for i in range(1, len(cdf)):
            if cdf[i] < cdf[i - 1]:
                cdf[i] = cdf[i - 1]

        return cdf

    def _format_bounds(
        self,
        lower_bound: Optional[float],
        upper_bound: Optional[float],
        units: str,
    ) -> str:
        """Format bounds for display in prompts."""
        parts = []
        if lower_bound is not None:
            parts.append(f"Lower bound: {lower_bound} {units}")
        if upper_bound is not None:
            parts.append(f"Upper bound: {upper_bound} {units}")
        if not parts:
            return "No explicit bounds specified"
        return ", ".join(parts)

    def _format_percentiles(self, percentiles: dict[int, float]) -> str:
        """Format percentiles for display in prompts."""
        if not percentiles:
            return "No base distribution available"
        lines = []
        for pct in sorted(percentiles.keys()):
            lines.append(f"Percentile {pct}: {percentiles[pct]:.4g}")
        return "\n".join(lines)

    def _clean_text(self, text: str) -> str:
        """Clean text for parsing - normalize unicode, remove formatting."""
        import unicodedata
        # Normalize unicode
        text = unicodedata.normalize("NFKC", text)
        # Replace various dash types with hyphen
        text = re.sub(r"[–—−]", "-", text)
        return text

    def _parse_number(self, s: str) -> float:
        """Parse a number string, handling commas and scientific notation."""
        s = s.replace(",", "")
        return float(s)
