Analysis:
**1) Target variable / resolution criteria (paraphrase)**  
Statewide voter turnout (“Wahlbeteiligung”) in **%** for Bavaria’s **Kommunalwahlen on March 8, 2026**, as published by the **Bayerisches Landesamt für Statistik** on its Kommunalwahlen page **before May 1, 2026**.

## (a) Source analysis (what each says; quality/date; fact vs opinion)

**Official / high-quality**
- **Bayerisches Landesamt für Statistik press release (Jan 2026)**: states ~**10.05m eligible voters**, ~**700k first-time local-election voters**, eligibility rules. **No turnout forecast**. *High reliability; factual; current.*  
- **Outside-view historical series referenced in prompt** (incl. 2002/2008/2014/2020 turnout; and 2020 = ~58.7–58.8%): treated as official/compiled from official. *High reliability; directly predictive via base rates.*

**Reputable media / high-quality**
- **BR24 (Aug 8, 2025) on shortened mail-voting timeline**: factual rule change: ballots may be sent **20 days** before (from **Feb 16, 2026**) vs **34 days** previously. Includes quotes: Greens claim suppression (opinion); Cities association warns about logistics (expert stakeholder); **Stefan Merz (Infratest dimap)** says no disadvantage but voters react to framework changes (expert opinion). *High quality; relevant mechanism; mixed directional signal.*
- **N-tv / Zeit Online (Jan 5, 2026) poll**: survey shows **49% “definitely vote”, 24% “probably”**; article notes “based on past turnout” expected ~**59%** (interpretive statement, but anchored to 2020). *Moderate quality for turnout (self-report overstates); still informative.*

**Local reporting / medium quality but useful as ground truth indicators**
- **Augsburger Allgemeine (Feb 14, 2026) Landkreis Augsburg explainer**: reports **2020 turnout ~60%** in that district and describes voting process; notes mail ballots start Feb 16 and advises drop-off due to postal delays. *Good local factual detail; not statewide.*
- **Merkur.de (Feb 13, 2026) “Briefwahl-Ansturm”**: reports **high demand for postal voting** (e.g., ~quarter of eligible in some towns already requested) and mentions **ballot delivery delays** in some places; emphasizes receipt deadline. *Anecdotal but timely; indicates mobilization + logistical risk.*
- **Passauer Neue Presse (Feb 14, 2026) Pocking**: administrative readiness; how to apply starting Feb 16. *Neutral; weak direct inference about turnout.*
- **Augsburger Allgemeine (Feb 13, 2026) Donau-Ries/Harburg**: very high early postal requests (Harburg ~2,000 of 4,450 eligible); notes some polling-station consolidation plus transport offer. *Anecdotal; could cut either way (convenience vs friction).*

**Advocacy / low predictive value**
- **Handelsverband Bayern (Feb 6, 2026)** and **DGB Regensburg (Jan 8, 2026)**: calls for high turnout. *Advocacy; no quant data; weak.*

**Other context**
- **Süddeutsche Zeitung (Jan 5, 2026) youth engagement**: states 2020 turnout in Upper Bavaria **56.7%** (regional) and stresses local turnout lower than federal. *Useful as regional anchor; not statewide.*
- **WELT (Feb 13, 2026) attack on candidate**: isolated intimidation incident. *Could marginally affect engagement; hard to generalize; weak for statewide turnout.*

## (b) Evidence analysis (weighted)

**Strong evidence**
1. **Historical Bavaria Kommunalwahl turnout is stable-ish around high-50s/low-60s**, with last observed **~58.7–58.8% (2020)**. This is the best direct predictor (structural, repeated cycles).

**Moderate evidence**
2. **Rule change shortening the mail-voting window (34 → 20 days)** (BR24): plausible to **reduce** turnout slightly at the margin (less time, more deadline misses), especially if many rely on mail voting. Counterpoint from an elections researcher: may be feasible without disadvantages, but even he notes behavior reacts to rules. Net: **small downward pressure** with uncertainty.
3. **Polling on intention (49% definitely, 24% probably)** (N-tv/Zeit): typically **overstates** actual turnout, but the article’s “around 59%” expectation is consistent with the 2020 anchor. Net: **supports status quo ~59%**.

