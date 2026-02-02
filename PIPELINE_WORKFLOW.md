# Forecasting Pipeline Workflow

**Complete end-to-end technical documentation of the Metaculus AI forecasting pipeline.**

This document traces a production forecast from initiation through submission, documenting inputs, outputs, data routing, and transformations at each stage. All intermediate artifacts are persisted to disk for reproducibility and analysis.

---

## Overview

The pipeline implements a structured forecasting methodology:
1. **Question Intake** - Fetch question from Metaculus API
2. **Research Phase** - Multi-source information gathering
3. **Outside View** - Establish base rate from reference classes
4. **Inside View** - Evidence-based adjustment via ensemble agents
5. **Aggregation** - Combine ensemble predictions
6. **Calibration** - Quality checks and validation
7. **Submission** - Push prediction to Metaculus (production mode only)
8. **Artifact Persistence** - Save complete audit trail

---

## Entry Point & Initialization

### Command Line Entry (`main.py`)

**User executes:**
```bash
python main.py --question 41594 --mode live
```

**Initialization sequence:**

1. **Load environment** (`.env` file)
   - API keys: `ANTHROPIC_API_KEY`, `METACULUS_TOKEN`, etc.

2. **Load config** (`config.yaml`)
   - Model selections (Haiku vs Sonnet based on mode)
   - Ensemble agent definitions
   - Research sources configuration
   - Submission settings

3. **Apply mode-based configuration** (`main.py:64-102`)
   - Mode determines model tier (`cheap` vs `production`)
   - Sets submission behavior (`_should_submit` flag)
   - Cheap mode: Uses Haiku, no submission
   - Production mode: Uses Sonnet 4, submits to Metaculus

4. **Initialize Forecaster** (`src/bot/forecaster.py:37-76`)
   - Creates `MetaculusClient` for API calls
   - Creates `ResearchOrchestrator` for multi-source research
   - Creates `ArtifactStore` for persisting outputs
   - Initializes `ForecastDatabase` (SQLite) for analytics
   - Creates type-specific forecasters: `BinaryForecaster`, `NumericForecaster`, `MultipleChoiceForecaster`

5. **Reset cost tracker** (`forecaster.py:129`)
   - Begins tracking LLM API costs for this forecast

---

## Stage 1: Question Intake

**Entry:** `forecaster.py:115-148`

### Inputs
- Question ID: `41594` (from CLI)
- Metaculus API token (from env)

### Process

1. **Fetch question from Metaculus API** (`metaculus_api.py`)
   ```python
   question = await metaculus.get_question(question_id=41594)
   ```

2. **Parse question object** (MetaculusQuestion dataclass)
   - `id`: 41594
   - `title`: "Will X happen by Y date?"
   - `description`: Full question text
   - `question_type`: "binary", "numeric", or "multiple_choice"
   - `resolution_criteria`: How question will be resolved
   - `scheduled_close_time`: When forecasting closes
   - `community_prediction`: Current community forecast
   - `num_forecasters`: How many people have forecasted
   - `raw`: Complete API response

3. **Create artifact container** (`artifact_store.py:99-106`)
   ```python
   artifacts = ArtifactStore.create_forecast_artifacts(question_id=41594)
   ```
   - Generates timestamp: `20260124_143022`
   - Creates directory structure: `data/41594_20260124_143022/`

### Outputs

**Saved artifacts:**
- `data/41594_20260124_143022/00_question.json` - Raw API response

**Passed to next stage:**
- `MetaculusQuestion` object
- `ForecastArtifactPaths` container

---

## Stage 2: Question Analysis

**Entry:** `forecaster.py:150-152`

### Inputs
- `MetaculusQuestion` object from Stage 1

### Process

**Extract metadata** (`forecaster.py:317-328`)
- Classify question type (binary/numeric/multiple_choice)
- Parse temporal information (close date, resolve date)
- Extract community baseline prediction
- Count existing forecasters

### Outputs

**Saved artifacts:**
- `data/41594_20260124_143022/01_analysis.json`
  ```json
  {
    "id": 41594,
    "title": "Will X happen?",
    "type": "binary",
    "status": "open",
    "scheduled_close": "2026-03-15T00:00:00Z",
    "community_prediction": 0.67,
    "num_forecasters": 142
  }
  ```

**Passed to next stage:**
- `analysis` dict
- Question type determines which forecaster to use (binary/numeric/multiple_choice)

---

## Stage 3: Research Phase

**Entry:** `forecaster.py:154-175`

### Inputs
- `question_title`: "Will X happen?"
- `question_text`: Full description
- `question_type`: "binary"

### Process

Research orchestration happens in parallel across multiple sources:

#### 3A. Query Generation (`searcher.py:170-210`)

**LLM call (Haiku in cheap mode):**
```
Prompt: "Generate 3 diverse search queries to research this forecasting question..."
Model: claude-3-haiku-20240307
Temperature: 0.7
```

**Output:** 3-5 search queries
```
["X event historical precedents", "X recent developments 2026", "expert analysis X probability"]
```

**Saved to:** `data/.../02_research/queries_generated.json`

#### 3B. Parallel Search Execution (`searcher.py:100-139`)

Multiple search sources execute concurrently (based on config):

**1. Web Search (Serper API)** - if enabled (`searcher.py:274-309`)
- Executes each query via Google Search API
- Returns: titles, URLs, snippets
- Saved to: `data/.../02_research/web_search.json`

