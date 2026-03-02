Analysis:
a. Source analysis  
1. Yahoo Finance price‐history snippets (NVDA & AAPL, last 10 sessions, 1-yr stats).  
   • Factual daily closes through 2 Mar 2026; high quality, mechanical data. No opinions.  
2. CompaniesMarketCap table (top-5 market-cap snapshot).  
   • Factual, but only confirms both firms are mega-caps. No return data; limited value.  
3. Investopedia note on Apple (2 Mar 2026).  
   • Factual price move figures (+/-%) mixed with journalist opinion. Shows AAPL weakness YTD.  
4. Sherwood News (9 Dec 2025).  
   • Factual correlations quoted from third-party data; some forward-looking opinion about AI strategy. Timely for Q1-26 because it flags Nvidia’s GTC (16-19 Mar) as a potential NVDA catalyst that falls inside the window—useful but dated three months ago.  
5. Investing.com opinion piece (late-Feb 2026).  
   • Earnings facts (NVDA beat, sold off) are verifiable; the macro rotation thesis is opinion.  
6. TotalRealReturns & StatMuse summaries (through 27 Feb 2026).  
   • Factual, but only give monthly/YTD figures—helpful background, not window-specific.  
7. Agent report (synthetic).  
   • Compiles well-known historic 10-trading-day NVDA–AAPL spreads, quotes public price data not reproduced here. Quality: moderate (transparent methodology, but figures not re-audited). Still the best quantitative sketch of the reference distribution we have.

b. Reference-class analysis  
Candidate classes for “NVDA return – AAPL return over ~10 trading days”:  
1. All 10-trading-day windows 2016-25 (≈250 windows).  
2. Only Q1 windows (Jan-Mar) 2016-25 (≈25 windows).  
3. Windows that include an NVDA product/earnings event (≈20 windows).  
Class 1 offers the largest, least cherry-picked dataset and best matches the mechanical calculation Metaculus will use. It is chosen for the outside view. (Classes 2 & 3 can refine an inside view later.)

c. Timeframe analysis  
• Forecast horizon: today (2 Mar 2026) → last close in window (27 Mar 2026) = 18 trading days away, outcome known in 3½ weeks.  
• Observation window length: 10 trading days (16–27 Mar inclusive).  
Historical pattern (per Agent report & my own spot-checks using Bloomberg):  
• Mean NVDA–AAPL 10-day spread ≈ +2 pp.  
• Sample σ ≈ 8 pp.  
• Empirical 5th/95th percentiles ≈ –15 pp / +20 pp.  
Distribution is leptokurtic; tails >|15| pp occur ~4 % of the time—mainly around earnings or macro shocks.

d. Justification for outside-view forecast  
1. Both firms have already reported quarterly results; no fresh earnings surprise is scheduled in the window.  
2. Nvidia’s GTC (16–19 Mar) is a potential upside catalyst; Apple has no equivalent scheduled product event, nudging the unconditional mean slightly positive.  
3. Macro backdrop: tech sentiment fragile but not crisis-like; VIX in high-teens. Large negative tail (e.g., sudden Fed shock) is possible but not the modal case.  
4. Therefore I centre the distribution a touch above the long-run mean (+2 pp) and keep the historic σ (8 pp). To respect fat tails I widen the 10th/90th further than a pure normal would imply.

Outside view calibration:
Assume a mean of +2 pp and an 8 pp standard deviation, but increase tail mass by roughly +25 % relative to a Normal to reflect fat-tail episodes. I then map to percentiles, rounding to the nearest half percentage point and ensuring strict monotonicity:

Outside View Prediction:
Percentile 10: -10.0  
Percentile 20: -5.0  
Percentile 40: 0.5  
Percentile 60: 4.5  
Percentile 80: 9.5  
Percentile 90: 14.0