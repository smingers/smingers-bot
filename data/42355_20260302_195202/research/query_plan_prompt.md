You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
How much will Nasdaq-100 Futures total price returns exceed S&P 500 Futures in these biweekly periods of Q1 2026? (Mar 16 - Mar 27)

Type: numeric

Background:
[Nasdaq-100](https://en.wikipedia.org/wiki/Nasdaq-100) focuses exclusively on 100 of the largest non-financial companies listed on the Nasdaq exchange, heavily weighted towards technology and innovation. This index includes tech titans like Apple (approximately 12-15% of the index), Microsoft, Amazon, NVIDIA, and Alphabet (Google), making it a prime indicator of the tech sector's performance and innovation economy.

[S\&P 500](https://en.wikipedia.org/wiki/S%26P_500) represents 500 of the largest publicly traded U.S. companies across diverse sectors. It captures the broader market sentiment, including technology, healthcare, financial, and industrial giants like Apple, Microsoft, Amazon, JPMorgan Chase, and Johnson & Johnson. The index is market-cap weighted, meaning larger companies have a more significant impact on its movement.

`{"format":"metac_reveal_and_close_in_period","info":{"post_id":41219,"question_id":42089}}`

Resolution criteria:
This question is a subquestion of a group question. This subquestion specifically pertains to (and resolves according to) the option 'Mar 16 - Mar 27'. The resolution criteria for the parent question is below. 

Each subquestion will resolve as the difference between the percent total price return of [Nasdaq-100 Futures (NQ)](https://finance.yahoo.com/quote/NQ%3DF/history/) and that of [S\&P 500 Futures (ES)](https://finance.yahoo.com/quote/ES%3DF/history/) for the corresponding biweekly period, according to Yahoo Finance data.

Specifically, each subquestion will resolve as NQ\_return - ES\_return.

Returns will be calculated as follows: If P₀ is the Close price of a company stock on the last trading day or half-day *before* the start of the period and P₁ is the Close price of the stock on the last trading day *of* the designated period, the percentage return will be calculated as:

$$
 \text{return} = 100 \times \frac{P1 - P0}{P0}
$$

Fine print:
* If ES outperforms NQ, the corresponding subquestion will resolve as a negative number.
* If Yahoo Finance delays or ceases reporting these data or if it reports them in error, Metaculus might use alternative credible sources to resolve this question.

***

For example, for the period Jun 9 - Jun 20, the subquestion would resolve based on the following calculations:

NQ\_P₀ = 21,789.50 (the Close price on Jun 6)

NQ\_P₁ = 21,889.89 (the Close price on Jun 20)

NQ\_return = 100 × (21,889.89 - 21,789.50) / 21,789.50 = 0.4607

ES\_P₀ = 6,006.75 (the Close price on Jun 6)

ES\_P₁ = 6,010.21 (the Close price on Jun 20)

ES\_return = 100 × (6,010.21 - 6,006.75) / 6,006.75 = 0.0576

And the resolution would be 0.4607 - 0.0576 = **0.4031** percentage points (pp).

***
This question's information (resolution criteria, fine print, background info, etc) is synced with an [original identical question](https://www.metaculus.com/questions/41219) which opened on 2026-02-27 21:00:00. This question will resolve based on the resolution criteria and fine print contained above. However, if this question would resolve differently than the original question, then this question will be annulled. Additionally, if the original question's resolution could have been known before this question opened, then this question will be annulled.



Question metadata:
- Opened: 2026-03-02T19:30:00Z
- Resolves: 2026-03-28T05:00:00Z
- Today: 2026-03-02 (26 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://en.wikipedia.org/wiki/Nasdaq-100">
## Summary of Nasdaq-100 Wikipedia Article

This article provides a comprehensive overview of the Nasdaq-100 (NDX) index. Key points relevant to the forecasting question include:

### Structure & Composition
- Comprises **100 of the largest non-financial companies** listed on Nasdaq
- Uses a **modified capitalization-weighted methodology** with rules capping the influence of largest components
- **Heavily weighted toward technology**, including tech titans like Apple, Microsoft, Amazon, NVIDIA, and Alphabet
- Excludes financial companies (which are tracked separately in the Nasdaq Financial-100)
- Includes **10 foreign-incorporated companies** as of December 2025

### Performance History
- Fell **78% during the dot-com bust (2002)** after peaking above 4,700
- Experienced significant losses during the **2008 financial crisis**
- Recovered strongly through quantitative easing periods

### Index Mechanics
- **Rebalanced quarterly** if concentration thresholds are breached (single company >24%, or top companies >48%)
- **Rebalanced annually** if one company exceeds 15% or top five exceed 40%
- Annual re-ranking each December

### Futures Trading
- E-mini futures trade on the **Chicago Mercantile Exchange under ticker NQ** — directly relevant to the resolution of this question

---
**Note:** This article contains no information specific to the Mar 16–Mar 27, 2026 period or recent price movements relevant to resolving the forecasting question.
</QuestionSource>

<QuestionSource url="https://en.wikipedia.org/wiki/S%26P_500">
## Summary of Article: S&P 500 (Wikipedia)

**Note:** This article is a general Wikipedia overview of the S&P 500 index and does not contain information specifically relevant to the Mar 16–Mar 27, 2026 biweekly period or NQ vs. ES futures performance comparisons.

---

### Key Facts

**Index Composition & Structure:**
- Tracks 500 leading U.S.-listed companies; covers ~80% of total U.S. public market cap (~$61.1 trillion as of Dec 31, 2025)
- Market-cap weighted; top 10 companies = ~38% of index; top 50 = ~60%
- **Top 10 components (as of January 2026):** Nvidia (7.17%), Alphabet (6.39%), Apple (5.86%), Microsoft (5.33%), Amazon (3.98%), Broadcom (2.51%), Meta (2.49%), Tesla (2.31%), Berkshire Hathaway (1.68%), Eli Lilly (1.55%)

**Historical Performance:**
- Compound annual growth rate since 1926: ~9.8% (including dividends); ~6% after inflation
- Posts annual gains ~70% of the time; ~5% of trading days result in record highs
- **Record closing high: 6,932.05 on December 24, 2025**
- Index fell to a low of **4,982.77 on April 8** (intra-year correction of 10–20%)
- S&P 500 **rose above 7,000 for the first time on January 28, 2026**

**Derivatives Market:**
- CME offers futures contracts (ES) tracking the S&P 500, traded via open outcry or Globex platform — described as CME's most popular product

---

*This article provides no data directly relevant to the Mar 16–Mar 27, 2026 resolution period or relative NQ/ES performance.*
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
