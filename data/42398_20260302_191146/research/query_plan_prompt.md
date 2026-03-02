You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
What will be the value of "Nikkei Stock Average, Nikkei 225" on 2026-03-11?

Type: numeric

Background:
The Federal Reserve Economic Data database (FRED) provides economic data from national, international, public, and private sources. The series NIKKEI225 is a dataset that is tracked by the FRED API. It represents the Nikkei 225 Stock Average, which represent the daily index value at market close. The title of the series is "Nikkei Stock Average, Nikkei 225". The last data point on the graph (as of creation of this question) is from 2026-02-27 and has a value of 58850.27. The units of the series are "Index". The update frequency of the series is "Daily". The seasonal adjustment of the series is "Not Seasonally Adjusted". An interactive graph for the series can be found [here](https://fred.stlouisfed.org/series/NIKKEI225). Below are the notes attached to the series:

> The observations for the Nikkei Stock Average, Nikkei 225 represent the daily index value at market close.
> 
> Nikkei 225 is the major stock market index comprising of 225 highly liquid stocks of the Tokyo Stock Exchange (TSE).
> 
> For in depth information, visit here (http://indexes.nikkei.co.jp/nkave/archives/faq/faq_nikkei_stock_average_en.pdf).
> 
> Copyright, 2016, Nikkei Inc. Reprinted with permission.
> 
> Downloading the data for research reports or research projects is permitted.
> 
> However, if you wish to redistribute the data itself or research reports (information with Nikkei data) to the third parties/persons, the user shall report back to the Nikkei, Inc for permission.

`{"format":"fred_value_at_time","info":{"series_id":"NIKKEI225"}}`

Resolution criteria:
Resolves to the value found on the FRED API for the series NIKKEI225 once the data is published.

Fine print:
A script will be used to determine the resolution of this question. It will paginate through the data found at the API endpoint `https://api.stlouisfed.org/fred/series/observations?series_id=NIKKEI225`. This endpoint includes the latest data for the series. The latest revised data will be used when the resolution is assessed. The datapoint matching 2026-03-11 will be used to determine the resolution of this question.

A datapoint matches if:
1. The series is updated daily and the date of the datapoint is within 1 day previous to the resolution date.
2. The series is updated weekly and the date of the datapoint is within 7 days previous to the resolution date.
3. The series is updated monthly and the date of the datapoint is within 31 days previous to the resolution date.

If the datapoint is clearly skipped, or no datapoint is found after 2 weeks of checking then the question will be annulled.



Question metadata:
- Opened: 2026-03-02T19:09:43Z
- Resolves: 2026-03-11T22:37:02Z
- Today: 2026-03-02 (9 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://fred.stlouisfed.org/series/NIKKEI225">
## Summary of FRED NIKKEI225 Series Data

**Source:** Federal Reserve Bank of St. Louis (FRED), data provided by Nikkei Industry Research Institute

### Key Data Points (Most Recent Observations)
The article provides the following recent daily closing values for the Nikkei 225:

| Date | Index Value |
|------|------------|
| 2026-03-02 | 58,057.24 |
| 2026-02-27 | 58,850.27 |
| 2026-02-26 | 58,753.39 |
| 2026-02-25 | 58,583.12 |
| 2026-02-24 | 57,321.09 |

### Series Characteristics
- **Units:** Index (Not Seasonally Adjusted)
- **Frequency:** Daily (market close values)
- **Coverage:** 225 highly liquid stocks listed on the Tokyo Stock Exchange (TSE)

### Notable Observations
- The most recent data point available is **2026-03-02 at 58,057.24**, representing a **decline** from the prior trading day (2026-02-27: 58,850.27), a drop of approximately **793 points**.
- The broader recent trend shows values generally ranging between ~57,321 and ~58,850 over the five most recent trading days shown.

**Disclaimer:** The article only provides the five most recent data points; no broader historical trend data or analytical commentary was included in the extracted content.
</QuestionSource>




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
