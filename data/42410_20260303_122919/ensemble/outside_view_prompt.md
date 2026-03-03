
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
What will be the value of "Crude Oil Prices: Brent - Europe" on 2026-03-12?

Question background:
The Federal Reserve Economic Data database (FRED) provides economic data from national, international, public, and private sources. The series DCOILBRENTEU is a dataset that is tracked by the FRED API. It represents the price of Brent crude oil. The title of the series is "Crude Oil Prices: Brent - Europe". The last data point on the graph (as of creation of this question) is from 2026-02-23 and has a value of 71.9. The units of the series are "Dollars per Barrel". The update frequency of the series is "Daily". The seasonal adjustment of the series is "Not Seasonally Adjusted". An interactive graph for the series can be found [here](https://fred.stlouisfed.org/series/DCOILBRENTEU). Below are the notes attached to the series:

> Definitions, Sources and Explanatory Notes (http://www.eia.doe.gov/dnav/pet/TblDefs/pet_pri_spt_tbldef2.asp)

`{"format":"fred_value_at_time","info":{"series_id":"DCOILBRENTEU"}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
Resolves to the value found on the FRED API for the series DCOILBRENTEU once the data is published.

Additional fine-print:
A script will be used to determine the resolution of this question. It will paginate through the data found at the API endpoint `https://api.stlouisfed.org/fred/series/observations?series_id=DCOILBRENTEU`. This endpoint includes the latest data for the series. The latest revised data will be used when the resolution is assessed. The datapoint matching 2026-03-12 will be used to determine the resolution of this question.

A datapoint matches if:
1. The series is updated daily and the date of the datapoint is within 1 day previous to the resolution date.
2. The series is updated weekly and the date of the datapoint is within 7 days previous to the resolution date.
3. The series is updated monthly and the date of the datapoint is within 31 days previous to the resolution date.

If the datapoint is clearly skipped, or no datapoint is found after 2 weeks of checking then the question will be annulled.

Units for answer: Dollars per Barrel

Question metadata:
- Opened for forecasting: 2026-03-03T12:02:34Z
- Resolves: 2026-03-12T03:01:09Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-03T12:02:34Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-03. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-03 should not be considered as speculative but rather an historical document.

The lower bound is 51.55046 and the upper bound is 90.33204.
Both bounds are OPEN: outcomes can fall below the lower bound or above the upper bound. Your percentile estimates may extend beyond this range if well-supported by evidence.

Historical context:

<QuestionSource url="https://fred.stlouisfed.org/series/DCOILBRENTEU">
**Disclaimer:** The extracted content is largely metadata and citation information from the FRED database page, rather than a substantive article with analytical content. It does not contain recent price data, forecasts, or expert commentary beyond what is described below.

---

## Summary: Crude Oil Prices: Brent - Europe (DCOILBRENTEU) – FRED Series Page

**Source & Attribution:**
- Data is published by the **U.S. Energy Information Administration (EIA)** as part of its **Spot Prices** release.
- Retrieved via the Federal Reserve Bank of St. Louis (FRED) database.

**Series Characteristics:**
- **Units:** Dollars per Barrel
- **Frequency:** Daily
- **Seasonal Adjustment:** Not Seasonally Adjusted
- **Series ID:** DCOILBRENTEU

**Key Notes:**
- All data points are **subject to revision**.
- Users can select either **automatic updates** or a **static time frame** when viewing the data.
- Further definitional and methodological details are available via the EIA's explanatory notes page.

**No price data, trend analysis, forecasts, or expert opinions** were included in the extracted content. The page primarily serves as a metadata and citation reference for the DCOILBRENTEU data series.
</QuestionSource>


<FREDData series="DCOILBRENTEU" query="DCOILBRENTEU">
FRED Economic Data: Crude Oil Prices: Brent - Europe
Series ID: DCOILBRENTEU
Units: Dollars per Barrel
Frequency: Daily
Latest observation: 71.90 (2026-02-23)

HISTORICAL STATISTICS:
- 1-year: mean=67.76, min=59.93, max=80.37
- 5-year: mean=81.08, min=59.93, max=133.18
- 10-year: mean=68.40, min=9.12, max=133.18
- All-time: mean=50.84, min=9.10, max=143.95 (since 1987-05-20)

RECENT CHANGES:
- 1-month change: +3.74 (+5.5%)
- 3-month change: +7.91 (+12.4%)
- 6-month change: +4.15 (+6.1%)
- Year-over-year: 71.90 vs 74.88 (-4.0%)

RECENT VALUES (Daily):
Date,Value
2026-02-06,70.45
2026-02-09,71.19
2026-02-10,71.01
2026-02-11,71.52
2026-02-12,69.80
2026-02-13,69.96
2026-02-16,70.81
2026-02-17,69.77
2026-02-18,71.78
2026-02-19,73.17
2026-02-20,72.75
2026-02-23,71.90

Source: Federal Reserve Economic Data (FRED), St. Louis Fed
</FREDData>


<Summary source="https://oilprice.com/oil-price-charts/">
**Disclaimer:** This article appears to be a real-time/delayed pricing dashboard from OilPrice.com rather than a traditional article. The data shown reflects prices with varying delays (ranging from minutes to weeks depending on the benchmark). The content is essentially a snapshot of global crude oil prices across numerous benchmarks and blends.

---

## Key Data Points from OilPrice.com Global Crude Price Dashboard

### Major Futures & Indexes (with 11-16 minute delays):
- **Brent Crude: $83.50** (+$5.76, +7.41%)
- **WTI Crude: $76.49** (+$5.26, +7.38%)
- **Murban Crude: $83.54** (+$4.99, +6.35%)

### Delayed Benchmarks Relevant to Brent/Europe Pricing:
- **Brent Weighted Average: $72.28** (+$1.29, +1.82%) — *4 days delay*
- **OPEC Basket: $69.29** (-$0.40, -0.57%) — *6 days delay*
- **Azeri Light: $87.49** (+$2.43, +2.86%) — *6 hours delay*
- **CPC Blend (Kazakhstan): $83.49** (+$2.43, +3.00%)

### Notable Observation:
The significant divergence between the near-real-time Brent Crude futures price (~$83.50) and the delayed Brent Weighted Average (~$72.28) reflects the varying lag times across different price series reported on this platform.
</Summary>

<Summary source="https://www.barchart.com/futures/quotes/CB*0/historical-prices">
**Disclaimer:** The extracted content from this Barchart.com article does not contain any actual crude oil price data, historical prices, or specific market figures relevant to the forecasting question. The content is entirely composed of site navigation instructions, feature descriptions, and membership/download policy explanations for the Barchart.com platform.

## Summary

The article is a **help/reference page** from Barchart.com describing the functionality of their "Historical Futures" pages. Key points include:

- **Page purpose:** Lists current and expired futures contracts for commodities, sorted by contract year, showing prices and last trade dates.
- **Data update timing:** Intraday data refreshes with a flash; U.S. equities have a 15-minute delay (Cboe BZX data is real-time); Futures and Forex have a 10–15 minute delay.
- **Available views:** Main, Technical, Performance, Moving Averages, Fundamental, Mini-Chart, and Pre/Post Market views, each displaying different sets of columns.
- **Special features:** "More Data" expandable rows, Flipcharts (free for site members), and CSV download functionality.
- **Download limits:** Free members get 1 download/day; Plus members get 10; Premier members get up to 250.

**No actual Brent crude oil price data or historical price figures are present in this article**, making it of no direct utility for forecasting the DCOILBRENTEU value on 2026-03-12.
</Summary>

<Summary source="https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm">
## Summary of EIA Spot Prices for Crude Oil and Petroleum Products

**Source:** U.S. Energy Information Administration (EIA)
**Release Date:** 2/25/2026
**Next Release Date:** 3/4/2026

### Key Data Points for Brent Crude Oil (Dollars per Barrel):

The table provides daily spot prices for the week ending 02/23/2026. The row identifiable as Brent crude (based on the FRED last data point of 71.90 on 02/23/26) shows the following values:

| Date | Price ($/barrel) |
|------|-----------------|
| 02/16/26 | 70.81 |
| 02/17/26 | 69.77 |
| 02/18/26 | 71.78 |
| 02/19/26 | 73.17 |
| 02/20/26 | 72.75 |
| 02/23/26 | **71.90** |

The historical data for this series spans **1987–2026**.

**Disclaimer:** The extracted web content appears to be a partially garbled table, with some rows and column headers not cleanly rendered. The Brent crude row was identified by cross-referencing the known FRED value of 71.90 for 02/23/26. Other rows in the table appear to represent different petroleum products (e.g., natural gas, heating oil, gasoline), but their labels were not clearly extracted.
</Summary>


<Summary source="https://www.oilpriceapi.com/historical-prices">
**Disclaimer:** This article is from a commercial API service (Oil Price API / oilpriceapi.com) that sells access to historical commodity price data. The "current" prices listed appear to reflect a specific snapshot date that is not explicitly stated in the article, and the source has a commercial interest in presenting its data favorably.

---

## Summary

The article is a product/marketing page for a historical oil price data API service. The key factual data points presented include:

### Current Price Snapshot (date unspecified)
| Commodity | Current Price | 12-Mo High | 12-Mo Low | 12-Mo Avg | YoY Change |
|---|---|---|---|---|---|
| **Brent Crude** | $75.58/bbl | $75.58 | $61.73 | $67.27 | +5.78% |
| WTI Crude Oil | $69.58/bbl | $69.58 | $57.95 | $63.53 | +2.43% |
| Natural Gas | $2.91 | $4.46 | $2.90 | $3.55 | -25.95% |

### Notable Historical Price Benchmarks Cited
- **All-time WTI high:** $147.27/barrel (July 2008)
- **Brent high:** $139.13/barrel (March 2022, post-Russia-Ukraine invasion)
- **All-time WTI low:** -$37.63/barrel (April 20, 2020, COVID-19 storage crisis)

The article notes that **Brent historically trades $2–5 higher than WTI**, though the spread varies. The service claims 20+ years of historical data coverage for major crude benchmarks.
</Summary>

<Summary source="https://www.barchart.com/futures/quotes/CBH10/historical-prices">
**Disclaimer:** The extracted content from this Barchart.com article does not contain any actual crude oil price data, historical prices, or specific market figures relevant to the forecasting question. The content is entirely composed of site navigation instructions, feature descriptions, and membership/download policy explanations for the Barchart.com platform.

**Summary of Article Content:**

The article is a general description of Barchart.com's **Historical Futures page** functionality, covering:

- **Data update frequencies**: U.S. equities have a 15-minute delay; Futures and Forex have a 10–15 minute delay (CT).
- **Page features**: Users can sort data tables by column headers, use various pre-set "Views" (Main, Technical, Performance, Moving Averages, Fundamental, Mini-Chart, Pre/Post Market), and access expanded symbol data via a "+" icon.
- **Exclusive tools**: "Flipcharts" (free for site members) allow scrolling through symbols in chart view with customizable templates. "Download" (free for members) allows CSV exports, with limits based on membership tier (Free: 1/day; Plus: 10/day; Premier: 250/day).
- **Licensing restrictions**: Canadian and certain international fundamental data cannot be downloaded.

**No specific Brent crude oil price data, historical values, or forecasts are present in this article.** It provides no information useful for resolving the forecasting question.
</Summary>

<Summary source="https://www.eia.gov/dnav/pet/hist/rbrted.htm">
**Disclaimer:** The extracted content from this article appears to be minimal, containing only the title and source attribution without substantive data, tables, or analytical content. The quality of the web content extraction appears incomplete.

## Summary

**Source:** U.S. Energy Information Administration (EIA)

**Series:** Europe Brent Spot Price FOB (Free on Board)

**Units:** Dollars per Barrel

The article references the EIA's dataset tracking the **Europe Brent Spot Price FOB**, which measures the spot market price for Brent crude oil at the point of delivery (Free on Board basis) in Europe, denominated in U.S. dollars per barrel. This is the underlying data source for the FRED series `DCOILBRENTEU`.

No specific price figures, trend data, forecasts, or analytical commentary were retrievable from the extracted content. The EIA is a **highly reliable, named government source** (part of the U.S. Department of Energy) that serves as the primary data provider for this crude oil price series.

For substantive price data relevant to the forecasting question, the forecaster would need to consult the full EIA dataset directly or the FRED API endpoint, as the article itself did not yield usable numerical or analytical content in this extraction.
</Summary>


<Summary source="https://www.investopedia.com/ask/answers/060415/how-much-influence-does-opec-have-global-price-oil.asp">
## Summary of Article: OPEC+ and Oil Price Dynamics

### What is OPEC+?
- OPEC+ is a coalition of 12 OPEC member nations plus 10 major non-OPEC oil-exporting countries, formed in 2016
- OPEC controls ~40% of global oil supplies and more than 80% of proven oil reserves
- The group's primary goal is to regulate oil supply to influence global crude oil prices

### How OPEC+ Influences Prices
- Members collectively agree on production levels, directly affecting global crude oil supply
- Supply cuts typically cause immediate price spikes, though prices tend to revert over time as supply adjustments prove incomplete or demand shifts
- Long-term influence is diluted by individual member nations' differing incentives and competition from non-OPEC producers (e.g., U.S., Canada)

### Key Historical Price Events Referenced
- **April 2020**: Brent crude fell below **$20/barrel** amid COVID-19 demand collapse and a Saudi Arabia-Russia production dispute
- **June 2022**: WTI prices exceeded **$115/barrel** following Russia's invasion of Ukraine
- **October 2022**: OPEC+ announced cuts of **2 million barrels/day** amid recession fears
- **Recent period**: Brent crude trading **below $80/barrel**; WTI below $70/barrel — levels insufficient for many OPEC+ members to balance national budgets

### Current Production Strategy (as of article writing)
- OPEC+ has continued production cuts through 2024 and plans to extend them into **2025**
- Cuts are aimed at countering weak demand, high interest rates, and rising U.S. production

### Relationship to Inflation
- Oil price changes have a greater impact on the **Producer Price Index (PPI)** than the **Consumer Price Index (CPI)**
- The U.S. economy's oil-dependence has declined over recent decades, reducing oil's capacity to drive consumer inflation

---
*Note: The article is a general explainer on OPEC+ and does not contain specific forecasts or data points for Brent crude prices in 2026.*
</Summary>

<Summary source="https://oilprice.com/Energy/Crude-Oil/Whats-The-Real-Reason-Behind-OPECs-Surprise-Oil-Production-Boost.html">
## Summary of Article: "Oil Prices Surge to $84 as Supply Risk Becomes Real"

**Note:** The article appears to be cut off at the end, so the summary reflects only the available content.

### Key Facts & Statistics

- OPEC+ announced a production increase of **137,000 bpd** starting in October, significantly lower than prior increases of 411,000 bpd (June–July) and 555,000 bpd (August–September).
- This reverses part of **1.65 million bpd** in cuts (announced April 2023) by eight members, occurring over a year ahead of schedule.
- U.S. shale oil production grew from ~0.2 million bpd (2011) to ~8.7 million bpd (2014), per EIA data.
- The 2014–2016 Oil Price War cost OPEC members a collective **$450 billion** in lost revenues (per IEA).
- Saudi Arabia ran a **$98 billion deficit** in 2015 and spent at least **$250 billion** in foreign exchange reserves.
- The Dallas Fed Energy Survey estimates the U.S. shale breakeven price at approximately **$65/barrel** for new wells.
- Every **$10/barrel** change in crude oil prices results in roughly a **25–30 cent** change per gallon of gasoline.
- Every **1 cent** rise in gasoline prices costs U.S. consumers over **$1 billion/year** in spending.

### Key Analytical Points (Author's Opinion)

- The author identifies a **"Trump Oil Price Range"** of approximately **$40–45/barrel (floor)** to **$75–80/barrel (ceiling)** for Brent crude, based on shale breakeven economics and gasoline price political thresholds.
- Saudi Arabia and the UAE are described as the **only two OPEC+ members with significant spare capacity**.
- The author questions whether OPEC+ is entering a new oil price war but concludes it seems **unlikely in the near term**, crediting Saudi Arabia with learning from past failures.
- The article suggests Saudi Arabia may be coordinating production decisions **in consultation with Washington**.
- The current oil price outlook is described as **bearish**, but subject to rapid change depending on U.S. geopolitical actions, particularly regarding **sanctions on Russia**.

### Historical Political Context (Named Sources)

- **Bob McNally**, former energy adviser to President George W. Bush: *"Few things terrify an American president more than a spike in fuel [gasoline] prices."*
- An unnamed **senior White House official** (off-the-record, end of 2016): *"We're not going to put up with any more crap from the Saudis."*
- **Donald Trump** reportedly warned Saudi King Salman and Crown Prince Mohammed bin Salman directly during the 2020 Oil Price War, threatening withdrawal of U.S. military support unless production cuts were implemented.
</Summary>


<Agent_report>
Query: Provide a list of historical episodes from the last 15 years where Brent crude moved more than $10 within a single week, noting the trigger events and summarizing common patterns.
Brent crude oil’s front-month contract has moved by more than US $10 between one Friday settlement and the next only nineteen times in the last fifteen years (11 March 2011-23 February 2026).  Cross-checking the earlier chronology against the fresh material returned in the latest search confirms every episode already listed and reveals no additional weeks that satisfy the > $10 criterion.

Verified list of > $10 Friday-to-Friday moves (March 2011-February 2026)

1. 11-18 Mar 2011  | + $12 Libyan civil war curtails ~1 mb/d exports (Gainesville Sun, 21 Mar 2011).  
2. 23-30 Dec 2011  | + $11 Iran warns it could close Strait of Hormuz (Financial Times, 30 Dec 2011).  
3. 28 Sep-5 Oct 2012  | – $10 Surprise Saudi supply increase and OECD stock build (Bloomberg, 5 Oct 2012).  
4. 27 Jun-4 Jul 2014  | – $11 Chinese slowdown signals; shale output record (Wall Street Journal, 7 Jul 2014).  
5. 21-28 Nov 2014  | – $11 OPEC Vienna meeting ends without a cut (Reuters, 28 Nov 2014).  
6. 26 Jun-3 Jul 2015  | – $10 Greek referendum risk; looming Iran deal (CNBC, 3 Jul 2015).  
7. 24 Feb-2 Mar 2016  | + $11 Rumoured OPEC-Russia “freeze” (Bloomberg, 2 Mar 2016).  
8. 9-16 Mar 2020  | – $16 Saudi-Russia price war plus first COVID-19 lockdowns (Reuters, 16 Mar 2020; countryeconomy.com daily prices).  
9. 30 Mar-6 Apr 2020  | + $14 Trump tweets on a 10-15 mb/d OPEC+ cut (Financial Times, 6 Apr 2020).  
10. 2-9 Nov 2020  | + $11 Pfizer/BioNTech vaccine efficacy news (Bloomberg, 9 Nov 2020).  
11. 18-25 Jun 2021  | + $11 OPEC+ hints at only modest output hike; US gasoline demand peaks (Reuters, 25 Jun 2021).  
12. 18-25 Feb 2022  | + $12 Russia invades Ukraine (Zhang 2023 in Nature HSSC, cited in Reuters wraps).  
13. 25 Feb-4 Mar 2022  | + $21 Escalating sanctions against Russian oil (Reuters, 4 Mar 2022).  
14. 4-11 Mar 2022  | – $17 Cease-fire talk plus IEA coordinated SPR release (Reuters, 11 Mar 2022).  
15. 23-30 Sep 2022  | – $12 Dollar index hits 20-year high; recession fear (Bloomberg, 30 Sep 2022).  
16. 30 Sep-7 Oct 2022  | + $15 OPEC+ unveils headline 2 mb/d cut (Reuters, 7 Oct 2022).  
17. 6-13 Oct 2023  | + $11 Hamas attack on Israel raises Hormuz risk (Reuters, 13 Oct 2023).  
18. 27 Oct-3 Nov 2023  | – $10 Conflict remains contained; Fed “higher-for-longer” stance (Bloomberg, 3 Nov 2023).  
19. 23-30 Dec 2025  | – $10 Year-end liquidation amid supply-glut narrative (Maeil Kyungje/Bloomberg recap, 31 Dec 2025).

Why the 2019 Abqaiq attack does NOT appear: Brent opened on Friday 13 Sep 2019 at roughly $60.22/bbl and closed Friday 20 Sep at ~$64.28, a gain of about $4—well below the $10 threshold despite the record one-day jump reported by CNBC on 16 Sep 2019.  The weekly close therefore fails the filter (CNBC, 16 Sep 2019).

Common trigger patterns across the 19 events

1. Geopolitical supply shocks (7/19 episodes).  
   • Libya 2011, Iran rhetoric 2011, Russia-Ukraine 2022 cluster, Israel-Hamas 2023.  
   These almost always produce upside moves and account for the four largest weekly surges (+$12, +$21, +$15, +$11).

2. OPEC/OPEC+ policy surprises (7/19).  
   • No-cut 2014 and price-war 2020 yielded the two steepest drops (–$11, –$16).  
   • Freeze rumours 2016 and quota cuts 2022 delivered double-digit rallies.

3. Macroeconomic demand shocks (3/19).  
   • COVID-19 first-wave collapse; vaccine euphoria; 2022-23 recession fears.  
   Demand shocks can drive both directions but usually require an accompanying sentiment or liquidity catalyst to clear the $10 bar.

4. Currency and liquidity effects (2/19).  
   • Dollar spike in Sep 2022 and thin holiday trade in Dec 2025 nudged Brent over the threshold, showing the importance of positioning in thin markets.

5. Mean-reversion clusters.  
   Six instances form back-to-back pairs where an extreme move is followed by a sharp reversal within one to two weeks (Mar 2020, Mar 2022, Sep-Oct 2022).  This underlines how quickly “event-risk premiums” decay once initial fears are reassessed.

Statistical perspective

• Nineteen qualifying weeks out of roughly 780 trading weeks since March 2011 equals a base frequency of 2.4 %.  
• Average absolute change across those weeks is $13.5/bbl; median $11.5/bbl.  
• The 2022 Russia-Ukraine sequence is the only time three consecutive $10-plus weeks occurred.

Implications for the 12 March 2026 Brent price outlook

1. Probability of an extreme, unforecastable weekly swing remains low (<3 %) absent fresh geopolitical or cartel shocks in early March.  
2. The date lies one week after the scheduled 5-6 March 2026 OPEC+ ministerial.  Based on past behaviour, an unexpected quota decision could raise the tail-risk of a $10 move but history suggests equal odds of a rally or slump depending on the policy surprise.  
3. In the absence of such a shock, Brent typically reverts to fundamental ranges—currently $65-$80/bbl—after volatility spikes, as evidenced by post-event retracements in 2014, 2020 and 2022.

Remaining information gaps that would further strengthen confidence in the episode list

• Exact ICE Friday settlements for the 26 Jun-3 Jul 2015 and 18-25 Jun 2021 weeks are cited from press wraps; downloading the official settle data would conclusively validate the –$10 and +$11 readings.  
• A systematic download of the DCOILBRENTEU daily series from FRED and recomputation of Friday-to-Friday differences would provide a fully transparent numeric backbone to the qualitative triggers already documented.  The present list is, however, corroborated by multiple contemporary news sources and by point-in-time price charts such as countryeconomy.com’s March 2020 series and ICE historical prints, so no additional episodes appear to be missing.

With these caveats noted, the chronology above can be treated as complete for the last fifteen years and forms a robust empirical base for forecasting volatility around the March 2026 target date.</Agent_report>


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
