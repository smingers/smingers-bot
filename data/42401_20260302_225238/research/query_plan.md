Analysis:
The question is narrowly focused on how the Google Trends daily value for the search term “irgc” (US, UTC day-granularity) will move between 2 Mar 2026 and 14 Mar 2026.  
What we already know:
• The current reading for 1 Mar 2026 is 100—i.e., the term is at its 30-day peak, which likely reflects a very recent news event.  
• Resolution will be based on SerpApi’s TIMESERIES end-point, so we must think in terms of the numbers returned by that API, not the in-browser chart.

Remaining information a forecaster needs:
1. Base rate / historical volatility: How often does the daily value for “irgc” change by >3 points over a 12-day window? What does the distribution of changes look like after past spikes?  
2. Resolution mechanics fine print: confirmation that locking the date range keeps scaling fixed, plus any quirks seen in SerpApi outputs.  
3. Key drivers: Which kinds of events (sanctions, military clashes, elections, hostage exchanges) have historically produced large upward or downward moves in “irgc” search traffic?  
4. Current state & near-term pipeline: What breaking or scheduled events between now and 14 Mar 2026 could plausibly keep interest elevated or cause it to subside? Are there any known anniversaries, planned operations, or diplomatic deadlines?  
5. Contrarian signals: Evidence that the present spike could be a one-day wonder that normally collapses quickly, or conversely that similar past spikes often lasted two weeks.

Search strategy:  
• Use Google/Agent queries to pull historical Google Trends data and compute frequency of >3-point moves.  
• Gather lists of past IRGC-related news spikes to link Google Trends jumps with concrete events (base rate + driver identification).  
• Scan current and very recent news for IRGC-linked stories that might keep the topic in headlines through mid-March.  
• Look for calendars of upcoming Iranian political/military events in early-to-mid March 2026.  
Roughly 60 % of the queries are historical, 40 % current, with one Agent query for the heavy base-rate computation.

Search queries:
1. [HISTORICAL] irgc google trends 2025 daily (Google) -- Intent: obtain daily trends data for “irgc” in 2025 to gauge typical volatility and decay after spikes.  
2. [HISTORICAL] google trends scaling fixed date range (Google) -- Intent: clarify how locking start/end dates affects number stability, relevant to resolution mechanics.  
3. [HISTORICAL] irgc search interest spikes history (Google) -- Intent: list previous occasions when “irgc” interest surged, to link with causal events.  
4. [HISTORICAL] IRGC big news timeline 2024 2025 (Google) -- Intent: compile a chronological list of major IRGC-related incidents to match with trend jumps.  
5. [HISTORICAL] Using Google Trends daily data for "irgc" in the United States from 2024-01-01 to 2026-03-01, calculate the distribution of 12-day interest changes and the frequency with which the absolute change exceeds 3 points; provide mean, median, and 90th percentile change sizes. (Agent) -- Intent: generate quantitative base-rate statistics directly.  
6. [CURRENT] IRGC attack March 2026 (Google News) -- Intent: detect any fresh or unfolding military incidents that could sustain high search interest.  
7. [CURRENT] U.S. sanctions IRGC 2026 (Google News) -- Intent: find new or pending sanction actions that might keep the topic in headlines through 14 Mar.  
8. [CURRENT] Upcoming March 2026 Iran events involving Revolutionary Guard, sanctions, elections, or military drills, United States coverage (AskNews) -- Intent: surface scheduled or expected events in early-to-mid March that could materially move search interest.