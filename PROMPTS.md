# Forecasting Bot Prompts Documentation

This document catalogs all prompts used in the Metaculus forecasting bot pipeline, organized by stage and question type.

## Pipeline Overview

The forecasting pipeline follows this structure:
1. **Research Stage** - Gather information from multiple sources
2. **Outside View** - Establish base rate/distribution from historical patterns
3. **Inside View** - Adjust based on current evidence (ensemble of agents)
4. **Calibration** - Final checks before submission

---

## 1. Research Stage

### 1.1 Query Generation

**Purpose:** Generate diverse search queries to research the forecasting question.

**Location:** `src/research/searcher.py::_generate_queries()`

**Model:** `query_generator` (from config, default: `claude-3-haiku-20240307`)

**Temperature:** 0.7

**Prompt:**
```
Generate {num_queries} diverse search queries to research this forecasting question.

Question: {question_title}

Description: {description_text}

Generate queries that will help find:
1. Historical base rates and precedents
2. Recent news and developments
3. Expert opinions and analysis
4. Statistical data and trends
5. Counterarguments and alternative perspectives

Output exactly {num_queries} queries, one per line, no numbering or bullets.
Keep queries concise (under 10 words each).
```

**Variables:**
- `{num_queries}` - Number of queries to generate (from config, default: 5)
- `{question_title}` - The question title
- `{description_text}` - Question description (truncated to 1000 chars)

---

### 1.2 Perplexity Research

**Purpose:** Get AI-synthesized research from Perplexity API.

**Location:** `src/research/searcher.py::_search_perplexity()`

**Model:** From config (default: `sonar-reasoning-pro`)

**Prompt:**
```
Research this forecasting question and provide relevant information:

Question: {question_title}

Description: {description_text}

Provide:
1. Relevant historical precedents and base rates
2. Recent developments and news
3. Key factors that could influence the outcome
4. Expert opinions if available
5. Data and statistics

Be thorough and cite sources where possible.
```

**Variables:**
- `{question_title}` - The question title
- `{description_text}` - Question description (truncated to 2000 chars)

---

### 1.3 Claude Native Web Search

**Purpose:** Use Claude's built-in web search tool for research.

**Location:** `src/research/searcher.py::_search_claude_native()`

**Model:** From config (default: `claude-3-haiku-20240307`)

**Prompt:**
```
Research this forecasting question and provide relevant, up-to-date information:

Question: {question_title}

Description: {description_text}

Search for:
1. Recent news and developments (last few months)
2. Historical precedents and base rates
3. Expert analysis and opinions
4. Relevant statistics and data

Provide a comprehensive summary with specific facts, dates, and sources.
```

**Variables:**
- `{question_title}` - The question title
- `{description_text}` - Question description (truncated to 2000 chars)

**Note:** This uses Claude's `web_search` tool, which requires the `web-search-2025-03-05` beta feature.

---

## 2. Outside View Stage

The Outside View establishes a base rate (binary) or base distribution (numeric/multiple choice) from historical patterns and reference classes, **before** considering current events.

### 2.1 Binary Questions - Outside View

**Purpose:** Establish base rate probability for binary (yes/no) questions.

**Location:** `src/bot/prompts/outside_view.md`

**Model:** `base_rate_estimator` (from config)

**Temperature:** 0.3

**Template File:** `src/bot/prompts/outside_view.md`

**Key Sections:**
1. Source Analysis - Evaluate historical data quality
2. Reference Class Analysis - Identify 2-3 reference classes with base rates
3. Fermi Estimation - Decompose probability if needed
4. Base Rate Integration - Weight reference classes by suitability
5. Confidence Assessment - Rate confidence 1-10

**Output Format Required:**
- Base Rate Estimate: [X%]
- Reference Classes Used: (list with weights)
- Confidence Level: [1-10]
- Key Uncertainties: (list)

**Variables:**
- `{question_title}` - Question title
- `{question_text}` - Full question description
- `{resolution_criteria}` - How the question resolves (truncated to 1000 chars)

