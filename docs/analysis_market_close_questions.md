# Market Close Price Questions: Performance Analysis

**Date:** 2026-02-21
**Category:** "Will [TICKER]'s market close price on [date] be higher than its market close price on [date]?"
**Source:** MiniBench tournament tracking data + forecast artifacts + 13 assessment reviews

---

## 1. Overview

26 market close price questions identified in minibench (25% of all 106 questions):
- **14 resolved** (7 Yes, 7 No — a perfect 50/50 split confirming these are near-coin-flips)
- **12 unresolved** (pending resolution through late Feb 2026)

All are binary questions asking whether a stock's closing price on date B will be higher than on date A, with horizons of 5-14 trading days.

---

## 2. Scoring Performance (14 Resolved Questions)

| Ticker | My P(Yes) | Comm P(Yes) | Resolved | Right Side? | Brier | Peer Score | Spot Peer |
|--------|-----------|-------------|----------|-------------|-------|------------|-----------|
| UHS    | 0.506     | 0.52        | Yes      | Y           | 0.244 | +0.27      | +0.79     |
| SMCI   | 0.416     | 0.46        | Yes      | N           | 0.341 | -1.91      | -7.91     |
| BAC    | 0.433     | 0.53        | No       | Y           | 0.187 | +9.74      | +18.26    |
| AAPL   | 0.506     | 0.55        | No       | N           | 0.256 | +3.50      | +11.55    |
| ALGN   | 0.582     | 0.53        | Yes      | Y           | 0.175 | +4.60      | +10.44    |
| NOW    | 0.550     | 0.53        | No       | N           | 0.303 | -0.53      | -5.74     |
| VRSN   | 0.552     | 0.53        | No       | N           | 0.305 | -5.16      | -6.47     |
| CSX    | 0.552     | 0.54        | Yes      | Y           | 0.201 | +1.20      | +2.16     |
| BA     | 0.466     | 0.52        | Yes      | N           | 0.285 | -7.49      | -10.51    |
| RCL    | 0.512     | 0.55        | No       | N           | 0.262 | +6.96      | +8.52     |
| PCG    | 0.548     | 0.52        | Yes      | Y           | 0.204 | +5.03      | +8.95     |
| HAL    | 0.558     | 0.54        | No       | N           | 0.311 | -1.57      | -4.24     |
| NVDA   | 0.516     | 0.50        | Yes      | Y           | 0.234 | +5.62      | +7.48     |
| TRMB   | 0.534     | 0.51        | No       | N           | 0.285 | +11.06     | +12.62    |

### Summary Statistics

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Correct direction | 6/14 (43%) | Worse than coin flip |
| Mean Brier score | 0.2567 | Slightly worse than 0.25 baseline |
| Avg peer score | +2.24 | Slightly beating peers overall |
| Avg spot peer score | +3.28 | Better at time of resolution |
| Avg baseline score | +3.44 | Slightly beating random baseline |

**Key takeaway:** Despite getting the direction wrong more often than right, the bot still achieves slightly positive peer and baseline scores. This is because:
1. When wrong, predictions were close to 50% (small loss)
2. Some big wins came from being more contrarian than community when correct (BAC, TRMB, ALGN)
3. The TRMB result (+11 peer, +45 baseline) is an outlier that lifts the average substantially

**Without TRMB:** Avg peer score drops to +1.56, avg baseline to +0.01 — essentially break-even.

---

## 3. Systematic Biases (24 Questions with Comparison Data)

### Directional bias
- My avg P(Yes): **0.5168**
- Community avg P(Yes): **0.5184**
- No meaningful directional bias — both clustered just above 50%.

### Extremeness
- My avg |distance from 0.50|: **0.0404**
- Community avg |distance from 0.50|: **0.0268**
- **I am 1.51x more extreme than community consensus.**
- I'm bullish (>50%) on 17/24, bearish (<50%) on 6/24, neutral on 1/24
- Community is bullish on 19/24, bearish on 3/24, neutral on 2/24

This means I move further from 50% than the community does, but I'm not systematically in one direction. The extra extremeness is hurting on these near-coin-flip questions — **being closer to 50% would improve scores.**