**2. Google News (Serper API)** - if enabled (`searcher.py:311-346`)
- Executes queries via Google News API
- Returns: news articles with titles, URLs, snippets, publish dates
- Saved to: `data/.../02_research/google_news.json`

**3. Agentic Search** - if enabled (`search.py:560-696`)
- Iterative LLM-based search using reasoning model
- Generates Google/Google News queries, analyzes results, iterates up to 7 steps
- Returns: AI-synthesized research with citations
- Output included in `<Agent_report>` tags in search results

**4. AskNews API** - if enabled (`searcher.py:405-490`)
- OAuth authentication flow
- Searches news database
- Returns: curated news articles with summaries
- Saved to: `data/.../02_research/asknews.json`

**5. Claude Web Search** - if enabled (`searcher.py:492-557`)
- Uses Claude's native web search tool
- Cost: $10/1000 searches + tokens
- Returns: synthesized research
- Saved to: `data/.../02_research/claude_web_search.json`

**6. Full Article Scraping** - if enabled (`searcher.py:348-403`)
- Takes top URLs from search results
- Scrapes full article text (via Trafilatura/BeautifulSoup)
- Truncates to 5000 chars per article
- Limits to 5 articles total
- Enriches `SearchResult` objects with `full_content` field

#### 3C. Research Synthesis (`searcher.py:559-634`)

Combines all search results into structured markdown:

```markdown
# Research Synthesis

**Generated:** 2026-01-24T14:30:45Z
**Total Sources:** 47

## Search Queries
1. X event historical precedents
2. X recent developments 2026
3. expert analysis X probability

## AI-Synthesized Research (Agent)
[Agent's analysis...]

## Google News Results
### [News Article Title](URL) (2026-01-20)
> Snippet text...
**Full Article:**
[Full scraped text...]

## Web Search Results
[Similar structure...]
```

### Outputs

**Saved artifacts:**
- `data/.../02_research/queries_generated.json` - Generated queries
- `data/.../02_research/web_search.json` - Web search results
- `data/.../02_research/google_news.json` - News results
- Agent reports included inline in search results
- `data/.../02_research/asknews.json` - AskNews results
- `data/.../02_research/synthesis.md` - Combined research markdown

**Passed to next stage:**
- `research_summary` (markdown string, ~5000 chars)
- Contains all relevant context for forecasting

---

## Stage 4: Outside View (Base Rate Estimation)

**Entry:** `forecaster.py:178-197` → `binary.py:38-111`

The pipeline now branches based on question type. This example follows the **binary** path.

### Inputs
- `question_title`: "Will X happen?"
- `question_text`: Full description
- `resolution_criteria`: How question resolves
- **Not used at this stage:** `research_summary` (reserved for inside view)

### Process

#### 4A. Load Prompt Template (`binary.py:113-130`)

**File:** `src/bot/prompts/outside_view.md`

Template uses Python `.format()` syntax:
```markdown
# Outside View: Base Rate Estimation

**Question:** {question_title}

**Description:** {question_text}

**Resolution Criteria:** {resolution_criteria}

Your task: Identify 3-5 reference classes and estimate a base rate...
```

#### 4B. Fill Template (`binary.py:126-130`)
```python
prompt = template.format(
    question_title=question_title,
    question_text=question_text[:3000],  # Truncate if needed
    resolution_criteria=resolution_criteria[:1000]
)
```

#### 4C. LLM Call (`binary.py:133-145`)

**Model selection (production mode):**
```yaml
# From config._active_models
base_rate_estimator: "claude-sonnet-4-20250514"
```

**API call:**
```python
response = await llm.complete(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3,  # Low temp for consistency
    max_tokens=4000
)
```

**LLM response format:**
```markdown
## Reference Classes Identified

**Reference Class 1:** Historical events of type X
- Base rate: 40% (12 out of 30 events)
- Relevance: High (similar timeframe and actors)

[Additional reference classes...]

## Synthesis
Weighing the reference classes by relevance...

**Base Rate Estimate: 35%**
**Confidence Level: 7/10**
```

#### 4D. Parse Response (`binary.py:150-160`)

**Extract base rate** (`binary.py:279-306`)
- Regex patterns search for: `"Probability: X%"`, `"Base Rate Estimate: X%"`
- Converts to float: `0.35`
- Clamps to bounds: `[0.001, 0.999]`

**Extract reference classes** (`binary.py:308-330`)
- Regex finds: `"Reference Class N: [text]"`
- Extracts up to 5 classes: `["Historical events of type X", "Similar situations in region Y", ...]`

**Extract confidence** (`binary.py:332-344`)
- Regex finds: `"Confidence Level: X"` or `"X/10"`
- Returns integer: `7`

### Outputs

**Saved artifacts:**
- `data/.../03_outside_view/prompt.md` - Filled template (note: currently saved as placeholder)
- `data/.../03_outside_view/response.md` - Full LLM reasoning
  ```markdown
  [Complete LLM response with reference class analysis...]
  ```
- `data/.../03_outside_view/extracted.json`
  ```json
  {
    "base_rate": 0.35,
    "reference_classes": ["Historical events of type X", "Similar situations..."],
    "confidence": 7
  }
  ```

**Passed to next stage:**
- `base_rate`: 0.35 (float)
- `reference_classes`: list of strings
- `base_rate_confidence`: 7 (int)
- `outside_view_reasoning`: full LLM response text

---

## Stage 5: Inside View (Ensemble Adjustment)

