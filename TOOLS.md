# Helper Tools & Visualizers

This document lists all the non-core helper scripts, dashboards, and visualizers in the project. These are auxiliary tools for monitoring, debugging, and analyzing forecasts—not part of the main forecasting pipeline.

## Quick Reference

| Tool | Command | Purpose |
|------|---------|---------|
| HTML Dashboard | `python scripts/dashboard_html.py` | Static HTML dashboard to browse forecasts |
| Streamlit Dashboard | `streamlit run scripts/dashboard_streamlit.py` | Interactive dashboard with filtering |
| ~~Forecast Tracker~~ | ~~`python scripts/track_forecasts.py --tournament 32916`~~ | *Unavailable: Metaculus API locked down (see Analysis & Tracking).* |
| Tracking Backfill | `python scripts/backfill_tracking_from_artifacts.py [--apply]` | Add missing questions to tracking files from local artifact dirs (no API) |
| Score Updater | `python scripts/update_score_tracking.py` | Fetch score data from Metaculus API |
| Resolution Scraper | `python scripts/scrape_resolutions.py` | Scrape resolution values via browser |
| Score Scatter Plot | `python scripts/plot_score_scatter.py` | Generate score scatter plot |
| Ensemble Diversity Report | `python scripts/ensemble_diversity_report.py` | Analyze forecaster agreement & anchoring across ensemble |
| Tool Usage Analyzer | `python scripts/analyze_tool_usage.py <path>` | Analyze research tool usage per forecast |
| Artifact Migration | `python scripts/migrate_artifacts.py` | Backfill missing database fields |

---

## Dashboards

### Static HTML Dashboard

**Location:** `scripts/dashboard_html.py`

A lightweight browser-based dashboard that lists all forecast runs with detailed drill-down views.

```bash
python scripts/dashboard_html.py [--port 8000] [--data-dir ./data]
```

Then open http://localhost:8000 in your browser.

**Features:**
- List view showing all forecast runs (question, type, prediction, cost)
- Detail view with full forecast breakdown (research, ensemble, aggregation)
- Markdown rendering for agent reasoning
- Computes actual percentile values from CDF for numeric questions
- Supports both old and new artifact formats

### Streamlit Dashboard

**Location:** `scripts/dashboard_streamlit.py`

**Requires:** `streamlit` (install via `pip install streamlit`)

An interactive dashboard with filtering capabilities that reads from the SQLite database.

```bash
streamlit run scripts/dashboard_streamlit.py
```

**Features:**
- Filter forecasts by mode (test/preview/live) and question type
- Summary metrics (total forecasts, cost, mode distribution)
- Charts showing forecast distribution by mode and type
- Agent agreement analysis for binary questions
- Raw data export

**Note:** If you see errors about missing database fields, run the migration script first:
```bash
python scripts/migrate_artifacts.py
```

---

## Analysis & Tracking

### ~~Forecast Tracker (Consensus Comparison)~~ — *Not usable currently*

**Location:** `scripts/track_forecasts.py`

**Status:** The Metaculus API was locked down in Feb 2026. The tracker relied on the API for the list of questions you’ve forecasted and for `aggregations` (community predictions). Those endpoints now return `null` or restricted data, so **track_forecasts.py cannot be used** to build or refresh tracking files from the API.

**Instead:** Use **`scripts/backfill_tracking_from_artifacts.py`** to add missing questions to `data/tracking/*.json` from your local forecast artifact dirs (no API calls). Then use the Score Updater and Resolution Scraper below to fill in scores and resolution values.

~~Fetches community consensus probabilities from Metaculus and compares them against your submitted forecasts. Helps identify systematic biases.~~

```bash
# (No longer usable — API lockdown)
# python scripts/track_forecasts.py --tournament 32916
```

~~**Output:** Per-forecast comparison, aggregate statistics, JSON saved to `data/tracking/<tournament_id>.json`. **Requires:** `METACULUS_TOKEN`.~~

### Score Tracking

Three scripts work together to track tournament performance. They exist because the Metaculus API was locked down in Feb 2026 — `resolution` and `aggregations` fields now return `null`, but `score_data` on `my_forecasts` is still available.

**Parameter:** These scripts do *not* take a tournament ID. They take **`--tracking-file`** (path to a tracking JSON). With no arguments, each defaults to **`data/tracking/minibench.json`**. To run for another set of questions, pass the path explicitly (e.g. `--tracking-file data/tracking/32916.json` or `data/tracking/other.json`). Run the script once per tracking file if you want to update all of them.

**Data files:** `data/tracking/minibench.json`, `data/tracking/32916.json`, `data/tracking/other.json`

