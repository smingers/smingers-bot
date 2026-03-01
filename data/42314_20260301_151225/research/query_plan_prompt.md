You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will Colombia hold its 2026 parliamentary election before March 9, 2026?

Type: binary

Background:
This checks whether Colombia’s 2026 legislative electoral timeline proceeds as scheduled.

`{"format":"bot_tournament_question","info":{"hash_id":"78d52b15730970e8","sheet_id":281.1}}`

Resolution criteria:
This question resolves to yes if the election date for the 2026 Colombian parliamentary election occurs before March 9, 2026. This question resolves to no otherwise. The primary source is Wikipedia’s page for the election at https://en.wikipedia.org/wiki/2026_Colombian_parliamentary_election

Fine print:
“Held” refers to the election day occurring, not final certification.



Question metadata:
- Opened: 2026-03-01T15:00:00Z
- Resolves: 2026-03-09T00:00:00Z
- Today: 2026-03-01 (8 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://en.wikipedia.org/wiki/2026_Colombian_parliamentary_election">
## Summary: 2026 Colombian Parliamentary Election (Wikipedia)

### Key Facts

- **Scheduled Election Date:** Parliamentary elections are scheduled to be held in Colombia on **8 March 2026**, which is *before* the March 9, 2026 resolution threshold.

### Electoral System Details
- The **House of Representatives** has 183 members elected through a mix of methods:
  - 162 via proportional representation across 33 multi-member constituencies (departmental)
  - Special seats for Afro-Colombian communities (2), Indigenous communities (1), Colombian expatriates (1), PDET/CITREP peace constituencies (16), and one for the second-highest vice-presidential vote
- The **Senate** has 103 members:
  - 100 from a single nationwide constituency (proportional representation)
  - 2 from an Indigenous community constituency
  - 1 for the presidential opposition
- **Notable change:** Unlike 2018 and 2022 elections, no seats are reserved for Commons (formerly FARC) in either chamber.

### Security Context
- On **20 February 2026**, the ELN (National Liberation Army) declared a **unilateral ceasefire** specifically to allow the election to proceed.

### Relevance to Forecast Question
The article confirms the election is scheduled for **March 8, 2026**, one day before the resolution cutoff of March 9, 2026. The ELN ceasefire suggests active steps were taken to facilitate the election occurring on schedule.
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
