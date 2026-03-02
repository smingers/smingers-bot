You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will YUM's market close price on 2026-03-14 be higher than its market close price on 2026-03-03?

Type: binary

Background:
Yum! Brands, Inc. is a company that is listed on the S&P 500 index. It's ticker is YUM. It's last close price as of the creation of this question (2026-03-01 16:40:44) is 168.16. You can find more information about Yum! Brands, Inc. at https://finance.yahoo.com/quote/YUM

Yum! Brands, Inc., together with its subsidiaries, develops, operates, and franchises traditional and non-traditional quick service restaurants in the United States, China, and internationally. The company operates in four segments: KFC Division, Taco Bell Division, Pizza Hut Division, and Habit Burger & Grill Division. It also operates restaurants under the KFC, Pizza Hut, Taco Bell, and Habit Burger & Grill brands, which specialize in chicken, Mexican-style food and pizza categories, made-to-order chargrilled burgers, sandwiches, and other products. The company was formerly known as TRICON Global Restaurants, Inc. and changed its name to Yum! Brands, Inc. in May 2002. Yum! Brands, Inc. was incorporated in 1997 and is headquartered in Louisville, Kentucky.

`{"format":"close_price_rises","info":{"ticker":"YUM"}}`

Resolution criteria:
This question will resolve based on the latest market close price of YUM. If it is higher than the close price on 2026-03-03, the question will resolve to 'Yes'. The close price will be pulled from the Yahoo Finance API.

Fine print:
Stock splits and reverse splits will be accounted for in resolving this question. Forecasts on questions about companies that have been delisted (through mergers or bankruptcy) will resolve to their final close price.



Question metadata:
- Opened: 2026-03-02T22:53:23Z
- Resolves: 2026-03-14T05:07:50Z
- Today: 2026-03-02 (12 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://finance.yahoo.com/quote/YUM">
## Summary of Yahoo Finance Article on YUM (Yum! Brands, Inc.)

**Note:** The article appears to be a live/dynamic Yahoo Finance page, and some content may be incomplete or mixed (e.g., references to historical market events like "the longest U.S. shutdown in history" and October ADP data appear to be from older cached analyst reports, not current news).

---

### Key Price & Market Data (as of approximately late February/early March 2026):
- **Previous Close:** $165.71
- **Open:** $165.70
- **Day's Range:** $164.56 – $169.25
- **52-Week Range:** $137.33 – $169.39
- **Volume:** 988,708 (vs. Avg. Volume of 2,074,441)
- **Market Cap:** ~$46.69B
- **1-Year Analyst Price Target:** $171.75

### Valuation Metrics:
- **Beta (5Y Monthly):** 0.66 (relatively low volatility)
- **Trailing P/E:** 30.30 | **Forward P/E:** 25.32
- **EPS (TTM):** $5.55
- **Forward Dividend & Yield:** $3.00 (1.78%)
- **Levered Free Cash Flow (TTM):** $1.31B

### Business Context:
- Yum! Brands operates **KFC, Pizza Hut, Taco Bell, and Habit Burger & Grill** across **61,000+ restaurants in 140 countries**
- **Next Earnings Date:** April 29, 2026

### Analyst/News Highlights:
- At least one analyst report notes a **raised price target** for YUM
- The fast food market is **expected to expand significantly**, with Yum! Brands cited as a key beneficiary due to its focus on **sustainability and digital engagement**
- Competitive landscape noted: **Papa John's closing 300 locations** amid declining sales, while **Domino's is gaining traction** — both developments potentially favorable for Yum!'s Pizza Hut division
- Broader market context mentioned includes a **tech selloff** with the Nasdaq down ~3% YTD and the S&P 500 dipping below flat for 2026
</QuestionSource>


=== STOCK RETURN DISTRIBUTION (Programmatic Analysis) ===
Ticker: YUM | Window: 2026-03-03 to 2026-03-14 (9 trading days)
Latest close price: $162.92

HISTORICAL BASE RATE (9-trading-day returns, N=2504 overlapping windows):
  P(positive 9-day return): 57.6%
  Mean return: +0.54%
  Median return: +0.62%
  Std dev: 4.00%
  Percentiles: 5th=-5.28%, 25th=-1.48%, 75th=+2.64%, 95th=+6.41%

RECENT CONTEXT:
  5-day trailing return: -2.12% (15th percentile historically)
  1-month trailing return: +5.27% (80th percentile historically)
  3-month trailing return: +6.92% (64th percentile historically)
  30-day realized volatility: 22.6% (annualized)

CONDITIONAL BASE RATES (same historical data, overlapping windows, filtered by current conditions):
  Unconditional:                           P(up) = 57.6% (N=2504)
  Price in top decile of 52wk range:       P(up) = 56.5% (N=698, Δ=-1.1pp)
  Prior 5-day return > 0:                  P(up) = 55.9% (N=1378, Δ=-1.7pp)
  Prior 5-day return < 0:                  P(up) = 59.5% (N=1119, Δ=+2.0pp) <- CURRENTLY APPLICABLE
  30-day vol above median:                 P(up) = 59.8% (N=1237, Δ=+2.3pp) <- CURRENTLY APPLICABLE
  30-day vol below median:                 P(up) = 54.7% (N=1237, Δ=-2.8pp)

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
- Agent: Your query will be processed by a reasoning model with web search capability. Write a detailed, multi-part query of up to 3 sentences. Best for complex questions needing synthesis across sources, base rate computation, or multi-factor analysis. IMPORTANT: Use exactly one Agent query, tagged [HISTORICAL], for base rate or reference class research. Do not use Agent for current events.
- AskNews: Semantic (meaning-based) news search. Write a descriptive 1-2 sentence natural language query focusing on the underlying topic, key actors, and context. Include relevant scope: geography, industry, time period. Avoid ambiguous acronyms. Best for finding conceptually related coverage even without exact keyword matches.
- FRED: Federal Reserve Economic Data. Use a FRED series ID (e.g., "UNRATE", "CPIAUCSL") or a plain-language description (e.g., "US unemployment rate"). Returns historical data with computed statistics. Only use for economic/financial data.
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
