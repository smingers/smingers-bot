"""
Numeric Question Handler - Port from Panshul42's tournament-winning implementation

5-agent ensemble pipeline with CDF generation:
1. Generate historical + current search queries
2. Execute searches
3. Run 5 agents on Step 1 (percentile estimation with historical context)
4. Run 5 agents on Step 2 (refined percentiles with current context + step 1 output)
5. Extract percentiles, generate CDFs, and aggregate

Output: 201-point CDF for Metaculus submission
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Union
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import PchipInterpolator

from ..utils.llm import LLMClient
from ..storage.artifact_store import ArtifactStore
from .handler_mixin import ForecasterMixin
from .extractors import (
    extract_percentiles_from_response,
    enforce_strict_increasing,
    VALID_PERCENTILE_KEYS,
)
from .prompts import (
    NUMERIC_PROMPT_HISTORICAL,
    NUMERIC_PROMPT_CURRENT,
    NUMERIC_PROMPT_1,
    NUMERIC_PROMPT_2,
    CLAUDE_CONTEXT,
    GPT_CONTEXT,
)
from .search import SearchPipeline, QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from a single forecasting agent."""
    agent_id: str
    model: str
    weight: float
    step1_output: str
    step2_output: str
    percentiles: Optional[Dict[int, float]] = None
    cdf: Optional[List[float]] = None
    error: Optional[str] = None


@dataclass
class NumericForecastResult:
    """Complete result from numeric forecasting pipeline."""
    final_cdf: List[float]  # 201-point CDF
    agent_results: List[AgentResult]
    historical_context: str
    current_context: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def _safe_cdf_bounds(cdf: np.ndarray, open_lower: bool, open_upper: bool, step: float) -> np.ndarray:
    """
    Enforce Metaculus CDF requirements:
    - For open bounds: cdf[0] >= 0.001, cdf[-1] <= 0.999
    - No single step may exceed 0.59
    """
    # Pin tails to legal open-bound limits
    if open_lower:
        cdf[0] = max(cdf[0], 0.001)
    if open_upper:
        cdf[-1] = min(cdf[-1], 0.999)

    # Enforce the 0.59 maximum step rule
    big_jumps = np.where(np.diff(cdf) > 0.59)[0]
    for idx in big_jumps:
        excess = cdf[idx + 1] - cdf[idx] - 0.59
        # Spread the excess evenly over the remaining points
        span = len(cdf) - idx - 1
        cdf[idx + 1:] -= excess * np.linspace(1, 0, span)
        # Re-monotonise
        cdf[idx + 1:] = np.maximum.accumulate(cdf[idx + 1:])

    return cdf


