# CLAUDE.md - Metaculus AI Forecasting Bot

## Project Overview

AI-powered forecasting bot for Metaculus prediction tournaments. Uses a multi-stage pipeline with ensemble LLM agents to generate calibrated probability forecasts.

**Competition:** Metaculus AI Forecasting Benchmark - bots compete on 300+ real-world questions for $30k+ prizes.

## Quick Start

```bash
# Install dependencies
poetry install

# Set up environment (copy and edit .env)
cp .env.template .env
# Add: ANTHROPIC_API_KEY, METACULUS_TOKEN

# Run a forecast (dry run with cheap models)
python main.py --question 41594 --mode dry_run

# Run a forecast (dry run with production models)
python main.py --question 41594 --mode dry_run_heavy

# Run a forecast (submit with production models)
python main.py --question 41594 --mode production

# List tournament questions
python main.py --tournament 32721 --list

# Forecast all new questions
python main.py --tournament 32721 --forecast-new --limit 5

# Verbose logging
python main.py --question 41594 --mode dry_run --verbose
```

### Automated Forecasting (GitHub Actions)

The bot runs automatically via `.github/workflows/run-bot.yaml` every 4 hours using `run_bot.py`:

```bash
# Forecast new AIB tournament questions only
python run_bot.py --mode aib

# Re-forecast questions older than N days
python run_bot.py --mode reforecast --reforecast-days 7
```

## Architecture

### Forecasting Pipeline

```
Question Intake → Research → Outside View (Base Rate) → Inside View (Ensemble) → Aggregation → Submit
```

1. **Research Phase** (`src/research/searcher.py`) - Gathers context via LLM knowledge, Perplexity, AskNews, web search
2. **Outside View** (`src/bot/prompts/outside_view*.md`) - Establishes base rate from reference classes
3. **Inside View** (`src/bot/prompts/inside_view*.md`) - Adjusts base rate with current evidence via ensemble agents
4. **Aggregation** (`src/ensemble/aggregator.py`) - Weighted average of agent predictions

### Question Types

The bot handles three question types with dedicated handlers:
- **Binary** (`src/bot/binary.py`) - Yes/No probability (0-1)
- **Numeric** (`src/bot/numeric.py`) - Continuous values with 201-point CDF
- **Multiple Choice** (`src/bot/multiple_choice.py`) - Probability distributions across options

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point (interactive use) |
| `run_bot.py` | Batch/automation entry point (GitHub Actions) |
| `config.yaml` | All tunable parameters (models, weights, prompts) |
| `src/bot/forecaster.py` | Main pipeline orchestrator |
| `src/bot/binary.py` | Binary question handler |
| `src/bot/numeric.py` | Numeric/continuous question handler |
| `src/bot/multiple_choice.py` | Multiple choice question handler |
| `src/bot/prompts/*.md` | Prompt templates (type-specific) |
| `src/ensemble/aggregator.py` | Weighted model aggregation |
| `src/research/searcher.py` | Multi-source research orchestration |
| `src/research/asknews_searcher.py` | AskNews-specific integration with caching |
| `src/research/extractor.py` | Web content extraction (Trafilatura) |
| `src/utils/llm.py` | LLM client with cost tracking |
| `src/utils/metaculus_api.py` | Metaculus API wrapper |
| `src/storage/artifact_store.py` | Saves all intermediate outputs |
| `src/storage/database.py` | SQLite analytics database |
| `src/storage/report_generator.py` | Markdown report generation |

### Prompt Templates

Prompts use Python's `.format()` for variable substitution. **Important:** Example placeholders use square brackets `[X]` to avoid conflicts with format variables `{variable}`.

```markdown
# In prompts, these are format variables (will be replaced):
{base_rate}, {question_title}, {research_summary}

# These are example placeholders (won't be replaced):
[UP/DOWN], [X], [+/- X]
```

**Type-specific prompts** in `src/bot/prompts/`:
- `outside_view.md` / `inside_view.md` - Binary questions
- `outside_view_numeric.md` / `inside_view_numeric.md` - Numeric questions
- `outside_view_multiple_choice.md` / `inside_view_multiple_choice.md` - Multiple choice
- `calibration_checklist.md` - Final calibration checks

## Configuration

All tunable parameters are in `config.yaml`:

- **Models**: `models.cheap` (testing) and `models.production` (quality) tiers
- **Ensemble**: `ensemble.cheap` and `ensemble.production` agent configurations
- **Research**: Enable/disable sources (llm_knowledge, perplexity, asknews, asknews_wiki, claude_web_search, web_search, google_news, article_scraping)
- **Iterative Research**: `research.iterative.enabled` for agentic search (LLM identifies gaps and generates follow-up queries)
- **Submission**: `dry_run: true` for testing without submitting

### Mode Selection

The `--mode` flag controls model tier and submission behavior:

| Mode | Models | Submits | Use Case |
|------|--------|---------|----------|
| `dry_run` | cheap | No | Quick testing |
| `dry_run_heavy` | production | No | Quality testing |
| `production` | production | Yes | Live forecasting |

### Iterative Research

