You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
As of April 30, 2026, what will be the cumulative number of people detected arriving in the UK in small boats in 2026?

Type: multiple_choice

Background:
Cumulative small boat arrivals are a high-salience operational and political metric for UK border policy, asylum processing capacity, and enforcement strategy.

`{"format":"bot_tournament_question","info":{"hash_id":"443aaf6af8122063","sheet_id":259.0}}`

Resolution criteria:
This question resolves to the option whose range contains the cumulative total number of people detected arriving in the UK in small boats from January 1, 2026 through April 30, 2026 (inclusive), as recorded in the Home Office small boats time series dataset available before May 1, 2026. The primary source is the Home Office dataset file at https://assets.publishing.service.gov.uk/media/6793689a5dc1be141475ff84/small_boats_time_series.ods.

Fine print:
Compute the cumulative total by summing the daily “arrivals” (people detected arriving) values for all dates from January 1, 2026 through April 30, 2026 inclusive, using the values in the primary dataset as available before May 1, 2026. If the dataset is revised after May 1, 2026, ignore those later revisions. If the primary dataset is unavailable at resolution time, resolve using credible sources per https://www.metaculus.com/faq/#definitions. Candidate Sources: UK Home Office small boat activity statistics landing page at https://www.gov.uk/government/statistics/small-boat-activity

Options: ['0–5,000', '5,001–10,000', '10,001–20,000', '20,001+']

Question metadata:
- Opened: 2026-03-06T03:00:00Z
- Resolves: 2026-04-30T00:00:00Z
- Today: 2026-03-06 (55 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.

No pre-research context available.



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
