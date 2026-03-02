Analysis:

### (a) Source analysis (what each source says; quality/date; facts vs opinions)

1) **Wikipedia: Janez Janša / SDS / Robert Golob / 2022 election / 1992 election (various pages)**  
- **What (facts):** Basic biographies, party positioning, and—most importantly—**official historical seat counts** (e.g., **2022: GS 41, SDS 27**).  
- **Quality:** Generally good for **verifiable, non-controversial facts** (election results, dates, office holding). Weaker on interpretation/labels (“far-right”, “illiberal”), which are partly **editorial characterizations** drawn from media.  
- **Date:** Evergreen; not tailored to 2026 forecasting.

2) **Wikipedia: Opinion polling for 2026 election (table not captured)**  
- **What:** Describes pollsters and structure but **no usable numeric polling** in the extraction.  
- **Quality:** Would be useful if tables were present; as provided, it’s mostly **method/context**.

3) **Electoral-Reform.org.uk explainer (April 2022)** and **IDEA.int electoral system summary**  
- **What (facts):** How seats are allocated (88 PR + 2 minority seats; 4% threshold; national top-up with d’Hondt).  
- **Quality:** High for system mechanics; helps translate vote swings into seat swings. Not predictive.

4) **Springer chapter on party system (1989–2022)**  
- **What:** Academic framing: persistent fragmentation, polarization, and “radical renewal” (party turnover).  
- **Quality:** Good for the **structural outside view** (instability/fragmentation), not for numeric forecasts.

5) **Agent report: historical election table + poll error summary**  
- **What (facts/claims):** Provides a **complete seat table since 1992** for top-2 parties and their gaps; plus a historical **final-poll vs result error** comparison.  
- **Quality:** Useful synthesis, but **secondary** and partly based on PolitPro/other non-primary archives for some early years; I treat it as **directionally informative** on distributions (e.g., typical seat gaps), not as a perfect record.

6) **The New Federalist (2018)**  
- **What:** Journalistic analysis of 2018; notes high undecideds and potential anti-Janša tactical voting; mentions historical polling misses.  
- **Quality:** Reasonable for qualitative patterns; not a data source for 2026.

7) **RosaLux article**  
- **What:** Narrative about “pendulum” dynamics (mobilization against SDS after SDS governs; tactical voting).  
- **Quality:** Ideologically tinted; useful mainly as a reminder of **anti-incumbent/anti-Janša coordination** as a recurring mechanism (qualitative, not numeric).

8) **PolitPro 2026 poll trend (contains numeric seat projection)**  
- **What:** A current poll aggregation projecting **SDS 31 vs GS 22** (gap +9).  
- **Quality:** Potentially helpful for an *inside view*, but it’s not independently verified here and is **not part of a pure outside view**. I’ll treat it as context only, not an anchor.

---

### (b) Reference class analysis (choose a suitable baseline)

We want **SDS seats − GS seats** in 2026. Since GS only exists since 2022, we need a proxy reference class.

**Reference class candidates:**

1) **All Slovenian elections since 1992: seat gap between the top two parties (1st − 2nd)**  
- Pros: Directly about seat gaps in the same electoral system; gives an empirical distribution of gaps (from agent report: gaps of **1 to 20 seats**, often in mid/high single digits).  
- Cons: Our target is *SDS − GS*, not *winner − runner-up*, and sign depends on who places first.

2) **Elections since ~2011 featuring “radical renewal”: dominant new/centrist party vs SDS** (PS 2011, SMC 2014, LMŠ 2018, GS 2022)  
- Pros: Closer to the specific dynamic: **SDS as stable pole** vs **volatile liberal/centrist vehicle**.  
- Cons: Small N; and our question is a 2026 head-to-head between two established (now) parties, not necessarily a brand-new entrant.

3) **Incumbent governing party vs main opposition party seat difference in Slovenian PR elections**  
- Pros: Captures incumbency advantage/disadvantage and coalition wear.  
- Cons: Still small N and depends on which party is incumbent (here GS) and whether “anti-Janša coordination” reappears.

**Most suitable outside-view anchor:**  
- Start with **(1)** for the *typical magnitude* of top-two seat gaps under Slovenia’s system, then adjust sign/magnitude using **(2)** to reflect that SDS is unusually **stable** while “GS-family” parties historically show higher volatility.

---

### (c) Timeframe analysis

- Today: **2026-03-02**. Election: **2026-03-22**. Roughly **20 days** to election day, with resolution by late March.  
- Historically, Slovenia has seen **late tactical coordination and undecided movement** (notably in narratives around elections like 2018 and 2022). In an outside view, this increases uncertainty: even close-to-election, **non-trivial seat swings** can occur.

---

### (d) Justification (outside view baseline → seat-difference distribution)

**Step 1: Typical top-two seat gaps (magnitude baseline).**  
From the agent report’s top-two gaps since 1992: **+7, +9, +20, +6, +1, +2, +15, +12, +14**.  
- Median is around **+9**; mean roughly **~9–10**.  
So, when two parties are clearly the top two, Slovenia often produces a **high single-digit** seat gap, but with meaningful probability of **very close outcomes** (1–2) and occasional **blowouts** (15–20).

**Step 2: Convert “winner–runner-up gap” to “SDS–GS gap.”**  
- If SDS is ahead: SDS−GS is positive, likely in the **+5 to +12** zone by default.  
- If GS is ahead: SDS−GS becomes negative, likely **−2 to −10** depending on margin.

**Step 3: Structural party-volatility adjustment (GS risk of mean reversion).**  
The “GS slot” (dominant liberal/centrist force) has often been **less stable** than SDS historically; multiple such parties have dropped sharply in subsequent elections. That pushes the outside-view center modestly toward **SDS > GS** (positive SDS−GS), while still allowing for GS resilience and/or anti-SDS tactical consolidation.

**Net outside-view expectation:**  
- Central tendency: **SDS ahead by ~8 seats** (not because of current polls, but because (i) typical top-two gaps are ~9 and (ii) SDS has been structurally stable while the governing “new” centrist bloc historically regresses).  
- Uncertainty: substantial; close result or a GS edge remains plausible.

---

Outside view calibration:

Key calibration choices:
- Use a **wide** 10–90 range because: PR fragmentation + tactical voting + late swings + seat translation nonlinearity around the threshold.
- Allow tails beyond the platform’s ±15.5 “soft” bounds since the bounds are open and historical top-two gaps reached **~20**.

I will center the distribution around **+7 to +9** but keep meaningful mass on negative outcomes.

Outside View Prediction:
Percentile 10: -7  
Percentile 20: -2  
Percentile 40: 4  
Percentile 60: 8  
Percentile 80: 13  
Percentile 90: 18