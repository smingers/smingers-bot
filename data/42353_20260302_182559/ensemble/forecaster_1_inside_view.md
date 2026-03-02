## Analysis

### (a) Source Analysis

**Trading Economics (March 2, 2026):** Shows 10Y yield at 4.06% on March 2, 2026, with a +0.11 pp increase from prior session. Notes geopolitical escalation (US-Iran conflict), energy price surge, and ISM prices gauge at 3-year high. Forecasts 3.95% by end of Q1 2026. Reliable data aggregator; the geopolitical narrative is notable but should be treated cautiously as it may be model-generated text. The 4.06% current level is the most actionable fact.

**Yahoo Finance (Feb 27, 2026):** Shows 10Y yield closed at 3.962% on February 27, down from 4.017% prior close. Broad equity selloff, VIX at 19.86. Reliable market data snapshot. Confirms the yield was in the 3.96-4.02% range in late February before today's move to 4.06%.

**US Treasury (FRED methodology):** Methodological document only. No yield data. Confirms FRED uses 3:30 PM NY Fed prices. High reliability for methodology, zero relevance for yield levels.

**BondSavvy (Dec 10, 2025):** Analyzes December 2025 dot plot. Fed cut to 3.50-3.75% in December 2025. Dot plot shows median of ~1 cut in 2026. Historical data on yield movements. Reliable institutional analysis, but dated (December 2025).

**Investopedia (March 2, 2026):** Confirms Fed cut to 3.50-3.75% range, 2026 dot plot median calls for single quarter-point cut. Three officials projected rate increases in 2026. Useful for understanding Fed policy backdrop. Some editorial inconsistency noted.

**CNBC (December 10, 2025):** Confirms Fed cut 25 bps to 3.5-3.75%, hawkish tone. 9-3 vote. Powell: "well positioned to wait and see." GDP growth for 2026 revised up to 2.3%. Reliable, named source (Jeff Cox/CNBC).

**TD Economics (Feb 13, 2026):** January 2026 CPI came in at 2.4% YoY, slightly below consensus. Core CPI +0.3% m/m. Tariff pass-through expected to firm core goods inflation. Fed expected to remain on hold until at least summer 2026. Named institutional source, high reliability.

**Capital Economics (Feb 3, 2026):** Paywalled preview. Expects global inflation to undershoot consensus. US core inflation expected to ease later in 2026. Moderate reliability (preview only).

**CNBC (Feb 12, 2026):** January CPI preview. Headline expected at 2.5% YoY. Fed funds at 3.5-3.75%. Soft CPI could give Fed room to cut. Reliable preview article.

### (b) Evidence Analysis

**Strong evidence:**
- **Current yield level ~4.05-4.06%** (Trading Economics, Yahoo Finance, multiple sources): This is the anchor for the distribution. Multiple independent sources confirm.
- **Fed on hold until summer 2026** (TD Economics, CNBC Dec 2025, dot plot): The March 18-19 FOMC meeting (within the resolution window) is very likely to result in a hold, not a cut. This reduces the probability of a dramatic yield drop from a surprise cut.
- **Geopolitical escalation (US-Iran)** (Trading Economics): Energy prices surging, ISM prices at 3-year high. This is inflationary and supports higher yields. However, geopolitical risk also drives safe-haven demand for Treasuries (lower yields). Net effect is uncertain but the inflation channel could push yields up.

**Moderate evidence:**
- **Recent downward trend in yields** (Feb 2026): Yields fell from ~4.29% in early Feb to 3.96% by Feb 27, then rebounded to 4.06% today. The trend suggests some downward pressure but the rebound today suggests a floor near 3.96%.
- **Trading Economics forecast of 3.95% by end of Q1**: Single model-based forecast. Directionally consistent with recent trend but uncertain.
- **FOMC March meeting within window**: The March 18-19 FOMC meeting is a significant event. Consensus is for a hold. If hold with hawkish tone, yields could rise slightly; if hold with dovish tone, yields could fall.
- **CPI at 2.4% YoY** (TD Economics): Below consensus, slightly disinflationary. Supports Fed holding or eventually cutting, which is marginally yield-negative.

**Weak evidence:**
- **Capital Economics global inflation undershoot**: Paywalled, limited detail.
- **Fed dot plot from December 2025**: Dated, already priced in.

### (c) Timeframe Analysis

The resolution date is March 27, 2026 (last Friday of the March 16-27 period). From today (March 2, 2026), this is approximately 25 calendar days / ~18 trading days.

