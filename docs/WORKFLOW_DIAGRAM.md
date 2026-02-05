# Metaculus Bot Workflow Diagram

## High-Level Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ENTRY POINTS                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   main.py (Interactive CLI)              run_bot.py (GitHub Actions)                    │
│   ─────────────────────────              ──────────────────────────                     │
│   python main.py                         python run_bot.py                              │
│     --question 41594                       --tournament 32916                           │
│     --mode test|preview|live               --question-selection new-only|reforecast     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FORECASTER ORCHESTRATOR                                    │
│                              (src/bot/forecaster.py)                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   1. Fetch question from Metaculus API                                                  │
│   2. Create artifact directory: data/{question_id}_{timestamp}/                         │
│   3. Route to type-specific handler based on question_type                              │
│                                                                                         │
│              ┌────────────────┬─────────────────┬──────────────────┐                    │
│              ▼                ▼                 ▼                  │                    │
│         ┌────────┐      ┌─────────┐      ┌─────────────────┐       │                    │
│         │ BINARY │      │ NUMERIC │      │ MULTIPLE CHOICE │       │                    │
│         └────────┘      └─────────┘      └─────────────────┘       │                    │
│              │               │                 │                   │                    │
│              └───────────────┴─────────────────┘                   │                    │
│                              │                                     │                    │
│                              ▼                                     │                    │
│                    ┌───────────────────┐                           │                    │
│                    │ 6-STEP PIPELINE   │ ◄─────────────────────────┘                    │
│                    │ (base_forecaster) │                                                │
│                    └───────────────────┘                                                │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed 6-Step Pipeline

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP 1: QUERY GENERATION                                                                 ║
║  ─────────────────────────                                                                ║
║                                                                                           ║
║  INPUT:  Question title, description, resolution_criteria, fine_print                     ║
║  MODEL:  test=Haiku, quality=o3                                                           ║
║                                                                                           ║
║  ┌─────────────────────────┐         ┌─────────────────────────┐                          ║
║  │   HISTORICAL QUERIES    │         │    CURRENT QUERIES      │                          ║
║  │   ──────────────────    │         │    ───────────────      │                          ║
║  │                         │ PARALLEL│                         │                          ║
║  │   "Generate 3-5 queries │◄───────►│   "Generate 3-5 queries │                          ║
║  │    for base rate info"  │         │    for recent news"     │                          ║
║  │                         │         │                         │                          ║
║  └───────────┬─────────────┘         └───────────┬─────────────┘                          ║
║              │                                   │                                        ║
║              ▼                                   ▼                                        ║
║  OUTPUT: 3-5 search queries          OUTPUT: 3-5 search queries                           ║
║  SAVED:  historical_queries.md       SAVED:  current_queries.md                           ║
║                                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
                                           │
                                           ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP 2: SEARCH EXECUTION                                                                 ║
║  ────────────────────────                                                                 ║
║                                                                                           ║
║  ┌────────────────────────────────────┐   ┌────────────────────────────────────┐          ║
║  │      HISTORICAL SEARCH             │   │       CURRENT SEARCH               │          ║
║  │      (for outside view)            │   │       (for inside view)            │          ║
║  ├────────────────────────────────────┤   ├────────────────────────────────────┤          ║
║  │                                    │   │                                    │          ║
║  │  ┌─────────────────────────────┐   │   │  ┌─────────────────────────────┐   │          ║
║  │  │ Google Web Search (Serper)  │   │   │  │ Google Web Search (Serper)  │   │          ║
║  │  └─────────────────────────────┘   │   │  └─────────────────────────────┘   │          ║
║  │              │                     │   │              │                     │          ║
║  │  ┌─────────────────────────────┐   │ P │  ┌─────────────────────────────┐   │          ║
║  │  │ Google News Search (Serper) │   │ A │  │ Google News Search (Serper) │   │          ║
║  │  └─────────────────────────────┘   │ R │  └─────────────────────────────┘   │          ║
║  │              │                     │ A │              │                     │          ║
║  │  ┌─────────────────────────────┐   │ L │  ┌─────────────────────────────┐   │          ║
║  │  │ Agentic Search (7 steps)    │   │ L │  │ AskNews API (72hr lookback) │   │          ║
║  │  │ - Iterative LLM research    │   │ E │  └─────────────────────────────┘   │          ║
║  │  │ - ~1000 word synthesis      │   │ L │              │                     │          ║
║  │  └─────────────────────────────┘   │   │  ┌─────────────────────────────┐   │          ║
║  │              │                     │   │  │ Agentic Search (7 steps)    │   │          ║
║  │  ┌─────────────────────────────┐   │   │  └─────────────────────────────┘   │          ║
║  │  │ Article Scraping (max 10)   │   │   │              │                     │          ║
║  │  └─────────────────────────────┘   │   │  ┌─────────────────────────────┐   │          ║
║  │              │                     │   │  │ Article Scraping (max 10)   │   │          ║
║  │  ┌─────────────────────────────┐   │   │  └─────────────────────────────┘   │          ║
║  │  │ Context-Aware Summarization │   │   │              │                     │          ║
║  │  └─────────────────────────────┘   │   │  ┌─────────────────────────────┐   │          ║
║  │              │                     │   │  │ Context-Aware Summarization │   │          ║
║  │              ▼                     │   │  └─────────────────────────────┘   │          ║
║  │  OUTPUT: historical_context        │   │              ▼                     │          ║
║  │          (~5000 chars)             │   │  OUTPUT: current_context           │          ║
║  │                                    │   │          (~5000 chars)             │          ║
║  │  SAVED: historical_search.json     │   │  SAVED: current_search.json        │          ║
║  └────────────────────────────────────┘   └────────────────────────────────────┘          ║
║                                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
                                           │
                                           ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP 3: OUTSIDE VIEW PREDICTION (5 Forecasters in Parallel)                               ║
