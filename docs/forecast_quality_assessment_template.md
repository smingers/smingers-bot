# Forecast Quality Assessment Template

## Instructions for Agent

When asked to analyze a forecast run using this template:

1. Read all artifacts in the specified `data/{QUESTION_ID}_{TIMESTAMP}/` folder:
   - `question.json`, `metadata.json`, `prediction.json`
   - `research/query_historical.md`, `query_current.md`
   - `research/search_historical.json`, `search_current.json`
   - Forecaster reasoning files (see naming conventions below)
   - `ensemble/aggregation.json`

   **Artifact naming conventions** (changed Feb 2, 2026):

   | Era | Forecaster files | Prompt file |
   |-----|------------------|-------------|
   | Current (Feb 2+) | `ensemble/forecaster_{i}_outside_view.md`, `forecaster_{i}_inside_view.md`, `forecaster_{i}.json` | `ensemble/outside_view_prompt.md` |
   | Legacy (pre-Feb 2) | `ensemble/agent_{i}_step1.md`, `agent_{i}_step2.md`, `agent_{i}.json` | `ensemble/step1_prompt.md` |

   The terminology mapping:
   - `step1` / `outside_view` = Historical context analysis, base rate derivation
   - `step2` / `inside_view` = Current news integration, final calibration

2. Cross-pollination structure for this pipeline:
   - Step 2 instance 1 (Sonnet 4.5): receives Step 1 output 1
   - Step 2 instance 2 (Sonnet 4.5): receives Step 1 output 4
   - Step 2 instance 3 (o3-mini): receives Step 1 output 2
   - Step 2 instance 4 (o3): receives Step 1 output 3
   - Step 2 instance 5 (o3): receives Step 1 output 5

3. Identify the question type (binary, numeric, or multiple choice) and use the appropriate prompts for that type throughout.

4. Complete all sections below with specific evidence and quotes from the artifacts. Be analytical and critical.

5. Save the completed assessment to: `docs/assessments/{QUESTION_ID}_{TIMESTAMP}_assessment.md`

---

# FORECAST QUALITY ASSESSMENT REPORT

## Critical Issues Summary

**Complete this section FIRST after reading all artifacts. List the most significant problems that affected forecast quality.**

**Note:** Methodological diversity and forecast spread are NOT inherently issues. Only flag instances where reasoning is flawed, evidence is misinterpreted, or analytical tools are misapplied to the specific question.

| Issue | Severity | Location | Description |
|-------|----------|----------|-------------|
| | Critical/High/Med/Low | Research / S1-X / S2-X / Aggregation | |
| | Critical/High/Med/Low | Research / S1-X / S2-X / Aggregation | |
| | Critical/High/Med/Low | Research / S1-X / S2-X / Aggregation | |

**Severity definitions:**
- **Critical**: Fundamentally compromises the forecast (e.g., misunderstood resolution criteria, hallucinated key facts, calculation errors that propagate)
- **High**: Significantly affects forecast quality (e.g., missed critical recent information, wrong update direction, major logical flaw)
- **Medium**: Notable weakness but core forecast intact (e.g., incomplete source analysis, suboptimal reference class, over/under-weighted evidence)
- **Low**: Minor issue (e.g., formatting, slight imprecision, redundant analysis)

---

## Summary

- **Question ID:**
- **Question Title:**
- **Question Type:** binary / numeric / multiple_choice
- **Forecast Date:**
- **Resolution Date:**
- **Forecast Window:** X days
- **Final Prediction:**
- **Step 2 Predictions:** S2-1: , S2-2: , S2-3: , S2-4: , S2-5:
- **Spread:**
- **Total Cost:** $
- **Duration:** seconds
- **One-sentence quality assessment:**

---

## 1. Research Query Analysis: Historical vs. Current

### Query Discreteness

**Historical Queries:**
- [List actual queries from query_historical.md]

**Current Queries:**
- [List actual queries from query_current.md]

**Assessment Table:**

| Aspect | Historical | Current |
|--------|------------|---------|
| Temporal focus | | |
| Content type | | |
| Unique contribution | | |

**Analysis:**
- How discrete vs. overlapping are the query sets?
- Did historical queries target base rate establishment?
- Did current queries surface recent decision-relevant events?
- What critical information gaps exist?

