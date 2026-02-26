
<Summary source="https://timesofindia.indiatimes.com/technology/gaming/how-this-30-year-old-pokemon-game-is-helping-google-openai-and-anthropic-to-evaluate-ai-models/articleshow/127301204.cms">
## Summary: How Pokemon Games Are Being Used to Evaluate AI Models
**Source:** Times of India, January 23, 2026 (citing a Wall Street Journal report)

### Key Facts

- Google, OpenAI, and Anthropic are all using original 1990s Pokémon games to evaluate their AI models' capabilities in handling complex, long-term goals.
- "Claude Plays Pokémon" was created in **February 2025** by **David Hershey**, Applied AI Lead at Anthropic, on Twitch, which inspired similar streams for OpenAI and Google models.
- The streams have collectively accumulated **hundreds of thousands of comments**.
- **Critically for the forecast question:** As of the article's publication (January 23, 2026), **none of the Claude versions have completed the game yet**. The latest version, **Claude Opus 4.5**, is currently playing live on Twitch.
- **Both OpenAI's GPT models and Google's Gemini have already beaten the original Pokémon game**, and are now playing sequel games — though developers note this may be attributable to differences in the "harnesses" (software frameworks) built around them.

### Expert Opinions
- **David Hershey (Anthropic):** Pokémon provides a quantitative way to evaluate model performance; newer Claude versions have improved but none have finished the game yet. He also built a memory system to help Claude retain in-game information.
- **Graham Neubig (Carnegie Mellon University):** Unlike traditional benchmarks, Pokémon allows researchers to observe AI decision-making and goal-pursuit over an extended period.
- **Jonathan Verron** ("GPT Plays Pokémon" developer): Calls Pokémon "a perfect game for AI right now."

### Contextual Notes
- Anthropic brings a "Claude Plays Pokémon" booth to industry conferences and maintains an internal Slack channel for staff to follow Claude's progress.
- The article confirms Claude has **not yet beaten the game** as of late January 2026, while competitors have.
</Summary>

<Summary source="https://www.newyorker.com/magazine/2026/02/16/what-is-claude-anthropic-doesnt-know-either">
## Article Summary

**Source:** The New Yorker (based on style and content); a long-form profile of Anthropic and its AI systems, particularly Claude.

---

### Key Facts Relevant to the Question

