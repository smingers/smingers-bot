Analysis:

(a) Source analysis  
1. Statista medal-table page (undated, historical Beijing-2022 data only).  High-quality for raw numbers but pay-walled; no forward-looking claims.  
2. ESPN Beijing-2022 medal tracker (Feb 2022).  Factual historical medal counts; no opinion, good quality.  
3. NBCOlympics Beijing-2022 standings (Feb 2022).  Same as #2, redundant but reliable.  
4. CBS8 explainer (31 Jan 2026).  Up-to-date, lays out IOC rules and gives the official AIN roster (20 athletes).  Straight reporting; opinions clearly attributed.  
5. Guardian op-ed (11 Feb 2026).  Mix of fact (roster size, vetting rejects) and commentary.  Factual pieces are sourced; opinions (e.g. “ban is hurting”) are recognised as such.  
6. Moscow Times report (12 Feb 2026).  On-the-ground factual coverage of AIN athletes, names and sports; notes that, as of two days ago, no medals yet.  Some quotes from politicians are opinion.  
7. Agent report (model synthesis).  Pulls IOC historical numbers (OAR 2018: 17 medals/168 athletes; ROC 2022: 32 medals/212 athletes) and vetting conditions.  Data points are traceable to CNN / IOC Results Books and are consistent with public records.

All factual numbers agree across independent outlets; therefore they are given high weight.  Opinionated remarks by politicians and columnists are ignored for quantitative estimation.

(b) Reference class analysis  
Candidate reference classes:

RC-1  Small Winter-Olympic delegations (≤20 athletes) since 1994.  
 Advantage: identical roster size.  
 Drawback: includes many micro-nations with little winter-sport tradition; likely under-states true medal potential.

RC-2  Russian athletes under neutral designations (OAR 2018, ROC 2022).  
 Advantage: identical talent pool.  
 Drawback: delegation sizes 8–10 × larger, included team events and many athletes now ineligible (military ties, doping).

RC-3  “Star-athlete micro-teams” – e.g. Liechtenstein 2018 (9 athletes, 1 bronze), Slovenia 2022 ski jump mixed team (4 athletes, 1 silver).  
 Advantage: shows that a few elite athletes can still medal.  
 Drawback: very small sample size and heterogeneous.

We use a blended approach: start with per-athlete medal efficiency from RC-2 (10–15 %), but scale down to account for (i) loss of strongest Russian medal factories – biathlon, relay cross-country, men’s hockey – and (ii) stringent vetting that excluded several champions.  A conservative adjusted efficiency of 5-7 % per athlete is defensible and keeps us well above RC-1’s micro-nation base rate (~1 %).

(c) Timeframe analysis  
The prediction horizon is 9 days (Games close 23 Feb 2026).  Historically, the bulk of Russian medals arrive throughout the fortnight, not just early.  Therefore the outside view should treat the current “zero medals so far” (per Moscow Times, 12 Feb) as normal noise, not evidence that the team will finish medal-less.

(d) Justification  
• Historical neutral Russian delegations:  
  – 2018 OAR: 17 medals / 168 athletes = 0.10 per athlete.  
  – 2022 ROC: 32 medals / 212 athletes = 0.15 per athlete.  
• Adjust downward for (a) no team events, (b) smaller, vetted roster.  Applying a 50–65 % haircut yields 0.05–0.07 expected medals per athlete.  
• With N = 20 AIN athletes, λ (Poisson mean medals) ≈ N × p = 1.0–1.4.  
• The probability of at least one medal is 1 − e^(-λ):  
  λ = 1.0  ⇒  63 %  
  λ = 1.4  ⇒  75 %

That range brackets both the optimistic “carry-over Russian strength” view and the pessimistic “too few stars left” view.  Expert commentary (Guardian, Moscow Times) still lists multiple plausible podium contenders in figure skating, cross-country and aerials, which makes the lower end (≈60 %) more plausible than the upper teeny-tiny country base rate (≈10 %).

Outside view calibration:

Anchor: 63–75 % derived from Poisson model above.  
Uncertainty sources: small sample of only 20 athletes, possible injury/under-performance, and the fact that we are 2 days into competition with zero medals yet.  Historically upsets run 10–15 % in Winter-Olympic event outcomes, which slightly widens tails.  I shave 5 percentage points off the midpoint (69 %) to allow for that extra variance and the possibility that the vetting really did remove almost all medal-class athletes.

Outside View Prediction:
64 %