---

### 2.2 Numeric Questions - Outside View

**Purpose:** Establish base distribution (percentiles) for numeric/continuous questions.

**Location:** `src/bot/prompts/outside_view_numeric.md`

**Model:** `base_rate_estimator` (from config)

**Temperature:** 0.3

**Template File:** `src/bot/prompts/outside_view_numeric.md`

**Key Sections:**
1. Source Analysis
2. Reference Class Analysis - Historical distributions
3. Fermi Estimation - Decompose if needed
4. Base Distribution Integration
5. Confidence Assessment

**Output Format Required:**
- Distribution with percentiles: 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99
- Median Estimate: [value] {units}
- Confidence Level: [1-10]
- Key Uncertainties: (list)

**Variables:**
- `{question_title}` - Question title
- `{question_text}` - Question description (truncated to 3000 chars)
- `{resolution_criteria}` - Resolution criteria (truncated to 1000 chars)
- `{bounds}` - Formatted bounds string (e.g., "Lower bound: 0 units, Upper bound: 100 units")
- `{units}` - Units for the numeric value
- `{percentiles}` - Comma-separated list of standard percentiles

**Note:** Percentiles must be monotonically increasing.

---

### 2.3 Multiple Choice Questions - Outside View

**Purpose:** Establish base probability distribution across discrete options.

**Location:** `src/bot/prompts/outside_view_multiple_choice.md`

**Model:** `base_rate_estimator` (from config)

**Temperature:** 0.3

**Template File:** `src/bot/prompts/outside_view_multiple_choice.md`

**Key Sections:**
1. Source Analysis
2. Reference Class Analysis - Historical distributions across options
3. Per-Option Analysis - Base rate for each option
4. Base Distribution Integration
5. Confidence Assessment

**Output Format Required:**
- Distribution: [Option name]: [X]% for each option
- Most Likely Outcome: [Option name] ([X]%)
- Confidence Level: [1-10]
- Key Uncertainties: (list)

**Variables:**
- `{question_title}` - Question title
- `{question_text}` - Question description (truncated to 3000 chars)
- `{resolution_criteria}` - Resolution criteria (truncated to 1000 chars)
- `{options}` - Formatted list of options (one per line with "- ")
- `{num_options}` - Number of options

**Note:** Probabilities must sum to exactly 100%.

---

## 3. Inside View Stage

The Inside View adjusts the base rate/distribution based on current evidence. Multiple agents run in parallel, each with a specific role/perspective.

### 3.1 Binary Questions - Inside View

**Purpose:** Adjust base rate probability based on current evidence.

**Location:** `src/bot/prompts/inside_view.md`

**Model:** Varies by agent (from `ensemble.agents[].model`)

**Temperature:** 0.7

**Template File:** `src/bot/prompts/inside_view.md`

**Key Sections:**
1. Source Analysis - Evaluate evidence quality and recency
2. Evidence Classification - STRONG/MODERATE/WEAK evidence
3. Direction of Update - UP/DOWN adjustments with reasoning
4. Integration - Cumulative adjustments from base rate
5. Sanity Checks - Extremity, base rate anchor, update magnitude, regression to mean
6. Final Reasoning - Role-specific analysis

**Output Format Required:**
- Evidence Summary: (strong evidence UP/DOWN, net direction)
- Adjustment Calculation: (base rate, total adjustment, final estimate)
- Confidence in Adjustment: [1-10]
- **Probability: [X]%** (must end with this exact format)

**Variables:**
- `{agent_role}` - Agent name (e.g., "analyst", "historian", "contrarian")
- `{role_description}` - Agent's role description from config
- `{question_title}` - Question title
- `{question_text}` - Question description (truncated to 3000 chars)
- `{resolution_criteria}` - Resolution criteria (truncated to 1000 chars)
- `{base_rate}` - Base rate percentage (e.g., "45%")
- `{reference_classes}` - Comma-separated list of reference classes
- `{base_rate_confidence}` - Confidence level 1-10
- `{research_summary}` - Research synthesis (truncated to 5000 chars)

