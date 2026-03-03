Analysis:
The forecaster needs:  
• Base rate: historical Brent prices and volatility to bound the likely range the price can reach in nine days; seasonality around mid-March.  
• Resolution mechanism: confirmation that the FRED series DCOILBRENTEU is the data that will be checked and typical publication lag/revisions. (Covered by including the FRED pull.)  
• Key drivers up to 2026-03-12: 1) Any OPEC+ production decision expected in the coming days, 2) Geopolitical supply shocks (Middle East, Russia/Ukraine), 3) Macro-demand news (global growth, inventories).  
• Current state: the latest spot/FRED value, current forward curve, news on supply/demand, scheduled OPEC+ meeting.  
• Contrarian check: examples of very large one-week moves and their causes to judge tail-risk.

The search strategy therefore:  
– Pull the full FRED data for baseline and lag awareness.  
– Find studies or datasets on daily volatility and past March-12 prices.  
– Gather historical examples of rapid price moves (> $10/wk) to bound extreme scenarios (Agent query).  
– Collect current quotes and immediate news about OPEC+ and geopolitical supply risk that could move prices before 12 Mar 2026.

Search queries:
1. [HISTORICAL] DCOILBRENTEU (FRED) -- Intent: Retrieve complete historical Brent daily series for base-rate stats and update lag patterns  
2. [HISTORICAL] Brent daily price volatility history (Google) -- Intent: Locate analyses/data on historical day-to-day volatility of Brent to estimate expected short-term move range  
3. [HISTORICAL] Brent price March 12 past years (Google) -- Intent: Get historical Brent prices on 12 March each year to check seasonality/base rate  
4. [HISTORICAL] OPEC+ decision impact Brent historical (Google) -- Intent: Find studies or past cases of Brent’s reaction to OPEC+ production announcements  
5. [HISTORICAL] Provide a list of historical episodes from the last 15 years where Brent crude moved more than $10 within a single week, noting the trigger events and summarizing common patterns. (Agent) -- Intent: Build contrarian/outlier move reference class  
6. [CURRENT] Brent crude price today March 3 2026 (Google News) -- Intent: Obtain the latest quoted Brent price and immediate market commentary  
7. [CURRENT] Upcoming OPEC+ meeting March 2026 (Google News) -- Intent: Verify if an OPEC+ meeting or statement is scheduled before 12 Mar and what analysts expect  
8. [CURRENT] Latest coverage of Middle East oil supply disruptions or ceasefire talks affecting Brent crude prices in early March 2026. (AskNews) -- Intent: Collect news on geopolitical risks that could trigger sharp price moves before resolution