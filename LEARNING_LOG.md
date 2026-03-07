# Learning Log — Metaculus Bot

Weekly Build-Measure-Learn sessions. One entry per week. Experiments are logged as hypotheses with pass/fail criteria before running, and results are filled in during reflection.

---

## 2026-03-02

### Context
Research pipeline quality is the primary concern. The bot is flying blind on many questions because of weak retrieval — JS-rendered data, wrong tool routing, redundant queries. Three experiments this week target different layers of the research pipeline.

### Upstream assumption
If the research planner's LLM output is fundamentally inconsistent (format, quality, tool selection), all three experiments are measuring noise on top of a broken foundation — and the real fix is prompt stability, not any of the incremental changes below.

---

### Experiment 1: FRED pre-research reduces redundant queries

**Hypothesis:** Pre-fetching the FRED series identified in question text before the planner runs will cause the planner to skip redundant FRED lookups and allocate its query budget to other dimensions.

**Minimum test:** Run 3 open questions that explicitly reference a FRED series. Check `research_plan.json` artifacts.

**Pass:** `fred_pre_research: true` fires in the artifact, planner generates 0 FRED queries (it already has the data), and remaining query budget goes to drivers/current state. Pre-fetched data shows up in forecaster reasoning.

**Fail:** Planner generates FRED queries anyway. Or pre-fetched data doesn't appear in forecaster reasoning.

**Time estimate:** 1–2 hours.

**Result:**
<!-- Fill in during reflection -->

**Updated belief:**
<!-- Fill in during reflection -->

**Verdict:** <!-- carry / pivot / abandon -->

---

### Experiment 2: Two-shot reflection improves query diversity

**Hypothesis:** Enabling the reflection phase with a reduced initial query cap (4 queries) will produce gap-fill queries that target genuinely different angles, rather than running 8 mediocre queries in one shot.

**Minimum test:** Enable `reflection_enabled: true`, set initial cap to 4, run 3–5 questions, read `query_plan.json` artifacts.

**Pass:** Gap-fill queries address a demonstrably different dimension than the initial 4 (e.g., initial covered base rate + drivers; gap-fill covers current state + contrarian). Forecaster reasoning visibly references gap-fill content.

**Fail:** Gap queries are reformulations of initial queries. Or total research cost rises >30% with no qualitative improvement in reasoning depth.

**Time estimate:** 3–4 hours.

**Result:**
<!-- Fill in during reflection -->

**Updated belief:**
<!-- Fill in during reflection -->

**Verdict:** <!-- carry / pivot / abandon -->

---

### Experiment 3: Domain-specific pipeline for stock price questions

**Hypothesis:** A question classifier routing short-window stock price questions to a leaner pipeline (yFinance + momentum/options focus, fewer base-rate LLM calls) will produce better-targeted outside views at lower cost than the default pipeline.

**Minimum test:** Build a classifier, apply to 5 stock price questions, run both default and specialized pipelines, compare artifacts side-by-side.

**Pass:** Classifier routes correctly. Outside view for a ≤2-week stock question focuses on price momentum/options/analyst targets rather than 3 independent base-rate analyses. Cost is measurably lower.

**Fail:** Can't build a reliable classifier. Or specialized pipeline produces demonstrably weaker reasoning quality than default.

**Time estimate:** 1–2 days. May not ship this week — this is a learning exercise first.

**Result:**
<!-- Fill in during reflection -->

**Updated belief:**
<!-- Fill in during reflection -->

**Verdict:** <!-- carry / pivot / abandon -->
