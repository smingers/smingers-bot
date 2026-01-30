# Forecast Quality Assessment Template

## Overview

This template provides a standardized framework for evaluating AI forecasting agent performance. Use it to assess individual forecast runs and enable cross-forecast comparison to identify trends.

---

## Usage Instructions

Start a new conversation with:

```
Analyze the forecast run for {QUESTION_ID}_{TIMESTAMP} using the Forecast Quality Assessment template located at docs/forecast_quality_assessment_template.md

Path: data/{QUESTION_ID}_{TIMESTAMP}/

Cross-pollination structure for this run:
- Agent 1 receives: Self
- Agent 2 receives: Agent 4's Step 1
- Agent 3 receives: Agent 2's Step 1
- Agent 4 receives: Agent 3's Step 1
- Agent 5 receives: Self

Please complete all sections of the assessment template with specific evidence from the artifacts.
```

---

## Scoring Guide

Score each criterion 0-2:
- **0** = Missing, incorrect, or poor
- **1** = Present but partial or inconsistent
- **2** = Fully demonstrated, high quality

---

# ASSESSMENT REPORT

## Metadata

| Field | Value |
|-------|-------|
| Question ID | |
| Question Title | |
| Question Type | binary / numeric / multiple_choice |
| Forecast Date | |
| Resolution Date | |
| Forecast Window | X days |
| Final Prediction | |
| Agent Predictions | A1: %, A2: %, A3: %, A4: %, A5: % |
| Spread (Max - Min) | |
| Total Cost | $ |
| Duration | seconds |

---

## Section 1: Research Quality

### 1.1 Query Generation

| Criterion | Score (0-2) | Evidence/Notes |
|-----------|-------------|----------------|
| Historical queries target base rates | | |
| Current queries target recent developments | | |
| Queries are discrete (minimal overlap) | | |
| Queries cover key aspects of question | | |
| No hallucinated search terms | | |
| **Subtotal** | /10 | |

### 1.2 Research Output Quality

| Criterion | Score (0-2) | Evidence/Notes |
|-----------|-------------|----------------|
| Surfaced decision-relevant information | | |
| Identified critical recent events | | |
| Sources are credible/authoritative | | |
| Research is factual (no forecasts embedded) | | |
| Gaps/limitations acknowledged | | |
| **Subtotal** | /10 | |

**Research Quality Score: /20**

### Key Information Surfaced
1.
2.
3.

### Critical Information Missed (if any)
-

---

## Section 2: Base Rate Reasoning

| Criterion | A1 | A2 | A3 | A4 | A5 | Notes |
|-----------|----|----|----|----|----| ------|
| Anchors on historical frequency | | | | | | |
| Reference class is appropriate | | | | | | |
| Calculation is mathematically correct | | | | | | |
| Time period properly defined | | | | | | |
| Acknowledges base rate uncertainty | | | | | | |
| **Agent Subtotals** | /10 | /10 | /10 | /10 | /10 | |

**Base Rate Reasoning Score: /50**

### Base Rates Used

| Agent | Base Rate | Calculation Method | Reference Period |
|-------|-----------|-------------------|------------------|
| A1 | | | |
| A2 | | | |
| A3 | | | |
| A4 | | | |
| A5 | | | |

### Base Rate Consistency Assessment
- **Agreement level:** High / Medium / Low
- **Divergence explanation:**

---

## Section 3: Evidence Handling

| Criterion | A1 | A2 | A3 | A4 | A5 | Notes |
|-----------|----|----|----|----|----| ------|
| Assesses source quality/reliability | | | | | | |
| Triangulates across multiple sources | | | | | | |
| Distinguishes fact from opinion | | | | | | |
| Identifies most decision-relevant facts | | | | | | |
| Notes conflicting information | | | | | | |
| Resolves factual ambiguities | | | | | | |
| **Agent Subtotals** | /12 | /12 | /12 | /12 | /12 | |

**Evidence Handling Score: /60**

### Key Factual Consensus Across Agents
1.
2.
3.

### Factual Disagreements/Ambiguities
-