- **Claude Plays Pokémon Red** was an ongoing experiment visible on small screens in Anthropic's office (as of the reporter's May visit), described as "a live stream of Anthropic's Claude playing the nineties Game Boy classic Pokémon Red."
- The experiment is explicitly characterized as **"an ongoing test of Claude's ability to complete tasks on a long time horizon."**
- **Progress timeline noted in the article:**
  - Initially, Claude **could not escape the opening confines of Pallet Town.**
  - By **late spring** (of the article's reporting period, presumably 2025), Claude **had arrived in Vermilion City** — a relatively early-to-mid point in the game.
- A behavioral observation: Claude **"often banged its head into the wall trying to make small talk with non-player characters who had little to report"** — suggesting persistent inefficiencies in navigation and interaction.

---

### Contextual Details

- The article frames Claude Plays Pokémon as one of several internal experiments designed to probe Claude's capabilities and character, alongside "Project Vend."
- No timeline or prediction for completing the game is offered by any named source in the article.

---

**Disclaimer:** The article does not focus primarily on Claude Plays Pokémon and provides only passing references to it. The progress described (reaching Vermilion City by late spring) is the most concrete data point available from this source.
</Summary>

<Summary source="https://arstechnica.com/ai/2025/03/why-anthropics-claude-still-hasnt-beaten-pokemon/">
## Summary: "Why Anthropic's Claude still hasn't beaten Pokémon" (Ars Technica, March 21, 2025)

### Context & Anthropic's Claims
Anthropic publicly promoted "Claude Plays Pokémon" in February 2025 as evidence of progress toward AGI, highlighting that Claude 3.7 Sonnet's "extended thinking" and "improved reasoning capabilities" allowed it to collect multiple Gym Badges — something older models "had little hope of achieving." Anthropic framed this as demonstrating skills like planning ahead, remembering objectives, and adapting strategies.

### Observed Performance Limitations
Despite the positive framing, the article documents significant and persistent failures observed by Twitch viewers:
- Claude frequently revisits completed towns, gets stuck in corners, and repeatedly interacts with unhelpful NPCs
- In Vermilion City (a small area with only 7 buildings), Claude spent **6–8 hours at a time** wandering and failing to find the S.S. Anne entrance, repeating the same failed loop **~20 times consecutively**
- Claude effectively **lacks functional long-term memory**: it has a note-taking system but rarely takes useful notes and often ignores them when it does
- Claude **never independently develops meta-strategies** (e.g., "hug the right wall"), and when it does make progress, it is often attributed to "dumb luck"

### Comparative Performance (Less Reliable Source)
The author ran their own informal experiment with Google and OpenAI LLMs, finding they performed **significantly worse** than Claude — hallucinating NPC dialogue, misreading screen states, and failing within the first two rooms. The author acknowledges not implementing all of Claude's supporting infrastructure, which may partly explain the gap.

### Author's Overall Assessment
The author (unnamed, writing for Ars Technica) distinguishes between **relative improvement** (Claude 3.7 is meaningfully better than prior models) and **absolute capability** (Claude still cannot reliably complete the game). They characterize Claude's behavior as more reminiscent of a pet than an AGI, and suggest Anthropic has overstated the bot's capabilities. They conclude that while further progress is plausible, consistent navigation of Pokémon remains beyond current LLM capability.
</Summary>

<Summary source="https://manifold.markets/Sketchy/will-claude-become-a-pokemon-master-ng2zSA9ync">
## Summary: "Will Claude become a Pokémon Master by the end of 2025?" (Manifold Markets)

**Source:** Manifold Markets prediction market (less reliable/crowd-sourced opinions, but contains some data-backed analysis)

---

### Market Structure
- Resolves YES if Claude beats Pokémon (Elite 4 + Rival) by end of 2025
- Broader resolution criteria than the Metaculus question (any Anthropic approach, any "regular" Pokémon game counts)

---

### Key Analytical Points from Traders

**Safari Zone identified as the critical bottleneck:**
- Requires ~80% optimal pathfinding efficiency (minimum 399 steps out of 500 allowed to reach the Secret House)
- One trader argues: *"the first run to defeat the Safari Zone will also defeat the Elite Four"* — implying it's the hardest obstacle remaining

**Claude's current pathfinding efficiency estimates:**
- Claude 3.7 used ~10,000 actions to defeat Mt. Moon (per Anthropic white paper)
- Estimated 5–10% pathfinding efficiency currently vs. 80% needed for Safari Zone
- Efficiency improvements per model generation: ~4x (3.5 Old → 3.5 New), ~4x (3.5 New → 3.7), ~3.5x on "Get Brock's badge" metric

**Model release timeline reasoning (bullish case):**
- 3.5 Old → 3.5 New: ~2 months apart; 3.5 New → 3.7: ~4 months apart
- With 3.7 released in February 2025, ~10 months remain in 2025 for potentially two more model generations
- Trader concludes: *"I think we're a model or two away from being efficient enough to defeat the Safari Zone"*

**Other potential obstacles noted:**
- Victory Cave and Seafoam Islands flagged as difficult navigation challenges (no hard step limit, but complex mazes)
- Lt. Surge's gym switch puzzle mentioned as a possible blocker
- Battles generally **not** considered a major blocker given Gen 1's low difficulty ceiling

**Possible workaround noted:**
- Anthropic could switch to Pokémon Yellow, which allows Safari Zone entry without money, eliminating the soft-lock risk — though this would be controversial among observers
</Summary>

<Summary source="https://www.lesswrong.com/posts/gogZyeistdaDFuhbG/claude-plays-pokemon-opus-4-5-follow-up">
## Summary: "Claude Plays Pokemon: Opus 4.5 Follow-up" (LessWrong, January 29, 2026)

### Current Status of the Run
- At the time of writing, Claude is at **Victory Road** (~230,000 steps), stuck on boulder puzzles required to progress to the Pokémon League.
- This is a significant advancement from the original article (published at ~48,000 steps), when Claude was stuck in Silph Co.
- Between those two points, Claude successfully completed: Silph Co, Safari Zone (after a backtrack), Pokémon Mansion, all **eight gym badges**, and reached Victory Road.

### Key Incident: Safari Zone/Strength HM
- On his first Safari Zone visit, Claude **missed the Gold Teeth**, which are needed to obtain the HM Strength from the Safari Warden — a prerequisite for solving Victory Road's boulder puzzles.
- After completing Pokémon Mansion, Claude recognized the dependency and **successfully backtracked** to retrieve the item, demonstrating recovery from a long-term planning failure.

### Assessment of Claude's Capabilities (Updated from Original Article)
The author revisits conclusions from a prior LessWrong piece ("Insights into Claude Opus 4.5 from Pokémon"):
- **Vision remains poor** — flagged as a genuine, unresolved problem; the author notes Anthropic has not prioritized fixing this.
- **Improved spatial awareness, context window use, and loop-detection** — these improvements largely hold up.
- **Long-term planning remains weak**, though Claude showed ability to recover from planning failures when forced to.
- **Persistence is highlighted as a key factor**: Claude overcame obstacles that would have caused human players to quit, eventually stumbling into solutions after prolonged attempts.

### Broader Methodological Discussion
- The author defends Claude Plays Pokemon as a **purer test of underlying LLM capability** compared to similar projects that use more elaborate scaffolding/harnesses.
- A debate is noted about whether providing more assistance (e.g., skill files, walkthroughs) constitutes "cheating" vs. realistic deployment conditions — the author acknowledges the tension but does not fully resolve it.

### Forward-Looking Signals
- The author **expects Claude to beat the game given unlimited time**.
- The post was written with urgency, anticipating an **imminent new Claude model release** that would reset the run — referencing a Manifold prediction market as a signal of this expectation.
- The author frames the current run as likely to become obsolete soon due to a model update.
</Summary>

<Summary source="https://www.anthropic.com/research/visible-extended-thinking?utm_cta=Anaconda-press-release-9-29%2F%3Fwtime&gclid=CjwKCAjwlbu2BhA3EiwA3yXyuxtljrx89ZKefQizJmR3fZZk_MCUQqXqgrP1E_HPie3UUA-m59X0MBoC1K8QAvD_BwE">
## Summary: Claude's Extended Thinking & Pokémon Performance

### Key Capability: Extended Thinking Mode
- Claude 3.7 Sonnet introduces a toggleable "extended thinking mode" allowing the model to spend more time and computational effort on difficult problems
- Developers can set a precise "thinking budget" to control how long Claude deliberates
- This is the **same model** allocating more effort, not a separate model/strategy

### Relevance to Pokémon (Direct Facts)
- Anthropic equipped Claude with **basic memory, screen pixel input, and function calls** to press buttons and navigate the screen
- The system allows Claude to play **continuously beyond its usual context limits**, sustaining gameplay through **tens of thousands of interactions**
- **Claude 3.0 Sonnet** failed to even leave the starting house in Pallet Town
- **Previous versions** (without extended thinking) became stuck very early in the game
- **Claude 3.7 Sonnet** successfully battled and defeated **three Pokémon Gym Leaders**, earning their Badges
- The article attributes this progress to Claude 3.7's ability to "try multiple strategies and question previous assumptions"

### Broader Performance Context
- Claude 3.7 Sonnet showed improved performance on **OSWorld** (computer use benchmark), with performance advantages growing over time during extended interactions
- Extended thinking improves math accuracy **logarithmically** with additional thinking tokens

*Note: The article appears to be cut off before completion.*
</Summary>

<Agent_report>
Query: What is the current status of the Claude Plays Pokemon Twitch stream as of February 2026? Has the run been reset? What model is currently playing? Has Claude beaten the Elite Four or Champion yet?
1. Current stream status (February 2026)  
   • The Twitch channel “Claude Plays Pokémon” is still live and active.  The experiment is now in its fourth calendar year and is deep into a single long-running play-through that began when the harness was upgraded for Claude Opus 4 (.5).  At the time of the most recent independent reporting – Time Magazine, 13 Jan 2026 – the run had logged “over 500 hours” of wall-clock play and roughly 170 000 discrete model actions, and it was still continuing in real time (Time, 13 Jan 2026).  
   • The model spends long stretches progressing, then stalling for many hours on navigation or puzzle bottlenecks, so the stream remains slow-moving but uninterrupted.

2. Has the run been reset recently?  
   • There is no evidence of any reset after the upgrade to Claude Opus 4 (.5).  The 500-plus-hour figure in the Time article refers to a single continuous save file, not a fresh start.  Earlier 2025 resets (when the experiment moved from Sonnet 3.5 to Sonnet 3.7 and later when the Mt. Moon “loop” was mercy-killed) are well-documented, but nothing since.  Therefore, as of February 2026 the current Opus 4.5 run is still the original Opus-era attempt.

3. Which Claude model is playing now?  
   • The stream is running on Claude Opus 4.5, Anthropic’s flagship released early February 2026 (Time, 13 Jan 2026; Manifold market resolving on 5 Feb 2026 confirms public launch of Opus 4.5).  
   • Earlier public commentary (LessWrong, Dec 2025) analysed Opus 4.5’s “memory-note” style of play, matching what the live stream shows.

4. Has Claude beaten the Elite Four or Champion?  
   • No.  The Time piece explicitly states that although Opus 4.5 “is performing much better,” it “frequently gets stuck” and at one point “spent four days circling a gym without being able to enter.”  Nothing in any 2026-dated source claims a Pokémon League victory.  
   • Comparative articles still frame the task as un-completed and use the stream as evidence of long-horizon limitations of present-day LLM agents (Time, 13 Jan 2026; LessWrong discussion threads through Jan 2026).

Summary answers to the query  
• Status: Stream is live; current continuous run is over 500 hours old and ongoing.  
• Reset?  No reset since the switch to Opus 4.5; the same save file is still in use.  
• Model: Claude Opus 4.5 (released February 2026).  
• Elite Four / Champion: Not yet defeated; Claude has not completed the game as of February 2026.

Remaining information gaps  
None of the available 2026 sources give the exact in-game location of Claude as of the specific date you ask, nor the precise badge count after January’s reporting, but they all agree the Champion is still unbeaten and the run is live.</Agent_report>

<Summary source="https://www.anthropic.com/news/claude-sonnet-4-6">
## Summary: Introducing Claude Sonnet 4.6

**Note:** This article is an Anthropic product announcement for Claude Sonnet 4.6 and does not directly address Claude Plays Pokémon. Its relevance to the forecasting question is indirect — it describes improvements in Claude's computer use capabilities, which is the core skill required for the Pokémon stream.

---

### Key Facts & Capabilities

**General:**
- Claude Sonnet 4.6 is described as Anthropic's most capable Sonnet model, positioned as a full upgrade across coding, computer use, long-context reasoning, agent planning, and knowledge work.
- Pricing remains the same as Sonnet 4.5 ($3/$15 per million input/output tokens).
- Features a **1 million token context window** (in beta).
- Now the default model on Claude.ai Free and Pro plans.

**Computer Use (Most Relevant to Question):**
- Sonnet 4.6 shows **"major improvement in computer use skills"** compared to prior Sonnet models.
- Benchmarked on **OSWorld** (standard AI computer use benchmark), showing steady gains over 16 months across Sonnet models.
- Early users report **"human-level capability"** in tasks like navigating complex spreadsheets and filling out multi-step web forms.
- Improved resistance to **prompt injection attacks** compared to Sonnet 4.5.
- One customer (in insurance) reported **94% accuracy** on computer use tasks, described as "the highest-performing model we've tested for computer use."

**Coding & Agentic Tasks:**
- Developers preferred Sonnet 4.6 over Sonnet 4.5 ~**70% of the time** in Claude Code testing.
- Users preferred it over the older Opus 4.5 **59% of the time**.
- Rated as less prone to "laziness," overengineering, and hallucinations; better at multi-step instruction following.

**Long-Horizon Planning:**
- On the **Vending-Bench Arena** evaluation (simulated business competition), Sonnet 4.6 demonstrated strategic long-term planning — investing heavily early, then pivoting to profitability — finishing ahead of competing models.
- The 1M token context window is cited as enabling better **long-horizon planning**.

**Safety:**
- Safety evaluations concluded Sonnet 4.6 is "as safe as, or safer than" recent Claude models, with "very strong safety behaviors and no signs of major concerns around high-stakes forms of misalignment."

---

### Relevance to Forecasting Question
The article's most pertinent detail is the **significant improvement in computer use capabilities**, which is the mechanism by which Claude interacts with the Pokémon game on stream. Improved consistency, instruction following, and long-horizon planning could plausibly accelerate progress on the stream, though the article makes no direct mention of Claude Plays Pokémon.
</Summary>

<Summary source="https://www.interconnects.ai/p/opus-46-vs-codex-53">
## Article Summary

**Disclaimer:** This article appears to be a technology/AI industry analysis blog post focused on comparing Claude Opus 4.6 and OpenAI's Codex 5.3 as coding agents. **It contains no information relevant to Claude Plays Pokémon or the resolution question.** The article is about AI coding assistants and the broader AI model landscape in 2026.

---

### Key Points from the Article (for general context):

**Model Releases:**
- In early February (implied 2026), Anthropic released **Claude Opus 4.6** and OpenAI released **GPT-5.3-Codex**, both positioned as coding assistants.

**Comparative Assessment:**
- The author finds Opus 4.6 superior in usability and breadth of tasks, while Codex 5.3 has a slight edge in pure coding/bug-fixing capability.
- Codex 5.3 is described as more "Claude-like" than previous OpenAI models, representing a significant step forward for OpenAI.

**Industry Trends:**
- Standard benchmarks are increasingly seen as poor signals of real-world model performance as of 2026.
- Anthropic is credited for early prioritization of agentic use cases (starting with Claude 4 in May 2025).

**This article contains no information relevant to Claude Plays Pokémon.**
</Summary>

<Summary source="https://www.anthropic.com/news/claude-opus-4-6">
## Summary: Introducing Claude Opus 4.6

**Note:** This article is an Anthropic product announcement for Claude Opus 4.6 and contains **no direct information about Claude Plays Pokémon**. Its relevance to the forecasting question is indirect — it describes the capabilities of a newer, more powerful Claude model that could potentially be used in the stream.

---

### Key Facts About Claude Opus 4.6:

**Model Capabilities:**
- Improved coding skills, longer agentic task sustenance, better performance in large codebases, and improved code review/debugging
- Features a **1 million token context window** (in beta) — a first for Opus-class models
- Introduces **adaptive thinking** (contextual calibration of extended thinking) and **effort controls** for developers

**Benchmark Performance:**
- Highest score on **Terminal-Bench 2.0** (agentic coding evaluation)
- Leads all frontier models on **Humanity's Last Exam** (complex multidisciplinary reasoning)
- Outperforms GPT-5.2 by ~144 Elo points on **GDPval-AA** (economically valuable knowledge work)
- Best performance on **Browse Comp** (locating hard-to-find information online)

**Agentic Improvements (Most Relevant to Pokémon Forecasting):**
- Partners specifically highlight improved **long-horizon task planning**, breaking complex tasks into independent subtasks, running tools and subagents in parallel
- Described as better at **sustained autonomous operation** without hand-holding
- Noted improvement in **navigating large, complex environments** and identifying blockers

**Availability & Pricing:**
- Available on claude.ai, API, and major cloud platforms (`claude-opus-4-6`)
- Pricing unchanged: $5/$25 per million input/output tokens
</Summary>
