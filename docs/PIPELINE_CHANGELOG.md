# Pipeline Changelog

A timeline of functional changes to the research and forecasting pipeline. Use this to correlate resolved question outcomes with the pipeline configuration that was active when the forecast was made.

**How to use this:** When a question resolves, check its forecast timestamp against the periods below to understand what pipeline version produced that forecast.

---

## Phase 0: Initial Build (Jan 23 - Jan 26, 2026)

### Jan 23-24 — First working pipeline
- `24bc42f` Initial implementation — binary forecasting only
- `49f6278` Add web search and probability extraction
- `a5230fe` **Add numeric and multiple-choice forecasting**
- `7112510` **Add Google News search and article scraping** to research pipeline

### Jan 25 — AskNews + automation
- `e126e8e` **Add AskNews SDK** as a research source
- `d4086e9` Fix forecast extraction bug
- `6c442e2` **Add GitHub Actions** for automated 30-min forecasting
- `278cc5b` Improve error handling for extraction across all question types

### Jan 26 — OpenRouter migration
- `0c2ba4a` **Migrate all LLM calls to OpenRouter**

> **Config Fingerprint — End of Phase 0:**
> - Pipeline: Custom prompts, custom agent roles
> - Research: Google search + AskNews
> - Automation: GH Actions every 30 min
> - Question types: Binary, numeric, multiple choice

---

## Phase 1: Panshul42 Rewrite (Jan 26 - Jan 27, 2026)

Complete pipeline replacement based on Q2 tournament winner's approach.

- `de742b5` **Kill all custom prompts and workflows, adopt Panshul42 pipeline** — Replaced custom agent roles with the 5-agent ensemble: outside view → cross-pollination → inside view → aggregation.
- `0a3555c` Emphasize current date in prompts
- `849c5cd` **Fail loudly when all agents fail** to extract probabilities (no more silent 0.5 fallback)
- `9fd8268` Set all forecasting agents to equal weight (1.0)
- `ddcea97` **Add cross-pollination to numeric handler** (was binary-only before)

> **Config Fingerprint — End of Phase 1:**
> - Pipeline: 5-agent ensemble with cross-pollination (binary + numeric)
> - Models: Equal weight, all agents
> - Research: Google search + AskNews
> - Error handling: Fail loudly on extraction failure

---

## Phase 2: Numeric Fixes & Metadata (Jan 28 - Feb 2, 2026)

### Jan 28 — Date clarity
- `f3ce450` **Clarify current date text** in prompts (forecasters were confused about dates)

### Feb 1 — Numeric improvements + model change
- `3c7d6d2` **Improve numeric question bounds info** for forecasting agents
- `93b7d8b` Use question title for AskNews instead of LLM-generated query
- `4c038e2` **Switch forecaster 3 to GPT-5.2**, deduplicate AskNews by URL, add percentile format rule

### Feb 2 — CDF fixes + full question metadata
- `7eba8f3` **Add AskNews Deep Research** + fix inverted CDF handling
- `15e65ca` Fix CDF validation for closed bounds
- `469a873` **Fix CDF max step from 0.59 to 0.2** — numeric CDFs were violating Metaculus constraints
- `fa3988c` **Feed full question metadata to agents**: background_info, numeric bounds, unit_of_measure

> **Config Fingerprint — End of Phase 2:**
> - Models: Sonnet 4.5 (1,2), GPT-5.2 (3), o3 (4,5)
> - Research: Google + AskNews + AskNews Deep Research
> - Numeric: Full bounds info, fixed CDF generation (max step 0.2)

---

## Phase 3: Research Expansion (Feb 3 - Feb 6, 2026)

### Feb 3 — Google Trends + numeric prompt fix
- `98d68c8` **Remove extreme percentiles from numeric prompt** — agents were giving unrealistic 1st/99th values
- `34254eb` Increase max tokens for Sonnet
- `7ceb6a8` **Add Google Trends** as a research source

### Feb 4 — Agentic search improvements
- `5f5363b` **Pass question description** to forecast pipeline
- `62b98cc` **Pass question context to agentic search** — agentic search was operating without knowing what the question was actually about

### Feb 5 — FRED and yFinance
- `18c8c8b` **Add FRED (Federal Reserve Economic Data)** as a research source
- `84667d1` **Add yFinance** (stock/ETF prices, fundamentals, options)
- `ebf0439` **Route yFinance through agentic search** for self-correcting ticker resolution

