"""
Multiple Choice Question Handler

Handles forecasting for multiple choice questions.
Produces a probability distribution over discrete options that sums to 1.0.

Key concepts:
- Each option gets a probability between 0.01 and 0.99
- All probabilities must sum to 1.0
- Metaculus requires the format: {option_id: probability, ...}
"""

import re
import asyncio
import logging
from typing import Optional
from pathlib import Path

from ..utils.llm import LLMClient
from ..ensemble.aggregator import EnsembleAggregator, AgentPrediction

logger = logging.getLogger(__name__)


class MultipleChoiceForecaster:
    """
    Forecaster for multiple choice questions.

    Implements the two-stage process:
    1. Outside view: Establish baseline probabilities from reference classes
    2. Inside view: Adjust based on current evidence (via ensemble)

    Output: Probability distribution over options summing to 1.0
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
        options: list[dict],  # List of {id: str, label: str} dicts
    ) -> dict:
        """
        Generate a forecast for a multiple choice question.

        Args:
            options: List of option dicts with 'id' and 'label' keys

        Returns dict with:
        - final_distribution: dict[str, float] mapping option_id to probability
        - base_distribution: dict[str, float]
        - agent_predictions: list[AgentPrediction]
        - aggregation: dict
        - outside_view_reasoning: str
        - inside_view_reasoning: dict[agent_name, str]
        """
        # Format options for prompts
        options_str = self._format_options(options)
        option_ids = [opt.get("id", opt.get("label", f"option_{i}")) for i, opt in enumerate(options)]
        option_labels = [opt.get("label", f"Option {i+1}") for i, opt in enumerate(options)]

        # Stage 1: Outside View
        logger.info("Stage 1: Establishing baseline distribution (outside view)")
        base_result = await self._estimate_base_distribution(
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            options_str=options_str,
            option_labels=option_labels,
        )

        base_distribution = base_result["distribution"]
        outside_view_reasoning = base_result["reasoning"]

        if base_distribution:
            best = max(base_distribution.items(), key=lambda x: x[1])
            logger.info(f"Base distribution: most likely = {best[0]} ({best[1]:.1%})")
        else:
            logger.warning("Could not extract base distribution")

        # Stage 2: Inside View (Ensemble)
        logger.info("Stage 2: Adjusting with evidence (inside view)")
        agent_predictions = await self._run_ensemble(
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            research_summary=research_summary,
            options_str=options_str,
            option_labels=option_labels,
            base_distribution=base_distribution,
        )

        # Stage 3: Aggregate distributions
        logger.info("Stage 3: Aggregating predictions")
        final_distribution = self._aggregate_distributions(agent_predictions, option_labels)

        # Map to option IDs for Metaculus submission
        final_distribution_by_id = {}
        for i, opt_id in enumerate(option_ids):
            label = option_labels[i]
            final_distribution_by_id[opt_id] = final_distribution.get(label, 1.0 / len(options))

        # Normalize
        final_distribution_by_id = self._normalize_distribution(final_distribution_by_id)

        best = max(final_distribution_by_id.items(), key=lambda x: x[1])
        logger.info(f"Final prediction: most likely = {best[0]} ({best[1]:.1%})")

        # Compile inside view reasoning
        inside_view_reasoning = {
            ap.agent_name: ap.reasoning for ap in agent_predictions
        }

        return {
            "final_distribution": final_distribution_by_id,
            "final_distribution_by_label": final_distribution,
            "base_distribution": base_distribution,
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
        options_str: str,
        option_labels: list[str],
    ) -> dict:
        """Estimate the base distribution using outside view reasoning."""
        template_path = self.prompts_dir / "outside_view_multiple_choice.md"
        with open(template_path) as f:
            template = f.read()

        prompt = template.format(
            question_title=question_title,
            question_text=question_text[:3000],
            resolution_criteria=resolution_criteria[:1000],
            options=options_str,
            num_options=len(option_labels),
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
        distribution = self._extract_distribution(reasoning, option_labels)

        return {
            "distribution": distribution,
            "reasoning": reasoning,
            "prompt": prompt,
        }

    async def _run_ensemble(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
        options_str: str,
        option_labels: list[str],
        base_distribution: dict[str, float],
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

        template_path = self.prompts_dir / "inside_view_multiple_choice.md"
        with open(template_path) as f:
            template = f.read()

        base_dist_str = self._format_distribution(base_distribution)

        tasks = []
        for agent in agents_config:
            task = self._run_single_agent(
                agent=agent,
                template=template,
                question_title=question_title,
                question_text=question_text,
                resolution_criteria=resolution_criteria,
                research_summary=research_summary,
                options_str=options_str,
                option_labels=option_labels,
                base_distribution=base_dist_str,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        predictions = []
        for result, agent in zip(results, agents_config):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent['name']} failed: {result}")
                continue
            predictions.append(result)

        return predictions

    async def _run_single_agent(
        self,
        agent: dict,
        template: str,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
        options_str: str,
        option_labels: list[str],
        base_distribution: str,
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
            options=options_str,
            num_options=len(option_labels),
            base_distribution=base_distribution,
            research_summary=research_summary[:5000],
        )

        response = await self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
        )

        reasoning = response.content
        distribution = self._extract_distribution(reasoning, option_labels)

        # Find most likely option for scalar prediction
        if distribution:
            best = max(distribution.items(), key=lambda x: x[1])
            prediction = best[1]
        else:
            prediction = 1.0 / len(option_labels)

        return AgentPrediction(
            agent_name=agent_name,
            model=model,
            weight=weight,
            prediction=prediction,
            reasoning=reasoning,
            prediction_distribution=distribution,
        )

    def _extract_distribution(
        self,
        text: str,
        option_labels: list[str],
    ) -> dict[str, float]:
        """
        Extract probability distribution from LLM response.

        Looks for patterns like:
        - JSON block with "distribution" key (most reliable)
        - "Option A: 30%"
        - "Probabilities: [0.3, 0.5, 0.2]"
        - "A: 30%, B: 50%, C: 20%"

        IMPORTANT: We prioritize finding distributions in the FINAL section of the
        response, as LLM outputs often mention base rates earlier that we don't want.
        """
        import json
        distribution = {}

        # Pattern 0: JSON block (most reliable - new foolproof format)
        json_match = re.search(
            r"```json\s*(\{[^`]+\})\s*```",
            text,
            re.DOTALL
        )
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                if "distribution" in json_data:
                    dist = json_data["distribution"]
                    # Map JSON keys to option labels (fuzzy match if needed)
                    for label in option_labels:
                        if label in dist:
                            distribution[label] = float(dist[label])
                        else:
                            # Try case-insensitive match
                            for key, val in dist.items():
                                if key.lower() == label.lower():
                                    distribution[label] = float(val)
                                    break
                    if len(distribution) == len(option_labels):
                        return self._normalize_distribution(distribution)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.debug(f"JSON parsing failed: {e}")

        # Pattern 1: "Probabilities: [0.3, 0.5, 0.2]"
        prob_list_match = re.search(
            r"Probabilities:\s*\[([0-9.,\s]+)\]",
            text,
            re.IGNORECASE
        )
        if prob_list_match:
            try:
                probs = [float(p.strip()) for p in prob_list_match.group(1).split(",")]
                if len(probs) == len(option_labels):
                    for label, prob in zip(option_labels, probs):
                        distribution[label] = prob
                    return self._normalize_distribution(distribution)
            except ValueError:
                pass

        # Pattern 2: Look for "Distribution:" section FIRST (most reliable)
        # This finds the LAST "Distribution:" section to get final values
        dist_sections = re.findall(
            r"\*{0,2}Distribution:?\*{0,2}\s*\n((?:[^\n]*[:=]\s*[0-9.]+%?\s*\n?)+)",
            text,
            re.IGNORECASE
        )
        if dist_sections:
            # Use the LAST distribution section (final answer)
            section_text = dist_sections[-1]
            for label in option_labels:
                escaped_label = re.escape(label)
                # Use word boundary for short labels (like "0", "1") to avoid false matches
                # Also capture the % sign to know if value is percentage
                if len(label) <= 2:
                    pattern = rf"(?:^|\s|-)({escaped_label})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(%?)"
                else:
                    pattern = rf"({escaped_label})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(%?)"

                match = re.search(pattern, section_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Value is always in group 2, % sign in group 3
                    val = float(match.group(2))
                    has_percent = match.group(3) == '%'
                    # If has % or value > 1, treat as percentage
                    if has_percent or val > 1:
                        val = val / 100
                    distribution[label] = val

            if len(distribution) == len(option_labels):
                return self._normalize_distribution(distribution)

        # Pattern 3: Fallback - find LAST occurrence of each label with percentage
        # This handles cases where there's no explicit "Distribution:" header
        if not distribution:
            for label in option_labels:
                escaped_label = re.escape(label)

                # For short labels, require start of line or whitespace before
                # Capture value and % sign
                if len(label) <= 2:
                    pattern = rf"(?:^|\n|\s|-)({escaped_label})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(%?)"
                else:
                    pattern = rf"({escaped_label})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(%?)"

                # Find ALL matches and take the LAST one
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Value is second element, % sign is third
                    val = float(matches[-1][1])
                    has_percent = matches[-1][2] == '%'
                    if has_percent or val > 1:
                        val = val / 100
                    distribution[label] = val

        # Pattern 4: Try decimal format (0.X) as last resort
        if not distribution:
            for label in option_labels:
                escaped_label = re.escape(label)
                matches = re.findall(
                    rf"{escaped_label}\s*[:=]\s*([0-9]*\.[0-9]+)",
                    text,
                    re.IGNORECASE
                )
                if matches:
                    val = float(matches[-1])
                    # If value > 1, assume it's a percentage
                    if val > 1:
                        val = val / 100
                    distribution[label] = val

        if not distribution:
            logger.warning("Could not extract distribution from response")
            # Return uniform distribution
            return {label: 1.0 / len(option_labels) for label in option_labels}

        return self._normalize_distribution(distribution)

    def _aggregate_distributions(
        self,
        predictions: list[AgentPrediction],
        option_labels: list[str],
    ) -> dict[str, float]:
        """Aggregate distributions from multiple agents using weighted average."""
        if not predictions:
            return {label: 1.0 / len(option_labels) for label in option_labels}

        total_weight = sum(p.weight for p in predictions if p.prediction_distribution)

        aggregated = {label: 0.0 for label in option_labels}

        for p in predictions:
            if p.prediction_distribution:
                for label in option_labels:
                    prob = p.prediction_distribution.get(label, 1.0 / len(option_labels))
                    aggregated[label] += prob * p.weight

        if total_weight > 0:
            aggregated = {k: v / total_weight for k, v in aggregated.items()}

        return self._normalize_distribution(aggregated)

    def _normalize_distribution(
        self,
        distribution: dict[str, float],
    ) -> dict[str, float]:
        """Normalize distribution to sum to 1.0 and respect bounds."""
        if not distribution:
            return distribution

        # Clamp values to [0.01, 0.99]
        clamped = {k: max(0.01, min(0.99, v)) for k, v in distribution.items()}

        # Normalize to sum to 1.0
        total = sum(clamped.values())
        if total > 0:
            normalized = {k: v / total for k, v in clamped.items()}
        else:
            # Uniform if all zeros
            normalized = {k: 1.0 / len(clamped) for k in clamped}

        # Fix floating point errors - adjust last item
        keys = list(normalized.keys())
        current_sum = sum(normalized.values())
        if abs(current_sum - 1.0) > 1e-9:
            normalized[keys[-1]] += 1.0 - current_sum

        return normalized

    def _format_options(self, options: list[dict]) -> str:
        """Format options for display in prompts."""
        lines = []
        for i, opt in enumerate(options):
            label = opt.get("label", f"Option {i+1}")
            lines.append(f"- {label}")
        return "\n".join(lines)

    def _format_distribution(self, distribution: dict[str, float]) -> str:
        """Format distribution for display in prompts."""
        if not distribution:
            return "No base distribution available"
        lines = []
        for label, prob in sorted(distribution.items(), key=lambda x: -x[1]):
            lines.append(f"- {label}: {prob:.1%}")
        return "\n".join(lines)
