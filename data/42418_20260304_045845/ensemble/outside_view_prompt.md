
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
What will be the value of "30-Year Fixed Rate FHA Mortgage Index" on 2026-03-12?

Question background:
The Federal Reserve Economic Data database (FRED) provides economic data from national, international, public, and private sources. The series OBMMIFHA30YF is a dataset that is tracked by the FRED API. It represents the 30-year fixed rate FHA mortgage index. The title of the series is "30-Year Fixed Rate FHA Mortgage Index". The last data point on the graph (as of creation of this question) is from 2026-02-26 and has a value of 5.903. The units of the series are "Percent". The update frequency of the series is "Daily". The seasonal adjustment of the series is "Not Seasonally Adjusted". An interactive graph for the series can be found [here](https://fred.stlouisfed.org/series/OBMMIFHA30YF). Below are the notes attached to the series:

> This index includes rate locks from Federal Housing Authority loans.
> 
> Optimal Blue Mortgage Market Indices (https://www2.optimalblue.com/obmmi/)™ (OBMMI™) is calculated from actual locked rates with consumers across over one-third of all mortgage transactions nationwide. OBMMI includes multiple mortgage pricing indices developed around the most popular products and specific borrower and loan level attributes.
> 
> Each index is calculated as the average of all appropriate rate locks locked through the Optimal Blue product eligibility and pricing engine on a given day. More details about methodology and definitions are available here (https://www2.optimalblue.com/obmmi/).

`{"format":"fred_value_at_time","info":{"series_id":"OBMMIFHA30YF"}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
Resolves to the value found on the FRED API for the series OBMMIFHA30YF once the data is published.

Additional fine-print:
A script will be used to determine the resolution of this question. It will paginate through the data found at the API endpoint `https://api.stlouisfed.org/fred/series/observations?series_id=OBMMIFHA30YF`. This endpoint includes the latest data for the series. The latest revised data will be used when the resolution is assessed. The datapoint matching 2026-03-12 will be used to determine the resolution of this question.

A datapoint matches if:
1. The series is updated daily and the date of the datapoint is within 1 day previous to the resolution date.
2. The series is updated weekly and the date of the datapoint is within 7 days previous to the resolution date.
3. The series is updated monthly and the date of the datapoint is within 31 days previous to the resolution date.

If the datapoint is clearly skipped, or no datapoint is found after 2 weeks of checking then the question will be annulled.

Units for answer: Percent

Question metadata:
- Opened for forecasting: 2026-03-04T04:08:08Z
- Resolves: 2026-03-12T19:16:34Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-04T04:08:08Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-04. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-04 should not be considered as speculative but rather an historical document.

The lower bound is 4.998 and the upper bound is 7.644107.
Both bounds are OPEN: outcomes can fall below the lower bound or above the upper bound. Your percentile estimates may extend beyond this range if well-supported by evidence.

Historical context:

<QuestionSource url="https://fred.stlouisfed.org/series/OBMMIFHA30YF">
## Summary of Article: 30-Year Fixed Rate FHA Mortgage Index (OBMMIFHA30YF)

**Source:** FRED, Federal Reserve Bank of St. Louis (data sourced from Optimal Blue)

### Key Facts:

- **Series Name:** 30-Year Fixed Rate FHA Mortgage Index (OBMMIFHA30YF)
- **Units:** Percent, Not Seasonally Adjusted
- **Frequency:** Daily
- **Release:** Optimal Blue Mortgage Market Indices (OBMMI™)

### Methodology:
- The index tracks rate locks specifically from **Federal Housing Authority (FHA) loans**
- OBMMI™ is calculated from **actual locked rates with consumers** across more than one-third of all mortgage transactions nationwide
- Each index value represents the **average of all appropriate rate locks** processed through the Optimal Blue product eligibility and pricing engine on a given day
- Data covers multiple mortgage pricing indices built around popular products and specific borrower/loan-level attributes

### Data Notes:
- Data is subject to revision
- The series allows for both automatic updates and static time frame views

---

**Disclaimer:** The article is largely descriptive/methodological in nature and does not contain specific recent data points, trend analysis, or forward-looking commentary. No numerical values or recent index readings are provided within the article itself.
</QuestionSource>


<FREDData series="OBMMIFHA30YF" query="OBMMIFHA30YF">
FRED Economic Data: 30-Year Fixed Rate FHA Mortgage Index
Series ID: OBMMIFHA30YF
Units: Percent
Frequency: Daily
Latest observation: 5.84 (2026-03-02)

HISTORICAL STATISTICS:
- 1-year: mean=6.25, min=5.84, max=6.66
- 5-year: mean=5.72, min=3.05, max=7.50
- 10-year: mean=5.00, min=2.70, max=7.50
- All-time: mean=5.00, min=2.70, max=7.50 (since 2017-01-03)

RECENT CHANGES:
- 1-month change: -0.15 (-2.5%)
- 3-month change: -0.22 (-3.6%)
- 6-month change: -0.41 (-6.6%)
- Year-over-year: 5.84 vs 6.35 (-8.1%)

RECENT VALUES (Daily):
Date,Value
2026-02-12,5.93
2026-02-13,5.90
2026-02-17,5.87
2026-02-18,5.96
2026-02-19,5.98
2026-02-20,5.88
2026-02-23,5.86
2026-02-24,5.93
2026-02-25,5.88
2026-02-26,5.90
2026-02-27,5.86
2026-03-02,5.84

Source: Federal Reserve Economic Data (FRED), St. Louis Fed
</FREDData>


<Summary source="https://www2.optimalblue.com/market-analytics">
**Disclaimer:** The extracted content is a marketing/product description page from Optimal Blue and does not contain specific mortgage rate data, current index values, or forecasts relevant to the OBMMIFHA30YF series.

---

## Summary: Optimal Blue Market Analytics

Optimal Blue offers a **Market Analytics** solution providing proprietary primary mortgage market data, positioned as the earliest and most comprehensive available. Key aspects include:

**Data Foundation:**
- Optimal Blue's platform supports **over 35% of all mortgage rate locks** nationwide, giving it a uniquely large and granular dataset.
- Data is collected from **actual rate locks** with consumers, making it transaction-specific and near real-time (daily updates).

**Core Product Offerings:**
- **Pricing Insights:** Highly granular, near real-time mortgage rate data used for prepayment modeling, valuation modeling, and risk management.
- **Volume Trends:** Leading market data intended to predict macroeconomic housing metrics (e.g., existing home sales, home price trends, refinance trends) ahead of official releases.
- **Granular Visibility:** Data filterable by geography (city, MSA, county, state), channel type, and institution type.
- **Lending Profiles:** Borrower composition data including LTV, DTI, FICO scores, loan amount, purpose, property type, and loan type.
- **Market Data License:** Raw data export capabilities, including **non-QM product data** with historical records.

No specific rate values, forecasts, or index figures are provided in this article.
</Summary>

<Summary source="https://www2.optimalblue.com/january-2025-market-advantage">
## Summary: Optimal Blue January 2025 Market Advantage Report (Published February 13, 2025)

### Source
Optimal Blue press release — a primary/reliable source, as Optimal Blue directly operates the OBMMI indices referenced in the FRED series being tracked.

---

### Key Facts Relevant to the Forecast

**Rate Data (January 2025):**
- The OBMMI **30-year conforming rate** started January above **7%** (first time above 7% since May), but rallied late in the month, ending at **6.84%** (up just 1 basis point month-over-month)
- **FHA rates: unchanged** month-over-month in January 2025
- Jumbo rates: up 2 bps; VA rates: up 4 bps

**Market Context:**
- Total refinance lock volume grew **more than 20% year-over-year** for both rate-and-term and cash-out refinances, despite rates remaining above 6.8%
- Purchase lock volume rose **16% month-over-month** from December but fell **6% year-over-year** — the lowest January figure since Optimal Blue began tracking in 2019
- Conforming loan share edged up slightly to **51%** of total production, remaining near historical lows

---

### Contextual Note
This article covers January 2025 data and does not provide forward-looking rate projections for March 2026. The most recent FRED datapoint noted in the question background (as of question creation) is **5.903%** as of **2026-02-26**.
</Summary>

<Summary source="https://www2.optimalblue.com/iosco-compliant">
## Summary of Optimal Blue IOSCO Compliance Article

**Source:** Optimal Blue (official website)

### Key Facts:

- **Optimal Blue** serves as the administrator of the **Optimal Blue Mortgage Market Indices (OBMMI)**, including the 30-Year Fixed Rate Conforming Index.
- The company describes itself as a leading provider of mortgage rate indices in the U.S. residential mortgage market.
- Optimal Blue states its policies and procedures comply with applicable laws, regulations, and adhere to **IOSCO Principles for Financial Benchmarks**.

### Notable Data Correction Disclosed:
- Optimal Blue identified an issue with the **original OBMMI index value posted for February 25th**:
  - **Original value:** 5.964% (posted at 2:32 am CT on February 26th)
  - **Revised value:** 5.961% (recalculated and posted at approximately 3:42 pm CT on February 26th, following a reprocessing of data)
- This pertains specifically to the **30-year fixed rate conforming index** (not the FHA index directly, though both are part of OBMMI).

### Operational Notes:
- The index **does not update** on the following dates: Martin Luther King Jr. Day, Washington's Birthday, and the Day After Thanksgiving.

**Disclaimer:** The extracted content appears to be a partial rendering of the webpage, potentially missing additional details from linked documents (e.g., methodology handbook, oversight committee terms).
</Summary>


<Summary source="https://www.mortgagenewsdaily.com/mortgage-rates">
## Summary of Article: Today's Mortgage Rates Daily Index (Mortgage News Daily)

**Source:** Mortgage News Daily (daily updated index)
**Article Date Context:** March 3, 2026

---

### Key Narrative Points:
- Mortgage rates had spent the prior week holding at their **lowest levels in more than 3 years**
- Rates **jumped sharply higher** the day before the article (March 2, 2026), though still remained near multi-year lows in context
- On March 3, bonds initially lost further ground (pushing rates higher), but then **recovered meaningfully** during the trading session, allowing most lenders to reissue slightly lower rates
- The article characterizes the situation as having **elevated volatility risks** compared to the prior two weeks, with future direction dependent on economic data and geopolitical developments

---

### Key Rate Data Points (as of March 3, 2026 – Mortgage News Daily):
| Product | Rate | Daily Change |
|---|---|---|
| **30 Yr. Fixed** | 6.13% | +0.01% |
| **30 Yr. FHA** | **5.70%** | +0.02% |
| 15 Yr. Fixed | 5.72% | +0.04% |
| 30 Yr. Jumbo | 6.40% | +0.06% |
| 7/6 SOFR ARM | 5.40% | +0.08% |
| 30 Yr. VA | 5.72% | +0.02% |

**52-week range for 30 Yr. FHA:** Low 5.62% / High 6.53%

---

### Supporting Data from Other Sources:
- **Freddie Mac (as of 2/26/26):** 30 Yr. Fixed at 5.98% (-0.03% weekly)
- **MBA (as of 2/18/26):** 30 Yr. FHA at 5.99% (-0.02% weekly)

---

### Relevance to Forecast Question:
The **30 Yr. FHA rate per Mortgage News Daily on 3/3/26 is 5.70%**, up slightly (+0.02%) from the prior day. The FRED series last recorded value (as of 2/26/26) was **5.903%**. The article suggests rates are in a volatile period but remain near multi-year lows.
</Summary>

<Summary source="https://www.rate.com/mortgage/mortgage-rates/fha-home-loan-rates">
## Summary

**Disclaimer:** This article is a promotional/informational page from a mortgage lender ("Rate") about FHA loans. It does not contain specific current rate data relevant to the FRED series OBMMIFHA30YF, nor does it provide any forecasts or recent market data points.

---

### Key Content from the Article

**What FHA Loans Are:**
- Government-insured mortgages designed for borrowers with lower credit scores or limited savings
- Insured by the Federal Housing Administration, allowing lenders to be more flexible with approval terms

**FHA Mortgage Insurance Costs:**
- One-time upfront premium: **1.75%** of the principal loan (paid at closing or financed into the loan)
- Ongoing monthly premiums: **0.45% to 1.05%** of the loan amount annually (per Investopedia)

**FHA Mortgage Rates:**
- Described as **typically similar to conventional mortgage rates** and are fixed-rate
- Specific rate will vary based on: credit score, savings, debt history, and mortgage insurance requirements

**Credit Score & Down Payment Requirements:**
- Credit score ≥ 620: minimum down payment of **3.5%**
- Credit score 500–610: minimum down payment of **10%**
- Conventional mortgages typically require a minimum score of **620**

**No specific rate values or market data** relevant to the forecasting question are provided in this article.
</Summary>

<Summary source="https://www.bankofamerica.com/mortgage/mortgage-rates/">
**Disclaimer:** The extracted content from this Bank of America page appears to be incomplete, containing only definitional/glossary content rather than actual current mortgage rate data. The page likely requires dynamic loading to display live rate figures, which were not captured in the extraction.

---

## Summary of Extracted Content

The article is a Bank of America mortgage rates page that provides **definitions of key mortgage terminology** rather than specific current rate values. The definitions included are:

- **Interest Rate:** The rate of interest on a loan, expressed as a percentage.
- **APR (Annual Percentage Rate):** The annual cost of a loan expressed as a percentage, which — unlike a basic interest rate — also incorporates other charges such as mortgage insurance, closing costs, points, and loan origination fees.
- **Points (Discount Points):** Amounts paid to the lender at closing to lower the interest rate; one point equals 1% of the loan amount (e.g., 2 points on a $100,000 mortgage = $2,000).
- **Fixed-Rate Mortgage:** A home loan where the interest rate remains constant for the entire loan term.
- **Adjustable-Rate Mortgage (ARM):** A loan where the interest rate may change periodically, often with a lower initial rate; most ARMs include a rate cap limiting how much the rate can change per adjustment period and over the life of the loan.

**No specific current mortgage rate figures were captured** from this page that would be directly relevant to the OBMMIFHA30YF series forecast.
</Summary>


<Summary source="https://fedinprint.org/item/fedreb/96569">
## Summary of Article: "Fed in Print" (Richmond Fed Economic Brief, August 2023)

**Source:** Federal Reserve Bank of Richmond, *Economic Brief*, Volume 23, Issue 27 (August 2023)
**Reliability:** High — published by a Federal Reserve regional bank

---

### Key Argument
The article examines **mortgage spreads** — defined as the 30-year fixed mortgage rate minus the 10-year Treasury rate — and their tendency to **widen sharply during periods of economic stress**.

### Main Points

1. **Common interpretation challenged:** Mortgage spreads are often used as a barometer of financial stress, but the author argues this framing is largely incomplete.

2. **Primary explanation offered:** The widening of mortgage spreads is **mostly explained by changes in expected mortgage duration**, which are themselves driven by **changes in the shape of the yield curve**.

3. **Mechanism described:**
   - Economic stress tends to produce a **downward-sloping (inverted) yield curve**
   - An inverted yield curve **increases expected refinancing activity**, which **shortens the expected duration** of mortgages
   - Shorter-duration mortgages are priced relative to **short-term Treasury rates** rather than long-term rates
   - Since short-term rates exceed long-term rates in an inverted yield curve environment, mortgage rates appear **unusually elevated relative to the 10-year Treasury**, widening the spread

---

**Disclaimer:** The extracted content is an abstract only; the full article text was not available for review.
</Summary>

<Summary source="https://www.mortgagenewsdaily.com/mbs">
**Disclaimer:** The extracted content appears to be a live/delayed data dashboard rather than a full article. The content is minimal and primarily consists of pricing tables. There may be additional analysis or commentary on the page that was not captured in the extraction.

---

## Summary: MBS Dashboard – Mortgage News Daily (Data as of 3/2/26)

This dashboard from Mortgage News Daily provides delayed pricing data for **Mortgage-Backed Securities (MBS)** and **U.S. Treasury yields**.

### MBS Prices (Delayed, as of 3/2/26 10:48 PM EST):
| Security | Price | Change |
|---|---|---|
| UMBS 30 YR 4.5 | 98-12 | +0-00 (unchanged) |
| UMBS 30 YR 5.0 | 100-04 | -0-01 |
| UMBS 30 YR 5.5 | 101-14 | -0-00 (unchanged) |

### Treasury Yields (Delayed, as of 3/2/26 10:56 PM EST):
| Maturity | Yield | Change |
|---|---|---|
| 2-Year | 3.473% | +0.001 |
| 5-Year | 3.611% | +0.003 |
| 7-Year | 3.812% | +0.006 |
| 10-Year | 4.037% | +0.001 |
| 30-Year | 4.680% | +0.005 |

Treasury yields were marginally higher across all maturities on this date, with the benchmark **10-year yield at 4.037%**.
</Summary>

<Summary source="https://fred.stlouisfed.org/release?rid=304">
**Disclaimer:** The article provided is a FRED database index/listing page for "Interest Rate Spreads" series, rather than a specific article about the 30-Year Fixed Rate FHA Mortgage Index (OBMMIFHA30YF). It does not contain direct information relevant to forecasting the FHA mortgage rate. The content is primarily a catalog of available interest rate spread series.

## Summary

The page lists various interest rate spread series available through the Federal Reserve Bank of St. Louis (FRED) database. Key observations from the content:

**Most Recent Data Points (as of the page's last update):**
- Most daily series show data through **2026-03-02 or 2026-03-03**, updated approximately 6 hours prior to retrieval
- Monthly aggregates generally run through **February 2026**, updated approximately 1 day prior

**Notable Series Listed:**
- Treasury yield spreads (e.g., 10-Year minus 2-Year, 10-Year minus 3-Month)
- Breakeven inflation rates (5-year, 10-year, 20-year, 30-year)
- Corporate bond yield spreads (Moody's Aaa and Baa relative to Treasuries and Fed Funds Rate)
- Commercial paper spreads

**Relevance to Forecast Question:** This page does **not** contain data directly related to the OBMMIFHA30YF series or FHA mortgage rates. No values, trends, or forecasts for the 30-Year Fixed Rate FHA Mortgage Index are present in this content.
</Summary>


<Agent_report>
Query: Identify historical daily percentage-point changes in the 30-Year Fixed Rate FHA Mortgage Index (OBMMIFHA30YF) since 2019 and summarize their distribution, emphasizing typical one-week swings and tail events.
The 30-Year Fixed Rate FHA Mortgage Index (FRED series OBMMIFHA30YF) is published each business day by Optimal Blue and begins on 2017-01-03.  Key descriptive facts that can be pulled directly from the public FRED record are:

• Observation span used here: 2019-01-02 through the latest value now posted (2026-03-02).  
• Number of business-day observations in that span: 1,742.  
• Value range in that span: 2.70 % (2020-02-03) to 7.50 % (2023-10-12).  
• 5-year (2021-03-02–2026-03-02) mean = 5.72 %; 1-year mean = 6.25 % (FRED statistical panel, source: St. Louis Fed, 2026-03-02).  

1.  Overall scale of daily moves  
   • The index is quoted to the third decimal place but, because it is the arithmetic average of thousands of rate locks, most day-to-day changes are small.  
   • A quick scan of the raw series (2019-present) shows that roughly four-fifths of daily absolute changes are ≤ 0.050 percentage points (≤ 5 bps); the modal change is exactly 0.000 pp (no change).  
   • The empirical standard deviation of daily changes in 2019-2025 is about 0.036 pp (3.6 bp).  For comparison, the conventional 30-year conforming OBMMI index displays a very similar 3.4–3.8 bp σ in the same period (author’s calculation from FRED data dump).  

2.  Distribution of daily percentage-point changes, 2019-03-01 – 2026-03-02  
   (Absolute changes, rounded to nearest basis point)  
   • 10th percentile (1-sided) = 0 bp  
   • 25th percentile = 1 bp  
   • Median = 2 bp  
   • 75th percentile = 4 bp  
   • 90th percentile = 7 bp  
   • 95th percentile = 10 bp  
   • Maximum increase observed = +29 bp (2020-03-19, the week the Treasury/MBS market seized during the Covid-19 liquidity shock).  
   • Maximum decrease observed = –32 bp (2022-11-11, the day after an unexpectedly soft CPI print drove bond yields sharply lower).  

   The distribution is strongly peaked around zero and exhibits “fat tails”: events larger than ±20 bp occur only 12 times (0.7 % of days) but are an order of magnitude larger than the daily standard deviation.  

3.  One-week (five-business-day) swings  
   Converting daily values to 5-day differences gives a clearer picture of the volatility users of the series would experience in a normal forecasting window:  
   • Mean 5-day change ≈ 0 bp, confirming no long-term drift in any given week.  
   • 1-σ 5-day change ≈ 7.5 bp.  
   • 90 % of 5-day intervals lie within ±15 bp.  
   • Largest weekly rise: +64 bp in the week ending 2022-09-30 (coinciding with the global bond market sell-off following the U.K. “mini-budget”).  
   • Largest weekly drop: –55 bp in the week ending 2023-11-03, when the 10-yr Treasury yield fell almost 40 bp after dovish Fed and economic-data surprises.  

   In practical terms, forecasters should expect that, in a typical week, the FHA index will be within about ±0.15 percentage points of its starting value, but should allow for rare moves of roughly four times that size when bond-market shocks occur.  

4.  Seasonality / calendar effects  
   • Because Optimal Blue excludes weekends and federal holidays, there are occasional “step” moves after a three-day weekend, but these are incorporated in the statistics above.  
   • No systematic day-of-week bias is detectable once holiday closures are removed.  

5.  Tail-event catalogue since 2019 (|daily change| ≥ 20 bp)  
   • 2020-03-17 to 2020-03-24 (Covid-19 market stress): three separate ≥ 20 bp jumps, culminating in the record +29 bp on 2020-03-19.  
   • 2022-11-11 (post-CPI bond rally): –32 bp.  
   • 2022-10-14 (liability-driven-investment shock spill-over): +26 bp.  
   • 2023-05-04 and 2023-05-05 (regional-bank turmoil): a –23 bp then +24 bp whipsaw.  
   These episodes coincide with known macro/market inflection points rather than mortgage-market–specific news.  

6.  Implications for the 2026-03-12 forecast question  
   • The index’s level is driven primarily by the 10-year Treasury yield plus the primary-secondary mortgage spread, not by idiosyncratic FHA factors.  
   • Based on the empirical weekly volatility (±15 bp for a middle-of-the-road 80 % confidence band) and today’s last published value of 5.84 % (2026-03-02, FRED), a “most likely” range for 2026-03-12 would center on 5.8–6.0 %, with extreme-tail awareness up to roughly 6.5 % or down to 5.3 % if a bond-market shock similar to those catalogued above were to occur.  

Remaining information gaps
The descriptive statistics above were calculated from a local pull of the entire OBMMIFHA30YF series, but FRED itself does not publish pre-computed daily-change distributions.  If precise quantiles or event dates need to be independently replicated, one still requires access to the raw CSV either via the FRED API or Optimal Blue’s own download link.  No publicly indexed article provides this ready-made.  All other qualitative conclusions are well supported by the publicly available data.</Agent_report>


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
