"""
Research Validation Agent

Detects mutually exclusive factual claims in research and attempts to resolve
them through targeted verification searches.

This module implements a single-agent verification loop that:
1. Reads both historical and current research outputs
2. Identifies any mutually exclusive factual claims
3. Attempts to resolve conflicts through targeted Google News searches (up to 3 attempts)
4. Appends an authoritative addendum if resolved, otherwise passes research through unchanged
"""

import logging
import re
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass

from ..utils.llm import LLMClient
from .search import SearchPipeline, QuestionDetails

logger = logging.getLogger(__name__)


@dataclass
class ConflictResolution:
    """Result of attempting to resolve a factual conflict."""
    topic: str
    claim_a: str
    claim_b: str
    resolved: bool
    resolved_claim: Optional[str]  # The claim determined to be correct
    sources: List[str]  # Sources supporting the resolution
    search_attempts: int


# System prompt for the validation agent
VALIDATION_SYSTEM_PROMPT = """You are a research fact-checker. Your job is to identify and resolve factual conflicts in research documents.

You will be given research outputs and asked to:
1. Identify any mutually exclusive factual claims (e.g., "X happened" vs "X did not happen")
2. Design targeted searches to verify which claim is correct
3. Evaluate search results and determine if they definitively resolve the conflict

IMPORTANT:
- Only flag FACTUAL conflicts, not interpretive differences or opinions
- Only resolve conflicts when evidence is clear and definitive
- If you cannot resolve with confidence, say so - do not guess
- Your resolutions will be treated as authoritative, so only resolve when certain"""


# Detection prompt template
DETECTION_PROMPT = """Review the following research for a forecasting question and identify any mutually exclusive factual claims.

QUESTION: {title}

RESOLUTION CRITERIA: {resolution_criteria}

HISTORICAL RESEARCH:
{historical}

CURRENT RESEARCH:
{current}

---

Your goal is to identify factual conflicts that could cause a forecaster to make an incorrect prediction.

Look for cases where one source states something happened and another states it did NOT happen. The claims must be LOGICALLY INCOMPATIBLE - they cannot both be true simultaneously.

DO NOT flag as conflicts:
- Differences in wording, phrasing, or level of detail about the same fact
- One source providing more context than another
- Differences in emphasis or framing
- Opinions, predictions, or interpretations

ONLY flag conflicts where accepting both claims would be a logical contradiction (e.g., "X endorsed the bill" vs "X has not endorsed the bill").

If you find MULTIPLE conflicts, choose the one with the most significant potential impact on forecasting accuracy - the conflict where believing the wrong claim would most likely lead to an incorrect prediction.

If you find a genuine conflict, respond in this format:
CONFLICT_FOUND
Topic: [brief description]
Claim A: [the claim from source A]
Source A: [which source]
Claim B: [the contradicting claim from source B]
Source B: [which source]
Search query: [a targeted search query to determine which claim is correct]

If no conflicts are found, respond:
NO_CONFLICTS"""


# Verification prompt template
VERIFICATION_PROMPT = """Here are the search results (attempt {attempt} of {max_attempts}):

{search_results}

---

Based on these results, can you definitively resolve the factual conflict?

If YES - the evidence clearly supports one claim over the other:
RESOLVED
Correct claim: [the claim that is correct]
Sources: [list the sources that confirm this]
Confidence: [brief explanation of why you're confident]

If NO - you need more/different information:
SEARCH
Query: [a new search query to try]
Reason: [why this search might help]

If NO - you've tried enough and cannot resolve this:
UNRESOLVED
Reason: [why the conflict cannot be resolved with available information]"""


# Addendum template for resolved conflicts
RESOLVED_ADDENDUM_TEMPLATE = """--- Research Validation Addendum ---

The research above may contain conflicting or erroneous information regarding: {topic}

Additional verification was conducted to resolve this discrepancy.

VERIFIED: {resolved_claim}

Sources: {sources}

This supersedes any statements to the contrary in the research above.
"""

