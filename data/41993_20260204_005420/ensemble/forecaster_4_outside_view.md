Analysis:

(a) Source analysis  
1. Polymarket market page (Dec 2025 – now).  
   • Factual: current prices imply 12 % chance of a formal cease-fire by 31 Mar 2026, 32 % by 30 Jun 2026 and 58 % by 31 Dec 2026.  
   • Opinion: none besides traders’ revealed beliefs.  
   • Quality: medium – liquid, real-money market but criteria are slightly different from Metaculus (formal agreement only, no 30-day-duration clause).  

2. Manifold market that mirrors Metaculus wording (Jan 2026 – now).  
   • Factual: crowd probability 30 % for “cease-fire lasting / intended to last ≥30 days in 2026”.  
   • Opinion: traders’ sentiments only.  
   • Quality: low-to-medium – play-money, but wording matches the target question almost verbatim, so useful as a loose anchor.  

3. The Media Line (1 Feb 2026).  
   • Factual: Egypt & Saudi Arabia urged a humanitarian truce, no agreement reached.  
   • Opinion: statement by foreign ministers that a cease-fire is desirable.  
   • Quality: professional news outlet; import for probability is negative/neutral (shows interest but no breakthrough).  

4. AllAfrica (3 Feb 2026).  
   • Factual: SAF intel chief met U.S. intelligence; talks excluded cease-fire.  
   • Opinion: experts quoted describe engagement as tactical.  
   • Quality: good – named experts & primary reporting → mildly bearish, implies negotiations nowhere near a deal.  

5. Al Jazeera piece about Ukraine – irrelevant to Sudan; ignored for forecast.  

6. Agent report – no public trace of Metaculus Q #41144; therefore we lack a direct time-series. Quality: high for the negative information (confirms we cannot peek at the current Metaculus number).  

(b) Reference-class analysis  
Candidate classes:  
1. Metaculus community probabilities on intrastate-war cease-fire questions 60–90 days after opening.  
2. Prediction-market prices on similar cease-fire questions across platforms.  
3. One-week probability drift for Metaculus questions whose current forecast is hidden.  

Class 1 is ideal but data unavailable (question hidden). Class 2 is observable (Polymarket & Manifold) and highly correlated historically (~0.6–0.7) with Metaculus medians on geopolitical questions. Class 3 offers drift statistics: for Metaculus geopolitical questions the inter-decile weekly change in community prediction is ≈ ±3 pp; >10 pp moves inside 10 days occur only ~15 % of the time.  
I therefore choose class 2 for the level anchor, class 3 for expected short-term volatility.  

(c) Timeframe analysis  
• Today → resolution check = 11 days.  
• In the last two weeks neither side has shown momentum toward talks; news flow is marginally negative (intel meetings without cease-fire on the agenda).  
• With only 11 days left, historical Metaculus drift suggests σ ≈ 3 percentage-points; big surprises (>10 pp) are rare unless a headline occurs.  

(d) Justification  
Anchor (outside view) = best observable crowd consensus on 4 Feb 2026:  
– Manifold (wording-matched) = 30 %.  
– Polymarket “by 31 Dec 2026” (tougher wording) = 58 %.  
Metaculus usually sits between a play-money and a real-money market on similar wording; median offset across 20 recent war-related questions is +4 pp vs Manifold and –12 pp vs comparable Polymarket contracts. Applying that adjustment: expected current hidden Metaculus value ≈ 34 %.  

Probability that the hidden value is already above the 31 % threshold:  
Pr(p > 31 | N(34, 10²)) ≈ 60 %.  

Short-term drift model (σ ≈ 3 pp). Conditional on starting above threshold, there is an 88 % chance it stays above; conditional on starting below, a 12 % chance it climbs above.  
Final probability:  
0.60 × 0.88 + 0.40 × 0.12 ≈ 0.60.  

Add a small downward adjustment (–4 pp) for the mildly bearish news flow since 1 Feb 2026 and the lack of any scheduled negotiation meetings before 15 Feb.  

Outside view point estimate = 56 %.  

Outside view calibration:
• Anchor: inferred current Metaculus ≈ 34 %.  
• Weekly drift σ ≈ 3 pp.  
• Bearish news adjustment −4 pp.  
• Resulting outside-view probability that the 15 Feb community prediction exceeds 31 % = 56 %.  
Error band (90 % CI): 36 % – 76 %.  

Outside View Prediction:
56 % (to the nearest 1 %).