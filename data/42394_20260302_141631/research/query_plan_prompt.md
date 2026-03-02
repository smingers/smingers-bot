You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will the interest in “reza pahlavi” change between 2026-03-02 and 2026-03-11 according to Google Trends?

Type: multiple_choice

Background:
Google Trends is a free tool from Google that shows how often particular search terms are entered into Google relative to the total search volume across different regions and time periods. One of its main features is the “interest over time” graph, which is scaled from 0 to 100. In this graph, 100 represents the peak popularity of the term during the selected time range and location, meaning the point in time when searches for that term were at their highest. A 0 does not mean no searches occurred, but rather that the search interest was too low to register compared to the peak values. Because the values are relative, the numbers for a given day can shift as new data is added or as the overall scale is recalibrated—for example, a value of 40 on one day could later appear as 35 if the relative scaling changes. This effect can be reduced by specifying fixed start and end dates in the URL, which locks the scale for that chosen period and keeps the values consistent.

The current value of the topic “reza pahlavi” at the time of writing this question (Mar 1, 2026) compared to the last 30 days is 100; seen at [this url](https://trends.google.com/trends/explore?geo=US&tz=0&q=reza%20pahlavi&date=2026-01-30%202026-03-01).

`{"format":"trends_interest_change_magnitude","info":{"topic":"reza pahlavi","trend_start":"2026-03-02","trend_end":"2026-03-11","verification_url":"https://trends.google.com/trends/explore?geo=US&tz=0&q=reza%20pahlavi&date=2026-02-09%202026-03-11"}}`

Resolution criteria:
This question resolves “Doesn't change” if the value on the timeline at [https://trends.google.com/trends/explore?geo=US&tz=0&q=reza%20pahlavi&date=2026-02-09%202026-03-11](https://trends.google.com/trends/explore?geo=US&tz=0&q=reza%20pahlavi&date=2026-02-09%202026-03-11) for 2026-03-11 is within 3 of the value at 2026-03-02. It resolves “Increases” if the value is more than 3 greater, and resolves “Decreases” if the value is more than 3 lower.

Fine print:
A script will be used to determine the resolution of this question. It will access the data on Google Trends using [SerpApi](https://serpapi.com/), and compare the height of the timeline for the two aforementioned dates. The specific python query will be structured as follows:
```
from serpapi import GoogleSearch

search = GoogleSearch(params={
  "api_key": API_KEY,
  "engine": "google_trends",
  "data_type": "TIMESERIES",
  "geo": "US",
  "tz": 0,
  "q": "reza pahlavi",
  "date": "2026-02-09 2026-03-11",
})
search.get_dict()
```
Note that there may be differences between the results returned by the API and the data appearing on the page. This seems to be due to the 'tz' parameter not having the intended effect in-browser. In this case, the API results will be considered authoritative.
Note that the precision of the timeline will be 1 day, so this will compare the overall interest for the whole day as determined by Google Trends.
Dates are determined in UTC.
If the data is no longer available, or the script fails, this question will be annulled or manually resolved by a moderator.

Options: ['Increases', "Doesn't change", 'Decreases']

Question metadata:
- Opened: 2026-03-02T14:05:26Z
- Resolves: 2026-03-11T07:41:51Z
- Today: 2026-03-02 (9 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://serpapi.com/">
**Disclaimer:** The article provided is a general marketing/landing page for SerpApi and contains no specific data about "reza pahlavi" Google Trends interest or any relevant search trend information for the dates in question.

---

## Summary: SerpApi Service Overview

The article is a promotional page for **SerpApi**, a commercial service that provides structured access to Google Search and other search engine result data. Key points include:

- **Infrastructure:** SerpApi operates a global IP network, a full browser cluster, and CAPTCHA-solving technology to mimic real human browsing behavior, ensuring results reflect what actual users see.
- **Speed:** Each API request runs immediately with no waiting period.
- **Geolocation:** Users can retrieve Google results from anywhere in the world using a "location" parameter, routed through proxy servers nearest to the desired location.
- **Data types available:** Organic results, Maps, Local, Stories, Shopping, Direct Answers, and Knowledge Graph, with rich structured data (links, addresses, prices, ratings, etc.).
- **Legal stance:** SerpApi asserts that crawling and parsing public data is protected by the First Amendment, and they assume scraping/parsing liabilities for clients, with exceptions for illegal activities.
- **Pricing:** Month-to-month contracts with a free tier, scalable paid plans, and enterprise options.

No trend data specific to "reza pahlavi" is contained in this article.
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