---

### 3.2 Numeric Questions - Inside View

**Purpose:** Adjust base distribution percentiles based on current evidence.

**Location:** `src/bot/prompts/inside_view_numeric.md`

**Model:** Varies by agent (from `ensemble.agents[].model`)

**Temperature:** 0.7

**Template File:** `src/bot/prompts/inside_view_numeric.md`

**Key Sections:**
1. Source Analysis
2. Evidence Classification - STRONG/MODERATE/WEAK
3. Direction of Update - HIGHER/LOWER shifts, WIDEN/NARROW uncertainty
4. Integration - How adjustments affect specific percentiles
5. Sanity Checks - Extremity, base rate anchor, update magnitude, monotonicity
6. Final Reasoning - Role-specific analysis

**Output Format Required:**
- Evidence Summary: (strong evidence HIGHER/LOWER, net direction)
- Distribution: All percentiles (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99)
- Median Estimate: [50th percentile value] {units}
- Confidence in Adjustment: [1-10]

**Variables:**
- `{agent_role}` - Agent name
- `{role_description}` - Agent's role description
- `{question_title}` - Question title
- `{question_text}` - Question description (truncated to 3000 chars)
- `{resolution_criteria}` - Resolution criteria (truncated to 1000 chars)
- `{bounds}` - Formatted bounds string
- `{base_distribution}` - Formatted base percentiles (one per line)
- `{units}` - Units for the numeric value
- `{research_summary}` - Research synthesis (truncated to 5000 chars)
- `{percentiles}` - Comma-separated list of standard percentiles

**Note:** Percentiles must be monotonically increasing.

---

### 3.3 Multiple Choice Questions - Inside View

**Purpose:** Adjust base probability distribution across options based on current evidence.

**Location:** `src/bot/prompts/inside_view_multiple_choice.md`

**Model:** Varies by agent (from `ensemble.agents[].model`)

**Temperature:** 0.7

**Template File:** `src/bot/prompts/inside_view_multiple_choice.md`

**Key Sections:**
1. Source Analysis
2. Evidence Classification - STRONG/MODERATE/WEAK, which options favored
3. Per-Option Update - Evidence favoring/against each option
4. Integration - Ensure probabilities sum to 100%
5. Sanity Checks - Extremity, base rate anchor, update magnitude, sum check
6. Final Reasoning - Role-specific analysis

**Output Format Required:**
- Evidence Summary: (strong evidence favoring/against, net direction)
- Distribution: [Option name]: [X]% for each option
- Most Likely Outcome: [Option name] ([X]%)
- Confidence in Adjustment: [1-10]

**Variables:**
- `{agent_role}` - Agent name
- `{role_description}` - Agent's role description
- `{question_title}` - Question title
- `{question_text}` - Question description (truncated to 3000 chars)
- `{resolution_criteria}` - Resolution criteria (truncated to 1000 chars)
- `{options}` - Formatted list of options
- `{num_options}` - Number of options
- `{base_distribution}` - Formatted base distribution (one per line with probabilities)
- `{research_summary}` - Research synthesis (truncated to 5000 chars)

**Note:** Probabilities must sum to exactly 100%.

---

## 4. Calibration Stage

### 4.1 Calibration Checklist

**Purpose:** Final verification checks before submitting forecast.

**Location:** `src/bot/prompts/calibration_checklist.md`

**Model:** Currently not used by LLM (manual checklist structure)

**Template File:** `src/bot/prompts/calibration_checklist.md`

**Checklist Items:**
1. **Paraphrase Check** - Can you summarize the question correctly?
2. **Base Rate Grounding** - Is prediction rooted in base rate?
3. **Consistency Test** - Does the probability feel right?
4. **Evidence Audit** - Are top 3-5 evidence pieces factually accurate?
5. **Blind Spot Identification** - What scenario would make this look foolish?
6. **Status Quo Bias Check** - Appropriate weighting of inertia?

