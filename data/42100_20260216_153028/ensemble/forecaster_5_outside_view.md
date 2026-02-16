Analysis:

(a) Source analysis  
1. OpenRouter “LLM rankings” live page (Feb-2026). Primary source that will ultimately determine resolution.  No historical numbers visible without scraping the API; still, it establishes the exact metric (weekly token share by author).  High factual value, current.  
2. OpenRouter “State-of-AI 2025” 100-T-token study (Oct-2025 data).  Internal analytics report; gives an average Chinese share ≈ 13 % YTD-2025 and a stacked-area plot covering Jan-2024 → Oct-2025.  High factual value, slightly dated, but methodology is documented.  
3. Wayback-extracted PDF of 11 Nov 2025 leaderboard (agent report). Lists exact shares: Qwen 8.1 %, DeepSeek 4.7 %, Moonshot 1.3 %, Baichuan 0.4 %, Yi 0.2 % → total Chinese 14.7 %.  Direct screenshot = high reliability for that week.  
4. SCMP (8 Dec 2025) & AryNews (10 Dec 2025).  Both summarise the OpenRouter 100-T study and emphasise “nearly 30 %” Chinese share in peak H2-2025 weeks.  Factual component is second-hand but consistent with source #2. Medium credibility.  
5. Al Jazeera (13 Nov 2025) & NBC News (30 Nov 2025).  Journalistic pieces quoting executives (Airbnb, Anthropic, etc.) and OpenRouter usage snapshots (7 Chinese models in top-20, 4 in top-10 coding).  Provide colour and corroboration but no precise percentages. Medium credibility.  
6. Interconnects.ai newsletter (summer 2025).  Analyst commentary that Chinese open models were “default for many months” with specific model anecdotes.  Opinionated but technically informed. Medium credibility.  
7. Agent research memo.  Collates hard datapoints (Jan 5 2025 ≈ 5 %, Jul 14 2025 ≈ 28 %, Nov 11 2025 = 14.7 %) and identifies gaps.  Transparent about uncertainty; useful for trend line.

(b) Reference-class analysis  
Candidates:  
1. “Share of Chinese LLM authors on OpenRouter, weekly”  (directly matches target; only ~110 historical weeks).  
2. “Global market share of Chinese open-source LLMs across all platforms.”  Broader but partially reflected in OpenRouter.  
3. “Share of non-US authors on comparable developer platforms (e.g., HuggingFace Spaces).”  Further removed.  
Reference class #1 best fits: same metric, platform, cadence.

(c) Timeframe analysis  
• Today → resolution: 63 days (≈ 9 weeks).  
• Weekly Chinese share swung from 5 % (Jan 2025) → 28 % (Jul 2025) → ~15 % (Nov 2025).  Typical intra-quarter oscillation 5-10 pp.  
• No evidence of single-week step-changes >15 pp without a blockbuster model drop.  
• Two months is short: base rate = “current share ± a few percentage points,” but we lack the exact current value.  The most recent hard number (Nov 2025) was 14.7 %.  Trend commentary (Nov–Dec press + continued Chinese releases in 2026) suggests the share likely drifted upward modestly into the high-teens.

(d) Justification for an outside-view baseline  
Status-quo anchor:  ≈ 16-18 % Chinese share in early-2026 (inferential).  
Drivers toward higher share by April 2026:  
• Numerous cost-efficient Chinese releases (e.g., DeepSeek-Coder series, Qwen-4-mix) emphasise latency/price advantages attractive to OpenRouter’s cost-sensitive user base.  
• Growing US-startup adoption (NBC, Al Jazeera pieces; anecdotal but repeated).  
Drivers toward lower share:  
• GPT-5.5 and Google Gemini-Ultra-2 landed in Jan 2026 and are being trial-priced aggressively; these can claw back tokens in the short term.  
• OpenRouter’s US customer mix (>50 % non-US, but enterprise skew still toward US labs).  
Given only nine weeks for movement, a gradual drift, not a regime change, is the outside-view expectation.  Historical weekly volatility (~±5 pp) becomes our rough σ.  
We therefore center the outside view at 20 % with a wide band recognising unknown-unknown events (export crack-down, breakthrough Chinese model, outages, etc.).

Outside view calibration:

1. Shape:  Assume an approximate normal around 20 % with σ ≈ 5 pp but manually fatten the tails (kurtosis) to respect past 28 % peak and a conceivable dip to ~10 %.  
2. Tails:  10th percentile set a little above the 2024 baseline (11 %) to reflect that a total collapse below 10 % in nine weeks would require an extreme negative shock.  90th percentile at 33 % (slightly above the 2025 peak) allows for a surprise blockbuster Chinese release or a major outage in US models.  
3. Middle values spaced to keep cumulative distribution strictly increasing and roughly consistent with a fat-tailed normal.

Outside View Prediction:
Percentile 10: 11
Percentile 20: 14
Percentile 40: 18
Percentile 60: 22
Percentile 80: 27
Percentile 90: 33