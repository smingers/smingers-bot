# Forecasting Pipeline Overview

This document describes the end-to-end forecasting pipeline used to generate probability predictions for Metaculus questions.

---

## High-Level Flow

```
Question → Historical Research → Step 1 (Outside View) → Current Research → Step 2 (Inside View) → Aggregation → Submit
              ↓                        ↓                       ↓                      ↓
         Google/News/Agent        5 Agents              Google/News/AskNews      5 Agents
         (base rates)             reason                (recent signals)         refine
```

---

## Phase 1: Historical Research

**Purpose:** Gather base rate information and historical context for the "outside view" prediction.

**Trigger:** A query-generation model analyzes the question and produces 3 search queries.

| Tool | Service | Query Style |
|------|---------|-------------|
| Google | Serper API | Keyword-optimized, ≤6 words |
| Google News | Serper API | Keyword-optimized, ≤6 words |
| Agent | Agentic search (o3 in production) | Natural language, up to 4 sentences |

**Agentic Search:** An LLM iteratively searches the web, reads pages, and synthesizes a research report. The model reasons about what to search next based on what it has learned. Limited to 7 steps.

**Output:** Combined research saved to `research/search_historical.json`. This context feeds into Step 1.

---

## Phase 2: Step 1 — Outside View Prediction

**Purpose:** Each of 5 agents independently analyzes the historical research to form an initial probability estimate based on base rates and reference classes.

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

This creates a cross-model cycle: Sonnet 4.5 → o3-mini-high → o3 → Sonnet 4.5, while agents #1 and #5 remain anchored to their own reasoning.

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
│   └── api_response.json      # Metaculus API response
└── metadata.json              # Costs, timing, config
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
