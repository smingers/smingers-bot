# Forecasting Pipeline Overview

This document describes the end-to-end forecasting pipeline used to generate probability predictions for Metaculus questions.

---

## High-Level Flow

```
Fetch Question → Historical Research → Step 1 (Outside View) → Current Research → Step 2 (Inside View) → Aggregation → Submit → Save
       ↓                ↓                      ↓                      ↓                      ↓                              ↓
  Metaculus API    Google/News/Agent      5 Agents            Google/News/AskNews      5 Agents                      Database
                   (base rates)           reason              (recent signals)         refine
```

---

## Phase 0: Question Fetching

**Purpose:** Retrieve question details from Metaculus API.

**Process:** The pipeline fetches the question by ID or URL, extracting:
- Title, description, resolution criteria, fine print
- Question type (binary, numeric, multiple choice)
- Bounds and options (for numeric/MC questions)
- Community prediction and forecaster count

**Output:** Raw question data saved to `question.json`.

---

## Phase 1: Historical Research

**Purpose:** Gather base rate information and historical context for the "outside view" prediction.

**Trigger:** A query-generation model analyzes the question and produces 3 search queries.

| Tool | Service | Query Style |
|------|---------|-------------|
| Google | Serper API | Keyword-optimized, ≤6 words |
| Google News | Serper API | Keyword-optimized, ≤6 words |
| Agent | Agentic search (o3 in production) | Natural language, up to 4 sentences |

**Agentic Search:** An LLM performs iterative research in a loop:
1. Initial prompt analyzes the query and generates up to 5 Google/Google News searches
2. Searches are executed and results scraped
3. Continuation prompt asks the LLM to synthesize findings and decide if more research is needed
4. If the LLM includes a "Search queries:" section, the loop continues; otherwise it terminates
5. Maximum 7 iterations to prevent runaway costs

The agentic search model (o3 in production) generates a comprehensive ~1000-word research report as its final output.

**Article Summarization:** After Google/Google News searches return URLs, the pipeline scrapes each article's content and uses an LLM (Sonnet 4.5 in production) to summarize it into a concise digest. This runs in parallel across all scraped articles.

**Output:** Combined research saved to `research/search_historical.json`. This context feeds into Step 1.

---

## Phase 2: Step 1 — Outside View Prediction

**Purpose:** Each of 5 agents independently analyzes the historical research to form an initial probability estimate based on base rates and reference classes.

**System Prompt:** Each agent receives a "superforecaster" system prompt that positions them as a top-1% forecaster from the Good Judgment Project. The prompt instructs them to:
- Use Fermi analysis to break down questions
- Generate an outside view baseline from historical context
- Consider time remaining, status quo, sub-factors for Yes/No outcomes
- Write detailed rationale for colleagues to understand

**Input:** The historical research context (from Phase 1) is inserted into a shared prompt template.

**Process:** All 5 agents receive the identical prompt and run in parallel. Each produces:
- Source analysis (quality, factual vs. opinion)
- Reference class analysis (what similar events tell us)
- Timeframe analysis (historical patterns over similar periods)
- Initial probability estimate with reasoning

**Output:** Each agent's Step 1 response is saved to `ensemble/forecaster_N_step1/response.md`.

---

## Phase 3: Current Research

**Purpose:** Gather recent news and signals for the "inside view" adjustment.

**Trigger:** A query-generation model produces 3 search queries focused on recent developments.

| Tool | Service | Query Style |
|------|---------|-------------|
| Google | Serper API | Keyword-optimized, ≤6 words |
| Google News | Serper API | Keyword-optimized, ≤6 words |
| Assistant | AskNews API | Natural language query (72-hour lookback) |

**Note:** The "Assistant" tool maps to AskNews, which specializes in recent news aggregation. This differs from Phase 1's "Agent" tool (agentic search).

**AskNews Dual Strategy:** AskNews actually runs two searches per query:
1. "latest news" strategy — Most recent articles (hot news)
2. "news knowledge" strategy — Historical news context

Both are combined and sorted by publication date. A 12-second rate limit delay is enforced between calls (AskNews Pro tier limitation).

**Article Summarization:** Same as Phase 1 — scraped articles are summarized in parallel using Sonnet 4.5 (production) or Haiku (dry run).

**Output:** Combined research saved to `research/search_current.json`. This context feeds into Step 2.

---

## Phase 4: Step 2 — Inside View Prediction (with Cross-Pollination)

**Purpose:** Each agent refines its prediction by incorporating current news and another agent's reasoning.

**Cross-Pollination:** Before Step 2, agents receive a different agent's Step 1 output to create diversity:

| Agent | Model | Receives Step 1 From |
|-------|-------|---------------------|
| #1 | Claude Sonnet 4.5 | Agent #1 (itself) |
| #2 | Claude Sonnet 4.5 | Agent #4 (o3) |
| #3 | o3-mini-high | Agent #2 (Sonnet 4.5) |
| #4 | o3 | Agent #3 (o3-mini-high) |
| #5 | o3 | Agent #5 (itself) |

**Input:** Each agent receives:
1. The current research context (from Phase 3)
2. Their assigned Step 1 output (per cross-pollination map)

**Process:** All 5 agents run in parallel. Each produces a final probability estimate, calibrated against common biases (anchoring, overconfidence, etc.).

**Output:** Each agent's Step 2 response is saved to `ensemble/forecaster_N_step2/response.md`.

---

## Phase 5: Extraction & Aggregation

**Purpose:** Parse each agent's final probability and combine into a single prediction.

