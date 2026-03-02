You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
How much will Nvidia's stock price returns exceed Apple's in these biweekly periods of Q1 2026? (Mar 16 - Mar 27)

Type: numeric

Background:
As of December 2025, Nvidia and Apple are the [1st and 2nd most valuable companies in the world](https://companiesmarketcap.com/) respectively. Nvidia's stock price has seen a rise of 33% over the past year, while Apple's stock has risen by 10%.

`{"format":"metac_reveal_and_close_in_period","info":{"post_id":41215,"question_id":42090}}`

Resolution criteria:
This question is a subquestion of a group question. This subquestion specifically pertains to (and resolves according to) the option 'Mar 16 - Mar 27'. The resolution criteria for the parent question is below. 

Each subquestion will resolve as the difference between the percent stock price return of [NVDA](https://finance.yahoo.com/quote/NVDA/history/) and that of [AAPL](https://finance.yahoo.com/quote/AAPL/history/) for the corresponding biweekly period, according to Yahoo Finance data.

Specifically, each subquestion will resolve as NVDA\_return - AAPL\_return.

Returns will be calculated as follows: If P₀ is the Adj Close price of a company stock on the last trading day or half-day *before* the start of the period and P₁ is the Adj Close price of the stock on the last trading day *of* the designated period, the percentage return will be calculated as:

$$
 \text{return} = 100 \times \frac{P1 - P0}{P0}
$$

Fine print:
* If Apple outperforms Nvidia, the corresponding subquestion will resolve as a negative number.
* If Yahoo Finance delays or ceases reporting these data or if it reports them in error, Metaculus might use alternative credible sources to resolve this question.
* Resolutions are based on the prices at the market close on the last trading day of the designated period. Further adjustments to Adj Close prices after that will not cause subquestions to re-resolve.

***

For example, for the period Jun 9 - Jun 20, the subquestion would resolve based on the following calculations:

NVDA\_P₀ = 141.71 (the Adj Close price on Jun 6)

NVDA\_P₁ = 143.85 (the Adj Close price on Jun 20)

NVDA\_return = 100 × (143.85 - 141.71) / 141.71 = 1.510

AAPL\_P₀ = 203.92 (the Adj Close price on Jun 6)

AAPL\_P₁ = 201.00 (the Adj Close price on Jun 20)

AAPL\_return = 100 × (201.00 - 203.92) / 203.92 = -1.4319

And the resolution would be 1.510 - (-1.4319) = **2.9419** percentage points (pp).

***
This question's information (resolution criteria, fine print, background info, etc) is synced with an [original identical question](https://www.metaculus.com/questions/41215) which opened on 2026-02-27 21:00:00. This question will resolve based on the resolution criteria and fine print contained above. However, if this question would resolve differently than the original question, then this question will be annulled. Additionally, if the original question's resolution could have been known before this question opened, then this question will be annulled.



Question metadata:
- Opened: 2026-03-02T21:00:00Z
- Resolves: 2026-03-28T05:00:00Z
- Today: 2026-03-02 (26 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://companiesmarketcap.com/">
**Disclaimer:** The article does not include company names alongside the market cap data — only ranks, market caps, prices, daily percentage changes, and country flags are visible in the extracted content. Therefore, it is not possible to directly identify which entries correspond to Nvidia (NVDA) or Apple (AAPL) from this table alone.

---

## Summary: Companies Ranked by Market Cap (CompaniesMarketCap.com)

This page lists the world's largest **publicly traded companies** by market capitalization. Private companies are excluded due to difficulties in valuing them.

### Key Data Points from the Top of the Rankings:
| Rank | Market Cap | Price | Daily Change | Country |
|------|-----------|-------|-------------|---------|
| 1 | $4.435 T | $182.48 | +2.99% | 🇺🇸 USA |
| 2 | $3.890 T | $264.72 | +0.20% | 🇺🇸 USA |
| 3 | $3.706 T | $306.36 | +1.63% | 🇺🇸 USA |
| 4 | $2.962 T | $398.55 | +1.48% | 🇺🇸 USA |
| 5 | $2.237 T | $208.39 | +0.77% | 🇺🇸 USA |

- The top 5 companies are all US-based, with the largest valued at **$4.435 trillion**.
- The list extends to at least **100 companies**, with the 100th ranked company having a market cap of **$178.00 billion**.
- Non-US companies begin appearing at **rank 6** (Taiwan) and **rank 7** (Saudi Arabia).

This snapshot reflects current market pricing but does **not** contain historical return data relevant to the Mar 16–27 resolution period.
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