### Do Research Outputs Offer Forecasts?

[Assess whether research outputs remain factual or inappropriately include probability estimates. Research should inform, not forecast.]

### Research Quality Summary

- **Key information successfully surfaced:**
- **Critical information missed:**
- **Source quality:**

---

## 2. Step 1 (Outside View) Analysis

The outside view prompt asks each instance to:
- (a) Analyze sources, evaluate quality, distinguish fact from opinion
- (b) Identify reference classes, evaluate suitability, choose best one
- (c) State prediction timeframe, examine historical patterns
- (d) Justify the outside view prediction

### Scoring Rubric - Step 1 (Outside View)

| Dimension | 4 pts | 3 pts | 2 pts | 1 pt |
|-----------|-------|-------|-------|------|
| **Source Analysis** | Evaluates each source's quality, distinguishes fact from opinion, identifies expert sources | Good but incomplete coverage | Superficial or misses key sources | Missing or uncritical |
| **Reference Class Selection** | Identifies multiple classes, evaluates fit, chooses appropriate one with justification | Reasonable class but weak justification | Questionable class or no alternatives considered | Missing or inappropriate |
| **Timeframe Analysis** | Correctly states window, examines historical patterns over similar periods | Mostly correct, minor gaps | Significant gaps or errors | Missing or wrong |
| **Base Rate Derivation** | Clear calculation from reference class, mathematically sound, acknowledges uncertainty | Minor issues but reasonable | Significant errors or unjustified | Missing or nonsensical |

### Step 1 Output Assessments

#### Step 1 Output 1 (Sonnet 4.5)

- **Source Analysis:**
- **Reference Class Selection:**
- **Timeframe Analysis:**
- **Base Rate Derivation:**

**Question-type-specific assessment:**

*For binary questions:*
- What probability did they derive and how?
- Did they consider both Yes and No pathways?

*For numeric questions:*
- What central estimate and range did they derive?
- Is the distribution shape appropriate (symmetric/skewed, fat/thin tails)?
- Did they anchor on specific data points?

*For multiple choice questions:*
- Did they assign probabilities to all options?
- Did they consider correlations between options?
- Do probabilities sum to 100%?

- **Score:** /16

---

#### Step 1 Output 2 (Sonnet 4.5)

- **Source Analysis:**
- **Reference Class Selection:**
- **Timeframe Analysis:**
- **Base Rate Derivation:**

**Question-type-specific assessment:**

- **Score:** /16

---

#### Step 1 Output 3 (o3-mini)

- **Source Analysis:**
- **Reference Class Selection:**
- **Timeframe Analysis:**
- **Base Rate Derivation:**

**Question-type-specific assessment:**

- **Score:** /16

---

#### Step 1 Output 4 (o3)

- **Source Analysis:**
- **Reference Class Selection:**
- **Timeframe Analysis:**
- **Base Rate Derivation:**

**Question-type-specific assessment:**

- **Score:** /16

---

#### Step 1 Output 5 (o3)

- **Source Analysis:**
- **Reference Class Selection:**
- **Timeframe Analysis:**
- **Base Rate Derivation:**

**Question-type-specific assessment:**

- **Score:** /16

---

### Step 1 Summary

| Output | Model | Prediction | Score | Key Strength | Key Weakness |
|--------|-------|------------|-------|--------------|--------------|
| S1-1 | Sonnet 4.5 | | /16 | | |
| S1-2 | Sonnet 4.5 | | /16 | | |
| S1-3 | o3-mini | | /16 | | |
| S1-4 | o3 | | /16 | | |
| S1-5 | o3 | | /16 | | |

---

## 3. Step 2 (Inside View) Analysis

The inside view prompt asks each instance to:
- (a) Analyze current sources, evaluate quality, distinguish fact from opinion
- (b) Weight evidence using Strong/Moderate/Weak framework
- (c) State timeframe, describe how prediction changes if halved/doubled
- (d) Justify shift from outside view base rate

Plus complete the calibration checklist: paraphrase, base rate stated, consistency check, top evidence, blind spot, status quo.

### Scoring Rubric - Step 2 (Inside View)