**Extraction:** Regex patterns find probability statements in each Step 2 response. Handles formats like:
- "Probability: 65%"
- "My forecast is 0.65"
- "I estimate a 65% chance"

**Aggregation:** Equal-weighted average of all successfully extracted probabilities.

```
Final = (P₁ + P₂ + P₃ + P₄ + P₅) / 5
```

**Failure Handling:** If all agents fail to produce valid probabilities, the pipeline raises an error rather than submitting a fallback value.

**Output:**
- Individual extractions saved to `ensemble/forecaster_N/extracted.json`
- Final aggregation saved to `ensemble/aggregation.json`

---

## Phase 6: Submission

**Purpose:** Submit the final prediction to Metaculus.

**Modes:**
- `dry_run` — Uses cheap models (Haiku), does not submit
- `dry_run_heavy` — Uses production models, does not submit
- `production` — Uses production models, submits to Metaculus

**Output:** API response saved to `submission/api_response.json`.

---

## Phase 7: Storage & Analytics

**Purpose:** Persist forecast data for analysis and debugging.

**Artifacts:** All intermediate outputs are saved to disk (see Artifact Directory Structure below).

**Database:** Key metrics are written to SQLite (`data/forecasts.db`) with three tables:
- `forecasts` — Question ID, timestamp, type, final prediction, total cost, config hash
- `agent_predictions` — Per-agent model, weight, prediction, reasoning length
- `research_sources` — Query, tool used, number of results

**Cost Tracking:** Every LLM call is tracked with input/output tokens and cost. The total cost breakdown is saved to `metadata.json`.

---

## Model Configuration

### Utility Tasks (Research Phase)

| Task | Dry Run Model | Production Model |
|------|---------------|------------------|
| Query Generation | claude-3.5-haiku | o3 |
| Article Summarization | claude-3.5-haiku | claude-sonnet-4.5 |
| Agentic Search | claude-3.5-haiku | o3 |

### Ensemble Agents (Forecasting Phases)

| Agent | Dry Run Model | Production Model |
|-------|---------------|------------------|
| #1 | claude-3.5-haiku | claude-sonnet-4.5 |
| #2 | claude-3.5-haiku | claude-sonnet-4.5 |
| #3 | claude-3.5-haiku | o3-mini-high |
| #4 | claude-3.5-haiku | o3 |
| #5 | claude-3.5-haiku | o3 |

---

## Artifact Directory Structure

Each forecast creates a timestamped directory with all intermediate outputs:

```
data/{question_id}_{timestamp}/
├── question.json              # Raw Metaculus API response
├── research/
│   ├── query_historical.md    # Generated historical queries
│   ├── search_historical.json # Historical search results
│   ├── query_current.md       # Generated current queries
│   └── search_current.json    # Current search results
├── ensemble/
│   ├── step1_prompt.md        # Shared Step 1 prompt (with historical context)
│   ├── forecaster_1_step1/
│   │   └── response.md        # Agent 1 outside view
│   ├── forecaster_1_step2/
│   │   └── response.md        # Agent 1 inside view
│   ├── forecaster_1/
│   │   └── extracted.json     # {probability: 0.52}
│   ├── ... (agents 2-5)
│   └── aggregation.json       # {final_probability: 0.545}
├── submission/
│   ├── final_prediction.json  # Submitted prediction value
│   └── api_response.json      # Metaculus API response
├── tool_usage.json            # Detailed tracking of all tools/queries used
└── metadata.json              # Costs, timing, config hash
```

---

## Question Types

The pipeline supports three question types, each with specialized prompts and extraction logic:

| Type | Output Format | Aggregation |
|------|---------------|-------------|
| Binary | Single probability (0-1) | Average of 5 probabilities |
| Multiple Choice | Probability per option | Average each option, normalize to sum to 1 |
| Numeric | 201-point CDF | Average CDFs point-by-point |

---

## Key Design Decisions

1. **Two-phase research:** Historical (base rates) feeds Step 1; Current (recent signals) feeds Step 2. They are never combined in a single prompt.

2. **Cross-pollination:** Agents see reasoning from different model families to create genuine diversity, not just sampling randomness.

3. **Fail loudly:** Pipeline errors rather than submitting fallback values (e.g., 50% for binary) when extraction fails.

4. **Equal weights:** All 5 agents contribute equally to the final forecast. No agent is privileged.

5. **Fresh instances:** Each Step 2 is a fresh API call with no conversation memory. The only "memory" is the Step 1 output explicitly included in the prompt.

6. **Parallel execution:** Historical and current query generation run in parallel. All 5 agents run Step 1 in parallel, then all 5 run Step 2 in parallel. Article summarization is parallelized across all scraped URLs.

7. **Context-aware summarization:** Article summaries are generated with the specific forecasting question in mind, extracting facts/statistics/expert opinions relevant to that question rather than generic summaries.

---

## Research Output Format

Search results are combined into a single context string with XML-like tags:

```
<Summary source="https://example.com/article1">
[LLM-generated summary of article 1, focused on the forecasting question]
</Summary>

<Summary source="https://example.com/article2">
[LLM-generated summary of article 2]
</Summary>

<Agent_report>
Query: [original agentic search query]
[~1000 word comprehensive research report synthesized by the agentic search model]
</Agent_report>

<Asknews_articles>
Query: [original AskNews query]
**Article Title 1**
[Summary from AskNews]
Publish date: January 28, 2026
Source: [source_id](url)

**Article Title 2**
...
</Asknews_articles>
```

This combined context is what the ensemble agents receive in their prompts.
