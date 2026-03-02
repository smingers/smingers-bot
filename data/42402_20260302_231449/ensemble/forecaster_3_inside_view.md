Analysis:
**1) Paraphrase / resolution criteria**
Resolve **Yes** if **YUM’s close on 2026-03-14** (pulled via Yahoo Finance API; split-adjusted) is **higher than YUM’s close on 2026-03-03**; otherwise **No**. Window is ~**9 trading days**.

## (a) Source analysis (what each source says + quality)
1) **Programmatic stock return distribution (historical YUM 9-trading-day windows, N=2,504)**  
   - **What it is:** Empirical base rates for “up vs down” over the exact horizon.  
   - **Key facts:** Unconditional **P(up)=57.6%**; mean +0.54%, stdev ~4%. Conditional: after **negative prior 5-day return** P(up)=59.5%; **30-day vol above median** P(up)=59.8%.  
   - **Quality/date:** High quality, directly on-target, computed from historical prices.

2) **SEC Form 4 (StockTitan summary of filing; 2026-03-02)**  
   - **What it is:** KFC Division CEO exercised SARs and sold **287 shares** (~$166) plus small tax-withholding disposal; ended with 0 direct shares, still holds SARs.  
   - **Quality/date:** High reliability (regulatory filing). Interpretation (“routine vs signal”) is opinion; the *facts* are solid.

3) **MarketBeat institutional/analyst roundup (2026-03-02)**  
   - **What it is:** Mentions one institution (DNB) reduced stake heavily in Q3; others increased; analyst consensus “Moderate Buy”, avg PT ~174.5; some recent insider sales totals.  
   - **Quality/date:** Medium reliability for the factual recap; but the institutional trades are stale (Q2/Q3) for a 9-trading-day forecast. Analyst targets are longer-horizon.

4) **PreparedFoods “2026 Food Trends Report” (2026-01-05)**  
   - **What it is:** Brand/consumer trend piece; no market-moving financial info.  
   - **Quality/date:** Fine as background; low relevance to 9-day stock direction.

5) **AskNews: VICE fast-food demand piece (2026-03-02)**  
   - **What it is:** Anecdotal/consumer behavior framing (“too tired to cook”), not YUM-specific.  
   - **Quality/date:** Current, but weak linkage to YUM’s next-two-weeks return.

6) **AskNews: FT-echo style piece on fast-food polarization (2026-02-18, mk.co.kr in Korean)**  
   - **What it is:** Industry headwinds (traffic pressure for low-income consumers; Pizza Hut comps weak historically).  
   - **Quality/date:** Medium; relevant to sector narrative but still not tightly linked to 9-day move.

7) **Macro release calendars (Scotiabank; BLS schedule) + BLS CPI Jan 2026 report**  
   - **What it is:** Identifies **major macro risk dates within the window** (jobs 3/6, CPI 3/11, sentiment 3/13). CPI trend moderate (food away from home +4% YoY; limited service +3.2% YoY).  
   - **Quality/date:** High reliability for dates/facts; relevance is indirect (market-wide volatility shocks).

## (b) Evidence analysis (weighted)
**Strong evidence (anchors the forecast)**
- **Historical YUM 9-trading-day base rate:** **~57.6% up** with mild positive drift. This is the closest reference class to the exact resolution criteria.

**Moderate evidence (small-to-moderate nudges)**
- **Current conditionals from the same dataset:** recent **negative 5-day return** and **above-median vol** modestly increase historical P(up) into ~59–60% territory. This is still noisy, but it’s at least *horizon-matched* evidence.
- **Macro event risk inside the window (jobs/CPI):** raises two-sided uncertainty; not clearly directional, but it reduces confidence that “drift wins” (i.e., fatter tails).

**Weak evidence (tiny nudges)**
- **Insider selling (Form 4):** small, plausibly routine; weak negative signal at best.
- **Institutional holding changes (Q2/Q3) + analyst price targets:** largely irrelevant for a 9-trading-day comparison; targets can provide mild “supportive narrative” but little predictive power at this horizon.
- **Industry trend articles:** mostly broad/qualitative; not a 2-week price driver.

## (c) Timeframe analysis
- Time left: from **2026-03-03 to 2026-03-14** is about **12 calendar days / ~9 trading days**.
- If the horizon were **halved** (~4–5 trading days), I’d pull probability **closer to ~55–57%** (less time for drift/mean reversion; more coin-flippy).
- If the horizon were **doubled** (~18 trading days), I’d push it **up modestly to ~60–63%** (more time for equity drift / fundamentals to matter).

## (d) Justification (inside view adjustment from outside view)
**Outside view base rate provided:** **58.5%**.

Adjustments:
- **+1.0 pp**: The same historical dataset says the *current* setup (recent short-term weakness; higher realized vol) has slightly higher subsequent “up” frequency than unconditional. This supports mild mean reversion / bounce odds.
- **-0.5 pp**: Clustered macro releases (employment + CPI) inside the window add event risk that can overwhelm small drift; not directional, but historically can slightly reduce “up” frequency when uncertainty is elevated (especially if equities are jittery).
- **-0.0 to -0.5 pp**: Insider sale is small and plausibly mechanical; I treat it as near-zero.

Net: approximately **flat to slightly up** vs 58.5%. I’ll land at **59%** rather than making a bigger move, because the dominant reality for 2-week single-name direction remains **near-random walk with a small positive drift**.

Probability calibration
- **Status quo / drift view:** In the absence of company-specific surprises, YUM has a modest upward drift over 9 trading days; base rates imply “up” happens a bit more often than “down.”
- **Yes scenario (how it happens):** market stabilizes or rebounds; defensives/QSR hold up; YUM recovers part of the recent dip; no bad idiosyncratic news.
- **No scenario (how it happens):** a risk-off macro surprise (jobs/CPI) hits equities; or a YUM/restaurant-sector specific negative headline appears; or the recent weakness continues another leg down.
- **Sensitivity to ±10%:** Moving to ~69% would require strong, near-term catalysts (earnings, guidance, takeover, major litigation)—not present. Moving to ~49% would require a clear negative catalyst or strongly bearish market regime—also not evidenced.

Checklist:
1) **Criteria:** Yes if **Close(2026-03-14) > Close(2026-03-03)** for YUM (Yahoo Finance close; split-adjusted).  
2) **Outside view base rate:** **58.5%** (given).  
3) **Consistency line:** **59 out of 100 times**, YUM’s 2026-03-14 close is higher than its 2026-03-03 close.  
4) **Top evidence (most important, <20 words each):**
   - YUM historical 9-day windows: **P(up)=57.6%** (N=2,504).  
   - Current conditionals: **recent 5-day down + above-median vol → slightly higher P(up)** historically.  
   - Major macro releases inside window (jobs/CPI) increase tail risk; no clear direction.  
5) **Blind spot:** A sharp, market-wide selloff on CPI/jobs (or sudden YUM-specific headline) could dominate drift and flip odds.  
6) **Status quo outcome:** Slight upward drift/mean reversion after a dip is more common than continued decline, but only modestly.

Probability: 59%