| Dimension | 4 pts | 3 pts | 2 pts | 1 pt |
|-----------|-------|-------|-------|------|
| **Evidence Weighting** | Correctly applies Strong/Moderate/Weak framework, identifies key facts | Uses framework but imperfectly | Superficial weighting | Ignores or misapplies |
| **Update from Base Rate** | Direction and magnitude justified, explains shift from outside view | Direction correct, magnitude questionable | Questionable direction | Contradicts evidence |
| **Timeframe Sensitivity** | Addresses how prediction changes if window halved/doubled | Mentions but incomplete analysis | Superficial treatment | Missing |
| **Calibration Checklist** | Completes all elements meaningfully | Most elements present | Partial completion | Missing or perfunctory |

### Cross-Pollination Flow

| Step 2 Instance | Model | Receives Step 1 From | Step 1 Input |
|-----------------|-------|---------------------|--------------|
| S2-1 | Sonnet 4.5 | S1-1 (self-model) | |
| S2-2 | Sonnet 4.5 | S1-4 (o3) | |
| S2-3 | o3-mini | S1-2 (Sonnet 4.5) | |
| S2-4 | o3 | S1-3 (o3-mini) | |
| S2-5 | o3 | S1-5 (self-model) | |

### Step 2 Output Assessments

#### Step 2 Output 1 (Sonnet 4.5): receives S1-1

- **Evidence Weighting:**
- **Update from Base Rate:** (Input: → Output: , Δ = )
- **Timeframe Sensitivity:**
- **Calibration Checklist:**

**Question-type-specific assessment:**

*For binary questions:*
- Did the update direction match the evidence direction?
- Is the final probability internally consistent with the stated reasoning?

*For numeric questions:*
- Did both the central estimate AND uncertainty range update appropriately?
- Are the tails calibrated (1st/99th percentiles reasonable)?
- Is the CDF monotonic and smooth?

*For multiple choice questions:*
- Did updates preserve probability sum = 100%?
- Were relative probabilities between options adjusted sensibly?
- Did they identify which options were most affected by new evidence?

- **Score:** /16

---

#### Step 2 Output 2 (Sonnet 4.5): receives S1-4

- **Evidence Weighting:**
- **Update from Base Rate:** (Input: → Output: , Δ = )
- **Timeframe Sensitivity:**
- **Calibration Checklist:**

**Question-type-specific assessment:**

- **Score:** /16

---

#### Step 2 Output 3 (o3-mini): receives S1-2

- **Evidence Weighting:**
- **Update from Base Rate:** (Input: → Output: , Δ = )
- **Timeframe Sensitivity:**
- **Calibration Checklist:**

**Question-type-specific assessment:**

- **Score:** /16

---

#### Step 2 Output 4 (o3): receives S1-3

- **Evidence Weighting:**
- **Update from Base Rate:** (Input: → Output: , Δ = )
- **Timeframe Sensitivity:**
- **Calibration Checklist:**

**Question-type-specific assessment:**

- **Score:** /16

---

#### Step 2 Output 5 (o3): receives S1-5

- **Evidence Weighting:**
- **Update from Base Rate:** (Input: → Output: , Δ = )
- **Timeframe Sensitivity:**
- **Calibration Checklist:**

**Question-type-specific assessment:**

- **Score:** /16

---

### Step 2 Summary

| Output | Model | S1 Input | Final | Delta | Score | Update Justified? |
|--------|-------|----------|-------|-------|-------|-------------------|
| S2-1 | Sonnet 4.5 | | | | /16 | Yes/No/Partial |
| S2-2 | Sonnet 4.5 | | | | /16 | Yes/No/Partial |
| S2-3 | o3-mini | | | | /16 | Yes/No/Partial |
| S2-4 | o3 | | | | /16 | Yes/No/Partial |
| S2-5 | o3 | | | | /16 | Yes/No/Partial |

---

## 4. Cross-Pollination Effectiveness

### Assessment

- Did cross-model instances (S2-2, S2-3, S2-4) engage meaningfully with their received outside view?
- Did any over-weight or under-weight the cross-pollinated input?
- Did same-model instances (S2-1, S2-5) behave differently than cross-model instances?
- Did cross-pollination increase or decrease diversity in final outputs?

---

## 5. Factual Accuracy & Comprehension

### Question Understanding

- Did all instances correctly understand the resolution criteria?
- Did they accurately identify the forecast timeframe?
- Did they correctly assess the current status/state of affairs?

### Factual Consensus

