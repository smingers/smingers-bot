Analysis:
Target: Total number of passengers screened by TSA at US checkpoints from Monday Feb 9, 2026 through Sunday Feb 15, 2026 (units: passengers).

(a) Source analysis (quality, date, what’s fact vs opinion)
- TSA passenger volumes page (tsa.gov, accessed contextually as of Feb 15, 2026): Primary source. Provides factual daily passenger screening counts. We have actuals for Feb 9–12 totaling 9,014,806. Missing Feb 13–15 as of forecast time.
- Google Sheets compilation of TSA data (via provided spreadsheet link, latest ~Feb 8, 2026): Secondary compilation of TSA data. Likely accurate but still secondhand; useful for recent-trend baselines (weekly totals/rolling averages), less for exact resolution.
- AInvest commentary (Feb 2026): Tertiary market commentary. Facts (record day references) may be right, but most is narrative/opinion (“new normal”) without methodology.
- CNN (Jan 28, 2026) on shutdown risk + TSA staffing: Generally reliable for factual shutdown status/contingency-plan statements; moderate relevance. Some impact statements are speculative.
- AP/CNBC-style shutdown coverage (Feb 13–15, 2026 via multiple outlets listed): The core facts are consistent across outlets—DHS shutdown starting ~Feb 14, TSA working without pay. Operational impact language (“could cause delays”) is partly expert opinion; still relevant for short-run throughput risk.
- Papersplease advocacy site (Jan 29, 2026): Strong viewpoint/advocacy; claims about enforcement and legality are largely opinion. Useful only as weak signal of possible friction; not relied upon for quantification.
- Port of Seattle Presidents’ Day travel note (regional): Credible for SEA, but not nationally representative; provides weak-to-moderate context on holiday uplift, not a direct national total.

(b) Evidence analysis (weighted)
Strong evidence
- TSA.gov partial-week actuals: Feb 9–12 = 9,014,806 (hard constraint; dominates forecast because only 3 days remain unknown).
- Strong day-to-day seasonality / weekday-weekend patterns in TSA volumes (structural, historically predictive), though exact mapping this week is uncertain without the missing days.

Moderate evidence
- Multiple reliable outlets confirming DHS/TSA shutdown beginning Feb 14 and TSA agents unpaid (credible mechanism for increased absenteeism/reduced throughput, but magnitude over the first 1–2 days is uncertain).
- Recent weeks in the spreadsheet showing elevated weekly totals and continued growth (momentum indicator; not determinative for this specific 7-day window but directionally supportive of higher totals).

Weak evidence
- REAL ID enforcement/fees and advocacy reporting: could create marginal friction, but any effect should already be partly visible in early-Feb actuals.
- Investor/market commentary (AInvest, TravelAndTourWorld): suggests heightened attention, but little measurable forecasting content.

(c) Timeframe analysis
- Resolution window is essentially “now”: the week Feb 9–15, 2026, with outcome known once TSA posts Feb 13–15 and we sum the week. We are forecasting the remaining 3 days’ totals.
- If the timeframe were halved (only ~1–2 unknown days left), uncertainty would shrink materially because most of the week would be observed.
- If doubled (two-week total), uncertainty would rise again because shutdown impacts could compound over time (absenteeism tends to grow with duration), and holiday effects (Presidents’ Day on Feb 16) would enter.

(d) Justification (inside-view adjustment from outside-view)
Outside-view base-rate distribution (given): P10 14,500,000; P20 15,000,000; P40 15,600,000; P60 16,000,000; P80 16,400,000; P90 16,800,000.

Key inside-view update: we now have a hard partial total (Feb 9–12 = 9,014,806). So the forecast reduces to estimating Fri–Sun (Feb 13–15).
- Trend-continue/status quo: Recent TSA daily levels implied by the observed four days are high (avg ~2.254M/day), and Thu Feb 12 is especially high (2.702M), which pulls expectations for Fri–Sun upward versus a “mid-Feb normal week.”
- Presidents’ Day timing nuance: Because Presidents’ Day is Mon Feb 16 (not in-week), some “return” travel can shift from Sun to Mon, slightly damping Sun Feb 15 versus a typical weekend-return Sunday. This is a mild downward adjustment to the outside-view’s higher-end weekend boost.
- Shutdown starting Feb 14: credible risk of delays/absences, but historically the largest throughput hits tend to accumulate as unpaid periods drag on. For Feb 14–15 specifically, I model a small negative effect (more variance than mean shift): some missed flights / longer lines could reduce screened counts modestly, but many travelers still attempt travel and get screened (possibly later), so net effect over 1–2 days is likely limited.

Net effect versus outside view:
- Slightly higher central estimate (because the observed 4-day subtotal is already strong), but
- Keep tails wide and slightly fatter on the downside due to shutdown uncertainty concentrated in the final two days.

Distribution calibration
Let Total = 9,014,806 (known) + X, where X is Feb 13–15 total.
- A plausible “normal-high” weekend for X is ~6.8M–7.6M.
- Downside (shutdown disruptions + some travelers deferring/canceling + weather as an unknown unknown) could push X closer to ~5.8M–6.3M.
- Upside (minimal disruption + strong holiday/weekend demand) could push X ~7.9M–8.2M.

This yields a central tendency around ~16.1M, with meaningful spread.

Checklist:
1) Target variable: TSA screened passengers, Feb 9–15, 2026 inclusive, total passengers.
2) Outside view base distribution: (14.5, 15.0, 15.6, 16.0, 16.4, 16.8) million.
3) Consistency: implied median ≈ 16,100,000; mean ≈ 16,150,000; consistent with strong observed first 4 days and moderate weekend uncertainty.
4) Most significant evidence:
   - TSA.gov actuals Feb 9–12 sum to 9,014,806.
   - Recent TSA levels are elevated (recent-week momentum).
   - Presidents’ Day on Feb 16 may shift some return travel off Sun Feb 15.
   - DHS/TSA shutdown begins ~Feb 14 raises variance/downside risk for Feb 14–15 throughput.
5) Blind spot: A sharp, immediate spike in TSA sick-outs or a major storm could crater Feb 14–15 totals (push outcome down).
6) Status quo: Absent major disruption, volumes remain high; keep center near recent realized pace.
7) Technicalities: strictly increasing percentiles; units passengers; values can exceed stated bounds (open), but kept within a plausible range.

Percentile 10: 14800000
Percentile 20: 15300000
Percentile 40: 15900000
Percentile 60: 16300000
Percentile 80: 16700000
Percentile 90: 17150000