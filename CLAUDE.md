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
# Optional: SERPER_API_KEY, ASKNEWS_CLIENT_ID, ASKNEWS_CLIENT_SECRET

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

## Architecture

### Forecasting Pipeline

```
Question -> Query Generation -> Search (Historical + Current) -> 5-Agent Ensemble -> Aggregation -> Submit
```

Each question type handler does its own integrated pipeline:
1. **Query Generation** - Generate historical queries (outside view) and current queries (inside view)
2. **Search Execution** - Google/Serper, AskNews, agentic search
3. **Outside View Prediction** - 5 forecasters analyze historical context
4. **Cross-Pollination** - Forecasters share outputs for diverse perspectives
5. **Inside View Prediction** - 5 forecasters refine with current news
6. **Aggregation** - Equal-weighted average of forecaster probabilities

### 5-Forecaster Ensemble

All forecasters have equal weight (1.0). Quality tier models:
- **Forecaster 1-2**: Claude Sonnet 4.5
- **Forecaster 3**: o3-mini-high
- **Forecaster 4-5**: o3

Cross-pollination structure (creates cross-model diversity):
- Forecaster 1 receives Forecaster 1's outside view output (Sonnet 4.5 ← self)
- Forecaster 2 receives Forecaster 4's outside view output (Sonnet 4.5 ← o3)
- Forecaster 3 receives Forecaster 2's outside view output (o3-mini-high ← Sonnet 4.5)
- Forecaster 4 receives Forecaster 3's outside view output (o3 ← o3-mini-high)
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
│   │   ├── binary.py          # Binary question handler
│   │   ├── numeric.py         # Numeric question handler
│   │   ├── multiple_choice.py # Multiple choice handler
│   │   ├── search.py          # Research pipeline
│   │   ├── prompts.py         # All prompt templates
│   │   ├── extractors.py      # Probability extraction logic
│   │   ├── handler_mixin.py   # Shared handler methods
│   │   └── content_extractor.py # Web scraping
│   ├── utils/
│   │   ├── llm.py             # LLM client with cost tracking
│   │   └── metaculus_api.py   # Metaculus API wrapper
│   ├── storage/
│   │   ├── artifact_store.py  # Forecast artifact persistence
│   │   ├── database.py        # SQLite analytics DB
│   │   └── report_generator.py # Report generation
│   └── config.py              # Configuration handling
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   └── unit/
│       ├── test_extractors.py # Extraction logic tests
│       ├── test_cdf_generation.py # CDF tests
│       ├── test_runner.py     # Runner tests
│       └── test_config.py     # Config tests
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
| `config.yaml` | All tunable parameters (models, ensemble, research) |
| `src/bot/forecaster.py` | Main pipeline orchestrator |
| `src/bot/binary.py` | Binary question handler |
| `src/bot/numeric.py` | Numeric/continuous question handler |
| `src/bot/multiple_choice.py` | Multiple choice question handler |
| `src/bot/prompts.py` | All prompt templates |
| `src/bot/search.py` | Search pipeline (Google, AskNews, agentic) |
| `src/bot/extractors.py` | Probability/percentile extraction from LLM responses |
| `src/bot/handler_mixin.py` | Shared methods for agent config, model selection |
| `src/bot/content_extractor.py` | Web content extraction |
| `src/utils/llm.py` | LLM client with cost tracking (via litellm) |
| `src/utils/metaculus_api.py` | Metaculus API wrapper |
| `src/storage/artifact_store.py` | Saves all intermediate outputs |
| `src/storage/database.py` | SQLite analytics database |
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

Prompts use Python's `.format()` with variables like `{title}`, `{today}`, `{context}`, `{resolution_criteria}`.

## Configuration

All tunable parameters are in `config.yaml`:

- **Models**: `models.fast` and `models.quality` for utility tasks (query generation, article summarization, agentic search)
- **Ensemble**: `ensemble.fast` and `ensemble.quality` define the 5 forecasters
- **Research**: Google, AskNews, agentic search settings

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
3. Execute searches via Google (Serper) and AskNews
4. Optionally run agentic search (iterative LLM-guided research)
5. Extract and summarize article content

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

Test files in `tests/unit/`:
- `test_extractors.py` - Probability/percentile extraction (100+ tests)
- `test_cdf_generation.py` - 201-point CDF generation
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
- **Tournament**: 32916 (spring-aib-2026)

**Required secrets:**
- `OPENROUTER_API_KEY` - For all LLM calls
- `METACULUS_TOKEN` - For Metaculus API
- `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET` - For news search
- `SERPER_API_KEY` - For Google search (optional but recommended)

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

1. Create handler in `src/bot/` inheriting from `ForecasterMixin`
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
