# AI Forecasting Bot

AI-powered forecasting bot.

## Acknowledgements

The forecasting pipeline and prompts in this bot were originally based on [Panshul42's Metaculus-AI-Benchmark-2025-Q2](https://github.com/Panshul42/Metaculus-AI-Benchmark-2025-Q2), which placed 1st in the Q2 2025 tournament.

## Setup

Requires Python 3.11+.

1. Copy `.env.template` to `.env` and fill in your API keys
2. Install dependencies: `poetry install`
3. Run a test forecast: `poetry run python main.py --question <id> --mode test`

## Entry points

- **`main.py`** — Interactive and single-question runs: test/preview/live, list questions, `--forecast-unforecasted`. Use for development and one-off forecasts.
- **`run_bot.py`** — Batch automation: forecast new tournament questions only, or reforecast questions older than N days. Used by GitHub Actions; run locally for bulk jobs.

## Usage

```bash
# Install dependencies
poetry install

# Set up environment (copy and edit .env)
cp .env.template .env
# Required: OPENROUTER_API_KEY, METACULUS_TOKEN
# Optional: SERPER_API_KEY, ASKNEWS_CLIENT_ID, ASKNEWS_CLIENT_SECRET, FRED_API_KEY
# See .env.template for full list and descriptions.

# Run a forecast (test mode: cheap models, no submission; ~$0.09/forecast)
python main.py --question 41594 --mode test

# Run a forecast (preview mode: production models, no submission)
python main.py --question 41594 --mode preview

# Run a forecast (live mode: production models, submits to Metaculus; ~$0.70/forecast)
python main.py --question 41594 --mode live

# List tournament questions
python main.py --tournament 32721 --list

# Forecast all unforecasted questions
python main.py --tournament 32721 --forecast-unforecasted --limit 5

# Verbose logging
python main.py --question 41594 --mode test --verbose
```

**Batch (run_bot.py):**

```bash
# Forecast new tournament questions only (same as GitHub Actions)
python run_bot.py --tournament 32916 --question-selection new-only

# Re-forecast questions older than N days
python run_bot.py --tournament 32916 --question-selection reforecast --reforecast-threshold-days 7
```

## Automation

The bot runs automatically via `.github/workflows/run-bot.yaml` every 30 minutes, using `run_bot.py` with `--question-selection new-only` for the configured tournaments.

## Forecast artifacts and tracking

- **Artifacts** — Each forecast writes to `data/{question_id}_{timestamp}/`: question JSON, research outputs, per-forecaster results, aggregation, and submission. See `metadata.json` for cost and timing.
- **SQLite** — Analytics are stored in `data/forecasts.db` (forecasts, agent_predictions, research_sources).
- **Tracking** — To compare forecasts to community and track scores:
  - `poetry run python scripts/track_forecasts.py --tournament <id>` — writes/updates `data/tracking/<tournament_id>.json`
  - `poetry run python scripts/update_score_tracking.py` — fetches score data from the API
  - `poetry run python scripts/scrape_resolutions.py` — scrapes resolution values (browser required; API no longer returns them)
  - `poetry run python scripts/plot_score_scatter.py` — generates the score scatter plot

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/unit/test_extractors.py
pytest tests/unit/test_cdf_generation.py

# Run with verbose output
pytest tests/ -v
```

## Code Quality

```bash
# Manual checks
poetry run ruff check .          # Lint
poetry run ruff check --fix .    # Lint with auto-fix
poetry run ruff format .         # Format

# Pre-commit runs automatically on git commit
# To run manually on all files:
poetry run pre-commit run --all-files
```

## Viewing Forecasts

```bash
# Launch the forecast dashboard (browser-based viewer)
python -m src.dashboard

# Custom port and data directory
python -m src.dashboard --port 8080 --data-dir ./data
```

Default port is 8000. Open http://localhost:8000 in your browser to browse and inspect forecast artifacts.

## Useful Commands

### Check OpenRouter Credits

```bash
# Check remaining credits (limit_remaining is the key field)
poetry run python -c "
import httpx, os
from dotenv import load_dotenv
load_dotenv(override=True)
resp = httpx.get('https://openrouter.ai/api/v1/auth/key',
    headers={'Authorization': f'Bearer {os.getenv(\"OPENROUTER_API_KEY\")}'})
data = resp.json().get('data', {})
print(f'Remaining: \${data.get(\"limit_remaining\", 0):.2f} / \${data.get(\"limit\", 0):.2f}')
print(f'Used: \${data.get(\"limit\", 0) - data.get(\"limit_remaining\", 0):.2f}')
"
```

### Check My Forecasts on Metaculus

```bash
# List questions I've forecasted in a tournament
poetry run python -c "
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from src.utils.metaculus_api import MetaculusClient

async def check():
    async with MetaculusClient() as client:
        forecasts = await client.get_my_forecasts(32916)  # Change tournament ID
        print(f'Forecasted {len(forecasts)} questions: {list(forecasts.keys())}')
asyncio.run(check())
"

# List all open questions in a tournament
poetry run python main.py --tournament 32916 --list
```

## Configuration

All tunable parameters are in `config.yaml`.

## Common issues

- **All agents failed to produce valid predictions** — Check `OPENROUTER_API_KEY` and `METACULUS_TOKEN`; confirm models in `config.yaml` are available on OpenRouter.
- **Search failures or empty research** — Verify `SERPER_API_KEY` (Google) and/or `ASKNEWS_CLIENT_ID` / `ASKNEWS_CLIENT_SECRET`; the pipeline degrades gracefully if APIs are missing but research will be sparse.

## Further reading

- **`CLAUDE.md`** — Architecture, pipeline, question types, directory map, prompts, and code conventions (protected vocabulary, adding question types).
- **`docs/`** — `docs/assessments/README.md` for forecast assessments; `docs/PIPELINE_CHANGELOG.md` for pipeline changes.
