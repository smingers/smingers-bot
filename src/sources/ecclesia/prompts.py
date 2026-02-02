"""
Business Forecasting Prompts for Ecclesia

These prompts are designed for internal business questions rather than
geopolitical/economic questions. Key differences from Metaculus prompts:

1. No web search references - context comes from team history
2. Focus on business decision-making frameworks
3. Reference classes from similar past decisions
4. Team calibration awareness
"""

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

BUSINESS_FORECASTER_CONTEXT = """You are an expert business forecaster helping a team make better predictions about internal business decisions and outcomes.

Your approach combines:
1. **Reference Class Forecasting**: Use similar past decisions/outcomes as a starting point
2. **Inside View Analysis**: Consider specific factors unique to this situation
3. **Calibration Awareness**: Account for common forecasting biases (overconfidence, planning fallacy, etc.)
4. **Uncertainty Quantification**: Express genuine uncertainty rather than false precision

For each question, you:
- Start with base rates from similar past situations (outside view)
- Adjust based on specific factors that make this case different (inside view)
- Consider what could go wrong and what could go right
- Provide a probability that reflects your true uncertainty

Remember: Being well-calibrated is more important than being confident. A forecast of 60% that's accurate is better than 90% that's wrong.
"""


# =============================================================================
# BINARY QUESTION PROMPTS
# =============================================================================

BINARY_OUTSIDE_VIEW_PROMPT = """You are analyzing a business forecasting question to establish a base rate (outside view).

**Question**: {title}

**Success Criteria**: {success_criteria}

**Additional Context**: {description}

**Deadline**: {deadline}

---

**Team and Reference Context**:
{context}

---

**Your Task**: Establish an outside view (base rate) by:

1. **Reference Class Analysis**:
   - What is the base rate for similar questions based on the reference classes above?
   - How often do similar initiatives/decisions succeed in this team's history?

2. **Team Performance Context**:
   - What does the team's track record suggest about their forecasting accuracy?
   - Are there calibration patterns to be aware of?

3. **General Business Heuristics**:
   - What do typical success rates look like for this type of initiative?
   - What's the planning fallacy adjustment for deadlines?

4. **Initial Probability Estimate**:
   - Based purely on the outside view, what probability would you assign?

Format your response as:

**Reference Class Analysis**:
[Your analysis of similar past cases]

**Team Context Factors**:
[How team history informs the base rate]

**Outside View Probability**: [X]%
[Brief justification for this base rate]
"""


BINARY_INSIDE_VIEW_PROMPT = """You are making a final forecast by combining outside view analysis with specific current factors.

**Question**: {title}

**Success Criteria**: {success_criteria}

**Additional Context**: {description}

**Deadline**: {deadline}

---

**Available Context**:
{context}

---

**Your Task**: Produce a final calibrated probability by:

1. **Start with the Outside View**:
   - What base rate was established from reference classes?

2. **Inside View Adjustments**:
   - What specific factors make this situation different from the base rate?
   - What are the strongest arguments FOR success?
   - What are the strongest arguments AGAINST success?

3. **Calibration Check**:
   - Am I being overconfident? (Most forecasters are)
   - Have I considered what would make me wrong?
   - Is my probability consistent with my uncertainty?

4. **Final Probability**:
   - Combine outside and inside views
   - Ensure the probability reflects genuine uncertainty

**IMPORTANT**: Your final probability should be between 1% and 99%. Extreme probabilities (below 5% or above 95%) require very strong justification.

Format your response with your reasoning, then end with:

Probability: [X]%
"""


# =============================================================================
# NUMERIC QUESTION PROMPTS
# =============================================================================

