Analysis:

(a) Source analysis  
1. BigTechnology interview (Feb 2026): no concrete dates for GPT-6; quality medium. Mainly competitive context.  
2. LifeArchitect.ai living document: crowdsourced chronology, accurately logged past OpenAI releases. Contains both facts (dates already happened) and author speculation (e.g., “GPT-6 due 2026”). Use the factual dates; treat future-looking lines as opinion. Quality: fair but un-official.  
3. CNBC (19 Aug 2025): on-record remarks by Sam Altman; high-quality primary evidence that GPT-6 is in development and “will arrive faster than GPT-4→5 gap”. No calendar commitment.  
4. ZDNet (Aug 2025): basically a rewrite of the CNBC story; no new facts.  
5. Times of India (31 Oct 2025): reports Altman tweet saying the model “will be renamed GPT-6-7”. Could be humour or re-branding; reliability low but points to naming uncertainty.  
6. Agent report: aggregated public release chronology (2020-2025) and five leadership quotes. Fact section cross-checks well with known OpenAI blog posts; judgement: good for historical dates, weaker on forward claims.

(b) Reference class analysis  
Candidate reference classes:  
R1. Time gaps between numbered GPT releases (GPT-3→4: 34 mo, GPT-4→5: 29 mo).  
R2. Time gaps between “flagship” model families across the whole industry (e.g., Google Gemini 1→2: 14 mo).  
R3. Any OpenAI upgrade of size ΔP ≥ 1.5× parameters (e.g., GPT-4→4o: 14 mo).  

The decision hinges on OpenAI’s own numbering convention, so R1 is most relevant. R2 and R3 show faster cycles but normally use incremental or different names rather than a new integer. I therefore use R1 as the base-rate class.

(c) Timeframe analysis  
Time remaining until resolution: 91 days.  
Observed historical pattern (R1): after a new integer model ships, the hazard of the next shipping within the first nine months is tiny; none of the two historical precedents did so (0/2). If we naïvely assume an exponential waiting-time distribution with mean 31 months (average of 34 and 29), the probability of arrival inside 9 months is 1 – exp(-9/31) ≈ 25 %. That is an upper bound; because OpenAI often soft-launches smaller point versions first (5.1, 5.2), the effective hazard for a brand-new integer number is plausibly lower.

(d) Justification / adjustments  
• Acceleration factor: Altman’s August-2025 quote (“faster than 29 mo”) does increase the hazard. If “faster” merely means 15-20 months, it does not help for a date only 9 months out. Small upward adjustment: +5 percentage points.  
• Compute readiness: Oracle “Stargate” capacity went live mid-2025, so training could have begun early enough. Training + alignment + eval pipelines for GPT-5 were ~11 months (inferred), so finishing by April 2026 would be unusually quick but not impossible. +3 pp.  
• Naming risk: The October-2025 “GPT-6-7” tweet and general trend to label variants (4o, 5.2) increases the chance the next flagship will not be called plain “GPT-6”. –6 pp.  
• Regulatory / safety headwinds and recent public criticism (post-GPT-5 launch issues) add friction. –5 pp.

Starting from the naïve 25 % exponential estimate and applying the net −3 pp adjustment yields ~22 %. However, that exponential bound itself is optimistic because it does not factor in the two-point empirical record (0/2). Treating the empirical frequency (0 %) as a Beta(1,3) posterior gives a mean of 25 %, but with wide variance. Combining both lines of evidence, I shrink modestly toward the empirical side and arrive at the low-20 s.

Outside view calibration:
• Anchor: exponential waiting-time odds for a 31-month mean → 25 % in nine months.  
• Empirical small-N correction (0/2 precedents) pushes downward.  
• Qualitative adjustments (acceleration, naming, regulation) net to roughly –3 pp.  
Resulting calibrated outside-view probability: 22 %.

Outside View Prediction:
22 %

