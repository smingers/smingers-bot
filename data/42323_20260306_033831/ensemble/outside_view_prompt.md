
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
As of April 30, 2026, what will be the cumulative number of people detected arriving in the UK in small boats in 2026?

Question background:
Cumulative small boat arrivals are a high-salience operational and political metric for UK border policy, asylum processing capacity, and enforcement strategy.

`{"format":"bot_tournament_question","info":{"hash_id":"443aaf6af8122063","sheet_id":259.0}}`

The options are: ['0–5,000', '5,001–10,000', '10,001–20,000', '20,001+']

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question resolves to the option whose range contains the cumulative total number of people detected arriving in the UK in small boats from January 1, 2026 through April 30, 2026 (inclusive), as recorded in the Home Office small boats time series dataset available before May 1, 2026. The primary source is the Home Office dataset file at https://assets.publishing.service.gov.uk/media/6793689a5dc1be141475ff84/small_boats_time_series.ods.

Additional fine-print:
Compute the cumulative total by summing the daily “arrivals” (people detected arriving) values for all dates from January 1, 2026 through April 30, 2026 inclusive, using the values in the primary dataset as available before May 1, 2026. If the dataset is revised after May 1, 2026, ignore those later revisions. If the primary dataset is unavailable at resolution time, resolve using credible sources per https://www.metaculus.com/faq/#definitions. Candidate Sources: UK Home Office small boat activity statistics landing page at https://www.gov.uk/government/statistics/small-boat-activity

Question metadata:
- Opened for forecasting: 2026-03-06T03:00:00Z
- Resolves: 2026-04-30T00:00:00Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-06T03:00:00Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-06. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-06 should not be considered as speculative but rather an historical document.

Historical context:

<Summary source="https://www.telegraph.co.uk/news/2025/01/27/small-boat-tracker-how-many-people-cross-the-channel/">
This summary is based on the provided article from *The Telegraph*, dated February 26, 2026.

### 1. Facts, Statistics, and Objective Measurements
*   **Historical Totals:** Nearly 200,000 migrants have crossed the English Channel in small boats since records began in 2018.
*   **Annual Comparisons:**
    *   **2025:** 41,472 arrivals.
    *   **2024:** 36,816 arrivals.
    *   **2022 (Record High):** 45,755 arrivals.
*   **Nationalities (2025 Data):** The top three countries of origin in 2025 were Eritrea (7,602), Afghanistan (4,755), and Iran (4,489).
*   **Nationalities (Long-term):** Iran has the highest cumulative total since 2018 (30,269). The single-year record for one nationality was 12,658 Albanians in 2022.
*   **Asylum Data:** 93% of arrivals between 2018 and 2024 claimed asylum. Approximately 50% of applicants are granted protection at the initial decision stage.
*   **Daily Records:**
    *   **All-time record:** 1,305 migrants on September 3, 2022.
    *   **Starmer Administration record:** 1,195 migrants on May 31 (year implied 2025).
*   **Safety and Logistics:** 59 people drowned in 2024 according to the IOM. While total migrant numbers have increased, the number of boats has remained steady, indicating increased overcrowding per vessel.
*   **Geography:** The crossing spans 21 miles at its narrowest point (Pas-de-Calais to Kent).

### 2. Opinions from Reliable and Named Sources
*   **The Home Office:** Notes that weekly published data may differ from official quarterly statistics, as the latter undergo a more thorough quality assurance process.
*   **International Organization for Migration (IOM):** Reported 59 drownings in the Channel in 2024.
*   **UK Government (Labour Party):** Defined the mission of the new Border Security Command as "smashing the criminal smuggling gangs."
*   **Sir Keir Starmer:** Unveiled a "one in, one out" returns deal with France one year after taking office.

### 3. Potentially Useful Opinions from Less Reliable/Not-named Sources
*   **The Telegraph (Authorial Analysis):** The article asserts there is "little evidence to suggest the tide is turning," noting that average weekly crossings under Prime Minister Starmer remain "significantly higher" than those under predecessors Rishi Sunak or Boris Johnson.
*   **General Observation:** The article notes that smugglers are showing an "increasing willingness" to severely overcrowd dinghies that are often in poor condition.
</Summary>

