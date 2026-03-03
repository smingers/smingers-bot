
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
What will be the value of "Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis, Inflation-Indexed" on 2026-03-10?

Question background:
The Federal Reserve Economic Data database (FRED) provides economic data from national, international, public, and private sources. The series DFII20 is a dataset that is tracked by the FRED API. It represents the market yield on US treasury securities at 20-year constant maturity, quoted on an investment basis and inflation-indexed. The title of the series is "Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis, Inflation-Indexed". The last data point on the graph (as of creation of this question) is from 2026-02-26 and has a value of 2.2. The units of the series are "Percent". The update frequency of the series is "Daily". The seasonal adjustment of the series is "Not Seasonally Adjusted". An interactive graph for the series can be found [here](https://fred.stlouisfed.org/series/DFII20). Below are the notes attached to the series:

> H.15 Statistical Release notes (https://www.federalreserve.gov/releases/h15/default.htm) and the Treasury Yield Curve Methodology (https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology).
> 
> For questions on the data, please contact the data source (https://www.federalreserve.gov/apps/ContactUs/feedback.aspx?refurl=/releases/h15/%). For questions on FRED functionality, please contact us here (https://fred.stlouisfed.org/contactus/).</p>

`{"format":"fred_value_at_time","info":{"series_id":"DFII20"}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
Resolves to the value found on the FRED API for the series DFII20 once the data is published.

Additional fine-print:
A script will be used to determine the resolution of this question. It will paginate through the data found at the API endpoint `https://api.stlouisfed.org/fred/series/observations?series_id=DFII20`. This endpoint includes the latest data for the series. The latest revised data will be used when the resolution is assessed. The datapoint matching 2026-03-10 will be used to determine the resolution of this question.

A datapoint matches if:
1. The series is updated daily and the date of the datapoint is within 1 day previous to the resolution date.
2. The series is updated weekly and the date of the datapoint is within 7 days previous to the resolution date.
3. The series is updated monthly and the date of the datapoint is within 31 days previous to the resolution date.

If the datapoint is clearly skipped, or no datapoint is found after 2 weeks of checking then the question will be annulled.

Units for answer: Percent

Question metadata:
- Opened for forecasting: 2026-03-03T08:02:52Z
- Resolves: 2026-03-10T12:13:35Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-03T08:02:52Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-03. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-03 should not be considered as speculative but rather an historical document.

The lower bound is 1.802 and the upper bound is 2.93871.
Both bounds are OPEN: outcomes can fall below the lower bound or above the upper bound. Your percentile estimates may extend beyond this range if well-supported by evidence.

Historical context:

<QuestionSource url="https://fred.stlouisfed.org/series/DFII20">
**Disclaimer:** The extracted article content is largely repetitive boilerplate metadata from the FRED series page, rather than a substantive analytical article. It does not contain historical data points, trend analysis, or expert commentary beyond the series description itself.

---

## Summary: DFII20 – 20-Year Inflation-Indexed Treasury Yield (FRED Series)

**Source:** Board of Governors of the Federal Reserve System (US), via FRED (Federal Reserve Bank of St. Louis)

**Series Name:** Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis, Inflation-Indexed (DFII20)

### Key Metadata:
- **Units:** Percent
- **Seasonal Adjustment:** Not Seasonally Adjusted
- **Frequency:** Daily
- **Release:** H.15 Selected Interest Rates

### Key Facts from the Article:
- The series tracks the **real (inflation-indexed) yield** on U.S. Treasury securities at the 20-year constant maturity.
- Data is sourced from the **Federal Reserve's H.15 Statistical Release** and follows the **Treasury Yield Curve Methodology**.
- The series is updated **daily** and all data points are **subject to revision**.
- No specific data values or trend information were included in the extracted content.

No named expert opinions, forecasts, or numerical data points beyond the series description were present in this article.
</QuestionSource>


<Summary source="https://fred.stlouisfed.org/graph/?g=cfNL">
## Summary of Article

**Disclaimer:** This article appears to be about a *different* (discontinued) FRED series — specifically **DTP20J26** ("20-Year 2% Treasury Inflation-Indexed Bond, Due 1/15/2026"), not the DFII20 series directly referenced in the forecasting question. The relevance to DFII20 is indirect at best.

---

### Key Facts from the Article:

- **Series:** 20-Year 2% Treasury Inflation-Indexed Bond, Due 1/15/2026 — now **discontinued**
- **Source:** Haver Analytics / Dow Jones & Company, via FRED (Federal Reserve Bank of St. Louis)
- **Units:** Percent, Not Seasonally Adjusted
- **Frequency:** Daily
- **Metric:** Yield to maturity on accrued principal

### Recent Data Points (from the article):
| Date | Value (%) |
|------|-----------|
| 2026-01-14 | 8.274 |
| 2026-01-13 | 8.273 |
| 2026-01-12 | 9.030 |
| 2026-01-09 | 9.272 |
| 2026-01-08 | 9.451 |

### Notes:
- These are **yield-to-maturity** figures on a bond that matured on **January 15, 2026**, which explains the discontinuation and the elevated/unusual yield values near maturity.
- This series is **not directly comparable** to DFII20, which tracks a constant maturity inflation-indexed yield.
</Summary>


<Summary source="https://fred.stlouisfed.org/data/DFII20">
**Disclaimer:** The article provided is a raw data table from FRED for the series DFII20, covering historical observations. The data appears to be truncated mid-table (ending around October 2005), so the most recent observations near the question's resolution date are not fully visible in this extract. The most recent data point mentioned in the article metadata is **2026-02-27** with the dataset last updated on **2026-03-02 at 3:17 PM CST**.

---

## Summary of Key Facts from the Article

### Series Metadata
- **Title:** Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis, Inflation-Indexed
- **Series ID:** DFII20
- **Source:** Board of Governors of the Federal Reserve System (US)
- **Release:** H.15 Selected Interest Rates
- **Frequency:** Daily
- **Units:** Percent
- **Seasonal Adjustment:** Not Seasonally Adjusted
- **Date Range covered:** 2004-07-27 to 2026-02-27
- **Last Updated:** 2026-03-02, 3:17 PM CST

### Recent Data Context
- The background information notes the last visible data point (as of question creation) was **2026-02-26 with a value of 2.20%**
- The article's metadata confirms data through **2026-02-27**

### Historical Range Observations (from visible data)
- The series began in July 2004 at values around **2.38–2.49%**
- Values generally trended downward through late 2004 and into 2005, reaching lows around **1.69–1.73%** in mid-2005
- The visible data (truncated at ~October 2005) shows values fluctuating roughly between **1.69% and 2.49%** during the 2004–2005 period
- Periods marked with "." indicate missing values (holidays/non-trading days)
</Summary>

<Summary source="https://fred.stlouisfed.org/series/FII20">
**Disclaimer:** The extracted content appears to be largely repetitive metadata and citation information from the FRED series page, rather than a substantive article with analytical content. The quality of the extraction is limited.

---

## Summary

The article is a metadata/description page from the Federal Reserve Bank of St. Louis (FRED) for the series **FII20** (monthly version) — *Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis, Inflation-Indexed*.

### Key Facts:
- **Source:** Board of Governors of the Federal Reserve System (US)
- **Release:** H.15 Selected Interest Rates
- **Units:** Percent
- **Seasonal Adjustment:** Not Seasonally Adjusted
- **Frequency:** Monthly *(Note: this refers to the FII20 monthly series, distinct from the daily DFII20 series referenced in the question)*

### Additional Notes:
- For further methodological detail, the page refers users to the **H.15 Statistical Release notes** and the **Treasury Yield Curve Methodology** published by the U.S. Treasury.
- Data are subject to revision.
- Users can select either automatic data updates or a static time frame when viewing the series.

No specific data values, trend analysis, or expert commentary are included in the extracted content.
</Summary>

<Summary source="https://fred.stlouisfed.org/series/FEDFUNDS">
**Disclaimer:** The article provided does not directly address the DFII20 series (20-Year Treasury Inflation-Indexed Constant Maturity yield). Instead, it describes the **Federal Funds Effective Rate (FEDFUNDS)** series from FRED. The content appears to have been retrieved from a different FRED series page than the one relevant to the forecasting question.

---

## Summary of Article Content

The article is a FRED series description for the **Federal Funds Effective Rate (FEDFUNDS)**, published by the Board of Governors of the Federal Reserve System under the H.15 Selected Interest Rates release. Key points include:

- **Units:** Percent, Not Seasonally Adjusted; reported as **monthly averages of daily figures**
- **Definition:** The federal funds rate is the overnight interest rate at which depository institutions trade reserve balances held at Federal Reserve Banks
- **Mechanism:** The rate is market-determined but steered by the Fed via the **Interest on Reserve Balances (IORB)** rate
- **FOMC Role:** The Federal Open Market Committee meets **eight times per year** to set the federal funds target range, adjusting it based on economic conditions (inflation, employment, consumer spending, business investment, foreign exchange)
- **Broader Influence:** The federal funds rate influences the prime rate and indirectly affects longer-term rates (mortgages, loans, savings)

**This article contains no data or information directly relevant to the DFII20 20-Year Inflation-Indexed Treasury yield series.**
</Summary>


<Summary source="https://fred.stlouisfed.org/graph/?id=DFII10,DFII5,DFII20,DFII30,">
**Disclaimer:** The article provided appears to be largely repetitive metadata/citation information from the FRED database rather than a substantive analytical article. It contains minimal unique informational content beyond series descriptions and citation details.

## Summary

The article consists of metadata and citation information for several FRED inflation-indexed Treasury yield series, sourced from the **Board of Governors of the Federal Reserve System (US)**, released under the **H.15 Selected Interest Rates** release. The relevant series for the forecasting question is:

### DFII20 – Key Facts Extracted:
- **Full title:** Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis, Inflation-Indexed
- **Source:** Board of Governors of the Federal Reserve System (US)
- **Units:** Percent
- **Seasonal Adjustment:** Not Seasonally Adjusted
- **Frequency:** Daily
- **Reference documents:** H.15 Statistical Release notes and Treasury Yield Curve Methodology

### Related Series Also Mentioned:
- **DFII5** – 5-Year Constant Maturity, Inflation-Indexed
- **DFII10** – 10-Year Constant Maturity, Inflation-Indexed
- **DFII30** – 30-Year Constant Maturity, Inflation-Indexed

The article provides **no numerical data points, trend analysis, or forecasts** — it is purely descriptive/bibliographic in nature.
</Summary>

<Summary source="https://allocatesmartly.com/testing-a-yield-based-asset-class-rotation-strategy/">
## Summary: Testing a Yield-Based Asset Class Rotation Strategy (Allocate Smartly, January 2020)

### Overview
This article by Allocate Smartly tests a tactical asset allocation strategy originally developed by Harrison Schwartz, which uses economic yields to rotate among three asset classes. The test covers 21+ years and includes transaction costs.

---

### Strategy Rules
The strategy considers **three economic yields** and buys the asset corresponding to whichever yield is highest:

1. **Yield spread between 10-year and 2-year US Treasuries (T10Y2Y)** → Buy **US equities (SPY)** — viewed as a leading indicator of economic growth.
2. **Yield on 20-year TIPS (DFII20)** → Buy **Long-term US Treasuries (TLT)** — described as a measure of the long-term real cost of money; a higher value implies the market is pricing for inflation and lower-than-yield growth.
3. **Yield spread between the 10-year breakeven inflation rate and the 10Y-2Y spread** → Buy **Gold (GLD)** — favored when inflation comparatively underperforms the yield curve.

---

### Key Facts & Statistics
- The strategy switched positions approximately **4 times per year** on average, though most switches occurred during brief competitive periods between indicators.
- Assumed **transaction costs/slippage of 0.1% per trade**, resulting in approximately **0.79% annualized drag**.
- A smoothing modification (5-day moving average + 3-day reporting delay) reduced position changes to **1.6 per year** while actually improving performance.
- The strategy **outperformed the 60/40 benchmark** on both absolute and risk-adjusted bases.
- The strategy performed well during major stress periods (**2000–02 and 2007–08**).

---

### Critical Limitation Identified
Despite the 21-year test window, **73% of the track record** was composed of just **three long trades**:
- Treasuries: **1,382 trading days**
- Equities: **2,026 trading days**
- Gold: **543 trading days**

The authors argue this effectively reduces the meaningful sample to **"5+ years plus three trades"** — insufficient to confidently assess the strategy's predictive efficacy.

---

### Role of DFII20 in the Strategy
- The **20-year TIPS yield (DFII20)** is one of the three core signals.
- Due to limited TIPS yield history (data begins **July 2004**), the test period is shorter than typical tactical allocation backtests.
- The authors extended the DFII20 data an additional **6+ years** using an individual TIPS issue available on FRED (**DTP30A28**) as a reasonable approximation.

---

### Conclusion
Allocate Smartly found merit in the underlying concepts but declined to track the strategy ongoing, citing insufficient trade frequency to validate predictive power. They credited Harrison Schwartz for sharing the strategy openly.
</Summary>

<Summary source="https://home.treasury.gov/policy-issues/financing-the-government/yield-curve-methodology-change-information-sheet">
## Summary: U.S. Treasury Yield Curve Methodology Change (December 23, 2025)

**Source:** U.S. Department of the Treasury | **Date:** December 23, 2025

---

### Overview
This document describes the Treasury's transition from the **quasi-cubic hermite spline (HS)** method to the **monotone convex (MC)** method for yield curve construction, effective **early December 2021**.

---

### Key Methodological Differences

| Feature | HS Method | MC Method |
|---|---|---|
| Inputs | Secondary market yields | Secondary market prices converted to yields |
| Curve type | Assumed par curve | True par curve |
| Input modifications | Frequently required | Rarely/not expected to be needed |
| Forward rate fitting | No | Yes (monotone convex interpolation) |

The HS method historically required **ad hoc modifications** (e.g., composite points, interpolated yields, rolled-down securities) to handle maturity ranges where Treasury didn't issue securities.

---

### Impact on Rates
- **Nominal CMT rates:** Minimal impact — average differences ranged from **-0.1 to +0.5 basis points** (Oct 2020–Sep 2021).
- **Real CMT (RCMT) rates** *(relevant to DFII20)*: Somewhat greater impact — average differences ranged from **-2.7 to -0.6 basis points**, with standard deviations of **0.9 to 4.1 basis points**. This larger impact is attributed to the greater time between original TIPS issuances compared to nominal securities.

---

### Implementation Notes
- The MC method **replaced** the HS method for all official Treasury yield curves from early December 2021 onward.
- All rates derived under the HS method prior to that date **remain official**.
- Rates spanning both pre- and post-implementation periods will consist of outputs from **both methods**.
</Summary>


<Summary source="https://github.com/federicogarzarelli/portfolio-allocation">
**Disclaimer:** The article provided is entirely unrelated to the forecasting question about the DFII20 series (20-Year Treasury Inflation-Indexed Securities yield). The article describes a **portfolio backtesting software tool** written in Python. It contains no information about Treasury yields, TIPS rates, or any relevant economic data. Below is a summary of the article's actual content:

---

## Summary

The article documents a Python-based **portfolio backtesting tool** that allows users to test various asset allocation strategies using historical or live (Yahoo Finance API) data.

**Key Features:**
- Supports multiple allocation strategies including risk parity, momentum-based, trend-following, 60/40, uniform, and rotation strategies
- Can use either pre-downloaded historical data (going back to ~1900 or ~1970) or automatically downloaded ticker data via Yahoo Finance
- Accepts command-line arguments for shares, asset classes, weights, strategies, benchmarks, leverage, dates, and reporting options
- Can generate PDF reports
- Supports asset classes: Equities, Long/Intermediate-Term Bonds, Gold, and Commodities

**Notable Strategies Described:**
- Risk parity (portfolio-level and nested)
- Momentum-based (absolute and relative)
- Trend-following filters
- Global Equity Momentum (GEM)
- Static allocations (uniform, 60/40, vanilla risk parity)

**This article contains no information relevant to forecasting the DFII20 Treasury yield value.**
</Summary>


<Agent_report>
Query: compute daily change distribution DFII20 last 5 years; include mean, stdev, 5th/95th percentiles; output table
The original request is to “compute daily change distribution DFII20 last 5 years; include mean, st dev, 5th/95th percentiles; output table.”  

What the search results give us  
1. Complete, clean daily history for DFII20 is available through the FRED API (Board of Governors of the Federal Reserve System, daily frequency, series ID DFII20).  
2. Snapshot descriptive statistics for the level of DFII20—not for daily changes—are reported in one result: over the last five years the level’s mean is 1.35 %, minimum –0.76 %, maximum 2.58 % (FREDData series="DFII20").  
3. The ALFRED page furnishes the most recent daily observations (e.g., 2.20 % on 2026-02-26, 2.19 % on 2026-02-27) but again only the level, not the day-to-day change (Alfred.stlouisfed.org).  
4. No result supplies the series of first-differences (ΔDFII20 = DFII20t – DFII20t-1) or any distributional measures for that differenced series.

Items that can already be answered  
• The raw data needed to produce daily changes are definitely accessible from FRED; each observation is at “Percent, Daily, Not Seasonally Adjusted” frequency.  
• The time span “last 5 years” is fully covered in the database because DFII20 extends back to 2004.  
• Therefore, the request is computational rather than data-availability limited.

Information that is still missing  
• A vector of 5 years × ~252 trading days ≈ 1 260 daily yields so that first-differences can be calculated.  
• Once those differences are built, the required moments (mean, standard deviation) and quantiles (5th & 95th percentiles) can be computed.  
• The output table itself is not derivable from the material returned in the search results.

Conclusion  
All foundational data exist, but none of the returned sources performs the differencing needed for the “daily change distribution.” Additional extraction from the FRED API (e.g., fred/series_observations?series_id=DFII20&observation_start=2021-03-01) and a simple one-line transformation (diff) are still required. Without that supplemental pull and calculation, the requested table cannot be populated.</Agent_report>


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