║  ───────────────────────────────────────────────────────────                               ║
║                                                                                            ║
║  INPUT:  Question details + historical_context (base rate information)                     ║
║  PROMPT: BINARY_OUTSIDE_VIEW_PROMPT / NUMERIC_... / MULTIPLE_CHOICE_...                    ║
║                                                                                            ║
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          ║
║  │ Forecaster  │ │ Forecaster  │ │ Forecaster  │ │ Forecaster  │ │ Forecaster  │          ║
║  │     1       │ │     2       │ │     3       │ │     4       │ │     5       │          ║
║  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤          ║
║  │ Sonnet 4.5  │ │ Sonnet 4.5  │ │ o3-mini-high│ │    o3       │ │    o3       │          ║
║  │ weight=1.0  │ │ weight=1.0  │ │ weight=1.0  │ │ weight=1.0  │ │ weight=1.0  │          ║
║  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘          ║
║         │               │               │               │               │                 ║
║         ▼               ▼               ▼               ▼               ▼                 ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐          ║
║  │                    5 OUTSIDE VIEW OUTPUTS (reasoning about base rates)      │          ║
║  └─────────────────────────────────────────────────────────────────────────────┘          ║
║                                                                                            ║
║  SAVED: forecaster_1_outside_view.md ... forecaster_5_outside_view.md                      ║
║                                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
                                           │
                                           ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP 4: CROSS-POLLINATION                                                                 ║
║  ────────────────────────                                                                  ║
║                                                                                            ║
║  PURPOSE: Create diversity by sharing outputs between different model families             ║
║                                                                                            ║
║  CROSS-POLLINATION MAPPING:                                                                ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐          ║
║  │                                                                             │          ║
║  │   Forecaster 1 (Sonnet) ◄──── receives ◄──── Forecaster 1's output (self)  │          ║
║  │   Forecaster 2 (Sonnet) ◄──── receives ◄──── Forecaster 4's output (o3)    │          ║
║  │   Forecaster 3 (o3-mini) ◄─── receives ◄──── Forecaster 2's output (Sonnet)│          ║
║  │   Forecaster 4 (o3)     ◄──── receives ◄──── Forecaster 3's output (o3-mini│          ║
║  │   Forecaster 5 (o3)     ◄──── receives ◄──── Forecaster 5's output (self)  │          ║
║  │                                                                             │          ║
║  └─────────────────────────────────────────────────────────────────────────────┘          ║
║                                                                                            ║
║  RESULT: Each forecaster's inside view context =                                           ║
║          current_context + cross-pollinated outside view                                   ║
║                                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
                                           │
                                           ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP 5: INSIDE VIEW PREDICTION (5 Forecasters in Parallel)                                ║