def generate_continuous_cdf(
    percentile_values: Dict,
    open_upper_bound: bool,
    open_lower_bound: bool,
    upper_bound: float,
    lower_bound: float,
    zero_point: Optional[float] = None,
    *,
    min_step: float = 5.0e-5,
    num_points: int = 201,
) -> List[float]:
    """
    Generate a 201-point continuous CDF with strict enforcement of Metaculus requirements.

    Args:
        percentile_values: Dictionary mapping percentiles (1-99) to values
        open_upper_bound: Whether the upper bound is open
        open_lower_bound: Whether the lower bound is open
        upper_bound: Maximum possible value
        lower_bound: Minimum possible value
        zero_point: Reference point for non-linear scaling
        min_step: Minimum step size between adjacent CDF points
        num_points: Number of points in the output CDF (default: 201)

    Returns:
        List of CDF values (length 201)
    """
    # Validate inputs
    if not percentile_values:
        raise ValueError("Empty percentile values dictionary")

    if upper_bound <= lower_bound:
        raise ValueError(f"Upper bound ({upper_bound}) must be greater than lower bound ({lower_bound})")

    if zero_point is not None:
        if abs(zero_point - lower_bound) < 1e-6 or abs(zero_point - upper_bound) < 1e-6:
            raise ValueError(f"zero_point ({zero_point}) too close to bounds [{lower_bound}, {upper_bound}]")

    # Clean and validate percentile values
    pv = {}
    for k, v in percentile_values.items():
        try:
            k_float = float(k)
            v_float = float(v)

            if not (0 < k_float < 100):
                continue  # Skip invalid percentiles

            if not np.isfinite(v_float):
                continue  # Skip non-finite values

            pv[k_float] = v_float
        except (ValueError, TypeError):
            continue  # Skip non-numeric entries

    if len(pv) < 2:
        raise ValueError(f"Need at least 2 valid percentile points (got {len(pv)})")

    # Handle duplicate values by adding small offsets
    vals_seen = {}
    for k in sorted(pv):
        v = pv[k]
        if v in vals_seen:
            # Add progressively larger offsets for duplicate values
            v += (len(vals_seen[v]) + 1) * 1e-9
        vals_seen.setdefault(v, []).append(k)
        pv[k] = v

    # Create arrays of percentiles and values
    percentiles, values = zip(*sorted(pv.items()))
    percentiles = np.array(percentiles) / 100.0  # Convert to [0,1] range
    values = np.array(values)

    # Check if values are strictly increasing after de-duplication
    if np.any(np.diff(values) <= 0):
        raise ValueError("Percentile values must be strictly increasing after de-duplication")

    # Add boundary points if needed
    if not open_lower_bound and lower_bound < values[0] - 1e-9:
        percentiles = np.insert(percentiles, 0, 0.0)
        values = np.insert(values, 0, lower_bound)

    if not open_upper_bound and upper_bound > values[-1] + 1e-9:
        percentiles = np.append(percentiles, 1.0)
        values = np.append(values, upper_bound)

    # Determine if log scaling is appropriate (all values positive)
    use_log = np.all(values > 0)
    x_vals = np.log(values) if use_log else values

    # Create interpolator with fallback
    try:
        spline = PchipInterpolator(x_vals, percentiles, extrapolate=True)
    except Exception as e:
        # Fallback to linear interpolation
        logger.warning(f"PchipInterpolator failed ({e}), falling back to linear interpolation")
        def spline(x):
            return np.interp(x, x_vals, percentiles)

    # Generate evaluation grid based on zero_point
    def create_grid(num_pts):
        t = np.linspace(0, 1, num_pts)

        if zero_point is None:
            # Linear grid
            return lower_bound + (upper_bound - lower_bound) * t
        else:
            # Non-linear grid based on zero_point
            ratio = (upper_bound - zero_point) / (lower_bound - zero_point)
            # Handle potential numerical issues
            if abs(ratio - 1.0) < 1e-10:
                return lower_bound + (upper_bound - lower_bound) * t
            else:
                return np.array([
                    lower_bound + (upper_bound - lower_bound) *
                    ((ratio ** tt - 1) / (ratio - 1))
                    for tt in t
                ])

    # Generate the grid and evaluate
    cdf_x = create_grid(num_points)

    # Handle log transformation for evaluation
    eval_x = np.log(cdf_x) if use_log else cdf_x

    # Clamp values to avoid extrapolation issues
    eval_x_clamped = np.clip(eval_x, x_vals[0], x_vals[-1])

    # Generate initial CDF values and clamp to [0,1]
    cdf_y = spline(eval_x_clamped).clip(0.0, 1.0)

    # Ensure monotonicity (non-decreasing)
    cdf_y = np.maximum.accumulate(cdf_y)

    # Set boundary values if bounds are closed
    if not open_lower_bound:
        cdf_y[0] = 0.0
    if not open_upper_bound:
        cdf_y[-1] = 1.0

    # Strict enforcement of minimum step size
    def enforce_min_steps(y_values, min_step_size):
        """Enforce minimum step size between adjacent points."""
        result = y_values.copy()

        # First pass: enforce minimum steps
        for i in range(1, len(result)):
            if result[i] < result[i - 1] + min_step_size:
                result[i] = min(result[i - 1] + min_step_size, 1.0)

        # Second pass: ensure we don't exceed 1.0
        if result[-1] > 1.0:
            overflow_idx = np.where(result > 1.0)[0][0]
            steps_remaining = len(result) - overflow_idx

            for i in range(overflow_idx, len(result)):
                t = (i - overflow_idx) / max(1, steps_remaining - 1)
                result[i] = min(1.0, result[overflow_idx - 1] + (1.0 - result[overflow_idx - 1]) * t)

            # Final check for minimum steps
            for i in range(overflow_idx, len(result)):
                if i > overflow_idx and result[i] < result[i - 1] + min_step_size:
                    result[i] = result[i - 1] + min_step_size
                    if result[i] > 1.0:
                        result[i] = 1.0
                        for j in range(i - 1, overflow_idx - 1, -1):
                            max_allowed = result[j + 1] - min_step_size
                            if result[j] > max_allowed:
                                result[j] = max_allowed

        return result

    # Apply strict step enforcement
    cdf_y = enforce_min_steps(cdf_y, min_step)
    cdf_y = _safe_cdf_bounds(cdf_y, open_lower_bound, open_upper_bound, min_step)

    # Double-check minimum step size requirement
    steps = np.diff(cdf_y)
    if np.any(steps < min_step):
        logger.warning("Minimum step size still violated. Using aggressive step enforcement.")

        if not open_lower_bound:
            start_val = 0.0
        else:
            start_val = cdf_y[0]

        if not open_upper_bound:
            end_val = 1.0
        else:
            end_val = min(cdf_y[-1], 1.0)

        available_range = end_val - start_val
        required_range = (len(cdf_y) - 1) * min_step

        if required_range > available_range:
            raise ValueError(
                f"Cannot satisfy minimum step requirement: need {required_range:.6f} "
                f"but only have {available_range:.6f} available in CDF range"
            )

        # Create a new CDF with exactly min_step between points where needed
        new_cdf = np.zeros_like(cdf_y)
        new_cdf[0] = start_val

        if len(cdf_y) > 2:
            orig_shape = np.diff(cdf_y)
            orig_shape = np.maximum(orig_shape, min_step)
            orig_shape = orig_shape / np.sum(orig_shape)

            remaining = available_range - (len(cdf_y) - 1) * min_step
            extra_steps = remaining * orig_shape

            for i in range(1, len(new_cdf)):
                new_cdf[i] = new_cdf[i - 1] + min_step + extra_steps[i - 1]
        else:
            for i in range(1, len(new_cdf)):
                new_cdf[i] = new_cdf[i - 1] + (available_range / (len(new_cdf) - 1))

        cdf_y = new_cdf

    # Final validation
    if np.any(np.diff(cdf_y) < min_step - 1e-10):
        problematic_indices = np.where(np.diff(cdf_y) < min_step - 1e-10)[0]
        raise RuntimeError(f"Failed to enforce minimum step size at indices: {problematic_indices}")

    return cdf_y.tolist()


