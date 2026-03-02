
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
How much will Nasdaq-100 Futures total price returns exceed S&P 500 Futures in these biweekly periods of Q1 2026? (Mar 16 - Mar 27)

Question background:
[Nasdaq-100](https://en.wikipedia.org/wiki/Nasdaq-100) focuses exclusively on 100 of the largest non-financial companies listed on the Nasdaq exchange, heavily weighted towards technology and innovation. This index includes tech titans like Apple (approximately 12-15% of the index), Microsoft, Amazon, NVIDIA, and Alphabet (Google), making it a prime indicator of the tech sector's performance and innovation economy.

[S\&P 500](https://en.wikipedia.org/wiki/S%26P_500) represents 500 of the largest publicly traded U.S. companies across diverse sectors. It captures the broader market sentiment, including technology, healthcare, financial, and industrial giants like Apple, Microsoft, Amazon, JPMorgan Chase, and Johnson & Johnson. The index is market-cap weighted, meaning larger companies have a more significant impact on its movement.

`{"format":"metac_reveal_and_close_in_period","info":{"post_id":41219,"question_id":42089}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question is a subquestion of a group question. This subquestion specifically pertains to (and resolves according to) the option 'Mar 16 - Mar 27'. The resolution criteria for the parent question is below. 

Each subquestion will resolve as the difference between the percent total price return of [Nasdaq-100 Futures (NQ)](https://finance.yahoo.com/quote/NQ%3DF/history/) and that of [S\&P 500 Futures (ES)](https://finance.yahoo.com/quote/ES%3DF/history/) for the corresponding biweekly period, according to Yahoo Finance data.

Specifically, each subquestion will resolve as NQ\_return - ES\_return.

Returns will be calculated as follows: If P₀ is the Close price of a company stock on the last trading day or half-day *before* the start of the period and P₁ is the Close price of the stock on the last trading day *of* the designated period, the percentage return will be calculated as:

$$
 \text{return} = 100 \times \frac{P1 - P0}{P0}
$$

Additional fine-print:
* If ES outperforms NQ, the corresponding subquestion will resolve as a negative number.
* If Yahoo Finance delays or ceases reporting these data or if it reports them in error, Metaculus might use alternative credible sources to resolve this question.

***

For example, for the period Jun 9 - Jun 20, the subquestion would resolve based on the following calculations:

NQ\_P₀ = 21,789.50 (the Close price on Jun 6)

NQ\_P₁ = 21,889.89 (the Close price on Jun 20)

NQ\_return = 100 × (21,889.89 - 21,789.50) / 21,789.50 = 0.4607

ES\_P₀ = 6,006.75 (the Close price on Jun 6)

ES\_P₁ = 6,010.21 (the Close price on Jun 20)

ES\_return = 100 × (6,010.21 - 6,006.75) / 6,006.75 = 0.0576

And the resolution would be 0.4607 - 0.0576 = **0.4031** percentage points (pp).

***
This question's information (resolution criteria, fine print, background info, etc) is synced with an [original identical question](https://www.metaculus.com/questions/41219) which opened on 2026-02-27 21:00:00. This question will resolve based on the resolution criteria and fine print contained above. However, if this question would resolve differently than the original question, then this question will be annulled. Additionally, if the original question's resolution could have been known before this question opened, then this question will be annulled.

Units for answer: pp

Question metadata:
- Opened for forecasting: 2026-03-02T19:30:00Z
- Resolves: 2026-03-28T05:00:00Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-02T19:30:00Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-02. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-02 should not be considered as speculative but rather an historical document.

The lower bound is -4.0 and the upper bound is 4.0.
Both bounds are OPEN: outcomes can fall below the lower bound or above the upper bound. Your percentile estimates may extend beyond this range if well-supported by evidence.

Historical context:

<QuestionSource url="https://en.wikipedia.org/wiki/Nasdaq-100">
## Summary of Nasdaq-100 Wikipedia Article

This article provides a comprehensive overview of the Nasdaq-100 (NDX) index. Key points relevant to the forecasting question include:

### Structure & Composition
- Comprises **100 of the largest non-financial companies** listed on Nasdaq
- Uses a **modified capitalization-weighted methodology** with rules capping the influence of largest components
- **Heavily weighted toward technology**, including tech titans like Apple, Microsoft, Amazon, NVIDIA, and Alphabet
- Excludes financial companies (which are tracked separately in the Nasdaq Financial-100)
- Includes **10 foreign-incorporated companies** as of December 2025

### Performance History
- Fell **78% during the dot-com bust (2002)** after peaking above 4,700
- Experienced significant losses during the **2008 financial crisis**
- Recovered strongly through quantitative easing periods

### Index Mechanics
- **Rebalanced quarterly** if concentration thresholds are breached (single company >24%, or top companies >48%)
- **Rebalanced annually** if one company exceeds 15% or top five exceed 40%
- Annual re-ranking each December

### Futures Trading
- E-mini futures trade on the **Chicago Mercantile Exchange under ticker NQ** — directly relevant to the resolution of this question

---
**Note:** This article contains no information specific to the Mar 16–Mar 27, 2026 period or recent price movements relevant to resolving the forecasting question.
</QuestionSource>

<QuestionSource url="https://en.wikipedia.org/wiki/S%26P_500">
## Summary of Article: S&P 500 (Wikipedia)

**Note:** This article is a general Wikipedia overview of the S&P 500 index and does not contain information specifically relevant to the Mar 16–Mar 27, 2026 biweekly period or NQ vs. ES futures performance comparisons.

---

### Key Facts

**Index Composition & Structure:**
- Tracks 500 leading U.S.-listed companies; covers ~80% of total U.S. public market cap (~$61.1 trillion as of Dec 31, 2025)
- Market-cap weighted; top 10 companies = ~38% of index; top 50 = ~60%
- **Top 10 components (as of January 2026):** Nvidia (7.17%), Alphabet (6.39%), Apple (5.86%), Microsoft (5.33%), Amazon (3.98%), Broadcom (2.51%), Meta (2.49%), Tesla (2.31%), Berkshire Hathaway (1.68%), Eli Lilly (1.55%)

**Historical Performance:**
- Compound annual growth rate since 1926: ~9.8% (including dividends); ~6% after inflation
- Posts annual gains ~70% of the time; ~5% of trading days result in record highs
- **Record closing high: 6,932.05 on December 24, 2025**
- Index fell to a low of **4,982.77 on April 8** (intra-year correction of 10–20%)
- S&P 500 **rose above 7,000 for the first time on January 28, 2026**

**Derivatives Market:**
- CME offers futures contracts (ES) tracking the S&P 500, traded via open outcry or Globex platform — described as CME's most popular product

---

*This article provides no data directly relevant to the Mar 16–Mar 27, 2026 resolution period or relative NQ/ES performance.*
</QuestionSource>


<Summary source="https://www.barchart.com/futures/quotes/NQ*0/futures-spreads">
**Disclaimer:** This article does not contain any information directly relevant to the forecasting question about Nasdaq-100 Futures vs. S&P 500 Futures price returns for the Mar 16–Mar 27 period. The page is a reference/educational page from Barchart.com explaining futures spread terminology and mechanics.

---

## Summary

The article is a **reference guide from Barchart.com** explaining the structure and terminology of futures spreads for the Nasdaq 100 E-Mini March 2026 contract. Key points include:

- **What a spread is:** A contract to simultaneously buy or sell multiple futures or options contracts, rather than trading them individually.
- **Symbol syntax:** Futures spread symbols begin with `_S`, followed by a spread type code and the individual contract legs (e.g., `_S_SP_ZWU7_ZWH0`).
- **Spread types defined:** The article provides detailed definitions for numerous spread types, including:
  - **SP** (Standard Calendar): Buy front month, sell back month
  - **EQ** (Equities Calendar): Sell front month, buy back month
  - **BF** (Butterfly), **CF** (Condor), **DF** (Double Butterfly)
  - **IS** (Inter-commodity), **IV** (Implied Intercommodity)
  - Various interest rate, energy, and foreign exchange spread types

The content is purely **definitional and structural**, with no pricing data, market analysis, or information pertinent to NQ vs. ES return comparisons.
</Summary>

<Summary source="https://www.tradingview.com/chart/ESM2020/aQntL7q2-Spread-Trading-The-NQ-and-ES/">
## Summary

**Disclaimer:** The extracted content is extremely limited — it appears to be a brief description/caption for a video post on TradingView, with no substantive article text available. The actual video content was not captured in the extraction.

### What the Content Reveals:

- **Source:** TradingView, posted by user "chrishall" on **April 23, 2020**
- **Topic:** The post describes a video covering **spread trading between NQ (Nasdaq-100 futures) and ES (S&P 500 futures)**
- The author characterizes this type of spread trading as:
  - Something they do **"on a regular basis"**
  - **"Popular with hedge funds"**
  - A **"very powerful type of trade"** to have in one's trading toolkit
- The post includes a standard **TradingView disclaimer** stating the content does not constitute financial, investment, trading, or other types of advice

### Relevance to the Forecasting Question:
This article provides **no quantitative data, price levels, or analytical insights** relevant to forecasting the NQ vs. ES return differential for the **March 16–27, 2026** period. It is a dated (2020) promotional description of a trading video with no substantive content extracted.
</Summary>

<Summary source="https://www.edgeful.com/blog/posts/es-vs-nq-futures-comparison">
## Article Summary

**Disclaimer:** This article appears to be a promotional/educational piece from a trading platform or service (likely "Edgeful"), written in an informal style. It lacks specific dates and some data tables appear incomplete in the extracted content. It should be treated as a less reliable source due to its commercial nature.

---

### Core Subject
A comparison of ES (S&P 500 Futures) and NQ (Nasdaq-100 Futures) for traders, using performance data and statistics.

### Key Structural Differences

| Feature | ES | NQ |
|---|---|---|
| Underlying Index | S&P 500 (500 companies, all sectors) | Nasdaq-100 (100 largest non-financial, tech-heavy) |
| Dollar per point | $50 | $20 |
| Tick size | 0.25 points = $12.50 | 0.25 points = $5.00 |
| Initial margin (overnight) | ~$12,000–$15,000 | ~$17,000–$20,000 |

### Volatility & Character
- **NQ** is heavily concentrated in tech giants (AAPL, MSFT, NVDA, GOOGL, AMZN), making it significantly more volatile, especially around tech earnings or AI-related news
- **ES** offers broader sector exposure; tends to produce slower, more predictable trends
- NQ can gap 100+ points on tech-specific news while ES "barely reacts"
- Average True Range (ATR) data confirms NQ has a **wider daily range** than ES

### Performance Data Referenced
- **ORB (Opening Range Breakout)** statistics tracked over 6 months show clear differences between ES and NQ, with NQ exhibiting wider ranges (specific numbers were not fully captured in extraction)
- **Gap Fill performance**: Described as "not much difference" between ES and NQ — noted as a surprising finding
- The author observed **gap fill performance degrading** across both instruments starting December 2024
- NQ ORB algorithm results tracked Oct 1 – Sep 3, 2025 (optimized settings, specific figures not fully captured)

### Correlation Between ES and NQ
- Correlation is **highest** during major macro events (Fed announcements, economic data releases)
- Correlation is **lowest** during earnings seasons when tech moves independently
- During broad market moves they tend to move together; sector rotation causes divergence

### Micro Futures
- Micro versions (MES, MNQ) are 1/10th the size of E-mini contracts
- MES tick = $1.25 | MNQ tick = $0.50
- Recommended for beginners, small accounts, or precise position sizing

### Practical Guidance (Author Opinion — Less Reliable/Unnamed Source)
- Author advises new traders to master ES before trading NQ
- NQ's faster pace demands quicker decision-making with less room for deliberation
- For prop firm traders with daily loss limits, NQ can reach max loss faster than ES
- Algorithmic strategies that work on ES may not translate directly to NQ due to volatility differences

---

**Relevance to Forecast Question:** The article provides general context about the structural differences between NQ and ES futures — notably that NQ tends to be more volatile and tech-driven — but contains **no specific data or forecasts** relevant to the Mar 16–27, 2026 resolution period.
</Summary>


<Summary source="https://www.nasdaq.com/articles/biweekly-investment-insights-we-know-much-least-theres-never-dull-moment">
**Disclaimer:** The article content provided is essentially non-functional — it appears to be an error/placeholder page from Nasdaq's website, containing only navigation interface instructions (how to add symbols to watchlists, quotes, etc.) rather than any actual article content. The title "Biweekly Investment Insights: We know this much at least: there's never a dull moment" is present, but no substantive article text was successfully extracted.

**Summary:** No meaningful information relevant to the forecasting question (NQ vs. ES returns for Mar 16 – Mar 27, 2026) can be extracted from this article. The page appears to have failed to load its actual content, returning only boilerplate website navigation and symbol-search instructions instead. There are no facts, statistics, named-source opinions, or market data available from this source to inform the forecast.
</Summary>

<Summary source="https://datatrekresearch.com/nasdaq-market-cycles/">
## Summary of DataTrek Research Article: "NASDAQ Market Cycles" (April 19, 2022)

**Note:** This article is from April 2022 and discusses historical NASDAQ market cycles. It does not contain information directly relevant to the Mar 16–Mar 27, 2026 resolution period. Its utility for the forecasting question is limited to providing historical context on NQ vs. ES relative performance patterns.

---

### Key Facts & Statistics

- At the time of writing (April 2022), the NASDAQ Composite was **down ~5%** and the QQQ (Nasdaq-100) was **down ~1%** over the trailing year, while the S&P 500 was **up ~5%** — meaning ES was outperforming NQ.
- Post-recession NASDAQ peak annual gains historically: **+87%** (1983), **+64%** (1991), **+56%** (2004), **+63%** (2010), **+80%** (2021).
- Following each post-recession peak, the NASDAQ **always** subsequently printed a negative annual return, ranging from shallow (−1% to −5%) to severe (−25% in 1984).
- Mid-cycle NASDAQ recoveries historically ranged from **+10% to +40%** annually.
- Recessions consistently produced **−20% or worse** annual NASDAQ returns.

---

### Named Source Opinions (DataTrek Research)

- DataTrek believed (as of April 2022) it was **premature** to call the start of a mid-cycle NASDAQ rally, citing three reasons:
  1. The 2021 post-recession rally (+80%) was above the historical average (+65%), suggesting more giveback may be needed.
  2. The Federal Reserve's rate-hiking cycle was a headwind for growth stocks; DataTrek projected 10-year Treasury yields heading to **3.2–3.7%**.
  3. Rising oil prices (linked to Russia-Ukraine conflict) posed recession risk, which historically devastates NASDAQ performance.
- DataTrek **strongly preferred "super cap" Big Tech** over speculative NASDAQ names, citing rising rates' mathematical effect on valuations and the value of steady profits from competitive advantages.
- DataTrek rated **2022 as below-average** for the animal spirits typically needed for mid-cycle tech rallies.

---

### Contextual Takeaways Relevant to NQ vs. ES Dynamics

- The article implicitly supports the idea that **NQ underperforms ES** during periods of Fed tightening, post-peak corrections, and recession fears.
- NQ tends to **outperform ES** during mid-cycle recoveries and when risk appetite is high, but this dynamic can take **1–4 years** to materialize after a post-recession peak.
</Summary>

<Summary source="https://www.longtermtrends.com/nasdaq-vs-sp500/">
## Summary: Nasdaq to S&P 500 Ratio (Longtermtrends, by Silvan Frank)

**Note:** The article's interactive chart data could not be fully loaded in the extracted content, limiting the availability of specific current numerical data.

### Key Concepts

- **The Nasdaq to S&P 500 ratio** compares the performance of the Nasdaq Composite Index (technology/growth-oriented) against the broader S&P 500.
  - **Rising ratio** → Nasdaq outperforming S&P 500 (tech/growth stocks stronger)
  - **Falling ratio** → Nasdaq underperforming S&P 500 (relative weakness in tech/growth)

### Structural Observations
- The ratio has a **theoretical ceiling**: it cannot grow indefinitely, as Nasdaq-listed stocks would eventually represent 100% of the U.S. stock market.
- **Historical peak**: The ratio reached its highest point during the **Dot-com bubble (~2000)**, driven by excessive optimism and overvaluation of tech companies.

### Index Characteristics
- Both indices are **capitalization-weighted** and **exclude dividends**.
- The **1-year rolling correlation** between the two indices is historically **strongly positive**, meaning they tend to move in the same direction, limiting diversification benefits between the two.

### Relevance to Forecasting Question
The article provides **conceptual and historical context** for the NQ/ES relationship but contains **no specific data points** for the Mar 16–27, 2026 resolution period.
</Summary>


<Agent_report>
Query: Over last 15 years, calculate every 10-trading-day total-return difference between CME NQ and ES futures; provide mean, median, stdev, 25th/75th percentiles, and share of periods where spread <0. Also list top five positive and negative outliers.
The original request has two parts:  
1) compile a 15-year history (January 2011–March 2026) of every 10-trading-day total-return spread between the CME E-mini Nasdaq-100 futures (continuous ticker NQ=F) and the CME E-mini S&P 500 futures (ES=F);  
2) summarise that 3,700-observation distribution (mean, median, standard deviation, 25th/75th percentiles, share < 0 %, and the five most-positive and five most-negative spreads).

What the currently retrieved material establishes

1. Instrument validity and identifiers  
   • CME webpages confirm both contracts and their tickers (NQ and ES) and that they are quoted continuously (CME Group – E-mini Nasdaq-100 Overview; CME Group – E-mini S&P 500 Overview).  
   • Yahoo Finance hosts back-adjusted continuous daily closes under the tickers “NQ=F” and “ES=F”. A yFinance snapshot shows daily settlement prices for both series through 2 Mar 2026 (yFinance: NQ=F, ES=F).

2. Existence of freely downloadable daily data back to at least 2000  
   • Barchart’s Historical Price pages state that daily data for both symbols extend to 01 Jan 2000 and are exportable as CSV (Barchart – Price History for NQ*1 and ESZ26).  
   • Yahoo Finance’s CSV endpoint likewise covers the period when suitable epoch timestamps are supplied; multiple public tutorials document the download procedure (QuantInsti, 2022; implicit in yFinance library).

3. Proof-of-concept calculation  
   • Using the last ten trading days displayed by yFinance (17 Feb – 2 Mar 2026), the 10-day returns are +1.25 % for NQ and +0.65 % for ES, giving a spread of +0.60 pp. That verifies the arithmetic that must be repeated for each historical window.

4. Absence of pre-computed statistics  
   • No academic or practitioner source in the search set provides the fifteen-year series of 10-day spreads or any of the requested descriptive moments/outliers. All evidence indicates the numbers must be generated programmatically from raw daily closes.

Why the uncovered information is insufficient

To answer the original quantitative query we still need:

• The complete vector of daily closing prices for NQ=F and ES=F from at least 2 Jan 2011 (the first trading day of the year) through 2 Mar 2026.  
• A decision on windowing: the question explicitly says “every 10-trading-day total-return difference”, which implies rolling (overlapping) windows rather than non-overlapping segments; roughly 3,780 trading days would produce ≈ 3,771 observations.  
• Computation of each pair of percentage returns, then their difference (spread).  
• Derivation of distributional statistics:  
  – mean, median, standard deviation, 25th and 75th percentiles;  
  – proportion of observations with spread < 0 %;  
  – identification of the five largest positive and five largest negative spreads together with their start-and-end dates and magnitudes.

None of those figures can be filled in until the raw data series are downloaded and rolled.

Materiality for the broader forecasting task

The forecasting market ultimately resolves on one specific bi-weekly period (16 Mar – 27 Mar 2026). Historical distribution parameters of 10-day NQ–ES spreads are essential inputs for:

• an empirical-Bayes prior (e.g., assume the next 10-day spread is drawn from the historical distribution, possibly adjusted for current macro/sector context);  
• volatility scaling (the standard deviation gives a reference range);  
• tail risk (outlier analysis shows how extreme spreads can get in 10 trading days).

Consequently, producing the missing statistics is not an optional refinement but a pre-requisite for any evidence-based forecast.

Feasibility of closing the gap

All technical barriers appear low:

• Yahoo Finance and Barchart both allow free CSV exports; nothing in the terms of service blocks academic-style offline analysis.  
• Open-source Python/R libraries (yfinance, pandas-datareader, quantmod, etc.) handle download and return calculations in under 50 lines of code.  
• Back-adjustment of contract rolls is already embedded in the continuous tickers supplied by Yahoo Finance and Barchart; further manual adjustment is usually unnecessary for percentage-return measures.  
• A full 15-year daily file is < 1 MB per symbol, well within spreadsheet or scripting limits.

Conclusion

The research to date verifies that (a) the necessary data exist in the public domain and (b) no published source has yet computed the requested 10-day NQ–ES return-spread statistics. However, because the historical price series themselves have not been extracted and processed, every numeric output demanded in the original query remains unknown. Procuring those two daily close series and running a simple rolling-window calculation is still required before the query can be fully satisfied.

No additional literature search will bridge this gap; only data retrieval and computation will.</Agent_report>


The information has been sourced from the internet and language models (for agent reports). Exercise healthy skepticism toward unverified claims.

Your analysis should have the following components, referring to the above historical context:
(a) Source analysis: Briefly summarize each information source (either web article or Agent report), evaluate source quality and date.
**Opinions are commonplace in writing. For each source, you must be able to discern factual information from opinions. You are advised to strongly consider only opinions originating from identifiable experts or entities**.
(b) Reference class analysis: Identify a few possible reference classes and evaluate respective suitabilities to the forecasting question. If applicable, choose the most suitable one.
(c) Timeframe analysis: State the prediction timeframe (e.g., how many days/months from now?) and examine historical patterns over similar periods
(d) Justification: Integrate the above factors with other points you found relevant to write a justification for your outside view prediction.

Subsequently, calibrate your outside view prediction, considering:
(a) You aim to predict a true probability distribution, not a hedged smooth distribution or an overconfident extremely narrow distribution. In your thinking, always consider ranges over singular values.
(b) Are there previously established distributions that you can tether your prediction to?
(c) Small changes in percentile values can significantly reshape the distribution, especially near the tails. Choose tail values carefully.
(d) Historically, what is the rate of upsets/unexpected outcomes in the domain of this forecasting question? How should this affect your CDF distribution?

Set wide 10th/90th percentile intervals to account for unknown unknowns.

**CRITICAL: Percentile values MUST be strictly increasing** (10th = lowest, 90th = highest).
Use the units requested by the question. Never use scientific notation.

Format your answer as below:

Analysis:
{Insert your analysis here, following the above components.}

Outside view calibration:
{Insert your calibration of your outside view prediction here.}

Outside View Prediction:
Percentile 10: XX
Percentile 20: XX
Percentile 40: XX
Percentile 60: XX
Percentile 80: XX
Percentile 90: XX
