# Metaculus AI Forecasting Bot

AI-powered forecasting bot for the Metaculus AI Forecasting Benchmark competition.

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
