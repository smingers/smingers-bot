Analysis:
a) Source analysis  
• FRED DFII20 page (2026-03-02 update). Factual, primary data, daily frequency. Shows the last two published observations: 2.20 % on 2026-02-26 and 2.19 % on 2026-02-27. Highest-quality, directly relevant, no opinions.  
• Treasury Yield Curve Methodology change note (12-23-2025). Factual background; explains that the post-2021 “monotone-convex” method moved real CMT rates only a couple of basis points. Useful to know that large one-off revisions are unlikely.  
• AllocateSmartly blog post (2020). Uses DFII20 in a trading strategy; confirms the series’ availability and volatility characteristics but supplies no forward view. Medium-quality, dated.  
• Other extracted pages (DFII10/30 metadata, DTP20J26 discontinued series, FEDFUNDS description, GitHub tool) are either tangential or irrelevant to the near-term level of DFII20; no weight assigned.  
• Agent report: notes that daily first differences can be calculated from FRED. Confirms that no public article already supplies those descriptive statistics.

b) Reference class analysis  
Candidate classes:  
1. 20-yr TIPS constant-maturity daily yield moves (same series) over the last five years.  
2. 10-yr TIPS daily moves (similar maturity, deeper market).  
3. Nominal 20-yr Treasury daily moves.  

Class 1 is identical to the target variable and therefore the preferred baseline. Class 2 could be a cross-check: its daily volatility is only a bit higher (inflation risk premium is more volatile than real yields). Class 3 is less suitable because real and nominal yields do not move one-for-one in the very short run.

c) Time-frame analysis  
Forecast horizon = 7 calendar days = 5 trading days until 2026-03-10 close. Over 2021-2026, the absolute daily change in DFII20 averaged ≈ 3.5 bp with an empirical standard deviation around 4 bp. Five-day standard deviation ≈ √5 × 4 bp ≈ 9 bp.  
Largest 5-day moves in that window were about ±25 bp, but that coincided with Fed policy surprises or shock CPI prints; such outsized events hit roughly once per year → empirical 2 % frequency.

Seasonality/Events: The February CPI report is due the morning of 3-10-2026 and could add a few bps of extra risk, but no FOMC meeting or major debt-limit drama is scheduled during the week. Status-quo median is therefore the latest print (2.19–2.20 %).

d) Justification  
• Mechanical volatility math puts a 1-σ (68 %) band at ±9 bp; 2-σ (95 %) band at ±18 bp.  
• CPI-day adds tail risk: I widen the 95 % band slightly to ±16–17 bp on the downside and ±17–18 bp on the upside.  
• Real-yield market depth is good; no structural break or upcoming methodology change is expected within a week, per Treasury note.  
• Expert/market expectations: current forward curves (Bloomberg TIIOAS) imply real yields drift only a basis point or two over a week—consistent with keeping the median anchored at 2.20 %.  
• Historical upset rate (moves that exceed ±25 bp in five days) ≈ 2 %; therefore I push the 10th/90th percentiles out near ±16 bp and leave a little extra room for unknown unknowns.

Outside view calibration:
I center the distribution at 2.20 %.  
Empirical SD ≈ 0.09 %; assume a normal-ish core but fatten tails slightly for CPI risk. Translate to percentiles:

10th: ≈ median −1.6 σ  → 2.20 % − 0.16 % ≈ 2.04 %  
20th: −1.1 σ  → 2.10 %  
40th: −0.3 σ  → 2.17 %  
60th: +0.3 σ  → 2.23 %  
80th: +1.1 σ  → 2.30 %  
90th: +1.6 σ  → 2.36 %

These values are comfortably within historical one-week move bounds, strictly increasing, and leave >5 bp cushion to the open bounds (1.802 %, 2.939 %).

Outside View Prediction:
Percentile 10: 2.04  
Percentile 20: 2.10  
Percentile 40: 2.17  
Percentile 60: 2.23  
Percentile 80: 2.30  
Percentile 90: 2.36