You are a research planner for a forecasting question. Your task is to design a search strategy that gives forecasters the best possible evidence base.

QUESTION:
When will Claude Plays Pokemon beat the first Pokémon game? (2026)

Type: numeric

Background:
Games have been a benchmark for computers and artificial intelligence for decades but there's been [an acceleration in the games that machine learning succeeding in beating](https://en.wikipedia.org/wiki/Machine_learning_in_video_games "an acceleration in the games that machine learning succeeding in beating"). Models like [OpenAI Five]() have brought to light the possibility that human players may soon be unable to beat AIs in any game setting.

Recent advances in AI have also allowed general purpose models like Anthropic’s Claude to perform complex reasoning tasks, including long term thinking and strategic decision-making. The first generation of Pokémon games are often used as benchmarks to compare the capability of many systems as it presents unique reasoning and agency challenges due to its combination of menu-based combat, short and long-term intersecting gameplay loops and in-game randomness.

Inspired by the famous [Twitch Plays Pokémon](https://en.wikipedia.org/wiki/Twitch_Plays_Pok%C3%A9mon), [Claude Plays Pokemon](https://www.twitch.tv/claudeplayspokemon "Claude Plays Pokemon") is an AI experiment with the Claude LLM to try and beat the first generation of Pokémon games.

In 2025, Claude made a lot of progress and went from being infinitely stuck in Mt Moon to being close to finishing the game. [This previous question](https://www.metaculus.com/questions/35956/when-will-claude-plays-pokemon-beat-the-first-pokemon-game/#comment-622377) was asking whether this would happen in 2025 and includes relevant information.

Resolution criteria:
This question resolves as the date on which [Claude Plays Pokemon](https://www.twitch.tv/claudeplayspokemon) successfully completes a full playthrough of the Pokémon game it plays on stream by reaching and defeating the Champion (Blue) at the Pokémon League.

The resolution will be based on direct confirmation from the Twitch stream, the organizer of the experiment, or credible sources.

Fine print:
* "Finishing" the game is defined for the purposes of this question as reaching the end of the main story (defeating the Elite Four and Champion), not completing the Pokédex or any post-game content.
* The current game played is a modded version of Pokémon Red. Further modifications to the game are irrelevant as long as the organizer maintains the same stream, and that the base game is still one of the first generation of Pokémon games or their remakes (as of early 2025, these are Blue, Red, Yellow, LeafGreen, FireRed).
* The AI does not have to be the current version of Claude, any AI by Anthropic would qualify.&#x20;
* The Claude Plays Pokemon Twitch stream is the only experience that matters for resolution, if Anthropic or any other actor announces that Claude has been able to beat a Pokémon game, this will not resolve the question.



Question metadata:
- Opened: 2026-01-18T17:48:12Z
- Resolves: 2026-10-01T01:00:00Z
- Today: 2026-02-26 (217 days until resolution)

PRE-RESEARCH CONTEXT:
The following information has already been gathered from sources referenced in the question. Use this to avoid redundant queries and to identify what additional research is needed.


<QuestionSource url="https://en.wikipedia.org/wiki/Twitch_Plays_Pok%C3%A9mon">
## Summary: Twitch Plays Pokémon

**Note:** This article is about *Twitch Plays Pokémon* (TPP), a crowdsourced experiment from 2014, and is **not directly about Claude Plays Pokémon**. Its relevance to the forecasting question is primarily as background/inspiration context.

### Key Facts

- TPP launched **February 12, 2014**, starting with Pokémon Red, developed by an anonymous Australian programmer using an IRC bot and Game Boy emulator.
- Pokémon Red was **completed on March 1, 2014** — after **more than 16 continuous days** of gameplay — with over **1.16 million participants** and peak simultaneous participation of 121,000.
- The stream holds a **Guinness World Record** for "most users to input a command to play a live streamed video game" (1,165,140 participants).

### Mechanics & Challenges
- Commands from chat were parsed and sent directly to the emulator; the chaotic, crowdsourced nature made navigation (mazes, ledges, menus) extremely difficult.
- A **Democracy mode** (majority-vote input) was introduced mid-run to help with difficult puzzles, alongside the original **Anarchy mode**.

### Relevance to Claude Plays Pokémon
- TPP is explicitly cited as the **direct inspiration** for the Claude Plays Pokémon experiment.
- The article notes that Pokémon Red was chosen partly because "even when played very poorly it is difficult not to make progress," due to its forgiving turn-based structure — a relevant baseline for assessing AI performance.
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
