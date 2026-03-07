You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Which range will the CBOE Volatility Index (VIX) close level fall in on April 30, 2026?

Type: multiple_choice

Background:
This forecasts implied equity volatility, a key measure for risk sentiment, hedging costs, and stress regimes.

`{"format":"bot_tournament_question","info":{"hash_id":"46a5d79c8f6ed158","sheet_id":333.1}}`

Resolution criteria:
This question resolves to the option whose range contains the VIX close value for April 30, 2026 as shown in FRED series VIXCLS using https://fred.stlouisfed.org/series/VIXCLS

Fine print:
If April 30, 2026 has no VIXCLS observation (market holiday), use the most recent prior trading day’s observation. Use the value shown on FRED (do not re-compute). Candidate Sources: CBOE VIX historical data (backup) https://www.cboe.com/tradable_products/vix/vix_historical_data/ | Stooq VIX historical data (backup) https://stooq.com/q/d/l/?s=%5Evix

Options: ['Below 15.0', '15.0 to below 20.0', '20.0 to below 25.0', '25.0 or higher']

Question metadata:
- Opened: 2026-03-07T10:30:00Z
- Resolves: 2026-04-30T00:00:00Z
- Today: 2026-03-07 (54 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://fred.stlouisfed.org/series/VIXCLS">
The following summary extracts the key data points and metadata from the provided FRED (Federal Reserve Bank of St. Louis) series documentation for the CBOE Volatility Index (VIX).

### 1. Facts, Statistics, and Objective Measurements
The article provides specific closing values for the VIX index for early March 2026 and late February 2026:
*   **March 5, 2026:** 23.75
*   **March 4, 2026:** 21.15
*   **March 3, 2026:** 23.57
*   **March 2, 2026:** 21.44
*   **February 27, 2026:** 19.86

**Technical Specifications:**
*   **Units:** Index (Not Seasonally Adjusted).
*   **Frequency:** Daily, Close.
*   **Definition:** The VIX measures market expectations of near-term volatility as conveyed by stock index option prices.
*   **Data Source:** Chicago Board Options Exchange (CBOE) Market Statistics.

### 2. Opinions from Reliable and Named Sources
*   **Federal Reserve Bank of St. Louis (FRED):** Notes that all data provided in the series are subject to revision.
*   **Chicago Board Options Exchange (CBOE):** As the primary source and copyright holder, the CBOE defines the index specifically as a measure of "market expectation of near term volatility."

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   No opinions from unnamed or less reliable sources were present in the provided text.
</QuestionSource>

<QuestionSource url="https://www.cboe.com/tradable_products/vix/vix_historical_data/">
The provided text from Cboe Global Markets serves as a foundational overview of the Cboe Volatility Index (VIX). Below are the key facts and objective measurements extracted from the article relevant to understanding the index's structure and history.

### 1. Facts, Statistics, and Objective Measurements
*   **Definition and Purpose:** The VIX Index is a gauge of U.S. equity market volatility, specifically measuring the market’s expectation of **30-day volatility**.
*   **Original Methodology (1993):** When introduced in 1993, the index was designed to measure volatility implied by **at-the-money S&P 100 (OEX)** Index option prices.
*   **Updated Methodology (2003):** In 2003, Cboe and Goldman Sachs updated the index. The current VIX is based on the **S&P 500 Index (SPX)**, which is considered the core index for U.S. equities.
*   **Calculation Method:** The index estimates expected volatility by aggregating the **weighted prices of SPX puts and calls** across a wide range of strike prices.
*   **Historical Continuity:** The price history for the **Cboe S&P 100 Volatility Index (VXO)** corresponds to the values of the original 1993 version of the VIX.
*   **Data Dissemination:** Cboe calculates and disseminates dozens of volatility indices beyond the standard VIX.

### 2. Opinions from Reliable and Named Sources
*   **Cboe Global Markets / Goldman Sachs:** These entities established the 2003 methodology that is currently "widely used by financial theorists, risk managers and volatility traders alike" to measure expected volatility.
*   **Cboe Global Markets:** The organization describes the VIX as the "world’s premier gauge of U.S. equity market volatility."

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   **Data Accuracy Disclaimer:** The article contains a standard legal disclaimer noting that while the data is obtained from sources "believed to be reliable," its accuracy is not guaranteed and the data is furnished without responsibility for omissions or inaccuracies.
</QuestionSource>




YOUR TASK:
1. Analyze the question and the pre-research context
2. Identify what information a skilled forecaster would need beyond what's already available
3. Generate up to 8 search queries to fill the remaining gaps

COVERAGE DIMENSIONS (ensure your queries collectively address these):
- Background conditions: The broader environment in which this question plays out. What are the macro-level forces or trends that will influence the outcome during the resolution period (e.g. when predicting if a stock price will go up or down, it is useful to understand recent and projected market conditions).
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
- AskNews: Semantic (meaning-based) news search. Write a descriptive 1-2 sentence natural language query focusing on the underlying topic, key actors, and context. Include relevant scope: geography, industry, time period. Avoid ambiguous acronyms. Best for finding conceptually related coverage even without exact keyword matches.
- FRED: Federal Reserve Economic Data. Use a FRED series ID (e.g., "UNRATE", "CPIAUCSL") or a plain-language description (e.g., "US unemployment rate"). Returns historical data with computed statistics. Use for economic/financial data.If the question references a FRED series ID, you MUST include a (FRED) query using that exact series ID.
- yFinance: Yahoo Finance ticker symbol (e.g., "AAPL", "^GSPC"). Returns price history, fundamentals, analyst targets, and options data. Only use for stocks, indices, or ETFs.
- Google Trends: A search term (e.g., "hospital"). Returns 90-day search interest data with base rate analysis. Only use when the question specifically involves Google Trends data.

TAG each query as [HISTORICAL] (for base rates, reference classes, past data, background context) or [CURRENT] (for recent news, latest values, current developments, upcoming events). Include at least 2 of each. Queries must be appropriately worded for the tool selected.

Format your answer exactly as below. Each query on its own line. The source in parentheses, temporal tag in brackets. Do not wrap queries in quotes.

Analysis:
{Your analysis of the question, what the pre-research context already provides, what key information gaps remain, and your search strategy.}

Search queries:
1. [HISTORICAL] your query here (Google) -- Intent: what this query aims to find
2. [CURRENT] your query here (Google News) -- Intent: what this query aims to find
3. [HISTORICAL] your detailed multi-part query here (Agent) -- Intent: what this query aims to find
...