**Key events in the window:**
- March 18-19: FOMC meeting (almost certainly a hold, but tone matters)
- Ongoing: Geopolitical developments (US-Iran), tariff impacts, economic data releases

**If timeframe were halved (~9 trading days, resolving ~March 13):** The distribution would be narrower, centered more tightly around current levels (~4.05%), with less event risk (FOMC meeting would not yet have occurred). Standard deviation would shrink to ~12-15 bp.

**If timeframe were doubled (~36 trading days, resolving ~April 17):** Distribution would widen significantly, incorporating more data releases and potentially another FOMC meeting. Standard deviation would expand to ~25-30 bp.

For the actual 18-trading-day window with FOMC in it, I estimate a standard deviation of ~18-22 bp.

### (d) Justification

**Starting point**: ~4.05-4.06% (today, March 2, 2026)

**Factors pulling yields lower:**
- Recent downward trend (Feb decline of ~33 bp)
- Fed expected to hold but eventually cut (dovish bias)
- CPI slightly below consensus (2.4% vs 2.5% expected)
- Safe-haven demand from geopolitical risk (US-Iran)
- Trading Economics model forecasts 3.95% by end of Q1

**Factors pulling yields higher:**
- ISM prices gauge at 3-year high (inflationary)
- Energy price surge from geopolitical conflict
- Fed on hold until summer 2026 (no imminent cuts)
- GDP growth revised up to 2.3% for 2026
- Today's rebound (+11 bp) suggests some upward momentum
- Tariff pass-through expected to firm core goods inflation

**Net assessment**: The factors are roughly balanced, with a slight tilt toward the current level persisting or modest decline. The FOMC meeting (March 18-19) is the key event risk. A hold with hawkish tone could push yields toward 4.10-4.20%; a hold with dovish tone could push yields toward 3.90-4.00%.

The outside view distribution (centered at ~4.05%) seems appropriate. I'll make a modest adjustment:
- Slight downward skew given the recent trend and Trading Economics forecast of 3.95%
- Wider tails given the FOMC event risk and geopolitical uncertainty
- The geopolitical escalation (US-Iran) is a significant wildcard that could move yields sharply in either direction

**Adjusted central tendency**: ~4.00-4.05% (slight downward nudge from recent trend and model forecasts)
**Standard deviation**: ~20 bp (slightly wider than baseline due to FOMC event risk)

---

## Distribution Calibration

Starting from ~4.05% with:
- Slight downward bias (~3-5 bp) from recent trend
- Standard deviation of ~20 bp for 18-trading-day horizon with FOMC event
- Fatter tails due to geopolitical uncertainty and FOMC event risk

The distribution centers around ~4.00-4.05%, with meaningful probability mass from 3.70% to 4.40%.

---

## Checklist

1. **Target variable**: Last available daily 10Y Treasury yield (FRED DGS10) for March 27, 2026 (or last available day in Mar 16-27 period), in percentage points. ✓

2. **Outside view base rate**: Centered at ~4.05%, SD ~20 bp, 10th/90th at ~3.72%/4.38%. My inside view is anchored here with modest adjustments. ✓

3. **Consistency check**: Implied median = ~4.02%; mean = ~4.03%; this is consistent with current level of 4.06% with slight downward bias from recent trend. ✓

4. **Key evidence pieces**:
   - Current yield: 4.05-4.06% (March 2, 2026) — factually confirmed by multiple sources ✓
   - FOMC March 18-19 meeting within window: hold expected, tone uncertain ✓
   - Recent downward trend: 4.29% → 3.96% in Feb, rebounded to 4.06% today ✓
   - Geopolitical risk (US-Iran): inflationary but also safe-haven demand ✓
   - Trading Economics Q1 end forecast: 3.95% (model-based, moderate weight) ✓

5. **Blind spot**: A surprise FOMC cut or major dovish pivot at the March 18-19 meeting could push yields sharply lower (toward 3.70-3.80%). Alternatively, a major inflation surprise or geopolitical escalation causing energy price spike could push yields toward 4.30-4.50%. The geopolitical scenario (US-Iran) is the most likely "surprise" scenario and could push in either direction.

6. **Status quo**: The yield has been in the 3.96-4.10% range for the past week. Status quo suggests it stays near 4.00-4.10%. This is consistent with my central estimate.

7. **Technicalities**: Values strictly increasing ✓; units in % ✓; values within reasonable bounds ✓.

Percentile 10: 3.68
Percentile 20: 3.82
Percentile 40: 3.96
Percentile 60: 4.08
Percentile 80: 4.22
Percentile 90: 4.40