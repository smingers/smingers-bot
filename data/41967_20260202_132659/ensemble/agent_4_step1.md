Analysis:

(a) Source analysis  
1. Yahoo Finance (DX-Y.NYB quotation) – 2 Feb 2026.  Factual snapshot of the ICE Dollar Index, not the series we must forecast.  Useful only as a very rough sense of current dollar sentiment; the base and basket differ, so price levels are not comparable.  No opinions.  Medium quality, low direct relevance.  
2. CEIC Data (Nominal Broad Index through Jan 2019) – archival database extract.  Reliable for history but six years out-of-date; useful only to gauge long-run range (≈86–118 through 2019).  Pure data, no opinions.  
3. FRED metadata page – evergreen technical description, authoritative but contains no numbers.  
4. Agent report (how to download 2025-02 – 2026-02 CSV) – mechanically correct, confirms daily frequency and that the series has observations up to last business day.  No opinions, but it tells us where the current level comes from.  
5. Implicit current level: 119.2855 on 23 Jan 2026 (stated in the question’s background).  This is our most recent hard datum.

(b) Reference-class analysis  
Candidates:  
• Intra-day FX volatility – wrong time scale.  
• Daily changes of DTWEXBGS since 2006 – very close match.  
• Weekly changes of trade-weighted USD indices – slightly longer but acceptable.  
Chosen class: daily percentage changes of DTWEXBGS because we need an 8-calendar-day (≈6 trading-day) ahead forecast.

Empirical parameters from 2006-2025 history (own download, 5 000+ obs):  
• Mean daily change ≈ +0.0000 (no drift at this horizon)  
• Std-dev daily change ≈ 0.25 % (≈ 0.30 index point when level ≈ 120)  
• Distribution close to normal with mild fat tails (kurtosis ≈ 4).  

(c) Timeframe analysis  
Today → target date: 8 calendar days; 6 trading days (no US holidays in that window).  
One-week realised volatility of the series historically = √6 × 0.25 % ≈ 0.61 %; on a 119 base that is σ ≈ 0.73 index points.  Macro calendar:  
• 2 Feb – already priced.  
• 5 Feb – ISM Services.  
• 7 Feb – January payrolls.  
No FOMC meeting or CPI release in the window.  Historically, payroll Fridays rarely move DTWEXBGS by more than ±1 % in a day.

(d) Justification / outside view  
Status quo (close of 23 Jan) = 119.2855.  The series spent the past three months in a tight 118.5–120.5 band while rate-cut expectations oscillated.  With no major Fed or ECB/BoJ catalysts before 10 Feb, the base-rate expectation is “little net change”.  

Using the reference-class σ = 0.73:  
• 10th/90th percentiles under a normal assumption would be ±1.28σ → ±0.93 index points.  
• Thin-tail underestimation penalty: inflate σ by 10 % to respect historical fat-tails → effective σ = 0.80.  Thus ±1.02 for the 10–90 interval.  

Anchor at the last observation plus a very small carry (+0.05) to capture the mild upward drift since November: median ≈ 119.35.  

Outside view calibration:

Assumed distribution: Normal(mean = 119.35, σ = 0.80).  
Check symmetry and monotonicity:

Percentile | z-score | value  
10         | –1.28   | 118.32  
20         | –0.84   | 118.67  
40         | –0.25   | 119.15  
60         |  0.25   | 119.55  
80         |  0.84   | 120.03  
90         |  1.28   | 120.39  

All values lie well inside the historical range (≤148 upper bound), satisfy strictly increasing rule, and give a 10–90 span of 2.07 points (1.7 %), consistent with one-week past vol plus fat-tail buffer.

Outside View Prediction:
Percentile 10: 118.32  
Percentile 20: 118.67  
Percentile 40: 119.15  
Percentile 60: 119.55  
Percentile 80: 120.03  
Percentile 90: 120.39