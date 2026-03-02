
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
What will be the value of "6-Month Treasury Bill Secondary Market Rate, Discount Basis" on 2026-03-12?

Question background:
The Federal Reserve Economic Data database (FRED) provides economic data from national, international, public, and private sources. The series DTB6 is a dataset that is tracked by the FRED API. It represents the Federal Reserve's 6-month secondary market treasury bill rate. The title of the series is "6-Month Treasury Bill Secondary Market Rate, Discount Basis". The last data point on the graph (as of creation of this question) is from 2026-02-26 and has a value of 3.53. The units of the series are "Percent". The update frequency of the series is "Daily". The seasonal adjustment of the series is "Not Seasonally Adjusted". An interactive graph for the series can be found [here](https://fred.stlouisfed.org/series/DTB6). Below are the notes attached to the series:

> data source (https://www.federalreserve.gov/apps/ContactUs/feedback.aspx?refurl=/releases/h15/%). For questions on FRED functionality, please contact us here (https://fred.stlouisfed.org/contactus/).</p>

`{"format":"fred_value_at_time","info":{"series_id":"DTB6"}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
Resolves to the value found on the FRED API for the series DTB6 once the data is published.

Additional fine-print:
A script will be used to determine the resolution of this question. It will paginate through the data found at the API endpoint `https://api.stlouisfed.org/fred/series/observations?series_id=DTB6`. This endpoint includes the latest data for the series. The latest revised data will be used when the resolution is assessed. The datapoint matching 2026-03-12 will be used to determine the resolution of this question.

A datapoint matches if:
1. The series is updated daily and the date of the datapoint is within 1 day previous to the resolution date.
2. The series is updated weekly and the date of the datapoint is within 7 days previous to the resolution date.
3. The series is updated monthly and the date of the datapoint is within 31 days previous to the resolution date.

If the datapoint is clearly skipped, or no datapoint is found after 2 weeks of checking then the question will be annulled.

Units for answer: Percent

Question metadata:
- Opened for forecasting: 2026-03-02T13:25:31Z
- Resolves: 2026-03-12T20:32:13Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-02T13:25:31Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-02. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-02 should not be considered as speculative but rather an historical document.

The lower bound is 2.958 and the upper bound is 4.7955.
Both bounds are OPEN: outcomes can fall below the lower bound or above the upper bound. Your percentile estimates may extend beyond this range if well-supported by evidence.

Historical context:

<QuestionSource url="https://fred.stlouisfed.org/series/DTB6">
**Disclaimer:** The extracted article content is largely metadata and citation information rather than substantive analytical content. It does not contain specific data points, trends, or forecasts beyond what is noted in the question's background information.

---

## Summary

The article is a FRED series page for **DTB6 – "6-Month Treasury Bill Secondary Market Rate, Discount Basis"**, published by the Federal Reserve Bank of St. Louis.

### Key Facts:
- **Source:** Board of Governors of the Federal Reserve System (US)
- **Release:** H.15 Selected Interest Rates
- **Units:** Percent
- **Seasonal Adjustment:** Not Seasonally Adjusted
- **Frequency:** Daily
- **Measurement Basis:** Discount Basis

### Notable Details:
- The series tracks the secondary market rate for 6-month U.S. Treasury Bills on a discount basis.
- Data is updated daily and is subject to revision.
- Users can select either automatic updates or a static time frame when viewing the data.
- For data-related questions, users are directed to the Federal Reserve's data source contact page; for FRED platform questions, a separate FRED contact page is provided.

The article itself contains no specific numerical data points, trend analysis, or forward-looking commentary beyond the series description and citation information.
</QuestionSource>


<Summary source="https://www.investing.com/rates-bonds/us-t-bill-c1-futures-historical-data">
**Disclaimer:** The extracted content from this article is extremely limited and does not contain substantive data relevant to the forecasting question. The article appears to be primarily a risk disclosure/legal disclaimer page from Investing.com related to US T-Bill Futures Historical Prices, with no actual historical price data, tables, or figures having been successfully extracted.

**Summary of Available Content:**

- The page is sourced from Investing.com, dated **February 27, 2026**, and is titled "US T-BILL Futures Historical Prices."
- The content retrieved consists almost entirely of a **standard risk disclosure statement** from Fusion Media (Investing.com's parent company), which warns that:
  - Trading financial instruments and cryptocurrencies carries high risk.
  - Data on the website is **"not necessarily real-time nor accurate."**
  - Prices may be provided by market makers rather than actual exchanges, and are described as **"indicative and not appropriate for trading purposes."**
  - Fusion Media disclaims liability for losses based on the site's information.

**No actual T-Bill futures price data, historical rates, or figures relevant to the 6-Month Treasury Bill Secondary Market Rate (DTB6) were captured in the extracted content.** The forecaster should seek the actual historical price table from the Investing.com page directly or consult the FRED API for relevant data points.
</Summary>

<Summary source="https://www.tradingview.com/symbols/FRED-DTB6/">
**Disclaimer:** The extracted content from this TradingView page is largely navigational/structural in nature, with minimal substantive data about the DTB6 series itself. The page appears to be a chart/data visualization page, and the actual historical data values and chart content were not captured in the extraction.

---

## Summary of Article: 6-Month Treasury Bill: Secondary Market Rate (FRED:DTB6) on TradingView

This TradingView page presents the **6-Month Treasury Bill Secondary Market Rate (DTB6)**, sourced from the **Federal Reserve**.

### Key Metadata Provided:
- **Category:** Money
- **Source:** Federal Reserve
- **Frequency:** Daily
- **Units:** Percent (%)

### Related Indicators Listed:
The page links DTB6 to a broader set of U.S. economic indicators, including:
- Effective Federal Funds Rate (USEFFR)
- Interbank Rate (USINBR)
- General Interest Rate (USINTR)
- Secured Overnight Financing Rate (USSECOFR)
- Proxy Funds Rate (USPFR)
- Repo Rate (USRR)
- Various money supply measures (M0, M1, M2)

### Notable Limitation:
No specific historical data points, trend descriptions, or analyst commentary were captured in the extraction. The page primarily serves as an **interactive chart interface**, and the underlying numerical data was not rendered in the extractable content.
</Summary>

<Summary source="https://fred.stlouisfed.org/series/DGS6MO">
**Disclaimer:** The extracted article content appears to be largely metadata and citation information rather than substantive analytical content. It does not contain specific data points, trend analysis, or forecasts. The article is primarily a description of the FRED data series **DGS6MO** (Market Yield on U.S. Treasury Securities at 6-Month Constant Maturity, Quoted on an Investment Basis), which is a **related but distinct series** from the question's target series **DTB6** (6-Month Treasury Bill Secondary Market Rate, Discount Basis).

---

## Summary

The article describes the FRED data series **DGS6MO**, published by the **Board of Governors of the Federal Reserve System (US)** as part of the **H.15 Selected Interest Rates** statistical release.

### Key Facts:
- **Units:** Percent, Not Seasonally Adjusted
- **Frequency:** Daily
- **Source:** Board of Governors of the Federal Reserve System (US)
- **Basis:** Investment Basis (as opposed to Discount Basis used in DTB6)
- For further methodology details, the series notes refer users to the **H.15 Statistical Release notes** and the **Treasury Yield Curve Methodology** documentation
- Data is subject to revision and can be retrieved with either automatic updates or static time frames

No specific numerical data points, trend information, or forecasts are provided in the article.
</Summary>


<Summary source="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_bill_rates&field_tdr_date_value=2026">
## Summary of Article: Treasury Rate Methodology and Series Notes

This article is primarily a **technical reference document** from the U.S. Treasury explaining the methodology and history behind various Treasury rate series. Key points relevant to the DTB6 (6-Month Treasury Bill Secondary Market Rate) question include:

### Daily Treasury Bill Rates (Most Relevant)
- These rates represent **daily secondary market quotations** on the most recently auctioned Treasury Bills across maturity tranches, including the **26-week (6-month)** bill
- Market quotations are obtained at approximately **3:30 PM each business day** by the Federal Reserve Bank of New York
- The **Bank Discount rate** (the basis for DTB6) is calculated based on par value, amount of discount, and a **360-day year**
- The Coupon Equivalent (Bond Equivalent/Investment Yield) is an alternative measure based on a 365/366-day year

### Treasury Par Yield Curve (CMT) Notes
- CMT yields are interpolated from daily par yield curves using a **monotone convex spline method**
- Inputs are indicative bid-side prices from the most recently auctioned nominal Treasury securities
- Negative yields are technically possible but the CMT series is **floored at zero**

### No Current Rate Data Provided
The article contains **no specific numerical rate values** for the 6-month T-bill as of any recent date, nor any forward-looking rate projections.
</Summary>

<Summary source="https://fred.stlouisfed.org/series/T6MFFM">
**Disclaimer:** The article content appears to be largely repetitive metadata/boilerplate from the FRED database rather than a substantive analytical article. The extracted content is limited in informational depth.

---

## Summary: 6-Month Treasury Constant Maturity Minus Federal Funds Rate (T6MFFM)

**Source:** Federal Reserve Bank of St. Louis (FRED), under the *Interest Rate Spreads* release.

**Key Facts:**
- **Series:** T6MFFM — "6-Month Treasury Constant Maturity Minus Federal Funds Rate"
- **Units:** Percent, Not Seasonally Adjusted
- **Frequency:** Monthly
- **Calculation Methodology:** The series represents the **spread** between two underlying FRED series:
  - 6-Month Treasury Constant Maturity rate (series: GS6M)
  - Effective Federal Funds Rate (series: FEDFUNDS)

**Relevance to DTB6 Question:**
This series is a *related but distinct* measure from DTB6. While DTB6 tracks the 6-Month Treasury Bill Secondary Market Rate on a discount basis (daily frequency), T6MFFM tracks the spread between the 6-month constant maturity rate and the federal funds rate on a monthly basis. The article provides no specific data points or forecasts relevant to the March 2026 resolution date.
</Summary>

<Summary source="https://www.federalreserve.gov/releases/h15/">
## Summary of Federal Reserve H.15 Selected Interest Rates (Daily)

**Source:** Board of Governors of the Federal Reserve System (federalreserve.gov), H.15 Selected Interest Rates release

### Key Data Point for DTB6 (6-Month Treasury Bill Secondary Market Rate, Discount Basis):

| Date | 6-Month T-Bill Rate |
|------|-------------------|
| Feb 20, 2026 | 3.52% |
| Feb 23, 2026 | 3.53% |
| Feb 24, 2026 | 3.53% |
| Feb 25, 2026 | 3.53% |
| Feb 26, 2026 | 3.53% |

### Broader Context from the Same Table:
- **Federal funds effective rate** held steady at **3.64%** across all five days shown
- **Bank prime loan rate** remained constant at **6.75%**
- **Discount window primary credit rate** held at **3.75%**
- **3-month T-bill (secondary market):** Consistently at **3.60%**
- **1-year T-bill (secondary market):** Ranged between **3.37–3.39%**

### Methodological Notes:
- Rates are annualized using a **360-day year** (discount basis)
- Data is sourced from the U.S. Treasury and Federal Reserve
- The 6-month T-bill rate showed minimal movement, stabilizing at **3.53%** for four consecutive days through Feb 26, 2026
</Summary>


<Agent_report>
Query: Compute 10-day ahead absolute and signed changes in DTB6 from 2010-01-01 to 2026-02-28; tabulate mean, std-dev, 25th/75th percentiles, and max moves.  Also retrieve conditional distributions around FOMC weeks and CPI-release weeks.  Provide results in a summary table.
The documentation returned by the new web search does three things:

1. It reconfirms that the raw inputs requested in the original query are readily obtainable.

• Complete DTB6 history – The FRED time-series “DTB6: 6-Month Treasury Bill Secondary Market Rate, Discount Basis” is continuously available from 1958-12-09 through at least 2026-02-26, the last observation displayed at 3.53 percent (FRED, series DTB6 – already cited in the previous memo).

• FOMC event calendar – The Board of Governors keeps a year-by-year archive of every two-day FOMC meeting. For example, the “FOMC historical 2010” page lists the 2010 meetings (Federalreserve.gov, fomchistorical2010.htm). Parallel pages exist for every subsequent year up to 2026, so all meeting dates needed to flag “FOMC weeks” are available.

• CPI release calendar – The Bureau of Labor Statistics maintains an archive of news-release pages for each CPI report. The hit returned for 14 April 2010 (BLS CPI release 2010-04-14) and the analogous pages for 2010-06-17, 2010-08-13, etc. demonstrate that the exact release dates are preserved for every month (BLS, news.release archives). These dates can therefore be mapped to “CPI-release weeks.”

2. It supplies no new numerical work: none of the pages calculates 10-trading-day DTB6 changes or their descriptive moments. No table of means, standard deviations, quartiles, or maxima—unconditional or conditional on event weeks—appears in the material retrieved.

3. It therefore leaves the same single information gap identified earlier: the mechanical computation of the statistics requested by the client.

   • What is still missing?  
     – For each trading day t between 2010-01-04 and 2026-02-28 (2010-01-01 is a holiday), one must compute  
       Δ10 t = DTB6 t+10 – DTB6 t (signed change) and |Δ10 t| (absolute change), where “t+10” is defined as the tenth subsequent trading day in the DTB6 calendar.  
     – Using those two vectors, derive five descriptive measures—mean, standard deviation, 25th percentile, 75th percentile, and maximum—under three sampling rules: (a) all days, (b) days that fall in an “FOMC week” (Monday-Friday containing an FOMC meeting), and (c) days that fall in a “CPI-release week.”

   • Why can’t we finish the job with the information in hand?  
     – None of the search results offers those pre-calculated transformations; all they provide is the source data and documentation.  
     – Consequently the summary table demanded by the original query is still empty.

Conclusion  
All external data prerequisites are fully satisfied: the DTB6 price path, every FOMC meeting date, and every CPI public-release date are publicly posted in stable HTML or CSV formats (FRED; Federalreserve.gov; BLS, news.release archives). What remains to be delivered is purely computational. Without running the DTB6 series through a 10-day difference filter and tabulating the required statistics, the client’s question—“Compute 10-day ahead absolute and signed changes in DTB6 … and provide results in a summary table”—cannot yet be answered. No additional conceptual research is necessary; only execution of the calculations is outstanding.</Agent_report>


<FREDData series="DTB6" query="DTB6">
FRED Economic Data: 6-Month Treasury Bill Secondary Market Rate, Discount Basis
Series ID: DTB6
Units: Percent
Frequency: Daily
Latest observation: 3.53 (2026-02-26)

HISTORICAL STATISTICS:
- 1-year: mean=3.85, min=3.48, max=4.17
- 5-year: mean=3.37, min=0.02, max=5.36
- 10-year: mean=2.28, min=0.02, max=5.36
- All-time: mean=4.48, min=0.02, max=15.93 (since 1958-12-09)

RECENT CHANGES:
- 1-month change: +0.00 (+0.0%)
- 3-month change: -0.13 (-3.6%)
- 6-month change: -0.33 (-8.5%)
- Year-over-year: 3.53 vs 4.17 (-15.3%)

RECENT VALUES (Daily):
Date,Value
2026-02-10,3.50
2026-02-11,3.51
2026-02-12,3.50
2026-02-13,3.50
2026-02-17,3.51
2026-02-18,3.51
2026-02-19,3.52
2026-02-20,3.52
2026-02-23,3.53
2026-02-24,3.53
2026-02-25,3.53
2026-02-26,3.53

Source: Federal Reserve Economic Data (FRED), St. Louis Fed
</FREDData>


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
