# Metaculus AI Forecasting Bot

AI-powered forecasting bot for the Metaculus AI Forecasting Benchmark competition.

## Acknowledgements

The forecasting pipeline and prompts in this bot are based on [Panshul42's Metaculus-AI-Benchmark-2025-Q2](https://github.com/Panshul42/Metaculus-AI-Benchmark-2025-Q2), which placed 1st in the Q2 2025 tournament. It adapts their 5-agent ensemble approach with cross-pollination for this implementation.

## Setup

1. Copy `.env.template` to `.env` and fill in your API keys
2. Install dependencies: `poetry install`
3. Run a test forecast: `poetry run python main.py --question <id> --mode test`

## Usage

```bash
# Install dependencies
poetry install

# Set up environment (copy and edit .env)
cp .env.template .env
# Required: OPENROUTER_API_KEY, METACULUS_TOKEN
# Optional: SERPER_API_KEY, ASKNEWS_CLIENT_ID, ASKNEWS_CLIENT_SECRET

# Run a forecast (test mode: cheap models, no submission)
python main.py --question 41594 --mode test

# Run a forecast (preview mode: production models, no submission)
python main.py --question 41594 --mode preview

# Run a forecast (live mode: production models, submits to Metaculus)
python main.py --question 41594 --mode live

# List tournament questions
python main.py --tournament 32721 --list

# Forecast all unforecasted questions
python main.py --tournament 32721 --forecast-unforecasted --limit 5

# Verbose logging
python main.py --question 41594 --mode test --verbose
```

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

Then open http://localhost:8000 in your browser to browse and inspect forecast artifacts.

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