**Weak evidence (small nudges; mostly about variance/tails)**
4. **Reports of very high postal-vote demand** (Merkur, Augsburger Allgemeine, PNP): suggests engagement and adaptation, which could **offset** the shorter window; but also highlights **logistical delays** that could create localized drop-off. Net: **raise uncertainty** more than the mean.
5. **Many open local races in some districts** (Augsburger Allgemeine Augsburg-Land) could lift local turnout, but statewide effect unclear. Net: slight upward possibility.

## (c) Timeframe analysis
- **Time remaining:** ~**22 days** (Feb 14 → Mar 8, 2026).  
- If the window were **halved (~11 days)**: I’d expect **less** movement in the median (administrative facts mostly set), but I might **tighten** slightly if logistics look smooth, or **widen** if postal delays worsen.  
- If the window were **doubled (~44 days)**: I’d keep a similar central estimate but **widen** tails (more time for shocks: weather on election day, administrative disruptions, major scandals).

## (d) Justification: adjusting the outside-view base rate to an inside view
**Outside view anchor:** Bavaria Kommunalwahlen turnout has recently clustered near **~59%**, with 2020 at **~58.8%**.

**Net inside-view adjustments**
- **Downward nudge to the center (small):** the **shorter mail-voting dispatch window** plus reported **ballot delivery delays** create mild turnout friction risk (especially lost/late mail ballots). I treat this as a **0.2–0.5 pp** downward pull on the median versus a naïve “repeat 2020”.
- **Offsetting upward nudge (small):** multiple reports of **high briefwahl demand** indicate many voters are engaged early and may compensate via drop-off at town halls (explicitly recommended). This pushes against a large drop.
- **Uncertainty increases (tails widen slightly):** because a small administrative/logistics issue can shift turnout by ~1 pp statewide (missed deadlines), I widen the lower tail a bit relative to outside view.

So I end up **very close to the 2020-like baseline**, with a **slightly lower median** and **slightly wider** 10–90 range.

Distribution calibration
- **Outside view distribution (given):** P10 55.5, P20 57.0, P40 58.5, P60 60.0, P80 61.5, P90 63.0.
- **Inside view changes:** small downward shift in central quantiles; widen tails modestly (especially lower tail) due to mail/administration timing risk, while keeping an upper tail that allows for mobilization/polarization effects.

Checklist:
1. **Target variable:** statewide **turnout %** for Bavaria Kommunalwahlen **Mar 8, 2026**, as published by **Bavarian statistical office** before **May 1, 2026**.  
2. **Outside view base rate distribution:** (55.5, 57.0, 58.5, 60.0, 61.5, 63.0).  
3. **Consistency check:** implied median ≈ **59.0**; mean ≈ **59.2**; consistent with “near-2020 with slight downside risk.”  
4. **Key evidence (3–5):**
   - 2020 statewide turnout ≈ **58.8%** (strong anchor).
   - Mail-voting dispatch window shortened **34 → 20 days** (possible friction).
   - Poll: **49% definitely + 24% probably** vote; media expects ~**59%** (intent supports status quo).
   - Multiple districts report **high briefwahl demand** (engagement; may offset friction).
5. **Blind spot scenario:** major **statewide postal/logistics failure or severe election-day weather** drives turnout **materially down** (e.g., ~55–56%).  
6. **Status quo outcome:** repeat near **~59%** remains most likely.  
7. **Technicalities:** percentiles strictly increasing; units in **%**.

Percentile 10: 54.8  
Percentile 20: 56.4  
Percentile 40: 58.1  
Percentile 60: 59.7  
Percentile 80: 61.6  
Percentile 90: 63.6