**Entry:** `binary.py:71-93` → `binary.py:162-221`

### Inputs
- All inputs from outside view
- `research_summary`: Complete research synthesis (markdown)
- `base_rate`: 0.35
- `reference_classes`: List from outside view
- `base_rate_confidence`: 7

### Process

#### 5A. Load Ensemble Configuration (`binary.py:173-187`)

**From config (production mode):**
```yaml
ensemble:
  production:
    - name: "analyst"
      model: "claude-sonnet-4-20250514"
      weight: 1.0
      role_description: "You are a geopolitical analyst..."

    - name: "historian"
      model: "claude-sonnet-4-20250514"
      weight: 1.0
      role_description: "You are a historian..."

    - name: "contrarian"
      model: "claude-sonnet-4-20250514"
      weight: 0.8
      role_description: "You are a contrarian forecaster..."

    - name: "quantitative"
      model: "claude-sonnet-4-20250514"
      weight: 1.0
      role_description: "You are a quantitative analyst..."

    - name: "synthesizer"
      model: "claude-sonnet-4-20250514"
      weight: 1.2
      role_description: "You are a synthesis expert..."
```

**Result:** 5 agents with different perspectives, weighted total = 5.0

#### 5B. Load Inside View Prompt Template (`binary.py:189-192`)

**File:** `src/bot/prompts/inside_view.md`

Template structure:
```markdown
# Inside View: Evidence-Based Adjustment

**Your Role:** {agent_role}
{role_description}

**Question:** {question_title}
**Description:** {question_text}
**Resolution Criteria:** {resolution_criteria}

## Base Rate (Outside View)
**Estimate:** {base_rate}%
**Reference Classes:** {reference_classes}
**Confidence:** {base_rate_confidence}/10

## Research Summary
{research_summary}

## Your Task
Starting from the base rate, evaluate how current evidence should update...

Classify evidence as STRONG/MODERATE/WEAK and provide your probability.
```

#### 5C. Run Agents in Parallel (`binary.py:194-220`)

**Concurrent execution:**
```python
tasks = [
    _run_single_agent(agent="analyst", ...),
    _run_single_agent(agent="historian", ...),
    _run_single_agent(agent="contrarian", ...),
    _run_single_agent(agent="quantitative", ...),
    _run_single_agent(agent="synthesizer", ...),
]
results = await asyncio.gather(*tasks)
```

**Per-agent execution** (`binary.py:223-277`):

1. **Fill template** with agent-specific role:
   ```python
   prompt = template.format(
       agent_role="analyst",
       role_description="You are a geopolitical analyst...",
       question_title=question_title,
       base_rate="35.0",  # Formatted as percentage
       reference_classes="Historical events of type X, Similar situations...",
       base_rate_confidence=7,
       research_summary=research_summary[:5000]  # Truncated
   )
   ```

2. **LLM call:**
   ```python
   response = await llm.complete(
       model="claude-sonnet-4-20250514",
       messages=[{"role": "user", "content": prompt}],
       temperature=0.7,  # Higher temp for ensemble diversity
       max_tokens=4000
   )
   ```

3. **Parse response:**
   - Extract probability: regex search for `"Probability: X%"`
   - Extract evidence weights: parse STRONG/MODERATE/WEAK sections

   Example response:
   ```markdown
   ## Evidence Analysis

   **STRONG Evidence (moves probability significantly):**
   - Recent development X changes the landscape
   - Key actor Y announced intent

   **MODERATE Evidence:**
   - Historical pattern suggests...

   **WEAK Evidence:**
   - Speculative reports about...

   **Probability: 42%**
   ```

4. **Create AgentPrediction object:**
   ```python
   AgentPrediction(
       agent_id="analyst",
       model="claude-sonnet-4-20250514",
       weight=1.0,
       prediction=0.42,
       reasoning="[Full LLM response]",
       evidence_weights={
           "strong": ["Recent development X...", "Key actor Y..."],
           "moderate": ["Historical pattern..."],
           "weak": ["Speculative reports..."]
       }
   )
   ```

**Parallel execution completes:** All 5 agents return predictions

Example results:
- Analyst: 0.42 (weight 1.0)
- Historian: 0.38 (weight 1.0)
- Contrarian: 0.25 (weight 0.8)
- Quantitative: 0.45 (weight 1.0)
- Synthesizer: 0.40 (weight 1.2)

### Outputs (per agent)

**Saved artifacts (for each agent):**
- `data/.../04_inside_view/{agent_id}/prompt.md` - Filled template
- `data/.../04_inside_view/{agent_id}/response.md` - Full LLM reasoning
- `data/.../04_inside_view/{agent_id}/extracted.json`
  ```json
  {
    "prediction": 0.42,
    "weight": 1.0,
    "evidence_weights": {
      "strong": ["..."],
      "moderate": ["..."],
      "weak": ["..."]
    }
  }
  ```

**Passed to next stage:**
- List of 5 `AgentPrediction` objects

---

## Stage 6: Aggregation

**Entry:** `binary.py:84-88` → `aggregator.py:67-126`

### Inputs
- `agent_predictions`: List of 5 AgentPrediction objects
- Predictions: `[0.42, 0.38, 0.25, 0.45, 0.40]`
- Weights: `[1.0, 1.0, 0.8, 1.0, 1.2]`

### Process

