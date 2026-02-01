Analysis:

### 1) Resolution criteria (make sure we’re forecasting the right thing)
This resolves to the **Rotten Tomatoes Tomatometer (critics) score** for *Melania* **as observed on or after February 13, 2026**, when Metaculus checks the page. (Not the audience/Popcornmeter score.)

### (a) Source analysis (what each source contributes; quality; fact vs opinion)
- **BBC (Jan 31, 2026)**: High-reliability outlet. Gives contextual reporting on screenings, controversy, and public reaction. Mostly *descriptive journalism*; it does not provide a precise RT score. Useful for understanding polarization/timing controversy (which affects critics’ tone), but not a direct numeric anchor.
- **Los Angeles Times (Jan 31, 2026)**: High-reliability major paper; includes strong editorial/critical opinion. Provides budget and content details, and a named critic’s harsh assessment. Opinion is clearly labeled (culture critic), but indicates likely continued negative critical consensus.
- **The Globe and Mail (Jan 30, 2026)**: Major publication, credible reviewer. Provides an extremely negative review (opinion), supporting the idea that many professional critics will rate it “rotten.”
- **The Hollywood Reporter (Jan 30, 2026)**: High-reliability trade. Critically important *factual* datapoint: reports RT score “around 16% based on 16 reviews” at that time, plus compiles many named critic takes (opinions) that are overwhelmingly negative.
- **Fox News (Feb 1, 2026)**: Mixed reliability due to framing, but the *reported numeric RT critics score (11%)* is straightforward and likely accurate. Also contrasts with 99% verified audience score (not our target).
- **The Daily Beast (Feb 1, 2026)**: Partisan tone, but the *RT score reporting (11%)* is likely accurate; includes box office and market anecdotes.
- **AskNews KRQE 13 (Feb 1, 2026)**: Local-TV syndication style, but cites NYT/industry figures; importantly reports *critics score around 10%* and describes demographics. Useful numeric anchor consistent with others.
- **AskNews ScreenRant / Us Weekly / Express / O Globo / Raw Story / TVA Nouvelles / Le Journal de Montréal / Breitbart**: Variable reliability. Several report critics scores ranging **6% to 11%**; some appear to be capturing *moment-in-time* snapshots as the review count updates. Raw Story/Breitbart are highly slanted; I treat them mainly as noisy corroboration that the score is in the low teens/single digits rather than as precise measurement.
- **“Outside view prediction” block in prompt (Feb 1 access)**: A synthesis. I treat it as a helpful structured baseline, but not a primary source. Its key claim—**~10-11% with ~20 reviews by Feb 1**—matches multiple independent outlets.

### (b) Evidence analysis (weighted factors affecting Feb 13 Tomatometer)
**Strong evidence**
1. **Multiple independent outlets converge on ~10-11% Tomatometer as of Feb 1** (Fox, Daily Beast, KRQE/NYT-style recap; plus other summaries). This is a direct measurement close to the resolution date and is hard to ignore.
2. **The review sample is already non-trivial (~16-20 critics)** and includes major outlets (Variety, THR, Guardian, etc.). Once big critics are in, large reversals are historically uncommon.
3. **Uniformly negative named-critic reception** across prestige publications (THR compilation; LAT/Globe reviews). Mechanism: Tomatometer is binary fresh/rotten; if most critics are calling it propaganda/boring, few will mark it “fresh.”

**Moderate evidence**
4. **Trajectory noise early (reports of 6%, 8%, 10%, 11%, ~16%)** suggests the score can move a few points as denominator grows, but it’s moving within a low band. Mechanism: with small-N, each fresh review moves the percent more.
5. **Polarizing political subject + “authorized/propaganda” framing** tends to keep critics’ scores low even if audience scores are high (consistent with current 99% verified audience). This matters because it reduces the chance of a late wave of “fresh” reappraisals.

**Weak evidence**
6. **Box office strength / audience enthusiasm**: may encourage more critics to review it (increasing N) but doesn’t imply higher critic approval.
7. **Protests/timing controversies**: could marginally worsen critical tone, but most critics already seem firmly negative.

### (c) Timeframe analysis
- **Forecast horizon:** from **Feb 1 to Feb 13 = 12 days**.
- In 12 days, I expect the Tomatometer to **stabilize** further as more reviews post (likely ending somewhere around ~30-60 total critics, but uncertain).
- **If the timeframe were halved (to ~6 days):** I’d expect even less movement from today’s ~10-11%—perhaps ±2-3 points.
- **If the timeframe were doubled (~24 days):** slightly more drift is possible (more long-tail critics), but big jumps are still unlikely given the already-established consensus; maybe +3 to +8 points at most in a plausible upside scenario.

### (d) Justification (outside view → inside view)
**Outside view base rate:** Films that sit around **~10% Tomatometer after ~15-20 reviews** typically finish still “rotten,” often **single digits to high teens**, with only modest regression upward unless there’s a genuine split among critics (not evident here).

**Inside view adjustment using current information:**
- The film’s *current* measured score is already extremely low and repeatedly corroborated (**~10-11% on Feb 1**).
- The critical rhetoric is not “mixed” but “scathing,” which implies additional reviews are likely to be “rotten” as well.
- Therefore I anchor near **12-14%** for Feb 13, with:
  - **Downside**: additional negative reviews from remaining major outlets could keep it near ~6-10%.
  - **Upside**: a trickle of contrarian/regional critics (or “interesting as artifact” takes) could lift it into the high teens/low 20s, but a move above ~25% would require an implausibly high share of fresh reviews from here.

Probability calibration

- **Trend continuation (status quo):** stays about **10-13** as more reviews accumulate.
- **My median:** **13** (small upward drift from 10-11 as denominator grows and a few fresh reviews appear).
- **My mean:** about **14** (slight right-skew: more room to drift up to ~20+ than to collapse far below current levels, though both are possible).
- **Uncertainty:** still meaningful because of small-ish N and possible future review influx, so I keep a fairly wide 90/10 interval.

Checklist:
1) Target variable: RT **Tomatometer critics score** for *Melania* as of/on/after **Feb 13 2026**, units percent.  
2) Outside view base rate: films at ~10% after ~20 reviews usually finish ~8-18.  
3) Consistency: Implied median = 13; mean = 14; consistent with “already scathing, limited upside.”  
4) Key evidence: (i) multiple reports of ~10-11% on Feb 1; (ii) many major critics already in; (iii) consensus language “propaganda/boring” suggests continued rotten reviews; (iv) early fluctuations (6-16%) imply a few-point drift possible.  
5) Blind spot: a surprisingly large wave of *fresh* reviews from mid-tier/regional critics pushing it into mid/high-20s (would push outcome up).

Distribution:
Percentile 1: 4  
Percentile 5: 6  
Percentile 10: 8  
Percentile 20: 10  
Percentile 40: 12  
Percentile 60: 14  
Percentile 80: 17  
Percentile 90: 20  
Percentile 95: 23  
Percentile 99: 28