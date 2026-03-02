Analysis:

(a) Source analysis  
1. Wikipedia biographies of Janez Janša, Slovenian Democratic Party (SDS) and Robert Golob (GS) – solid, up-to-date factual overviews, negligible opinion content.  Useful for long-run party strength and ideological positioning.  
2. Wikipedia 2022 election page – official final seat counts, therefore high factual value.  
3. Wikipedia “Opinion polling for the 2026 election” – structure is reliable but numerical tables missing in the extract, so of limited quantitative value for this exercise.  
4. PolitPro aggregate (19 days old) – proprietary model, transparent about methods, but not peer-reviewed; treat as a single poll-of-polls rather than ground truth.  
5. Reuters, FT, etc. (Janša acquittal, Bank governor approval, assisted-dying referendum) – reputable journalism; provide context but no numbers.  
6. Academic chapter on party system, IDEA note on electoral rules, Electoral-Reform.org explainer – high-quality background, little direct quantitative input.  
7. Agent report table of every election 1992-2022 plus final-poll errors – data compiled from official electoral commission and archived polls; methodology stated; cross-checks with my own spot checks match.  I treat this as the backbone quantitative source.  
Overall, only the agent report delivers the hard historical numbers (seat gaps and poll errors) required for a reference-class approach.

(b) Reference class analysis  
Candidate classes:  
• All eight National-Assembly elections since 1996 that featured both SDS and a liberal/centrist challenger (LDS → GS family) (sample size = 8)  
• Sub-set of those elections in which SDS was in opposition (2004, 2018, 2026) (sample size = 2)  
• All Slovenian elections regardless of the parties involved (1992-2022, n = 9)  

The forecasting target is “SDS seats minus GS seats”.  The first class isolates exactly that rivalry across time and supplies eight usable data points – large enough to sketch a base distribution yet small enough to remain comparable.  I therefore adopt it.

Observed seat-gap values (SDS–liberal) by year: 1996 –9, 2000 –20, 2004 +6, 2008 –1, 2011 –2, 2014 –15, 2018 +12, 2022 –14.  
Mean = –5.4 seats Std dev ≈ 10 seats.  Histogram roughly symmetric but slightly left-skewed (SDS behind more often than ahead: 6/8 times).

(c) Timeframe analysis  
Today is 2 March 2026; polling day is 22 March – 20 days away.  Historically, shifts larger than 5 percentage points (~10 seats) within the final three weeks have been rare but not unheard of (2004 swing against LDS, 2022 tactical wave for GS).  Thus most of the eventual SDS–GS gap is already “baked in”, yet fat-tail surprises (late tactical vote, scandal) cannot be ruled out.

(d) Justification for the outside-view forecast  
1. Base statistical tendency: SDS trails liberal challengers by ≈5 seats on average and leads only one-quarter of the time.  
2. Volatility: Standard deviation of 10 seats implies a broad 80 % range spanning roughly –15 to +5 seats.  
3. Incumbency drag: Governing parties in Slovenia have lost vote share in 7 of the last 8 elections; this mechanically favours SDS in 2026, nudging the distribution rightwards by ~2 seats relative to the unconditional mean.  
4. Poll error asymmetry: The agent report shows polls have on average overstated SDS by about 3½ percentage points (~7 seats) while understating the liberal challenger by ~5 pp (~10 seats).  That pattern tempers the pro-SDS shift by reminding us that an apparent SDS polling lead often melts on election day.  
5. Time remaining: With only 20 days left, we down-weight scenarios requiring double-digit movements but still allow ≈10 % probability mass in each tail for genuine shocks.  
Blending these considerations, I centre the 50th-percentile around –3 seats (slender GS edge) but widen intervals to capture the historical ±15-seat swings.

Outside view calibration:

• Distribution type chosen: symmetric but slightly skewed to the left (favouring small GS advantage).  
• Anchors: Empirical mean (–5.4), plus +2 seat incumbency correction → baseline –3.4 ≈ –3 seats median.  
• Spread: 80 % of past outcomes fall within ±12 seats; I retain that span.  
• Tail probability: Assign 10 % combined to outcomes beyond ±15 seats in line with two extreme historical cases (2000 –20, 2018 +12).  

Outside View Prediction:
Percentile 10: –18  
Percentile 20: –12  
Percentile 40: –5  
Percentile 60:  +1  
Percentile 80:  +8  
Percentile 90:  +13