# Base Rate Estimation: US Attack on Iran Before April 2026

## Step 1: Source Analysis

**Available Data Sources:**
- Historical records of US military interventions (Congressional Research Service, Department of Defense records)
- Academic databases on interstate conflicts (Correlates of War Project, UCDP/PRIO Armed Conflict Dataset)
- Historical records of US-Iran relations since 1979
- Records of US military actions in the Middle East post-WWII

**Reliability Assessment:**
- Post-1945 data is highly reliable and comprehensive
- "Attack" definition matters: ranges from airstrikes to full invasion
- US military actions are well-documented with minimal reporting bias
- Some covert operations may be underreported, but overt attacks are reliably recorded

**Systematic Biases:**
- Classified operations may not appear in historical record immediately
- Definition of "attack" vs. "military action" vs. "intervention" varies
- Proxy conflicts and covert support harder to categorize

## Step 2: Reference Class Analysis

### Reference Class 1: US Military Attacks on Sovereign Nations (Post-Cold War Era, 1991-2024)

**Description:** Direct US military attacks (airstrikes, missile strikes, or invasions) against sovereign nations, excluding ongoing operations in active war zones where US is already engaged.

**Historical Cases:**
- Iraq (1991 - Gulf War)
- Iraq (1998 - Operation Desert Fox)
- Afghanistan (2001)
- Iraq (2003)
- Libya (2011)
- Syria (2017, 2018 - limited strikes)
- Iran (2020 - Soleimani strike, limited)

**Analysis:**
- Time period: 33 years (1991-2024)
- Number of distinct countries attacked: 5 (Iraq, Afghanistan, Libya, Syria, Iran)
- Number of new attack decisions: ~7-8 major operations
- Historical base rate: ~7-8 attacks / 33 years = ~21-24% per decade, or ~2-2.4% per year
- For 16-month period (Jan 2025 - April 2026): ~2.7-3.2%

**Suitability Score: 7/10**

**Reasoning:** Good reference class because it captures post-Cold War US military doctrine and willingness to use force. However, it doesn't account for the specific US-Iran relationship or regional context.

### Reference Class 2: US Military Actions Specifically Against Iran (1979-2024)

**Description:** Direct US military strikes against Iranian targets or forces.

**Historical Cases:**
- Operation Praying Mantis (1988) - naval engagement
- Soleimani assassination (January 2020) - drone strike
- Various incidents with Iranian proxies (not direct attacks on Iran)

**Analysis:**
- Time period: 45 years (1979-2024)
- Number of direct attacks on Iranian territory/forces: 2 major incidents
- Historical base rate: 2 attacks / 45 years = 4.4% per year
- For 16-month period: ~5.9%

**Suitability Score: 9/10**

**Reasoning:** Most directly relevant reference class as it specifically examines US-Iran military history. High suitability because it captures the unique dynamics of this bilateral relationship, including periods of high tension that didn't result in attacks.

### Reference Class 3: US Attacks on Adversarial States With Nuclear Ambitions

**Description:** US military attacks on countries pursuing or suspected of pursuing nuclear weapons programs.

**Historical Cases:**
- Iraq (2003) - suspected WMD program
- Syria (2007) - Israeli strike with US support on suspected reactor
- No direct attacks on: North Korea, Pakistan (became nuclear), Libya (gave up program before 2011 intervention)

**Analysis:**
- Countries with nuclear ambitions that US did NOT attack: North Korea (70+ years), Pakistan, Libya (pre-2003)
- Countries with nuclear ambitions that US DID attack: Iraq (though WMD claims were disputed)
- Time period consideration: ~50 years of nuclear proliferation concerns
- Base rate: ~1-2 attacks out of ~5-6 cases = 17-33% over multi-decade periods

**For a specific 16-month window:** ~0.5-1%

**Suitability Score: 6/10**

**Reasoning:** Relevant because Iran's nuclear program is a key factor, but sample size is small and circumstances vary widely. Nuclear ambitions may actually deter attacks rather than provoke them.

### Reference Class 4: Frequency of US Initiating New Major Military Operations

**Description:** How often does the US begin entirely new military campaigns (not continuations)?

**Analysis:**
- Post-Cold War: approximately every 3-5 years the US initiates a significant new military operation
- 33 years / ~7 major new operations = one every ~4.7 years
- Annual probability: ~21%
- 16-month probability: ~28%

**However, this needs adjustment:**
- Most operations were against weaker states
- Iran represents a major regional power
- Subset of "major regional powers": Iraq (2003) was last such case
- Base rate for attacking major regional powers: much lower, perhaps 1 per 20+ years = ~5% annual, ~6.7% for 16 months

**Suitability Score: 5/10**

**Reasoning:** Too broad and doesn't account for target characteristics. Needs significant adjustment for Iran's military capabilities.

## Step 3: Fermi Estimation

Breaking down the probability:

**P(US attacks Iran) = P(Crisis occurs) × P(Crisis escalates to military action) × P(US chooses attack over alternatives)**

- **P(Crisis occurs):** US-Iran tensions are chronic. Major crisis probability in 16 months ≈ 30-40%
- **P(Crisis escalates to military threshold):** Given a crisis, ~10-20% reach military action threshold historically
- **P(US chooses attack):** Given escalation, US might choose: diplomacy, sanctions, covert action, or attack. Attack chosen ~20-30% of time

**Fermi estimate:** 0.35 × 0.15 × 0.25 ≈ 1.3%

## Step 4: Base Rate Integration

**Weighting by suitability:**

- Reference Class 1 (US attacks post-Cold War): 3.0% (weight: 0.20)
- Reference Class 2 (US-Iran specific history): 5.9% (weight: 0.45)
- Reference Class 3 (Nuclear ambitions): 0.75% (weight: 0.15)
- Reference Class 4 (Major powers): 6.7% (weight: 0.20)

**Weighted average:**
(3.0 × 0.20) + (5.9 × 0.45) + (0.75 × 0.15) + (6.7 × 0.20) = 0.6 + 2.66 + 0.11 + 1.34 = **4.71%**

**Fermi check:** 1.3% (suggests lower)

**Integration:** The reference class analysis clusters around 3-6%, with the most relevant class (US-Iran history) at 5.9%. The Fermi estimation suggests lower (~1.3%), possibly because it better captures the specific barriers to action. 

**Integrated base rate: ~3-5%**, centering on **4%**

## Step 5: Confidence Assessment

**Confidence Level: 6/10**

**Reasoning:**
- Moderate-good historical data availability
- Most relevant reference class (US-Iran) has small sample size (N=2)
- Clear historical pattern of US restraint toward Iran despite tensions
- 45 years of hostility with only 2 direct military actions suggests strong base rate
- However, small sample size and changing geopolitical contexts limit confidence

---

## Output

**Base Rate Estimate: 4%**

**Reference Classes Used:**
1. US-Iran specific military history (1979-2024): 5.9% base rate (weight: 0.45)
2. US attacks on major regional powers: 6.7% base rate (weight: 0.20)
3. US military attacks post-Cold War: 3.0% base rate (weight: 0.20)
4. US attacks on nuclear-ambitious states: 0.75% base rate (weight: 0.15)

**Confidence Level: 6/10**

**Key Uncertainties:**
- Small sample size for most relevant reference class (only 2 US-Iran direct military engagements in 45 years)
- Definition ambiguity: what constitutes an "attack" vs. limited strike vs. covert operation
- Changing geopolitical context: nuclear program advancement, regional proxy conflicts, and domestic politics in both countries may make historical patterns less predictive
- 16-month timeframe crosses potential US administration transition, adding uncertainty to policy continuity