# Forecast Quality Assessment Template

## Overview

This template produces a narrative analysis of AI forecasting agent performance, focusing on research quality, reasoning soundness, and superforecasting principles. The goal is consistent, comparable assessments across forecast runs.

---

## Prompt Template

Copy and paste this to start a new assessment conversation:

```
Analyze the forecast run for {QUESTION_ID}_{TIMESTAMP}

Read all artifacts in data/{QUESTION_ID}_{TIMESTAMP}/ including:
- question.json, metadata.json, prediction.json
- research/query_historical.md, query_current.md
- research/search_historical.json, search_current.json
- ensemble/agent_*_step1.md (outside view)
- ensemble/agent_*_step2.md (inside view)
- ensemble/aggregation.json

Cross-pollination structure:
- Agent 1 (Sonnet 4.5): receives own Step 1
- Agent 2 (Sonnet 4.5): receives Agent 4's Step 1
- Agent 3 (o3-mini): receives Agent 2's Step 1
- Agent 4 (o3): receives Agent 3's Step 1
- Agent 5 (o3): receives own Step 1

Produce an assessment report following the structure below. Use specific evidence and quotes from the artifacts. Be analytical and critical - identify both strengths and weaknesses.

---

# FORECAST QUALITY ASSESSMENT REPORT

## Summary

Provide a brief overview:
- Question ID and title
- Final prediction (aggregated) and individual agent predictions
- Forecast timeframe
- One-sentence assessment of overall quality

---

## 1. Research Query Analysis: Historical vs. Current

### Query Discreteness

List the actual queries generated for historical and current research. Then assess:

**Historical Queries:**
- List each query

**Current Queries:**
- List each query

**Assessment Table:**

| Aspect | Historical | Current |
|--------|------------|---------|
| Temporal focus | | |
| Content type | | |
| Unique contribution | | |

Evaluate:
- How discrete vs. overlapping are the query sets?
- Did historical queries target base rate establishment?
- Did current queries surface recent decision-relevant events?
- What critical information gaps exist in the queries?

### Do Research Outputs Offer Forecasts?

Assess whether the research outputs remain factual or inappropriately include probability estimates. Research should inform, not forecast.

### Research Quality Summary

- Key information successfully surfaced
- Critical information missed
- Source quality assessment

---

## 2. Agent Reasoning Analysis

For each agent, analyze BOTH Step 1 (outside view) and Step 2 (inside view):

### Agent 1 ({model}): Step 1 X% → Step 2 Y%

**Step 1 (Outside View):**
- Base rate methodology used
- Reference class selection
- Key reasoning points

**Step 2 (Inside View):**
- How did they update from Step 1?
- Key evidence they incorporated
- Adjustment rationale

**Strengths:**
-

**Weaknesses:**
-

**Superforecasting Principles:**
- Base rate anchoring: Strong/Moderate/Weak
- Evidence integration: Strong/Moderate/Weak
- Calibration discipline: Strong/Moderate/Weak

[Repeat for Agents 2-5]

---

## 3. Cross-Pollination Effectiveness

### Cross-Pollination Flow

| Agent | Receives From | Input Probability | Own Step 1 | Final Step 2 | Delta |
|-------|---------------|-------------------|------------|--------------|-------|
| A1 | Self | | | | |
| A2 | A4 | | | | |
| A3 | A2 | | | | |
| A4 | A3 | | | | |
| A5 | Self | | | | |

### Assessment

For each cross-pollinated agent (A2, A3, A4):
- Did they meaningfully engage with the received input?
- Did they over-weight or under-weight the input?
- Did cross-pollination improve diversity of perspectives?

**Pattern Analysis:**
- Did self-pollinated agents (A1, A5) move in different directions than cross-pollinated agents?
- Is there evidence that cross-pollination is improving update discipline?

---

## 4. Factual Accuracy & Comprehension

### Question Understanding

- Did all agents correctly understand the resolution criteria?
- Did they accurately identify the forecast timeframe?
- Did they correctly assess the current status/state of affairs?

### Factual Consensus

List facts that all/most agents correctly identified:
1.
2.
3.

### Factual Errors or Ambiguities

| Agent | Error/Ambiguity | Description | Impact |
|-------|-----------------|-------------|--------|
| | | | High/Medium/Low |

### Hallucinations

Were there any invented facts, dates, events, or sources?

---

## 5. Update Direction Analysis

### Step 1 → Step 2 Movement

| Agent | Step 1 | Step 2 | Delta | New Evidence | Direction Justified? |
|-------|--------|--------|-------|--------------|---------------------|
| A1 | | | | | Yes/No/Partial |
| A2 | | | | | Yes/No/Partial |
| A3 | | | | | Yes/No/Partial |
| A4 | | | | | Yes/No/Partial |
| A5 | | | | | Yes/No/Partial |

### Assessment

- Did agents who received positive news (e.g., repairs completed) appropriately lower their estimates?
- Did agents who received negative news appropriately raise their estimates?
- Were there agents who moved in counterintuitive directions? Explain.

---

## 6. Superforecasting Principles Assessment

| Principle | Overall Assessment | Notes |
|-----------|-------------------|-------|
| Base rate anchoring | Strong/Moderate/Weak | Did agents start from historical frequency? |
| Reference class reasoning | Strong/Moderate/Weak | Was the comparison class appropriate? |
| Inside/outside view integration | Strong/Moderate/Weak | Did Step 2 properly combine both views? |
| Granular estimates | Strong/Moderate/Weak | Avoiding round numbers, false precision? |
| Updating on evidence | Strong/Moderate/Weak | Proportional updates in correct direction? |
| Fermi estimation | Strong/Moderate/Weak | Breaking down into components? |
| Considering alternatives | Strong/Moderate/Weak | Counterfactuals, blind spots identified? |
| Epistemic humility | Strong/Moderate/Weak | Acknowledging uncertainty appropriately? |
| Avoiding cognitive biases | Strong/Moderate/Weak | Anchoring, narrative seduction, recency? |

---

## 7. Agent Rankings

| Rank | Agent | Model | Score Estimate | Key Strength | Key Weakness |
|------|-------|-------|----------------|--------------|--------------|
| 1 | | | /100 | | |
| 2 | | | /100 | | |
| 3 | | | /100 | | |
| 4 | | | /100 | | |
| 5 | | | /100 | | |

---

## 8. Overall Assessment

### Strengths of This Forecast Run
1.
2.
3.

### Weaknesses
1.
2.
3.

### Overall Quality Grade

| Grade | Criteria |
|-------|----------|
| A (90-100) | Excellent research, sound reasoning, appropriate calibration, no major errors |
| B (80-89) | Good overall, minor issues in reasoning or evidence handling |
| C (70-79) | Adequate, notable weaknesses but core reasoning intact |
| D (60-69) | Below standard, significant reasoning or factual issues |
| F (<60) | Poor, major errors, unreliable output |

**This Forecast Grade: [ ]**

---

## 9. Recommendations

### Research Improvements
-

### Prompt/Pipeline Improvements
-

### Agent-Specific Feedback
-

---

## 10. Comparison Flags

Quick reference flags for cross-forecast trend analysis:

| Flag | Value | Notes |
|------|-------|-------|
| Agent spread >30pp | Yes/No | |
| Update direction errors | Yes/No | Which agents? |
| Factual errors present | Yes/No | |
| Hallucinations detected | Yes/No | |
| Cross-pollination effective | Yes/No | |
| Critical info missed in research | Yes/No | What? |
| Base rate calculation errors | Yes/No | |
| Outlier agent (>1.5 SD) | Yes/No | Which? |

---

## Appendix: Raw Data

### Agent Probability Summary
```
Agent 1 ({model}): Step 1: %  →  Step 2: %  (Δ )
Agent 2 ({model}): Step 1: %  →  Step 2: %  (Δ )
Agent 3 ({model}): Step 1: %  →  Step 2: %  (Δ )
Agent 4 ({model}): Step 1: %  →  Step 2: %  (Δ )
Agent 5 ({model}): Step 1: %  →  Step 2: %  (Δ )
Final Aggregated: %
```

### Metadata
- Forecast generated:
- Question closes:
- Question resolves:
- Total cost: $
- Duration: seconds

### Key Dates Mentioned in Research
-

---

## Post-Resolution Analysis (Complete Later)

| Field | Value |
|-------|-------|
| Actual Outcome | |
| Final Prediction | % |
| Brier Score | |

### Retrospective
- Was the forecast well-calibrated given the outcome?
- What did the agents get right?
- What did they miss that was knowable at the time?
- What was genuinely unknowable?

---

_Template version: 2.0_
_Style: Narrative analysis with structured summaries_
```

---

## Tips for Consistent Assessments

1. **Always read the actual artifacts** - don't summarize from memory
2. **Quote specific passages** from agent reasoning to support assessments
3. **Compare agents against each other** - who handled evidence best?
4. **Check the math** - verify base rate calculations are correct
5. **Trace the logic** - does the final probability follow from the stated reasoning?
6. **Look for the critical fact** - was there one piece of information that should have dominated?
7. **Assess update direction** - did new evidence move probabilities the right way?

---

## CSV Export Schema

For trend analysis across forecasts:

```
question_id, timestamp, question_type, forecast_window_days, final_prediction, agent_spread, grade, research_quality, reasoning_quality, cross_poll_effective, update_errors, factual_errors, hallucinations, critical_info_missed, outlier_agent, best_agent, worst_agent, resolution, brier_score
```