<Summary source="https://www.statista.com/statistics/1171253/small-boat-channel-crossings-in-the-uk/?srsltid=AfmBOooDuod2q4ZiDZmYmJG6kZw30NeX2I8wWDwgnUOU76Ob0z51bcSY">
This summary is based on the provided Statista page regarding UK small boat crossings. Please note that the provided text consists primarily of bibliographic citations and metadata rather than a detailed narrative report.

### 1. Facts, Statistics, and Objective Measurements
The article provides a historical time series of the number of people detected arriving in the UK (or heading toward the UK) in small boats. The data, sourced from the **UK Home Office** and **GOV.UK**, covers the following period:
*   **Timeframe:** 2018 to 2024.
*   **Data Source:** UK Home Office official statistics.
*   **Publication/Update Date:** The statistics were updated/published on **May 22, 2025**.
*   **Access Date:** The information was retrieved from the Statista platform on **March 6, 2026**.

### 2. Opinions from Reliable and Named Sources
*   **UK Home Office / GOV.UK:** These are the primary official sources cited for the data. While the provided text does not include specific qualitative commentary from these bodies, the data itself represents the official government record of small boat detections for the years 2018 through 2024.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   The provided text does not contain opinions from unnamed or less reliable sources; it is restricted to the citation of official government data hosted on the Statista platform.

***

**Note for the Forecaster:** While this source confirms the availability of official Home Office data through the end of 2024, it does not provide specific figures for 2025 or the first quarter of 2026. However, it establishes the **UK Home Office** as the definitive authority for the "small boat activity" metrics required to resolve your forecasting question.
</Summary>

<Summary source="https://www.gov.uk/government/publications/migrants-detected-crossing-the-english-channel-in-small-boats/migrants-detected-crossing-the-english-channel-in-small-boats-last-7-days">
This summary is based on the provided GOV.UK landing page regarding small boat arrivals. Please note that the provided text serves as a methodological overview and data directory rather than a report of specific recent figures.

### 1. Facts, Statistics, and Objective Measurements
*   **Data Scope:** The source tracks migrants attempting to cross the English Channel in small boats without permission to enter the UK, including those intercepted at sea and those involved in "uncontrolled landings" (arriving without prior interception).
*   **Vessel Definitions:** A "small boat" is defined as a vessel used to cross the Channel for unauthorized entry; the most common types are **rigid-hulled inflatable boats (RHIBs), dinghies, and kayaks**.
*   **Reporting Frequency:**
    *   The page provides figures for the **last 7 days**.
    *   A daily arrival time series is available dating back to **January 1, 2018**.
    *   Weekly "small boat preventions" data is available from **April 29, 2024**.
*   **Data Categorization:** "Boats involved in uncontrolled landings" are a specific subset of "boats detected." However, all individuals from both categories are aggregated into the "migrants arrived" count.

### 2. Opinions from Reliable and Named Sources
*   **UK Home Office (GOV.UK):** The Home Office designates the **"Immigration system statistics" quarterly release** as the "final and authoritative statistics" on small boat arrivals and other illegal entry routes.
*   **Official Methodology:** The source explicitly links the "migrants arrived" metric to both those intercepted by authorities and those who land undetected but are subsequently recorded.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   *None identified in the provided text.*
</Summary>


<Summary source="https://www.bbc.com/news/articles/cly07pyde00o">
This summary focuses on the key metrics and trends from the BBC article dated February 26, 2026, regarding UK asylum and small boat arrivals.

### 1. Facts, Statistics, and Objective Measurements

**Small Boat Arrivals and Asylum Claims (2025 Data):**
*   **Total Small Boat Arrivals:** 41,262 people arrived via small boats in 2025, a **13%
</Summary>

<Summary source="https://www.nbcrightnow.com/national/near-record-number-of-small-boat-migrants-reach-uk-in-2025/article_cb4b8d5d-2482-59f9-b5b8-94d5086c1ecf.html">
This summary focuses on the key data points and political context from the provided article regarding small boat arrivals in the UK, relevant to forecasting 2026 trends.

