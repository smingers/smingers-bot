You are evaluating the completeness of research gathered for a forecasting question and identifying critical gaps.

QUESTION: Will the United States attack Iran before April 2026?
Type: binary
Resolution criteria: This question will resolve as **Yes** if, before April 1, 2026, the United States carries out a military attack against Iran's territory or military personnel, according to credible sources.
Fine print: To qualify for this question, the attack must physically affect Iran's territory or military personnel: cyberattacks, warning shots in international waters, or other actions without immediate physical impact will not count.

If it is disputed whether the United States is responsible for an attack, this question will refer to credible sources or may resolve as ambiguous.
Days to resolution: 34

RESEARCH RESULTS SUMMARY:
The following searches were executed and their results summarized below.

[HISTORICAL] US military strikes Iranian territory timeline (Google) — SUCCESS

<Summary source="https://www.cnn.com/interactive/2025/06/world/us-iran-conflict-timeline-dg/">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.foxnews.com/world/full-breakdown-operation-midnight-hammer-largest-b-2-operational-strike-us-history">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.pbs.org/newshour/world/... [truncated]

---
[HISTORICAL] dataset US overseas combat operations 1945-2025 frequency (Agent) — FAILED (Error during agentic search: 'SearchPipeline' object has no attribute '_current_agentic_cost')

<Agent_report>
Query: dataset US overseas combat operations 1945-2025 frequency
Error: Error during agentic search: 'SearchPipeline' object has no attribute '_current_agentic_cost'
</Agent_report>


---
[HISTORICAL] US interventions following large foreign protests case studies (Google) — SUCCESS

<Summary source="https://revista.drclas.harvard.edu/united-states-interventions/">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.pbs.org/wgbh/pages/frontline/shows/military/etc/cron.html">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://thestandard.nz/the-top-20-biggest-u-s-military-interventions-best-to-worst/">
Erro... [truncated]

---
[HISTORICAL] congressional authorization history limited strikes without AUMF (Google) — SUCCESS

<Summary source="https://www.npr.org/2025/06/23/nx-s1-5442396/iran-war-trump-power-congress-constitution">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://constitutioncenter.org/blog/does-the-president-need-congress-to-approve-military-actions-in-iran">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.nbcnews.com/politic... [truncated]

---
[HISTORICAL] media confirmation process past US strikes Iran 2025 bunker busters (Google) — SUCCESS

<Summary source="https://abcnews.com/Politics/early-us-intel-assessment-finds-us-strikes-set/story?id=123169267">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.cnn.com/2025/06/24/politics/intel-assessment-us-strikes-iran-nuclear-sites">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.cbsnews.com/news/satellite-pho... [truncated]

---
[HISTORICAL] US carrier deployments Persian Gulf crisis 1990-2025 data (Agent) — FAILED (Error during agentic search: 'SearchPipeline' object has no attribute '_current_agentic_cost')

<Agent_report>
Query: US carrier deployments Persian Gulf crisis 1990-2025 data
Error: Error during agentic search: 'SearchPipeline' object has no attribute '_current_agentic_cost'
</Agent_report>


---
[CURRENT] US carrier group Gulf February 2026 (Google News) — SUCCESS

<Summary source="https://gulfnews.com/world/mena/iran-us-tensions-aircraft-carrier-uss-gerald-ford-arrives-sends-clear-signal-1.500453290">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.bbc.com/news/articles/c1d64p3q2d0o">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://www.stripes.com/branches/navy/2026-02-20/ford-mi... [truncated]

---
[CURRENT] Trump administration Iran strike deliberations 2026 (AskNews) — SUCCESS

<Asknews_articles>
Query: Trump administration Iran strike deliberations 2026
Here are the relevant news articles:

**Washington Wants Israel To Strike Iran First**
Advisers to U.S. President Donald Trump believe it would be politically advantageous for Israel to conduct a military strike on Iran before the United States intervenes, according to two knowledgeable sources cited by Politico. White House officials reportedly stated that the 'political situation is budding' and emphasized that Isra... [truncated]

---
[CURRENT] Iran protests crackdown February 2026 death toll escalation (Google News) — SUCCESS

<Summary source="https://www.cfr.org/global-conflict-tracker/conflict/confrontation-between-united-states-and-iran">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summary>

<Summary source="https://iranhumanrights.org/2026/01/iranian-authorities-intensify-crackdown-on-protests-with-live-fire-arbitrary-arrests-and-attacks-on-hospitals/">
Error summarizing article: 'SearchPipeline' object has no attribute '_current_summarization_cost'
</Summar... [truncated]

---
[CURRENT] US Iran backchannel negotiations ceasefire 2026 (AskNews) — SUCCESS

<Asknews_articles>
Query: US Iran backchannel negotiations ceasefire 2026
Here are the relevant news articles:

**Geneva at a Crossroads: Iran-US Talks Decide the Fate of Peace Amid Global Crises**
On February 26, 2026, pivotal diplomatic talks took place in Geneva between Iran and the United States, marking what could be the final opportunity to prevent military escalation before Donald Trump potentially implements his war threats. The Iranian Foreign Minister, Abbas Araghtschi, and U.S. envoy... [truncated]


YOUR TASK:
Evaluate coverage across these dimensions. For each, state COVERED or GAP with a brief note (1 sentence):

1. Base rate: Do we have historical frequency/distribution data for the outcome?
2. Resolution mechanism: Do we know the current state of the specific metric/event that determines resolution?
3. Key drivers: Do we have data on the main causal factors?
4. Current state: Do we have recent (last 7 days) news or data?
5. Contrarian: Do we have information supporting the less obvious outcome?

Then decide:
- If research is sufficient for a well-calibrated forecast: Write "Coverage: SUFFICIENT"
- If there are important gaps that would materially change a forecast: Write "Coverage: GAPS_FOUND" followed by 1-3 targeted queries to fill the most critical gaps

Only generate gap-fill queries for gaps that would materially affect a forecaster's prediction. Do not generate queries for nice-to-have information.

Use the same tagged format:
1. [HISTORICAL/CURRENT] query (Tool) -- Intent: what gap this fills

Analysis:
{Your coverage evaluation across the 5 dimensions.}

Coverage: SUFFICIENT/GAPS_FOUND

Search queries:
{Only if GAPS_FOUND. 1-3 queries.}