║  ──────────────────────────────────────────────────────────                                ║
║                                                                                            ║
║  INPUT:  Question details + current_context + cross-pollinated outside view                ║
║  PROMPT: BINARY_INSIDE_VIEW_PROMPT / NUMERIC_... / MULTIPLE_CHOICE_...                     ║
║                                                                                            ║
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          ║
║  │ Forecaster  │ │ Forecaster  │ │ Forecaster  │ │ Forecaster  │ │ Forecaster  │          ║
║  │     1       │ │     2       │ │     3       │ │     4       │ │     5       │          ║
║  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤          ║
║  │ Sonnet 4.5  │ │ Sonnet 4.5  │ │ o3-mini-high│ │    o3       │ │    o3       │          ║
║  │             │ │             │ │             │ │             │ │             │          ║
║  │ Context:    │ │ Context:    │ │ Context:    │ │ Context:    │ │ Context:    │          ║
║  │ Own outside │ │ F4's outside│ │ F2's outside│ │ F3's outside│ │ Own outside │          ║
║  │ + current   │ │ + current   │ │ + current   │ │ + current   │ │ + current   │          ║
║  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘          ║
║         │               │               │               │               │                 ║
║         ▼               ▼               ▼               ▼               ▼                 ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐          ║
║  │           5 INSIDE VIEW OUTPUTS (refined predictions with current news)     │          ║
║  │                                                                             │          ║
║  │   Each output contains:                                                     │          ║
║  │   - Detailed reasoning                                                      │          ║
║  │   - Final probability/percentiles/distribution                              │          ║
║  └─────────────────────────────────────────────────────────────────────────────┘          ║
║                                                                                            ║
║  SAVED: forecaster_1_inside_view.md ... forecaster_5_inside_view.md                        ║
║                                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
                                           │
                                           ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP 6: EXTRACTION & AGGREGATION                                                          ║
║  ────────────────────────────────                                                          ║
║                                                                                            ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐          ║
║  │  A. EXTRACT PREDICTIONS FROM EACH FORECASTER                                │          ║
║  │  ──────────────────────────────────────────────                             │          ║
║  │                                                                             │          ║
║  │  BINARY:          Extract "Probability: 65%" → 0.65                         │          ║
║  │  NUMERIC:         Extract percentiles {10: 45.2, 50: 78.5, 90: 105.3}       │          ║
║  │                   → Generate 201-point CDF                                  │          ║
║  │  MULTIPLE CHOICE: Extract per-option probabilities → normalize to sum=1.0  │          ║
║  │                                                                             │          ║
║  └─────────────────────────────────────────────────────────────────────────────┘          ║
║                                           │                                               ║
║                                           ▼                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐          ║
║  │  B. AGGREGATE INTO FINAL PREDICTION                                         │          ║
║  │  ──────────────────────────────────────                                     │          ║
║  │                                                                             │          ║
║  │  BINARY (weighted average):                                                 │          ║
║  │  ┌────────────────────────────────────────────────────────────────┐         │          ║
║  │  │  F1: 0.42  ──┐                                                 │         │          ║
║  │  │  F2: 0.38  ──┤                                                 │         │          ║
║  │  │  F3: 0.35  ──┼──► Σ(prob × weight) / Σ(weight) = 0.40 FINAL   │         │          ║
║  │  │  F4: 0.45  ──┤     (all weights = 1.0)                         │         │          ║
║  │  │  F5: 0.40  ──┘                                                 │         │          ║
║  │  └────────────────────────────────────────────────────────────────┘         │          ║
║  │                                                                             │          ║
║  │  NUMERIC (point-wise CDF averaging):                                        │          ║
║  │  ┌────────────────────────────────────────────────────────────────┐         │          ║
║  │  │  For each of 201 CDF points:                                   │         │          ║
║  │  │  final_cdf[i] = Σ(cdf_i × weight) / Σ(weight)                  │         │          ║
║  │  └────────────────────────────────────────────────────────────────┘         │          ║
║  │                                                                             │          ║
║  │  MULTIPLE CHOICE (per-option averaging):                                    │          ║
║  │  ┌────────────────────────────────────────────────────────────────┐         │          ║
║  │  │  For each option: final[opt] = Σ(prob[opt] × weight) / Σ(wt)   │         │          ║
║  │  │  Then normalize so all options sum to 1.0                      │         │          ║
║  │  └────────────────────────────────────────────────────────────────┘         │          ║
║  │                                                                             │          ║
║  └─────────────────────────────────────────────────────────────────────────────┘          ║
║                                                                                            ║
║  SAVED: forecaster_1.json ... forecaster_5.json, aggregation.json                          ║
║                                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
                                           │
                                           ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  SUBMISSION (if mode=live)                                                                 ║
