#!/usr/bin/env python3
"""
Test script for the research validator on 41901 artifacts.

This tests the validator's ability to:
1. Detect the Trump endorsement conflict
2. Attempt to resolve it through targeted searches
3. Generate an appropriate addendum
"""

import asyncio
import json
import yaml
from dotenv import load_dotenv

load_dotenv()

from src.bot.research_validator import ResearchValidator
from src.bot.search import QuestionDetails
from src.utils.llm import LLMClient


async def main():
    # Load config
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    # Override to enable validation and use Sonnet
    config["research"]["validation_enabled"] = True
    config["research"]["validation_model"] = "openrouter/anthropic/claude-sonnet-4.5"

    # Load the 41901 research artifacts
    with open("data/41901_20260131_211005/research/search_historical.json") as f:
        historical_context = json.load(f)["context"]

    with open("data/41901_20260131_211005/research/search_current.json") as f:
        current_context = json.load(f)["context"]

    # Load question details
    with open("data/41901_20260131_211005/question.json") as f:
        question_data = json.load(f)

    question_details = QuestionDetails(
        title=question_data.get("title", ""),
        resolution_criteria=question_data.get("resolution_criteria", ""),
        fine_print=question_data.get("fine_print", ""),
        description=question_data.get("description", ""),
    )

    print(f"Question: {question_details.title}")
    print(f"Historical context: {len(historical_context)} chars")
    print(f"Current context: {len(current_context)} chars")
    print()

    # Create validator
    llm_client = LLMClient()
    validator = ResearchValidator(config, llm_client)

    print("Running validator...")
    print("=" * 60)

    # Run validation
    validated_historical, validated_current, metadata = await validator.validate(
        historical_context,
        current_context,
        question_details,
    )

    print("=" * 60)
    print()
    print("RESULTS:")
    print(f"  Conflict found: {metadata.get('conflict_found', False)}")

    if metadata.get("conflict_found"):
        conflict = metadata.get("conflict", {})
        print(f"  Topic: {conflict.get('topic', 'N/A')}")
        print(f"  Claim A: {conflict.get('claim_a', 'N/A')[:100]}...")
        print(f"  Claim B: {conflict.get('claim_b', 'N/A')[:100]}...")
        print(f"  Search attempts: {metadata.get('search_attempts', 0)}")
        print(f"  Resolved: {metadata.get('resolved', False)}")

        if metadata.get("resolved"):
            resolution = metadata.get("resolution", {})
            print(f"  Resolution: {resolution.get('claim', 'N/A')[:100]}...")
            print(f"  Sources: {resolution.get('sources', 'N/A')}")

    # Check if addendum was added
    if len(validated_current) > len(current_context):
        addendum = validated_current[len(current_context):]
        print()
        print("ADDENDUM ADDED:")
        print(addendum)
    else:
        print()
        print("No addendum added (contexts unchanged)")

    # Save full metadata for inspection
    with open("validation_test_result.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print()
    print("Full metadata saved to validation_test_result.json")

    # Print cost summary
    from src.utils.llm import get_cost_tracker
    tracker = get_cost_tracker()
    print()
    print("COST SUMMARY:")
    print(f"  Total cost: ${tracker.total_cost:.4f}")
    print(f"  Input tokens: {tracker.total_input_tokens:,}")
    print(f"  Output tokens: {tracker.total_output_tokens:,}")


if __name__ == "__main__":
    asyncio.run(main())