#### 6A. Calculate Statistics (`aggregator.py:86-89`)
```python
mean_pred = statistics.mean([0.42, 0.38, 0.25, 0.45, 0.40])
           = 0.38

median_pred = statistics.median([0.42, 0.38, 0.25, 0.45, 0.40])
             = 0.40

std_dev = statistics.stdev([0.42, 0.38, 0.25, 0.45, 0.40])
        = 0.074
```

#### 6B. Weighted Average (`aggregator.py:92-94`)

**Formula:**
```
final = Σ(prediction_i × weight_i) / Σ(weight_i)
      = (0.42×1.0 + 0.38×1.0 + 0.25×0.8 + 0.45×1.0 + 0.40×1.2) / (1.0+1.0+0.8+1.0+1.2)
      = (0.42 + 0.38 + 0.20 + 0.45 + 0.48) / 5.0
      = 1.93 / 5.0
      = 0.386
```

#### 6C. Bound Check (`aggregator.py:114`)
```python
final_pred = max(0.001, min(0.999, 0.386))
           = 0.386  # Within bounds
```

### Outputs

**Saved artifacts:**
- `data/.../04_inside_view/aggregation.json`
  ```json
  {
    "individual_predictions": [
      {"agent": "analyst", "prediction": 0.42, "weight": 1.0},
      {"agent": "historian", "prediction": 0.38, "weight": 1.0},
      {"agent": "contrarian", "prediction": 0.25, "weight": 0.8},
      {"agent": "quantitative", "prediction": 0.45, "weight": 1.0},
      {"agent": "synthesizer", "prediction": 0.40, "weight": 1.2}
    ],
    "method": "weighted_average",
    "mean": 0.38,
    "median": 0.40,
    "std_dev": 0.074,
    "min": 0.25,
    "max": 0.45,
    "final": 0.386
  }
  ```

**Passed to next stage:**
- `final_prediction`: 0.386
- `aggregation`: dict with statistics

---

## Stage 7: Calibration Checks

**Entry:** `forecaster.py:199-207` → `forecaster.py:521-578`

### Inputs
- `question`: MetaculusQuestion object
- `forecast_result`: dict containing base_rate (0.35) and final_prediction (0.386)

### Process

#### 7A. Automated Checklist (`forecaster.py:532-563`)

**Checks performed:**

1. **Paraphrase check** - Can question be summarized?
   - Status: Auto-pass (uses question title)

2. **Base rate grounding** - Is final prediction near base rate?
   ```python
   passed = abs(final_prediction - base_rate) < 0.3
          = abs(0.386 - 0.35) < 0.3
          = 0.036 < 0.3
          = True
   ```

3. **Consistency test** - Does "39 out of 100 times" feel right?
   - Status: Auto-pass (manual review recommended)

4. **Evidence audit** - Are top pieces of evidence valid?
   - Status: Auto-pass (evidence recorded in artifacts)

5. **Blind spots** - What scenario would make forecast look silly?
   - Status: Auto-pass (manual review recommended)

6. **Status quo bias** - Considered inertia/status quo?
   - Status: Auto-pass (manual review recommended)

**Passed count:** 6/6

**Recommendation:** SUBMIT (≥4 checks passed)

### Outputs

**Saved artifacts:**
- `data/.../05_calibration/checklist.json`
  ```json
  {
    "paraphrase": {"passed": true, "response": "Will X happen?"},
    "base_rate_grounded": {"passed": true, "response": "Base rate: 35.0%, Final: 38.6%"},
    "consistency_test": {"passed": true, "response": "Automated check passed"},
    "evidence_audit": {"passed": true, "response": "Evidence recorded in artifacts"},
    "blind_spots": {"passed": true, "response": "To be reviewed manually"},
    "status_quo_bias": {"passed": true, "response": "To be reviewed manually"}
  }
  ```

- `data/.../05_calibration/adjustments.json`
  ```json
  {
    "passed_count": 6,
    "total_checks": 6,
    "recommendation": "SUBMIT"
  }
  ```

**Passed to next stage:**
- `calibration_result`: dict with checklist results

---

## Stage 8: Submission

**Entry:** `forecaster.py:209-238` → `forecaster.py:580-632`

### Inputs
- `question`: MetaculusQuestion (id=41594)
- `forecast_result`: Contains `final_prediction` (0.386)
- `dry_run`: False (in live mode)

### Process (Live Mode)

#### 8A. Submit to Metaculus API (`metaculus_api.py`)

**Binary question:**
```python
response = await metaculus.submit_prediction(
    question=question,  # id=41594
    prediction=0.386    # As decimal
)
```

**API request:**
```http
POST https://www.metaculus.com/api/questions/41594/predict/
Authorization: Token {METACULUS_TOKEN}
Content-Type: application/json

{
  "prediction": 0.386
}
```

**API response:**
```json
{
  "id": 123456,
  "question_id": 41594,
  "prediction": 0.386,
  "created_at": "2026-01-24T14:35:22Z",
  "user_id": 7890
}
```

#### 8B. Handle Other Question Types

**Numeric question:**
```python
response = await metaculus.submit_numeric_prediction(
    question_id=41594,
    cdf=[0.001, 0.01, 0.05, ..., 0.95, 0.99, 0.999]  # 201 points
)
```

**Multiple choice question:**
```python
response = await metaculus.submit_multiple_choice_prediction(
    question_id=41594,
    distribution={
        "option_1": 0.25,
        "option_2": 0.35,
        "option_3": 0.30,
        "option_4": 0.10
    }
)
```

### Process (Test/Preview Mode)