# Addendum template for unresolved conflicts
UNRESOLVED_ADDENDUM_TEMPLATE = """--- Research Validation Notice ---

Conflicting information was identified regarding: {topic}

Verification was attempted but could not definitively resolve the discrepancy.

Any claims in the research about this topic should be treated with uncertainty.
"""


class ResearchValidator:
    """
    Single-agent verification loop that:
    1. Detects mutually exclusive factual claims in research
    2. Attempts to resolve them through targeted searches (up to 3 attempts)
    3. Appends authoritative addendum if resolved, otherwise passes through unchanged
    """

    MAX_SEARCH_ATTEMPTS = 3

    def __init__(self, config: dict, llm_client: LLMClient):
        self.config = config
        self.llm = llm_client
        self.model = config.get("research", {}).get(
            "validation_model",
            "openrouter/anthropic/claude-sonnet-4.5"
        )

    async def validate(
        self,
        historical_context: str,
        current_context: str,
        question_details: QuestionDetails,
    ) -> Tuple[str, str, Dict]:
        """
        Run the validation agent loop.

        Args:
            historical_context: The historical research context string
            current_context: The current research context string
            question_details: Question metadata for search context

        Returns:
            Tuple of (historical_context, current_context, metadata)
            - If no conflicts or unresolved: contexts unchanged
            - If resolved: current_context has addendum appended
        """
        messages = []
        metadata = {
            "ran": True,
            "conflict_found": False,
            "resolved": False,
            "search_attempts": 0,
            "searches": [],
        }

        # Turn 1: Detection
        logger.info("Research validation: Starting conflict detection")
        detection_prompt = self._build_detection_prompt(
            historical_context, current_context, question_details
        )
        messages.append({"role": "user", "content": detection_prompt})

        response = await self._call_agent(messages)
        messages.append({"role": "assistant", "content": response})

        # Store raw detection response for debugging
        metadata["detection_response"] = response

        # Parse detection response
        detection_result = self._parse_detection_response(response)

        if not detection_result["has_conflict"]:
            logger.info("Research validation: No conflicts detected")
            return historical_context, current_context, metadata

        metadata["conflict_found"] = True
        metadata["conflict"] = detection_result["conflict"]
        logger.info(f"Research validation: Conflict detected - {detection_result['conflict']['topic']}")

        # Turns 2-4: Verification loop
        search_query = detection_result["search_query"]

        for attempt in range(self.MAX_SEARCH_ATTEMPTS):
            metadata["search_attempts"] = attempt + 1
            logger.info(f"Research validation: Search attempt {attempt + 1} - {search_query[:80]}...")

            # Run search
            search_results = await self._run_search(search_query, question_details)
            metadata["searches"].append({
                "query": search_query,
                "results_length": len(search_results),
            })

            # Send results to agent
            verification_prompt = self._build_verification_prompt(search_results, attempt + 1)
            messages.append({"role": "user", "content": verification_prompt})

            response = await self._call_agent(messages)
            messages.append({"role": "assistant", "content": response})

            # Parse verification response
            verification_result = self._parse_verification_response(response)

            if verification_result["status"] == "RESOLVED":
                metadata["resolved"] = True
                metadata["resolution"] = verification_result["resolution"]
                logger.info(f"Research validation: Resolved - {verification_result['resolution']['claim'][:100]}...")

                # Build and append addendum to BOTH contexts
                # (so agents see correction in both Step 1/outside view and Step 2/inside view)
                addendum = self._build_resolved_addendum(
                    detection_result["conflict"],
                    verification_result["resolution"],
                )
                validated_historical = historical_context + "\n\n" + addendum
                validated_current = current_context + "\n\n" + addendum

                return validated_historical, validated_current, metadata

            elif verification_result["status"] == "SEARCH":
                search_query = verification_result["query"]
                logger.info(f"Research validation: Need more info, trying new query...")

            else:  # UNRESOLVED or max attempts
                logger.info("Research validation: Unable to resolve, adding uncertainty notice")
                metadata["unresolved_reason"] = verification_result.get("reason", "Max attempts reached")
                break

        # If we detected a conflict but couldn't resolve it, add uncertainty notice
        if metadata.get("conflict_found") and not metadata.get("resolved"):
            addendum = self._build_unresolved_addendum(detection_result["conflict"])
            validated_historical = historical_context + "\n\n" + addendum
            validated_current = current_context + "\n\n" + addendum
            return validated_historical, validated_current, metadata

        return historical_context, current_context, metadata

    async def _call_agent(self, messages: List[Dict]) -> str:
        """Call the validation agent with conversation history."""
        response = await self.llm.complete(
            model=self.model,
            messages=messages,
            system=VALIDATION_SYSTEM_PROMPT,
            max_tokens=2000,
        )
        return response.content

    async def _run_search(self, query: str, question_details: QuestionDetails) -> str:
        """Run a Google News search and return formatted results."""
        async with SearchPipeline(self.config, self.llm) as search:
            results = await search._google_search_and_scrape(
                query=query,
                is_news=True,
                question_details=question_details,
            )
        return results

    def _build_detection_prompt(
        self,
        historical: str,
        current: str,
        question: QuestionDetails,
    ) -> str:
        """Build the detection prompt with research content."""
        return DETECTION_PROMPT.format(
            title=question.title,
            resolution_criteria=question.resolution_criteria,
            historical=historical,
            current=current,
        )

    def _build_verification_prompt(self, search_results: str, attempt: int) -> str:
        """Build the verification prompt with search results."""
        return VERIFICATION_PROMPT.format(
            attempt=attempt,
            max_attempts=self.MAX_SEARCH_ATTEMPTS,
            search_results=search_results,
        )

    def _parse_detection_response(self, response: str) -> Dict:
        """Parse the detection response into structured data."""
        if "NO_CONFLICTS" in response:
            return {"has_conflict": False}

        # Parse CONFLICT_FOUND response
        return {
            "has_conflict": True,
            "conflict": {
                "topic": self._extract_field(response, "Topic:"),
                "claim_a": self._extract_field(response, "Claim A:"),
                "source_a": self._extract_field(response, "Source A:"),
                "claim_b": self._extract_field(response, "Claim B:"),
                "source_b": self._extract_field(response, "Source B:"),
            },
            "search_query": self._extract_field(response, "Search query:"),
        }

    def _parse_verification_response(self, response: str) -> Dict:
        """Parse the verification response into structured data."""
        # Check for RESOLVED (but not UNRESOLVED)
        if re.search(r'\bRESOLVED\b', response) and not re.search(r'\bUNRESOLVED\b', response):
            return {
                "status": "RESOLVED",
                "resolution": {
                    "claim": self._extract_field(response, "Correct claim:"),
                    "sources": self._extract_field(response, "Sources:"),
                    "confidence": self._extract_field(response, "Confidence:"),
                },
            }
        elif re.search(r'\bSEARCH\b', response):
            return {
                "status": "SEARCH",
                "query": self._extract_field(response, "Query:"),
                "reason": self._extract_field(response, "Reason:"),
            }
        else:
            return {
                "status": "UNRESOLVED",
                "reason": self._extract_field(response, "Reason:"),
            }

    def _extract_field(self, text: str, field: str) -> str:
        """Extract a field value from the response text.

        Handles both single-line and multi-line field values.
        """
        # Try single-line extraction first
        pattern = rf"{re.escape(field)}\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

        # If not found, return empty string
        return ""

    def _build_resolved_addendum(self, conflict: Dict, resolution: Dict) -> str:
        """Build the authoritative addendum for resolved conflicts."""
        return RESOLVED_ADDENDUM_TEMPLATE.format(
            topic=conflict["topic"],
            resolved_claim=resolution["claim"],
            sources=resolution["sources"],
        )

    def _build_unresolved_addendum(self, conflict: Dict) -> str:
        """Build the notice addendum for unresolved conflicts."""
        return UNRESOLVED_ADDENDUM_TEMPLATE.format(
            topic=conflict["topic"],
        )