**Variables:**
- `{question_title}` - Question title
- `{prediction}` - Final ensemble prediction percentage
- `{base_rate}` - Base rate percentage
- `{min_prediction}` - Minimum agent prediction
- `{max_prediction}` - Maximum agent prediction
- `{deviation}` - Absolute deviation from base rate
- `{passed}` - Number of checks passed

**Note:** Currently this is a structural template. The actual calibration in `forecaster.py` uses simplified automated checks rather than LLM evaluation.

---

## Agent Roles

Agents are configured in `config.yaml` under `ensemble.agents[]`. Each agent has:
- `name` - Agent identifier (e.g., "analyst", "historian", "contrarian", "quantitative", "synthesizer")
- `model` - LLM model to use
- `weight` - Weight in ensemble aggregation
- `role_description` - Description of the agent's perspective/role

**Example Role Descriptions:**
- **Analyst:** "You are a geopolitical analyst and superforecaster. Focus on the current situation, key actors, their incentives, and recent developments."
- **Historian:** "You are a historian and superforecaster. Focus on historical precedents, analogous situations, and patterns from the past."
- **Contrarian:** "You are a contrarian forecaster. Your job is to challenge the obvious narrative, find reasons the consensus might be wrong, and identify blind spots."
- **Quantitative:** "You are a quantitative analyst and superforecaster. Focus on data, statistics, and numerical analysis."
- **Synthesizer:** "You are a synthesis expert and superforecaster. Your job is to integrate multiple perspectives, identify key uncertainties, and form a balanced view."

---

## Prompt Variables Summary

### Common Variables (All Stages)
- `{question_title}` - Question title
- `{question_text}` - Question description (various truncations)
- `{resolution_criteria}` - How the question resolves (truncated to 1000 chars)

### Research Stage
- `{num_queries}` - Number of queries to generate
- `{description_text}` - Question description (various truncations)

### Outside View Stage
- `{bounds}` - Formatted bounds (numeric only)
- `{units}` - Units (numeric only)
- `{percentiles}` - Comma-separated percentile list (numeric only)
- `{options}` - Formatted option list (multiple choice only)
- `{num_options}` - Number of options (multiple choice only)

### Inside View Stage
- `{agent_role}` - Agent name
- `{role_description}` - Agent role description
- `{base_rate}` - Base rate percentage (binary)
- `{base_distribution}` - Formatted base distribution (numeric/multiple choice)
- `{reference_classes}` - Comma-separated reference classes (binary)
- `{base_rate_confidence}` - Confidence 1-10 (binary)
- `{research_summary}` - Research synthesis (truncated to 5000 chars)

---

## Model Selection

Models are selected based on run mode (`dry_run`, `dry_run_heavy`, `production`):

- **dry_run:** Uses `models.cheap.*` (default: `claude-3-haiku-20240307`)
- **dry_run_heavy / production:** Uses `models.production.*` (default: `claude-sonnet-4-20250514` for base_rate_estimator, varies for agents)

Agent models come from `ensemble.cheap[]` or `ensemble.production[]` based on mode.

---

## Temperature Settings

- **Query Generation:** 0.7 (creative, diverse queries)
- **Outside View:** 0.3 (focused, consistent base rates)
- **Inside View:** 0.7 (creative reasoning, diverse perspectives)
- **Research (Perplexity/Claude):** Default (varies by service)

---

## Output Parsing

The code extracts structured data from LLM responses using regex patterns:

- **Binary:** Extracts probability from "Probability: X%" format
- **Numeric:** Extracts percentiles from "Percentile X: Y" or "Xth percentile: Y" formats
- **Multiple Choice:** Extracts distribution from "Option: X%" or "Probabilities: [X, Y, Z]" formats

All outputs are validated and normalized (e.g., probabilities bounded to [0.001, 0.999], distributions normalized to sum to 1.0).