**If `dry_run=True` (test or preview mode):**
```python
logger.info(f"DRY RUN: Would submit 38.6%")
# No API call made
# Still save prediction artifact
```

### Outputs

**Saved artifacts:**
- `data/.../06_submission/final_prediction.json`
  ```json
  {
    "prediction": 0.386,
    "submitted": true,
    "timestamp": "2026-01-24T14:35:22Z"
  }
  ```

- `data/.../06_submission/api_response.json`
  ```json
  {
    "id": 123456,
    "question_id": 41594,
    "prediction": 0.386,
    "created_at": "2026-01-24T14:35:22Z",
    "user_id": 7890
  }
  ```

**Status:** Prediction successfully submitted to Metaculus

---

## Stage 9: Report Generation

**Entry:** `forecaster.py:241-247` → `forecaster.py:634-710`

### Inputs
- All data from previous stages
- `research_results`: ResearchResults object
- `forecast_result`: Complete forecast with base_rate, predictions, aggregation
- `calibration_result`: Checklist results

### Process

#### 9A. Compile Report Data (`report_generator.py`)

**Build ForecastData object:**
```python
ForecastData(
    question_id=41594,
    question_title="Will X happen?",
    question_type="binary",
    timestamp="2026-01-24 14:35:22 UTC",
    research_sources_count=47,
    research_summary="[Agent synthesis or research artifact preview]",
    base_rate=0.35,
    reference_classes=["Historical events of type X", "Similar situations..."],
    outside_view_reasoning="[Full outside view LLM response]",
    agent_results=[
        AgentResult(name="analyst", model="...", weight=1.0, prediction=0.42, reasoning="..."),
        AgentResult(name="historian", ...),
        # ... 5 agents total
    ],
    aggregation_method="weighted_average",
    final_prediction=0.386,
    calibration_checklist={...},
    total_cost=0.0342  # USD
)
```

#### 9B. Generate Markdown Report

**Template output:**
```markdown
# Forecast Report: Will X happen?

**Question ID:** 41594
**Forecast Generated:** 2026-01-24 14:35:22 UTC
**Question Type:** Binary

---

## Final Prediction: 38.6%

**Base Rate (Outside View):** 35.0%
**Adjustment:** +3.6 percentage points

---

## Research Summary

**Sources Consulted:** 47

[Research synthesis excerpt...]

---

## Outside View Analysis

**Base Rate Estimate:** 35%

**Reference Classes:**
1. Historical events of type X
2. Similar situations in region Y
3. [...]

**Reasoning:**
[Full outside view reasoning...]

---

## Inside View: Agent Forecasts

### Agent: analyst (Weight: 1.0)
**Model:** claude-sonnet-4-20250514
**Prediction:** 42%

**Reasoning:**
[Full agent reasoning...]

**Evidence Classification:**
- **STRONG:** Recent development X..., Key actor Y...
- **MODERATE:** Historical pattern...
- **WEAK:** Speculative reports...

### Agent: historian (Weight: 1.0)
[Similar structure...]

[... 5 agents total ...]

---

## Aggregation

**Method:** Weighted Average

**Individual Predictions:**
- analyst: 42% (weight 1.0)
- historian: 38% (weight 1.0)
- contrarian: 25% (weight 0.8)
- quantitative: 45% (weight 1.0)
- synthesizer: 40% (weight 1.2)

**Statistics:**
- Mean: 38%
- Median: 40%
- Std Dev: 7.4%
- Range: [25%, 45%]

**Final (Weighted):** 38.6%

---

## Calibration Checklist

✓ Paraphrase: Can summarize question clearly
✓ Base Rate Grounding: Final prediction within 30pp of base rate
✓ Consistency Test: "39 out of 100 times" feels reasonable
✓ Evidence Audit: Key evidence is factually valid
✓ Blind Spots: Considered scenarios that would invalidate forecast
✓ Status Quo Bias: Accounted for inertia/default outcomes

**Checks Passed:** 6/6
**Recommendation:** SUBMIT

---

## Cost Breakdown

- Research: $0.003
- LLM Forecasting: $0.031
- **Total:** $0.034

---

## Artifacts

Full audit trail saved to: `data/41594_20260124_143022/`
```

### Outputs

**Saved artifacts:**
- `data/.../06_submission/reasoning_report.md` - Complete human-readable report

**Report is available for:**
- Manual review before submission (dry run mode)
- Post-submission documentation
- Metaculus reasoning field (if enabled in config)

---

## Stage 10: Metadata & Database Persistence

**Entry:** `forecaster.py:249-271`

### Process

#### 10A. Calculate Final Metadata (`forecaster.py:250-262`)

**Cost tracking:**
```python
costs = get_cost_tracker().get_summary()
{
    "total_cost": 0.0342,
    "calls_by_model": {
        "claude-sonnet-4-20250514": 6,
        "claude-3-haiku-20240307": 1
    },
    "cost_by_model": {
        "claude-sonnet-4-20250514": 0.0312,
        "claude-3-haiku-20240307": 0.003
    }
}
```

**Timing:**
```python
timing = {
    "start": "2026-01-24T14:30:22Z",
    "end": "2026-01-24T14:35:22Z",
    "duration_seconds": 300
}
```

#### 10B. Save Metadata (`artifact_store.py:230-249`)