### **1. Facts, Statistics, and Objective Measurements**
*   **2025 Annual Total:** A total of **41,472 migrants** arrived in the UK via small boats in 2025. This is the second-highest annual figure since records began in 2018.
*   **Historical Record:** The highest annual total remains **45,774 arrivals**, recorded in 2022.
*   **Asylum Applications:** Approximately **111,000 asylum applications** were made in the year ending June 2025, a record high.
*   **Returns Deal Performance:** Under a "one-in one-out" returns deal with France, **153 people** were removed from the UK to France, while **134 people** were brought to the UK from France.
*   **Protest Activity:** In September 2025, an estimated **150,000 people** participated in a far-right protest in London regarding immigration.

### **2. Opinions and Policy Stances from Named/Reliable Sources**
*   **Home Office / Interior Ministry:** A spokesperson described the number of crossings as **"shameful"** in December 2025.
*   **Shabana Mahmood (Home Secretary):** Stated in November 2025 that irregular migration was **"tearing our country apart."** She has proposed "sweeping reforms," including a drastic reduction in refugee protections and ending automatic benefits for asylum seekers to remove incentives for arrivals.
*   **Alex Norris (Minister for Border Security and Asylum):** Described the returns deal with France as a **"landmark one-in one-out scheme"** that allows the UK to send small boat arrivals back to France.
*   **Keir Starmer (Prime Minister):** Pledged to **"smash the gangs"** by dismantling smuggling networks, though the article notes he has had no more success than his predecessors.
*   **Nigel Farage (Reform UK Leader):** Predicted that his party—which led Labour by double digits in polls for most of 2025—could win the next general election (due by 2029) if they perform well in the **May 2026 local elections**.
*   **Rishi Sunak (Former Prime Minister):** Expressed regret over his "stop the boats" slogan, calling it **"too stark and binary"** for the complexity of the challenge.

### **3. Potentially Useful Context from the Article**
*   **Policy Inspiration:** The UK government is reportedly modeling new migration policies after **Denmark’s coalition government**, which has implemented some of Europe’s strictest policies, resulting in a 40-year low in successful asylum claims.
*   **Internal Political Pressure:** The article notes that Starmer faces a "thorny" situation: pressure from the right (Reform UK) to curb arrivals, and potential opposition from left-wing Labour lawmakers who fear losing voters to the Green Party if migration policies become too restrictive.
</Summary>

<Summary source="https://www.lemonde.fr/en/international/article/2026/01/02/small-boat-migrants-reached-uk-in-near-record-numbers-in-2025_6749012_4.html">
This summary focuses on the key data points and political developments from the provided *Le Monde* article relevant to small boat arrivals in the UK.

### **1. Facts, Statistics, and Objective Measurements**
*   **2025 Annual Total:** A total of **41,472 migrants** arrived in the UK via small boats in 2025. This is the second-highest annual total since records began in 2018.
*   **Historical Record:** The record for arrivals remains **45,774**, set in 2022.
*   **Asylum Claims:** Approximately **111,000 asylum applications** were made in the year ending June 2025, a record high.
*   **Returns Deal Data:** Under a "one-in one-out" scheme with France, **153 people** were removed from the UK to France, while **134 people** were brought to the UK from France.
*   **Protest Scale:** In September 2025, an estimated **150,000 people** participated in a far-right protest in London regarding immigration.

### **2. Opinions and Policy Statements from Named/Reliable Sources**
*   **Home Office / Interior Ministry:** A spokesperson described the number of crossings as **"shameful"** and stated that "sweeping reforms" are intended to remove incentives for arrivals.
*   **Shabana Mahmood (Home Secretary):** Stated in November 2025 that irregular migration was **"tearing our country apart."** She has proposed a "drastic reduction" in refugee protections and the ending of automatic benefits for asylum seekers.
*   **Alex Norris (Border Security and Asylum Minister):** Characterized the returns deal with France as a **"landmark"** scheme that allows the UK to send small boat arrivals back to France.
*   **Keir Starmer (Prime Minister):** Pledged to **"smash the gangs"** by dismantling smuggling networks, though the article notes he has had "no more success than his predecessor" as of early 2026.
*   **Nigel Farage (Reform UK Leader):** Predicted that his party’s success in upcoming local elections could lead to winning the 2029 general election and **"fundamentally changing the whole system of government."**
*   **Rishi Sunak (Former Prime Minister):** Expressed regret over his **"stop the boats"** slogan, calling it too "stark" and "binary" for the complexity of the challenge.

