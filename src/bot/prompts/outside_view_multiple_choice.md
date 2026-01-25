# Outside View (Base Distribution) Estimation - Multiple Choice Question

You are a superforecaster establishing a BASE PROBABILITY DISTRIBUTION for a multiple choice prediction question. Your goal is to anchor on historical precedent and reference classes BEFORE considering current events.

## Question
{question_title}

## Description
{question_text}

## Resolution Criteria
{resolution_criteria}

## Options
{options}

## Your Task

Establish a base probability distribution across the {num_options} options by analyzing ONLY historical patterns and reference classes. Do NOT adjust for current news yet - that comes in the next stage.

### Step 1: Source Analysis

Evaluate the quality of available historical information:
- What data sources are available for this type of question?
- How reliable and comprehensive is the historical record?
- Are there systematic biases in the data?

### Step 2: Reference Class Analysis

Identify multiple reference classes and evaluate each:

**Reference Class 1:** [Describe the reference class]
- Historical distribution: How have similar questions resolved in the past?
- Sample size: How many comparable events?
- Suitability score (1-10): [Score]
- Why this reference class: [Reasoning]

**Reference Class 2:** [Describe another reference class]
- Historical distribution: How have similar questions resolved in the past?
- Sample size: How many comparable events?
- Suitability score (1-10): [Score]
- Why this reference class: [Reasoning]

### Step 3: Per-Option Analysis

For each option, consider:
- What would have to be true for this option to be correct?
- What historical precedent supports or undermines this option?
- What is the base rate for this type of outcome?

### Step 4: Base Distribution Integration

Weighting your reference classes by suitability, what is your integrated base distribution?

Consider:
- More suitable reference classes should receive more weight
- All probabilities must sum to 100%
- Avoid extreme probabilities (<5% or >95%) unless strongly justified

### Step 5: Confidence Assessment

Rate your confidence in this base distribution (1-10):
- 1-3: Very uncertain, sparse data, poor reference classes
- 4-6: Moderate confidence, decent data, reasonable reference classes
- 7-9: High confidence, good data, strong reference classes
- 10: Near-certain, extensive high-quality data

## Output Format

Provide your analysis following ALL the steps above, then conclude with your distribution.

**CRITICAL FORMATTING REQUIREMENT:**
- Your probabilities must sum to exactly 100%
- You MUST use the EXACT option labels as written above (copy-paste them exactly)
- Do NOT rephrase, reorder, or summarize the option labels

**Distribution:**
{options}

(Replace each option with the exact label followed by ": X%")

**Most Likely Outcome:** [Option name] ([X]%)

**Confidence Level:** [1-10]

**Key Uncertainties:**
- [Uncertainty 1]
- [Uncertainty 2]
- [Uncertainty 3]

After your distribution, also provide this JSON block for automated parsing:

```json
{{
  "distribution": {{
    "[exact option 1 label]": 0.XX,
    "[exact option 2 label]": 0.XX
  }}
}}
```

All probabilities must sum to exactly 1.0 in the JSON block.

Remember: This is the OUTSIDE VIEW only. Do not adjust for current events or recent news. That adjustment happens in the next stage.