**Saved artifacts:**
- `data/.../metadata.json`
  ```json
  {
    "question_id": 41594,
    "timestamp": "20260124_143022",
    "created_at": "2026-01-24T14:35:22Z",
    "config_hash": "a3f5e9b2c1d4",
    "config_snapshot": {
      "mode": "live",
      "models": {...},
      "ensemble": {...}
    },
    "costs": {
      "total_cost": 0.0342,
      "calls_by_model": {...},
      "cost_by_model": {...}
    },
    "timing": {
      "start": "2026-01-24T14:30:22Z",
      "end": "2026-01-24T14:35:22Z",
      "duration_seconds": 300
    },
    "errors": []
  }
  ```

#### 10C. Database Records (`forecaster.py:712-775`)

**SQLite database:** `data/forecasts.db`

**1. Main forecast record:**
```sql
INSERT INTO forecasts (
    id, question_id, timestamp, question_type, question_title,
    base_rate, final_prediction, total_cost, config_hash, tournament_id
) VALUES (
    '41594_20260124_143022',
    41594,
    '20260124_143022',
    'binary',
    'Will X happen?',
    0.35,
    0.386,
    0.0342,
    'a3f5e9b2c1d4',
    32721
);
```

**2. Agent predictions (5 records):**
```sql
INSERT INTO agent_predictions (
    forecast_id, agent_id, model, weight, prediction, reasoning_length
) VALUES
    ('41594_20260124_143022', 'analyst', 'claude-sonnet-4-20250514', 1.0, 0.42, 2847),
    ('41594_20260124_143022', 'historian', 'claude-sonnet-4-20250514', 1.0, 0.38, 3012),
    ('41594_20260124_143022', 'contrarian', 'claude-sonnet-4-20250514', 0.8, 0.25, 2654),
    ('41594_20260124_143022', 'quantitative', 'claude-sonnet-4-20250514', 1.0, 0.45, 2991),
    ('41594_20260124_143022', 'synthesizer', 'claude-sonnet-4-20250514', 1.2, 0.40, 3156);
```

**3. Research sources (47 records):**
```sql
INSERT INTO research_sources (
    forecast_id, source_type, query, num_results
) VALUES
    ('41594_20260124_143022', 'web_search', 'X event historical precedents', 10),
    ('41594_20260124_143022', 'google_news', 'X recent developments 2026', 15),
    ('41594_20260124_143022', 'agent', 'Will X happen?', 1),
    -- ... 44 more rows
```

### Outputs

**Database analytics available:**
- Query all forecasts for a question
- Compare predictions across config versions
- Analyze agent agreement patterns
- Track costs over time
- Aggregate research source effectiveness

---

## Final Result

**Entry:** `forecaster.py:273-303` → `main.py:122-158`

### Console Output

```
============================================================
FORECAST COMPLETE
============================================================
Question: Will X happen?
Type: binary
Prediction: 38.6%
Base Rate: 35.0%
Cost: $0.0342
Artifacts: data/41594_20260124_143022
Status: SUBMITTED
```

### Return Value

```python
{
    "question": MetaculusQuestion(id=41594, title="Will X happen?", ...),
    "prediction": 0.386,
    "forecast_result": {
        "final_prediction": 0.386,
        "base_rate": 0.35,
        "reference_classes": ["..."],
        "agent_predictions": [AgentPrediction(...), ...],
        "aggregation": {...},
        "outside_view_reasoning": "...",
        "inside_view_reasoning": {...}
    },
    "calibration": {...},
    "submission": {
        "success": true,
        "response": {...}
    },
    "costs": {
        "total_cost": 0.0342,
        ...
    },
    "artifacts_dir": "data/41594_20260124_143022"
}
```

---

## Complete Artifact Directory Structure

```
data/41594_20260124_143022/
├── 00_question.json                    # Raw Metaculus API response
├── 01_analysis.json                    # Question classification & metadata
├── 02_research/
│   ├── queries_generated.json          # LLM-generated search queries
│   ├── web_search.json                 # Google search results via Serper
│   ├── google_news.json                # Google News results via Serper
│   ├── agent_report.json               # Agentic search synthesis (if enabled)
│   ├── asknews.json                    # AskNews articles (if enabled)
│   └── synthesis.md                    # Combined research markdown
├── 03_outside_view/
│   ├── prompt.md                       # Filled template sent to LLM
│   ├── response.md                     # Full LLM response
│   └── extracted.json                  # Parsed base_rate, reference_classes, confidence
├── 04_inside_view/
│   ├── analyst/
│   │   ├── prompt.md                   # Agent-specific prompt
│   │   ├── response.md                 # Agent's full reasoning
│   │   └── extracted.json              # Prediction & evidence weights
│   ├── historian/
│   │   ├── prompt.md
│   │   ├── response.md
│   │   └── extracted.json
│   ├── contrarian/
│   │   ├── prompt.md
│   │   ├── response.md
│   │   └── extracted.json
│   ├── quantitative/
│   │   ├── prompt.md
│   │   ├── response.md
│   │   └── extracted.json
│   ├── synthesizer/
│   │   ├── prompt.md
│   │   ├── response.md
│   │   └── extracted.json
│   └── aggregation.json                # Weighted average calculation
├── 05_calibration/
│   ├── checklist.json                  # Calibration checklist responses
│   └── adjustments.json                # Final recommendation (SUBMIT/REVIEW)
├── 06_submission/
│   ├── final_prediction.json           # Final prediction that was submitted
│   ├── api_response.json               # Metaculus API response
│   └── reasoning_report.md             # Complete human-readable report
└── metadata.json                       # Config snapshot, costs, timing, errors
```