### Feb 6 — Extraction fixes + cross-pollination resilience
- `ac3b420` Change floor/ceiling for multiple choice responses
- `4420968` Fix markdown bold percentile extraction (`**25th:** 100` was not being parsed), add FRED to agentic search
- `60050ac` **Fix cross-pollination fallback when outside view fails** — pipeline was crashing when an agent's outside view failed and another agent depended on its output

> **Config Fingerprint — End of Phase 3:**
> - Research: Google + AskNews + AskNews Deep + Google Trends + FRED + yFinance
> - Agentic search: Now has question context, FRED and yFinance access
> - Cross-pollination: Resilient to individual agent failures

---

## Phase 4: Prompt Overhaul (Feb 7, 2026)

Systematic cleanup of all prompt templates.

- `70c8aa0` **Harmonize semantic differences** across binary, numeric, and MC prompts
- `b1f637c` Clean up historical query prompts — remove ambiguity and noise
- `9a843bc` Clean up current query prompts
- `3209ccf` Clean up outside view prompts — fix typos, tighten formatting
- `2786744` **Fix inside view prompts** — found copy-paste error (wrong prompt text in some question types)
- `bb9e261` **Auto-scrape URLs found in question text** (resolution_criteria, fine_print, description)

> **Config Fingerprint — End of Phase 4:**
> - Prompts: All 4 prompt types harmonized across all 3 question types
> - Research: Now auto-scrapes URLs embedded in question text
> - Major quality inflection point — prompts went from Panshul42 originals + ad hoc edits to systematically reviewed and consistent

---

## Phase 5: Temperature Tuning (Feb 8 - Feb 12, 2026)

- `d2a5ccd` **Add configurable LLM temperatures** — previously hardcoded
- `146ecb4` Fix wording differences in binary/numeric inside view checklists
- `d822670` **Add missing `{units}` to numeric current query prompt** — numeric queries weren't mentioning the unit of measurement
- `03de6ef` Adjust agentic search prompts
- `9168dea` Add prompt refinement on question opening date
- `79d87c7` **Raise max_output_tokens to 5000** — agents were getting truncated mid-response

> **Config Fingerprint — End of Phase 5:**
> - Temperature: Configurable per task type (forecasting at 0.5 for diversity)
> - Numeric: Current queries now include units
> - max_output_tokens: 5000 (previously lower, causing truncation)
> - Extractors: Handle space-separated thousands, ≈/=/~ separators

---

## Phase 6: Supervisor Agent (Feb 13 - Feb 14, 2026)

- `b14f1eb` **Add supervisor agent** for ensemble disagreement resolution — based on AIA Forecaster paper (arxiv 2511.07678v1). When forecasters significantly disagree, a supervisor:
  1. Analyzes disagreements between the 5 forecasters
  2. Conducts targeted research to resolve factual disputes
  3. Produces an updated forecast that replaces the weighted average
- `e78466b` **Integrate supervisor into the forecasting pipeline**
- `3420c69` Tune divergence thresholds

> **Config Fingerprint — End of Phase 6:**
> - Pipeline: 5-agent ensemble + optional supervisor for high-disagreement cases
> - Supervisor model: Claude Opus 4.6 (quality) / Haiku (test)
> - Supervisor triggers: binary stddev > 15pp, numeric CoV > 0.25, MC max range > 25pp
> - Models: Sonnet 4.5 (1,2), GPT-5.2 (3), o3 (4,5)
> - Research: Google + AskNews + Google Trends + FRED + yFinance + question URL scraping + agentic search
> - Temperatures: query 0.3, summarization 0.1, agentic 0.3, forecasting 0.5
> - max_output_tokens: 5000

---

## Phase 7: Community Predictions, Model Upgrade & Bug Fixes (Feb 16 - Feb 20, 2026)

- `eda97c0` **Tighten agentic search continuation prompt** — instruct the agent to write a finished report, not a research plan. Added "NO PROCESS NARRATION" directive so agentic search output is directly usable as forecaster context rather than containing meta-commentary about next steps and remaining gaps.
- `1c8f7bd` **Fix critical bug: fine_print silently dropped from all forecasts** — `forecaster.py` used `question.raw.get("fine_print", "")` but fine_print is nested in the API response at `question.raw["question"]["fine_print"]`, so it always resolved to empty string. Every forecast since project inception was made without fine print context. Root cause of the 94.6% vs 30% community divergence on Q42115 (Dutch municipal elections), where fine print contained a definitional exclusion that completely changed the question.
- `10d5de4` **Integrate community prediction scraping into forecasting pipeline** — for meta-questions ("Will the community prediction be above/below X%?")

