import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load env before importing other modules
load_dotenv()

# Add src to pythonpath so we can import bot modules
sys.path.append(str(Path(__file__).parent.parent))

from src.bot.content_extractor import ConcurrentContentExtractor  # noqa: E402
from src.bot.search import QuestionDetails, _bm25_filter_content  # noqa: E402
from src.utils.llm import CostTracker, LLMClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# New modified prompt with the kill switch
TEST_ARTICLE_SUMMARY_PROMPT = """
You are an assistant to a superforecaster and your task involves high-quality information retrieval to help the forecaster make the most informed forecasts. Forecasting involves parsing through an immense trove of internet articles and web content. To make this easier for the forecaster, you read entire articles and extract the key pieces of the articles relevant to the question. The key pieces generally include:

1. Facts, statistics and other objective measurements described in the article
2. Opinions from reliable and named sources (e.g. if the article writes 'according to a 2023 poll by Gallup' or 'The 2025 presidential approval rating poll by Reuters' etc.)
3. Potentially useful opinions from less reliable/not-named sources (you explicitly document the less reliable origins of these opinions though)

Today, you're focusing on the question:

{title}

Resolution criteria:
{resolution_criteria}

Fine print:
{fine_print}

Background information:
{background}

Article to summarize:
{article}

If the article is completely and totally useless for forecasting this question, reply with exactly the word "IRRELEVANT" and nothing else.

Note: If the web content extraction is incomplete or you believe the quality of the extracted content isn't the best, feel free to add a disclaimer before your summary.

Please summarize only the article given, not injecting your own knowledge or providing a forecast. Aim to achieve a balance between a superficial summary and an overly verbose account.
"""


def extract_urls_from_text(text: str) -> list[str]:
    # Find all source="..." or url="..." in Summary and QuestionSource tags, handling possible JSON escaping
    urls = []
    # match <Summary source="...">
    matches = re.finditer(r'<Summary\s+source=\\?"([^"\\]+)\\?">', text)
    for m in matches:
        urls.append(m.group(1))
    # match <QuestionSource url="...">
    matches2 = re.finditer(r'<QuestionSource\s+url=\\?"([^"\\]+)\\?">', text)
    for m in matches2:
        urls.append(m.group(1))
    return list(set(urls))


