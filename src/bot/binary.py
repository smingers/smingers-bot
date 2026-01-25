"""
Binary Question Handler

Handles the full forecasting pipeline for binary (yes/no) questions.
"""

import re
import asyncio
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

from ..utils.llm import LLMClient
from ..ensemble.aggregator import EnsembleAggregator, AgentPrediction
from .multiple_choice import ExtractionError

logger = logging.getLogger(__name__)


class BinaryForecaster:
    """
    Forecaster for binary questions.

    Implements the two-stage process:
    1. Outside view: Establish base rate from reference classes
    2. Inside view: Adjust based on current evidence (via ensemble)
    """

    def __init__(self, config: dict):
        self.config = config
        self.llm = LLMClient()
        self.aggregator = EnsembleAggregator(
            method=config.get("ensemble", {}).get("aggregation", "weighted_average")
        )

        # Load prompt templates
        self.prompts_dir = Path(__file__).parent / "prompts"

    async def forecast(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
    ) -> dict:
        """
        Generate a forecast for a binary question.

        Returns dict with:
        - final_prediction: float (0.001-0.999)
        - base_rate: float
        - agent_predictions: list of AgentPrediction
        - aggregation: dict
        - outside_view_reasoning: str
        - inside_view_reasoning: dict[agent_name, str]
        """
        # Stage 1: Outside View
        logger.info("Stage 1: Establishing base rate (outside view)")
        base_rate_result = await self._estimate_base_rate(
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
        )

        base_rate = base_rate_result["base_rate"]
        reference_classes = base_rate_result["reference_classes"]
        base_rate_confidence = base_rate_result["confidence"]
        outside_view_reasoning = base_rate_result["reasoning"]

        logger.info(f"Base rate established: {base_rate:.1%}")

        # Stage 2: Inside View (Ensemble)
        logger.info("Stage 2: Adjusting with evidence (inside view)")
        agent_predictions = await self._run_ensemble(
            question_title=question_title,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            research_summary=research_summary,
            base_rate=base_rate,
            reference_classes=reference_classes,
            base_rate_confidence=base_rate_confidence,
        )

        # Stage 3: Aggregate
        logger.info("Stage 3: Aggregating predictions")
        aggregation_result = self.aggregator.aggregate_binary(agent_predictions)

        final_prediction = aggregation_result.final_prediction
        logger.info(f"Final prediction: {final_prediction:.1%}")

        # Compile inside view reasoning
        inside_view_reasoning = {
            ap.agent_name: ap.reasoning for ap in agent_predictions
        }

        return {
            "final_prediction": final_prediction,
            "base_rate": base_rate,
            "reference_classes": reference_classes,
            "base_rate_confidence": base_rate_confidence,
            "agent_predictions": agent_predictions,
            "aggregation": {
                "method": aggregation_result.method,
                "mean": aggregation_result.mean,
                "median": aggregation_result.median,
                "std_dev": aggregation_result.std_dev,
                "min": aggregation_result.min_prediction,
                "max": aggregation_result.max_prediction,
            },
            "outside_view_reasoning": outside_view_reasoning,
            "inside_view_reasoning": inside_view_reasoning,
        }

    async def _estimate_base_rate(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
    ) -> dict:
        """Estimate the base rate using outside view reasoning."""
        # Load prompt template
        template_path = self.prompts_dir / "outside_view.md"
        with open(template_path) as f:
            template = f.read()

        # Fill in the template
        prompt = template.format(
            question_title=question_title,
            question_text=question_text[:3000],  # Truncate if too long
            resolution_criteria=resolution_criteria[:1000],
        )

        # Get model from config (mode-aware)
        active_models = self.config.get("_active_models", {})
        model = active_models.get(
            "base_rate_estimator",
            self.config.get("models", {}).get("base_rate_estimator", "claude-sonnet-4-5-20250929")
        )

        # Call LLM
        response = await self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more consistent base rates
            max_tokens=4000,
        )

        reasoning = response.content

        # Extract base rate from response
        base_rate = self._extract_probability(
            reasoning,
            context="Base rate estimation (outside view)",
            agent_name="base_rate_estimator"
        )
        reference_classes = self._extract_reference_classes(reasoning)
        confidence = self._extract_confidence(reasoning)

        return {
            "base_rate": base_rate,
            "reference_classes": reference_classes,
            "confidence": confidence,
            "reasoning": reasoning,
            "prompt": prompt,
        }

    async def _run_ensemble(
        self,
        question_title: str,
        question_text: str,
        resolution_criteria: str,
        research_summary: str,
        base_rate: float,
        reference_classes: list[str],
        base_rate_confidence: int,
    ) -> list[AgentPrediction]:
        """Run all ensemble agents in parallel."""
        # Get agents from mode-aware config
        agents_config = self.config.get("_active_agents", [])

        if not agents_config:
            # Fallback to old config format
            agents_config = self.config.get("ensemble", {}).get("agents", [])

        if not agents_config:
            # Default single agent if no ensemble configured
            agents_config = [{
                "name": "default",
                "model": "claude-sonnet-4-5-20250929",
                "weight": 1.0,
                "role_description": "You are a balanced forecaster.",
            }]

        # Create tasks for each agent
        tasks = []
        for agent in agents_config:
            # Load appropriate template based on agent name
            agent_name = agent.get("name", "unnamed")
            if agent_name == "panshul42":
                template_path = self.prompts_dir / "inside_view_panshul42.md"
            else:
                template_path = self.prompts_dir / "inside_view.md"
            
            with open(template_path) as f:
                template = f.read()
            
            task = self._run_single_agent(
                agent=agent,
                template=template,
                question_title=question_title,
                question_text=question_text,
                resolution_criteria=resolution_criteria,
                research_summary=research_summary,
                base_rate=base_rate,
                reference_classes=reference_classes,
                base_rate_confidence=base_rate_confidence,
            )
            tasks.append(task)

        # Run all agents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful predictions
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
                f"Probability extraction failed for {len(extraction_errors)} agent(s): {failed_agents}. "
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
        base_rate: float,
        reference_classes: list[str],
        base_rate_confidence: int,
    ) -> AgentPrediction:
        """Run a single ensemble agent."""
        agent_name = agent.get("name", "unnamed")
        model = agent.get("model", "claude-sonnet-4-5-20250929")
        weight = agent.get("weight", 1.0)
        role_description = agent.get("role_description", "You are a forecaster.")

        # Check if this is the Panshul42 prompt format
        is_panshul42 = "{today}" in template and "{context}" in template and "{fine_print}" in template
        
        if is_panshul42:
            # Panshul42 prompt format
            # Construct context: "Outside view analysis + current information/news articles"
            outside_view_text = f"Base rate: {base_rate * 100:.1f}%\n"
            if reference_classes:
                outside_view_text += f"Reference classes: {', '.join(reference_classes)}\n"
            outside_view_text += f"Confidence: {base_rate_confidence}/10"
            
            context = f"{outside_view_text}\n\nCurrent information/news articles:\n{research_summary[:5000]}"
            
            # Fill in the Panshul42 template
            prompt = template.format(
                title=question_title,
                resolution_criteria=resolution_criteria[:1000],
                fine_print="",  # fine_print not available in current function signature
                today=datetime.now().strftime("%Y-%m-%d"),
                context=context,
            )
        else:
            # Standard prompt format
            prompt = template.format(
                agent_role=agent_name,
                role_description=role_description,
                question_title=question_title,
                question_text=question_text[:3000],
                resolution_criteria=resolution_criteria[:1000],
                base_rate=f"{base_rate * 100:.1f}",
                reference_classes=", ".join(reference_classes) if reference_classes else "N/A",
                base_rate_confidence=base_rate_confidence,
                research_summary=research_summary[:5000],  # Truncate if too long
            )

        # Call LLM
        response = await self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Higher temperature for diversity in ensemble
            max_tokens=4000,
        )

        reasoning = response.content

        # Extract prediction
        prediction = self._extract_probability(
            reasoning,
            context=f"Agent '{agent_name}' ({model})",
            agent_name=agent_name
        )

        # Extract evidence weights if possible
        evidence_weights = self._extract_evidence_weights(reasoning)

        return AgentPrediction(
            agent_name=agent_name,
            model=model,
            weight=weight,
            prediction=prediction,
            reasoning=reasoning,
            evidence_weights=evidence_weights,
        )

    def _extract_probability(self, text: str, context: str = "unknown", agent_name: str = None) -> float:
        """
        Extract probability from LLM response.

        Args:
            text: The LLM response text
            context: Description of where this came from (for error messages)
            agent_name: Name of the agent (for error messages)

        Raises:
            ExtractionError: If no probability can be extracted
        """
        # Look for "Probability: X%" pattern (with optional markdown formatting)
        match = re.search(r"\*{0,2}Probability:?\*{0,2}\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, re.IGNORECASE)
        if match:
            prob = float(match.group(1)) / 100
            return max(0.001, min(0.999, prob))

        # Look for "Base Rate Estimate: X%" pattern (with optional markdown formatting)
        match = re.search(r"\*{0,2}Base Rate Estimate:?\*{0,2}\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, re.IGNORECASE)
        if match:
            prob = float(match.group(1)) / 100
            return max(0.001, min(0.999, prob))

        # Look for "Final Estimate: X%" or "Final Probability: X%" pattern
        match = re.search(r"\*{0,2}Final (?:Estimate|Probability):?\*{0,2}\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, re.IGNORECASE)
        if match:
            prob = float(match.group(1)) / 100
            return max(0.001, min(0.999, prob))

        # Look for any percentage near the end
        matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*%", text[-500:])
        if matches:
            prob = float(matches[-1]) / 100
            return max(0.001, min(0.999, prob))

        # All extraction methods failed - raise error
        response_preview = text[:500] + "..." if len(text) > 500 else text
        raise ExtractionError(
            f"{context}: Could not extract probability from response. "
            f"Looked for 'Probability: X%', 'Base Rate Estimate: X%', 'Final Estimate: X%', "
            f"and any percentage in last 500 chars.",
            agent_name=agent_name,
            response_preview=response_preview
        )

    def _extract_reference_classes(self, text: str) -> list[str]:
        """Extract reference classes from outside view reasoning."""
        classes = []

        # Look for numbered reference classes
        matches = re.findall(r"Reference Class \d+[:\s]+([^\n]+)", text, re.IGNORECASE)
        classes.extend(matches)

        # Look for bullet points under "Reference Classes Used"
        section_match = re.search(
            r"Reference Classes Used:?\s*\n((?:[-•\d.]+[^\n]+\n?)+)",
            text,
            re.IGNORECASE
        )
        if section_match:
            lines = section_match.group(1).strip().split("\n")
            for line in lines:
                # Clean up the line
                line = re.sub(r"^[-•\d.]+\s*", "", line).strip()
                if line and line not in classes:
                    classes.append(line)

        return classes[:5]  # Limit to 5

    def _extract_confidence(self, text: str) -> int:
        """Extract confidence level from response."""
        # Look for "Confidence Level: X"
        match = re.search(r"Confidence Level:\s*(\d+)", text, re.IGNORECASE)
        if match:
            return min(10, max(1, int(match.group(1))))

        # Look for "Confidence: X/10"
        match = re.search(r"Confidence[^:]*:\s*(\d+)\s*/\s*10", text, re.IGNORECASE)
        if match:
            return min(10, max(1, int(match.group(1))))

        return 5  # Default moderate confidence

    def _extract_evidence_weights(self, text: str) -> Optional[dict]:
        """Extract evidence weights from inside view reasoning."""
        weights = {"strong": [], "moderate": [], "weak": []}

        # Look for STRONG Evidence section
        strong_match = re.search(
            r"STRONG Evidence[^\n]*\n((?:[-•\*][^\n]+\n?)+)",
            text,
            re.IGNORECASE
        )
        if strong_match:
            items = re.findall(r"[-•\*]\s*([^\n]+)", strong_match.group(1))
            weights["strong"] = [i.strip()[:100] for i in items[:5]]

        # Look for MODERATE Evidence section
        moderate_match = re.search(
            r"MODERATE Evidence[^\n]*\n((?:[-•\*][^\n]+\n?)+)",
            text,
            re.IGNORECASE
        )
        if moderate_match:
            items = re.findall(r"[-•\*]\s*([^\n]+)", moderate_match.group(1))
            weights["moderate"] = [i.strip()[:100] for i in items[:5]]

        # Look for WEAK Evidence section
        weak_match = re.search(
            r"WEAK Evidence[^\n]*\n((?:[-•\*][^\n]+\n?)+)",
            text,
            re.IGNORECASE
        )
        if weak_match:
            items = re.findall(r"[-•\*]\s*([^\n]+)", weak_match.group(1))
            weights["weak"] = [i.strip()[:100] for i in items[:5]]

        if any(weights.values()):
            return weights
        return None
