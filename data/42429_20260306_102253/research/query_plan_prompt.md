You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will the interest in “war” change between 2026-03-06 and 2026-03-14 according to Google Trends?

Type: multiple_choice

Background:
Google Trends is a free tool from Google that shows how often particular search terms are entered into Google relative to the total search volume across different regions and time periods. One of its main features is the “interest over time” graph, which is scaled from 0 to 100. In this graph, 100 represents the peak popularity of the term during the selected time range and location, meaning the point in time when searches for that term were at their highest. A 0 does not mean no searches occurred, but rather that the search interest was too low to register compared to the peak values. Because the values are relative, the numbers for a given day can shift as new data is added or as the overall scale is recalibrated—for example, a value of 40 on one day could later appear as 35 if the relative scaling changes. This effect can be reduced by specifying fixed start and end dates in the URL, which locks the scale for that chosen period and keeps the values consistent.

The current value of the topic “war” at the time of writing this question (Mar 1, 2026) compared to the last 30 days is 100; seen at [this url](https://trends.google.com/trends/explore?geo=US&tz=0&q=war&date=2026-01-30%202026-03-01).

`{"format":"trends_interest_change_magnitude","info":{"topic":"war","trend_start":"2026-03-06","trend_end":"2026-03-14","verification_url":"https://trends.google.com/trends/explore?geo=US&tz=0&q=war&date=2026-02-12%202026-03-14"}}`

Resolution criteria:
This question resolves “Doesn't change” if the value on the timeline at [https://trends.google.com/trends/explore?geo=US&tz=0&q=war&date=2026-02-12%202026-03-14](https://trends.google.com/trends/explore?geo=US&tz=0&q=war&date=2026-02-12%202026-03-14) for 2026-03-14 is within 3 of the value at 2026-03-06. It resolves “Increases” if the value is more than 3 greater, and resolves “Decreases” if the value is more than 3 lower.

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
  "q": "war",
  "date": "2026-02-12 2026-03-14",
})
search.get_dict()
```
Note that there may be differences between the results returned by the API and the data appearing on the page. This seems to be due to the 'tz' parameter not having the intended effect in-browser. In this case, the API results will be considered authoritative.
Note that the precision of the timeline will be 1 day, so this will compare the overall interest for the whole day as determined by Google Trends.
Dates are determined in UTC.
If the data is no longer available, or the script fails, this question will be annulled or manually resolved by a moderator.

Options: ['Increases', "Doesn't change", 'Decreases']

Question metadata:
- Opened: 2026-03-06T09:53:23Z
- Resolves: 2026-03-14T20:48:01Z
- Today: 2026-03-06 (8 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://serpapi.com/">
The following summary is based on the provided documentation for **SerpApi**, the tool specified in the resolution criteria for the forecasting question.

### **1. Facts, Statistics, and Technical Capabilities**
*   **Infrastructure:** SerpApi utilizes a global network of IP addresses and a full browser cluster to execute search requests.
*   **Functionality:** The API mimics human behavior by running requests in a full browser and automatically solving CAPTCHAs.
*   **Speed:** Requests are processed immediately without a waiting period for results.
*   **Geographic Accuracy:** The service uses Google’s geolocated, encrypted parameters and routes requests through proxy servers nearest to the user's desired location to ensure data accuracy.
*   **Data Types:** The API provides structured data for various Google features, including:
    *   Regular organic results
    *   Google Maps and Local results
    *   Stories, Shopping, and Knowledge Graph
    *   Direct Answers
*   **Structured Data Points:** Extracted information includes links, addresses, tweets, prices, thumbnails, ratings, reviews, and rich snippets.
*   **Service Model:** The platform operates on month-to-month contracts with a free starting tier and scalable enterprise plans.

### **2. Legal and Compliance Positions (Named Source: SerpApi)**
*   **Legal Protection:** SerpApi asserts that the crawling and parsing of public data is protected by the **First Amendment of the United States Constitution**.
*   **Liability:** The company explicitly states that it assumes scraping and parsing liabilities for both domestic and foreign clients, provided the client's usage is legal.
*   **Prohibited Usage:** Liability coverage is void if the service is used for illegal acts, including cyber criminality, terrorism, denial of service attacks, or war crimes.

### **3. Potentially Useful Opinions from Less Reliable/Not-Named Sources**
*   **User Base:** The article claims that users are "in good company" by joining their existing client base, though specific high-profile clients are not named in this text.
*   **Reliability Claim:** The service claims to guarantee that users "get what users truly see" due to their browser-mimicking technology.
</QuestionSource>


<GoogleTrendsData term="war">
Google Trends US data for "war" (last 90 days):

Current value: 72
90-day mean: 37.0
90-day std dev: 14.2

BASE RATE ANALYSIS (using 8-day windows to match question timeframe):
- In 36% of 8-day windows, the value changed by ≤3 points ("Doesn't change")
- In 39% of 8-day windows, the value INCREASED by >3 points
- In 25% of 8-day windows, the value DECREASED by >3 points

Recent trend: increasing (last 7 days avg: 82.6 vs prior 7 days: 34.1)

DAILY VALUES (last 30 days):
Date,Value
2026-02-05,45
2026-02-06,39
2026-02-07,31
2026-02-08,33
2026-02-09,33
2026-02-10,33
2026-02-11,36
2026-02-12,36
2026-02-13,40
2026-02-14,32
2026-02-15,35
2026-02-16,35
2026-02-17,39
2026-02-18,37
2026-02-19,40
2026-02-20,34
2026-02-21,30
2026-02-22,32
2026-02-23,35
2026-02-24,33
2026-02-25,35
2026-02-26,35
2026-02-27,39
2026-02-28,100
2026-03-01,92
2026-03-02,85
2026-03-03,82
2026-03-04,74
2026-03-05,73
2026-03-06,72

Note: Google Trends values are relative (0-100 scale), not absolute search volumes.
</GoogleTrendsData>



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
