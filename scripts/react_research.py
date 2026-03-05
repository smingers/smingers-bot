"""
Standalone Hybrid ReAct Research Agent

Combines upfront planning with iterative ReAct execution.
Takes a question from an existing data/ artifact folder (or Metaculus API)
and runs a Thought -> Action -> Observation loop to build a research brief.

Usage:
    poetry run python scripts/react_research.py --data-dir data/41594_20260226_211645
    poetry run python scripts/react_research.py --question 41594
    poetry run python scripts/react_research.py --data-dir data/41594_20260226_211645 --plan-only
    poetry run python scripts/react_research.py --data-dir data/41594_20260226_211645 --max-steps 5
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bot.search import QuestionDetails, SearchPipeline  # noqa: E402
from src.config import ResolvedConfig  # noqa: E402
from src.utils.llm import LLMClient, get_cost_tracker, reset_cost_tracker  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PLAN_PROMPT = """\
You are a superforecaster's research assistant. Your job is to create a research \
plan for the following forecasting question. You are NOT forecasting — you are \
planning what information to gather so that a forecaster can make a well-calibrated \
prediction.

## Question
Title: {title}
Type: {question_type}
Resolution date: {resolution_date}
Today's date: {today}
Days until resolution: {days_to_resolution}

## Background
{description}

## Resolution criteria
{resolution_criteria}

## Fine print
{fine_print}

## Your task

Think carefully about this question. Then produce a research plan with two parts:

### Part 1: Key uncertainties
List the 3-5 most important things a forecaster would need to know to make a \
good prediction on this question. For each, explain briefly WHY it matters for \
the forecast. Be specific to THIS question — not generic forecasting advice.

### Part 2: Research plan
For each key uncertainty, describe what you would search for and which tool you \
would use. Available tools:

{tool_descriptions}

Order your plan from most important to least important. The researcher will work \
through the plan iteratively, so front-load the highest-value searches.

Format your plan as a numbered list. Each item should have:
- What to search for (be specific)
- Which tool to use
- What you hope to learn from it
- How it connects to the key uncertainties above

Keep the plan to 6-10 items. You have a limited budget — be strategic.\
"""

REACT_SYSTEM_PROMPT = """\
You are a research agent for a superforecaster. You are researching a forecasting \
question by iteratively searching for information and reasoning about what you find.

## Rules
1. Each turn, you MUST output a Thought (your reasoning) and then EITHER an Action \
OR a Finish.
2. Your Thought should reflect on what you've learned so far and what's still missing.
3. An Action is a search query using one tool. You may output MULTIPLE Actions \
per turn if they are independent (e.g. fetching several tickers, or running a \
Google query alongside a yFinance lookup). All actions in a turn execute in parallel.
4. A Finish means you have enough information to write the research brief.
5. Stay focused on the question. Don't drift into tangentially related topics.
6. If a search returns nothing useful, reason about why and try a different approach.
7. You have a limited step budget — be strategic. Batch independent queries into \
one turn to save steps.
8. You may DEVIATE from the plan if your findings suggest a different direction is \
more valuable. The plan is a guide, not a mandate.

## Output format

Thought: <your reasoning about what you know and what you need to find out>

Action: <tool_name>: <query>
Action: <tool_name>: <query>
...

OR

Thought: <your reasoning about why you have enough information>

Finish: done

You may output 1-4 Action lines per turn. All will execute in parallel.

Available tools: {tool_list}

Tool guidelines:
- Google: keyword queries, max 6 words. Good for reference pages, reports, datasets.
- Google News: keyword queries, max 6 words. Good for recent news articles.
- AskNews: 1-2 sentence semantic query. Good for recent news with geographic/industry scope.
- FRED: FRED series ID (e.g. "UNRATE") or plain-language description. Economic data only.
- yFinance: ticker symbol (e.g. "AAPL"). Stock/ETF prices, fundamentals, options.
- Google Trends: single search term. Returns 90-day interest data.\
"""

REACT_TURN_PROMPT = """\
## Question (reminder)
{title}
Resolution date: {resolution_date} | Today: {today} | Days left: {days_to_resolution}
Resolution criteria: {resolution_criteria}

## Research plan
{plan}

## Research so far
{history}

Continue your research. Output a Thought and then either an Action or a Finish.\
"""

FINAL_BRIEF_PROMPT = """\
You are a research assistant to a superforecaster. Based on the research below, \
write a structured research brief for the following question.

## Question
Title: {title}
Type: {question_type}
Resolution date: {resolution_date}
Resolution criteria: {resolution_criteria}
Fine print: {fine_print}

