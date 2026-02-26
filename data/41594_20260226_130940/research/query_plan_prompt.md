You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
Will the United States attack Iran before April 2026?

Type: binary

Background:
In 1979, the people of Iran [overthrew](https://en.wikipedia.org/wiki/Iranian_Revolution) the United States–backed Shah Mohammad Reza Pahlavi and installed an Islamic government, [relations between the two countries](https://en.wikipedia.org/wiki/Iran%E2%80%93United_States_relations) have since ranged from hostile to non-existent ever since.

Decades later, in his first term, U.S. President Donald Trump [increased pressure on Iran](https://en.wikipedia.org/wiki/Iran%E2%80%93United_States_relations_during_the_first_Trump_administration) by means of sanctions, withdrew from an [international agreement](https://en.wikipedia.org/wiki/Joint_Comprehensive_Plan_of_Action) to limit Iran's nuclear program, and [assassinated](https://en.wikipedia.org/wiki/Assassination_of_Qasem_Soleimani) the highest-ranking Iranian military official while they were in Iraq.

In June 2025, Israel launched an attack on Iran's military and nuclear facilities, sparking a [twelve-day war](https://en.wikipedia.org/wiki/Iran%E2%80%93Israel_war) between the countries, which ended shortly after the U.S. [dropped "bunker-buster" bombs](https://en.wikipedia.org/wiki/United_States_strikes_on_Iranian_nuclear_sites) on three Iranian nuclear sites.

In December 2025, [protests](https://en.wikipedia.org/wiki/2025%E2%80%932026_Iranian_protests) erupted across Iran in what has been described as the largest popular demonstrations in the country since the 1979 revolution. The protests take place in the context of an [economic crisis](https://en.wikipedia.org/wiki/Iranian_economic_crisis) exacerbated by international sanctions, while the Iranian government has responded by [killing thousands of protesters](https://en.wikipedia.org/wiki/2026_Iran_massacres).&#x20;

U.S. President Trump has previously [threatened](https://www.reuters.com/world/middle-east/iran-warns-retaliation-if-trump-strikes-us-withdraws-some-personnel-bases-2026-01-14/) that the U.S. would intervene on behalf of the protesters, while he has also called for ["new leadership" for Iran](https://www.politico.com/news/2026/01/17/trump-to-politico-its-time-to-look-for-new-leadership-in-iran-00735528). Reza Pahlavi, the son of the deposed shah, [attempted to position](https://apnews.com/article/iran-protests-reza-pahlavi-trump-shah-63348442feefaaf1cdd7fffc142b2062) himself as a future leader of a secular Iranian state.

[According to Sentinel](https://blog.sentinel-team.org/p/trump-administration-mulls-strikes), a foresight team that aims to anticipate large-scale catastrophes:

> Forecasters think there’s a 59% chance (55% to 65%) that the US strikes Iranian territory by March 31, 2026, and a 26.5% chance (10% to 51%) that Ayatollah Khamenei is out of power by then, for any reason (including death). Last week, they gave an aggregate estimate of 43% that the Iranian regime will fall by the end of 2026. Some readers, including some sharp prediction market traders, think those probabilities are too high.

Resolution criteria:
This question will resolve as **Yes** if, before April 1, 2026, the United States carries out a military attack against Iran's territory or military personnel, according to credible sources.

Fine print:
To qualify for this question, the attack must physically affect Iran's territory or military personnel: cyberattacks, warning shots in international waters, or other actions without immediate physical impact will not count.

If it is disputed whether the United States is responsible for an attack, this question will refer to credible sources or may resolve as ambiguous.



Question metadata:
- Opened: 2026-01-21T17:00:00Z
- Resolves: 2026-04-01T00:00:00Z
- Today: 2026-02-26 (34 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://en.wikipedia.org/wiki/Iranian_Revolution">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</QuestionSource>

<QuestionSource url="https://en.wikipedia.org/wiki/Iran%E2%80%93United_States_relations">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</QuestionSource>

<QuestionSource url="https://en.wikipedia.org/wiki/Iran%E2%80%93United_States_relations_during_the_first_Trump_administration">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</QuestionSource>

<QuestionSource url="https://en.wikipedia.org/wiki/Joint_Comprehensive_Plan_of_Action">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</QuestionSource>

<QuestionSource url="https://en.wikipedia.org/wiki/Assassination_of_Qasem_Soleimani">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</QuestionSource>




YOUR TASK:
1. Analyze the question and the pre-research context
2. Identify what information a skilled forecaster would need beyond what's already available
3. Generate 10 search queries to fill the remaining gaps

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

AVAILABLE TOOLS:
- Google: Keyword search. Write short queries (max 6 words) using terms likely to appear on relevant web pages. Best for reference pages, datasets, official reports.
- Google News: Keyword search over recent news articles. Max 6 words. Best for breaking news, recent events, and current developments.
- Agent: Your query will be processed by a reasoning model with web search capability. Write a detailed, multi-part query of up to 3 sentences. Best for complex questions needing synthesis across sources, base rate computation, or multi-factor analysis.
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