---

## Section 4: Reasoning Quality

| Criterion | A1 | A2 | A3 | A4 | A5 | Notes |
|-----------|----|----|----|----|----| ------|
| Inside/outside view properly integrated | | | | | | |
| Update direction matches evidence | | | | | | |
| Update magnitude is proportional | | | | | | |
| Causal mechanisms identified | | | | | | |
| Counterfactuals considered | | | | | | |
| Avoids anchoring on salient details | | | | | | |
| Resists narrative seduction | | | | | | |
| **Agent Subtotals** | /14 | /14 | /14 | /14 | /14 | |

**Reasoning Quality Score: /70**

### Step 1 → Step 2 Movement

| Agent | Step 1 | Step 2 | Delta | Direction Justified? |
|-------|--------|--------|-------|---------------------|
| A1 | | | | Yes / No / Partial |
| A2 | | | | Yes / No / Partial |
| A3 | | | | Yes / No / Partial |
| A4 | | | | Yes / No / Partial |
| A5 | | | | Yes / No / Partial |

### Reasoning Errors Observed
-

---

## Section 5: Cross-Pollination Effectiveness

### Cross-Pollination Structure

| Agent | Receives From | Input Probability | Own Step 1 | Output Step 2 |
|-------|---------------|-------------------|------------|---------------|
| A1 | Self | | | |
| A2 | A4 | | | |
| A3 | A2 | | | |
| A4 | A3 | | | |
| A5 | Self | | | |

### Cross-Pollination Scoring

| Criterion | A2 | A3 | A4 | Notes |
|-----------|----|----|----| ------|
| Engages with received input | | | | |
| Appropriate weight given to input | | | | |
| Maintains independent judgment | | | | |
| Identifies areas of agreement/disagreement | | | | |
| **Agent Subtotals** | /8 | /8 | /8 | |

**Cross-Pollination Score: /24**

### Cross-Pollination Assessment
- **Diversity introduced:** High / Medium / Low
- **Over-reliance on input observed:** Yes / No
- **Under-utilization of input observed:** Yes / No

---

## Section 6: Question Comprehension

| Criterion | A1 | A2 | A3 | A4 | A5 | Notes |
|-----------|----|----|----|----|----| ------|
| Resolution criteria correctly understood | | | | | | |
| Timeline/dates accurate | | | | | | |
| Current status correctly identified | | | | | | |
| No hallucinated facts | | | | | | |
| Key terms properly interpreted | | | | | | |
| **Agent Subtotals** | /10 | /10 | /10 | /10 | /10 | |

**Question Comprehension Score: /50**

### Comprehension Errors
-

---

## Section 7: Calibration & Consistency

| Criterion | A1 | A2 | A3 | A4 | A5 | Notes |
|-----------|----|----|----|----|----| ------|
| Explicit calibration check performed | | | | | | |
| Reasoning supports final probability | | | | | | |
| Avoids false precision | | | | | | |
| Sensitivity analysis conducted | | | | | | |
| Blind spots identified | | | | | | |
| Status quo bias addressed | | | | | | |
| **Agent Subtotals** | /12 | /12 | /12 | /12 | /12 | |

**Calibration Score: /60**

### Probability Distribution Analysis
- **Mean:** %
- **Median:** %
- **Std Dev:**
- **Range:** % to %
- **Outliers (>1.5 SD from mean):**

---

## Section 8: Process Quality

| Criterion | A1 | A2 | A3 | A4 | A5 | Notes |
|-----------|----|----|----|----|----| ------|
| Follows structured methodology | | | | | | |
| Shows work transparently | | | | | | |
| Adjustments are explicit and traceable | | | | | | |
| Appropriate epistemic humility | | | | | | |
| **Agent Subtotals** | /8 | /8 | /8 | /8 | /8 | |

**Process Quality Score: /40**

---

## Summary Scores

