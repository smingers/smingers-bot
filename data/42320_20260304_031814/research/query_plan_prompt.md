You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will the Maldives hold its 2026 local elections before April 5, 2026?

Type: binary

Background:
This checks whether scheduled local elections proceed, which matters for governance and political momentum.

`{"format":"bot_tournament_question","info":{"hash_id":"660b197b1899cc94","sheet_id":284.1}}`

Resolution criteria:
This question resolves to yes if the election date for the 2026 Maldivian local elections occurs before April 5, 2026. This question resolves to no otherwise. The primary source is https://en.wikipedia.org/wiki/2026_Maldivian_local_elections

Fine print:
“Held” refers to the election day occurring, not final certification. If Wikipedia is unavailable or does not clearly state the election date, resolve using the Maldives Elections Commission official notices or results. Candidate Sources: Maldives Elections Commission https://www.elections.gov.mv/en/



Question metadata:
- Opened: 2026-03-04T03:00:00Z
- Resolves: 2026-04-05T00:00:00Z
- Today: 2026-03-04 (32 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://www.elections.gov.mv/en/">
## Summary of Elections Commission of Maldives Website Content

**Source:** Elections Commission of Maldives (elections.gov.mv)
**Note:** The extracted content appears to be a partial rendering of the website's interface/navigation rather than a full detailed article. Key specific dates (e.g., the exact election day) are not explicitly stated in the extracted text.

---

### Key Facts Extracted:

1. **Countdown Timer:** The website displays a countdown of **"30 Days 15 Hrs 41 Min"** for three simultaneous events:
   - **Local Council Election 2026**
   - **Women's Development Committee (WDC) Election 2026**
   - **Public Referendum Vote 2026**

2. **Recent Election-Related Activities:**
   - **20 Feb 2026:** A delegation led by President Mohamed Zahid observed Thailand's 2026 election process.
   - **18 Jan 2026:** Voting boxes for the 2026 Local Council Election and WDC Election announced.
   - **18 Jan 2026:** Voter registration updates published; complaints submission opened.
   - **18 Jan 2026:** Accreditation of international observers announced.
   - **17 Jan 2026:** Online portal opened for candidate application forms.
   - **3 Jan 2026:** Training of trainers program underway for 2026 elections.

### Inference from Countdown:
If the content was captured approximately 30 days before the election (dated within ~30 days of the article's retrieval), the election date would fall **roughly 30 days after the article's capture date**, though the exact election date is **not explicitly stated** in the extracted content.
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
