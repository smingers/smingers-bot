You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will US existing home sales (seasonally adjusted annual rate) for March 2026 be at least 4.0 million?

Type: binary

Background:
This forecasts housing-market transaction volume, a key channel for consumption, credit demand, and construction-related activity.

`{"format":"bot_tournament_question","info":{"hash_id":"0fcf1dc94baf791f","sheet_id":330.1}}`

Resolution criteria:
This question resolves to yes if the National Association of Realtors reports March 2026 existing home sales at a seasonally adjusted annual rate of 4.0 million or higher in its first publication reporting March 2026, released before May 1, 2026. This question resolves to no if the first reported March 2026 SAAR is below 4.0 million. The value will be taken from NAR’s Existing-Home Sales page at https://www.nar.realtor/research-and-statistics/housing-statistics/existing-home-sales

Fine print:
Use the first reported March 2026 SAAR (ignore later revisions). Use the headline “Existing-home sales” SAAR level. Candidate Sources: NAR press release linked from the Existing-Home Sales page (backup) https://www.nar.realtor/newsroom | FRED series EXHOSLUSM495S (for cross-check only) https://fred.stlouisfed.org/series/EXHOSLUSM495S



Question metadata:
- Opened: 2026-03-07T03:00:00Z
- Resolves: 2026-04-01T00:00:00Z
- Today: 2026-03-07 (25 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://www.nar.realtor/research-and-statistics/housing-statistics/existing-home-sales">
The following summary extracts key information from the NAR article dated February 12, 2026, relevant to the forecast of March 2026 existing home sales.

### 1. Facts, Statistics, and Objective Measurements
*   **January 2026 Performance:** Existing-home sales fell by **8.4%** in January 2026.
*   **Regional Trends:** Sales decreased both month-over-month and year-over-year across all four major U.S. regions (West, Midwest, South, and Northeast).
*   **Affordability Metrics:** According to the NAR Housing Affordability Index, housing is currently at its **most affordable level since March 2022**.
*   **Economic Drivers:** Wage gains are currently outpacing home price growth, and mortgage rates are lower than they were one year ago.
*   **Inventory:** Housing supply remains "quite low" and has not kept pace with other economic improvements.
*   **Upcoming Data:** February 2026 sales data is scheduled for release on Tuesday, March 10, 2026.

### 2. Opinions from Reliable and Named Sources
*   **Dr. Lawrence Yun (NAR Chief Economist):**
    *   **Weather Impact:** Yun notes that "below-normal temperatures and above-normal precipitation" in January make it difficult to determine if the 8.4% sales drop is an "aberration" or driven by underlying market factors.
    *   **Market Outlook:** He describes the sales decrease as "disappointing" but highlights that affordability conditions are improving.
    *   **Supply Constraints:** He explicitly identifies low supply as a primary headwind despite better affordability.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   *None provided in the text.*
</QuestionSource>

<QuestionSource url="https://fred.stlouisfed.org/series/EXHOSLUSM495S">
The following summary is based on the provided data from the Federal Reserve Bank of St. Louis (FRED) regarding National Association of Realtors (NAR) existing home sales.

### **1. Facts, Statistics, and Objective Measurements**
The article provides the Seasonally Adjusted Annual Rate (SAAR) for existing home sales for the five months leading up to the target period. The data points are as follows:

*   **January 2026:** 3,910,000
*   **December 2025:** 4,270,000
*   **November 2025:** 4,090,000
*   **October 2025:** 4,110,000
*   **September 2025:** 4,080,000

**Key Definitions and Methodology:**
*   **Scope:** The data measures transaction volume for existing single-family homes, condos, and co-ops (excluding new construction).
*   **Source:** The National Association of Realtors (NAR) collects this data from a representative sample of local boards and multiple listing services (MLS).
*   **Frequency:** Monthly, reported as a Seasonally Adjusted Annual Rate (SAAR).
*   **Revisions:** The source notes that all data are subject to revision.

### **2. Opinions from Reliable and Named Sources**
*   **National Association of Realtors (NAR):** As the primary source of the data, the NAR defines "existing homes" specifically as those that were owned and occupied prior to being placed on the market. They emphasize that their indicators are based on a representative sample across the U.S. in aggregate and by census region.

### **3. Potentially Useful Opinions from Less Reliable/Not-Named Sources**
*   The provided text does not contain opinions from unnamed or less reliable sources; it is strictly a data report and methodological overview from FRED and the NAR.
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
