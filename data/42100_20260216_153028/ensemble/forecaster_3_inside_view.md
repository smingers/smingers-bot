Analysis:
**Target variable / resolution criteria (paraphrase):** Sum weekly token usage shares (excluding “others”) of *Chinese model authors* on OpenRouter’s Rankings page for the **week of Apr 19, 2026**, expressed in **%**.

## (a) Source analysis (what each says; quality; date; facts vs opinions)

1. **OpenRouter + a16z “State of AI” empirical study (reported via SCMP/Yahoo/etc., Dec 8–9 2025)**  
   - **Facts:** Uses OpenRouter token-volume data (100T tokens). Chinese open models rose from ~1.2% (late 2024) to **peaks near ~30% during parts of 2025**, with **~13% average weekly share in 2025**; late-2025 levels sometimes ~high teens.  
   - **Quality:** High on *methodology relevance* (directly about OpenRouter token share), but we’re consuming it through journalism summaries and a rasterized chart problem (precision limited).  
   - **Use:** Strong baseline for plausible ranges and volatility.

2. **TrendForce citing Nikkei (Jan 26, 2026): “Chinese AI models hit ~15% global share in Nov 2025.”**  
   - **Facts:** ~15% global share (method likely broader than OpenRouter).  
   - **Quality:** Medium—secondary reporting; and “global share” ≠ OpenRouter share.  
   - **Use:** Directionally supportive that Chinese usage is material, but not directly resolving.

3. **CNBC (Feb 4, 2026): OpenRouter rankings—DeepSeek #3, Moonshot/Kimi #4 in the prior week**  
   - **Facts:** Claims about OpenRouter author rankings positions in late Jan/early Feb 2026; includes price comparisons (Artificial Analysis).  
   - **Quality:** Medium-high for the ranking-position fact (named outlet, specific claim), but still **not the numeric shares** we need.  
   - **Use:** Important “inside-view” signal that Chinese authors are currently among top usage on OpenRouter.

4. **SCMP (Feb 9, 2026): Qwen-3.5 imminent; mentions other upcoming Chinese releases (GLM-5, etc.)**  
   - **Facts:** Pull requests suggesting Qwen-3.5 release; describes model sizes/features.  
   - **Quality:** Medium; credible tech reporting, but forward-looking impact on OpenRouter share is uncertain.  
   - **Use:** Suggests near-term catalysts for Chinese share *upside* by April.

5. **CNN (Feb 11, 2026): mixture of facts + expert opinions on gap, chips, and upcoming DeepSeek model**  
   - **Facts:** Repeats OpenRouter late-2025 study; mentions reported conditional approvals for H200 purchases; says DeepSeek to unveil a new model later Feb (timing claim).  
   - **Opinions:** Justin Lin’s “<20% chance of overtaking in 3–5 years,” etc. (about *frontier performance*, not usage share).  
   - **Quality:** Medium.  
   - **Use:** Mixed—performance-gap opinions slightly temper the idea that usage must keep climbing, but cost/open-source can still drive usage.

6. **AskNews Chinese-language roundups (Feb 15–16, 2026): GLM-5 launch/open-source; MiniMax M2.5; DeepSeek V4 rumors; ByteDance upgrades**  
   - **Facts (claimed):** GLM-5 “previously topped OpenRouter popularity rankings”; releases on Feb 12–13; Qwen-3.5 timed for Spring Festival.  
   - **Quality:** Medium-low to medium: these are recaps; some statements are hard to verify, and “topped rankings” could mean brief spikes.  
   - **Use:** Supports near-term release density as an upside driver, but I treat magnitude claims cautiously.

7. **VentureBeat (Nov 26, 2025): OpenRouter used as model gateway in an orchestration project**  
   - **Facts:** Illustrates OpenRouter’s role in multi-model workflows.  
   - **Quality:** Medium; not about Chinese share directly.  
   - **Use:** Weak indirect support: if model-orchestration grows, cheaper models (often Chinese/open) can gain share.

## (b) Evidence analysis (weighted)

**Strong evidence (large shifts):**
- **OpenRouter/a16z empirical study** showing Chinese shares **can reach ~30% in some weeks** and **average ~13% in 2025** (directly on-metric, establishes feasible range and volatility).  
  *Implication:* 25–35% is plausible in “surge weeks,” and teens are plausible in “normal weeks.”

**Moderate evidence (moderate shifts):**
- **CNBC: DeepSeek #3 and Moonshot #4** in late Jan/early Feb 2026 on OpenRouter author rankings.  
  *Mechanism:* being top-4 by usage strongly suggests Chinese share is currently **not** stuck near low teens; likely in the high-teens to 30s depending on concentration.  
