You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Which team will win the 2026 Six Nations Championship?

Type: multiple_choice

Background:
This forecasts the overall champion of the 2026 Six Nations, a major annual international rugby competition.

`{"format":"bot_tournament_question","info":{"hash_id":"f781606119d263ed","sheet_id":263.1}}`

Resolution criteria:
This question resolves to the option corresponding to the team ranked first in the final 2026 Six Nations table as shown on the official [2026 Six Nations Championship](https://en.wikipedia.org/wiki/2026_Six_Nations_Championship). If no champion is shown as the table leader before May 1, 2026 due to cancellation or an incomplete competition, this question will be annulled. The primary source is the official Six Nations table page: https://www.sixnationsrugby.com/en/m6n/fixtures/202600/table

Fine print:
This question resolves strictly using the final table order shown on the official table page, including any tie-breakers embedded in that table. If the official table page is unavailable, resolve using credible sources per https://www.metaculus.com/faq/#definitions and prefer sources that reproduce the official final standings. Candidate Source: https://en.wikipedia.org/wiki/2026_Six_Nations_Championship

Options: ['England', 'France', 'Ireland', 'Scotland', 'Wales', 'Italy']

Question metadata:
- Opened: 2026-02-27T06:00:00Z
- Resolves: 2026-05-01T00:00:00Z
- Today: 2026-02-27 (63 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://en.wikipedia.org/wiki/2026_Six_Nations_Championship">
## Summary: 2026 Six Nations Championship (Wikipedia Article)

**Disclaimer:** The article appears to be incomplete — Rounds 4 and 5 fixtures/results, the final standings table, and player statistics sections contain no extracted data. The summary below reflects only what was available.

---

### Overview
- The 2026 Men's Six Nations Championship (sponsored as "Guinness Men's Six Nations") runs from **5 February to 14 March 2026**, featuring England, France, Ireland, Italy, Scotland, and Wales.
- It is the **132nd season** of the competition and **27th as Six Nations**.
- **France enter as reigning champions**, having reclaimed the title from Ireland in 2025.
- Notable format change: the competition runs over a **reduced timeframe**, with only one rest week (after Round 3) instead of two.

---

### Results Through Round 3 (as of article extraction)

**Round 1:**
- France defeated Ireland (France claimed the inaugural Solidarity Trophy)
- Italy defeated their opponent (reclaimed the Cuttitta Cup; Italy's first opening-round Six Nations win since 2013)
- England played (Tom Roebuck replaced injured Feyi-Waboso)

**Round 2:**
- Ireland won (Edwin Edogbo debuted; Hollie Davidson became first woman to referee a men's Six Nations match)
- Scotland defeated England (reclaimed the Calcutta Cup)
- France defeated Wales **by a record margin** (most points France have ever scored against Wales, surpassing 51 points from 1998; lowest-ever Six Nations attendance in Cardiff: 57,744)

**Round 3:**
- **Ireland defeated England** away — Ireland's 42 points was their highest away score against England; 21-point winning margin was their biggest away win vs. England. Maro Itoje earned his 100th England cap. Ireland retained the Millennium Trophy.
- Scotland defeated Wales (retained the Doddie Weir Cup; Gabriel Hamer-Webb debuted for Wales)
- France defeated Italy (retained the Giuseppe Garibaldi Trophy; Matthieu Jalibert ruled out, Thomas Ramos earned 50th cap)

---

### Rounds 4 & 5
- **No results were available** in the extracted content. The tournament concludes with **France vs. England on 14 March 2026**.

---

### Key Observations (from available data)
- **Ireland** appear strong through Round 3, with a notable away win over England.
- **France** won Round 1 and Round 3 matches but the Round 2 result vs. Ireland (from Round 1) suggests France beat Ireland early.
- **Scotland** picked up a notable win over England (Calcutta Cup).
- **Italy** won their opening match for the first time since 2013.
- **Wales** appear to be struggling, having lost to both France (heavily) and Scotland.
- Final standings and champion are **not determinable** from the extracted content.
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
