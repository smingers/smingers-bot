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

The bot runs automatically via `.github/workflows/run-bot.yaml` every 30 minutes using `run_bot.py`:

```bash
# Forecast new AIB tournament questions only
python run_bot.py --tournament 32916 --mode aib

# Re-forecast questions older than N days
python run_bot.py --tournament 32916 --mode reforecast --reforecast-days 7
```

## Architecture

### Forecasting Pipeline (Panshul42)

```
Question → Query Generation → Search (Historical + Current) → 5-Agent Ensemble → Aggregation → Submit
```

Each question type handler does its own integrated pipeline:
1. **Query Generation** - Generate historical queries (outside view) and current queries (inside view)
2. **Search Execution** - Google/Serper, AskNews, agentic search
3. **Step 1 (Outside View)** - 5 agents analyze historical context
4. **Cross-Pollination** - Agents share outputs for diverse perspectives
5. **Step 2 (Inside View)** - 5 agents refine with current news
6. **Aggregation** - Equal-weighted average of agent probabilities

### 5-Agent Ensemble

All agents have equal weight (1.0). Production models:
- **Forecaster 1-2**: Claude Sonnet 4.5
- **Forecaster 3**: o3-mini-high
- **Forecaster 4-5**: o3

Cross-pollination structure:
- Agent 1 receives Agent 1's step 1 output
- Agent 2 receives Agent 3's step 1 output
- Agent 3 receives Agent 2's step 1 output
- Agent 4 receives Agent 4's step 1 output
- Agent 5 receives Agent 5's step 1 output

### Question Types

The bot handles three question types with dedicated handlers:
- **Binary** (`src/bot/binary_panshul42.py`) - Yes/No probability (0-1)
- **Numeric** (`src/bot/numeric_panshul42.py`) - Continuous values with 201-point CDF
- **Multiple Choice** (`src/bot/multiple_choice_panshul42.py`) - Probability distributions across options

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point (interactive use) |
| `run_bot.py` | Batch/automation entry point (GitHub Actions) |
| `config.yaml` | All tunable parameters (models, ensemble, research) |
| `src/bot/forecaster.py` | Main pipeline orchestrator |
| `src/bot/binary_panshul42.py` | Binary question handler |
| `src/bot/numeric_panshul42.py` | Numeric/continuous question handler |
| `src/bot/multiple_choice_panshul42.py` | Multiple choice question handler |
| `src/bot/prompts_panshul42.py` | All prompt templates |
| `src/bot/search_panshul42.py` | Search pipeline (Google, AskNews, agentic) |
| `src/bot/content_extractor.py` | Web content extraction |
| `src/utils/llm.py` | LLM client with cost tracking (via litellm) |
| `src/utils/metaculus_api.py` | Metaculus API wrapper |
| `src/storage/artifact_store.py` | Saves all intermediate outputs |
| `src/storage/database.py` | SQLite analytics database |

### Prompts

All prompts are in `src/bot/prompts_panshul42.py`. Key prompts per question type:

**Binary:**
- `BINARY_PROMPT_HISTORICAL` - Generate historical search queries
- `BINARY_PROMPT_CURRENT` - Generate current news queries
- `BINARY_PROMPT_1` - Outside view prediction
- `BINARY_PROMPT_2` - Inside view prediction (with calibration checklist)

**Numeric:** `NUMERIC_PROMPT_HISTORICAL`, `NUMERIC_PROMPT_CURRENT`, `NUMERIC_PROMPT_1`, `NUMERIC_PROMPT_2`

**Multiple Choice:** `MULTIPLE_CHOICE_PROMPT_HISTORICAL`, `MULTIPLE_CHOICE_PROMPT_CURRENT`, `MULTIPLE_CHOICE_PROMPT_1`, `MULTIPLE_CHOICE_PROMPT_2`

Prompts use Python's `.format()` with variables like `{title}`, `{today}`, `{context}`, `{resolution_criteria}`.

## Configuration

All tunable parameters are in `config.yaml`:

- **Models**: `models.cheap` and `models.production` for utility tasks (query generation, article summarization, agentic search)
- **Ensemble**: `ensemble.cheap` and `ensemble.production` define the 5 forecasting agents
- **Research**: Google, AskNews, agentic search settings

### Mode Selection

The `--mode` flag controls model tier and submission behavior:

| Mode | Models | Submits | Use Case |
|------|--------|---------|----------|
| `dry_run` | cheap (Haiku) | No | Quick testing (~$0.09/forecast) |
| `dry_run_heavy` | production | No | Quality testing |
| `production` | production | Yes | Live forecasting (~$0.70/forecast) |

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
  agentic_search_enabled: true
  agentic_search_max_steps: 7
  scraping_enabled: true
  max_articles_to_scrape: 10
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
data/41594_20260123_203130/
├── 00_question.json           # Raw question from Metaculus
├── 01_analysis.json           # Question type classification
├── 02_research/
│   ├── historical_search.json
│   └── current_search.json
├── 04_inside_view/
│   ├── forecaster_1_step1.md
│   ├── forecaster_1_step2.md
│   ├── ...
│   └── aggregation.json
├── 06_submission/
│   └── final_prediction.json
└── metadata.json              # Config, costs, timing
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
pytest tests/
```

### GitHub Actions

The bot runs automatically via `.github/workflows/run-bot.yaml`:
- **Schedule**: Every 30 minutes
- **Entry point**: `run_bot.py`
- **Mode**: `aib` for new questions only
- **Tournament**: 32916 (Seasonal AIB)

**Required secrets:**
- `OPENROUTER_API_KEY` - For all LLM calls
- `METACULUS_TOKEN` - For Metaculus API
- `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET` - For news search
- `SERPER_API_KEY` - For Google search (optional but recommended)

### Database

SQLite at `data/forecasts.db` for analytics:
- `forecasts` - main predictions table
- `agent_predictions` - individual agent outputs

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

## Legacy Code

The previous pipeline (role-based agents, separate research phase, calibration checklist) is available in git history. The current implementation is based on Panshul42's tournament-winning approach.
