Analysis:
**Target variable (resolution criteria):** Total **TSA checkpoint passengers screened** in the **7-day period Mon Feb 16, 2026 through Sun Feb 22, 2026**, in **passengers**.

### (a) Source analysis (quality, date, facts vs opinions)
- **TSA passenger volumes page (tsa.gov)** *(implied/authoritative resolution source; current through mid-Feb)*: Highest-quality official daily counts. No speculation; this is what will resolve the question.
- **Google spreadsheet of historical TSA weekly totals** *(high quality if faithfully transcribed)*: Useful for week-over-week/YoY context and volatility; secondary compilation (possible transcription error risk).
- **AInvest commentary (Feb 2026)**: Mostly narrative framing/opinion (“new normal”); factual claim about a record day is plausible but not the resolution source. Treat as weak signal on trend persistence.
- **Polymarket market for Feb 22 single-day volume**: Potentially informative but **thin liquidity** (very low volume) and it’s **one day not the week**; treat as weak-to-moderate at best for the **Sunday** level.
- **Travel Radar (Dec 2025) TSA holiday projection**: Some attributed statements; pertains to holiday peak, not late-Feb baseline. Moderate relevance for “system capacity/demand is high,” but timing mismatch.
- **Weather disruption articles (Feb 12–15, 2026; NBC Bay Area / KQED / TravelAndTourWorld)**: Credible for **localized** disruption risk around Presidents’ Day weekend, especially Northern CA. Facts: storm timing and disruption; effect on *national* weekly total is uncertain.
- **Government shutdown / TSA unpaid work articles (Feb 13–14, 2026; CNBC/AP syndication via Boston Globe/Univision; SimpleFlying; TravelAndTourWorld)**:
  - **High-quality core fact** (CNBC/AP-level): DHS funding lapse → TSA working without pay; historical precedent of sick-outs/lines in prior shutdowns.
  - **More sensational pieces** (TravelAndTourWorld): plausible but tends to exaggerate; treat mainly as color, not quantified evidence.

### (b) Evidence analysis (weighted)
**Strong evidence**
- **Seasonality + reference week totals (2024/2025)**: This specific week historically ~**16.7M** passengers; week-level volumes are usually stable absent major nationwide shocks.

**Moderate evidence**
- **Current DHS shutdown affecting TSA pay** (multiple credible outlets): Mechanism exists for reduced throughput (call-outs → fewer open lanes → missed flights/cancellations). Likely *some* negative impact, but magnitude in the **first 1–2 weeks** of a shutdown is uncertain.
- **Early-Feb 2026 YoY growth reported in the compiled data**: Suggests upside pressure vs 2025 baseline, though may be distorted by calendar/weather and not persist into this exact week.

**Weak evidence**
- **Polymarket Feb 22 single-day**: Thin market; still mildly suggests Sunday could be relatively high (2.6M+), but can’t scale reliably to a full week.
- **Northern CA storm**: Real disruptions but geographically limited; national weekly impact likely small unless cascading delays propagate widely.

### (c) Timeframe analysis
- **Forecast horizon:** The window starts **tomorrow (Feb 16)** and ends in **7 days**; outcome known shortly after **Feb 22**.
- **If timeframe were halved (3–4 days):** uncertainty would shrink somewhat (less exposure to compounding disruptions), but single-day weather/ops variance would matter more.
- **If timeframe were doubled (14 days):** uncertainty would grow meaningfully because shutdown dynamics (fatigue, sick-outs) can **worsen over time**, and additional weather systems could appear.

### (d) Justification: inside-view adjustments to the outside view
**Outside view base-rate distribution (given):**
- P10 16.2M; P20 16.6M; P40 17.0M; P60 17.3M; P80 17.7M; P90 18.0M.

**Adjustments:**
1. **Shutdown risk (downward shift + wider tails):** With TSA unpaid starting Feb 14 and likely persisting into this week, I expect *some* reduction in screenings vs a no-shutdown counterfactual (throughput constraints, missed flights, airlines padding schedules). I’m not assuming a collapse (FAA funded; effects often worsen later), but enough to nudge the median down and fatten the left tail.
2. **Presidents’ Day week inclusion (mixed):** Having the holiday Monday *inside* the week can support demand, but storm + shutdown may offset; net effect near-neutral to slightly positive on demand, slightly negative on realized screenings.
3. **Storm (small net down):** Likely reduces realized screenings modestly (cancellations), with some spillover rebookings later in the week.

Net: **small downward shift from the outside-view median** and **slightly increased uncertainty**, especially on the downside.

Distribution calibration:
- I center the week around roughly **~17.0M** (vs outside-view ~17.15M median-ish), reflecting modest disruption drag.
- I widen the lower tail more than the upper tail: shutdown escalation + weather can knock totals down faster than upside surprises can push them up.
- **Implied median (between P40 & P60) ≈ 17.0M; mean ≈ 17.05M** (slight right-skew capped by capacity).

Checklist:
1) **Paraphrase:** Total TSA-screened passengers **Feb 16–Feb 22, 2026** (7 days), **passengers**.  
2) **Outside view used:** (16.2, 16.6, 17.0, 17.3, 17.7, 18.0) million at 10/20/40/60/80/90.  
3) **Consistency:** Implied median ≈ 17000000; mean ≈ 17050000; consistent with modest negative disruption + holiday demand.  
4) **Key evidence (3–5):**
   - Same-week totals in 2024/2025 near **16.7M** (stable baseline).
   - **DHS shutdown → TSA unpaid** (credible multi-source) → higher absenteeism risk.
   - **Localized major CA winter storm** around the start of the window → cancellations/delays.
   - Early Feb 2026 showed **strong YoY** (moderate upside pressure but uncertain persistence).
5) **Blind spot:** A rapid shutdown resolution (or minimal sick-outs) + strong demand could push totals **up** toward 17.8–18.2M.  
6) **Status quo:** Week-level TSA totals typically move slowly; I kept the shift modest.  
7) **Technicalities:** Strictly increasing percentiles; units passengers; values plausible vs bounds.

Percentile 10: 15900000
Percentile 20: 16300000
Percentile 40: 16800000
Percentile 60: 17200000
Percentile 80: 17700000
Percentile 90: 18100000