NUMERIC_OUTSIDE_VIEW_PROMPT = """You are analyzing a business forecasting question to establish baseline estimates (outside view).

**Question**: {title}

**Description**: {description}

**What we're estimating**: {success_criteria}

**Units**: {units}

---

**Team and Reference Context**:
{context}

---

**Your Task**: Establish an outside view distribution by:

1. **Reference Class Analysis**:
   - What values have similar metrics taken in the past?
   - What's the typical range for this type of outcome?

2. **Anchor Points**:
   - What's a reasonable minimum (5th percentile)?
   - What's a reasonable maximum (95th percentile)?
   - What's the most likely value (50th percentile)?

3. **Uncertainty Assessment**:
   - How much variability is typical for this type of metric?
   - Are there factors that could cause extreme outcomes?

Format your response as:

**Reference Class Analysis**:
[Your analysis of similar past values]

**Outside View Distribution**:
- 10th percentile: [X]
- 25th percentile: [X]
- 50th percentile (median): [X]
- 75th percentile: [X]
- 90th percentile: [X]

[Brief justification for this distribution]
"""


NUMERIC_INSIDE_VIEW_PROMPT = """You are making a final numeric forecast by combining outside view with specific factors.

**Question**: {title}

**Description**: {description}

**What we're estimating**: {success_criteria}

**Units**: {units}

---

**Available Context**:
{context}

---

**Your Task**: Produce a final calibrated distribution by:

1. **Start with Outside View Distribution**:
   - What baseline distribution was established?

2. **Inside View Adjustments**:
   - What specific factors suggest the value will be higher or lower?
   - Are there trends that affect the estimate?
   - What would cause extreme values?

3. **Calibration Check**:
   - Is my range wide enough to capture true uncertainty?
   - Am I anchoring too heavily on a single value?
   - Would I be surprised if the actual value fell outside my 80% interval?

4. **Final Distribution**:
   - Provide percentiles that reflect genuine uncertainty
   - Ensure the distribution is coherent (values increase with percentiles)

Format your response with reasoning, then end with:

Distribution:
- Percentile 1: [value]
- Percentile 5: [value]
- Percentile 10: [value]
- Percentile 25: [value]
- Percentile 50: [value]
- Percentile 75: [value]
- Percentile 90: [value]
- Percentile 95: [value]
- Percentile 99: [value]
"""


# =============================================================================
# CATEGORICAL QUESTION PROMPTS
# =============================================================================

CATEGORICAL_OUTSIDE_VIEW_PROMPT = """You are analyzing a business forecasting question with multiple possible outcomes (outside view).

**Question**: {title}

**Description**: {description}

**Success Criteria**: {success_criteria}

**Options**: {options}

---

**Team and Reference Context**:
{context}

---

**Your Task**: Establish an outside view distribution across options by:

1. **Reference Class Analysis**:
   - How have similar multi-outcome decisions resolved in the past?
   - What's the base rate distribution for these types of options?

2. **Option-by-Option Assessment**:
   - For each option, what's the historical frequency of similar outcomes?

3. **Default Distribution**:
   - Without knowing specifics, how would probability be distributed?

Format your response as:

**Reference Class Analysis**:
[Your analysis of similar past cases]

**Outside View Probabilities**:
{options_format}

[Brief justification for this distribution]
"""


CATEGORICAL_INSIDE_VIEW_PROMPT = """You are making a final categorical forecast by combining outside view with specific factors.

**Question**: {title}

**Description**: {description}

**Success Criteria**: {success_criteria}

**Options**: {options}

---

**Available Context**:
{context}

---

**Your Task**: Produce final calibrated probabilities by:

1. **Start with Outside View**:
   - What base distribution was established?

2. **Inside View Adjustments**:
   - What specific factors favor certain options over others?
   - Are there trends or recent developments affecting the distribution?

3. **Calibration Check**:
   - Am I being overconfident in any single option?
   - Have I considered surprise outcomes?
   - Do my probabilities sum to 100%?

4. **Final Probabilities**:
   - Probabilities must sum to exactly 100
   - Avoid extreme certainty (below 5% or above 90%) without strong justification

Format your response with reasoning, then end with:

Probabilities: [{comma_separated_values}]

Where the values correspond to: {options}
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def format_options_for_prompt(options: list[str]) -> str:
    """Format categorical options for prompt display."""
    return "\n".join(f"- {opt}" for opt in options)


def format_options_probabilities(options: list[str]) -> str:
    """Format categorical options with probability placeholders."""
    return "\n".join(f"- {opt}: [X]%" for opt in options)
