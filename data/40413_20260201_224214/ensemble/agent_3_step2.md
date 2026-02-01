Analysis:
Target variable: Republican seats minus Democratic seats in the US House after the November 2026 election (units: seats; positive = GOP majority, negative = Democratic majority).

(a) Source analysis (facts vs opinions; quality/date)
1) Ballotpedia (2026 House elections page; accessed via provided summary; updated through Jan 31 2026)
- Facts: current House is roughly a very narrow GOP majority; Democrats need a net of 3 seats for control; identifies crossover districts (Trump-won/D-held and Harris-won/R-held); reports 49 incumbent departures (21 D, 28 R); notes 6 states with map changes (CA, MO, NC, TX, OH, UT); tracks 42 battleground seats.
- Quality: good descriptive election almanac; generally reliable for counts/lists. Less useful for causal inference.

2) Cook Political Report ratings table via 270toWin (dated Jan 15 2026)
- Facts: a district-by-district rating snapshot and a list of rating changes; indicates a limited battlefield and enumerates some notable retirements/open seats.
- Quality: high for “what Cook rated”; medium for forward-looking inference because ratings this early can drift, and “consensus forecast” numbers in the table are not a probabilistic model.

3) G. Elliott Morris article (Feb 1 2026)
- Facts: reports Fox News generic ballot D+6 (52-46) and other polling averages; reports Trump net approval around -18 (YouGov/Economist) and generic ballot average about D+4.5.
- Opinion/analysis: “wave territory,” and notes early generic ballot is not strongly predictive; also claims out-party often gains ~5 points between now and November (directionally plausible historically, but not a law).
- Quality: good, data-driven journalism; still one analyst’s framing.

4) CNN/SSRS poll article (Jan 18 2026)
- Facts: indicates Democrats lead generic ballot; highlights independent approval of Trump (very low); motivation asymmetry (Dem base highly motivated) and bleak mood.
- Opinion: interpretive language about motivation and what it implies.
- Quality: high for polling snapshot; medium for translating sentiment into seats.

5) Emerson poll (Jan 22 2026)
- Facts: generic ballot D+6 (48-42); Trump approval 43/51; “wrong track” 56.
- Quality: medium-high; online panel methodology is standard but varies across houses.

6) Asknews / news articles (mostly Jan-Feb 2026)
- Texas TX-18 special election (Feb 1 2026): Fact that a Democrat won a safe-D seat, narrowing the sitting GOP margin (expected result). Quality: high for the outcome; low signal about November because the district is overwhelmingly Democratic.
- Texas state senate upset near Dallas (Feb 1 2026): Fact of a notable special election result in a normally red seat; could indicate enthusiasm/turnout composition. Quality: medium as a political signal; special elections are noisy.
- NPR redistricting piece (Dec 8 2025): Fact pattern that multiple states are redrawing; cites estimates of net seat shifts from mapping battles and notes VRA/legal uncertainty. Quality: high.
- The Hill/Newsweek/opinion and politician statements (Pelosi, party strategists): mostly opinion. Quality: low as forecasting evidence; can be used only as “what actors claim.”

(b) Evidence analysis (weighted)
Strong evidence (large shifts)
1) Midterm structural penalty against the president’s party, especially with low approval.
- Multiple independent sources show Trump approval underwater (YouGov/Economist, Emerson, CNN reporting). In modern midterms, presidential approval is one of the best “fundamentals” predictors of House swings.

2) Generic ballot advantage for Democrats in multiple reputable polls/averages (D+4 to D+6).
- Fox, Emerson, and referenced averages broadly align on a meaningful Dem edge. Translating votes to seats is noisy, but direction is clear.

3) Map/redistricting structure constraining the battlefield.
- Ballotpedia + NPR: multiple states changing maps; gerrymandering/line-drawing can both blunt a wave and also create discrete step-changes (a few seats) independent of national mood.

Moderate evidence (moderate shifts)
4) Incumbent retirements/open seats (Ballotpedia: 49 total; more Rs leaving than Ds).
- Open seats tend to be more flippable and expose the majority party if their seats are marginal. The direction mildly favors Democrats, but the magnitude depends on which districts.

5) Special-election overperformance narratives.
- TX-18 is not informative (safe-D). The Texas state senate upset is more informative but still a single datapoint with turnout quirks; I treat it as modest evidence of Democratic enthusiasm tailwinds.

Weak evidence (small adjustments)
6) Registration edge anecdotes (e.g., NC GOP registrations up).
- Registration ≠ turnout; unaffiliated share is large; district lines and candidate quality dominate.

7) Pure punditry (“blue wave unlikely,” “wake-up call,” Pelosi confidence).
- Useful only to generate hypotheses, not to move numbers much.