Facts all/most outputs correctly identified:
1.
2.
3.

### Factual Errors or Ambiguities

| Output | Error/Ambiguity | Description | Impact |
|--------|-----------------|-------------|--------|
| | | | High/Medium/Low |

### Hallucinations

[Were there any invented facts, dates, events, or sources?]

---

## 6. Overall Assessment

### Strengths
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
| A | Excellent research, sound reasoning, appropriate calibration, no major errors |
| B | Good overall, minor issues in reasoning or evidence handling |
| C | Adequate, notable weaknesses but core reasoning intact |
| D | Below standard, significant reasoning or factual issues |
| F | Poor, major errors, unreliable output |

**This Forecast Grade: [ ]**

---

## 7. Recommendations

### Research Improvements

### Prompt/Pipeline Improvements

### Model-Specific Feedback

---

## 8. Comparison Flags

| Flag | Value | Notes |
|------|-------|-------|
| Output spread >30pp (binary) / >20% of range (numeric) | Yes/No | |
| Update direction errors | Yes/No | Which outputs? |
| Factual errors present | Yes/No | |
| Hallucinations detected | Yes/No | |
| Cross-pollination effective | Yes/No | |
| Critical info missed in research | Yes/No | What? |
| Base rate calculation errors | Yes/No | |
| Outlier output (>1.5 SD) | Yes/No | Which? |

---

## Appendix: Raw Data

### Probability Summary

*For binary questions:*
```
Step 1 Outputs (Outside View):
  S1-1 (Sonnet 4.5): %
  S1-2 (Sonnet 4.5): %
  S1-3 (o3-mini):    %
  S1-4 (o3):         %
  S1-5 (o3):         %

Step 2 Outputs (Inside View):
  S2-1 (Sonnet 4.5): % (received S1-1)
  S2-2 (Sonnet 4.5): % (received S1-4)
  S2-3 (o3-mini):    % (received S1-2)
  S2-4 (o3):         % (received S1-3)
  S2-5 (o3):         % (received S1-5)

Final Aggregated: %
```

*For numeric questions:*
```
Step 1 Outputs (Outside View) - Median [10th, 90th]:
  S1-1 (Sonnet 4.5): X [Y, Z]
  S1-2 (Sonnet 4.5): X [Y, Z]
  S1-3 (o3-mini):    X [Y, Z]
  S1-4 (o3):         X [Y, Z]
  S1-5 (o3):         X [Y, Z]

Step 2 Outputs (Inside View) - Median [10th, 90th]:
  S2-1 (Sonnet 4.5): X [Y, Z] (received S1-1)
  S2-2 (Sonnet 4.5): X [Y, Z] (received S1-4)
  S2-3 (o3-mini):    X [Y, Z] (received S1-2)
  S2-4 (o3):         X [Y, Z] (received S1-3)
  S2-5 (o3):         X [Y, Z] (received S1-5)

Final Aggregated: Median X [10th: Y, 90th: Z]
```

*For multiple choice questions:*
```
Step 1 Outputs (Outside View) - Option A / Option B / Option C / ...:
  S1-1 (Sonnet 4.5): % / % / % / ...
  S1-2 (Sonnet 4.5): % / % / % / ...
  S1-3 (o3-mini):    % / % / % / ...
  S1-4 (o3):         % / % / % / ...
  S1-5 (o3):         % / % / % / ...

Step 2 Outputs (Inside View):
  S2-1 (Sonnet 4.5): % / % / % / ... (received S1-1)
  S2-2 (Sonnet 4.5): % / % / % / ... (received S1-4)
  S2-3 (o3-mini):    % / % / % / ... (received S1-2)
  S2-4 (o3):         % / % / % / ... (received S1-3)
  S2-5 (o3):         % / % / % / ... (received S1-5)

Final Aggregated: % / % / % / ...
```

### Key Dates
- Forecast generated:
- Question closes:
- Question resolves:
- Key event dates from research:

---

## Post-Resolution Analysis (Complete After Resolution)

| Field | Value |
|-------|-------|
| Actual Outcome | |
| Final Prediction | |
| Brier Score (binary) / CRPS (numeric) | |

### Retrospective
- Was the forecast well-calibrated?
- What did the outputs get right?
- What did they miss that was knowable?
- What was genuinely unknowable?
