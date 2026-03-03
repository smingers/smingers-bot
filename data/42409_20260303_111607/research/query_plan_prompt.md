You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will EXR's market close price on 2026-03-10 be higher than its market close price on 2026-03-03?

Type: binary

Background:
Extra Space Storage Inc. is a company that is listed on the S&P 500 index. It's ticker is EXR. It's last close price as of the creation of this question (2026-03-01 16:40:36) is 151.03. You can find more information about Extra Space Storage Inc. at https://finance.yahoo.com/quote/EXR

Extra Space Storage Inc., headquartered in Salt Lake City, Utah, is a self-administered and self-managed REIT and a member of the S&P 500. As of September 30, 2025, the Company owned and/or operated 4,238 self-storage stores in 43 states and Washington, D.C.The Company's stores comprise approximately 2.9 million units and approximately 326.9 million square feet of rentable space operating under the Extra Space brand. The Company offers customers a wide selection of conveniently located and secure storage units across the country, including boat storage, RV storage and business storage. It is the largest operator of self-storage properties in the United States.

`{"format":"close_price_rises","info":{"ticker":"EXR"}}`

Resolution criteria:
This question will resolve based on the latest market close price of EXR. If it is higher than the close price on 2026-03-03, the question will resolve to 'Yes'. The close price will be pulled from the Yahoo Finance API.

Fine print:
Stock splits and reverse splits will be accounted for in resolving this question. Forecasts on questions about companies that have been delisted (through mergers or bankruptcy) will resolve to their final close price.