| Section | Max Score | Actual Score | Percentage |
|---------|-----------|--------------|------------|
| 1. Research Quality | 20 | | % |
| 2. Base Rate Reasoning | 50 | | % |
| 3. Evidence Handling | 60 | | % |
| 4. Reasoning Quality | 70 | | % |
| 5. Cross-Pollination | 24 | | % |
| 6. Question Comprehension | 50 | | % |
| 7. Calibration & Consistency | 60 | | % |
| 8. Process Quality | 40 | | % |
| **TOTAL** | **374** | | **%** |

### Overall Quality Grade

| Grade | Score Range | Assessment |
|-------|-------------|------------|
| A | 90-100% | Excellent - production ready |
| B | 80-89% | Good - minor improvements needed |
| C | 70-79% | Adequate - notable weaknesses |
| D | 60-69% | Below standard - significant issues |
| F | <60% | Poor - major problems |

**This Forecast Grade: [ ]**

---

## Agent Rankings

| Rank | Agent | Model | Total Score | Key Strength | Key Weakness |
|------|-------|-------|-------------|--------------|--------------|
| 1 | | | /74 | | |
| 2 | | | /74 | | |
| 3 | | | /74 | | |
| 4 | | | /74 | | |
| 5 | | | /74 | | |

---

## Key Findings

### Strengths
1.
2.
3.

### Weaknesses
1.
2.
3.

### Factual/Logical Errors

| Agent | Error Type | Description | Impact |
|-------|------------|-------------|--------|
| | Factual / Logical / Calculation | | High / Medium / Low |

### Superforecasting Principles Adherence

| Principle | Observed | Notes |
|-----------|----------|-------|
| Base rate anchoring | Strong / Moderate / Weak | |
| Inside/outside view integration | Strong / Moderate / Weak | |
| Granular probability estimates | Strong / Moderate / Weak | |
| Updating on new evidence | Strong / Moderate / Weak | |
| Awareness of cognitive biases | Strong / Moderate / Weak | |
| Epistemic humility | Strong / Moderate / Weak | |

---

## Recommendations

### Immediate (This Question Type)
1.
2.

### Systemic (Pipeline Improvements)
1.
2.

### Research Improvements
1.

### Prompt Improvements
1.

---

## Comparison Flags

Use these flags to enable cross-forecast comparison:

| Flag | Value | Notes |
|------|-------|-------|
| High agent disagreement (spread >30pp) | Yes / No | |
| Update direction errors observed | Yes / No | |
| Factual errors present | Yes / No | |
| Cross-pollination effective | Yes / No | |
| Base rate calculation errors | Yes / No | |
| Critical information missed | Yes / No | |
| Hallucinations detected | Yes / No | |
| Outlier agent present | Yes / No | Agent: |

---

## Raw Data Appendix

### Agent Probability Summary

```
Agent 1 ({model}): Step 1: %, Step 2: %, Delta:
Agent 2 ({model}): Step 1: %, Step 2: %, Delta:
Agent 3 ({model}): Step 1: %, Step 2: %, Delta:
Agent 4 ({model}): Step 1: %, Step 2: %, Delta:
Agent 5 ({model}): Step 1: %, Step 2: %, Delta:
Final Aggregated: %
```

### Key Dates
- Forecast generated:
- Question closes:
- Question resolves:
- Key event dates mentioned:

---

## Post-Resolution Analysis (Complete After Resolution)

| Field | Value |
|-------|-------|
| Actual Outcome | Yes / No / Value |
| Prediction | % |
| Brier Score | |
| Calibration Error | |

### Retrospective Assessment
- Was the probability well-calibrated?
- What did agents get right?
- What did agents miss?
- Would different research have helped?

---

## Trend Analysis CSV Schema

For aggregating across multiple forecasts, export to CSV with these columns:

```
question_id, timestamp, question_type, forecast_window_days, final_prediction, agent_spread, total_score, research_score, base_rate_score, reasoning_score, cross_poll_score, comprehension_score, calibration_score, process_score, grade, high_disagreement, update_errors, factual_errors, cross_poll_effective, outlier_agent, resolution, brier_score
```

---

_Template version: 1.0_
_Last updated: 2026-01-30_