#### Score Updater

**Location:** `scripts/update_score_tracking.py`

Fetches the 7 scoring fields (`baseline_score`, `peer_score`, `coverage`, `relative_legacy_score`, `weighted_coverage`, `spot_peer_score`, `spot_baseline_score`) from the Metaculus API for each question in the tracking file. Also marks newly resolved questions.

```bash
poetry run python scripts/update_score_tracking.py                              # defaults to minibench
poetry run python scripts/update_score_tracking.py --tracking-file data/tracking/32916.json
```

**What it does:**
- Fetches `/api/posts/{id}/` for each question (authenticated, 1.2s rate limit)
- Updates `score_data` and `resolved` status
- Recomputes aggregate statistics (mean/median scores, positive/negative counts)
- Handles rate limiting with exponential backoff (4s, 8s, 16s, 32s)

**Requires:** `METACULUS_TOKEN` environment variable

#### Resolution Scraper

**Location:** `scripts/scrape_resolutions.py`

Scrapes actual resolution values (Yes/No, option names, numeric values) from the Metaculus UI using Playwright. Needed because the API returns `resolution: null` due to the lockdown.

```bash
# One-time setup
poetry add -G dev playwright
poetry run playwright install chromium

# Run the scraper
poetry run python scripts/scrape_resolutions.py                                 # defaults to minibench
poetry run python scripts/scrape_resolutions.py --tracking-file data/tracking/32916.json
```

**What it does:**
- Finds questions where `resolution` is null (resolved but missing the actual outcome, or newly resolved)
- Opens each question page in a headed Chromium browser (headless is blocked by Cloudflare)
- Extracts the resolution from the "Resolved" badge in the DOM
- Parses binary (Yes/No), multiple choice (option name), and numeric (float with unit stripping) resolutions
- Updates the tracking file with the scraped values

**Requires:** `playwright` dev dependency, Chromium browser installed via Playwright

**Note:** Uses a headed (visible) browser because Cloudflare blocks headless requests. You may need to solve a CAPTCHA on the first page load.

#### Score Scatter Plot

**Location:** `scripts/plot_score_scatter.py`

Generates a dark-themed scatter plot of spot peer scores over time, matching the Metaculus tournament dashboard style.

```bash
poetry run python scripts/plot_score_scatter.py                                 # defaults to minibench
poetry run python scripts/plot_score_scatter.py --tracking-file data/tracking/32916.json
poetry run python scripts/plot_score_scatter.py --tracking-file data/tracking/32916.json --output my_plot.png
```

**Output:** Derived from tracking file name (e.g., `minibench.json` → `minibench_scores.png`), or specify with `--output`.

**What it shows:**
- Hollow orange circles for each scored question (x = forecast time, y = spot peer score)
- White running average line (cumulative mean)
- Total question count and average score in the subtitle

**Requires:** `matplotlib` dev dependency

#### Typical Workflow

```bash
# 1. Fetch latest scores from API (fast, ~1 min)
poetry run python scripts/update_score_tracking.py --tracking-file data/tracking/32916.json

# 2. Scrape resolution values for newly resolved questions (slower, needs browser)
poetry run python scripts/scrape_resolutions.py --tracking-file data/tracking/32916.json

# 3. Generate the plot
poetry run python scripts/plot_score_scatter.py --tracking-file data/tracking/32916.json
```

Run step 1 regularly. Run step 2 only when questions have resolved since the last scrape. Run step 3 whenever you want an updated visualization.

### Tool Usage Analyzer

**Location:** `scripts/analyze_tool_usage.py`

Analyzes the `tool_usage.json` file generated by each forecast run to show which research tools were used and how.

```bash
python scripts/analyze_tool_usage.py data/41594_20260128_123456/tool_usage.json
```

**Output:**
- Historical and current query breakdown
- Tools used (Google, AskNews, Agentic) with result counts
- Per-agent model lineup and search activity
- Cost, token, and timing metrics (if available)

---

## Reports & Assessments

### Ensemble Diversity Report

**Location:** `scripts/ensemble_diversity_report.py`

Generates a static HTML report analyzing how the 5-forecaster ensemble behaves — whether forecasters agree or diverge, how much they shift between outside and inside views, and whether cross-pollination is creating real diversity.

```bash
# Generate report (scans all artifacts in data/)
python scripts/ensemble_diversity_report.py

# Custom output path
python scripts/ensemble_diversity_report.py --output my_report.html
```

**Default output:** `data/ensemble_diversity_report.html`

**To view the report**, open the HTML file directly in a browser, or serve it locally:

