You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
What will be the value of "30-Year Fixed Rate FHA Mortgage Index" on 2026-03-12?

Type: numeric

Background:
The Federal Reserve Economic Data database (FRED) provides economic data from national, international, public, and private sources. The series OBMMIFHA30YF is a dataset that is tracked by the FRED API. It represents the 30-year fixed rate FHA mortgage index. The title of the series is "30-Year Fixed Rate FHA Mortgage Index". The last data point on the graph (as of creation of this question) is from 2026-02-26 and has a value of 5.903. The units of the series are "Percent". The update frequency of the series is "Daily". The seasonal adjustment of the series is "Not Seasonally Adjusted". An interactive graph for the series can be found [here](https://fred.stlouisfed.org/series/OBMMIFHA30YF). Below are the notes attached to the series:

> This index includes rate locks from Federal Housing Authority loans.
> 
> Optimal Blue Mortgage Market Indices (https://www2.optimalblue.com/obmmi/)™ (OBMMI™) is calculated from actual locked rates with consumers across over one-third of all mortgage transactions nationwide. OBMMI includes multiple mortgage pricing indices developed around the most popular products and specific borrower and loan level attributes.
> 
> Each index is calculated as the average of all appropriate rate locks locked through the Optimal Blue product eligibility and pricing engine on a given day. More details about methodology and definitions are available here (https://www2.optimalblue.com/obmmi/).

`{"format":"fred_value_at_time","info":{"series_id":"OBMMIFHA30YF"}}`

Resolution criteria:
Resolves to the value found on the FRED API for the series OBMMIFHA30YF once the data is published.

Fine print:
A script will be used to determine the resolution of this question. It will paginate through the data found at the API endpoint `https://api.stlouisfed.org/fred/series/observations?series_id=OBMMIFHA30YF`. This endpoint includes the latest data for the series. The latest revised data will be used when the resolution is assessed. The datapoint matching 2026-03-12 will be used to determine the resolution of this question.

A datapoint matches if:
1. The series is updated daily and the date of the datapoint is within 1 day previous to the resolution date.
2. The series is updated weekly and the date of the datapoint is within 7 days previous to the resolution date.
3. The series is updated monthly and the date of the datapoint is within 31 days previous to the resolution date.

If the datapoint is clearly skipped, or no datapoint is found after 2 weeks of checking then the question will be annulled.



Question metadata:
- Opened: 2026-03-04T04:08:08Z
- Resolves: 2026-03-12T19:16:34Z
- Today: 2026-03-04 (8 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://fred.stlouisfed.org/series/OBMMIFHA30YF">
## Summary of Article: 30-Year Fixed Rate FHA Mortgage Index (OBMMIFHA30YF)

**Source:** FRED, Federal Reserve Bank of St. Louis (data sourced from Optimal Blue)

### Key Facts:

- **Series Name:** 30-Year Fixed Rate FHA Mortgage Index (OBMMIFHA30YF)
- **Units:** Percent, Not Seasonally Adjusted
- **Frequency:** Daily
- **Release:** Optimal Blue Mortgage Market Indices (OBMMI™)

### Methodology:
- The index tracks rate locks specifically from **Federal Housing Authority (FHA) loans**
- OBMMI™ is calculated from **actual locked rates with consumers** across more than one-third of all mortgage transactions nationwide
- Each index value represents the **average of all appropriate rate locks** processed through the Optimal Blue product eligibility and pricing engine on a given day
- Data covers multiple mortgage pricing indices built around popular products and specific borrower/loan-level attributes

### Data Notes:
- Data is subject to revision
- The series allows for both automatic updates and static time frame views

---

**Disclaimer:** The article is largely descriptive/methodological in nature and does not contain specific recent data points, trend analysis, or forward-looking commentary. No numerical values or recent index readings are provided within the article itself.
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