║  ─────────────────────────                                                                 ║
║                                                                                            ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐          ║
║  │                                                                             │          ║
║  │  BINARY:          POST prediction=0.40                                      │          ║
║  │  NUMERIC:         POST cdf=[0.001, 0.01, ..., 0.99, 0.999] (201 points)     │          ║
║  │  MULTIPLE CHOICE: POST distribution={"opt_1": 0.25, "opt_2": 0.35, ...}     │          ║
║  │                                                                             │          ║
║  └─────────────────────────────────────────────────────────────────────────────┘          ║
║                                                                                            ║
║  SAVED: final_prediction.json, api_response.json                                           ║
║                                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Artifact Directory Structure

```
data/{question_id}_{timestamp}/
│
├── 00_question.json                     # Raw Metaculus API response
│   └─ {id, title, description, resolution_criteria, type, ...}
│
├── 01_analysis.json                     # Parsed question metadata
│   └─ {question_type, bounds, options, fine_print, ...}
│
├── 02_research/
│   ├── query_historical_prompt.md       # Prompt sent to LLM
│   ├── query_historical.md              # LLM output: search queries
│   ├── query_current_prompt.md          # Prompt sent to LLM
│   ├── query_current.md                 # LLM output: search queries
│   ├── historical_search.json           # Search results + scraped articles
│   │   └─ {queries: [...], results: [...], articles: [...]}
│   └── current_search.json              # Search results + scraped articles
│
├── ensemble/
│   ├── outside_view_prompt.md           # Shared prompt template
│   │
│   ├── forecaster_1_outside_view.md     # Full LLM reasoning (base rates)
│   ├── forecaster_1_inside_view.md      # Full LLM reasoning (with news)
│   ├── forecaster_1.json                # Extracted: {probability: 0.42}
│   │
│   ├── forecaster_2_outside_view.md
│   ├── forecaster_2_inside_view.md
│   ├── forecaster_2.json                # {probability: 0.38}
│   │
│   ├── forecaster_3_outside_view.md
│   ├── forecaster_3_inside_view.md
│   ├── forecaster_3.json                # {probability: 0.35}
│   │
│   ├── forecaster_4_outside_view.md
│   ├── forecaster_4_inside_view.md
│   ├── forecaster_4.json                # {probability: 0.45}
│   │
│   ├── forecaster_5_outside_view.md
│   ├── forecaster_5_inside_view.md
│   ├── forecaster_5.json                # {probability: 0.40}
│   │
│   └── aggregation.json                 # {final_probability: 0.40, weights: [...]}
│
├── 06_submission/
│   ├── final_prediction.json            # What was/would be submitted
│   └── api_response.json                # Metaculus API response (if submitted)
│
└── metadata.json                        # {total_cost, timing, config_hash, errors}
```

---

## Data Flow Diagram