**Total files:** 27 artifacts per forecast

---

## Configuration Parameters That Affect Pipeline

### Question Type Routing

**Binary questions** (`question_type="binary"`):
- Uses `BinaryForecaster`
- Prompts: `outside_view.md`, `inside_view.md`
- Output: Single probability (0.001-0.999)
- Submission: `POST /questions/{id}/predict/` with `{"prediction": 0.386}`

**Numeric questions** (`question_type="numeric"`):
- Uses `NumericForecaster`
- Prompts: `outside_view_numeric.md`, `inside_view_numeric.md`
- Output: Full CDF (201 points) + percentiles
- Submission: `POST /questions/{id}/predict/` with `{"cdf": [0.001, ..., 0.999]}`

**Multiple choice questions** (`question_type="multiple_choice"`):
- Uses `MultipleChoiceForecaster`
- Prompts: `outside_view_multiple_choice.md`, `inside_view_multiple_choice.md`
- Output: Probability distribution over options
- Submission: `POST /questions/{id}/predict/` with `{"distribution": {"A": 0.25, "B": 0.35, ...}}`

### Research Sources (Enabled/Disabled)

**Minimal setup** (free, no API keys):
```yaml
research:
  sources:
    - type: "llm_knowledge"
      enabled: true
```

**Full research** (requires API keys):
```yaml
research:
  sources:
    - type: "llm_knowledge"
      enabled: true
    - type: "web_search"          # Requires SERPER_API_KEY
      enabled: true
    - type: "google_news"          # Requires SERPER_API_KEY
      enabled: true
    - type: "article_scraping"     # Free, uses Trafilatura
      enabled: true
    - type: "agentic_search"       # Uses configured agentic_search model
      enabled: true
    - type: "asknews"              # Requires ASKNEWS credentials
      enabled: true
    - type: "claude_web_search"    # Requires ANTHROPIC_API_KEY
      enabled: false
```

### Model Selection by Mode

**Test mode** (cheap, fast testing):
```yaml
mode: "test"
models:
  cheap:
    base_rate_estimator: "claude-3-haiku-20240307"
ensemble:
  cheap:
    - {name: "analyst", model: "claude-3-haiku-20240307", weight: 1.0}
```
- Cost: ~$0.002 per forecast
- Speed: ~30 seconds
- No submission to Metaculus

**Live mode** (high quality, submits):
```yaml
mode: "live"
models:
  production:
    base_rate_estimator: "claude-sonnet-4-20250514"
ensemble:
  production:
    - {name: "analyst", model: "claude-sonnet-4-20250514", weight: 1.0}
    - {name: "historian", model: "claude-sonnet-4-20250514", weight: 1.0}
    - {name: "contrarian", model: "claude-sonnet-4-20250514", weight: 0.8}
    - {name: "quantitative", model: "claude-sonnet-4-20250514", weight: 1.0}
    - {name: "synthesizer", model: "claude-sonnet-4-20250514", weight: 1.2}
```
- Cost: ~$0.03-0.05 per forecast
- Speed: ~5 minutes
- Submits to Metaculus

### Ensemble Size & Weights

**Minimal** (1 agent):
```yaml
ensemble:
  production:
    - {name: "default", model: "...", weight: 1.0}
```

**Full** (5 agents, optimized weights):
```yaml
ensemble:
  production:
    - {name: "analyst", weight: 1.0}
    - {name: "historian", weight: 1.0}
    - {name: "contrarian", weight: 0.8}     # Downweight contrarian
    - {name: "quantitative", weight: 1.0}
    - {name: "synthesizer", weight: 1.2}    # Upweight synthesis
```

**Aggregation method:**
- `weighted_average` (default): Σ(pred × weight) / Σ(weight)
- `median`: Middle value (ignores weights)
- `trimmed_mean`: Remove outliers, then average

---

## Error Handling & Resilience

### Research Phase Failures

**If a search source fails:**
- Exception is caught in `asyncio.gather(..., return_exceptions=True)`
- Logged as warning: `"Search failed: {error}"`
- Pipeline continues with remaining sources
- Minimum viable: LLM knowledge only (no external APIs)

### Ensemble Agent Failures

**If an agent fails:**
- Exception is caught during `asyncio.gather`
- Agent is excluded from aggregation
- Remaining agents proceed
- Minimum viable: 1 successful agent

### API Submission Failures

**If Metaculus API fails:**
- Prediction is still saved to artifacts
- Error is logged in `submission_dir/final_prediction.json`
- Return value includes `{"submission": {"success": false, "error": "..."}}`
- User can manually retry or resubmit from saved artifacts

---

## Performance Characteristics

### Production Run Timings

**Typical breakdown (total ~5 minutes):**
- Question fetch: 1 second
- Research (parallel): 30-60 seconds
  - Query generation: 5 seconds
  - Web search: 10 seconds
  - News search: 10 seconds
  - Article scraping: 20-40 seconds
  - Agentic search: 20-60 seconds
- Outside view: 20-30 seconds
- Inside view (5 agents parallel): 60-90 seconds
- Aggregation: <1 second
- Calibration: <1 second
- Submission: 2 seconds
- Report generation: 5 seconds
- Database persistence: 1 second

### Cost Breakdown (Live Mode)

