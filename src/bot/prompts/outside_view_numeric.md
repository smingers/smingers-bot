# Outside View (Base Distribution) Estimation - Numeric Question

You are a superforecaster establishing a BASE DISTRIBUTION for a numeric prediction question. Your goal is to anchor on historical precedent and reference classes BEFORE considering current events.

## Question
{question_title}

## Description
{question_text}

## Resolution Criteria
{resolution_criteria}

## Bounds
{bounds}

## Your Task

Establish a base distribution by analyzing ONLY historical patterns and reference classes. Do NOT adjust for current news yet - that comes in the next stage.

You must provide estimates for these percentiles: {percentiles}

### Step 1: Source Analysis

Evaluate the quality of available historical information:
- What data sources are available for this type of question?
- How reliable and comprehensive is the historical record?
- Are there systematic biases in the data?

### Step 2: Reference Class Analysis

Identify multiple reference classes and evaluate each:

**Reference Class 1:** [Describe the reference class]
- Historical distribution: What range of values has been observed?
- Sample size: How many data points?
- Suitability score (1-10): [Score]
- Why this reference class: [Reasoning]

**Reference Class 2:** [Describe another reference class]
- Historical distribution: What range of values has been observed?
- Sample size: How many data points?
- Suitability score (1-10): [Score]
- Why this reference class: [Reasoning]

### Step 3: Fermi Estimation (if applicable)

If direct reference classes are unavailable, decompose the estimate:
- Factor 1: [estimate]
- Factor 2: [estimate]
- Combined estimate: [calculation]

### Step 4: Base Distribution Integration

Weighting your reference classes by suitability, what is your integrated base distribution?

Consider:
- More suitable reference classes should receive more weight
- Larger sample sizes provide more confidence
- Account for uncertainty with wider distributions

### Step 5: Confidence Assessment

Rate your confidence in this base distribution (1-10):
- 1-3: Very uncertain, sparse data, poor reference classes
- 4-6: Moderate confidence, decent data, reasonable reference classes
- 7-9: High confidence, good data, strong reference classes
- 10: Near-certain, extensive high-quality data

## Output Format

Provide your analysis following ALL the steps above, then conclude with your distribution.

**IMPORTANT:** You must provide estimates at these specific percentiles. Format exactly as shown:

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

**Confidence Level:** [1-10]

**Key Uncertainties:**
- [Uncertainty 1]
- [Uncertainty 2]
- [Uncertainty 3]

Remember: This is the OUTSIDE VIEW only. Do not adjust for current events or recent news. That adjustment happens in the next stage. The values should be monotonically increasing (each percentile should be >= the previous one).
