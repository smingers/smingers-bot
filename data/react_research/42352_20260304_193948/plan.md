# Research Plan: How much will Crude Oil Futures total price returns exceed S&P 500 Futures's in these biweekly periods of Q1 2026? (Mar 16 - Mar 27)

Research Plan for “CL vs ES Bi-Weekly Return Spread, Mar 16–27 2026”

────────────────────────
PART 1. Key uncertainties
1. Direction & magnitude of CL futures price change (Mar 13 close → Mar 27 close).  
   Why: 50 % of the spread. Highly sensitive to OPEC+ policy, Middle-East/Russia supply disruptions, and Chinese demand data released in this window.

2. Direction & magnitude of ES futures price change over the same dates.  
   Why: The other 50 %. Reacts mainly to U.S. macro news (FOMC meeting, CPI/PPI, earnings confessions) and global risk sentiment.

3. Event calendar asymmetries that could differentially hit oil or equities between Mar 16–27.  
   Why: A big oil-specific shock (e.g., OPEC+ meeting) or equity-specific shock (e.g., Fed decision) could swing the spread by several pp.

4. Current market-implied distribution for each asset (short-dated volatility, option skew, positioning).  
   Why: Converts qualitative news into quantitative tails; helps set the mean and credible interval of the spread.

5. Recent correlation regime between CL and ES.  
   Why: If they are tightly positively correlated, the spread’s expected absolute value is smaller; if anti-correlated, larger. Guides baseline and uncertainty.

────────────────────────
PART 2. Step-by-step research actions
1. yFinance | CL=F 1-mo history  
   Learn: Latest close price (Mar 3), 1-month % swings, spot vs nearby contract rollover dates.  
   Addresses: Uncertainty #1 baseline & volatility.

2. yFinance | ES=F 1-mo history  
   Learn: Same metrics for S&P 500 futures.  
   Addresses: Uncertainty #2 baseline & volatility.

3. yFinance | ^OVX, ^VIX 3-mo history  
   Learn: Short-dated implied vol for crude oil and equities; compare current level to 3-mo median.  
   Addresses: Uncertainty #4 (market-implied dispersion).

4. Google News | “OPEC+ meeting March 2026”  
   Learn: Whether OPEC/JMMC meets during Mar 16–27, leaked quota rhetoric.  
   Addresses: Uncertainties #1 & #3 (oil-specific catalyst).

5. AskNews | “Middle East oil supply risks March 2026”  
   Learn: Any brewing geopolitical threats (Strait of Hormuz, Iraq, etc.) timed for the period.  
   Addresses: Uncertainties #1 & #3.

6. Google News | “FOMC March 2026 meeting expectations”  
   Learn: Exact dates, market consensus on rate decision, dot-plot chatter.  
   Addresses: Uncertainties #2 & #3 (equity-specific catalyst).

7. Google News | “US CPI release March 2026 preview”  
   Learn: Release date (likely Mar 17) and surprise risk sizing.  
   Addresses: Uncertainty #2 (macro data shock differential).

8. FRED | OILINV (or “Ending Stocks excluding SPR”) latest weekly  
   Learn: Inventory trend; large draws/builds affect near-term crude prices.  
   Addresses: Uncertainty #1 (fundamental supply signal).

9. yFinance | CL=F vs ES=F 6-mo correlation  
   Method: Download daily returns; compute 60-day rolling corr.  
   Learn: Current correlation regime intensity & sign.  
   Addresses: Uncertainty #5.

10. Google Trends | “oil price”  
    Learn: Retail attention spikes which sometimes precede volatility.  
    Addresses: Supplementary to Uncertainties #1 & #4 (sentiment gauge).

Follow items 1–4 first; they supply the core quantitative baselines and the biggest scheduled catalyst. Subsequent steps refine probability distribution and correlation adjustments.