Based on the AIA Forecaster paper, iterative/agentic search improves forecast accuracy. The LLM:
1. Runs initial search
2. Analyzes results and identifies information gaps
3. Generates targeted follow-up queries
4. Repeats until confident or max iterations reached

**Configuration in `config.yaml`:**
```yaml
research:
  iterative:
    enabled: true              # Enable iterative research
    max_iterations: 3          # Maximum research iterations
    confidence_threshold: 0.7  # Stop when LLM confidence reaches this level
    queries_per_iteration: 2   # Number of follow-up queries per iteration
```

**Note:** Iterative research uses more API calls. With AskNews free tier, you may hit rate limits. Consider:
- Setting `max_iterations: 2` for testing
- Disabling iterative research for rapid iteration on other parts of the pipeline

### AskNews Integration

AskNews provides news search and AI-powered forecasting. Free for Metaculus tournament participants (3k+ calls/month).

**Setup:**
1. Sign up at https://my.asknews.app with your Metaculus-registered email
2. Create API credentials with **all scopes**: news, chat, stories, analytics
3. Add to `.env`: `ASKNEWS_CLIENT_ID` and `ASKNEWS_CLIENT_SECRET`

**Features in `config.yaml`:**
```yaml
- type: "asknews"
  enabled: true
  max_results: 10           # Articles per search
  hours_back: 72            # How far back to search

  # Forecast endpoint (deep API call - uses more credits)
  forecast_enabled: false   # Enable for AskNews probability forecasts
  forecast_lookback: 14     # Days of news to analyze
  forecast_articles: 15     # Articles to use for forecast
  forecast_model: "gpt-4.1-2025-04-14"  # Model for forecast
  forecast_web_search: true # Enable web search in forecast
```

**Programmatic access:**
```python
from src.research.searcher import ResearchSearcher

searcher = ResearchSearcher(config)

# News search
results = await searcher._search_asknews(queries=["topic query"])

# AI forecast (returns probability, reasoning, sources, timeline)
forecast = await searcher.get_asknews_forecast(
    question_title="Will X happen?",
    question_text="Full question details...",
    resolution_criteria="Resolves YES if..."
)
```

### Cost Management

Model tiers are configured in `config.yaml` under `models.cheap` and `models.production`. The `--mode` flag selects which tier to use:

```bash
# Uses cheap models (fast, low cost)
python main.py --question 41594 --mode dry_run

# Uses production models (higher quality)
python main.py --question 41594 --mode production
```

### AskNews Cache Modes

Control AskNews caching behavior:

```yaml
- type: "asknews"
  cache_mode: "use_cache_with_fallback"  # Options: no_cache, use_cache, use_cache_with_fallback
```

## Artifacts

Every forecast saves complete artifacts to `data/{question_id}_{timestamp}/`:

```
data/41594_20260123_203130/
├── 00_question.json           # Raw question from Metaculus
├── 01_analysis.json           # Classification
├── 02_research/
│   ├── queries_generated.json
│   ├── llm_knowledge.json
│   └── synthesis.md
├── 03_outside_view/
│   ├── prompt.md
│   ├── response.md
│   └── extracted.json
├── 04_inside_view/
│   ├── forecaster/
│   │   ├── prompt.md
│   │   ├── response.md
│   │   └── extracted.json
│   └── aggregation.json
├── 05_calibration/
├── 06_submission/
│   ├── final_prediction.json
│   └── reasoning_report.md
└── metadata.json              # Config, costs, timing
```

## Development Notes

### Running Tests
```bash
pytest tests/
```

### GitHub Actions

The bot runs automatically via `.github/workflows/run-bot.yaml`:
- **Schedule**: Every 4 hours
- **Entry point**: `run_bot.py` (not main.py)
- **Mode**: `aib` for new questions only

### Database
SQLite at `data/forecasts.db` for analytics queries:
- `forecasts` - main predictions table
- `agent_predictions` - individual agent outputs
- `research_sources` - research metadata

Managed by `src/storage/database.py` with dataclasses:
- `ForecastRecord`, `AgentPredictionRecord`, `ResearchSourceRecord`

### Common Issues

1. **Template KeyError** (e.g., `'direction'`): Prompt templates have format variables that Python's `.format()` tries to replace. Use square brackets `[X]` for examples, curly braces `{variable}` only for actual variables.

2. **API Errors**: Check `.env` has correct keys. AskNews requires tournament registration for free access.

3. **Cost tracking**: All LLM calls tracked via `src/utils/llm.py`. Check `metadata.json` for per-forecast costs.

## API Keys

Required in `.env`:
- `ANTHROPIC_API_KEY` - Claude models
- `METACULUS_TOKEN` - Metaculus API

Optional:
- `OPENROUTER_API_KEY` - OpenRouter for multi-provider access
- `PERPLEXITY_API_KEY` - Perplexity search
- `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET` - AskNews (free via Metaculus, requires all scopes)
- `SERPER_API_KEY` - Web search (free tier: 2,500/month)

## Additional Documentation

See these files for more details:
- `PIPELINE_WORKFLOW.md` - Detailed pipeline workflow
- `PROMPTS.md` - Prompt documentation
- `.env.template` - Complete environment variable reference
