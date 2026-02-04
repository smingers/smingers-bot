# Forecasting Analysis: 2026 WBC Knockout Stage Total Runs

## Target Variable
Total runs scored across all 2026 WBC knockout games (4 quarterfinals + 2 semifinals + 1 final = 7 games), March 13-17, 2026.

## (a) Source Analysis

**Historical Context Sources:**
1. **Agent Report (Feb 2026)** - High quality. Provides complete knockout scoring data from all five previous WBCs (2006-2023), traceable to MLB.com. Key facts: 2023 had 76 runs in 7 games (10.9 rpg); three-game formats averaged 22 runs (range 12-33).

**Current News Sources (AskNews):**
2. **Multiple roster announcements (Feb 2-4, 2026)** - High quality, factual. Japan finalizes 30-man roster with Yoshida; Dominican Republic confirms Juan Soto; USA roster features Judge, Skubal, Skenes. These are verifiable roster commitments, not speculation.

3. **Puerto Rico insurance crisis (Feb 2, 2026, The Athletic)** - High quality, concerning. Francisco Lindor, Carlos Correa, and 8-10 other Puerto Rican players may withdraw due to insurance denials. This is factual reporting with named sources.

4. **Strategic analysis articles (Feb 4, 2026, Asian sources)** - Moderate quality. South Korea's "avoid Japan, target Taiwan" strategy and tactical predictions. Mix of factual scheduling info and expert opinion from former player Kang Jung-ho.

5. **Tournament structure confirmations (multiple sources)** - High quality, factual. Confirms 7-game knockout format identical to 2023, venues in Houston and Miami.

## (b) Evidence Analysis

**Strong Evidence:**
- **Format consistency**: 7-game knockout structure confirmed (4 QF + 2 SF + 1 F), identical to 2023 which produced 76 runs. This is the most directly relevant reference class.
- **Elite roster quality**: Multiple independent sources confirm top MLB talent participating (Ohtani, Judge, Soto, Skubal, Skenes). Dominican Republic fielding $2.2B roster. High talent = higher run scoring historically.

**Moderate Evidence:**
- **Puerto Rico roster crisis**: 8-10 potential withdrawals from one team. Effect: Puerto Rico was a Pool A contender; weakened roster reduces their advancement probability. If they don't reach knockouts, replaced by potentially lower-scoring team. Modest downward pressure (−2 to −4 runs across tournament).
- **Pitching depth concerns**: South Korea's Kang Jung-ho notes bullpen concerns under 65-pitch limits. Several teams may have thinner pitching than desired, suggesting slightly elevated scoring.
- **2023 scoring context**: The 10.9 rpg in 2023 knockouts was ~20% above typical MLB scoring and represented the highest WBC knockout average in history. Regression toward mean is plausible.

**Weak Evidence:**
- **Individual player narratives**: Yoshida's 2023 heroics, Kershaw joking about avoiding Ohtani. Anecdotal; minimal predictive value.
- **"Dark horse" speculation**: Media predictions about Mexico, Venezuela as contenders. Opinions without clear methodology.

## (c) Timeframe Analysis

**Prediction window**: 39 days until first knockout game (March 13), 43 days until final (March 17).

**If timeframe halved** (knockouts in ~20 days): No material change. Rosters are essentially locked (due Feb 5), and tactical adjustments occur during pool play regardless of calendar time.

**If timeframe doubled** (knockouts in ~80 days): Slight downward adjustment. More time for injuries during pool play; increased roster uncertainty. Would widen confidence intervals by ~10%.

## (d) Justification & Base Rate Adjustment

**Outside View Anchor**: 74 runs (mean), 55-95 (90% range)

**Key Adjustments:**

1. **Puerto Rico insurance crisis** (−3 runs): If Puerto Rico advances with weakened roster, they'll likely score fewer runs and allow more in knockout games. If they fail to advance, replacement team (likely Panama or Colombia) may produce similar total. Net effect: modest downward pressure.

2. **Elite talent concentration** (+2 runs): Dominican Republic's unprecedented roster depth, USA's Cy Young duo, Japan's full MLB contingent suggest slightly higher offensive firepower than 2023 average. However, defensive quality also rises, partially offsetting.

3. **Regression consideration** (−2 runs): 2023's 10.9 rpg was historically high. Some regression toward the 8-10 rpg range seen in earlier editions is reasonable, though modern MLB scoring environment (~9.0 rpg in 2024-25) supports elevated WBC scoring.

4. **Format stability** (neutral): Identical 7-game structure to 2023 removes format uncertainty.

**Net adjustment**: −3 runs from anchor → revised mean ≈ 71 runs

**Uncertainty assessment**: 
- Historical SD of ~12 runs per 7-game tournament remains appropriate
- Puerto Rico situation adds ~2 runs of extra variance
- Revised SD ≈ 13 runs
- 90% range: 71 ± 1.6(13) ≈ 50-92 runs

## Consistency Check
Implied median ≈ 71, mean ≈ 71. Reasonable given 2023 produced 76 with similar format, adjusted down for Puerto Rico crisis and mild regression.

## Key Evidence Summary
1. 2023 knockout stage: 76 runs in 7 games (10.9 rpg) - most relevant reference
2. Puerto Rico may lose 8-10 players to insurance issues - factual, modest downward impact
3. Elite rosters confirmed (Soto, Judge, Ohtani, etc.) - supports high-scoring environment
4. Identical 7-game format to 2023 - removes structural uncertainty
5. Modern MLB scoring ~9.0 rpg supports elevated WBC rates

## Blind Spot
**Most likely scenario to make forecast look silly**: Dominican Republic and USA both advance and produce an offensive explosion in semifinals/final (combined 35+ runs in 3 games), pushing total above 95. This would occur if elite hitting overwhelms even quality pitching under pitch-count constraints. Direction: **upward**.

## Final Calibration

Starting from adjusted mean of 71 runs with SD of 13:
- 10th percentile: 71 - 1.28(13) ≈ 54
- 20th percentile: 71 - 0.84(13) ≈ 60  
- 40th percentile: 71 - 0.25(13) ≈ 68
- 60th percentile: 71 + 0.25(13) ≈ 74
- 80th percentile: 71 + 0.84(13) ≈ 82
- 90th percentile: 71 + 1.28(13) ≈ 88

Rounding and ensuring monotonicity while respecting tail uncertainty:

**Percentile 10: 54**
**Percentile 20: 60**
**Percentile 40: 68**
**Percentile 60: 74**
**Percentile 80: 82**
**Percentile 90: 88**