**Per forecast (~$0.03-0.05):**
- Query generation (Haiku): $0.0002
- Outside view (Sonnet 4): $0.005
- Inside view agents (5x Sonnet 4): $0.025-0.04
- Research APIs:
  - Serper (web + news): $0.001 (2,500 free/month)
  - Agentic search: $0.02-0.10 (depends on iterations)
  - AskNews: Free for tournament participants
  - Article scraping: Free

**Optimization strategies:**
- Use Haiku for simple tasks (classification, query generation)
- Use Sonnet 4 only for reasoning-heavy tasks
- Disable expensive research sources for testing
- Reduce ensemble size for rapid iteration

---

## Data Flow Summary

```
CLI Command
    ↓
main.py: Load config, apply mode
    ↓
Forecaster.__init__: Initialize components
    ↓
┌─────────────────────────────────────────────────────────────┐
│ forecast_question()                                          │
│                                                              │
│  1. Fetch Question (Metaculus API)                          │
│     → MetaculusQuestion object                              │
│     → Save: 00_question.json                                │
│                                                              │
│  2. Analyze Question                                        │
│     → analysis dict                                         │
│     → Save: 01_analysis.json                                │
│                                                              │
│  3. Research                                                │
│     ├→ Generate queries (LLM)                               │
│     ├→ Execute searches (parallel)                          │
│     │   ├→ Web search (Serper)                              │
│     │   ├→ Google News (Serper)                             │
│     │   ├→ Agentic search (if enabled)                      │
│     │   ├→ AskNews (if enabled)                             │
│     │   └→ Scrape articles                                  │
│     └→ Synthesize results                                   │
│     → research_summary (markdown)                           │
│     → Save: 02_research/*                                   │
│                                                              │
│  4. Outside View                                            │
│     ├→ Load prompt template                                 │
│     ├→ Fill with question details                           │
│     ├→ LLM call (Sonnet 4)                                  │
│     └→ Parse response                                       │
│     → base_rate, reference_classes                          │
│     → Save: 03_outside_view/*                               │
│                                                              │
│  5. Inside View (Ensemble)                                  │
│     ├→ Load agent configs                                   │
│     ├→ Load prompt template                                 │
│     ├→ For each agent (parallel):                           │
│     │   ├→ Fill template with role                          │
│     │   ├→ LLM call (Sonnet 4)                              │
│     │   └→ Parse prediction                                 │
│     └→ Collect AgentPrediction objects                      │
│     → agent_predictions list                                │
│     → Save: 04_inside_view/{agent}/*                        │
│                                                              │
│  6. Aggregation                                             │
│     ├→ Calculate statistics                                 │
│     └→ Weighted average                                     │
│     → final_prediction                                      │
│     → Save: 04_inside_view/aggregation.json                 │
│                                                              │
│  7. Calibration                                             │
│     ├→ Run automated checks                                 │
│     └→ Generate recommendation                              │
│     → calibration_result                                    │
│     → Save: 05_calibration/*                                │
│                                                              │
│  8. Submission                                              │
│     ├→ Format prediction                                    │
│     └→ POST to Metaculus API (if production mode)           │
│     → submission_result                                     │
│     → Save: 06_submission/*                                 │
│                                                              │
│  9. Report Generation                                       │
│     ├→ Compile all data                                     │
│     └→ Generate markdown report                             │
│     → reasoning_report                                      │
│     → Save: 06_submission/reasoning_report.md               │
│                                                              │
│  10. Metadata & Database                                    │
│      ├→ Calculate costs & timing                            │
│      ├→ Save metadata.json                                  │
│      └→ Insert into SQLite database                         │
│      → Complete artifact directory                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
    ↓
Return result dict to main.py
    ↓
Print summary to console
```

---

## Key Design Principles

1. **Everything is persisted** - No intermediate outputs are lost; complete reproducibility

2. **Parallel execution** - Research sources and ensemble agents run concurrently for speed

3. **Graceful degradation** - Pipeline continues even if individual components fail

4. **Mode-aware configuration** - Single config file supports testing and production

5. **Type-agnostic orchestration** - Same pipeline handles binary/numeric/multiple-choice

6. **Cost tracking** - Every LLM call is tracked and reported

7. **Artifact-first design** - All outputs saved before being used in next stage

8. **Human-readable artifacts** - Mix of JSON (structured) and Markdown (readable)

9. **Database for analytics** - Structured queries across multiple forecasts

10. **Composable components** - Research, forecasting, aggregation are independent modules

---

## Appendix: API Keys Required

**Minimum (free):**
- `ANTHROPIC_API_KEY` - Claude models ($5 free credits)
- `METACULUS_TOKEN` - Metaculus API (free account)

**Recommended (enhanced research):**
- `SERPER_API_KEY` - Web + News search (2,500 free/month)

**Optional (premium research):**
- `PERPLEXITY_API_KEY` - AI-synthesized research
- `ASKNEWS_CLIENT_ID` + `ASKNEWS_CLIENT_SECRET` - News API (free for tournament participants)
- `OPENROUTER_API_KEY` - Access to multiple LLM providers

---

## Appendix: CLI Examples

**Basic forecast (dry run):**
```bash
python main.py --question 41594
```

**Live forecast (submits):**
```bash
python main.py --question 41594 --mode live
```

**Preview with production models, don't submit:**
```bash
python main.py --question 41594 --mode preview
```

**Forecast all new questions in tournament:**
```bash
python main.py --tournament 32721 --forecast-new --limit 5 --mode live
```

**List tournament questions:**
```bash
python main.py --tournament 32721 --list
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-24
**Codebase Version:** Based on commit 7112510