```bash
cd data && python -m http.server 8765
# Then open http://localhost:8765/ensemble_diversity_report.html
```

**What it shows:**

- **Global stats** — total forecasts, avg prediction move, convergence/divergence counts
- **Per question type** (binary, numeric, multiple choice, discrete, date):
  - Avg outside view and inside view spread (std dev or coefficient of variation)
  - Ensemble spread change (do forecasters converge or diverge after the inside view?)
- **Per forecast** — all 5 forecasters' outside view and inside view predictions, shift from OV → IV, range, std dev, and final aggregated value
- **Cross-pollination aware** — shifts are computed against the outside view each forecaster actually *received* (not their own), so F2's shift is relative to F4's outside view, etc.
- **Tags** — each forecast is labeled CONVERGED, STABLE, or DIVERGED based on whether the inside view spread shrank, stayed flat, or grew relative to the outside view spread

**Important:** This is a manual re-run script, not a live dashboard. It scans all artifact directories in `data/` each time it runs, excluding test mode forecasts and pre-refactor (pre Jan 27) artifacts. Re-run it after new forecasts to update.

### Forecast Quality Assessments (Manual)

**Location:** `docs/assessments/`

A manually maintained collection of markdown-based forecast quality reviews. Each assessment grades a forecast and documents reasoning quality.

**Index page:** `docs/assessments/README.md`

**Template:** `docs/forecast_quality_assessment_template.md`

This is a manual review system, not an automated tool.

### Report Generator (Programmatic)

**Location:** `src/storage/report_generator.py`

Python module for generating markdown reports from forecast data. Used programmatically, not as a CLI tool.

```python
from src.storage.report_generator import generate_reasoning_report, ForecastData

data = ForecastData(...)
report = generate_reasoning_report(data)
```

**Functions:**
- `generate_reasoning_report(data)` - Detailed report for a single forecast
- `generate_summary_report(forecasts)` - Summary across multiple forecasts

---

## Database & Migration

### Forecast Database

**Location:** `src/storage/database.py`

SQLite database at `data/forecasts.db` storing forecast records, agent predictions, and research sources.

**Schema Tables:**
- `forecasts` - Main prediction records (question_id, timestamp, prediction, cost, etc.)
- `agent_predictions` - Individual agent outputs per forecast
- `research_sources` - Research queries and sources used

This is a library module, not a CLI tool. Access via the dashboards or programmatically:

```python
from src.storage.database import ForecastDatabase
db = ForecastDatabase("data/forecasts.db")
forecasts = await db.get_forecasts_with_agents(limit=100)
```

### Artifact Migration

**Location:** `scripts/migrate_artifacts.py`

One-time migration utility for backfilling database fields from artifact directories. Run this if you have old forecasts with incomplete database records.

```bash
# Preview changes (dry run)
python scripts/migrate_artifacts.py --dry-run

# Apply changes
python scripts/migrate_artifacts.py
```

**What it does:**
- Backfills `mode` field from `metadata.json`
- Backfills `prediction_data` JSON from prediction artifacts
- Updates agent prediction data

Safe to run multiple times (only updates rows with missing data).

---

## Cost Tracking

### Built-in LLM Cost Tracker

**Location:** `src/utils/llm.py`

Cost tracking is built into the LLM client—there's no separate budget checker script.

**During a forecast run:**
Costs are automatically tracked and saved to `metadata.json` in each artifact directory.

**Programmatic access:**
```python
from src.utils.llm import get_cost_tracker

tracker = get_cost_tracker()
summary = tracker.get_summary()
# Returns: {total_calls, successful_calls, failed_calls, total_input_tokens, total_output_tokens, total_cost}
```

**Model pricing table:** See `MODEL_COSTS` dict in `src/utils/llm.py`

**To check costs from artifacts:**
```bash
# View cost for a specific forecast
cat data/41594_20260128_123456/metadata.json | jq '.costs'
```

---

## Troubleshooting

### "No forecasts found" in dashboards

1. Check that `data/forecasts.db` exists
2. Run the migration script: `python scripts/migrate_artifacts.py`
3. Ensure you have artifact directories in `data/` with the pattern `{question_id}_{timestamp}/`

### Streamlit dashboard errors

1. Install streamlit: `pip install streamlit`
2. Run migration: `python scripts/migrate_artifacts.py`
3. Check database exists: `ls -la data/forecasts.db`

### Track forecasts rate limiting

The tracker includes built-in rate limiting (1s delay between requests) and exponential backoff for 429 errors. If you still hit limits, wait a few minutes and try again.
