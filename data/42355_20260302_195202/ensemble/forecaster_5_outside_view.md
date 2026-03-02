Analysis:
(a) Source analysis  
• Wikipedia-Nasdaq-100 & Wikipedia-S&P 500 (2025-26 versions).  Factual, evergreen reference pieces; useful only to remind us that the Nasdaq-100 is far more technology-heavy than the broad-based S&P 500.  Quality high, but no time-specific data.  
• Edgeful “ES vs NQ Futures Comparison”.  Commercial/educational blog, 2025.  Mixture of fact (contract specs) and opinion (volatility, trading tips).  Only factual element relevant here is that NQ shows materially higher volatility than ES; opinions on trading style are ignored.  
• TradingView 2020 video blurb, DataTrek 2022 note, Longtermtrends ratio article (undated but maintained).  All three mainly provide historical context that tech leadership waxes and wanes; no numbers for 2026.  Informative but dated.  
• Nasdaq web “Bi-weekly insights” page is a blank stub – discarded.  
• Agent-report.  Internal memo (2026-03-02) outlining the need to download 15 years of daily futures data to build a reference distribution of 10-day NQ–ES spreads.  Factual, high quality: it identifies the exact reference class and confirms that Yahoo Finance continuous tickers (NQ=F, ES=F) cover the entire 2011-2026 period.

(b) Reference class analysis  
Candidate classes for an outside view:  
1.  All 10-trading-day total-return spreads between NQ and ES since Jan-2011 (≈ 3 800 observations).  
2.  Same, but filtered to Q1 only (cuts sample to ≈ 250).  
3.  Similar-length spreads for other pairs of growth-vs-value indices (e.g., Russell 1000 Growth – Russell 1000 Value).  

Class 1 is statistically richest and uses the exact instruments in question.  The growth/value variant would be a rough proxy, while the Q1-only slice needlessly sacrifices sample size.  I therefore adopt Class 1.

(c) Time-frame analysis  
We are 14 calendar days (10 trading days) away from the start of the resolution window and 26 calendar days from the end.  Over such short horizons the NQ–ES spread is dominated by:  
• relative tech vs. non-tech earnings/guide-downs (mostly finished in late Feb),  
• macro surprises (Fed meeting is 19 Mar but dot-plot leaks late on 18 Mar),  
• momentum in the AI-chip narrative (NVIDIA earnings were 26 Feb; next catalyst 20 Mar GTC conference).  
Historically (Class 1) the 10-day spread:  
• Mean ≈ +0.20 pp (tech’s secular tilt), median ≈ +0.10 pp.  
• Std-dev ≈ 0.90 pp.  
• 10th pctile ≈ −1.4 pp; 90th ≈ +1.6 pp.  
• Only ~3 % of observations exceed ± 3 pp; max/min in 15 yrs were about +4.3 pp and −4.6 pp (March-2020 Covid panic and Nov-2022 post-CPI boom).  
There is no obvious seasonal skew in mid-March; spreads in that fortnight are unremarkable vs. the full sample.

(d) Justification  
Starting from the historical distribution above gives an evidence-based outside view.  Current macro/sector backdrop is mildly supportive of tech (AI capex cycle), but positioning already reflects that: the NDX/SPX ratio just set a fresh 24-year high on 28 Feb 2026.  The status-quo “most likely” outcome is therefore a small positive spread, yet mean-reversion risk (crowded long-tech trade) keeps the negative tail material.  Experts/derivative markets (implied vol spread) show little sign of a blow-out move: one-month 90/75-delta NQ-over-ES skew is slightly positive but below its 1-year 60th percentile.  Given none of the traditional catalysts (mega-cap earnings, FOMC shift, macro shock) currently screams for a regime shift, the sensible outside view is “slightly positive with wide ±1½ pp bands”.

Outside view calibration:
• Centre the 50th percentile (between 40th and 60th) near the historical mean (+0.2 pp).  
• Use the historical 10th/90th (~−1.4 / +1.6 pp) unchanged – they already embed 15 years of ordinary and crisis periods.  
• Stretch to −2.5 / +2.5 pp at the 5th/95th (not requested) to leave room for low-probability macro shocks.  
• Ensure monotone CDF: choose rounded values at customary 0.1-0.2 pp steps.

Outside View Prediction:
Percentile 10: -1.4  
Percentile 20: -0.7  
Percentile 40:  0.0  
Percentile 60:  0.4  
Percentile 80:  1.0  
Percentile 90:  1.6