(c) Timeframe analysis
- Time to Election Day: about 9 months (Feb 1 2026 → Nov 3 2026). Time to resolution: about 10 months (to Dec 1 2026).
- If timeframe were halved (to ~4.5 months out, mid-June 2026): I’d expect less room for macro conditions to swing; I would narrow the distribution somewhat and lean more on the then-current generic ballot and finalized maps.
- If timeframe were doubled (as if we were 18 months out): I’d widen the distribution considerably and regress more heavily to a base rate of “modest loss for president’s party” rather than today’s polling.

(d) Justification: updating the outside view to an inside view
Outside-view anchor (from the prompt’s baseline reasoning):
- The provided outside view centered around Republicans ending around -10 (i.e., Democrats +10 seats relative to Republicans), with a wide interval reflecting midterm volatility and map uncertainty.

Inside-view adjustments using current (Feb 1 2026) conditions:
1) Fundamentals/polls push toward Democratic control, but not necessarily a 2018-size blowout.
- Multiple polls show Democrats ahead on the generic ballot by ~4-6 points and Trump approval notably underwater. That combination typically implies Democratic gains sufficient to flip a narrow GOP House.
- However, compared to 2018, the seat map is more efficiently gerrymandered, limiting the number of true swing districts. Cook’s early ratings also suggest a constrained toss-up universe (not dozens upon dozens).

2) Redistricting is the main “offset” that keeps me from forecasting a very large Democratic margin.
- With several states changing maps (and at least some GOP-leaning redraws), the same national vote may yield fewer seat flips than historical averages. I treat this as a meaningful dampener (a few seats) rather than a total override of national fundamentals.

3) Status quo if “nothing changes” still likely produces a GOP loss.
- Starting from a razor-thin GOP edge in the sitting House, even a modest national swing against the president’s party is usually enough for Democrats to end with a small-to-mid majority.

Net effect:
- Relative to the prompt’s outside-view median around R-10, I make a small upward adjustment (toward Republicans) because I expect the combination of constrained battlegrounds + map effects to cap the seat swing somewhat, even if Democrats win the national vote.
- But I keep the mean/median clearly negative (Dem House), because (i) the generic ballot is consistently pro-D and (ii) Trump approval is substantially underwater this far out.

Probability calibration:
1) Convert “environment” to seats (rough, intentionally):
- A D+4 to D+6 generic ballot environment often corresponds to something like a mid-to-high single digit or low double-digit Democratic seat gain in a polarized/gerrymandered era (smaller than older “wave” translations).
- With Republicans starting near a low single-digit seat edge, that implies Democrats end up ahead by roughly 5-15 seats in the central mass of outcomes (i.e., Republican advantage around -5 to -15).

2) Scenario decomposition (what produces Yes/No-style outcomes for GOP advantage):
- GOP ends with an advantage (positive): requires either (i) Trump approval recovery + improved economy/security salience, (ii) a favorable map/seat efficiency outcome in key states, and/or (iii) Democratic underperformance in turnout/candidate quality in the limited number of battleground seats.
- Democrats end with an advantage (negative): requires merely a “normal” midterm penalty against a weakly approved president, plus holding their own seats; does not require a massive wave given the narrow current margin.

3) Tail risks (why interval stays wide):
- Legal and late-cycle map changes, a major international/economic shock, or a sharp approval reversal could swing outcomes by 10+ seats versus expectations, especially because control hinges on a small number of districts.

Checklist:
1) Variable check: GOP seats minus Democratic seats in the House after the 2026 election, in seats.
2) Outside view base rate: prompt’s baseline centered near R-10 with wide tails (midterm penalty + modest D advantage).
3) Consistency check: implied median ≈ -8; mean ≈ -7; consistent with “Democrats favored but maps cap upside.”
4) Key evidence (most weight):
- Multiple polls/averages show generic ballot around D+4 to D+6 (Fox, Emerson, reported averages).
- Trump approval materially underwater (YouGov/Economist; Emerson; CNN reporting).
- Multiple states changing maps; gerrymandering reduces number of flippable seats (Ballotpedia, NPR).
- Narrow starting margin means modest swing flips control.
5) Blind-spot scenario: A strong economic rebound + successful GOP reframing on immigration/national security + favorable finalized maps could yield GOP holding a small majority (pushes forecast upward/positive).

Distribution:
Percentile 1: -45
Percentile 5: -34
Percentile 10: -27
Percentile 20: -18
Percentile 40: -11
Percentile 60: -5
Percentile 80: 3
Percentile 90: 9
Percentile 95: 14
Percentile 99: 23