### **3. Contextual Trends and Unnamed Sources**
*   **Political Pressure:** The article notes that the Labour government is under significant pressure as **Reform UK** has led the Labour Party by double-digit margins in opinion polls for most of 2025.
*   **Policy Inspiration:** Senior British officials are reportedly looking to **Denmark’s center-left government** as a model for strict migration policies, where successful asylum claims are at a 40-year low.
*   **Internal Opposition:** The article mentions that the government's proposed restrictive plans will likely face opposition from **left-wing Labour lawmakers** who fear losing voters to the Green Party.
</Summary>


<Summary source="https://www.statista.com/statistics/1171253/small-boat-channel-crossings-in-the-uk/?srsltid=AfmBOoqN8rgSF_h5wF-4naj3fPiYaoM-QiaMDeCqBJwZUUJrbb1X7VW9">
This summary is based on the provided Statista document titled **"UK small boat crossings 2024."**

### 1. Facts, Statistics, and Objective Measurements
The article provides a historical time series of the number of people detected arriving in the UK (or heading to the UK) via small boats. The data, sourced from the **UK Home Office** and **GOV.UK**, covers the period from 2018 to 2024:

*   **2018:** 299 arrivals
*   **2019:** 1,843 arrivals
*   **2020:** 8,462 arrivals
*   **2021:** 28,526 arrivals
*   **2022:** 45,755 arrivals
*   **2023:** 29,437 arrivals
*   **2024:** 29,237 arrivals (Note: While the title mentions 2024, the data provided in the text reflects the annual totals leading up to the end of that year).

### 2. Opinions from Reliable and Named Sources
*   **UK Home Office & GOV.UK:** These are the primary official sources for the data presented. The statistics are categorized under "Migration in the UK," specifically focusing on "Visas & Asylum" and "Nationality."
*   **Statista:** Acts as the aggregator and publisher of this data, providing the platform for tracking these metrics over time.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   The provided text does not contain qualitative opinions or commentary from unnamed sources; it is strictly a data-reporting document focused on official government figures.

***

**Note on Data Context:** The document was accessed on March 6, 2026, but the specific dataset summarized concludes with the 2024 annual figures as reported by the Home Office on May 22, 2025. It does not contain specific monthly breakdowns for the first quarter of any year, nor does it contain 2025 or 2026 figures.
</Summary>

<Summary source="https://www.theguardian.com/uk-news/2025/jan/01/uk-small-boat-arrivals-in-2024-up-25-compared-with-previous-year">
This summary provides the key data points and contextual information from the *Guardian* article dated January 1, 2025, regarding UK small boat arrivals.

### 1. Facts, Statistics, and Objective Measurements
The article provides a detailed breakdown of Home Office and PA Media data regarding small boat arrivals:

*   **2024 Annual Total:** 36,816 people arrived in the UK via small boats in 2024, a **25% increase** from 2023 (29,437) but lower than the 2022 record (45,774).
*   **Historical Annual Totals:**
    *   **2018:** 299
    *   **2019:** 1,843
    *   **2020:** 8,466
    *   **2021:** 28,526
    *   **2022:** 45,774
    *   **2023:** 29,437
    *   **2024:** 36,816
*   **Early Year Performance (Jan 1 – July 5):** In 2024, 13,574 people arrived by July 5. This was a record for that specific period, representing a **19% increase** over the same period in 2023 (11,433) and a **5% increase** over 2022 (12,900).
*   **Late Year Performance (July 5 – Dec 31):** 23,242 people arrived during this period in 2024, a **29% increase** over the same period in 2023 (18,004) but a **29% decrease** compared to 2022 (32,855).
*   **Recent Activity:** The final crossings of 2024 occurred on December 29 (291 people in six boats). No crossings occurred on December 30 or 31 due to blustery weather.
*   **Fatalities:** 2024 was the deadliest year on record for crossings, with **53 deaths** recorded by the French coastguard.
*   **Enforcement:** The National Crime Agency (NCA) is currently leading approximately 70 live investigations into human trafficking and organized immigration crime.

