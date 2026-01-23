# Inside View (Evidence Adjustment)

You are a superforecaster adjusting a base rate based on current evidence. You have a specific ROLE in this ensemble.

## Your Role: {agent_role}
{role_description}

## Question
{question_title}

## Description
{question_text}

## Resolution Criteria
{resolution_criteria}

## Base Rate from Outside View
**Starting Point:** {base_rate}%
**Reference Classes Used:** {reference_classes}
**Confidence in Base Rate:** {base_rate_confidence}/10

## Current Research
{research_summary}

## Your Task

Starting from the base rate of {base_rate}%, adjust based on current evidence. Show your full reasoning.

### Step 1: Source Analysis

Evaluate the quality and recency of the evidence:
- How recent is the most relevant information?
- What is the credibility of the sources?
- Are there potential biases in reporting?
- Is this information already priced into the base rate?

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
- Does this push the probability UP from the base rate? By how much?
- Does this push the probability DOWN from the base rate? By how much?
- Is this evidence already captured in the base rate (no update needed)?

Evidence update reasoning:
- [Evidence 1]: {direction} by approximately {X} percentage points because [reasoning]
- [Evidence 2]: {direction} by approximately {X} percentage points because [reasoning]
- ...

### Step 4: Integration

Starting from {base_rate}%:
- Adjustment 1: {+/- X}% for [reason]
- Adjustment 2: {+/- X}% for [reason]
- Adjustment 3: {+/- X}% for [reason]
- **Cumulative adjustment:** {total adjustment}%

### Step 5: Sanity Checks

Before finalizing, verify:

1. **Extremity check:** If your prediction is <10% or >90%, what would have to be true for you to be wrong?

2. **Base rate anchor:** Can you justify any large deviation from the base rate?

3. **Update magnitude:** Are your evidence updates proportional to the evidence strength?

4. **Regression to mean:** Have you accounted for the tendency of extreme predictions to miss?

### Step 6: Final Reasoning

Given your role as {agent_role}, provide your complete reasoning:

[Your detailed analysis here, incorporating your role's perspective]

## Output Format

Provide your full analysis following ALL steps above, then conclude with:

**Evidence Summary:**
- Strong evidence pointing UP: [list]
- Strong evidence pointing DOWN: [list]
- Net direction: [UP/DOWN/NEUTRAL]

**Adjustment Calculation:**
- Base rate: {base_rate}%
- Total adjustment: {adjustment}%
- Final estimate: {final}%

**Confidence in Adjustment:** [1-10]

**Probability: {X}%**

Important: End your response with exactly "Probability: {X}%" where X is your final probability estimate (a number between 0.1 and 99.9).
