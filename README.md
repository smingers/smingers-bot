# Metaculus AI Forecasting Bot

AI-powered forecasting bot for the Metaculus AI Forecasting Benchmark competition.

## Acknowledgements

The forecasting pipeline and prompts in this bot are based on [Panshul42's Metaculus-AI-Benchmark-2025-Q2](https://github.com/Panshul42/Metaculus-AI-Benchmark-2025-Q2), which placed 1st in the Q2 2025 tournament. It adapts their 5-agent ensemble approach with cross-pollination for this implementation.

## Setup

1. Copy `.env.template` to `.env` and fill in your API keys
2. Install dependencies: `poetry install`
3. Run a test forecast: `poetry run python main.py --question <id> --dry-run`

## Usage

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

## Configuration

All tunable parameters are in `config.yaml`.
