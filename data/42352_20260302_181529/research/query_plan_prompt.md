You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
How much will Crude Oil Futures total price returns exceed S&P 500 Futures's in these biweekly periods of Q1 2026? (Mar 16 - Mar 27)

Type: numeric

Background:
Crude Oil Futures directly reflect global energy demand, transportation costs, and geopolitical tensions affecting oil production. Traders and analysts use these futures to gauge economic health, predict inflation, and understand supply chain dynamics. Significant price movements can signal economic slowdowns, changes in global trade, or disruptions in major oil-producing regions like the Middle East, Russia, and North America.

[S\&P 500](https://en.wikipedia.org/wiki/S%26P_500) represents 500 of the largest publicly traded U.S. companies across diverse sectors. It captures the broader market sentiment, including technology, healthcare, financial, and industrial giants like Apple, Microsoft, Amazon, JPMorgan Chase, and Johnson & Johnson. The index is market-cap weighted, meaning larger companies have a more significant impact on its movement.

`{"format":"metac_reveal_and_close_in_period","info":{"post_id":41218,"question_id":42086}}`

Resolution criteria:
This question is a subquestion of a group question. This subquestion specifically pertains to (and resolves according to) the option 'Mar 16 - Mar 27'. The resolution criteria for the parent question is below. 

Each subquestion will resolve as the difference between the percent total price return of [Crude Oil Futures (CL)](https://finance.yahoo.com/quote/CL%3DF/history/) and that of [S\&P 500 Futures (ES)](https://finance.yahoo.com/quote/ES%3DF/history/) for the corresponding biweekly period, according to Yahoo Finance data.

Specifically, each subquestion will resolve as CL\_return - ES\_return.

Returns will be calculated as follows: If P₀ is the Close price of a company stock on the last trading day or half-day *before* the start of the period and P₁ is the Close price of the stock on the last trading day *of* the designated period, the percentage return will be calculated as:

$$
 \text{return} = 100 \times \frac{P1 - P0}{P0}
$$

Fine print:
* If ES outperforms CL, the corresponding subquestion will resolve as a negative number.
* If Yahoo Finance delays or ceases reporting these data or if it reports them in error, Metaculus might use alternative credible sources to resolve this question.

***

For example, for the period Jun 9 - Jun 20, the subquestion would resolve based on the following calculations:

CL\_P₀ = 64.58 (the Close price on Jun 6)

CL\_P₁ = 74.93 (the Close price on Jun 20)

CL\_return = 100 × (74.93 - 64.58) / 64.58 = 16.0266

ES\_P₀ = 6,006.75 (the Close price on Jun 6)

ES\_P₁ = 6,010.21 (the Close price on Jun 20)

ES\_return = 100 × (6,010.21 - 6,006.75) / 6,006.75 = 0.0576

And the resolution would be 16.0266 - 0.0576 = **15.9690** percentage points (pp).

***
This question's information (resolution criteria, fine print, background info, etc) is synced with an [original identical question](https://www.metaculus.com/questions/41218) which opened on 2026-02-27 21:00:00. This question will resolve based on the resolution criteria and fine print contained above. However, if this question would resolve differently than the original question, then this question will be annulled. Additionally, if the original question's resolution could have been known before this question opened, then this question will be annulled.



Question metadata:
- Opened: 2026-03-02T18:00:00Z
- Resolves: 2026-03-28T05:00:00Z
- Today: 2026-03-02 (26 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://en.wikipedia.org/wiki/S%26P_500">
## Summary of S&P 500 Wikipedia Article

### Overview
The S&P 500 is a stock market index tracking 500 leading U.S.-listed companies, representing approximately 80% of total U.S. public company market capitalization, with an aggregate market cap exceeding **$61.1 trillion as of December 31, 2025**.

### Index Composition
- The index is **public float/capitalization-weighted**
- The **10 largest components** account for ~38% of market cap; the 50 largest account for ~60%
- **As of January 2026**, top 10 components by weighting: Nvidia (7.17%), Alphabet (6.39%), Apple (5.86%), Microsoft (5.33%), Amazon (3.98%), Broadcom (2.51%), Meta (2.49%), Tesla (2.31%), Berkshire Hathaway (1.68%), Eli Lilly (1.55%)
- Companies derive **72% of revenues from the U.S.** and 28% internationally

### Historical Performance
- Since 1926, compound annual growth rate (including dividends): **~9.8% (~6% after inflation)**
- The index posts annual increases **70% of the time**
- **Record closing high of 6,932.05** was set on **December 24, 2025**
- The index fell to a low of **4,982.77 on April 8** (intra-year correction) before recovering
- The S&P 500 **rose above 7,000 points for the first time on January 28, 2026**

### Derivatives (Relevant to Question)
- The **Chicago Mercantile Exchange (CME)** offers S&P 500 futures contracts (ES), described as the exchange's **most popular product**
- The **S&P E-mini futures contract** was introduced on **September 9, 1997**

---
*Note: This article provides general background on the S&P 500 index but contains no specific data relevant to the Mar 16–Mar 27, 2026 resolution period or comparative crude oil performance.*
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
