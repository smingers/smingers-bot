---
name: update-forecast-results
description: Updates forecast tracking with latest scores and resolution values by running the score-tracking script then the resolution scraper. Use when the user wants to update forecast results, refresh score tracking, scrape resolutions, or sync tracking data after new resolutions.
---

# Update Forecast Results

Runs the two-step workflow to refresh the tracking file: fetch score data from the API, then scrape resolution values in a browser.

## Workflow (run in order)

**Step 1 — Score data (API, no browser):**
```bash
poetry run python scripts/update_score_tracking.py
```
Optionally: `--tracking-file data/tracking/32916.json` (default is minibench).

**Step 2 — Resolution values (headed browser):**
```bash
poetry run python scripts/scrape_resolutions.py
```
Use the same `--tracking-file` if you passed it in step 1. A **visible browser** opens; Cloudflare blocks headless. User may need to complete a CAPTCHA on first load.

## Notes

- Step 1 is fast (API only). Step 2 opens a browser and visits each question page that needs a resolution value.
- Both scripts default to `data/tracking/minibench.json`. For a specific tournament (e.g. 32916), pass `--tracking-file data/tracking/32916.json` to both.