> **Config Fingerprint — End of Phase 7:**
> - Pipeline: 5-agent ensemble + optional supervisor + community prediction scraping for meta-questions
> - Models: Sonnet 4.6 (1,2), GPT-5.2 (3), o3 (4,5)
> - Supervisor: Fixed normalization (binary /100, MC normalize, date extractor)
> - Research: Google + AskNews + Google Trends + FRED + yFinance + question URL scraping + agentic search + community prediction scraping
> - Fine print: Now correctly fed to all forecasters (was silently empty before)
> - Temperatures: query 0.3, summarization 0.1, agentic 0.3, forecasting 0.5
> - max_output_tokens: 5000

---

## Phase 8: Content & Research Overhaul (Feb 21 - Feb 26, 2026)

- `03760a0` **Replace content truncation with BM25 relevance-based chunk selection** — long articles no longer truncated by position; chunks selected by relevance to the question
- `f6891ea` **Switch agentic search model from o3 to Sonnet 4.6**
- `b5755f8` **Add programmatic stock return distribution** for close-price questions (yFinance historical returns as base-rate anchor)
- `96e0dd9` Add table parsing to content extractor
- `3f2be8c` **Fix supervisor information gaps**: remove truncation, add missing context so supervisor sees full research
- `9b61616` **Add per-URL scraping tracking** to tool_usage.json
- `7b0882d` Add conditional base rates, percentile ranks, and 5-day return to stock return tool
- `e33c577` **Improve AskNews relevance**: semantic search, LLM query for article retrieval
- `4be6935` **Create iterative research planner** to replace legacy 2-step query generation — unified plan-execute pipeline; single LLM call for up to 8 tagged queries (historical/current)
- `76bb5ca` **Add cross-phase URL deduplication** for research (avoid re-scraping same URL in historical vs current phase)

> **Config Fingerprint — End of Phase 8:**
> - Research: Iterative planner default (plan → execute → assemble), max 8 plan queries, URL dedup across phases
> - Content: BM25 chunk selection, table parsing in extractor
> - Stock: Programmatic return distribution for close-price questions
> - Agentic: Sonnet 4.6 (quality); per-URL scraping in tool_usage
> - Supervisor: Full context (no truncation)

---

## Phase 9: Three Outside-View, Content Parsing (Feb 27 - Mar 7, 2026)

- `39a2cf9` **Use three-outside-view cross-pollination** — only forecasters 1, 3, and 5 run the outside-view LLM call; forecasters 2 and 4 reuse outputs from 5 and 3 respectively (saves 2 LLM calls, keeps model diversity)
- `49b4703` **Pass pre-research (seed_context) to supervisor** as primary-source input
- `609330b` Stop forecasting community-prediction meta-questions in automated runs
- `2dda6f0` Add Google Trends pre-research to seed context for trends-related questions
- `1ea0c2e` Add CSV, Excel, and Google Sheets parsing to content extractor
- `d128ef8` Add PDF and JSON parsing to content extractor
- `ffa19f1` Disable agentic search (config: agentic_search_enabled: false)
- `3149c31` Add new models: GPT-5.4 and Gemini 3.1 Pro Preview** — forecaster 3 → GPT-5.4; quality article summarizer → Gemini 3 flash preview
- `f555308` Expand FRED data retrieval (broader use in research)

> **Config Fingerprint — End of Phase 9 (current):**
> - Pipeline: 5-agent ensemble, 3 outside-view (1,3,5), optional supervisor, typed steps
> - Models: Sonnet 4.6 (1,2), **GPT-5.4** (3), o3 (4,5); quality summarizer Gemini 3 flash / Sonnet
> - Research: Iterative planner (max 8 queries), Google + AskNews + Trends + FRED + yFinance + question URL scraping; **agentic search disabled**; FRED pre-fetch and expanded retrieval; URL cache shared; blocked domains centralized; uniform URL tracking
> - Content: CSV, Excel, Google Sheets, PDF, JSON parsing in extractor; BM25 chunk selection
> - Stock: Programmatic return + fundamentals for close-price questions
> - Automation: Meta-questions skipped in run_bot
> - Temperatures: query 0.3, summarization 0.1, agentic 0.3, forecasting 0.5
> - max_output_tokens: 5000

---

## Quick Reference: Model History