```
                    ┌──────────────────┐
                    │  Metaculus API   │
                    │  (Question Data) │
                    └────────┬─────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│   QUESTION                                                                     │
│   ────────                                                                     │
│   • id: 41594                                                                  │
│   • title: "Will X happen by Y date?"                                          │
│   • type: binary | numeric | multiple_choice                                   │
│   • resolution_criteria: "Resolves YES if..."                                  │
│   • fine_print: "Edge cases..."                                                │
│   • background_info: "Context..."                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │  QUERY GENERATION   │
                   │  (LLM: o3/Haiku)    │
                   └──────────┬──────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │ Historical Qs    │            │ Current Qs       │
    │ ──────────────   │            │ ──────────────   │
    │ • Base rate X    │            │ • X latest news  │
    │ • Historical Y   │            │ • Recent X       │
    │ • Statistics Z   │            │ • 2024 X update  │
    └────────┬─────────┘            └────────┬─────────┘
             │                               │
             ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │ SEARCH EXECUTION │            │ SEARCH EXECUTION │
    │ ──────────────── │            │ ──────────────── │
    │ • Google Web     │            │ • Google Web     │
    │ • Google News    │            │ • Google News    │
    │ • Agentic Search │            │ • AskNews        │
    │ • Scrape Articles│            │ • Agentic Search │
    │ • Summarize      │            │ • Scrape Articles│
    └────────┬─────────┘            └────────┬─────────┘
             │                               │
             ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │ historical_      │            │ current_         │
    │ context          │            │ context          │
    │ (~5000 chars)    │            │ (~5000 chars)    │
    └────────┬─────────┘            └────────┬─────────┘
             │                               │
             │    ┌──────────────────────────┼────────────────────────────┐
             │    │                          │                            │
             ▼    ▼                          │                            │
    ┌────────────────────┐                   │                            │
    │  OUTSIDE VIEW      │                   │                            │
    │  (5 Forecasters)   │                   │                            │
    │  ────────────────  │                   │                            │
    │  Input:            │                   │                            │
    │  • Question        │                   │                            │
    │  • historical_ctx  │                   │                            │
    └─────────┬──────────┘                   │                            │
              │                              │                            │
              ▼                              │                            │
    ┌────────────────────┐                   │                            │
    │ 5 Outside View     │                   │                            │
    │ Outputs            │                   │                            │
    │ (reasoning about   │───────────────────┼───────────┐                │
    │  base rates)       │                   │           │                │
    └────────────────────┘                   │           │                │
                                             │           │                │
                                             │           ▼                │
                                             │  ┌─────────────────┐       │
                                             │  │CROSS-POLLINATION│       │
                                             │  │ F1←F1, F2←F4   │       │
                                             │  │ F3←F2, F4←F3   │       │
                                             │  │ F5←F5          │       │
                                             │  └────────┬────────┘       │
                                             │           │                │
                                             ▼           ▼                │
                                    ┌────────────────────────────┐        │
                                    │      INSIDE VIEW           │        │
                                    │      (5 Forecasters)       │        │
                                    │      ────────────────      │        │
                                    │      Input:                │        │
                                    │      • Question            │        │
                                    │      • current_context  ◄──┼────────┘
                                    │      • cross-pollinated    │
                                    │        outside view        │
                                    └─────────────┬──────────────┘
                                                  │
                                                  ▼
                                    ┌────────────────────────────┐
                                    │ 5 Inside View Outputs      │
                                    │ (final predictions)        │
                                    └─────────────┬──────────────┘
                                                  │
                                                  ▼
                                    ┌────────────────────────────┐
                                    │      EXTRACTION            │
                                    │      ──────────            │
                                    │ Parse probabilities from   │
                                    │ natural language output    │
                                    └─────────────┬──────────────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    ▼             ▼             ▼
                               ┌────────┐   ┌────────┐   ┌────────┐
                               │  0.42  │   │  0.38  │   │  0.35  │ ...
                               └────────┘   └────────┘   └────────┘
                                    │             │             │
                                    └─────────────┼─────────────┘
                                                  │
                                                  ▼
                                    ┌────────────────────────────┐
                                    │      AGGREGATION           │
                                    │      ───────────           │
                                    │  Weighted average of all   │
                                    │  valid forecaster outputs  │
                                    │                            │
                                    │  (0.42+0.38+0.35+0.45+0.40)│
                                    │  ────────────────────────  │
                                    │            5               │
                                    │         = 0.40             │
                                    └─────────────┬──────────────┘
                                                  │
                                                  ▼
                                    ┌────────────────────────────┐
                                    │   FINAL PREDICTION: 0.40   │
                                    └─────────────┬──────────────┘
                                                  │
                                                  ▼
                                    ┌────────────────────────────┐
                                    │      SUBMIT TO METACULUS   │
                                    │      (if mode=live)        │
                                    └────────────────────────────┘
```

---

## Mode Comparison

```
┌─────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
│    MODE     │        TEST          │       PREVIEW        │        LIVE          │
├─────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Models      │ Fast tier (Haiku)    │ Quality tier         │ Quality tier         │
│             │                      │ (Sonnet/o3)          │ (Sonnet/o3)          │
├─────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Submits     │ NO                   │ NO                   │ YES                  │
├─────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Cost        │ ~$0.09/forecast      │ ~$0.70/forecast      │ ~$0.70/forecast      │
├─────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Use Case    │ Quick testing        │ Quality testing      │ Production           │
└─────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
```

---

