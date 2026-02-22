# CLAUDE.md - Metaculus AI Forecasting Bot

## Project Overview

AI-powered forecasting bot for Metaculus prediction tournaments. Uses a 5-agent ensemble pipeline (based on Panshul42's Q2 tournament-winning approach) to generate calibrated probability forecasts.

**Competition:** Metaculus AI Forecasting Benchmark - bots compete on 300+ real-world questions for $30k+ prizes.

## Quick Start

```bash
# Install dependencies
poetry install

# Set up environment (copy and edit .env)
cp .env.template .env
# Required: OPENROUTER_API_KEY, METACULUS_TOKEN
# Optional: SERPER_API_KEY, ASKNEWS_CLIENT_ID, ASKNEWS_CLIENT_SECRET, FRED_API_KEY

# Run a forecast (test mode: fast models, no submission)
python main.py --question 41594 --mode test

# Run a forecast (preview mode: quality models, no submission)
python main.py --question 41594 --mode preview

# Run a forecast (live mode: quality models, submits to Metaculus)
python main.py --question 41594 --mode live

# List tournament questions
python main.py --tournament 32721 --list

# Forecast all unforecasted questions
python main.py --tournament 32721 --forecast-unforecasted --limit 5

# Verbose logging
python main.py --question 41594 --mode test --verbose
```

### Automated Forecasting (GitHub Actions)

The bot runs automatically via `.github/workflows/run-bot.yaml` every 30 minutes using `run_bot.py`:

```bash
# Forecast new tournament questions only (always uses live mode)
python run_bot.py --tournament 32916 --question-selection new-only

# Re-forecast questions older than N days
python run_bot.py --tournament 32916 --question-selection reforecast --reforecast-threshold-days 7
```

### Forecast Tracking

Compare your forecasts against community consensus to identify systematic biases:

```bash
# Track forecasts for tournament 32916 (spring-aib-2026)
poetry run python scripts/track_forecasts.py --tournament 32916

# Custom output file
poetry run python scripts/track_forecasts.py --tournament 32916 --output data/tracking/spring_aib_2026.json

# Quiet mode (just save, minimal output)
poetry run python scripts/track_forecasts.py --tournament 32916 --quiet
```

Output is saved to `data/tracking/<tournament_id>.json` and progressively updated on each run.

### Score Tracking

Metaculus locked down their API in Feb 2026 — `resolution` and `aggregations` fields now return `null`. These scripts work around the lockdown using a combination of the API (which still returns `score_data`) and browser scraping (for resolution values). They work with any tracking file.

**Data files:** `data/tracking/minibench.json`, `data/tracking/32916.json`

```bash
# Step 1: Fetch latest score data from the API (scores are still available)
poetry run python scripts/update_score_tracking.py                              # defaults to minibench
poetry run python scripts/update_score_tracking.py --tracking-file data/tracking/32916.json

# Step 2: Scrape resolution values for any newly resolved questions
# (Opens a headed browser — Cloudflare blocks headless requests)
poetry run python scripts/scrape_resolutions.py                                 # defaults to minibench
poetry run python scripts/scrape_resolutions.py --tracking-file data/tracking/32916.json

# Step 3: Generate the score scatter plot
poetry run python scripts/plot_score_scatter.py                                 # defaults to minibench
poetry run python scripts/plot_score_scatter.py --tracking-file data/tracking/32916.json
```

**Typical workflow:** Run step 1 first (fast, API-only), then step 2 only if there are new resolutions to scrape (slower, needs browser), then step 3 to visualize.

### Adding New Forecasts to Tracking Files

When new questions are forecasted (via `run_bot.py` or `main.py`), they need to be added to the tracking JSON files so the ensemble diversity report can include community comparison data. The Metaculus API no longer returns community predictions, so this must be done via browser scraping.

**Tracking files:**
- `data/tracking/32916.json` — Spring AIB 2026 tournament
- `data/tracking/minibench.json` — All MiniBench rounds (any tournament ID with slug "minibench")
- `data/tracking/other.json` — Standalone questions and other tournaments

**Step 1: Create skeleton entries for new questions**

For each new forecast artifact directory (e.g., `data/42200_20260219_120000/`), read `question.json` to get the question metadata, then add a skeleton entry to the appropriate tracking file:

```json
{
  "question_id": 42200,
  "question_title": "...",
  "question_type": "binary",
  "question_url": "https://www.metaculus.com/questions/42200/",
  "forecast_timestamp": "2026-02-19T12:00:00+00:00",
  "snapshot_timestamp": null,
  "num_forecasters": null,
  "resolved": false,
  "resolution": null,
  "comparison": null,
  "score_data": null
}
```

Note: The question type is at `question.json → question.type` (nested), not the top-level `type` field.

**Step 2: Scrape community data via Chrome (Claude in Chrome MCP)**

For each question without comparison data, navigate to the Metaculus page and run the JS extractor:

1. Navigate to `https://www.metaculus.com/questions/{id}/`
2. Wait 5 seconds for JS to render
3. Run the JS extractor (below) to get community predictions, score data, and resolution status
4. Parse the output and update the tracking JSON entry with the `comparison` object

**JS Extractor:**
```javascript
const scripts=[...document.querySelectorAll('script')];let d='';for(const s of scripts)if(s.textContent.includes('self.__next_f'))d+=s.textContent;const r={};const pt=document.body.innerText;const rm=pt.match(/RESOLVED\s*\n\s*(.+)/);r.res=rm?rm[1].trim():null;const tm=d.match(/\\?"type\\?":\\?"(binary|numeric|multiple_choice|date|discrete)\\?"/);r.type=tm?tm[1]:null;const om=d.match(/\\?"options\\?":\[([^\]]+)\]/);if(om)r.opts=om[1].replace(/\\\\"/g,'"').replace(/"/g,'');const bm=d.match(/\\?"centers\\?":\[([^\]]*)\]/);if(bm)r.centers=bm[1];const fvm=d.match(/\\?"forecast_values\\?":\[([^\]]+)\]/);if(fvm){const vals=fvm[1].split(',');if(vals.length<=10)r.fv=fvm[1]}function pV(s){s=s.replace(/%$/,'').replace(/,/g,'');const m={'M':1e6,'K':1e3,'B':1e9,'T':1e12};const v=parseFloat(s);const u=s.slice(-1).toUpperCase();return m[u]?v*m[u]:v}function gQ(l){let m=pt.match(new RegExp(l+'\\t[\\d.]+%\\t([\\d.,%MKBTmkbt]+)\\t([\\d.,%MKBTmkbt]+)\\t([\\d.,%MKBTmkbt]+)\\t[\\d.]+%'));if(!m)m=pt.match(new RegExp(l+'\\t([\\d.,%MKBTmkbt]+)\\t([\\d.,%MKBTmkbt]+)\\t([\\d.,%MKBTmkbt]+)\\t[\\d.]+%'));if(!m)m=pt.match(new RegExp(l+'\\t[\\d.]+%\\t([\\d.,%MKBTmkbt]+)\\t([\\d.,%MKBTmkbt]+)\\t([\\d.,%MKBTmkbt]+)'));return m?{p25:pV(m[1]),med:pV(m[2]),p75:pV(m[3])}:null}r.cq=gQ('Community');r.mq=gQ('My Prediction');const mi=d.indexOf('my_forecasts');if(mi>-1){const a=d.substring(mi);const sm=a.match(/score_data\\?":\{\\?"baseline_score\\?":([-\d.eE+]+),\\?"peer_score\\?":([-\d.eE+]+),\\?"coverage\\?":([-\d.eE+]+),\\?"relative_legacy_score\\?":([-\d.eE+]+),\\?"weighted_coverage\\?":([-\d.eE+]+),\\?"spot_peer_score\\?":([-\d.eE+]+),\\?"spot_baseline_score\\?":([-\d.eE+]+)/);if(sm)r.sd={bs:+sm[1],ps:+sm[2],cov:+sm[3],rls:+sm[4],wc:+sm[5],sps:+sm[6],sbs:+sm[7]}}const fc=d.match(/forecaster_count\\?":\s*(\d+)/);if(fc)r.fc=+fc[1];JSON.stringify(r)
```

**Extractor output fields:**
- `type`: question type (binary, numeric, multiple_choice, discrete)
- `fv`: forecast_values array (community P(No)/P(Yes) for binary, option probs for MC) — only captured when ≤10 values
- `centers`: community centers array (same as fv but from aggregation)
- `cq`/`mq`: Community/My Prediction quartiles `{p25, med, p75}` for numeric/discrete (parsed from visible page text)
- `opts`: option labels for MC questions
- `sd`: score data (7 fields) if available
- `fc`: forecaster count
- `res`: resolution text if resolved

**Comparison format by question type:**

Binary: `{"type": "binary", "my_probability": X, "community_probability": Y, "difference": X-Y}`
- Community P(Yes) comes from `fv[1]` (second value in forecast_values array)

Numeric/Discrete: `{"type": "numeric", "my_median": X, "community_median": Y, "my_lower_quartile": ..., "my_upper_quartile": ..., "community_lower_quartile": ..., "community_upper_quartile": ..., "median_difference": ..., "my_iqr": ..., "community_iqr": ..., "uncertainty_ratio": ...}`
- Quartiles come from `cq`/`mq` (visible Community/My Prediction rows on the page)

Multiple Choice: `{"type": "multiple_choice", "my_probabilities": {...}, "community_probabilities": {...}, "differences": {...}, "max_difference_option": "...", "max_difference_value": ...}`
- Community probs come from `fv` (forecast_values) array, matched to `opts` labels. Do NOT use `centers` — that is an internal aggregation field and does not match the displayed community prediction.

**Step 3: Regenerate the diversity report**

```bash
poetry run python scripts/ensemble_diversity_report.py
```

Verify "Tracking data: X matched" equals or is close to the total forecast count.

## Architecture

### Forecasting Pipeline

```
Question -> Query Generation -> Search (Historical + Current) -> 5-Agent Ensemble -> Aggregation -> [Supervisor] -> Submit
```

Each question type handler does its own integrated pipeline:
1. **Query Generation** - Generate historical queries (outside view) and current queries (inside view)
2. **Search Execution** - Google/Serper, AskNews, Google Trends, FRED, yFinance, agentic search
3. **Outside View Prediction** - 5 forecasters analyze historical context
4. **Cross-Pollination** - Forecasters share outputs for diverse perspectives
5. **Inside View Prediction** - 5 forecasters refine with current news
6. **Aggregation** - Equal-weighted average of forecaster probabilities
7. **Supervisor (optional)** - If ensemble divergence exceeds threshold, a supervisor agent analyzes disagreements, conducts targeted research, and produces an updated forecast

### 5-Forecaster Ensemble

All forecasters have equal weight (1.0). Quality tier models:
- **Forecaster 1-2**: Claude Sonnet 4.6
- **Forecaster 3**: GPT-5.2
- **Forecaster 4-5**: o3

Cross-pollination structure (creates cross-model diversity):
- Forecaster 1 receives Forecaster 1's outside view output (Sonnet 4.6 ← self)
- Forecaster 2 receives Forecaster 4's outside view output (Sonnet 4.6 ← o3)
- Forecaster 3 receives Forecaster 2's outside view output (GPT-5.2 ← Sonnet 4.6)
- Forecaster 4 receives Forecaster 3's outside view output (o3 ← GPT-5.2)
- Forecaster 5 receives Forecaster 5's outside view output (o3 ← self)

### Question Types

The bot handles three question types with dedicated handlers:
- **Binary** (`src/bot/binary.py`) - Yes/No probability (0-1)
- **Numeric** (`src/bot/numeric.py`) - Continuous values with 201-point CDF
- **Multiple Choice** (`src/bot/multiple_choice.py`) - Probability distributions across options

### Directory Structure

```
metaculus-bot/
├── .github/workflows/
│   └── run-bot.yaml           # GitHub Actions (30-min schedule)
├── src/
│   ├── bot/                   # Core forecasting pipeline
│   │   ├── forecaster.py      # Main orchestrator
│   │   ├── base_forecaster.py # Shared base class for all handlers
│   │   ├── binary.py          # Binary question handler
│   │   ├── numeric.py         # Numeric question handler
│   │   ├── multiple_choice.py # Multiple choice handler
│   │   ├── search.py          # Research pipeline (Google, AskNews, FRED, yFinance, agentic)
│   │   ├── prompts.py         # All prompt templates (incl. supervisor)
│   │   ├── extractors.py      # Probability extraction logic
│   │   ├── handler_mixin.py   # Shared handler methods
│   │   ├── cdf.py             # CDF generation and interpolation
│   │   ├── supervisor.py      # Supervisor agent for disagreement resolution
│   │   ├── divergence.py      # Ensemble divergence calculation
│   │   ├── exceptions.py      # Custom exception types
│   │   ├── metrics.py         # Typed metrics dataclasses
│   │   └── content_extractor.py # Web scraping
│   ├── utils/
│   │   ├── llm.py             # LLM client with cost tracking
│   │   └── metaculus_api.py   # Metaculus API wrapper
│   ├── storage/
│   │   ├── artifact_store.py  # Forecast artifact persistence
│   │   ├── database.py        # SQLite analytics DB
│   │   └── report_generator.py # Report generation
│   ├── runner.py              # Shared runner module for batch forecasting
│   └── config.py              # Configuration handling
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   └── unit/                  # 22 test files (see Test Infrastructure below)
├── data/                      # Forecast artifacts and database
├── main.py                    # CLI entry point
├── run_bot.py                 # GitHub Actions entry point
├── config.yaml                # All tunable parameters
└── pyproject.toml             # Poetry dependencies
```

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point (interactive use) |
| `run_bot.py` | Batch/automation entry point (GitHub Actions) |
| `config.yaml` | All tunable parameters (models, ensemble, research, supervisor, LLM) |
| `src/bot/forecaster.py` | Main pipeline orchestrator |
| `src/bot/base_forecaster.py` | Shared base class for all question type handlers |
| `src/bot/binary.py` | Binary question handler |
| `src/bot/numeric.py` | Numeric/continuous question handler |
| `src/bot/multiple_choice.py` | Multiple choice question handler |
| `src/bot/prompts.py` | All prompt templates (incl. supervisor prompts) |
| `src/bot/search.py` | Search pipeline (Google, AskNews, Google Trends, FRED, yFinance, agentic) |
| `src/bot/extractors.py` | Probability/percentile extraction from LLM responses |
| `src/bot/handler_mixin.py` | Shared methods for agent config, model selection |
| `src/bot/cdf.py` | CDF generation and interpolation for numeric questions |
| `src/bot/supervisor.py` | Supervisor agent for ensemble disagreement resolution |
| `src/bot/divergence.py` | Ensemble divergence calculation |
| `src/bot/content_extractor.py` | Web content extraction |
| `src/utils/llm.py` | LLM client with cost tracking (via litellm) |
| `src/utils/metaculus_api.py` | Metaculus API wrapper |
| `src/storage/artifact_store.py` | Saves all intermediate outputs |
| `src/storage/database.py` | SQLite analytics database |
| `src/runner.py` | Shared runner module for batch forecasting |
| `src/config.py` | Configuration resolution with mode handling |

### Prompts

All prompts are in `src/bot/prompts.py`. Key prompts per question type:

**Binary:**
- `BINARY_PROMPT_HISTORICAL` - Generate historical search queries
- `BINARY_PROMPT_CURRENT` - Generate current news queries
- `BINARY_OUTSIDE_VIEW_PROMPT` - Outside view prediction
- `BINARY_INSIDE_VIEW_PROMPT` - Inside view prediction (with calibration checklist)

**Numeric:** `NUMERIC_PROMPT_HISTORICAL`, `NUMERIC_PROMPT_CURRENT`, `NUMERIC_OUTSIDE_VIEW_PROMPT`, `NUMERIC_INSIDE_VIEW_PROMPT`

**Multiple Choice:** `MULTIPLE_CHOICE_PROMPT_HISTORICAL`, `MULTIPLE_CHOICE_PROMPT_CURRENT`, `MULTIPLE_CHOICE_OUTSIDE_VIEW_PROMPT`, `MULTIPLE_CHOICE_INSIDE_VIEW_PROMPT`

**Supervisor:**
- `SUPERVISOR_ANALYSIS_PROMPT` - Analyze ensemble disagreement
- `BINARY_SUPERVISOR_UPDATE_PROMPT` / `NUMERIC_SUPERVISOR_UPDATE_PROMPT` / `MULTIPLE_CHOICE_SUPERVISOR_UPDATE_PROMPT` - Produce updated forecast per question type

Prompts use Python's `.format()` with variables like `{title}`, `{today}`, `{context}`, `{resolution_criteria}`.

## Configuration

All tunable parameters are in `config.yaml`:

- **Models**: `models.fast` and `models.quality` for utility tasks (query generation, article summarization, agentic search)
- **Ensemble**: `ensemble.fast` and `ensemble.quality` define the 5 forecasters
- **Research**: Google, AskNews, Google Trends, FRED, yFinance, agentic search settings
- **LLM**: Temperatures per task type, max_output_tokens, timeout
- **Supervisor**: Optional supervisor agent for ensemble disagreement

### Mode Selection

The `--mode` flag controls model tier and submission behavior:

| Mode | Models | Submits | Use Case |
|------|--------|---------|----------|
| `test` | fast (Haiku) | No | Quick testing (~$0.09/forecast) |
| `preview` | quality | No | Quality testing |
| `live` | quality | Yes | Live forecasting (~$0.70/forecast) |

### Research Pipeline

Research is integrated into each handler. The pipeline:
1. Generate historical queries (for outside view context)
2. Generate current queries (for inside view context)
3. Execute searches via Google (Serper), AskNews, Google Trends, FRED, and yFinance
4. Scrape URLs found in question text (resolution_criteria, fine_print, description)
5. Optionally run agentic search (iterative LLM-guided research with access to FRED + yFinance)
6. Extract and summarize article content

**Configuration in `config.yaml`:**
```yaml
research:
  google_enabled: true
  google_max_results: 10
  asknews_enabled: true
  asknews_max_results: 10
  asknews_hours_back: 72
  agentic_search_enabled: true
  agentic_search_max_steps: 7
  google_trends_enabled: true
  fred_enabled: true
  yfinance_enabled: true
  question_url_scraping_enabled: true
  question_url_max_scrape: 5
  scraping_enabled: true
  max_articles_to_scrape: 10
  max_content_length: 15000
```

### AskNews Integration

AskNews provides news search. Free for Metaculus tournament participants (3k+ calls/month).

**Setup:**
1. Sign up at https://my.asknews.app with your Metaculus-registered email
2. Create API credentials with **all scopes**: news, chat, stories, analytics
3. Add to `.env`: `ASKNEWS_CLIENT_ID` and `ASKNEWS_CLIENT_SECRET`

## Artifacts

Every forecast saves artifacts to `data/{question_id}_{timestamp}/`:

```
data/41594_20260126_230107/
├── 00_question.json                    # Raw Metaculus API response
├── 01_analysis.json                    # Question metadata & analysis
├── 02_research/
│   ├── query_historical_prompt.md      # Prompt for historical queries
│   ├── query_historical.md             # Generated historical queries
│   ├── query_current_prompt.md         # Prompt for current queries
│   ├── query_current.md                # Generated current queries
│   ├── historical_search.json          # Search results (Google/AskNews)
│   └── current_search.json             # Search results (Google/AskNews)
├── ensemble/
│   ├── outside_view_prompt.md          # Shared outside view prompt
│   ├── forecaster_1_outside_view.md    # Forecaster 1 outside view response
│   ├── forecaster_1_inside_view.md     # Forecaster 1 inside view response
│   ├── forecaster_1.json               # Extracted: {probability: 0.52}
│   ├── forecaster_2_outside_view.md
│   ├── forecaster_2_inside_view.md
│   ├── forecaster_2.json
│   ├── forecaster_3_outside_view.md
│   ├── forecaster_3_inside_view.md
│   ├── forecaster_3.json
│   ├── forecaster_4_outside_view.md
│   ├── forecaster_4_inside_view.md
│   ├── forecaster_4.json
│   ├── forecaster_5_outside_view.md
│   ├── forecaster_5_inside_view.md
│   ├── forecaster_5.json
│   └── aggregation.json                # Final: {final_probability: 0.545}
├── 06_submission/
│   ├── final_prediction.json           # Submitted prediction
│   └── api_response.json               # Metaculus API response
└── metadata.json                       # Costs, timing, config hash
```

## Error Handling

The pipeline fails loudly if all agents fail to extract valid probabilities:
- **Binary**: Raises `RuntimeError` instead of defaulting to 0.5
- **Multiple Choice**: Raises `RuntimeError` instead of uniform distribution
- **Numeric**: Raises `RuntimeError` if fewer than 3 valid CDFs

This prevents submitting meaningless forecasts.

## Development Notes

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/unit/test_extractors.py
pytest tests/unit/test_cdf_generation.py

# Run with verbose output
pytest tests/ -v
```

### Code Formatting

Run ruff to lint and format code before committing:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Test Infrastructure

22 test files in `tests/unit/`. Key test files:
- `test_extractors.py` - Probability/percentile extraction (100+ tests)
- `test_cdf_generation.py` - 201-point CDF generation
- `test_base_forecaster.py` - Base forecaster with mocked LLM pipeline
- `test_handler_mixin.py` - Handler mixin methods
- `test_divergence.py` - Ensemble divergence calculation
- `test_supervisor.py` - Supervisor agent
- `test_fred_search.py` - FRED integration
- `test_yfinance_search.py` - yFinance integration
- `test_question_url_extraction.py` - URL scraping from question text
- `test_runner.py` - Batch runner error handling
- `test_config.py` - Configuration resolution

Fixtures in `conftest.py` provide sample LLM responses for:
- Binary responses (standard, decimal, extreme, missing)
- Multiple choice responses (3-option, 4-option)
- Numeric percentile responses

### GitHub Actions

The bot runs automatically via `.github/workflows/run-bot.yaml`:
- **Schedule**: Every 30 minutes
- **Entry point**: `run_bot.py`
- **Strategy**: `new-only` (forecasts new questions only)
- **Tournaments**: 32916 (spring-aib-2026) and MiniBench

**Required secrets:**
- `OPENROUTER_API_KEY` - For all LLM calls
- `METACULUS_TOKEN` - For Metaculus API
- `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET` - For news search
- `SERPER_API_KEY` - For Google search (optional but recommended)
- `FRED_API_KEY` - For FRED economic data (optional)

### Database

SQLite at `data/forecasts.db` for analytics with three tables:

**forecasts** - Main predictions:
- `id`, `question_id`, `timestamp`, `question_type`, `question_title`
- `final_prediction`, `actual_outcome`, `brier_score`
- `total_cost`, `config_hash`, `tournament_id`

**agent_predictions** - Individual agent outputs:
- `forecast_id`, `agent_id`, `model`, `weight`, `prediction`, `reasoning_length`

**research_sources** - Research tracking:
- `forecast_id`, `source_type`, `query`, `num_results`

### Common Issues

1. **All agents failed**: Check LLM API keys and model availability. The pipeline now fails loudly rather than submitting fallback values.

2. **Search failures**: Verify `SERPER_API_KEY` and `ASKNEWS_*` credentials. Searches gracefully degrade if APIs are unavailable.

3. **Cost tracking**: All LLM calls tracked via `src/utils/llm.py`. Check `metadata.json` for per-forecast costs.

## API Keys

**Required in `.env`:**
- `OPENROUTER_API_KEY` - All LLM calls go through OpenRouter
- `METACULUS_TOKEN` - Metaculus API

**Optional:**
- `SERPER_API_KEY` - Google search (free tier: 2,500/month)
- `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET` - AskNews (free via Metaculus tournament)
- `FRED_API_KEY` - Federal Reserve Economic Data (free: https://fred.stlouisfed.org/docs/api/api_key.html)

## Code Conventions

### Protected Vocabulary

When refactoring or renaming, do NOT change the following terms:

**Metaculus-Specific Terms** (defined by the platform):
- `binary`, `numeric`, `multiple_choice` - Question type identifiers from Metaculus API
- `tournament`, `question` - Core Metaculus entities
- `resolution_criteria`, `fine_print`, `background_info` - Metaculus question fields

**Domain Terms** (forecasting methodology):
- `forecaster` / `ensemble` - The 5-agent prediction system
- `outside_view` / `inside_view` - Two-stage prediction approach (historical vs current context)
- `cross_pollination` - Sharing outputs between forecasters for diversity
- `aggregation` - Combining forecaster predictions into final probability
- `CDF` - Cumulative distribution function for numeric questions

**Codebase Conventions** (project preferences):
- `forecaster` - Preferred term for ensemble members (avoid `agent` for this purpose)
- Explicit question type prefixes in prompts: `BINARY_*`, `NUMERIC_*`, `MULTIPLE_CHOICE_*`
- Mode names: `test`, `preview`, `live`

When doing naming reviews, focus on:
- Ambiguous variable names (`data`, `result`, `info`, `item`)
- Inconsistent naming across similar concepts
- Abbreviations that could be spelled out
- Boolean variables that don't read as predicates
- Function names that don't describe what they return

### Adding New Question Types

1. Create handler in `src/bot/` inheriting from `BaseForecaster`
2. Add prompts to `src/bot/prompts.py` (HISTORICAL, CURRENT, OUTSIDE_VIEW_PROMPT, INSIDE_VIEW_PROMPT)
3. Add extraction logic to `src/bot/extractors.py`
4. Register in `src/bot/forecaster.py`

### LLM Calls

All LLM calls go through `src/utils/llm.py`:
```python
from src.utils.llm import LLMClient
client = LLMClient(cost_tracker)
response = await client.generate(prompt, model="openrouter/anthropic/claude-sonnet-4.5")
```

### Artifact Storage

Use `ArtifactStore` to save intermediate outputs:
```python
store = ArtifactStore(base_dir)
artifacts = store.create_forecast_artifacts(question_id)
store.save_query_generation(artifacts, "historical", prompt, output)
store.save_aggregation(artifacts, aggregation_data)
```

## Legacy Code

The previous pipeline (role-based agents, separate research phase, calibration checklist) is available in git history. The current implementation is based on Panshul42's tournament-winning approach.
