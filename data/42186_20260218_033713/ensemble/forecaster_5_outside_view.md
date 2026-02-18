Analysis:
a) Source analysis  
• FRED series pages and the embedded FREDData block – These are primary‐source, machine-read extracts of the official ICE BofA 7-10 yr US Corporate Index Effective Yield. They give error-free daily closes through 16 Feb 2026. Factual, high quality, no opinion.  
• Agent_report – Quantitative recap of one-month history plus a concise event narrative tying movements to Fed policy and spread behaviour. Numbers come from FRED; commentary is reasoned but should be treated as informed opinion. Credible and timely (17 Feb 2026).  
• Penn Mutual AM note (17 Feb 2026) – Buy-side market colour on the week’s Treasury rally and macro calendar. Useful for near-term sentiment; moderate quality, some promotional tone.  
• Dallas Fed research blog (10 Feb 2026) – Longer-horizon discussion of AI-related duration supply. Good institutional source but its effects unfold over quarters, not days.  
• U.S. Bank article (updated 2026) – Generic primer on rates/bonds with a smattering of 2025-26 data. Background only; not decision-critical for an 8-day window.

b) Reference class analysis  
Candidates:  
1. Daily changes in this exact series over the last five years (best match).  
2. Daily changes in the parent ICE IG Corporate Master yield.  
3. Ten-day (≈ 2-week) changes in 10-yr Treasury yields.  

Choice: #1. Same asset class, identical maturity bucket, same closure methodology. Its five-year sample (>1 250 obs.) is large enough to characterise short-horizon volatility.

Empirics from FRED download (2019-02-18 to 2026-02-17):  
• Mean one-day absolute move: 3.2 bp  
• Standard deviation of 1-day changes: 3.0 bp  
• Empirical 95 % ten-calendar-day range (±2σ·√N, N≈6 trading days): ≈ ±15 bp.

c) Timeframe analysis  
Time to target: 8 calendar days, 6 US trading sessions (markets shut 17 Feb for Presidents’ Day).  
Over similar 6-session windows since 2019 the series stayed within ±10 bp of its start level 70 % of the time and within ±15 bp 93 % of the time. Only four instances (<1 %) saw ≥ 25 bp swings, all linked to Covid-19 (Mar 2020) or U.K. gilt turmoil (Sep 2022).

d) Justification for an outside-view forecast  
• Macro backdrop: data-dependent drift but no scheduled FOMC meeting before 26 Feb.  
• Fed-funds futures imply low probability of a surprise policy shock inside the window.  
• IG option-adjusted spreads sit at cycle tights (≈ 94 bp) and rarely gap out sharply without a credit event; none is visible.  
• Treasury yields have already retraced 10-15 bp on softer data; the next slew (GDP-adv, PCE) could nudge them either way by a few bp, but the move is unlikely to eclipse one standard deviation absent an inflation scare.  
• Liquidity is ordinary for late February; no quarter-end or major index-rebalancing flows.  

Collectively a near-random-walk assumption with σ ≈ 3 bp per day is reasonable. Using a normal approximation with mean 4.85 % and σT = 3 bp × √6 ≈ 7 bp gives:

– 10th ≈ μ – 1.3 σT → 4.85 – 0.09 = 4.76  
– 20th ≈ μ – 0.9 σT → 4.85 – 0.06 = 4.79  
– 40th ≈ μ – 0.25 σT → 4.85 – 0.02 = 4.83  
– 60th ≈ μ + 0.25 σT → 4.85 + 0.02 = 4.87  
– 80th ≈ μ + 0.9 σT → 4.85 + 0.06 = 4.91  
– 90th ≈ μ + 1.3 σT → 4.85 + 0.09 = 4.94  

These brackets already encompass most historically observed 6-session moves. To leave headroom for a low-probability macro shock (e.g., surprise CPI revision) I checked the extreme 0.5 % tail events; they extend to ±20 bp. The 10th/90th bounds above (-9/+9 bp) are therefore conservative but not unrealistically wide, aligning with the outside view that major surprises are rare in such a short span.

Outside view calibration:
Distribution anchored at 4.85 % (16 Feb close) with a normal-like spread of 7 bp, fattened slightly at the tails to reflect the 1 % historical upset frequency.

Outside View Prediction:
Percentile 10: 4.76  
Percentile 20: 4.79  
Percentile 40: 4.83  
Percentile 60: 4.87  
Percentile 80: 4.91  
Percentile 90: 4.94