class NumericForecaster(ForecasterMixin):
    """
    Numeric question forecaster using Panshul42's 5-agent ensemble.

    Generates a 201-point CDF for Metaculus submission.
    """

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        artifact_store: Optional[ArtifactStore] = None,
    ):
        self.config = config
        self.llm = llm_client or LLMClient()
        self.artifact_store = artifact_store

    async def forecast(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        fine_print: str,
        open_upper_bound: bool,
        open_lower_bound: bool,
        upper_bound: float,
        lower_bound: float,
        zero_point: Optional[float] = None,
        unit: str = "(unknown)",
        write: callable = print,
    ) -> NumericForecastResult:
        """
        Generate a forecast for a numeric question.

        Returns:
            NumericForecastResult with 201-point CDF and all agent outputs
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Question details for search
        question_details = QuestionDetails(
            title=question_title,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            description=question_text,
        )

        # Build bound messages and hint
        lower_bound_msg = "" if open_lower_bound else f"Cannot go below {lower_bound}."
        upper_bound_msg = "" if open_upper_bound else f"Cannot go above {upper_bound}."
        hint = f"The answer is expected to be above {lower_bound} and below {upper_bound}. Think carefully, and reconsider your sources, if your projections are outside this range."

        # =========================================================================
        # STEP 1: Generate historical and current search queries
        # =========================================================================
        write("\n=== Step 1: Generating search queries ===")

        historical_prompt = NUMERIC_PROMPT_HISTORICAL.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            lower_bound_message=lower_bound_msg,
            upper_bound_message=upper_bound_msg,
            units=unit,
            hint=hint,
        )
        current_prompt = NUMERIC_PROMPT_CURRENT.format(
            title=question_title,
            today=today,
            background=question_text,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            lower_bound_message=lower_bound_msg,
            upper_bound_message=upper_bound_msg,
            units=unit,
            hint=hint,
        )

        query_model = self._get_model("query_generator", "openrouter/openai/o3")

        historical_output, current_output = await asyncio.gather(
            self._call_model(query_model, historical_prompt),
            self._call_model(query_model, current_prompt),
        )

        write(f"\nHistorical query output:\n{historical_output[:500]}...")
        write(f"\nCurrent query output:\n{current_output[:500]}...")

        if self.artifact_store:
            self.artifact_store.save_query_generation("historical", historical_prompt, historical_output)
            self.artifact_store.save_query_generation("current", current_prompt, current_output)

        # =========================================================================
        # STEP 2: Execute searches
        # =========================================================================
        write("\n=== Step 2: Executing searches ===")

        async with SearchPipeline(self.config, self.llm) as search:
            historical_context, current_context = await asyncio.gather(
                search.process_search_queries(historical_output, "-1", question_details),
                search.process_search_queries(current_output, "0", question_details),
            )

        write(f"\nHistorical context ({len(historical_context)} chars)")
        write(f"Current context ({len(current_context)} chars)")

        if self.artifact_store:
            self.artifact_store.save_search_results("historical", {"context": historical_context})
            self.artifact_store.save_search_results("current", {"context": current_context})

        # =========================================================================
        # STEP 3: Run 5 agents on Step 1
        # =========================================================================
        write("\n=== Step 3: Running Step 1 ===")

        agents = self._get_agents()

        step1_prompt = NUMERIC_PROMPT_1.format(
            title=question_title,
            today=today,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            context=historical_context,
            units=unit,
            lower_bound_message=lower_bound_msg,
            upper_bound_message=upper_bound_msg,
            hint=hint,
        )

        step1_tasks = []
        for agent in agents:
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT
            step1_tasks.append(self._call_model(model, step1_prompt, system_prompt=system_prompt))

        step1_outputs = await asyncio.gather(*step1_tasks, return_exceptions=True)

        for i, output in enumerate(step1_outputs):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i + 1} step 1 ERROR: {output}")
                step1_outputs[i] = f"Error: {output}"
            else:
                write(f"\nForecaster_{i + 1} step 1 output:\n{output[:300]}...")

        if self.artifact_store:
            self.artifact_store.save_step1_prompt(step1_prompt)
            for i, output in enumerate(step1_outputs):
                if not isinstance(output, Exception):
                    self.artifact_store.save_agent_step1(i + 1, output)

        # =========================================================================
        # STEP 4: Build context maps and run Step 2
        # =========================================================================
        write("\n=== Step 4: Running Step 2 ===")

        # Each agent gets current context + their own step 1 output
        context_map = {
            i: f"Current context: {current_context}\nPrior: {step1_outputs[i]}"
            for i in range(5)
            if not isinstance(step1_outputs[i], Exception)
        }

        step2_tasks = []
        for i, agent in enumerate(agents):
            model = agent["model"]
            system_prompt = CLAUDE_CONTEXT if "claude" in model.lower() else GPT_CONTEXT

            ctx = context_map.get(i, f"Current context: {current_context}")

            step2_prompt = NUMERIC_PROMPT_2.format(
                title=question_title,
                today=today,
                resolution_criteria=resolution_criteria,
                fine_print=fine_print,
                context=ctx,
                units=unit,
                lower_bound_message=lower_bound_msg,
                upper_bound_message=upper_bound_msg,
                hint=hint,
            )

            step2_tasks.append(self._call_model(model, step2_prompt, system_prompt=system_prompt))

        step2_outputs = await asyncio.gather(*step2_tasks, return_exceptions=True)

        # =========================================================================
        # STEP 5: Extract percentiles and generate CDFs
        # =========================================================================
        write("\n=== Step 5: Extracting percentiles and generating CDFs ===")

        all_cdfs = []
        agent_results = []

        for i, (agent, output) in enumerate(zip(agents, step2_outputs)):
            if isinstance(output, Exception):
                write(f"\nForecaster_{i + 1} step 2 ERROR: {output}")
                agent_results.append(AgentResult(
                    agent_id=f"forecaster_{i + 1}",
                    model=agent["model"],
                    weight=agent["weight"],
                    step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                    step2_output="",
                    error=str(output),
                ))
                continue

            write(f"\nForecaster_{i + 1} step 2 output:\n{output[:300]}...")

            try:
                percentiles = extract_percentiles_from_response(output, verbose=True)
                percentiles = enforce_strict_increasing(percentiles)

                cdf = generate_continuous_cdf(
                    percentiles,
                    open_upper_bound,
                    open_lower_bound,
                    upper_bound,
                    lower_bound,
                    zero_point,
                )

                write(f"Forecaster_{i + 1} CDF generated ({len(cdf)} points)")

                # Weight for o3 agents (indices 3, 4) is 2, others are 1
                weight = agent["weight"]
                all_cdfs.append((np.array(cdf), weight))

                agent_results.append(AgentResult(
                    agent_id=f"forecaster_{i + 1}",
                    model=agent["model"],
                    weight=weight,
                    step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                    step2_output=output,
                    percentiles=percentiles,
                    cdf=cdf,
                ))

            except Exception as e:
                write(f"Forecaster_{i + 1} CDF generation failed: {e}")
                agent_results.append(AgentResult(
                    agent_id=f"forecaster_{i + 1}",
                    model=agent["model"],
                    weight=agent["weight"],
                    step1_output=step1_outputs[i] if not isinstance(step1_outputs[i], Exception) else "",
                    step2_output=output,
                    error=str(e),
                ))

        # Save step 2 artifacts
        if self.artifact_store:
            for i, result in enumerate(agent_results):
                if result.step2_output:
                    self.artifact_store.save_agent_step2(i + 1, result.step2_output)
                self.artifact_store.save_agent_extracted(i + 1, {
                    "percentiles": result.percentiles,
                    "cdf_length": len(result.cdf) if result.cdf else 0,
                    "error": result.error,
                })

        # =========================================================================
        # STEP 6: Aggregate CDFs
        # =========================================================================
        write("\n=== Step 6: Aggregating CDFs ===")

        if len(all_cdfs) < 3:
            raise RuntimeError(f"Only {len(all_cdfs)} valid CDFs — need at least 3 to proceed")

        numer = sum(cdf * weight for cdf, weight in all_cdfs)
        denom = sum(weight for _, weight in all_cdfs)
        combined = (numer / denom).tolist()

        if len(combined) != 201:
            raise RuntimeError(f"Combined CDF malformed: {len(combined)} points")

        write(f"\nCombined CDF: {combined[:5]}...{combined[-5:]}")

        if self.artifact_store:
            self.artifact_store.save_aggregation({
                "num_valid_cdfs": len(all_cdfs),
                "method": "weighted_average",
                "final_cdf_length": len(combined),
                "final_cdf_sample": combined[:5] + combined[-5:],
            })

        return NumericForecastResult(
            final_cdf=combined,
            agent_results=agent_results,
            historical_context=historical_context,
            current_context=current_context,
        )

# Convenience function
async def get_numeric_forecast(
    question_details: dict,
    config: dict,
    llm_client: Optional[LLMClient] = None,
    artifact_store: Optional[ArtifactStore] = None,
    write: callable = print,
) -> Tuple[List[float], str]:
    """
    Convenience function to get a numeric forecast.

    Returns:
        Tuple of (201-point CDF, formatted comment)
    """
    forecaster = NumericForecaster(config, llm_client, artifact_store)

    result = await forecaster.forecast(
        question_title=question_details.get("title", ""),
        question_text=question_details.get("description", ""),
        resolution_criteria=question_details.get("resolution_criteria", ""),
        fine_print=question_details.get("fine_print", ""),
        open_upper_bound=question_details.get("open_upper_bound", True),
        open_lower_bound=question_details.get("open_lower_bound", True),
        upper_bound=question_details.get("scaling", {}).get("range_max", 100),
        lower_bound=question_details.get("scaling", {}).get("range_min", 0),
        zero_point=question_details.get("scaling", {}).get("zero_point"),
        unit=question_details.get("unit", "(unknown)"),
        write=write,
    )

    # Format comment
    comment_parts = [
        f"Combined CDF: `{result.final_cdf[:5]}...{result.final_cdf[-5:]}`\n",
    ]

    for agent_result in result.agent_results:
        comment_parts.append(
            f"=== {agent_result.agent_id} ({agent_result.model}) ===\n"
            f"Output:\n{agent_result.step2_output[:500]}...\n"
        )

    comment = "\n\n".join(comment_parts)

    return result.final_cdf, comment