Question metadata:
- Opened: 2026-03-03T11:08:14Z
- Resolves: 2026-03-10T20:43:52Z
- Today: 2026-03-03 (7 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://finance.yahoo.com/quote/EXR">
## Summary of Yahoo Finance Article on EXR (Extra Space Storage Inc.)

### Recent Financial Performance
- **Q4 Core FFO growth**: 2.5%
- **Q4 Revenue**: $857.5 million, surpassing estimates
- Analyst views described as **mixed**, with a **cautious sector outlook** noted

### Key Market Data (as of ~March 2, 2026)
- **Previous Close**: $151.03
- **Open**: $149.54
- **Day's Range**: $149.29 – $153.49
- **52-Week Range**: $121.03 – $160.58
- **Average Volume**: ~1.395 million shares
- **Market Cap**: ~$33.83B (intraday) / $32.23B (valuation measures)
- **Beta (5Y Monthly)**: 1.24
- **1-Year Analyst Price Target**: $151.50

### Valuation & Financials
- **Trailing P/E**: 33.26 | **Forward P/E**: 31.35
- **Revenue (TTM)**: $3.45B | **Net Income**: $972.26M
- **Diluted EPS (TTM)**: $4.59
- **Forward Dividend & Yield**: $6.48 (4.25%)
- **Ex-Dividend Date**: March 16, 2026
- **Next Earnings Date (est.)**: April 28, 2026

### Analyst Ratings (Named Sources: Research Reports)
- Multiple **BUY ratings** with raised price targets:
  - Target raised to **$165.00**
  - Target raised to **$163.00**
  - Target raised to **$156.00**
- All BUY-rated reports cite **High** ratings for Management, Safety, and Financial Strength
</QuestionSource>


=== STOCK RETURN DISTRIBUTION (Programmatic Analysis) ===
Ticker: EXR | Window: 2026-03-03 to 2026-03-10 (5 trading days)
Latest close price: $152.65
Reference close price (2026-03-03): $152.65
Return so far: +0.00% (down from reference)
Next ex-dividend: 2026-03-16 (outside window)
Dividend yield: 4.25%
52-week range: $121.03 - $160.58
ANALYST TARGETS:
- Mean: $151.50 | Low: $140.00 | High: $178.00
- Number of analysts: 20
- Recommendation: Buy

HISTORICAL BASE RATE (5-trading-day returns, N=2508 overlapping windows):
  P(positive 5-day return): 55.0%
  Mean return: +0.26%
  Median return: +0.42%
  Std dev: 3.77%
  Percentiles: 5th=-5.94%, 25th=-1.89%, 75th=+2.51%, 95th=+5.86%

RECENT CONTEXT:
  5-day trailing return: +1.49% (63rd percentile historically)
  1-month trailing return: +9.92% (91st percentile historically)
  3-month trailing return: +15.92% (86th percentile historically)
  30-day realized volatility: 26.1% (annualized)

CONDITIONAL BASE RATES (same historical data, overlapping windows, filtered by current conditions):
  Unconditional:                           P(up) = 55.0% (N=2508)
  3-month return > 20%:                    P(up) = 49.8% (N=201, Δ=-5.2pp)
  Price in top decile of 52wk range:       P(up) = 58.0% (N=600, Δ=+3.0pp) <- CURRENTLY APPLICABLE
  Price in bottom decile of 52wk range:    P(up) = 53.8% (N=145, Δ=-1.2pp)
  Prior 5-day return > 0:                  P(up) = 55.6% (N=1375, Δ=+0.7pp) <- CURRENTLY APPLICABLE
  Prior 5-day return < 0:                  P(up) = 54.0% (N=1125, Δ=-0.9pp)
  30-day vol above median:                 P(up) = 56.6% (N=1239, Δ=+1.6pp) <- CURRENTLY APPLICABLE
  30-day vol below median:                 P(up) = 53.3% (N=1239, Δ=-1.6pp)

This is a PROGRAMMATIC computation from actual historical price data. Use the historical base rate as an anchor and adjust for current conditions.
=== END STOCK RETURN DISTRIBUTION ===

YOUR TASK:
1. Analyze the question and the pre-research context
2. Identify what information a skilled forecaster would need beyond what's already available
3. Generate 8 search queries to fill the remaining gaps

COVERAGE DIMENSIONS (ensure your queries collectively address these):
- Base rate: Historical frequency, distribution, or precedent for the outcome being forecast. How often has something like this happened before?
- Resolution mechanism: How exactly does this question resolve? What specific data source, metric, threshold, or event determines the outcome? What is the current state of that mechanism?
- Key drivers: The 1-3 most important causal factors that will determine the outcome. What moves this metric or makes this event more/less likely?
- Current state: Latest news, data points, or developments relevant to the question
- Contrarian check: Information that could support the less obvious outcome. What would make the unlikely scenario happen?

TYPE-SPECIFIC GUIDANCE:
- For binary "will X reach Y by Z" questions: Include a query for the historical base rate of X reaching Y in comparable timeframes. Also query the current trajectory/trend.
- For numeric questions: Query for recent values of the metric AND its primary upstream drivers. For financial metrics, query for upcoming scheduled events (data releases, FOMC meetings, earnings) before the resolution date.
- For multiple choice questions: Ensure at least one query is relevant to each substantive option. For catch-all/"other" options, query for the base rate of non-favored outcomes.

AVAILABLE TOOLS (only use tools listed here):
- Google: Keyword search. Write short queries (max 6 words) using terms likely to appear on relevant web pages. Best for reference pages, datasets, official reports.
- Google News: Keyword search over recent news articles. Max 6 words. Best for breaking news, recent events, and current developments.
- Agent: A reasoning model with web search capability. Write a detailed query of up to 3 sentences. Best for qualitative synthesis: identifying the most relevant historical analogies, evaluating which reference classes apply and why, assessing competing explanations, or finding expert analyses that provide base rate estimates. The Agent CANNOT compute statistics. IMPORTANT: Use exactly one Agent query, tagged [HISTORICAL]. Do not use Agent for current events.
- AskNews: Semantic (meaning-based) news search. Write a descriptive 1-2 sentence natural language query focusing on the underlying topic, key actors, and context. Include relevant scope: geography, industry, time period. Avoid ambiguous acronyms. Best for finding conceptually related coverage even without exact keyword matches.
- FRED: Federal Reserve Economic Data. Use a FRED series ID (e.g., "UNRATE", "CPIAUCSL") or a plain-language description (e.g., "US unemployment rate"). Returns historical data with computed statistics. Use for economic/financial data.If the question references a FRED series ID, you MUST include a (FRED) query using that exact series ID.
- yFinance: Yahoo Finance ticker symbol (e.g., "AAPL", "^GSPC"). Returns price history, fundamentals, analyst targets, and options data. Only use for stocks, indices, or ETFs.
- Google Trends: A search term (e.g., "hospital"). Returns 90-day search interest data with base rate analysis. Only use when the question specifically involves Google Trends data.

TAG each query as [HISTORICAL] (for base rates, reference classes, past data, background context) or [CURRENT] (for recent news, latest values, current developments, upcoming events). Aim for roughly 60% historical and 40% current. Include at least 2 of each.

Format your answer exactly as below. Each query on its own line. The source in parentheses, temporal tag in brackets. Do not wrap queries in quotes.

Analysis:
{Your analysis of the question, what the pre-research context already provides, what key information gaps remain, and your search strategy.}

Search queries:
1. [HISTORICAL] your query here (Google) -- Intent: what this query aims to find
2. [CURRENT] your query here (Google News) -- Intent: what this query aims to find
3. [HISTORICAL] your detailed multi-part query here (Agent) -- Intent: what this query aims to find
...
