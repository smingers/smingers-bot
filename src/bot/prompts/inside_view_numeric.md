# Inside View (Distribution Adjustment) - Numeric Question

You are a superforecaster adjusting a base distribution based on current evidence. You have a specific ROLE in this ensemble.

## Your Role: {agent_role}
{role_description}

## Question
{question_title}

## Description
{question_text}

## Resolution Criteria
{resolution_criteria}

## Bounds
{bounds}

## Base Distribution from Outside View

**Starting Point:**
{base_distribution}

## Current Research
{research_summary}

## Your Task

Starting from the base distribution above, adjust based on current evidence. Show your full reasoning.

You must provide estimates for these percentiles: {percentiles}

### Step 1: Source Analysis

Evaluate the quality and recency of the evidence:
- How recent is the most relevant information?
- What is the credibility of the sources?
- Are there potential biases in reporting?
- Is this information already priced into the base distribution?

### Step 2: Evidence Classification

Classify each piece of evidence by strength:

**STRONG Evidence** (Multiple independent sources, clear causal mechanism, strong precedent)
- [Evidence 1]: [Description and relevance]
- [Evidence 2]: [Description and relevance]

**MODERATE Evidence** (Single credible source, indirect links, weak precedent)
- [Evidence 1]: [Description and relevance]
- [Evidence 2]: [Description and relevance]

**WEAK Evidence** (Anecdotes, speculation, volatile indicators)
- [Evidence 1]: [Description and relevance]
- [Evidence 2]: [Description and relevance]

### Step 3: Direction of Update

For each piece of strong/moderate evidence, determine:
- Does this shift the distribution HIGHER? By how much?
- Does this shift the distribution LOWER? By how much?
- Does this WIDEN or NARROW the distribution (change uncertainty)?
- Is this evidence already captured in the base distribution (no update needed)?

Evidence update reasoning:
- [Evidence 1]: Shift [HIGHER/LOWER] by approximately [X]% because [reasoning]
- [Evidence 2]: [WIDEN/NARROW] distribution because [reasoning]
- ...

### Step 4: Integration

How does each adjustment affect specific percentiles?
- Lower percentiles (1, 5, 10): [adjustment reasoning]
- Middle percentiles (25, 50, 75): [adjustment reasoning]
- Upper percentiles (90, 95, 99): [adjustment reasoning]

### Step 5: Sanity Checks

Before finalizing, verify:

1. **Extremity check:** Are your 1st and 99th percentiles reasonable bounds?
2. **Base rate anchor:** Can you justify any large deviations from the base distribution?
3. **Update magnitude:** Are your adjustments proportional to the evidence strength?
4. **Monotonicity:** Each percentile should be >= the previous one.

### Step 6: Final Reasoning

Given your role as {agent_role}, provide your complete reasoning:

[Your detailed analysis here, incorporating your role's perspective]

## Output Format

Provide your full analysis following ALL steps above, then conclude with your adjusted distribution.

**IMPORTANT:** You must provide estimates at these specific percentiles. Format exactly as shown:

**Evidence Summary:**
- Strong evidence pointing HIGHER: [list]
- Strong evidence pointing LOWER: [list]
- Net direction: [HIGHER/LOWER/UNCERTAIN]

**Distribution:**
Percentile 1: [value]
Percentile 5: [value]
Percentile 10: [value]
Percentile 15: [value]
Percentile 20: [value]
Percentile 25: [value]
Percentile 30: [value]
Percentile 35: [value]
Percentile 40: [value]
Percentile 45: [value]
Percentile 50: [value]
Percentile 55: [value]
Percentile 60: [value]
Percentile 65: [value]
Percentile 70: [value]
Percentile 75: [value]
Percentile 80: [value]
Percentile 85: [value]
Percentile 90: [value]
Percentile 95: [value]
Percentile 99: [value]

**Median Estimate:** [50th percentile value] {units}

**Confidence in Adjustment:** [1-10]

The values must be monotonically increasing (each percentile >= the previous one).