| Date | Change | Commit |
|------|--------|--------|
| Jan 26 | Migrate to OpenRouter | `0c2ba4a` |
| Jan 27 | Panshul42 ensemble (5 equal-weight agents) | `9fd8268` |
| Feb 1 | GPT-5.2 for forecaster 3 | `4c038e2` |
| Feb 8 | Temperature settings added to config | `d2a5ccd` |
| Feb 13 | Supervisor agent uses Opus 4.6 | `b14f1eb` |
| Feb 19 | Sonnet 4.5 → 4.6 for forecasters 1-2 + article summarizer | `6973c36` |
| Feb 21 | Agentic search: o3 → Sonnet 4.6 | `f6891ea` |
| Mar 5 | Forecaster 3: GPT-5.2 → GPT-5.4; quality summarizer Gemini 3 flash | `3149c31` |

## Quick Reference: Research Source History

| Date | Source Added | Commit |
|------|-------------|--------|
| Jan 24 | Google search + article scraping | `7112510` |
| Jan 25 | AskNews SDK | `e126e8e` |
| Feb 2 | AskNews Deep Research | `7eba8f3` |
| Feb 3 | Google Trends | `7ceb6a8` |
| Feb 4 | Question context passed to agentic search | `62b98cc` |
| Feb 5 | FRED (Federal Reserve Economic Data) | `18c8c8b` |
| Feb 5 | yFinance (stocks, ETFs, options) | `84667d1` |
| Feb 7 | Auto-scrape question URLs | `bb9e261` |
| Feb 19 | Community prediction scraping (Playwright + Xvfb) | `10d5de4` |
| Feb 26 | Iterative research planner (plan-execute, URL dedup) | `4be6935` |
| Mar 4 | Google Trends pre-research for trends questions | `2dda6f0` |
| Mar 5 | CSV, Excel, Google Sheets, PDF, JSON in content extractor | `1ea0c2e`, `d128ef8` |
| Mar 7 | FRED pre-fetch before planner, expanded FRED retrieval | `e027b10`, `f555308` |

## Quick Reference: Key Bug Fixes

| Date | Fix | Impact | Commit |
|------|-----|--------|--------|
| Jan 27 | Fail loudly on extraction failure | No more silent 0.5 fallback | `849c5cd` |
| Feb 2 | CDF max step 0.59 → 0.2 | Numeric CDFs violating Metaculus constraints | `469a873` |
| Feb 2 | Fix inverted CDF handling | Some numeric CDFs were backwards | `7eba8f3` |
| Feb 3 | Remove extreme percentiles from numeric prompt | Unrealistic 1st/99th percentile values | `98d68c8` |
| Feb 6 | Cross-pollination fallback | Pipeline crash when outside view failed | `60050ac` |
| Feb 6 | Bold markdown percentile extraction | `**25th:** 100` not parsed | `4420968` |
| Feb 7 | Inside view copy-paste error | Wrong prompt text in some question types | `2786744` |
| Feb 12 | Space-separated thousands extraction | "10 000" not parsed as 10000 | `79f1519` |
| Feb 12 | Raise max_output_tokens to 5000 | Agents truncated mid-response | `79d87c7` |
| Feb 17 | Supervisor prediction normalization | Binary always 99.9%, MC always uniform, date wrong extractor | `1b480a9` |
| Feb 19 | fine_print silently dropped | All forecasts made without fine print since inception | `1c8f7bd` |
| Feb 21 | BM25 budget overflow | Crash on pages with few paragraph breaks | `5744e04` |
| Feb 21 | Stock return timezone | Wrong dates for distribution | `f68392d` |

---

## Mapping Forecasts to Pipeline Versions

To determine what pipeline produced a given forecast:

1. Find the forecast's timestamp in `data/{question_id}_{timestamp}/metadata.json`
2. Match against the phase boundaries:
   - **Before Jan 27**: Phase 0 — custom pipeline, pre-Panshul42
   - **Jan 27 - Jan 28**: Phase 1 — Panshul42 ensemble, basic research
   - **Jan 28 - Feb 3**: Phase 2 — GPT-5.2 added, CDF fixes, full metadata
   - **Feb 3 - Feb 7**: Phase 3 — Google Trends, FRED, yFinance added
   - **Feb 7**: Phase 4 — all prompts harmonized, question URL scraping
   - **Feb 8 - Feb 12**: Phase 5 — temperature config, numeric units, max tokens 5000, extractor fixes
   - **Feb 13 - Feb 15**: Phase 6 — supervisor agent available
   - **Feb 16 - Feb 20**: Phase 7 — fine print fix, Sonnet 4.6, community prediction scraping
   - **Feb 21 - Feb 26**: Phase 8 — iterative planner, BM25 content, stock return, supervisor full context
   - **Feb 27+**: Phase 9 — three outside-view, content parsing (CSV/Excel/PDF/JSON), agentic disabled
3. Check `metadata.json` for `config_hash` to confirm exact config