### 2. Opinions from Reliable and Named Sources
*   **Prime Minister Keir Starmer:** Stated the Rwanda deportation plan is "dead and buried." He attributed the record arrivals in the first half of 2024 to the previous government's focus on "gimmicks" rather than dismantling smuggling gangs. His strategy focuses on international law enforcement cooperation and restricting the supply of boats and engines.
*   **Home Secretary Yvette Cooper:** Stated the government has a "moral responsibility" to tackle crossings but **refused to set a specific deadline** or target date for when arrival numbers would fall sharply. She emphasized targeting gangs over creating new safe and legal routes.
*   **Home Office:** Provided the provisional figures confirming 2024 as the second-highest year for arrivals since records began in 2018.

### 3. Contextual Policy Information
*   **Policy Shifts:** The Rwanda scheme was officially scrapped following the Labour Party's general election victory on July 5, 2024.
*   **New Initiatives:** The current government has established a new "Border Security Command" and intends to treat people smugglers with the same urgency as terrorists.
</Summary>

<Summary source="https://news.sky.com/story/small-boat-migrant-crossings-in-2024-surpass-last-years-total-two-months-early-13448041">
This summary is based on the provided Sky News article dated October 22, 2025.

### **1. Facts, Statistics, and Objective Measurements**
*   **2025 Cumulative Total (to date):** As of October 22, 2025, more than **36,816** people have crossed the English Channel in small boats.
*   **Comparison to 2024:** The 2025 total surpassed the entire 2024 annual total (36,816) by late October, two months earlier than the previous year.
*   **First Half of 2025:** There was a **50% increase** in arrivals during the first six months of 2025 compared to the same period in 2024.
    *   **Jan 1 – July 1, 2025:** 19,982 arrivals (a record high for the first half of any year since records began in 2018).
    *   **Jan 1 – July 1, 2024:** 13,489 arrivals.
*   **Historical Peak:** 2022 remains the year with the highest annual total on record, with **45,755** crossings.
*   **Returns/Deportations:** Under a "one in, one out" agreement with France, the UK has removed **42** illegal migrants to France and accepted **16** asylum seekers in return.
*   **General Enforcement:** The government reports having detained and removed more than **35,000** individuals who were in the UK illegally (timeframe not specified, but presented in the context of current government action).

### **2. Opinions from Reliable and Named Sources**
*   **Home Office Sources:** Confirmed that 2025 arrivals have already exceeded the total for 2024.
*   **Shabana Mahmood (Home Secretary):** Described the figures as "shameful" and blamed the previous government for leaving borders in "crisis." She stated the government is taking action through the deal with France and intends to go "further and faster" to stop crossings and restore border order.
*   **Chris Philp (Shadow Home Secretary):** Criticized the government, claiming "the floodgates are open" and describing the Channel as a "conveyor belt for illegal immigration." He characterized the current deportation efforts as a "revolving-door deportation scheme" and a "national humiliation."
*   **Keir Starmer (Prime Minister):** Has stated his mission is to "smash the gangs" responsible for the small boat crossings.

### **3. Potentially Useful Information from Less Reliable/Unspecified Sources**
*   **Sky News "Understanding":** The article notes that while official daily figures for Wednesday (Oct 22) were not yet published, Sky News understands from sources that the 2024 threshold has been crossed.
*   **Unnamed Sources:** Reported a specific instance of an Iranian national who was deported to France under the new treaty but successfully returned to the UK via a small boat and was subsequently detained.
</Summary>


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
Write your final probabilities as whole percentages for the options in this order ['0–5,000', '5,001–10,000', '10,001–20,000', '20,001+']:
Option_A: Probability_A
Option_B: Probability_B
...
Option_N: Probability_N
