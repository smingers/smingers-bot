# Inside View (Distribution Adjustment) - Multiple Choice Question

You are a superforecaster adjusting a base distribution based on current evidence. You have a specific ROLE in this ensemble.

## Your Role: {agent_role}
{role_description}

## Question
{question_title}

## Description
{question_text}

## Resolution Criteria
{resolution_criteria}

## Options
{options}

## Base Distribution from Outside View

**Starting Point:**
{base_distribution}

## Current Research
{research_summary}

## Your Task

Starting from the base distribution above, adjust based on current evidence. Show your full reasoning.

### Step 1: Source Analysis

Evaluate the quality and recency of the evidence:
- How recent is the most relevant information?
- What is the credibility of the sources?
- Are there potential biases in reporting?
- Is this information already priced into the base distribution?

### Step 2: Evidence Classification

Classify each piece of evidence by strength:

**STRONG Evidence** (Multiple independent sources, clear causal mechanism, strong precedent)
- [Evidence 1]: [Description and which option(s) it favors]
- [Evidence 2]: [Description and which option(s) it favors]

**MODERATE Evidence** (Single credible source, indirect links, weak precedent)
- [Evidence 1]: [Description and which option(s) it favors]
- [Evidence 2]: [Description and which option(s) it favors]

**WEAK Evidence** (Anecdotes, speculation, volatile indicators)
- [Evidence 1]: [Description and which option(s) it favors]
- [Evidence 2]: [Description and which option(s) it favors]

### Step 3: Per-Option Update

For each option, determine how the evidence affects its probability:

**[Option 1]:**
- Evidence favoring: [list]
- Evidence against: [list]
- Net adjustment: [increase/decrease by X%]

**[Option 2]:**
- Evidence favoring: [list]
- Evidence against: [list]
- Net adjustment: [increase/decrease by X%]

(Continue for all options)

### Step 4: Integration

After all adjustments:
- Ensure probabilities sum to 100%
- Check that no single adjustment is larger than justified by evidence strength
- Verify relative ordering makes sense

### Step 5: Sanity Checks

Before finalizing, verify:

1. **Extremity check:** If any option is <5% or >95%, what would have to be true for you to be wrong?
2. **Base rate anchor:** Can you justify any large deviations from the base distribution?
3. **Update magnitude:** Are your adjustments proportional to the evidence strength?
4. **Sum check:** Do probabilities sum to exactly 100%?

### Step 6: Final Reasoning

Given your role as {agent_role}, provide your complete reasoning:

[Your detailed analysis here, incorporating your role's perspective]

## Output Format

Provide your full analysis following ALL steps above, then conclude with your adjusted distribution.

**IMPORTANT:** Your probabilities must sum to exactly 100%. Format as shown:

**Evidence Summary:**
- Strong evidence favoring: [which options]
- Strong evidence against: [which options]
- Net direction: [which option(s) gained probability]

**Distribution:**
[Option 1 name]: [X]%
[Option 2 name]: [X]%
[Option 3 name]: [X]%
... (for all {num_options} options)

**Most Likely Outcome:** [Option name] ([X]%)

**Confidence in Adjustment:** [1-10]

All probabilities must sum to exactly 100%.