async def main():
    parser = argparse.ArgumentParser(
        description="Test LLM relevance filter on a forecast artifact dir."
    )
    parser.add_argument(
        "data_dir", help="Path to the forecast data directory (e.g., data/41594_...)"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Directory {data_dir} does not exist.")
        return

    # Load question details
    q_file = data_dir / "00_question.json"
    if not q_file.exists():
        q_file = data_dir / "question.json"

    if not q_file.exists():
        print(f"Could not find question.json in {data_dir}")
        return

    with open(q_file) as f:
        q_data = json.load(f)

    # Structure might vary depending on whether it's raw api response or stripped
    if "title" in q_data:
        title = q_data.get("title", "")
        desc = q_data.get("description", "")
        res = q_data.get("resolution_criteria", "")
        fp = q_data.get("fine_print", "")
    elif "question" in q_data:  # raw api format
        title = q_data["question"].get("title", "")
        desc = q_data["question"].get("description", "")
        res = q_data["question"].get("resolution_criteria", "")
        fp = q_data["question"].get("fine_print", "")
    else:
        print("Unknown question.json format")
        return

    details = QuestionDetails(
        title=title,
        description=desc,
        resolution_criteria=res,
        fine_print=fp,
    )

    print(f"Question: {details.title}\n")

    # Extract URLs from research files
    urls = []
    research_dir = data_dir / "research"
    if not research_dir.exists():
        research_dir = data_dir / "02_research"

    if research_dir.exists():
        for f in research_dir.glob("*.json"):
            with open(f) as file:
                content = file.read()
                urls.extend(extract_urls_from_text(content))

    urls = list(set(urls))
    print(f"Found {len(urls)} URLs to test.\n")

    if not urls:
        print("No URLs found in the research files.")
        return

    from src.config import ResolvedConfig

    config_obj = ResolvedConfig.from_yaml("config.yaml", "preview")
    config = config_obj.model_dump() if hasattr(config_obj, "model_dump") else vars(config_obj)
    # Wait, ResolvedConfig returns a Pydantic model? Let's check `to_dict()` or `dict()`

    # Just to be safe, I'll pass the raw dict
    import yaml

    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    print(f"Config loaded: type={type(config)}")
    cost_tracker = CostTracker()
    llm = LLMClient(cost_tracker)
    output_dir = Path("scratchpad/test_relevance_filter")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use the question ID or first 15 chars of title for the report name
    question_id = q_data.get("id", "unknown_id")
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"{question_id}_{timestamp}"
    report_path = output_dir / f"{report_name}.md"

    with open(report_path, "w") as f:
        f.write("# Relevance Filter Test Results\n\n")
        f.write(f"**Question:** {details.title}\n\n")
        f.write(f"**Tested {len(urls)} URLs**\n\n")

    kept = 0
    dropped = 0
    failed = 0
    total_cost = 0.0

    print(f"Running extraction on {len(urls)} URLs...\n")

    # Run concurrent extraction
    async with ConcurrentContentExtractor(config) as extractor:
        extracted_results = await extractor.extract_content(urls)

    for url in urls:
        if not url.startswith("http"):
            continue

        print(f"--- URL: {url} ---")
        try:
            res_dict = extracted_results.get(url)
            if not isinstance(res_dict, dict):
                print(f"  -> Failed to extract content: res_dict is type {type(res_dict)}")
                failed += 1
                continue

            if not res_dict.get("success") or not res_dict.get("content"):
                err = res_dict.get("error", "unknown") if isinstance(res_dict, dict) else "unknown"
                print(f"  -> Failed to extract content: {err}")
                failed += 1
                continue

            html = res_dict.get("content", "")
            # 2. BM25
            truncated = _bm25_filter_content(html, details.title, max_chars=15000)
            print(f"  -> Extracted & BM25 truncated to {len(truncated)} chars")

            # 3. LLM Filter/Summarize
            prompt = TEST_ARTICLE_SUMMARY_PROMPT.format(
                title=details.title,
                resolution_criteria=details.resolution_criteria,
                fine_print=details.fine_print,
                background=details.description,
                article=truncated,
            )

            response = await llm.complete(
                model=config.get("models", {})
                .get("quality", {})
                .get("article_summarizer", "claude-3-haiku-20240307"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.0,
            )

            total_cost += response.cost
            summary = response.content.strip()

            # Extract reasoning from OpenRouter's reasoning_details or similar structure
            reasoning = "No reasoning captured"
            if getattr(response, "reasoning_content", None):
                reasoning = response.reasoning_content
            elif hasattr(response, "raw_response") and response.raw_response:
                try:
                    # Look for it inside raw_response -> choices -> message
                    choices = response.raw_response.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        if "reasoning_content" in message:
                            reasoning = message["reasoning_content"]
                        elif "reasoning" in message:
                            reasoning = message["reasoning"]
                except Exception:
                    pass

            if summary.upper() == "IRRELEVANT" or summary.upper().startswith("IRRELEVANT"):
                print("  -> RESULT: \033[91mDROPPED (IRRELEVANT)\033[0m")
                dropped += 1
                result_str = "DROPPED"
            else:
                print(f"  -> RESULT: \033[92mKEPT\033[0m (Summary length: {len(summary)} chars)")
                # Print a small snippet to see what it kept
                snippet = summary.replace("\n", " ")[:100]
                print(f"     Snippet: {snippet}...")
                kept += 1
                result_str = "KEPT"

            with open(report_path, "a") as f:
                f.write(f"### URL: {url}\n")
                f.write(f"**Result**: {result_str}\n")
                f.write(
                    f"**Cost**: ${response.cost:.5f} (Input: {response.input_tokens}, Output: {response.output_tokens}, Reasoning: {response.reasoning_tokens})\n\n"
                )
                f.write(f"**Reasoning**:\n```\n{reasoning}\n```\n\n")
                f.write(f"**Summary**:\n```\n{summary}\n```\n\n---\n\n")

        except Exception as e:
            print(f"  -> Error processing URL: {e}")
            failed += 1

    print("\n" + "=" * 40)
    print(f"SUMMARY: Kept: {kept} | Dropped: {dropped} | Failed/Skipped: {failed}")
    print(f"Cost of test: ${total_cost:.4f}")
    print("=" * 40)


if __name__ == "__main__":
    asyncio.run(main())
