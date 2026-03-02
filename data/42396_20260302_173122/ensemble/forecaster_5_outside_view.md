Analysis:

(a) Source analysis  
1. Wikipedia RSF article (updated Feb 2026). High-level overview of battlefield situation; reliable for basic facts but not a real-time news wire.  Shows continued RSF advances and foreign support – factual, pessimistic for peace.  
2. Wikipedia SAF article (late-2025 edit).  Mostly historical; “75 % Islamist influence” claim is uncited opinion – low evidentiary weight.  
3. Dabanga Sudan timeline Oct–Dec 2025.  Local independent outlet that routinely breaks Sudan news; useful, though not a primary international wire.  Reports escalating violence and failed diplomacy.  
4. Grand Pinnacle Tribune, Nov 2025.  Re-aggregates AFP/BBC content; facts match mainstream reporting.  Key fact: SAF refused a US-led 3-month truce.  
5. Daily Sabah, 21 Jan 2026.  Credible regional paper quoting SAF sources; notes a new (but still unaccepted) US–Saudi proposal.  
6. UN News brief, 1 Mar 2026 (cited in Agent report).  Primary UN source; confirms no imminent talks, humanitarian focus only.  
7. Agent report (2026-03-02).  Synthesises open-source material and Metaculus-specific empirical studies (EA Forum, Rethink Priorities).  Good methodological quality; all numerical statements are traceable.

Factual consensus across sources: fighting and humanitarian crises are intensifying, diplomatic activity remains stuck at the “plead for humanitarian pause” stage.  No credible announcement of negotiations is on the calendar for early- to mid-March 2026.

(b) Reference class analysis  
Potential classes:
1. “All Metaculus geopolitical binary questions” – large N, but content-agnostic.  
2. “Metaculus cease-fire/peace-agreement binaries” – content-relevant but small N.  
3. “Metaculus binaries whose community prediction sits within ±0.5 pp of a round threshold 10 days before measurement” – behaviourally the closest match, because the event we care about is *crossing* a knife-edge.

Class 3 is most predictive here; historical API pulls (Rethink Priorities dataset, 600+ binaries) show that when a CP is within 0.5 pp of a threshold, the median absolute change over the next 10 days is ≈0.9 pp, with a mild downward drift (-0.05 pp day⁻¹) for conflict questions.  Roughly 35 – 40 % of those cases end up on the “above-threshold” side 10 days later.

(c) Timeframe analysis  
• Today → resolution date: 12.0 days.  
• In 2023-2025 data, 10- to 14-day windows produced a standard-deviation of ≈1.7 pp in CP changes for conflict binaries.  
• The underlying cease-fire probability itself rarely gets materially better in under two weeks unless (i) formal talks are announced or (ii) one side collapses – neither is visible now.  Therefore any drift is more likely slightly downward than upward.

(d) Justification  
1. Starting point: CP = 30.00 %.  
2. Historical volatility: σ10-day ≈1.7 pp ⇒ P(|Δ| < 0.5 pp) ≈ 45 %.  Small moves dominate.  
3. Directional drift: -0.6 pp expected over 12 days (-0.05 pp day⁻¹ × 12).  
4. Treat Δ ~ Normal(-0.6, 1.7²).  Probability that CP_final > 30 % ≡ P(Δ > 0) = Φ(-(-0.6)/1.7) = Φ(0.35) ≈ 0.36.  
5. Expert/market expectations: none signal improved prospects; if anything, sentiment is deteriorating.  That nudges the outside view slightly lower.

Outside view calibration:

• Anchor on 36 % from the simple drift/volatility model.  
• Adjust -2 pp to reflect fresh negative UN briefing on 1 March that is unlikely to spur optimistic forecasts and may attract a few bearish updates.  
• No positive scheduled events inside the window to offset.  

Calibrated outside-view probability ≈ 34 %.

Outside View Prediction:
34 %