- **Near-term Chinese model release cadence (Qwen-3.5, GLM-5, DeepSeek next model, MiniMax updates)** ahead of an April target week.  
  *Mechanism:* OpenRouter users are price/perf sensitive; new “good-enough + cheap” models tend to get tried and integrated quickly.

**Weak evidence (small shifts):**
- “Year of Qwen” type narratives and general geopolitical commentary; also “global share” stats not aligned to OpenRouter.  
  *Mechanism:* Directional only; doesn’t map cleanly to the resolution definition.

## (c) Timeframe analysis

- **Today:** 2026-02-16  
- **Target week:** week of **Apr 19, 2026** (≈ **9 weeks** ahead); resolves Apr 27.

**If timeframe were halved (~4–5 weeks):** I’d hew closer to “current ranking regime” (DeepSeek/Moonshot high), so I’d narrow slightly and keep the median a bit higher (less time for US response or geopolitical shocks).  
**If timeframe were doubled (~18 weeks):** I’d widen tails materially (more time for US model launches, pricing moves, or sanctions) and slightly regress the median toward the longer-run 2025 average unless we had hard current share numbers.

## (d) Justification (how I move from outside view to inside view)

**Outside-view anchor (given):**  
P10 9.5, P20 11.5, P40 14.0, P60 16.5, P80 20.0, P90 24.0.

**Why shift upward (main):**
1. **CNBC’s OpenRouter ranking snapshot** (2 Chinese authors in the top 4 very recently) is a strong clue that the system is in a higher-Chinese-share regime than the Nov-2025 ~15% snapshot. Even without numeric shares, top-4 placement usually implies substantial token volume.  
2. **Release density in Feb (GLM-5, MiniMax M2.5, Qwen-3.5 imminent, DeepSeek next model rumored)** creates a plausible pathway for **April** to be a “surge week” akin to 2025 peaks (though not guaranteed).  
3. **Structural driver persists:** Chinese models compete hard on **cost/latency + open weights**, which is exactly what many OpenRouter users optimize for (experimentation, agent pipelines, cost control).

**Why not shift too far upward (constraints):**
1. **US providers still lead the top slots** (Anthropic/Google) per CNBC, implying China is not dominating outright.  
2. **Trust/compliance/geopolitical risk** can cap adoption in some enterprise segments (even if models are runnable on-prem).  
3. 2025’s ~30% appears episodic; absent hard live-share numbers, I avoid assuming a permanent step-change to 35–45%.

Net: I shift the whole distribution upward, especially the 40–80th percentiles, and widen the upper tail to allow an April “spike week.”

Distribution calibration
- I’m targeting an **inside-view median ~22%** (up from ~15% outside-view), with meaningful mass in the **mid-to-high 20s** and an upper tail into the **high 30s**.
- Sensitivity: If I moved all percentiles **down by ~10% relative** (multiplicative), the median would land ~20%—still consistent with “two Chinese in top 4.” If I moved them **up by ~10%**, median ~24%—plausible if Qwen/DeepSeek releases cause another surge.

Checklist:
1. **Paraphrase check:** Chinese authors’ summed token share ÷ total (excluding “others”) on OpenRouter Rankings, **week of Apr 19, 2026**, **%**.
2. **Outside view base rate:** (9.5, 11.5, 14.0, 16.5, 20.0, 24.0).
3. **Consistency check:** Implied median ≈ (19.5+24.5)/2 = **22.0**; mean ≈ **24** (right-skew). Seems consistent with “top-4 presence + possible spike week.”
4. **Top evidence (3–5):**
   - OpenRouter/a16z: Chinese share **peaked near ~30% in 2025**, avg **~13%** (direct metric).
   - CNBC: **DeepSeek #3, Moonshot #4** on OpenRouter very recently (strong inside-view signal).
   - Multiple imminent Chinese releases (Qwen-3.5, GLM-5, DeepSeek next) before April (upside catalyst).
   - US models still lead (caps extreme outcomes).
5. **Blind spot:** A sudden **sanctions/compliance shock** or OpenRouter policy/UI change causes rapid Chinese share drop (pushes outcome **down**).
6. **Status quo:** Given recent rankings, status quo likely **high-teens to 20s**, so I avoid regressing all the way to ~13–15%.
7. **Technicalities:** Strictly increasing percentiles; units are %; tails allow <15 and >45 (though I keep <45).

Percentile 10: 11.0
Percentile 20: 14.5
Percentile 40: 19.5
Percentile 60: 24.5
Percentile 80: 31.5
Percentile 90: 38.0