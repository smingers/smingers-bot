# Metaculus AI Forecasting Bot

AI-powered forecasting bot for the Metaculus AI Forecasting Benchmark competition.

## Acknowledgements

The forecasting pipeline and prompts in this bot are based on [Panshul42's Metaculus-AI-Benchmark-2025-Q2](https://github.com/Panshul42/Metaculus-AI-Benchmark-2025-Q2), which placed 1st in the Q2 2025 tournament. We've adapted their 5-agent ensemble approach with cross-pollination for this implementation.

## Setup

1. Copy `.env.template` to `.env` and fill in your API keys
2. Install dependencies: `poetry install`
3. Run a test forecast: `poetry run python main.py --question <id> --dry-run`

## Usage

```bash
# Forecast a specific question (dry run - no submission)
poetry run python main.py --question 12345 --dry-run

# List questions in a tournament
poetry run python main.py --tournament 32721 --list

# Forecast all new questions in a tournament
poetry run python main.py --tournament 32721 --forecast-new --dry-run
```

## Configuration

All tunable parameters are in `config.yaml`.
