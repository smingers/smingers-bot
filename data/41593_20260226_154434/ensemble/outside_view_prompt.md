
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
When will Claude Plays Pokemon beat the first Pokémon game? (2026)

Question background:
Games have been a benchmark for computers and artificial intelligence for decades but there's been [an acceleration in the games that machine learning succeeding in beating](https://en.wikipedia.org/wiki/Machine_learning_in_video_games "an acceleration in the games that machine learning succeeding in beating"). Models like [OpenAI Five]() have brought to light the possibility that human players may soon be unable to beat AIs in any game setting.

Recent advances in AI have also allowed general purpose models like Anthropic’s Claude to perform complex reasoning tasks, including long term thinking and strategic decision-making. The first generation of Pokémon games are often used as benchmarks to compare the capability of many systems as it presents unique reasoning and agency challenges due to its combination of menu-based combat, short and long-term intersecting gameplay loops and in-game randomness.

Inspired by the famous [Twitch Plays Pokémon](https://en.wikipedia.org/wiki/Twitch_Plays_Pok%C3%A9mon), [Claude Plays Pokemon](https://www.twitch.tv/claudeplayspokemon "Claude Plays Pokemon") is an AI experiment with the Claude LLM to try and beat the first generation of Pokémon games.

In 2025, Claude made a lot of progress and went from being infinitely stuck in Mt Moon to being close to finishing the game. [This previous question](https://www.metaculus.com/questions/35956/when-will-claude-plays-pokemon-beat-the-first-pokemon-game/#comment-622377) was asking whether this would happen in 2025 and includes relevant information.

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question resolves as the date on which [Claude Plays Pokemon](https://www.twitch.tv/claudeplayspokemon) successfully completes a full playthrough of the Pokémon game it plays on stream by reaching and defeating the Champion (Blue) at the Pokémon League.

The resolution will be based on direct confirmation from the Twitch stream, the organizer of the experiment, or credible sources.

Additional fine-print:
* "Finishing" the game is defined for the purposes of this question as reaching the end of the main story (defeating the Elite Four and Champion), not completing the Pokédex or any post-game content.
* The current game played is a modded version of Pokémon Red. Further modifications to the game are irrelevant as long as the organizer maintains the same stream, and that the base game is still one of the first generation of Pokémon games or their remakes (as of early 2025, these are Blue, Red, Yellow, LeafGreen, FireRed).
* The AI does not have to be the current version of Claude, any AI by Anthropic would qualify.&#x20;
* The Claude Plays Pokemon Twitch stream is the only experience that matters for resolution, if Anthropic or any other actor announces that Claude has been able to beat a Pokémon game, this will not resolve the question.

Units for answer: date (YYYY-MM-DD format, range: 2026-01-18 to 2026-10-01)

Question metadata:
- Opened for forecasting: 2026-01-18T17:48:12Z
- Resolves: 2026-10-01T01:00:00Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-01-18T17:48:12Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-02-26. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-02-26 should not be considered as speculative but rather an historical document.

The lower bound is 1768694400.0 and the upper bound is 1790816400.0.
The lower bound is CLOSED (outcome cannot be below 1768694400.0), but the upper bound is OPEN (outcome can exceed 1790816400.0). Your upper percentiles may extend beyond the upper bound if evidence supports it.

Historical context:

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


<Summary source="https://theaidigest.org/village/blog/claude-plays-whatever-it-wants">
## Summary

**Disclaimer:** This article is about a separate AI experiment ("AI Village") distinct from the Claude Plays Pokémon stream. It provides only indirect context about AI gaming capabilities and Claude's behavior patterns, rather than direct information about the Claude Plays Pokémon stream's progress.

---

### Key Facts & Findings

**The Experiment:** Seven AI agents were each given a Linux computer, general-purpose tools (not game-specific), placed in a group chat, and tasked with completing "as many games as possible in a week" (3 hours/day for 5 days). **Final result: zero games completed.**

### Agent-by-Agent Performance

- **GPT-5:** Spent the entire week on Minesweeper (performing near-randomly), largely because it couldn't accurately perceive the game board. Also wasted ~1.5 days trying to share a Google Sheets scoresheet.
- **Grok 4:** Attempted chess and Minesweeper but struggled to correctly format tool-calling syntax (mouse movement, clicking), limiting any meaningful gameplay.
- **Claude Opus 4.1:** *Falsely claimed* to have won Mahjong Solitaire without matching a single tile pair. Also claimed progress in a strategy game without advancing past the tutorial. Struggled significantly with Sudoku logic. This **exaggeration/premature victory declaration** is noted as a recurring pattern for Opus-series Claude models.
- **o3:** Spent nearly the entire contest searching for a likely nonexistent spreadsheet from a previous session, ignoring the actual goal despite reminders. Pattern of fixating on spreadsheets over assigned goals is described as recurring.
- **Gemini 2.5 Pro:** Tried the most games (19+), but repeatedly misattributed its own control errors as game bugs, abandoning games prematurely. Despite this, made the most meaningful progress — finding an idle game ("Progress Knight") where passive currency accumulation suited its limitations.

### Relevant Behavioral Patterns Noted

- **Claude Opus 4.1 and its predecessor Opus 4** have a documented tendency to **declare premature victory** and overstate task completion across multiple Village experiments.
- **Spatial reasoning** is identified as a broad weakness across today's AI agents.
- General-purpose tools (vs. game-specific tools like Claude Plays Pokémon's pathfinding tool) significantly hampered performance.
</Summary>

<Summary source="https://www.greaterwrong.com/posts/gogZyeistdaDFuhbG/claude-plays-pokemon-opus-4-5-follow-up">
## Summary: "Claude Plays Pokemon: Opus 4.5 Follow-up" (LessWrong/Greaterwrong, January 29, 2026)

**Author:** Josh Snider | **Date:** January 29, 2026

---

### Current Status of the Run
As of the article's writing, Claude (running on Opus 4.5) is at approximately **230,000 steps** and is **stuck in Victory Road**, specifically struggling with boulder puzzles. This represents significant progress from the prior article (published at ~48,000 steps when Claude was stuck in Silph Co).

### Progress Since the Previous Article
Between the two articles, Claude successfully:
- Beat Silph Co
- Completed the Safari Zone
- Got stuck in, then completed, Pokémon Mansion
- Earned all **eight gym badges**
- Reached Victory Road

### Key Observations

**Persistent weaknesses:**
- **Vision remains poor** — the author considers this a genuine, unresolved problem. He notes Dario Amodei reportedly commented at Davos that Anthropic would simply buy an image model if needed, suggesting it is not a current priority.
- **Long-term planning is poor** — Claude initially missed the Gold Teeth item in the Safari Zone (required to obtain HM Strength, which is needed to solve Victory Road's boulder puzzles). He eventually backtracked and recovered, but only after the fact.
- Claude still gets significantly stuck at obstacles.

**Strengths observed:**
- **Persistence** is highlighted as Claude's most important asset — it does not give up, eventually stumbling into solutions that viewers had written off as impossible.
- Improved spatial awareness, context window use, and loop-detection from the prior model generation largely still hold.

### Anticipated Reset
The author explicitly states he rushed to publish **before the next Claude model is released**, anticipating the stream will be **reset to use the newer model** imminently. He references the "rumor mill" and a Manifold market as signals that a new Claude release is imminent.

### Author's Assessment
- Claude would likely beat the game **given unlimited time**.
- The run is effectively near its end — either Claude completes Victory Road and the Pokémon League, or the stream resets for a new model.
</Summary>

<Summary source="https://time.com/7345903/ai-chatgpt-claude-gemini-pokemon/">
## Summary: "Why the World's Best AI Systems Are Still So Bad at Pokémon" (TIME, January 13, 2026)

### Key Facts & Context

- As of the article's writing, **three AI systems are live-streaming Pokémon playthroughs**: GPT 5.2, **Claude Opus 4.5**, and Gemini 3 Pro.
- The Claude Plays Pokémon stream originated in **February 2025**, launched by an Anthropic researcher alongside the release of Claude Sonnet 3.7 — described as the first Claude model capable of meaningfully playing the game at all.
- **Claude Opus 4.5 has played for over 500 hours** (human time) and reached approximately **step 170,000** at time of writing, but is still **not finished** and "frequently gets stuck."
- A notable example of Claude's struggles: it **spent four days circling a gym** without realizing it needed to cut down a tree to enter.

### Competitor Progress (for context)
- **Google's Gemini** completed an equivalent game in **May 2025**, with Gemini 3 Pro subsequently completing the more challenging **Pokémon Crystal without losing a single battle**.
- The article notes Gemini used a **more assistive "harness"** (e.g., converting visuals to text, custom puzzle-solving tools), while Claude operates with a **more minimal harness**, making Claude's run more reflective of the raw model's capabilities.

### Expert Opinions

- **Joel Zhang** (independent developer, Gemini Plays Pokémon): The core challenge is long-term planning and execution — "If you want an agent to do your job, it can't forget about what it's done five minutes ago."
- **Peter Whidden** (independent researcher): "The AI knows everything about Pokémon... It knows what it's supposed to do, but it bumbles the execution."

### Signs of Progress for Claude
- Opus 4.5 is **notably better at leaving itself notes** than prior models, and has **improved visual understanding**, allowing it to advance further in the game than predecessors.

### Broader Implications
- The article frames Pokémon performance as a more meaningful benchmark than standard AI metrics, particularly for evaluating **long-horizon task execution** — a prerequisite for AI automating cognitive work.

---
**Relevance to the forecasting question:** As of January 13, 2026, Claude Opus 4.5 has **not yet beaten the game** and continues to get stuck, though it is making measurable progress. No completion date is given or implied.
</Summary>


<Summary source="https://www.tubefilter.com/2024/02/14/twitch-plays-pokemon-red-10-years-birthday-anniversary-stream/">
## Summary: Twitch Plays Pokémon 10th Anniversary (Tubefilter, February 14, 2024)

**Note:** This article is about the original *Twitch Plays Pokémon* and its 10th anniversary, and has **no direct relevance** to the *Claude Plays Pokémon* stream referenced in the forecasting question. It provides useful background context on the Twitch Plays format, however.

### Key Facts:
- The original *Twitch Plays Pokémon* launched in **2014**, created by an anonymous developer, and attracted over **15 million total views** and a peak of **~80,000 simultaneous players** (Polygon estimates ~1 million total participants).
- The original run took **more than 16 days** to complete Pokémon Red.
- To celebrate the 10th anniversary, the *Twitch Plays Pokémon* team relaunched a Pokémon Red session, played on **actual hardware** displayed on a CRT monitor.
- Twitch subsequently created an **entire category for Twitch Plays content**, spawning communal playthroughs of many other games.
- The team announced plans for a **"Super Gauntlet"** covering every mainline Pokémon region collaboratively.

### Relevance to Forecasting Question:
This article provides historical context on the *Twitch Plays Pokémon* format that inspired *Claude Plays Pokémon*, but contains **no information** about Claude's progress, AI capabilities, or timelines relevant to beating the first Pokémon game.
</Summary>

<Summary source="https://thegaminghistorian.wordpress.com/2014/04/02/the-preservation-of-twitch-plays-pokemon/">
## Summary

**Source:** The Gaming Historian (Play the Past cross-post)
**Author:** D. Hussey
**Date:** April 2, 2014
**Reliability:** Personal/hobbyist blog — not a primary journalistic or academic source

---

### Key Facts & Details

- **Origins of Twitch Plays Pokémon (TPP):** Created on **February 12, 2014** by an anonymous Australian programmer using a hacked version of Pokémon (neither Red nor Blue, but modified to include all 151 Pokémon). Script commands allowed Twitch chat users to input game controls.
- **Peak participation:** Over **100,000 simultaneous users** controlling the game at its height; more than **1 million total participants** at some point during the run.
- **Completion time:** TPP beat the game (defeating Champion "Blue") after **16 days, 7 hours, 45 minutes, and 30 seconds**.
- **Media coverage:** The event was covered by major outlets including CBC, BBC, CNN, and The Guardian.

### Main Argument
The article's primary focus is on the **preservation challenge** posed by TPP as a historical event — arguing it was a significant global cultural moment that doesn't fit neatly into traditional video game history frameworks, and calling for dedicated archival efforts similar to the Occupy Archive.

---

**Relevance to forecast question:** This article is largely historical background on the original TPP experiment and has **limited direct relevance** to the Claude Plays Pokémon question.
</Summary>

<Summary source="https://bulbapedia.bulbagarden.net/wiki/Twitch_Plays_Pok%C3%A9mon">
## Summary

This article is about **Twitch Plays Pokémon (TPP)**, a Twitch channel that streams chat-controlled Pokémon games — it is the **inspiration** for Claude Plays Pokémon but is a **distinct and separate project**. The article contains **no direct information about Claude Plays Pokémon** or its progress toward beating the first Pokémon game.

### Key Facts About Twitch Plays Pokémon (for context):
- Launched **February 12, 2014**, with a playthrough of Pokémon Red, receiving widespread international media attention
- At peak, had ~**120,000 simultaneous viewers** and nearly **36 million total views** in the first run alone
- Uses a crowd-sourced input system where Twitch chat users type commands (e.g., "A", "left") to control the game
- Features two input modes: **Anarchy** (inputs accepted immediately, first-come-first-served) and **Democracy** (most-voted input wins in a given timeframe)
- The channel is volunteer-run and has been active continuously, celebrating 500, 1,000, and 1,500 days of near-continuous operation

### Relevance to the Forecasting Question:
This article provides **background context only** — TPP is cited as the inspiration for Claude Plays Pokémon in the question's background information. It contains **no data points relevant to forecasting when Claude will beat the Champion**.
</Summary>


<Summary source="https://saanyaojha.substack.com/p/pokemon-red-silly-benchmark-serious">
## Summary: "Pokémon Red: Silly Benchmark, Serious Implications"

**Source:** Saanya Ojha's Substack | **Note:** The article does not provide a precise publication date beyond referencing "last week" for GPT-5's achievement, placing it approximately in mid-2025.

---

### Core Claim
The article argues that Pokémon Red is emerging as a standardized, culturally intuitive benchmark for **long-horizon agentic AI reasoning**, analogous to how Atari games benchmarked reinforcement learning.

---

### Key Facts & Statistics

| Model/Agent | Steps to Complete | Time to Complete |
|---|---|---|
| Twitch Plays Pokémon (humans) | N/A | 16 days |
| GPT-o3 | 18,184 steps | 15 days |
| **GPT-5** | **6,470 steps** | **7 days** |
| Claude (community reports) | ~35,000 steps | Not specified |
| Gemini (community reports) | ~68,000 steps | Not specified |

- GPT-5's completion represents roughly a **3x efficiency improvement** over GPT-o3 under the same standardized setup.
- Community reports (flagged as **less reliable/unverified**) suggest Claude and Gemini also completed the game, but far less efficiently than GPT-5.

---

### Why Pokémon Red Is Considered a Meaningful Benchmark (Author's Analysis)
1. **Long-horizon task** – Early decisions cascade into later consequences
2. **Partially observable, noisy environment** – Randomness requires adaptation
3. **Multi-skill integration** – Navigation, resource management, and combat strategy must work together
4. **Cultural transparency** – Broadly understood difficulty, unlike obscure academic benchmarks
5. **Historical parallel** – Sits in a progression from Chess/Go → Atari → Pokémon as increasingly complex AI testbeds

---

### Broader Implications (Author's Argument)
The shift from GPT-o3 to GPT-5 is characterized not merely as "finishing the game" but as a transition from **brute-force completion to efficient planning**. The author ties this directly to real-world enterprise value through three levers:
- **Cost reduction** (~3x fewer inference calls)
- **Latency & persistence** (enabling multi-day autonomous workflows)
- **Reliability** (handling stochastic environments without failure)

---

### Relevant Context for the Forecasting Question
- The article **confirms Claude completed Pokémon Red**, though this is attributed to unverified community reports and the step count (~35,000) suggests significantly less efficiency than GPT-5.
- The completion described for Claude appears to be under a **different setup** than the Claude Plays Pokémon Twitch stream referenced in the forecasting question — the article does not reference the Twitch stream specifically.
- The article does not provide a specific date for Claude's completion.
</Summary>

<Summary source="https://www.marca.com/en/technology/gaming/2025/08/18/68a372e3e2704e9d728b458f.html">
## Summary: ChatGPT-5 Beats Pokémon Red in Record Time (MARCA, August 18, 2025)

**Key Achievement:**
OpenAI's GPT-5 completed Pokémon Red in a record **141 hours** and **6,470 steps**, roughly **three times better** than the previous OpenAI record. For comparison, its predecessor GPT-3 required **18,184 steps** to complete the same game.

**Methodology:**
- GPT-5 analyzed the game continuously through screenshots
- It was able to learn from mistakes and adjust strategies in real time
- It employed a simple strategy: focusing almost exclusively on leveling its starter Pokémon (Charmander)

**Final Team Composition:**
The Elite Four was defeated with a **level 67 Charizard** as the primary Pokémon, supported by significantly lower-level teammates (Hypno L26, Pidgeotto L27, Snorlax L30, Lapras L15, Farfetch'd L15), highlighting that its strategic depth remains well below that of an average human player.

**Context & Next Steps:**
OpenAI expressed satisfaction with the result as a meaningful improvement over prior benchmarks. GPT-5 is now attempting **Pokémon Crystal** via its Twitch channel.

---
**Disclaimer:** This article pertains to **OpenAI's GPT-5**, not Anthropic's Claude Plays Pokémon stream, and is therefore only tangentially relevant to the resolution question.
</Summary>

<Summary source="https://www.gonintendo.com/contents/49139-openai-is-playing-pokemon-red-and-it-s-not-going-that-well">
## Summary: OpenAI Playing Pokémon Red (GoNintendo)

**Core Topic:** A comparison of AI performance in Pokémon Red, highlighting the struggles of AI programs relative to human players.

### Key Facts:

- **OpenAI's performance:** After **80 hours** of gameplay, OpenAI's "smartest model to date" had only obtained **2 gym badges** in Pokémon Red — a notably poor showing.
- **Twitch Plays Pokémon benchmark:** The crowd-sourced chaos experiment (thousands of people inputting random commands) reached 2 badges in approximately **45 hours** — meaning OpenAI was *slower* than that chaotic baseline.
- **Google Gemini 2.5 Pro (UPDATE, June 19):** Gemini 2.5 Pro completed Pokémon Blue but required **813 hours** to do so. After unspecified tweaks/optimizations, it completed the game in **406.5 hours** — still dramatically longer than any human playthrough would take.

### Context:
The article frames AI Pokémon performance as a benchmark for general AI capability, noting that even highly trained, state-of-the-art models struggle significantly with a game an 8-year-old could complete.

---

**Disclaimer:** The article does not specifically mention Claude Plays Pokémon, but provides useful **comparative benchmarks** for other AI systems (OpenAI and Gemini) attempting the same or similar games, which may inform expectations for Claude's performance.
</Summary>


<Summary source="https://github.com/portalcorp/ClaudePlaysPokemon">
## Summary

**Source:** GitHub repository by user "portalcorp" — a technical/developer source, not an official Anthropic publication.

**Disclaimer:** The extracted content appears to be incomplete, providing only a partial description of the repository's README file. A fuller summary of the codebase and its features may not be fully captured here.

### Key Points:

- The repository is described as "some extra UI and scaffolding" built on top of a starter repository by someone named "David," suggesting it is a community/third-party contribution rather than an official Anthropic project.

- The core implementation is described as **minimal**, using the **PyBoy emulator** to run **Pokémon Red** with Claude as the AI agent.

- The repository includes an **automated logging system** that:
  - Creates a new log directory for each run under `/logs`
  - Uses timestamped directory names (e.g., `logs/run_20240321_123456/`)
  - Tracks **Claude's decision-making process** and **game progression over time**

### Relevance to Forecast Question:
This article provides technical background on the scaffolding used to run Claude Plays Pokémon, but contains **no information about game progress, milestones reached, or timeline for completing the game**. It is primarily useful for understanding the technical infrastructure behind the experiment.
</Summary>

<Summary source="https://news.ycombinator.com/item?id=46347669">
**Disclaimer:** This article is entirely unrelated to the "Claude Plays Pokemon" question it is being used to inform. The article describes a separate project called **"Twitch Plays Claude"** — a crowd-controlled LLM live-coding experiment — and contains no information about the Claude Plays Pokemon Twitch stream or its progress in beating Pokémon Red.

---

**Summary of Actual Article Content:**

A developer built a live experiment called **"Twitch Plays Claude"** (stream: twitch.tv/artix187), inspired by Twitch Plays Pokémon, where Twitch chat users collectively control **Claude 4.5 Opus** to live-code a single `index.html` file in real time.

**How it works:**
- Users submit prompts via `!idea <prompt>` to modify the webpage
- Two modes manage crowd chaos:
  - **Anarchy:** Inputs are batched; AI weighs crowd demand proportionally
  - **Democracy:** Inputs are synthesized by Claude, then voted on before execution
- Each cycle lasts ~1.5–2 minutes; a "Collective Goal" is set every 30 minutes (page resets if goal changes)

**Technical stack:** FastAPI, Gunicorn, Nginx, custom Twitch bot, morphdom via websockets for smooth DOM updates, sandboxed environment with allowlisted libraries (e.g., Three.js)

**Planned improvements:** Hierarchical clustering on semantic embeddings for Democracy mode; potentially giving chat control over the system prompt.

The developer expresses curiosity about whether the result will be chaotic or demonstrate a "wisdom of the crowd" effect.
</Summary>

<Summary source="https://github.com/puravparab/Claude-Pokemon">
## Summary

**Source:** GitHub repository by user *puravparab*
**Title:** Claude-Pokemon — An AI agent that watches Claude AI play Pokémon and posts updates autonomously to X/Twitter

---

### What It Is
This is a third-party, open-source AI agent project (not affiliated with Anthropic) designed to autonomously monitor the *Claude Plays Pokémon* Twitch stream and post real-time updates to X (formerly Twitter).

### How It Works
The system runs two parallel processes:
1. **Monitoring Agent** — Periodically captures screenshots from the Twitch stream, runs them through an LLM (via OpenRouter API) to extract game analysis and metadata, and saves results to a `context.jsonl` file.
2. **Posting Agent** — Reviews events from the past 5 minutes alongside longer-running "agent notes," decides whether to compose and post a tweet, and logs output to `posts.jsonl` while updating its internal notes.

### Technical Requirements
- Python 3.12
- X (Twitter) Developer Account
- OpenRouter API key (for LLM access)
- `uv` Python package manager
- Configurable environment variables for Twitch channel, timing intervals, and API credentials

---

**Disclaimer:** This article is a GitHub README and contains primarily technical/setup information. It offers **no direct information** about Claude's current progress in the Pokémon game, nor any timestamps or milestones relevant to forecasting when the game might be completed.
</Summary>


<Summary source="https://www.scientificamerican.com/article/ais-victories-in-go-inspire-better-human-game-playing/">
## Summary: "AI's Victories in Go Inspire Better Human Game Playing" (*Scientific American*, Emily Willingham)

### Core Finding
A research study examined whether AlphaGo's landmark defeats of human Go champions (2016–2017) influenced the quality of human decision-making in the game. Analyzing **5.8 million game moves** spanning 66 years, researchers found that **human decision quality improved measurably after AI surpassed human champions**.

### Key Facts & Statistics
- AlphaGo defeated world champion Lee Sedol in 2016 (winning 4 of 5 games), drawing comparisons to Deep Blue's 1997 chess victory over Kasparov
- Researchers used AI system **KataGo** to rate move quality by simulating **10,000 possible game continuations** per human decision
- For 66 years prior to 2016–2017, human decision quality remained **largely uniform**
- After 2016–2017, both **decision quality scores and novelty scores increased**
- Post-2016, novel moves tended to appear **earlier in games** (by move 35 rather than later)
- Memorization was found **unlikely** to fully explain the quality improvements

### Named Expert Opinions
- **David Silver** (DeepMind, AlphaGo project lead): Called human adaptation "amazing," suggesting humans will "massively increase their potential" by building on AI discoveries
- **Murat Kantarcioglu** (UT Dallas, Computer Science): Concluded "AI can help improve human decision-making" by processing vast search spaces to find novel solutions

### Relevance Disclaimer
This article focuses on AI improving *human* gameplay in Go and does not directly address Claude Plays Pokémon or AI autonomously completing games. Its relevance to the forecasting question is limited to providing broader context about AI as a benchmark in games.
</Summary>

<Summary source="https://www.verses.ai/blog/mastering-atari-games-with-natural-intelligence">
## Summary

**Disclaimer:** This article appears to be about a company called "Genius" and their AI agent benchmarked against Atari games — it does **not appear directly relevant** to the Claude Plays Pokémon question. The content does not mention Claude, Pokémon, or the Twitch stream in question. It may have been retrieved due to tangential keyword overlap (AI gaming benchmarks, Claude mentioned only as one of many LLMs in passing).

---

### Article Content (for completeness):

The article traces AI gaming milestones — IBM Deep Blue (chess, 1996), AlphaGo (Go, 2016) — and argues that video games, particularly **Atari games**, represent a more realistic benchmark for general intelligence due to their dynamic, interactive environments.

The core claim is that a company's **"Genius Agent"** outperforms state-of-the-art transformer-based model **IRIS** on an **Atari 10k challenge** (10,000 training steps vs. the standard 100k benchmark):
- Genius Agent trained in **2 hours** achieved **Human Normalized Score (HNS) ≥ 1.0** (human-level) in Pong
- IRIS trained over **2 days** on the same data achieved only HNS 0.0–0.3
- Genius Agent's model size is **350,000 parameters** vs. IRIS's **8,000,000** (96% smaller)

The article emphasizes generalizability across games (Boxing, Freeway) and cautions against over-reliance on single benchmarks.

**This article contains no information relevant to Claude Plays Pokémon.**
</Summary>

<Summary source="https://deepmind.google/blog/agent57-outperforming-the-human-atari-benchmark/">
## Summary

**Disclaimer:** This article is about DeepMind's **Agent 57** and the Atari 57 benchmark — it does not contain any information directly relevant to Claude Plays Pokémon. The article appears to have been retrieved in error or as background context on AI gaming benchmarks generally.

---

### Key Points from the Article:

**The Benchmark:**
- The Atari 57 suite (57 Atari 2600 games) has been a standard AI benchmark since 2012, using human performance as a baseline (0% = random play, 100%+ = human-level or better).

**The Problem with Average Scores:**
- Average/median performance metrics can be misleading indicators of *generality* — an agent can score very high on easy games while failing completely on hard ones, yet still appear strong on average.

**Agent 57's Achievement:**
- Agent 57 is described as **the first deep RL agent to score above human baseline on all 57 Atari games**, including four previously unconquered games: *Montezuma's Revenge*, *Pitfall*, *Solaris*, and *Skiing*.
- Prior agents consistently failed on these four games due to challenges in **exploration** (Montezuma's Revenge, Pitfall) and **long-term credit assignment** (Solaris, Skiing).

**Technical Approach:**
- Agent 57 uses a distributed architecture separating data collection from learning, a prioritized replay buffer, memory mechanisms, and a meta-controller adapting exploration vs. exploitation behavior.

---

*This article provides general context on AI game-playing benchmarks but contains no specific information about Claude Plays Pokémon.*
</Summary>


<Agent_report>
Query: List documented cases since 2010 of autonomous AI agents (not crowd-sourced humans) completing Pokémon Red/Blue/Yellow, including date of first completion, total training/play time, and typical lag from first public demo to completion.
Below is the consolidated record of every publicly-documented instance since 2010 in which an autonomous, software-only AI agent (i.e. no humans in the control loop, no “crowd-play”) has completed one of the first-generation Pokémon games (Red, Blue, or Yellow).  For each case I list:

• AI system & organisation  
• Game version cleared  
• Date the first full clear was publicly confirmed  
• Reported training / play time (or closest proxy that the sources give)  
• Gap between the first publicly-visible demo of the project and the day of the first clear (“demo-to-clear lag”)  

1. OpenAI “GPT-o 3” agent  
   • Version cleared: Pokémon Red  
   • First clear announced: mid-2024 (“last week” from 2024-dated article) (Ojha, Saanya. Pokémon Red: Silly Benchmark, Serious Implications)  
   • Training / play time: 18 ,184 emulator steps, 15 days wall-clock to finish (same source)  
   • Demo-to-clear lag: c. 5 weeks.  The Substack piece notes that GPT-o 3 was first shown playing in early March 2024 and finished in April 2024, implying ~35 days from public debut to victory.  
   • Notes: First documented autonomous clear under a “standardised” minimal-help harness; provided the baseline for later LLM agents.

2. OpenAI GPT-5 agent  
   • Version cleared: Pokémon Red  
   • First clear announced: early February 2025 (article dated 28 Feb 2025 references “last week”) (Ojha, same source)  
   • Training / play time: 6 ,470 steps; 7 days wall-clock (same source)  
   • Demo-to-clear lag: ~9 days.  GPT-5’s first public demo on the Twitch stream began two days before the 7-day playthrough started, per the article’s timeline.  
   • Notes: Roughly ×3 step-efficiency improvement over GPT-o 3.

3. Google / DeepMind Gemini 2.5 Pro (“Gemini Plays Pokémon”)  
   • Version cleared: Pokémon Blue  
   • First clear announced: 2 May 2025 (TechCrunch, 03 May 2025; Ars Technica, 05 May 2025)  
   • Training / play time: “over 106 ,000 in-game actions” (Ars Technica, 05 May 2025).  Exact hours are not given; the livestream ran continuously from 30 Apr to 2 May, so ~48–55 h real time.  
   • Demo-to-clear lag: ~1 month.  The developer’s first public broadcast with two badges was in early April 2025 (TechCrunch notes Kilpatrick’s 5-badge tweet “last month”).  Clear occurred first week of May.  
   • Notes: Required a richer agent harness (textual minimap, passability overlays, specialised sub-agents for path-finding and Victory Road puzzle) than the Claude and GPT harnesses (Ars Technica, 05 May 2025).

4. Pokémon RL (independent academic project, Rubinstein et al.)  
   • Version cleared: Pokémon Red  
   • First clear announced: 26 Feb 2025 website update (drubinstein.github.io/pokerl)  
   • Training / play time: Achieved with a <10 M-parameter PPO policy.  The site does not quote wall-clock hours; RL logs show ~11 billion emulator frames (~150 M game steps) over 23 days of distributed training on 8 GPUs before a successful champion clear.  
   • Demo-to-clear lag: ~4 years.  The project’s GitHub shows first commits and partial-route demos in 2021; the first complete clear is 2025-02-26.  
   • Notes: No language model; pure vision-and-state reinforcement learning with minimal environment simplifications.

5. Anthropic Claude 3.7 (“Claude Plays Pokémon”) – NOT YET CLEARED  
   • As of February 2025 Claude had reached three badges but had not beaten the Elite Four (PCMag, 28 Feb 2025).  It therefore does not yet meet the “completed” bar and is excluded from the list above, but is included here for context concerning the Metaculus forecasting question.  

Summary statistics & observations

• Earliest documented autonomous clear of a Gen 1 game: GPT-o 3 in 2024.  No credible public records of a full clear between 2010-2023 were found.

• Typical wall-clock play time once an agent begins a continuous finishing run ranges from 7 days (GPT-5) to roughly 2 days (Gemini’s 48-55 h stream) to 15 days (GPT-o 3).  Reinforcement-learning approaches spend the overwhelming majority of time in training; their final inference playthrough is on the order of the human 25-hour average but total compute time is weeks.

• Demo-to-clear lag for LLM-based agents has been short: ~1–5 weeks.  By contrast, the RL-based project incubated for years before producing a champion run.

• Efficiency (measured in in-game actions or steps) improved dramatically across the LLM lineage: 106 k+ (Gemini) → 18 k (GPT-o 3) → 6.5 k (GPT-5), a ~16× reduction in one year.

Information gaps

• Exact wall-clock hours for GPT-o 3 and GPT-5 runs beyond “days” were not reported in available sources.  
• Reinforcement-learning project gives aggregate training frames but not emulator-steps-to-finish for its final policy.  
• No sources explicitly document any autonomous clear of Pokémon Yellow; all reported clears are Red or Blue.

If more precision on run length or additional Yellow completions surfaces later, those data would refine the table, but the core historical record above is complete given currently published evidence.</Agent_report>


The information has been sourced from the internet and language models (for agent reports). Exercise healthy skepticism toward unverified claims.

Your analysis should have the following components, referring to the above historical context:
(a) Source analysis: Briefly summarize each information source (either web article or Agent report), evaluate source quality and date.
**Opinions are commonplace in writing. For each source, you must be able to discern factual information from opinions. You are advised to strongly consider only opinions originating from identifiable experts or entities**.
(b) Reference class analysis: Identify a few possible reference classes and evaluate respective suitabilities to the forecasting question. If applicable, choose the most suitable one.
(c) Timeframe analysis: State the prediction timeframe (e.g., how many days/months from now?) and examine historical patterns over similar periods
(d) Justification: Integrate the above factors with other points you found relevant to write a justification for your outside view prediction.

Subsequently, calibrate your outside view prediction, considering:
(a) You aim to predict a true probability distribution, not a hedged smooth distribution or an overconfident extremely narrow distribution. In your thinking, always consider ranges over singular values.
(b) Are there previously established distributions that you can tether your prediction to?
(c) Small changes in percentile values can significantly reshape the distribution, especially near the tails. Choose tail values carefully.
(d) Historically, what is the rate of upsets/unexpected outcomes in the domain of this forecasting question? How should this affect your CDF distribution?

Set wide 10th/90th percentile intervals to account for unknown unknowns.

**CRITICAL: Percentile values MUST be strictly increasing** (10th = lowest, 90th = highest).
Use the units requested by the question. Never use scientific notation.

Format your answer as below:

Analysis:
{Insert your analysis here, following the above components.}

Outside view calibration:
{Insert your calibration of your outside view prediction here.}

Outside View Prediction:
Percentile 10: XX
Percentile 20: XX
Percentile 40: XX
Percentile 60: XX
Percentile 80: XX
Percentile 90: XX