## Ensemble Configuration (Quality Mode)

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                         5-FORECASTER ENSEMBLE                                      │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   │ Forecaster 1│  │ Forecaster 2│  │ Forecaster 3│  │ Forecaster 4│  │ Forecaster 5│
│   ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│   │ Claude      │  │ Claude      │  │ o3-mini     │  │ o3          │  │ o3          │
│   │ Sonnet 4.5  │  │ Sonnet 4.5  │  │ -high       │  │             │  │             │
│   ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│   │ Weight: 1.0 │  │ Weight: 1.0 │  │ Weight: 1.0 │  │ Weight: 1.0 │  │ Weight: 1.0 │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
│                                                                                   │
│   CROSS-POLLINATION (for inside view):                                            │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  F1 receives F1's outside view  (Sonnet ← Sonnet: self-consistency)         │ │
│   │  F2 receives F4's outside view  (Sonnet ← o3: cross-model diversity)        │ │
│   │  F3 receives F2's outside view  (o3-mini ← Sonnet: cross-model diversity)   │ │
│   │  F4 receives F3's outside view  (o3 ← o3-mini: cross-model diversity)       │ │
│   │  F5 receives F5's outside view  (o3 ← o3: self-consistency)                 │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Search Pipeline Detail

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SEARCH PIPELINE                                         │
│                              (src/bot/search.py)                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   INPUT: List of search queries from LLM                                            │
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  PARALLEL SEARCH EXECUTION                                                  │   │
│   │                                                                             │   │
│   │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │   │
│   │  │ Google Web       │  │ Google News      │  │ AskNews API      │          │   │
│   │  │ (Serper API)     │  │ (Serper API)     │  │ (72hr lookback)  │          │   │
│   │  │                  │  │                  │  │                  │          │   │
│   │  │ Max: 10 results  │  │ Max: 10 results  │  │ Max: 10 results  │          │   │
│   │  │ per query        │  │ per query        │  │ per query        │          │   │
│   │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘          │   │
│   │           │                     │                     │                    │   │
│   │           └─────────────────────┼─────────────────────┘                    │   │
│   │                                 │                                          │   │
│   │                                 ▼                                          │   │
│   │                    ┌────────────────────────┐                              │   │
│   │                    │ Deduplicate URLs       │                              │   │
│   │                    └───────────┬────────────┘                              │   │
│   │                                │                                           │   │
│   │                                ▼                                           │   │
│   │                    ┌────────────────────────┐                              │   │
│   │                    │ AGENTIC SEARCH         │                              │   │
│   │                    │ (LLM-guided research)  │                              │   │
│   │                    │                        │                              │   │
│   │                    │ Max 7 iterations:      │                              │   │
│   │                    │ 1. Analyze results     │                              │   │
│   │                    │ 2. Identify gaps       │                              │   │
│   │                    │ 3. Generate new query  │                              │   │
│   │                    │ 4. Search again        │                              │   │
│   │                    │ 5. Repeat until done   │                              │   │
│   │                    │                        │                              │   │
│   │                    │ Output: ~1000 word     │                              │   │
│   │                    │ synthesis              │                              │   │
│   │                    └───────────┬────────────┘                              │   │
│   │                                │                                           │   │
│   └────────────────────────────────┼───────────────────────────────────────────┘   │
│                                    │                                               │
│                                    ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  ARTICLE PROCESSING                                                         │   │
│   │                                                                             │   │
│   │  1. Select top 10 URLs                                                      │   │
│   │  2. Scrape full article content                                             │   │
│   │  3. Truncate to 15,000 chars                                                │   │
│   │  4. Summarize with question context                                         │   │
│   │                                                                             │   │
│   │  ARTICLE_SUMMARY_PROMPT:                                                    │   │
│   │  "Given this question: {title}                                              │   │
│   │   Extract relevant facts, statistics, and expert opinions                   │   │
│   │   from this article: {content}"                                             │   │
│   │                                                                             │   │
│   └───────────────────────────────┬─────────────────────────────────────────────┘   │
│                                   │                                                 │
│                                   ▼                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  OUTPUT: Research Context (~5000 chars)                                     │   │
│   │                                                                             │   │
│   │  # Research Synthesis                                                       │   │
│   │                                                                             │   │
│   │  ## Search Queries                                                          │   │
│   │  1. [Query 1]                                                               │   │
│   │  2. [Query 2]                                                               │   │
│   │                                                                             │   │
│   │  ## AI-Synthesized Research                                                 │   │
│   │  [Agentic search synthesis - ~1000 words]                                   │   │
│   │                                                                             │   │
│   │  ## Google News Results                                                     │   │
│   │  ### [Article Title](URL) (Date)                                            │   │
│   │  > Snippet                                                                  │   │
│   │  **Summary:** [LLM summary]                                                 │   │
│   │                                                                             │   │
│   │  ## Web Search Results                                                      │   │
│   │  [Similar structure]                                                        │   │
│   │                                                                             │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Question Type Handling

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           QUESTION TYPE HANDLERS                                   │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  BINARY (binary.py)                                                         │ │
│   │  ──────────────────                                                         │ │
│   │                                                                             │ │
│   │  Question:  "Will X happen by Y?"                                           │ │
│   │  Prompts:   BINARY_PROMPT_HISTORICAL                                        │ │
│   │             BINARY_PROMPT_CURRENT                                           │ │
│   │             BINARY_OUTSIDE_VIEW_PROMPT                                      │ │
│   │             BINARY_INSIDE_VIEW_PROMPT                                       │ │
│   │                                                                             │ │
│   │  Extraction: extract_binary_probability_percent()                           │ │
│   │              Regex: "Probability: 65%" → 0.65                               │ │
│   │                                                                             │ │
│   │  Output:    Single float (0.001 - 0.999)                                    │ │
│   │  Example:   0.386                                                           │ │
│   │                                                                             │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  NUMERIC (numeric.py)                                                       │ │
│   │  ─────────────────────                                                      │ │
│   │                                                                             │ │
│   │  Question:  "What will the value of X be?"                                  │ │
│   │  Prompts:   NUMERIC_PROMPT_HISTORICAL                                       │ │
│   │             NUMERIC_PROMPT_CURRENT                                          │ │
│   │             NUMERIC_OUTSIDE_VIEW_PROMPT                                     │ │
│   │             NUMERIC_INSIDE_VIEW_PROMPT                                      │ │
│   │                                                                             │ │
│   │  Extraction: extract_percentiles_from_response()                            │ │
│   │              → generate_continuous_cdf()                                    │ │
│   │              Example: {10: 45.2, 50: 78.5, 90: 105.3}                        │ │
│   │                                                                             │ │
│   │  Output:    201-point CDF array                                             │ │
│   │  Example:   [0.001, 0.01, 0.05, ..., 0.95, 0.99, 0.999]                      │ │
│   │                                                                             │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  MULTIPLE CHOICE (multiple_choice.py)                                       │ │
│   │  ────────────────────────────────────                                       │ │
│   │                                                                             │ │
│   │  Question:  "Which of these outcomes will occur?"                           │ │
│   │  Prompts:   MULTIPLE_CHOICE_PROMPT_HISTORICAL                               │ │
│   │             MULTIPLE_CHOICE_PROMPT_CURRENT                                  │ │
│   │             MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT                             │ │
│   │             MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT                              │ │
│   │                                                                             │ │
│   │  Extraction: extract_multiple_choice_probabilities()                        │ │
│   │              + normalize to sum=1.0                                         │ │
│   │              Example: {"Option A": 0.25, "Option B": 0.35, "Option C": 0.40}│ │
│   │                                                                             │ │
│   │  Output:    Dict mapping option IDs to probabilities                        │ │
│   │  Example:   {"opt_1": 0.25, "opt_2": 0.35, "opt_3": 0.40}                    │ │
│   │                                                                             │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              ERROR HANDLING                                        │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   FAIL LOUDLY POLICY: The pipeline raises RuntimeError rather than submitting     │
│   meaningless fallback predictions.                                               │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  BINARY                                                                     │ │
│   │  • If ALL 5 agents fail to extract → RuntimeError                           │ │
│   │  • Does NOT default to 0.5                                                  │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  MULTIPLE CHOICE                                                            │ │
│   │  • If ALL 5 agents fail to extract → RuntimeError                           │ │
│   │  • Does NOT default to uniform distribution                                 │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  NUMERIC                                                                    │ │
│   │  • If fewer than 3 valid CDFs → RuntimeError                                │ │
│   │  • Requires minimum ensemble diversity                                      │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────┐ │
│   │  SEARCH DEGRADATION                                                         │ │
│   │  • Individual search sources can fail gracefully                            │ │
│   │  • If Google fails, AskNews/Agentic continue                                │ │
│   │  • Empty context still allows forecasting (with lower confidence)           │ │
│   └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```
