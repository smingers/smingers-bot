
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
Will the interest in “irgc” change between 2026-03-02 and 2026-03-14 according to Google Trends?

Question background:
Google Trends is a free tool from Google that shows how often particular search terms are entered into Google relative to the total search volume across different regions and time periods. One of its main features is the “interest over time” graph, which is scaled from 0 to 100. In this graph, 100 represents the peak popularity of the term during the selected time range and location, meaning the point in time when searches for that term were at their highest. A 0 does not mean no searches occurred, but rather that the search interest was too low to register compared to the peak values. Because the values are relative, the numbers for a given day can shift as new data is added or as the overall scale is recalibrated—for example, a value of 40 on one day could later appear as 35 if the relative scaling changes. This effect can be reduced by specifying fixed start and end dates in the URL, which locks the scale for that chosen period and keeps the values consistent.

The current value of the topic “irgc” at the time of writing this question (Mar 1, 2026) compared to the last 30 days is 100; seen at [this url](https://trends.google.com/trends/explore?geo=US&tz=0&q=irgc&date=2026-01-30%202026-03-01).

`{"format":"trends_interest_change_magnitude","info":{"topic":"irgc","trend_start":"2026-03-02","trend_end":"2026-03-14","verification_url":"https://trends.google.com/trends/explore?geo=US&tz=0&q=irgc&date=2026-02-12%202026-03-14"}}`

The options are: ['Increases', "Doesn't change", 'Decreases']

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question resolves “Doesn't change” if the value on the timeline at [https://trends.google.com/trends/explore?geo=US&tz=0&q=irgc&date=2026-02-12%202026-03-14](https://trends.google.com/trends/explore?geo=US&tz=0&q=irgc&date=2026-02-12%202026-03-14) for 2026-03-14 is within 3 of the value at 2026-03-02. It resolves “Increases” if the value is more than 3 greater, and resolves “Decreases” if the value is more than 3 lower.

Additional fine-print:
A script will be used to determine the resolution of this question. It will access the data on Google Trends using [SerpApi](https://serpapi.com/), and compare the height of the timeline for the two aforementioned dates. The specific python query will be structured as follows:
```
from serpapi import GoogleSearch

search = GoogleSearch(params={
  "api_key": API_KEY,
  "engine": "google_trends",
  "data_type": "TIMESERIES",
  "geo": "US",
  "tz": 0,
  "q": "irgc",
  "date": "2026-02-12 2026-03-14",
})
search.get_dict()
```
Note that there may be differences between the results returned by the API and the data appearing on the page. This seems to be due to the 'tz' parameter not having the intended effect in-browser. In this case, the API results will be considered authoritative.
Note that the precision of the timeline will be 1 day, so this will compare the overall interest for the whole day as determined by Google Trends.
Dates are determined in UTC.
If the data is no longer available, or the script fails, this question will be annulled or manually resolved by a moderator.

Question metadata:
- Opened for forecasting: 2026-03-02T22:22:37Z
- Resolves: 2026-03-14T14:11:09Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-02T22:22:37Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-02. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-02 should not be considered as speculative but rather an historical document.

Historical context:

<QuestionSource url="https://serpapi.com/">
**Disclaimer:** The article provided is a general marketing/landing page for SerpApi and contains no specific information relevant to the question about IRGC Google Trends data for the specified date range.

---

## Summary

The article is a promotional page for **SerpApi**, a commercial API service that provides structured data from Google Search and other search engines. Key points include:

- **Core offering**: SerpApi provides infrastructure (global IPs, full browser cluster, CAPTCHA-solving technology) to deliver structured search engine results page (SERP) data via API requests.
- **Speed & accuracy**: Each API request runs immediately in a full browser environment, mimicking human behavior to ensure results reflect what real users see.
- **Geolocation support**: Results can be retrieved from anywhere in the world using a "location" parameter, routed through proxy servers nearest to the desired location.
- **Data types available**: Organic results, Maps, Local, Stories, Shopping, Direct Answers, Knowledge Graph, along with structured metadata (links, prices, ratings, reviews, rich snippets, etc.).
- **Legal stance**: The company asserts that crawling and parsing public data is protected under the First Amendment, and they assume scraping/parsing liabilities for clients (with exceptions for illegal activities).
- **Pricing model**: Month-to-month contracts with a free tier, scalable paid plans, and enterprise options.

No IRGC-specific or Google Trends-specific data is present in this article.
</QuestionSource>


<Summary source="https://www.searchenginejournal.com/google-reveals-the-top-searches-of-2025/563738/">
## Summary: Google's Top Searches of 2025

**Source:** Search Engine Journal | **Date:** December 23, 2025 | **Author:** Matt G. Southern | **Reliability:** Established industry publication

### Overview
Google's 2025 Year in Search highlights the fastest-growing search queries relative to 2024, spanning news, entertainment, sports, and lifestyle categories.

### Key Findings Relevant to IRGC/Iran Context
- **Iran** was noted as one of the topics people searched for globally in 2025, mentioned alongside other major news events like the TikTok ban and LA fires.
- No specific mention of "IRGC" as a standalone trending search term in either global or US top lists.

### Broader Trends
- **Global top searches** were led by AI tool Gemini, followed heavily by cricket and sports events.
- **US top searches** diverged significantly, led by Charlie Kirk, with political appointees and domestic events (government shutdown, "One Big Beautiful Bill Act") featuring prominently.
- Natural disasters (LA Fires, Hurricane Melissa) and political events drove major news search spikes.

### Relevance to Question
This article provides **limited direct relevance** to IRGC-specific search interest in early 2026. It confirms Iran-related topics generated notable search interest in 2025, suggesting baseline public curiosity, but offers no data specific to the March 2026 timeframe in question.
</Summary>

<Summary source="https://www.cbsnews.com/news/charlie-kirk-google-top-search-trends-2025/">
## Summary of Article

**Source:** CBS News | **Date:** December 5, 2025 | **Author:** Jennifer Earl

### Key Points:

This article covers **Google's annual "Year in Search" report for 2025**, highlighting the top search trends in the United States. The article does **not contain any information directly relevant to "IRGC"** as a search topic.

### Notable findings from the report:

- **Charlie Kirk** (conservative activist, assassinated in September 2025) was the **#1 overall search** in the U.S. for 2025
- Other top searches included the **"One Big Beautiful Bill Act"**, a **43-day government shutdown**, **tariffs**, and **"No Kings" protests**
- **Zohran Mamdani** (NYC Mayor-elect, first Muslim mayor) was a top-searched person
- Pop culture trends included **KPop Demon Hunters**, **Labubu**, and **iPhone 17**
- Notable passings searched included Kirk, Gene Hackman, Ozzy Osbourne, Anne Burrell, and Diane Keaton

---

**Disclaimer:** This article contains **no information relevant to IRGC search trends** for the specified resolution period (March 2–14, 2026). It should not be used as a basis for forecasting changes in IRGC-related Google search interest.
</Summary>

<Summary source="https://evrimagaci.org/gpt/global-search-trends-of-2025-reveal-shifting-priorities-520954?srsltid=AfmBOoo25v85VCcNJXFHMgjAm6hXttdnXq8OmT1axNxo71JSXJXjvB6d">
**Disclaimer:** This article appears to be from a source called "Grand Pinnacle Tribune," which is not a widely recognized major publication. The content reads as a general year-in-review piece and may not be fully reliable. Additionally, the article contains at least one factually questionable claim (referencing "the tragic death of his aide Charlie Kirk in September 2025"), which raises concerns about the overall accuracy of the piece.

---

## Summary

The article analyzes global Google search trends for 2025, drawing on data from Players Time using Ahrefs search volume data.

**Key findings relevant to the forecasting question:**

- **Iran and the IRGC context:** The article notes that "Iran topped search results as the world watched events unfold," citing Iran's military responses and the ongoing Gaza conflict as major drivers of global search interest throughout **both 2024 and 2025**. Related events such as the **Pahalgam attack and Operation Sindoor** also consistently trended.

**Other notable findings (broader context):**
- Donald Trump was the most searched person globally (~16M monthly searches); Elon Musk second (~11M).
- Entertainment, film/TV (36% of top 100 search volume), and sports (16%) dominated.
- Natural disasters (Hurricane Milton, Hurricane Melissa) drove significant search spikes.
- Search behavior in 2025 was characterized by **rapid, news-driven surges** rather than sustained long-term interest — described as an "attention economy driven by immediacy rather than longevity."
</Summary>


<Summary source="https://newsinitiative.withgoogle.com/resources/trainings/basics-of-google-trends/">
## Summary: Basics of Google Trends (Google News Initiative)

This article is a beginner's guide to using Google Trends' Explore tool. It does **not contain information specific to the "irgc" search term or its trends data**. Instead, it explains how Google Trends works generally:

### Key Mechanics Explained:
- **Data Source**: Google Trends pulls from a random, unbiased sample of Google searches — it does **not** provide exact search volumes.
- **Indexing**: Values are scaled from **1–100**, where **100 represents the peak search interest** for the selected time period and location. All other values are proportional to that peak.
- **Normalization**: Values reflect the **percentage of searches** for a topic relative to *all* searches at that time and location — not raw search counts.
- **Scale Sensitivity**: The maximum point (100) **shifts depending on the time range selected** and any comparison terms added, meaning the same data point can show different values under different settings.

### Practical Notes Relevant to the Forecasting Question:
- Specifying **fixed date ranges** in the URL helps lock the scale and keep values consistent.
- Topics (vs. raw search terms) tend to capture broader data including misspellings and acronyms.
- The tool updates in real time and data can be recalibrated as new searches occur.
</Summary>

<Summary source="https://support.google.com/trends/answer/4365533?hl=en">
## Summary: FAQ About Google Trends Data (Support.google)

This article explains how Google Trends works and how its data should be interpreted. Key points relevant to the forecasting question:

### Data Collection & Sampling
- Google Trends uses a **sample** (not the entirety) of actual Google searches, which is considered representative given billions of daily searches
- Data is **anonymized, categorized, and aggregated**

### Normalization Method
- Each data point is divided by total searches for its geography/time range (to control for volume differences between regions)
- Results are then **scaled 0–100** based on a topic's proportion to all searches — 100 = peak popularity within the selected period

### Data Limitations
- May include irregular/automated searches (intentionally retained as a security measure)
- Filters out: low-volume searches (shown as "0"), duplicate searches from the same person in a short period, and special characters

### Time Zone Clarification (Directly Relevant)
- For **time ranges of 30 days or longer** (daily/weekly/monthly granularity): data uses **UTC**
- For **time ranges of 7 days or shorter** (hourly granularity): data uses the **user's local time zone**
- The question's date range (2026-02-12 to 2026-03-14) exceeds 30 days, so **UTC applies**, consistent with the API query using `"tz": 0`

### Important Caveat
- Google Trends is **not a scientific poll** and reflects search interest only, not popularity or sentiment
</Summary>

<Summary source="https://www.evilworks.com/blog/live-data-science-walkthrough-making-google-trends-data-usable">
## Summary

**Disclaimer:** This article is a technical data science tutorial about working with Google Trends data methodology. It contains **no information directly relevant** to IRGC search interest trends or the specific forecasting question at hand. Its relevance is limited to understanding how Google Trends data works mechanically.

---

### Key Technical Points About Google Trends Data

**The Core Problem:**
- Google Trends normalizes each query window **independently** — the highest value in any given window is set to 100, with everything else scaled relative to that peak
- This means naively stitching together multiple time windows produces **incompatible scales**, creating artificial-looking spikes or drops that don't reflect real search behavior

**Data Granularity Limitations:**
- Short periods (~hours): data available every 15–16 minutes
- ~1 month: daily granularity
- ~1 year: weekly aggregation only (reducing ~365 points to ~52)

**The Proposed Fix (Rolling Windows with Overlap):**
- Pull 90-day windows, advancing 60 days each time
- This creates **30-day overlapping periods** between consecutive windows
- Use overlap periods to calculate **scaling factors** that normalize each batch relative to the first batch
- Multiplying chained scaling factors brings all batches onto a common scale

**Result:** The corrected data produces a smoother, continuous trend line that aligns with Google's own long-term trend graphs in terms of peak timing, though absolute scale values may differ.
</Summary>


<Summary source="https://www.theguardian.com/world/2025/aug/26/iran-has-a-long-history-clandestine-attacks-abroad-to-further-its-ends">
## Summary: Iran's Clandestine Operations Abroad (The Guardian, August 26, 2025)

### Core Argument
Experts characterize Iran's overseas covert operations as a strategy born of **conventional military weakness**, dating back to the 1979 revolution. The article was prompted by Australian authorities blaming Iran for a series of antisemitic attacks in Australia.

### Key Facts & Statistics
- Researchers have identified **more than 200 plots linked to Iran** around the world since 1979
- At least **33 assassination or abduction attempts** in the West since 2020 have alleged Iranian links
- The US, UK, Canada, and **12 European countries** issued a joint condemnation in July of Iranian intelligence service activities
- A British minister stated **more than 20 Iran-backed plots** presenting potentially lethal threats to UK citizens/residents have occurred since the start of 2022
- A **two-week war with Israel and the US in June** damaged Iran's nuclear programme, with Tehran widely seen as coming off worse

### The IRGC's Role
- The **IRGC is identified as the primary organizer** of most overseas plots, answering directly to Supreme Leader Ali Khamenei with its own financial resources
- Historical IRGC activities include links to **1982 Beirut bombings** killing hundreds of US diplomats and military personnel, and the formation of Hezbollah

### Expert Opinions
- **Matthew Redhead (RUSI):** Described the Australia attacks as "smacking of desperation," suggesting Iran is "signalling that they are still active" rather than demonstrating genuine capability
- **Matthew Levitt (Iran operations authority):** Noted Iran reached out to **organised crime groups in Europe** even during the 12-day Israel-Iran war to carry out attacks against Israeli and American interests
- Both experts frame recent activity as indicative of **weakness rather than strength**, with criminal proxies used as a substitute for on-the-ground IRGC assets

### Relevance to IRGC Search Interest
The article provides context for why searches for "irgc" may fluctuate — ongoing news coverage of IRGC-linked plots, the June 2025 Israel-Iran conflict, and incidents like the Australia attacks could drive periodic spikes in search interest.
</Summary>

<Summary source="https://fews.net/middle-east-and-asia/iran/targeted-analysis/june-2025">
## Summary of FEWS NET Report (Current as of June 26, 2025)

**Note:** This article is a FEWS NET food security report focused on the Middle East region, dated June 2025. It is not directly about Google Trends data for "irgc" but contains highly relevant information about IRGC-related events that could drive search interest.

---

### Key IRGC-Related Events (June 2025)

- **June 12-13:** Israel launched **"Operation Rising Lion"** targeting Iran's nuclear program, **IRGC leadership**, missile sites, and stockpiles.
- The strikes **significantly degraded IRGC leadership**, killing key military figures and contributors to Iran's nuclear program, and damaged Iran's air defense and missile capabilities (per IDF leadership).
- Subsequent strikes hit Natanz and Fordow nuclear facilities and oil infrastructure.
- **June 14-16:** Iran retaliated with hundreds of drones and missiles at Israel (mostly intercepted); Iran's proxies (Hezbollah, PMFs, Ansar Allah) largely refrained from joining.
- **June 17:** Iran's retaliatory capabilities significantly degraded, though small salvos continued.
- **June 21:** The U.S. struck Iran's Fordow, Isfahan, and Natanz nuclear facilities.
- **June 23:** Iran fired missiles at Al-Udeid base in Qatar (largely symbolic, no casualties); Trump announced a **"complete and total ceasefire"** between Israel and Iran.
- **June 24:** Both sides signaled willingness to adhere to the ceasefire.

### Shipping & Oil Market Impacts
- Strait of Hormuz handles ~18-19 mb/d; Iranian parliament passed a non-binding motion to potentially close it to hostile shipping.
- Spot freight rates and war-risk insurance premiums surged; VLCC earnings peaked at ~$78,000/day on June 21 before falling ~10% post-ceasefire.
- Suez Canal traffic remains 60% below normal; major shippers continue avoiding the Red Sea.
- Brent crude had declined from ~$80/bbl in January to ~$64 in May before the conflict.
- Global oil surplus of 1.6 mb/d confirmed by IEA; OPEC estimates 5-6 mb/d spare capacity.

### Regional Food Security Context
- Poor households across the region depend heavily on market purchases for food, making them vulnerable to market disruptions.
- Wheat and barley are key staples supplied through local markets and imports.
- The Middle East accounts for over 10% of global dry bulk trade (primary shipping method for staple foods).

---

**Relevance to the forecasting question:** This article documents major real-world events involving the IRGC (Israeli strikes on IRGC leadership, significant military degradation) occurring in **June 2025**, well after the question's resolution window of March 2–14, 2026. It does not provide direct information about search interest trends during the question's specified period.
</Summary>

<Summary source="https://asiatimes.com/2026/03/a-strike-is-not-a-strategy-iran-will-prove-it/">
## Summary: "A Strike Is Not a Strategy — Iran Will Prove It" (*Asia Times*)

**Author:** M. A. Hossain, described as a senior journalist and international affairs analyst based in Bangladesh.

**Core Argument:** The article argues that military strikes — specifically a hypothetical or described coordinated US-Israeli strike targeting Iran's supreme leader and senior commanders — cannot substitute for coherent long-term strategy, and that history consistently demonstrates the failure of this approach.

### Key Points:

**Historical Precedents Cited:**
- Iraq: Removal of Saddam Hussein led to sectarian violence and jihadist expansion rather than democracy
- Libya: Removal of Gaddafi produced a fractured state and humanitarian crisis
- Syria: Regime-change efforts turned a domestic uprising into a prolonged regional conflict

**Material/Strategic Concerns:**
- The **Strait of Hormuz** carries roughly **one-fifth of the world's traded oil**; disruption would cause global energy price spikes and inflationary pressure
- Iran's **IRGC** has spent decades building regional influence through partners in Lebanon, Iraq, Yemen, and beyond — institutions that survive decapitation strikes
- The article notes Iran's **ballistic missiles striking regional bases** and the **IRGC mobilizing** as evidence decapitation has not produced anticipated paralysis

**Geopolitical Opportunity Cost:**
- A prolonged Iran conflict would divert military assets (cruise missiles, carrier strike groups), intelligence, and political capital away from the **Indo-Pacific/China rivalry**, benefiting Beijing without requiring Chinese action

**Narrative/Accountability Concerns:**
- The author urges skepticism toward threat inflation, referencing the false WMD claims before the Iraq invasion
- Notes a pattern: strike telegraphed for weeks, diplomatic process abandoned before a potential deal, no apparent post-conflict plan

**Conclusion:**
The author does not defend the Iranian regime but argues that prudence — "the disciplined alignment of means and ends" — demands more than tactical military action. A strike may disrupt command structures but does not resolve underlying power balances or guarantee favorable successors. The "harder work" of stabilization, market reassurance, and escalation prevention remains unaddressed.

---
*Note: The article appears to describe events (strikes on Iran, Khamenei's death, IRGC mobilization, Iranian missile retaliation) in a partially hypothetical or speculative framing, though some passages treat these as occurring facts. The exact status of these events relative to real-world developments at time of publication is unclear from the article alone.*
</Summary>


<Summary source="https://www.aljazeera.com/news/2026/3/2/what-is-irans-military-strategy-how-it-has-changed-since-june-2025-war">
## Article Summary

**Source quality note:** This appears to be an Al Jazeera article describing an ongoing, escalating military conflict between Iran/IRGC and Israel/US. The article appears to be set in a **hypothetical or future scenario** (referencing events in 2026, including the death of Khamenei), which is relevant context for the forecasting question.

---

### Key Facts & Events Described:

- **Khamenei's death** was confirmed by Iranian state media, triggering IRGC vows of revenge
- The **IRGC launched what it called "the heaviest offensive operations in the history of the armed forces of the Islamic Republic"** against Israel and US military assets
- Iran fired **137 missiles and 209 drones** targeting UAE-based US military assets on Saturday
- Strikes hit **Dubai and Abu Dhabi airports**; at least 1 killed at Abu Dhabi airport
- **At least 9 killed** in Iran's missile strike on Israeli town of Beit Shemesh
- Iran threatened to **close the Strait of Hormuz**; ~150 tankers anchored in open Gulf waters
- **Hezbollah** fired rockets at northern Israel in retaliation for Khamenei's killing

### Expert Opinions (Named Sources):

- **John Phillips** (British security/risk adviser, former military chief instructor): Iran's strategy focuses on asymmetric endurance, regional saturation, proxy warfare, and energy coercion; Iran is "more structurally aggressive in doctrine" but "operationally constrained by battle damage, sanctions and internal instability"
- **Anonymous military specialist/former military official**: Iran's military strategy is designed to "safeguard territorial integrity and stop foreign intervention targeted at overthrowing their rule"

### Relevant Background Context:
- A **June 2025 12-day war** between Iran and Israel (with US involvement) is cited as a prior escalation point, ending in a fragile ceasefire
- Iran's military structure includes parallel armies: the **Artesh** (conventional defense) and the **IRGC** (political/ideological protection, drone/airspace control)
- The article draws comparisons to Iran's response after the **killing of Soleimani in January 2020**

---

**Relevance to forecasting question:** The article describes a major, ongoing conflict prominently featuring the IRGC, which would likely drive **significantly elevated Google search interest** in "irgc" during this period.
</Summary>

<Summary source="https://www.criticalthreats.org/analysis/iran-update-evening-special-report-march-1-2026">
## Summary of Article (CTP-ISW Update, March 1, 2026)

**Note:** The article appears to be cut off at the end, so the summary reflects only the available content.

### Key Facts & Events

**Military Operations:**
- A combined US-Israeli force has struck **over 2,000 targets in Iran** since the conflict began on February 28, 2026, per a US official cited by the New York Times.
- The IDF announced it has achieved **air superiority over Tehran** after targeting Iranian air defenses at the conflict's outset.
- The US deployed **four B-2 stealth bombers** to strike underground ballistic missile sites in Iran on March 1.
- The IDF announced it has begun **"systematically dismantling" Iran's nuclear infrastructure**.
- Strikes near the **Atomic Energy Organization of Iran headquarters** in Tehran were reported, though the Tehran Research Reactor was assessed as not yet attacked as of 2:00 AM ET on March 1.

**Targets Struck:**
- West Azerbaijan Provincial Border Guard
- Mehran Border Regiment (Ilam Province) — **22 security personnel killed**
- Possibly the **IRGC Ansar ol Mehdi Unit** in Zanjan Province (an IRGC Ground Forces unit historically used for internal suppression)
- Shahr-e Rey Law Enforcement Command (LEC) Station in Tehran (linked to crackdowns on protesters in December 2025–January 2026)

**Cyberattacks:**
- Reuters reported that likely US and Israeli hackers compromised **multiple Iranian news sites and a religious calendar app**, displaying the message *"it's time for reckoning"* and urging security forces to disarm and join civilians.

**Iranian Internal Stability Measures:**
- Iran maintained a **nationwide internet blackout** at ~1% connectivity (per Netblocks), likely to prevent protest coordination.
- The LEC set up **checkpoints across Tehran** to prevent public gatherings (per Wall Street Journal).
- **Basij members** staged anti-US protests at Iranian universities.

### Iranian Leadership Developments

- **Ali Khamenei has died** (referenced contextually; the Leadership Council was formed to assume his responsibilities).
- The **Expediency Discernment Council** appointed **Ali Reza Arafi** as the third member of the **Leadership Council**, joining President Masoud Pezeshkian and Judiciary Chief Gholam Hossein Mohseni Ejei.
  - Arafi is described as a close Khamenei ally, appointed Qom Friday Prayer Leader in 2015 and to the Supreme Council of the Qom Seminary in 2016.
- The Leadership Council held its **second meeting on March 1**.
- **Ali Larijani** (Supreme National Security Council Secretary) and **Parliament Speaker Mohammad Bagher Ghalibaf** delivered televised speeches; Ghalibaf called Khamenei's killing a "red line."
- A New York Times report indicated Larijani had effectively been **running Iran** since recent protests, and Ghalibaf was designated a **"de facto deputy"** to command Iranian armed forces in the event of a US attack.

### Strategic Context
- US President Trump vowed the US **"will never allow Iran to develop a nuclear weapon"** when announcing the strike campaign on February 28.
- The combined force's stated objective includes **toppling the Iranian regime**.
- US and Israeli strikes have divided responsibilities: the US focuses on strategic infrastructure, while Israel focuses on **ballistic missile launchers and Iranian leadership**.

---
*This article is from the Critical Threats Project (CTP) at the American Enterprise Institute and the Institute for the Study of War (ISW), both named and identifiable analytical organizations.*
</Summary>

<Summary source="https://www.whitehouse.gov/articles/2026/03/the-iranian-regimes-decades-of-terrorism-against-american-citizens/">
## Summary: White House Fact Sheet on Iranian Regime's Attacks on Americans (March 2, 2026)

**Source:** The White House (official government publication)
**Date:** March 2, 2026

### Key Content

This White House document presents a chronological record of attacks attributed to Iran and Iran-backed groups against American citizens and service members, spanning from 1979 to 2025. It frames the Trump Administration's military actions against Iran (described as "destroying Iran's missiles, annihilating their navy") as a response to this history.

### Key Statistics Cited
- **241 U.S. military personnel** killed in the 1983 Beirut Marine barracks bombing
- **At least 603 U.S. troops** killed by Iran-backed militias in Iraq between 2003–2011, described as "roughly one in every six American combat fatalities in Iraq"
- **46 Americans killed** and at least **12 kidnapped** in the October 7, 2023 Hamas massacre
- **More than 180 attacks** against U.S. forces between October 2023 and November 2024, wounding 180+ service members and killing three
- **109 U.S. troops** suffered traumatic brain injuries in a January 2020 Iranian ballistic missile attack

### Notable Recent Events Referenced
- **November 2024:** An Iranian national and IRGC asset charged for plotting to assassinate President Trump
- **June 2025:** Iran-backed militias attacked at least three U.S. bases in Syria and two in Iraq

### Relevance to IRGC Search Interest
The document explicitly names the **IRGC (Islamic Revolutionary Guard Corps)** multiple times, including a January 2007 incident where IRGC Quds Force members killed five U.S. soldiers, and the November 2024 assassination plot. The White House's publication of this document on **March 2, 2026** — coinciding with the start of the trend measurement window — suggests a deliberate effort to build public justification for military action against Iran, which could drive elevated search interest in "IRGC" during the measurement period.
</Summary>


<Agent_report>
Query: Using Google Trends daily data for "irgc" in the United States from 2024-01-01 to 2026-03-01, calculate the distribution of 12-day interest changes and the frequency with which the absolute change exceeds 3 points; provide mean, median, and 90th percentile change sizes.
The task requires a purely empirical deliverable:  
(1) the full distribution of 12-day changes in Google-Trends “interest-over-time” values for the topic “irgc” in the United States between 1 Jan 2024 and 1 Mar 2026;  
(2) the share of those 12-day changes whose absolute value is larger than 3 index points; and  
(3) summary statistics for the size of the 12-day changes (mean, median, 90th percentile).

What the search results do – and do not – give us  

1. Availability of daily data  
   • Google Trends’ web interface will only serve DAILY data if the requested window is ≤ 269 days; otherwise it down-samples to weekly values (PytrendsLongitudinalR vignette, CRAN).  
   • To obtain a daily series over > 2 years one must stitch together a sequence of ≤ 269-day requests and re-scale them so all sub-segments share one common 0-to-100 scale. Tools that automate this include:   
     – Pytrends Longitudinal R (CRAN vignettes)  
     – Python’s pytrends library together with the “anchor-window” re-scaling technique described in the pytrends FAQ and various blog posts.  
   • Google announced an official Trends API (alpha) in July 2025 that returns “consistently scaled” daily data for any span up to five years (Google Developers blog, 24 Jul 2025). If one already has access to that alpha, the entire 2024-01-01 → 2026-03-01 daily series can be fetched in a single call; otherwise the stitching method above is required.

2. Data actually retrieved  
   None of the returned search snippets contains the raw daily values for “irgc”, nor any ready-made CSV covering the 2024-01-01 → 2026-03-01 window. The White-House and Treasury-OFAC articles, CFR backgrounder, and other narrative pieces are topical context only; the technical hits (AnalyticsHacker Google-Sheets tool, CRAN PytrendsLongitudinalR, etc.) explain how to pull the data but do not embed it.

3. Implications for the numerical calculations requested  
   Because the underlying daily numbers are missing, the required calculations (rolling 12-day differences, absolute-change>3 frequency, mean/median/90th-percentile) cannot be executed from the material at hand. All methodological ingredients are known, but the essential input data are absent.

How the calculations would be carried out once the daily series is in hand  

Step 1  Acquire daily values of “irgc” interest in the US, fixed-scale, 2024-01-01 to 2026-03-01.  
   • If using the official API (alpha): one API call with parameters  
     – geo=US,  
     – date_start=2024-01-01, date_end=2026-03-01,  
     – time_granularity=daily.  
   • If using pytrends / PytrendsLongitudinalR: break the 791-day interval into four overlapping 269-day blocks, pull each block, then apply the anchor-window re-scaling so that all four blocks share a common index.

Step 2  Compute 12-day changes  
   • For every day t ≥ 2024-01-13 calculate Δ₁₂(t) = value(t) – value(t-12).  
   • That produces 779 observations.

Step 3  Describe the distribution  
   • Absolute-change-greater-than-3 frequency:  
     freq = count{|Δ₁₂| > 3} / 779.  
   • Mean, median, 90th percentile of the signed changes (or of |Δ₁₂| if magnitude is requested) obtained directly from the vector Δ₁₂.

What additional information is still needed  
• The actual day-by-day index values. Without them, no descriptive statistics can be produced.  
• Confirmation that the “irgc” identifier used is the Google Trends TOPIC (preferred, because it aggregates spelling variants) rather than the literal search string; this affects the API request syntax (topic code looks like “/m/0123abc”).  
• If the forthcoming Google Trends API is not accessible, a decision on which stitching technique and reference anchor to use (e.g., “US-CA” sub-series as anchor, as suggested in PytrendsLongitudinalR vignette).

Conclusion  
All methodological steps are documented in the retrieved sources (CRAN PytrendsLongitudinalR vignette; AnalyticsHacker Google-Sheets exporter; Google Trends API announcement). However, the key empirical input—the 791-day daily time series for “irgc” in the United States—is not included in those sources, so the requested distribution, exceedance frequency, and summary statistics cannot yet be computed. Acquiring that series (via the official API or a stitched pytrends workflow) is the sole missing piece needed to complete the calculation.</Agent_report>


The information has been sourced from the internet and language models (for agent reports). Exercise healthy skepticism toward unverified claims.

Your analysis should have the following components, referring to the above historical context:
(a) Source analysis: Briefly summarize each information source (either web article or Agent report), evaluate source quality and date.
**Opinions are commonplace in writing. For each source, you must be able to discern factual information from opinions. You are advised to strongly consider only opinions originating from identifiable experts or entities**.
(b) Reference class analysis: Identify a few possible reference classes and evaluate respective suitabilities to the forecasting question. If applicable, choose the most suitable one.
(c) Timeframe analysis: State the prediction timeframe (e.g., how many days/months from now?) and examine historical patterns over similar periods
(d) Justification: Integrate the above factors with other points you found relevant to write a justification for your outside view prediction.

Subsequently, calibrate your outside view prediction, considering:
(a) You aim to predict the true probability of events occurring, not a hedged or overconfident projection of your beliefs.
(b) Are there previously established distributions concerning the options that you can tether your prediction to?
(c) Small differences in probabilities can be significant: 90% is a 9:1 odds and 99% is a 99:1 odds.
(d) Historically, what is the rate of upsets/unexpected outcomes in the domain of this forecasting question? How should this affect your probability distribution?

Format your answer as below:

Analysis:
{Insert your analysis here, following the above components.}

Outside view calibration:
{Insert your calibration of your outside view prediction here.}

Outside View Prediction:
Write your final probabilities as whole percentages for the options in this order ['Increases', "Doesn't change", 'Decreases']:
Option_A: Probability_A
Option_B: Probability_B
...
Option_N: Probability_N
