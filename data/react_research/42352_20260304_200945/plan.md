# Research Plan: How much will Crude Oil Futures total price returns exceed S&P 500 Futures's in these biweekly periods of Q1 2026? (Mar 16 - Mar 27)

Part 1. Key uncertainties to resolve

1. Magnitude and direction of crude-oil price moves during 16-27 Mar 2026  
   • Oil’s total return is half of the “spread” we must forecast. Supply shocks (Middle-East conflict, Russia, OPEC+ quotas, U.S. shale output), demand signals (China PMI, OECD growth), and inventory data can swing CL ≥5 pp in two weeks.

2. Magnitude and direction of S&P 500 futures moves during 16-27 Mar 2026  
   • The other half of the spread. U.S. macro releases (CPI 17 Mar, FOMC decision 18 Mar, PCE 27 Mar), earnings announcements, and shifts in Fed-rate expectations could quickly add or subtract several percentage points from ES.

3. Event schedule overlap and asymmetric impact on oil vs. equities  
   • An OPEC+ ministerial on 22 Mar would hit CL far more than ES; a dovish FOMC would help ES more than CL. Knowing which high-impact events actually fall inside the window clarifies which leg is likely to outperform.

4. Typical 9-trading-day spread distribution (CL return – ES return)  
   • Historical mean, volatility, skew, and any regime dependency (e.g., wartime) give a statistical prior that a forecaster can update with current fundamentals.

5. Current market positioning and sentiment in both contracts  
   • Extreme net-speculative length/short or elevated implied volatility can foreshadow outsized, one-sided moves or mean-reversion over the next fortnight.

Part 2. Research plan (ordered by importance)

1. yFinance query: CL=F  
   – Pull daily closes 2016-present.  
   – Goal: compute rolling 9-trading-day returns and volatility to size plausible CL moves (uncertainties 1 & 4).

2. yFinance query: ES=F  
   – Same extraction and calculations for ES.  
   – Goal: baseline ES volatility and the historical CL−ES spread (uncertainties 2 & 4).

3. Google News search: “OPEC March 2026 meeting”  
   – Identify exact date and agenda of any OPEC/OPEC+ gatherings and consensus on quota policy.  
   – Pinpoints potential asymmetric oil shock (uncertainties 1 & 3).

4. AskNews query: “Upcoming U.S. FOMC March 2026 decision market expectations”  
   – Collect previews and probability distributions for rate path and dot plot.  
   – Gauges likely ES reaction and cross-asset spill-over (uncertainties 2 & 3).

5. Google News search: “EIA oil inventory March 18 2026”  
   – Find analyst expectations for the two weekly EIA releases (18 Mar & 25 Mar).  
   – Assess whether inventories are tightening or loosening, affecting CL inside the window (uncertainty 1).

6. AskNews query: “Speculative positioning CFTC crude oil March 2026”  
   – Retrieve latest Commitments of Traders commentary.  
   – Measures crowdedness/risk of reversal in CL (uncertainty 5).

7. AskNews query: “S&P 500 earnings releases week of 16 March 2026”  
   – List any mega-cap or sector-defining earnings due.  
   – Spots equity-specific catalysts (uncertainties 2 & 3).

8. Google News search: “Geopolitical risk Middle East March 2026 oil”  
   – Scan for brewing conflicts, shipping threats, sanctions timelines.  
   – Supplements oil-specific event assessment (uncertainty 1).

9. Google search: “S&P 500 futures implied vol March 2026”  
   – Look for VIX-related commentary or options data.  
   – Helps judge sentiment/positioning in equities (uncertainty 5).

10. Google Trends query: Oil price  
    – Detect surges in public attention that often accompany big price moves; useful sentiment cross-check (uncertainty 5).

Follow the list top-down; later items can be skipped if earlier searches already clarify the corresponding uncertainty.