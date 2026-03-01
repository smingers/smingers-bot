
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
Will Cloudflare experience another critical incident before May 2026?

Question background:
[Cloudflare](https://en.wikipedia.org/wiki/Cloudflare) is an internet infrastructure company which acts as intermediary for a significant portion of global internet traffic. Used by over 20% of websites, the company's infrastructure covers many of the worlds most popular sites.&#x20;

When Cloudflare undergoes significant issues, major portions of the global internet can fail. During both [November](https://www.theguardian.com/technology/2025/nov/18/cloudflare-outage-causes-error-messages-across-the-internet) and [December](https://apnews.com/article/internet-outage-cloudflare-zoom-linkedin-2ac314f7dcd112a63eb12b30afb74a33) 2025, Cloudflare experienced major outages due to internal changes leading to bugs in their system. Although brief, these issues caused massive global disruption, with users being unable to access a wide breadth of websites, including Metaculus itself.

On [February 4, 2026](https://www.cloudflarestatus.com/incidents/gx9nbv7l3yqs), Cloudflare experienced a critical incident in which live broadcasts were unable to function. Although limited in scope, this issue severely affected any ongoing broadcasts.

`{"format":"metac_reveal_and_close_in_period","info":{"post_id":42284,"question_id":42071}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question will resolve as Yes if after February 25, 2026 and before May 1, 2026, Cloudflare experiences a critical incident.

The primary source for this question will be the [Cloudflare Status Page](https://www.cloudflarestatus.com/history), with critical incidents shown in red.

Additional fine-print:
This question will only consider reporting and categorisation directly from Cloudflare. If Cloudflare changes their categorisation scheme such that no comparable category exists, this question will be annulled.

***
This question's information (resolution criteria, fine print, background info, etc) is synced with an [original identical question](https://www.metaculus.com/questions/42284) which opened on 2026-02-25 17:00:00. This question will resolve based on the resolution criteria and fine print contained above. However, if this question would resolve differently than the original question, then this question will be annulled. Additionally, if the original question's resolution could have been known before this question opened, then this question will be annulled.

Question metadata:
- Opened for forecasting: 2026-03-01T15:30:00Z
- Resolves: 2026-04-01T01:00:00Z
- Note: Unless the question title specifies otherwise, the Forecast Opening Date of 2026-03-01T15:30:00Z should be considered the start of the question's resolution window. Events before this date do not count toward resolution.

IMPORTANT: Today's date is 2026-03-01. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-03-01 should not be considered as speculative but rather an historical document.

Historical context:

<QuestionSource url="https://en.wikipedia.org/wiki/Cloudflare">
## Summary: Cloudflare Wikipedia Article

### Company Overview
Cloudflare is an American internet infrastructure company founded in 2009, providing CDN services, cybersecurity, DDoS mitigation, and domain registration. As of January 2026, it serves approximately **21.3% of all websites** on the internet, handling an average of **45 million HTTP requests per second** as of 2023. The company went public on the NYSE in 2019 (ticker: NET).

---

### Relevant Incident History

**Cloudbleed (2016–2017):** A major bug leaked sensitive data including passwords and authentication tokens from customer websites for approximately six months.

**November 18, 2025 Outage:**
- A major global outage caused widespread 500 errors
- Affected services included Twitter, Spotify, Uber, DoorDash, ChatGPT, Microsoft Copilot, League of Legends, and many others
- Cloudflare's VPN service (WARP) was briefly disabled in London
- A Cloudflare spokesperson acknowledged "a spike in unusual" activity during the incident

**December 2025:** The article references a second significant outage period (details truncated), coinciding with a record-breaking 31.4 tbps DDoS attack dubbed "The Night Before Christmas."

---

### Scale & Infrastructure Context
Given Cloudflare's role as intermediary for over 20% of global web traffic, any critical incident has **outsized global impact**. The company's recent history shows multiple significant incidents within a short timeframe (November and December 2025), suggesting operational vulnerability during periods of rapid expansion and infrastructure change.

---

*Note: The article was truncated before completing the December 2025 outage section, so full details of that incident are unavailable from this source.*
</QuestionSource>

<QuestionSource url="https://www.theguardian.com/technology/2025/nov/18/cloudflare-outage-causes-error-messages-across-the-internet">
## Summary: Cloudflare Outage – November 18, 2025 (The Guardian)

**What Happened:**
Cloudflare experienced a global outage on November 18, 2025, causing widespread error messages across the internet. Users were unable to access some Cloudflare-protected websites, and site owners lost access to their performance dashboards. Sites including X (formerly Twitter) and OpenAI also reported increased outages concurrently, according to Downdetector.

**Timeline:**
- Outage reported at **11:48 AM London time**
- By **2:48 PM**, Cloudflare announced a fix had been implemented and believed the incident resolved, while continuing to monitor services

**Root Cause:**
Cloudflare identified the cause as **a configuration file automatically generated to manage threat traffic**, which grew beyond its expected size and triggered a crash in the software system handling traffic for several of Cloudflare's services. The company explicitly stated there was **no evidence of malicious activity or attack**.

**Impact:**
- Cloudflare's Warp encryption service was disabled in London as part of mitigation efforts
- Some service degradation was expected post-incident due to natural traffic spikes

**Expert Commentary:**
- **Prof. Alan Woodward (Surrey Centre for Cyber Security)** described Cloudflare as a "gatekeeper" for internet traffic, noting the outage highlighted how few major infrastructure companies exist — making failures immediately and broadly visible
- A **Cloudflare spokesperson** apologized and committed to learning from the incident
</QuestionSource>

<QuestionSource url="https://apnews.com/article/internet-outage-cloudflare-zoom-linkedin-2ac314f7dcd112a63eb12b30afb74a33">
## Summary: AP News – Cloudflare Outage (December 5, 2025)

### Key Facts
- Cloudflare experienced a service outage on Friday morning (December 5, 2025), bringing down major global websites including **LinkedIn and Zoom**
- This was the **second major outage in less than three weeks** (following a November 2025 incident)
- Cloudflare confirmed the issue was **not due to an attack**
- The cause was identified as **a change to how its firewall handles requests**, which made Cloudflare's network unavailable for **"several minutes"**
- Cloudflare was also investigating issues with its **Dashboard and related APIs**
- Service was fully restored by the time of the report

### Named Expert Opinion
- **Richard Ford, CTO at Integrity 360** (Europe/Africa-based cybersecurity firm): Characterized the incident as "a database change made as part of planned maintenance that just went slightly awry," which "effectively overloaded their systems"
- Ford also noted a broader trend: *"We are seeing the frequency increase as organizations put more eggs in fewer baskets"* as the scale of operations at companies like Cloudflare, AWS, Google Cloud, and Microsoft Azure grows

### Context
- The **November 2025 Cloudflare outage** lasted three hours and affected ChatGPT, "League of Legends," and the New Jersey Transit system
- Similar configuration-related outages also affected **Microsoft Azure** and **Amazon Web Services** in recent months
</QuestionSource>


<Summary source="https://www.datayard.us/blog/the-cloudflare-outage-took-down-parts-of-the-internet-heres-what-businesses-can-learn-from-it/">
## Summary: Top Cybersecurity Risks for Manufacturers in 2025 (Datayard.us, December 1, 2025)

This article primarily focuses on the **Cloudflare outage of November 18, 2025**, using it as a case study for cybersecurity and infrastructure risk for manufacturers and businesses.

### Key Facts About the November 18, 2025 Cloudflare Outage:
- **Started:** 11:20 AM UTC, November 18, 2025
- **Root cause:** A misconfigured database permission allowed a Bot Management feature file to grow uncontrollably large, overwhelming Cloudflare's routing and proxy systems and causing cascading crashes globally
- **Services affected:** CDN delivery, DNS, WAF, Access, Workers KV (caching), and the Cloudflare Dashboard
- **Duration:** Approximately **six hours** of widespread disruption
- **Initial misdiagnosis:** Early diagnostics suggested a possible malicious attack; Cloudflare later confirmed it was an internal misconfiguration, not a security event
- **Recovery:** Services restored gradually, with impact varying by region and setup

### Named Source Opinion:
- **Cloudflare CEO Matthew Prince** stated: *"An outage like today is unacceptable... On behalf of the entire team at Cloudflare, I would like to apologize for the pain we caused the Internet today."*

### Cloudflare's Identified Areas for Improvement (per their postmortem):
- More robust file size validation for features like Bot Management
- Stronger observability and diagnostic tools
- Improved safeguards and testing before global configuration rollouts

### Broader Takeaways Offered by Datayard:
- Major provider outages are described as **relatively rare** but high-impact due to centralized dependency
- The article recommends resilience planning, vendor diversification, and failover testing rather than abandoning Cloudflare
</Summary>

<Summary source="https://www.cloudflarestatus.com/">
## Summary of Cloudflare Status Page Content

**Note:** The extracted content appears to be a mix of incident updates and scheduled maintenance notices, without clear severity classifications (e.g., "critical" labels) visible in the extracted text.

### Active/Recent Incidents

**Incident 1: Newark, NJ Elevated Latency (Feb 16–27, 2026)**
- **Started:** Feb 16, 2026 at 10:19 UTC
- **Nature:** Elevated latency affecting a subset of HTTP requests in the Newark, NJ datacenter; some customers using Cloudflare's **Data Loss Prevention (DLP)** suite experienced intermittent errors
- **Progress:** Issue identified Feb 16; fix implemented and monitoring began Feb 26 at 10:12 UTC
- **Resolution update:** Feb 26–27 confirmed DLP services were **not impacted** by the incident; monitoring continued through Feb 27 at 13:40 UTC

**Incident 2: Peering Authentication Outage (Feb 27, 2026)**
- **Started:** Feb 27, 2026 at 02:27 UTC
- **Nature:** Issue impacting customers/peers using `peering.cloudflare.com`; authentication affected due to an **outage with a third-party authentication provider**
- **Scope:** Did **not** affect serving of cached files via Cloudflare CDN or other edge security features
- **Status:** Under investigation as of Feb 27 at 13:24 UTC; fix being worked on

### Scheduled Maintenance (Upcoming)
Multiple datacenters have scheduled maintenance windows, with possible traffic rerouting and latency increases:
- **BOG (Bogotá):** Mar 3, 15:00–20:00 UTC
- **TLL (Tallinn):** Mar 3–4
- **LIS (Lisbon):** Mar 4
- **GRU (São Paulo):** Mar 5
- **YYZ (Toronto):** Mar 6
- **PDX (Portland):** Mar 9–12 (multi-day windows, 14:00–23:59 UTC each day)
</Summary>

<Summary query="site:cloudflarestatus.com "[Critical]" 2023">No URLs returned from Google.</Summary>


<Summary source="https://www.itpro.com/infrastructure/networking/cloudflare-outage-explained-what-happened-who-was-impacted-and-how-was-it-resolved">
## Summary: Cloudflare Outage – February 21, 2026 (IT Pro, February 23, 2026)

### What Happened
Cloudflare experienced a **major outage lasting six hours and seven minutes** that affected customers using its **Bring Your Own IP (BYOIP)** service. A bug in a configuration change caused Cloudflare to **unintentionally withdraw customer IP prefixes via BGP (Border Gateway Protocol)**, making affected services and applications unreachable from the internet.

### Technical Details
- The problematic change was intended to **automate the manual removal of prefixes** from the BYOIP service, part of Cloudflare's internal "Code Orange: Fail Small" initiative.
- A **regularly running sub-task queried the API with a bug**, triggering the unintended withdrawals.
- Affected customers experienced **"BGP Path Hunting"**, where connections traversed networks searching for routes until timing out.
- Visitors to Cloudflare's **1.1.1.1 DNS resolver website** encountered HTTP 403 errors, though DNS resolution itself was unaffected.
- Approximately **1,100 prefixes were withdrawn** — roughly **a quarter of all BYOIP prefixes**.

### Impact
Notable affected services included **Uber, Workday, Minecraft, Wikipedia, and Microsoft Outlook**. Betting site Bet365 also publicly acknowledged disruption.

### Resolution & Response
- Cloudflare reversed the change, and some customers restored service independently via the Cloudflare dashboard.
- Cloudflare acknowledged the "unacceptably large blast radius" and committed to improving staged testing and correctness checks in its Addressing API.
</Summary>

<Summary source="https://controld.com/blog/biggest-cloudflare-outages/">
## Summary of Cloudflare Outage History Article

**Note:** The article appears to be truncated, cutting off mid-sentence during the description of the January 2023 incident. The summary below reflects only what was available.

---

### Key Facts and Historical Incidents

**November 18, 2025 (Most Recent Major Outage)**
- Described as Cloudflare's **worst outage since 2019**
- Affected roughly **1 in 5 webpages** and **1/3 of the world's 10,000 most popular websites**
- Major services impacted: X/Twitter, ChatGPT, Spotify, Canva, Zoom, Coinbase, Downdetector
- **Root cause:** A database permissions change in the Bot Management system caused a machine-learning feature file to grow abnormally large, crashing the core proxy software and generating HTTP 5xx errors
- Duration: ~11:20 UTC to ~14:30 UTC for core restoration; full cleanup by ~17:06 UTC
- Cloudflare committed to better configuration file validation and additional kill switches

**Other Notable Historical Outages:**
- **June 2019:** BGP routing issue via Verizon/DQE (~3 hours; affected Amazon, Google, Facebook)
- **July 2020:** Router misconfiguration in Atlanta (~1 hour; affected Shopify, Discord)
- **August 2020:** CenturyLink ISP fault (affected Hulu, Xbox Live)
- **June 2022:** Critical P0 incident lasting ~90 minutes (affected Fitbit, Peloton)
- **January 2023:** 121-minute outage affecting Workers Platform and Zero Trust (article truncated)

### General Context
The article frames Cloudflare outages as **recurring but typically brief**, often caused by internal configuration errors or upstream provider failures. Each incident tends to have **broad global impact** given Cloudflare's role serving over 20% of websites.
</Summary>


<Summary source="https://newsletter.pragmaticengineer.com/p/why-reliability-is-hard-at-scale">
## Article Summary: Infrastructure Outage Postmortems at Scale

**Note:** This article focuses primarily on Heroku, Google Cloud, and Neon outages — it does not directly discuss Cloudflare incidents. Its relevance to the forecasting question is indirect, as it provides context about the frequency and nature of critical infrastructure failures at large-scale providers.

---

### Key Findings

**Heroku's Major Outage (Primary Focus):**
- Heroku suffered what appears to be its **longest-ever outage**, with a timeline revealing significant operational failures:
  - 8 hours to publicly acknowledge the global outage
  - 11 hours to isolate the issue
  - **23 hours to fully resolve** the outage
  - 5 days to publish a postmortem
- **Root cause:** An automated Ubuntu 22.04 OS update triggered a `systemd` upgrade, which restarted `systemd-networkd`, flushing IP routing rules and severing outbound network connectivity for all affected dynos (virtual machines)
- Heroku's own internal tools and status page ran on the same affected infrastructure, **severely hampering their ability to respond and communicate**

**Striking Historical Parallel (Objective Fact):**
- The article identifies that Heroku's outage appears to have had an **almost identical root cause** to Datadog's largest-ever outage in 2023:
  - Same OS: Ubuntu 22.04
  - Same process: systemd
  - Same failure mode: restart clearing networking routes
- This suggests Heroku did not learn from a publicly documented prior incident

**Google Cloud:**
- A globally replicated configuration change triggered a **worldwide outage**
- Article notes that "failing open" and using feature flags for risky updates could have reduced outage duration by approximately two-thirds

**Neon (Serverless PostgreSQL):**
- Suffered typical PostgreSQL failure modes at scale, including **query plan drift and slow vacuum**, despite being PostgreSQL specialists

---

### Broader Thematic Observations (Article Authors' Opinions)
- The article argues Heroku's handling "bears the hallmarks of a company that has gone from being obsessed with reliability... to it being a backseat issue"
- Heroku's postmortem was described as a **"word salad" with few specifics**, contrasting with more transparent postmortems from other providers
- The article frames these outages as educational opportunities, noting that **failure to learn from others' documented incidents is a real and demonstrated risk**
</Summary>

<Summary source="https://blog.cloudflare.com/fail-small-resilience-plan/">
## Summary: Cloudflare's "Code Orange: Fail Small" Resilience Plan

### Context & Recent Incidents
Cloudflare experienced **two major global outages** in late 2025:
- **November 18, 2025**: Network failures lasting approximately **2 hours and 10 minutes**
- **December 5, 2025**: Network failures affecting **28% of applications** for approximately **25 minutes**
- **February 20, 2026**: A separate incident where BYOIP (Bring Your Own IP) customers had their BGP routes withdrawn

Both 2025 incidents followed the same pattern: **instantaneous global deployment of a configuration change** that caused cascading failures. The November incident stemmed from an automatic Bot Management classifier update; the December incident was triggered by a security tool change deployed to address a React framework vulnerability.

### Root Cause Identified
The core problem was a **disparity between how Cloudflare handles software updates vs. configuration changes**:
- **Software updates**: Deployed through controlled, monitored rollouts with multiple gates, starting with employee traffic, then progressively wider audiences, with automatic rollback capability
- **Configuration changes**: Deployed **instantly and globally** via a system called **Quicksilver**, reaching 90% of servers within seconds — with no equivalent staged rollout or automatic rollback

### The "Code Orange" Response
Cloudflare declared a **"Code Orange"** — a designation used only once previously — meaning this work is **prioritized above all other work** company-wide, with cross-functional teams pausing other projects. The plan is called **"Fail Small"**, organized into **three main workstreams** (not fully detailed in the extracted content), with iterative improvements rather than a single large change.

**Key planned changes include:**
1. **Controlled configuration rollouts via Quicksilver**: Treating configuration changes the same as code releases, with staged geographic and population-based deployment
2. **Health Mediated Deployment (HMD) for configurations**: Applying the existing software deployment framework — which requires teams to define success/failure metrics, rollout plans, and automatic rollback triggers — to configuration changes as well
3. **Improved isolation**: Preventing errors in one part of the network from cascading into the broader technology stack, including the customer-facing control plane

### Stated Goals
Cloudflare explicitly states they are **"deeply embarrassed"** by the incidents and expect that by the end of Code Orange, their network will be **"much more resilient"** to the types of issues that caused the recent global incidents.

---
*Note: The article extract appears to be cut off before fully describing all three Code Orange workstreams and some technical details. The summary reflects only what was present in the provided content.*
</Summary>

<Summary source="https://www.ilert.com/postmortems/cloudflare-outage-june-2025">
## Summary: Cloudflare Third-Party Storage Failure Event (June 12, 2025)

**Source:** Ilert (incident analysis/postmortem article) — *Note: Ilert is a third-party incident management platform, not Cloudflare itself. This is an analytical summary of the incident, not an official Cloudflare postmortem.*

---

### Incident Overview
On **June 12, 2025**, Cloudflare experienced a **high-severity global outage lasting approximately 2 hours and 28 minutes**, caused by a failure in the **third-party storage backend** powering **Workers KV** — a critical dependency for many of Cloudflare's core services.

### Services Affected
- **Near-total failure:** Access logins (100% errors), Stream Live (100% errors)
- **Partial degradation:** Images (~97% success rate), elevated CDN latency
- **Remained online:** DNS, Magic WAN, Transit, WAF (though downstream effects were observed)
- Other affected services: WARP, Gateway, Turnstile, Workers AI, Dashboard

### Timeline
| Time (UTC) | Event |
|---|---|
| 17:52 | WARP team detects device registration failures |
| 18:05 | Access team paged due to spiking error rates |
| 18:06 | Incident declared **P1** |
| 18:21 | Escalated to **P0** as global impact became clear |
| 18:43 | Access decoupled from Workers KV |
| 19:09 | Gateway graceful degradation initiated |
| 19:32 | Load shedding implemented |
| 20:23 | Third-party storage vendor comes back online |
| 20:25 | Access and Device Posture resume normal operation |
| 20:28 | Incident fully resolved |

### Key Metrics
- **MTTD (Mean Time to Detect):** ~13 minutes
- **MTTR (Mean Time to Resolve):** ~2 hours 36 minutes

### Root Cause & Contributing Factors
- Failure originated in a **third-party storage vendor** (not Cloudflare's own infrastructure)
- Key systemic risks identified: **single vendor dependency** and **fail-closed design** (secure-by-design policies led to disruption without fallback paths)
- Recovery tooling was still under development at the time of the incident

### Response & Communication
- Cloudflare followed internal runbooks and maintained **transparent, timely communication** via its status page and a subsequent postmortem
- The team operated with a **blameless, learning-focused culture**
- Noted weakness: users relying on indirect dependencies may not have had early visibility into the root cause

### Planned Improvements
- Better observability to reduce detection lag
- Improved fallback/graceful degradation design to reduce single-vendor dependency risk
</Summary>


<Agent_report>
Query: During 2018-2022 how many Cloudflare status incidents were labelled Critical and what was the average monthly frequency? Provide counts by year and note any clustering.
Summary of “Critical”-labelled incidents on Cloudflare’s public status page, 2018-2022  

Year  | Date(s) of Critical status incidents                                                     | Count  
2018  | No Critical incidents recorded in the sources reviewed                                    | 0  
2019  | 24 Jun 2019 – Global outage triggered by Verizon BGP route leak (Cloudflare declared a “P0 / Critical” incident on its status page) (controld.com blog) | 1  
2020  | 17 Jul 2020 – Worldwide traffic disruption after route-misconfiguration in Atlanta backbone (labelled Critical) (controld.com blog)  
      | 30 Aug 2020 – CenturyLink backbone failure propagated to Cloudflare; Cloudflare opened a “Critical P0” incident because all resolver and edge traffic through CenturyLink was unreachable (controld.com blog) | 2  
2021  | No Critical incidents surfaced in the status-page history or secondary reporting           | 0  
2022  | 21 Jun 2022 – Major network configuration error across 19 PoPs, opened as “Critical P0” (Site24x7 recap quoting Cloudflare status; controld.com blog) | 1  
TOTAL |                                                                                            | 4  

Average monthly frequency, 2018-2022  

• Period length: 60 months  
• Critical incidents: 4  
• Mean frequency: 4 / 60 ≈ 0.067 incidents per month, i.e. about one Critical incident every 15 months.

Clustering / dispersion observations  

• 3 of the 4 Critical incidents fell inside a 14-month window from June 2019 to August 2020, indicating a pronounced cluster.  
• After August 2020 there was a 22-month gap with no Critical events until June 2022.  
• Neither 2018 nor 2021 registered any Critical-labelled incidents in the available record, suggesting quieter years bracketed by two bursts of severe outages.

Sources  
– Verizon BGP leak causing 24 Jun 2019 Critical outage (controld.com blog, “Cloudflare Goes Down in Internet Traffic Jam With Verizon”).  
– Atlanta routing error, 17 Jul 2020 Critical outage; and CenturyLink failure, 30 Aug 2020 Critical outage (controld.com blog, same page).  
– 21 Jun 2022 network configuration error marked “critical P0” (Site24x7 post-mortem; corroborated by controld.com blog).</Agent_report>


The information has been sourced from the internet and language models (for agent reports). Exercise healthy skepticism toward unverified claims.

Your analysis should have the following components, referring to the above historical context:
(a) Source analysis: Briefly summarize each information source (either web article or Agent report), evaluate source quality and date.
**Opinions are commonplace in writing. For each source, you must be able to discern factual information from opinions. You are advised to strongly consider only opinions originating from identifiable experts or entities**.
(b) Reference class analysis: Identify a few possible reference classes and evaluate respective suitabilities to the forecasting question. If applicable, choose the most suitable one.
(c) Timeframe analysis: State the prediction timeframe (e.g., how many days/months from now?) and examine historical patterns over similar periods
(d) Justification: Integrate the above factors with other points you found relevant to write a justification for your outside view prediction.

Subsequently, calibrate your outside view prediction, considering:
(a) You aim to predict the true probability of an event occurring, not a hedged or overconfident projection of your beliefs.
(b) Is there a rough figure in the sources you can tether your prediction to?
(c) Small differences in probabilities can be significant: 90% is a 9:1 odds and 99% is a 99:1 odds.
(d) Historically, what is the rate of upsets/unexpected outcomes in the domain of this forecasting question? How should this affect your probability?

Format your answer as below:

Analysis:
{Insert your analysis here, following the above components.}

Outside view calibration:
{Insert your calibration of your outside view prediction here.}

Outside View Prediction:
Provide your outside view prediction as a percentage. Be precise — don't round to multiples of 5%.