## Full research trace
{history}

## Instructions

Write a research brief with the following sections:

### Key findings
The most important facts, data points, and evidence discovered during research. \
Cite sources where available. Organize by relevance to the forecast.

### Base rate / historical context
What historical precedents or base rates are relevant? What happened in similar \
situations?

### Current situation
What is the latest state of affairs? What recent developments matter?

### Key uncertainties
What important questions remain unanswered? What couldn't be determined from \
the research?

### Sources
List all sources consulted with brief descriptions.

Be factual and concise. Do NOT make a forecast — just present the evidence.

CRITICAL: Only cite sources that appear in the research trace above. Do NOT \
fabricate, hallucinate, or invent sources, data points, or search results that \
were not actually retrieved. If the research trace is empty or incomplete, say \
so explicitly and note what information is missing.\
"""

# ---------------------------------------------------------------------------
# Tool descriptions
# ---------------------------------------------------------------------------

TOOL_DESCRIPTIONS = {
    "Google": "Web search for reference pages, datasets, reports, Wikipedia. Max 6-word keyword queries.",
    "Google News": "Recent news articles. Max 6-word keyword queries.",
    "AskNews": "Semantic news search. 1-2 sentence queries with geographic/industry scope.",
    "FRED": "Federal Reserve Economic Data. Series IDs (e.g. UNRATE) or plain-language descriptions.",
    "yFinance": "Yahoo Finance. Ticker symbols (e.g. AAPL). Price history, fundamentals, options.",
    "Google Trends": "Google search interest over 90 days. Single search term.",
}


def get_enabled_tools(config: dict) -> dict[str, str]:
    """Return tool name -> description for enabled tools."""
    research = config.get("research", {})
    tools = {}
    if research.get("google_enabled", True) and os.getenv("SERPER_API_KEY"):
        tools["Google"] = TOOL_DESCRIPTIONS["Google"]
        tools["Google News"] = TOOL_DESCRIPTIONS["Google News"]
    if research.get("asknews_enabled", True) and os.getenv("ASKNEWS_CLIENT_ID"):
        tools["AskNews"] = TOOL_DESCRIPTIONS["AskNews"]
    if research.get("fred_enabled", True) and os.getenv("FRED_API_KEY"):
        tools["FRED"] = TOOL_DESCRIPTIONS["FRED"]
    if research.get("yfinance_enabled", True):
        tools["yFinance"] = TOOL_DESCRIPTIONS["yFinance"]
    if research.get("google_trends_enabled", True):
        tools["Google Trends"] = TOOL_DESCRIPTIONS["Google Trends"]
    return tools


# ---------------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------------


def load_question_from_data_dir(data_dir: str) -> dict:
    """Load question context from an existing artifact directory."""
    qpath = Path(data_dir) / "question.json"
    if not qpath.exists():
        raise FileNotFoundError(f"No question.json found in {data_dir}")

    with open(qpath) as f:
        data = json.load(f)

    q = data.get("question", {})
    return {
        "id": data.get("id", "unknown"),
        "title": data.get("title", q.get("title", "Unknown")),
        "type": q.get("type", "binary"),
        "description": q.get("description", ""),
        "resolution_criteria": q.get("resolution_criteria", ""),
        "fine_print": q.get("fine_print", ""),
        "resolution_date": q.get("scheduled_resolve_time", ""),
        "options": q.get("options"),
    }


async def load_question_from_api(question_id: int) -> dict:
    """Fetch question from Metaculus API."""
    from src.utils.metaculus_api import MetaculusClient

    async with MetaculusClient() as client:
        q = await client.get_question(question_id)
    return {
        "id": q.id,
        "title": q.title or "Unknown",
        "type": q.question_type or "binary",
        "description": q.description or "",
        "resolution_criteria": q.resolution_criteria or "",
        "fine_print": q.fine_print or "",
        "resolution_date": q.scheduled_resolve_time or "",
        "options": q.options,
    }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


# Patterns that match Action/Thought/Finish with optional markdown bold/italic
_ACTION_LINE_RE = re.compile(r"^\s*\**\s*Action\s*\**\s*:\s*(.+)", re.IGNORECASE)
_FINISH_LINE_RE = re.compile(r"^\s*\**\s*Finish\s*\**\s*:?\s*(.*)", re.IGNORECASE)
_THOUGHT_PREFIX_RE = re.compile(r"^\s*\**\s*Thought\s*\**\s*:\s*", re.IGNORECASE)
_ACTION_OR_FINISH_RE = re.compile(r"^\s*\**\s*(Action|Finish)\s*\**\s*:", re.IGNORECASE)


def parse_actions(response: str) -> list[tuple[str, str]]:
    """Parse all 'Action: tool_name: query' lines from LLM response.

    Handles markdown bold (**Action:**), extra whitespace, etc.
    Returns a list of (tool_name, query) tuples (may be empty).
    """
    actions: list[tuple[str, str]] = []
    for line in response.split("\n"):
        m = _ACTION_LINE_RE.match(line)
        if m:
            rest = m.group(1).strip()
            # Strip trailing markdown bold if present
            rest = rest.rstrip("*").strip()
            if ":" in rest:
                tool, query = rest.split(":", 1)
                actions.append((tool.strip().strip("*"), query.strip().strip("*")))
    return actions


def has_finish(response: str) -> bool:
    """Check if response contains a Finish signal."""
    for line in response.split("\n"):
        if _FINISH_LINE_RE.match(line):
            return True
    return False


def extract_thought(response_text: str) -> str:
    """Extract the Thought portion of a response (everything before Action/Finish)."""
    thought_lines = []
    for line in response_text.split("\n"):
        if _ACTION_OR_FINISH_RE.match(line):
            break
        text = line.strip()
        # Strip Thought: prefix (with optional bold)
        text = _THOUGHT_PREFIX_RE.sub("", text).strip()
        thought_lines.append(text)
    return "\n".join(thought_lines).strip()


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------


async def execute_action(
    tool_name: str,
    query: str,
    search_pipeline: SearchPipeline,
    question_details: QuestionDetails,
    seen_urls: set[str],
) -> str:
    """Execute a single search action and return the observation."""
    tool_lower = tool_name.lower().strip()

    try:
        if tool_lower in ("google", "google news"):
            is_news = tool_lower == "google news"
            result = await search_pipeline._google_search_and_scrape(
                query=query,
                is_news=is_news,
                question_details=question_details,
                seen_urls=seen_urls,
            )
            return result.formatted_output or "No results found."

        elif tool_lower == "asknews":
            result = await search_pipeline._call_asknews(news_query=query)
            return result or "No results found."

        elif tool_lower == "fred":
            return await search_pipeline._fred_search(query) or "No results found."

        elif tool_lower == "yfinance":
            return await search_pipeline._yfinance_search(query) or "No results found."

        elif tool_lower == "google trends":
            return (
                await search_pipeline._google_trends_search(
                    query, question_details=question_details
                )
                or "No results found."
            )

        else:
            return f"Unknown tool: {tool_name}. Available: Google, Google News, AskNews, FRED, yFinance, Google Trends."

    except Exception as e:
        logger.error(f"Error executing {tool_name} query '{query}': {e}")
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


async def run_react_research(
    question: dict,
    config: ResolvedConfig,
    model: str,
    max_steps: int = 7,
    plan_only: bool = False,
    verbose: bool = False,
) -> dict:
    """Run the hybrid plan + ReAct research loop."""
    reset_cost_tracker()
    llm = LLMClient()
    config_dict = config.to_dict()
    enabled_tools = get_enabled_tools(config_dict)

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    res_date = question.get("resolution_date", "unknown")
    try:
        days_left = (
            datetime.fromisoformat(res_date.replace("Z", "+00:00")) - datetime.now(UTC)
        ).days
    except (ValueError, TypeError):
        days_left = "unknown"

    tvars = {
        "title": question["title"],
        "question_type": question["type"],
        "resolution_date": res_date,
        "today": today,
        "days_to_resolution": days_left,
        "description": question["description"],
        "resolution_criteria": question["resolution_criteria"],
        "fine_print": question["fine_print"],
    }

    # --- Phase 1: Plan ---
    print("\n" + "=" * 70)
    print("PHASE 1: PLANNING")
    print("=" * 70)

    tool_desc_text = "\n".join(f"- **{k}**: {v}" for k, v in enabled_tools.items())
    plan_prompt = PLAN_PROMPT.format(**tvars, tool_descriptions=tool_desc_text)

    plan_response = await llm.complete(
        model=model,
        messages=[{"role": "user", "content": plan_prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    plan = plan_response.content
    print(f"\n{plan}")
    print(f"\n[Plan cost: ${plan_response.cost:.4f}]")

    if plan_only:
        return {"plan": plan, "trace": [], "brief": None, "cost": plan_response.cost}

    # --- Phase 2: ReAct execution ---
    print("\n" + "=" * 70)
    print("PHASE 2: REACT EXECUTION")
    print("=" * 70)

    question_details = QuestionDetails(
        title=question["title"],
        resolution_criteria=question["resolution_criteria"],
        fine_print=question["fine_print"],
        description=question["description"],
        resolution_date=res_date,
    )

    tool_list = ", ".join(enabled_tools.keys())
    system_prompt = REACT_SYSTEM_PROMPT.format(tool_list=tool_list)

    trace: list[dict] = []
    seen_urls: set[str] = set()

    async with SearchPipeline(config_dict, llm_client=llm) as search_pipeline:
        for step in range(1, max_steps + 1):
            print(f"\n--- Step {step}/{max_steps} ---")

            # Build history from trace
            if trace:
                history_parts = []
                for t in trace:
                    history_parts.append(f"### Step {t['step']}")
                    history_parts.append(f"**Thought:** {t['thought']}")
                    if t.get("action"):
                        history_parts.append(f"**Action:** {t['action']}")
                        obs = t.get("observation", "")
                        if len(obs) > 6000:
                            obs = obs[:6000] + "\n... [truncated]"
                        history_parts.append(f"**Observation:**\n{obs}")
                    history_parts.append("")
                history_text = "\n".join(history_parts)
            else:
                history_text = "(No research conducted yet)"

            turn_prompt = REACT_TURN_PROMPT.format(**tvars, plan=plan, history=history_text)

            response = await llm.complete(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": turn_prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            response_text = response.content

            if verbose:
                print(f"\n{response_text}")

            thought = extract_thought(response_text)

            if not verbose:
                thought_display = thought[:200] + "..." if len(thought) > 200 else thought
                print(f"Thought: {thought_display}")

            # Finish?
            if has_finish(response_text):
                print("\n>> Agent signaled FINISH")
                trace.append(
                    {
                        "step": step,
                        "thought": thought,
                        "action": None,
                        "tool": None,
                        "query": None,
                        "observation": None,
                    }
                )
                break

            # Parse actions (may be multiple per turn)
            actions = parse_actions(response_text)
            if not actions:
                print(">> No action parsed from response. Full LLM output:")
                print(response_text)
                print(">> Retrying step with explicit nudge...")

                # Retry once with a nudge to use the correct format
                retry_prompt = turn_prompt + (
                    "\n\nIMPORTANT: You must output an Action in this exact format:\n"
                    "Action: <tool_name>: <query>\n\n"
                    "For example:\n"
                    "Action: Google Trends: ethel kennedy\n"
                    "Action: Google News: iran nuclear talks 2026\n\n"
                    "Output your Thought and then at least one Action now."
                )
                retry_response = await llm.complete(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": retry_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1500,
                )
                response_text = retry_response.content
                thought = extract_thought(response_text)

                if has_finish(response_text):
                    print("\n>> Agent signaled FINISH on retry")
                    trace.append(
                        {
                            "step": step,
                            "thought": thought,
                            "action": None,
                            "tool": None,
                            "query": None,
                            "observation": None,
                        }
                    )
                    break

                actions = parse_actions(response_text)
                if not actions:
                    print(">> Still no action parsed after retry. Full output:")
                    print(response_text)
                    print(">> Giving up on this step.")
                    trace.append(
                        {
                            "step": step,
                            "thought": thought,
                            "action": None,
                            "tool": None,
                            "query": None,
                            "observation": None,
                        }
                    )
                    break

            # Execute all actions in parallel
            for tool_name, query in actions:
                print(f"Action: {tool_name}: {query}")

            observations = await asyncio.gather(
                *(
                    execute_action(tool_name, query, search_pipeline, question_details, seen_urls)
                    for tool_name, query in actions
                )
            )

            # Record each action+observation as a separate trace entry within this step
            for i, ((tool_name, query), observation) in enumerate(
                zip(actions, observations, strict=True)
            ):
                obs_display = observation[:300] + "..." if len(observation) > 300 else observation
                label = f"{tool_name}: {query}"
                suffix = f" [{i + 1}/{len(actions)}]" if len(actions) > 1 else ""
                print(f"Observation{suffix}: {obs_display}")

                trace.append(
                    {
                        "step": step,
                        "thought": thought if i == 0 else f"(parallel with step {step} action 1)",
                        "action": label,
                        "tool": tool_name,
                        "query": query,
                        "observation": observation,
                    }
                )

    # --- Phase 3: Final brief ---
    print("\n" + "=" * 70)
    print("PHASE 3: RESEARCH BRIEF")
    print("=" * 70)

    full_history_parts = []
    for t in trace:
        full_history_parts.append(f"### Step {t['step']}")
        full_history_parts.append(f"**Thought:** {t['thought']}")
        if t.get("action"):
            full_history_parts.append(f"**Action:** {t['action']}")
            full_history_parts.append(f"**Observation:**\n{t.get('observation', '')}")
        full_history_parts.append("")
    full_history = "\n".join(full_history_parts)

    brief_prompt = FINAL_BRIEF_PROMPT.format(
        title=question["title"],
        question_type=question["type"],
        resolution_date=res_date,
        resolution_criteria=question["resolution_criteria"],
        fine_print=question["fine_print"],
        history=full_history,
    )

    brief_response = await llm.complete(
        model=model,
        messages=[{"role": "user", "content": brief_prompt}],
        temperature=0.2,
        max_tokens=4000,
    )
    brief = brief_response.content
    print(f"\n{brief}")

    # --- Summary ---
    cost_summary = get_cost_tracker().get_summary()
    print("\n" + "=" * 70)
    print("COST SUMMARY")
    print("=" * 70)
    print(f"Total LLM calls: {cost_summary['total_calls']}")
    print(f"Total cost: ${cost_summary['total_cost']:.4f}")
    print(f"Input tokens: {cost_summary['total_input_tokens']:,}")
    print(f"Output tokens: {cost_summary['total_output_tokens']:,}")
    print(f"Steps taken: {len([t for t in trace if t.get('action')])}")

    return {"plan": plan, "trace": trace, "brief": brief, "cost": cost_summary}


# ---------------------------------------------------------------------------
# Output saving
# ---------------------------------------------------------------------------


def save_output(result: dict, question: dict, output_dir: str | None = None):
    """Save research output to files."""
    if output_dir is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_dir = f"scratchpad/react_research/{question['id']}_{timestamp}"

    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "plan.md"), "w") as f:
        f.write(f"# Research Plan: {question['title']}\n\n")
        f.write(result["plan"])

    with open(os.path.join(output_dir, "trace.md"), "w") as f:
        f.write(f"# Research Trace: {question['title']}\n\n")
        for t in result["trace"]:
            f.write(f"## Step {t['step']}\n\n")
            f.write(f"**Thought:** {t['thought']}\n\n")
            if t.get("action"):
                f.write(f"**Action:** {t['action']}\n\n")
                f.write(f"**Observation:**\n{t.get('observation', '')}\n\n")
            f.write("---\n\n")

    if result.get("brief"):
        with open(os.path.join(output_dir, "brief.md"), "w") as f:
            f.write(f"# Research Brief: {question['title']}\n\n")
            f.write(result["brief"])

    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(
            {
                "question_id": question["id"],
                "question_title": question["title"],
                "question_type": question["type"],
                "timestamp": datetime.now(UTC).isoformat(),
                "cost": result.get("cost"),
                "steps": len([t for t in result["trace"] if t.get("action")]),
            },
            f,
            indent=2,
        )

    print(f"\nOutput saved to: {output_dir}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hybrid ReAct Research Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--data-dir", help="Path to existing data/ artifact directory")
    group.add_argument("--question", type=int, help="Metaculus question ID")

    parser.add_argument(
        "--model", default="openrouter/openai/o3", help="Model for reasoning (default: o3)"
    )
    parser.add_argument("--max-steps", type=int, default=7, help="Maximum ReAct steps (default: 7)")
    parser.add_argument("--plan-only", action="store_true", help="Just print the plan")
    parser.add_argument("--verbose", action="store_true", help="Show full LLM responses")
    parser.add_argument("--no-save", action="store_true", help="Don't save output files")
    parser.add_argument("--mode", default="preview", choices=["test", "preview", "live"])

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    # Suppress noisy third-party loggers
    for noisy_logger in ("httpx", "httpcore", "litellm", "LiteLLM"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    config = ResolvedConfig.from_yaml("config.yaml", mode=args.mode)

    if args.data_dir:
        question = load_question_from_data_dir(args.data_dir)
        print(f"Loaded question from {args.data_dir}")
    else:
        question = asyncio.run(load_question_from_api(args.question))
        print(f"Loaded question {args.question} from Metaculus API")

    print(f"Question: {question['title']}")
    print(f"Type: {question['type']}")
    print(f"Resolution: {question['resolution_date']}")

    result = asyncio.run(
        run_react_research(
            question=question,
            config=config,
            model=args.model,
            max_steps=args.max_steps,
            plan_only=args.plan_only,
            verbose=args.verbose,
        )
    )

    if not args.no_save and not args.plan_only:
        save_output(result, question)


if __name__ == "__main__":
    main()