### Resolved direction analysis
- When stock went **UP** (Yes): My avg P = 0.512, Comm avg P = 0.513 → both barely above 50%
- When stock went **DOWN** (No): My avg P = 0.521, Comm avg P = 0.534 → both wrongly bullish

The bot (and community) both show a slight bullish bias — predicting "up" more often than "down" — which is rational for equities over long horizons but not informative for 5-14 day windows.

### Worst and best cases
- **Best peer score:** TRMB +11.06 — community at 51%, I was at 53.4%, resolved No. I got the direction wrong but was slightly less wrong than peers.
- **Worst peer score:** BA -7.49 — data contamination from a misleading Investopedia article produced a distorted forecast of 46.6% when it should have been ~52%.
- **Biggest Brier win:** ALGN 0.175 — I was at 58.2%, resolved Yes.
- **Biggest Brier loss:** SMCI 0.341 — I was at 41.6%, resolved Yes.

---

## 4. yFinance Tool Usage

### Architecture
yFinance is available **only through agentic search** (the direct/programmatic path is disabled). The relevant code comment explains why:

> Direct yFinance queries from the query builder are disabled. The LLM often guesses wrong ticker symbols (e.g., "TWEX" instead of "^TWII" for TAIEX) and the direct path has no way to self-correct. yFinance is now available through agentic search instead, where the LLM can observe failures and retry with corrected tickers.

### Usage rate

| Period | Questions | yFinance Used | Rate |
|--------|-----------|---------------|------|
| Feb 2-5 (early) | 11 | 0 | 0% |
| Feb 6+ (later) | 13* | 11 | 85% |
| **Overall** | **24** | **11** | **46%** |

*2 questions (DELL, LMT) have no artifact directories.

The agentic search LLM simply didn't choose to use yFinance for the first 11 market questions. Starting Feb 6 (NVDA, TRMB), usage became consistent. This is likely due to prompt or model changes around that time, not a code change.

### What data was fetched
When used, yFinance was typically queried for:
- Ticker symbol lookup (e.g., `["TRMB", "yFinance"]`)
- Historical price data (e.g., `["CCL historical 1y", "yFinance"]`)
- Peer comparisons (e.g., `["RCL", "yFinance"]` alongside `["CCL", "yFinance"]`)

The yFinance tool provides: current price, 52-week range, 1Y/5Y price history, fundamentals, analyst targets, options data, and recent daily prices (10 trading days). However, the raw `<YFinanceData>` output is consumed internally by the agentic search LLM and summarized — the formatted data does not appear verbatim in saved artifacts.

### Effectiveness
Despite being available and fetching data successfully, the agentic search LLM frequently **failed to compute the key statistic needed for these questions**: the historical N-day return distribution (probability of positive return over the question's time horizon). The NVDA forecast (42011) is illustrative — the agent spent all 7 steps trying to get historical price return distributions, querying yFinance once for current data but then repeatedly trying Google to find pre-computed CSVs of return distributions that don't exist.

**The tool provides prices but the pipeline lacks a mechanism to compute return statistics from those prices.**

---

## 5. Assessment Patterns (13 Reviewed)

### Grade distribution
- B+: 1 (NOW)
- B: 8 (UHS, SMCI, BAC, AAPL, ALGN, VRSN, CSX, RCL, PCG)
- B-: 2 (HAL, NVDA)
- C: 1 (BA)

### Top weaknesses (by frequency across assessments)

| Weakness | Assessments Affected | Impact |
|----------|---------------------|--------|
| **No historical return distribution** | 13/13 | Cannot anchor to empirical base rate for N-day returns |
| **AskNews ticker disambiguation** | 8/13 | Wrong company's news mixed in (e.g., "HAL" → Hindustan Aeronautics) |
| **o3 fabricates base rate statistics** | 5/13 | Presents invented numbers as empirical data |
| **Sonnet over-adjusts from base rate** | 4/13 | Narrative-driven momentum adjustments of 8-10pp |
| **Model family clustering** | 7/13 | Effective ensemble diversity reduced from 5 to 2-3 viewpoints |
| **Missing options/implied vol data** | 5/13 | Can't calibrate expected move magnitude |
| **Extraction errors** | 2/13 | BAC: regex extracted price stat (-6.4%) as probability, distorting final by 9pp |
| **Data contamination** | 1/13 | BA: stale Investopedia article with wrong price ($175 vs actual $233) |

### Assessment recommendations (appearing in 3+ reviews)
1. **Integrate yFinance for automatic return distribution computation** — compute P(positive N-day return) from historical data
2. **Fix AskNews ticker disambiguation** — use full company names, not ticker symbols
3. **Add options-implied volatility/expected move** — calibrate the range of likely price changes
4. **Add outlier detection for extracted probabilities** — flag values <10% or >90% when ensemble is near 50%
5. **Cap per-factor adjustment magnitude** — limit narrative-driven adjustments to ~5pp for short-term stock questions
6. **Add broader market context** — include VIX, S&P 500, sector ETF performance
7. **Provide random-walk baseline guidance** — explicitly tell forecasters that short-term stock direction is ~50/50

---

## 6. Improvement Recommendations

### High Impact, Low Effort

**1. Add automatic return distribution computation to yFinance handler**

The single highest-impact improvement. When the question mentions a stock ticker and a time horizon, automatically compute from yFinance historical data:
- P(positive N-day return) over the last 5/10 years
- Mean and std dev of N-day returns
- Number of observations

This should be a programmatic step (not LLM-dependent) that injects a standardized preamble into the forecaster prompt:
```
HISTORICAL BASE RATE: Over the past 10 years, TRMB has had a positive 5-trading-day return 52.3% of the time (N=2,510 observations, mean=+0.21%, stdev=3.8%).
```

**2. Add stock question detection and base-rate anchoring prompt**

Detect "market close price" questions and inject explicit guidance:
- "Short-term stock price direction is close to a coin flip. Your base rate should be near 50% unless there is a specific, verifiable catalyst."
- "Do not adjust more than 5 percentage points from your base rate for any single factor."
- "Do not fabricate or invent historical return statistics. If you don't have the data, say so."

**3. Fix AskNews queries for stock questions**

Use full company name + ticker in AskNews queries (e.g., "Halliburton HAL" instead of just "HAL") to reduce disambiguation failures. The current 8/13 failure rate on stock questions wastes research budget on irrelevant articles.

### Medium Impact

**4. Add extraction outlier detection**

For binary questions near 50%, flag any extracted probability below 20% or above 80% as suspicious. The BAC incident (6.4% extracted instead of 47%) would have been caught by this.

**5. Reduce extremeness — move predictions closer to 50%**

The bot is 1.51x more extreme than community on these questions. For market close price questions specifically, consider:
- Shrinking the ensemble average toward 50% by a calibration factor
- Or adding an explicit instruction to forecasters: "For short-term stock questions, resist the temptation to move far from 50%"

**6. Add options-implied move data**

yFinance already returns ATM implied volatility and options data. Use this to calibrate: if IV implies a 3% expected move, but the question is asking about a direction (binary), the "expected move" information is less useful for the direction but helps forecasters understand the noise level.

### Lower Priority

**7. Address model family clustering**

Currently Sonnet 4.6 and o3 form two clusters. Cross-pollination helps but doesn't fully break the pattern. Consider:
- Adding explicit diversity instructions per forecaster
- Assigning different analytical frameworks (e.g., "You must use a technical analysis perspective" vs "You must use a fundamentals perspective")

**8. Block fabricated statistics**

Add to prompts: "If you cite a specific historical probability or return statistic, you must identify the source. Do not present estimates as empirical data."

---

## 7. Bottom Line

Performance on market close price questions is **near break-even** — slightly positive peer scores but slightly worse than the naive 0.50 baseline on Brier. The bot is getting the direction wrong 57% of the time, which means forecasting effort is essentially adding noise rather than signal on these questions.

The root cause is clear from the assessments: **the pipeline lacks the one piece of information that would be most useful** — a pre-computed historical return distribution for the specific ticker over the specific time horizon. The yFinance tool provides all the raw data needed to compute this, but the pipeline relies on the agentic search LLM to compute statistics from price data, which it consistently fails to do. A deterministic, programmatic step that automatically computes P(positive N-day return) from yFinance data would be the single most impactful improvement.

The second-order improvement is reducing extremeness: predictions should stay closer to 50% on these questions unless there's a clear, verifiable catalyst (earnings, major news event). The 1.51x extremeness ratio vs community is costing points.
