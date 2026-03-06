
<Summary source="https://www.cisa.gov/news-events/alerts/2026/02/24/cisa-adds-one-known-exploited-vulnerability-catalog">
The following summary extracts the key information from the CISA announcement dated February 24, 2026, regarding updates to the Known Exploited Vulnerabilities (KEV) Catalog.

### 1. Facts, Statistics, and Objective Measurements
*   **New Entries:** Exactly **one (1) new vulnerability** was added to the KEV Catalog on February 24, 2026.
*   **Vulnerability Identifier:** CVE-2026-25108.
*   **Vulnerability Description:** Soliton Systems K. K. File Zen OS Command Injection Vulnerability.
*   **Regulatory Context:** The addition is mandated under **Binding Operational Directive (BOD) 22-01**, which requires Federal Civilian Executive Branch (FCEB) agencies to remediate these vulnerabilities by a specific due date.
*   **Criteria for Inclusion:** CISA adds vulnerabilities to this catalog only when there is clear evidence of **active exploitation**.

### 2. Opinions from Reliable and Named Sources
*   **CISA (Official Agency Statement):** The agency characterizes this specific type of vulnerability (OS Command Injection) as a **"frequent attack vector"** for malicious cyber actors.
*   **CISA (Risk Assessment):** The agency states that this vulnerability poses **"significant risks to the federal enterprise."**
*   **CISA (Guidance):** While BOD 22-01 is legally binding only for FCEB agencies, CISA "strongly urges" all private and public organizations to prioritize the remediation of these cataloged vulnerabilities to reduce cyber exposure.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   *None identified in the provided text.*
</Summary>

<Summary source="https://thehackernews.com/2026/02/cisa-flags-four-security-flaws-under.html">
This summary focuses on the key data points and expert assessments from the provided article regarding CISA’s KEV catalog updates, relevant to the forecasting period of February to April 2026.

### 1. Facts, Statistics, and Objective Measurements
*   **KEV Additions:** CISA added **four** specific vulnerabilities to the KEV catalog in this update:
    *   **CVE-2026-2441 (CVSS 8.8):** A use-after-free flaw in Google Chrome.
    *   **CVE-2024-7694 (CVSS 7.2):** An arbitrary file upload flaw in TeamT5 Threat Sonar Anti-Ransomware (v3.4.5 and earlier).
    *   **CVE-2020-7796 (CVSS 9.8):** An SSRF vulnerability in Synacor Zimbra Collaboration Suite.
    *   **CVE-2008-0015 (CVSS 8.8):** A stack-based buffer overflow in Microsoft Windows Video ActiveX Control.
*   **Remediation Deadline:** Federal Civilian Executive Branch (FCEB) agencies were mandated to apply fixes for these specific flaws by **March 10, 2026**.
*   **Exploitation Scale (CVE-2020-7796):** A March 2025 report identified a cluster of approximately **400 IP addresses** actively exploiting this SSRF vulnerability across multiple countries (U.S., Germany, Singapore, India, Lithuania, and Japan).
*   **Vulnerability Age:** The catalog update includes a mix of contemporary (2026), recent (2024), and legacy (2020, 2008) vulnerabilities, indicating CISA continues to add older flaws if active exploitation is newly confirmed.

### 2. Opinions and Data from Reliable/Named Sources
*   **Google:** Confirmed that an exploit for **CVE-2026-2441** exists "in the wild." The company is intentionally withholding technical details on weaponization until a majority of users have updated their software.
*   **Microsoft:** Stated via its threat encyclopedia that **CVE-2008-0015** is being used to download malware, specifically the **Dogkild worm**. This worm is capable of overwriting system files, terminating security processes, and modifying Windows Hosts files to block security websites.
*   **GreyNoise (Threat Intelligence Firm):** Provided the data regarding the 400-IP cluster targeting the Zimbra SSRF vulnerability.
*   **TeamT5 (Security Company):** In a follow-up on **February 22, 2026**, the company clarified that the vulnerability in their Anti-Ransomware product was an issue from 2024 and claimed all impacted customers had already migrated to secure versions.

### 3. Potentially Useful Information from Less Reliable/Unspecified Sources
*   **The Hacker News (Author):** Notes that it is "presently unclear" how the TeamT5 vulnerability is being exploited in the wild, despite its addition to the KEV.
*   **General Observation:** The article highlights that information regarding the specific weaponization of new flaws (like the Chrome CVE) is often suppressed by vendors to prevent "other threat actors from joining the exploitation bandwagon."
</Summary>

<Summary source="https://www.vulnerability-lookup.org/2026/03/02/vulnerability-report-february-2026/">
This summary is based on the provided "Vulnerability Report - February 2026" from Vulnerability-Lookup.

### 1. Facts, Statistics, and Objective Measurements
*   **CISA KEV Catalog Activity:** The CISA Known Exploited Vulnerabilities (KEV) catalog added **28 new entries** during the month of February 2026.
*   **Specific CISA KEV Additions:** Notable vulnerabilities added to the CISA catalog in February 2026 include:
    *   **CVE-2026-1731:** BeyondTrust Remote Support (RS) & Privileged Remote Access (PRA).
    *   **CVE-2026-2441:** Google Chrome.
    *   **CVE-2026-20127:** Cisco Catalyst SD-WAN Manager.
    *   **CVE-2026-22769:** Dell RecoverPoint for Virtual Machines.
    *   **CVE-2025-49113:** Roundcube Webmail.
    *   **CVE-2020-7796:** Synacor Zimbra Collaboration Suite.
*   **Other Catalog Activity:** 
    *   The **CIRCL KEV** catalog added 3 entries (CVE-2026-25108, CVE-2026-1340, and CVE-2026-1281).
    *   The **ENISA KEV** catalog added 0 entries.
*   **Vulnerability Sightings (Frequency):**
    *   **CVE-2026-1731** was the most frequently mentioned vulnerability with 158 sightings.
    *   **CVE-2026-2441** followed with 143 sightings.
*   **Ghost CVEs:** Eight vulnerability identifiers were observed in the wild despite being listed as "RESERVED" or "NOT_FOUND" in official registries. The most frequent was **CVE-2023-42344** (5 occurrences).

### 2. Opinions from Reliable and Named Sources
*   **Vulnerability-Lookup/CIRCL:** The report characterizes February 2026 as an "active month" for known exploited vulnerabilities.
*   **FETTA (Federated European Team for Threat Analysis):** Notes that developing actionable Cyber Threat Intelligence (CTI) is a complex task requiring the interpretation of large amounts of data, often leading to fragmented efforts across different SOCs and CSIRTs.
*   **Contributor Insights:** Reports link **UAC-0001 (APT 28)** to active cyberattacks against Ukraine and EU countries leveraging **CVE-2026-21509** (Microsoft 365 Apps for Enterprise).

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   **Community Sightings:** The report relies on aggregated data from various community-driven and automated sources (e.g., Bluesky, Mastodon, GitHub Gists, and various exploit databases). While these provide the "sighting" counts, they represent raw activity rather than official government verification.
*   **Ghost CVE Observations:** The identification of "Ghost CVEs" (like CVE-2026-1584 or CVE-2026-23456) relies on sightings of vulnerabilities that do not yet have public records in the NVD or MITRE, making their exact nature or severity less certain until officially published.
</Summary>

<Summary source="https://www.infosecurity-magazine.com/news/trump-cut-nearly-1000-jobs-cisa/">
This summary focuses on the proposed budget and personnel changes at the Cybersecurity and Infrastructure Security Agency (CISA) for fiscal year 2026, as detailed in the *Infosecurity Magazine* article dated June 3, 2025.

### 1. Facts, Statistics, and Objective Measurements
*   **Proposed Personnel Cuts:** The Trump administration’s fiscal year 2026 proposal seeks to reduce CISA’s staff from **3,292 to 2,324 positions**, a loss of nearly 1,000 employees.
*   **Budget Reduction:** The proposal includes a **$495 million budget cut**, bringing total funding down to **$1.96 billion**.
*   **Division-Specific Funding Cuts:**
    *   **Cybersecurity Division:** 18% reduction.
    *   **Integrated Operations Division:** 20% reduction.
    *   **Stakeholder Engagement Division:** 62% reduction.
    *   **National Risk Management Center:** 73% reduction.
*   **Election Security:** The proposal includes the elimination of election security funding.

### 2. Opinions from Reliable and Named Sources
*   **The White House / Administration:** Stated the cuts are intended to refocus CISA on defending federal networks and critical infrastructure while eliminating "weaponized rot." The administration accused the agency of working with tech companies to "target free speech."
*   **Gabrielle Hempel (Threat Intelligence Researcher, Exabeam):**
    *   Describes the cut as a "strategic deprecation of US cyber defense capability" occurring while threat actors are accelerating.
    *   Argues that gutting the Stakeholder Engagement Division and National Risk Management Center "hollows out" the mission rather than refocusing it, as these teams drive the cross-sector collaboration necessary for private-sector resilience.
    *   States that pulling funding for election security gives "tacit permission to interfere."
*   **Kevin Kirkwood (CISO, Exabeam):**
    *   Notes that the private sector has come to rely on CISA’s role in protecting critical infrastructure.
    *   Criticizes the budgeting approach, suggesting the administration is cutting programs they do not fully understand.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   The article mentions that the administration "vowed to return [CISA] to what the administration considers its core mission," though the specific "core mission" definition remains a point of contention among experts cited in the text.
</Summary>

<Summary source="https://cyberscoop.com/cisa-workforce-cuts-house-leaders-legislation/">
This summary focuses on the provided *CyberScoop* article dated April 2, 2025, regarding the legislative and operational status of the Cybersecurity and Infrastructure Security Agency (CISA).

### 1. Facts, Statistics, and Objective Measurements
*   **Personnel Reductions:** The Trump administration has implemented personnel cuts at CISA, specifically targeting probationary employees. Rep. Eric Swalwell noted that thousands of government employees are currently on "paid leave" due to administrative confusion regarding their employment status.
*   **Grant Programs:** A $1 billion, four-year state and local grant program administered by CISA is currently expiring.
*   **Legislative History:** In 2023, House Republicans voted on an amendment to cut CISA’s budget by 25%, though the cut was not enacted.
*   **Regulatory Mandates:** CISA is currently drafting regulations in response to a 2022 cyber incident reporting law.
*   **Information Sharing:** The 2015 Cybersecurity Information Sharing Act is currently up for reauthorization.

### 2. Opinions from Reliable and Named Sources
*   **Rep. Andrew Garbarino (R-NY), Chair of the House Homeland Security Subcommittee on Cybersecurity:**
    *   **Agency Scope:** Believes CISA should take on a broader role across the federal government (e.g., taking over cyber responsibilities from agencies like the EPA) rather than being reduced.
    *   **Personnel Cuts:** Stated that while efficiency is good, recent cuts have "cut the bone" rather than just "the fat," and he intends to "fix that."
    *   **Leadership:** Expressed optimism regarding Sean Plankey’s nomination to lead CISA, viewing it as a sign the administration takes the agency seriously.
    *   **Legislative Goals:** Plans to push for a 10-year reauthorization of the state and local grant program and further oversight of CISA’s incident reporting regulations, which he views as "overly burdensome."
*   **Rep. Eric Swalwell (D-CA), Ranking Member of the Subcommittee:**
    *   **Efficiency:** Characterized the personnel cuts as "schizophrenic" and counterproductive to the goals of the Department of Government Efficiency (DOGE), arguing that paying employees to stay home on leave is inefficient.
    *   **Legislative Goals:** Aims to pass legislation in 2025 to codify the Joint Cyber Defense Collaborative (JCDC) into law and establish a formal charter for it.
*   **Sen. Rand Paul (R-KY), Chair of the Senate Homeland Security and Governmental Affairs Committee:**
    *   **Agency Future:** Has pledged to fight the agency or potentially eliminate it entirely.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   **Industry Sentiment:** The article notes that "industry" has joined Rep. Garbarino in criticizing CISA’s proposed cyber incident reporting regulations as being "overly burdensome." (Specific companies or industry groups are not named).
*   **General House Republican Sentiment:** The article mentions that many Republicans previously targeted CISA due to its work on "disinformation and misinformation," though Garbarino believes education efforts have mitigated this hostility.
</Summary>

<Summary source="https://www.infosecurity-magazine.com/news/trump-cisa-layoffs-funding-cuts/">
This summary focuses on the organizational and budgetary changes at the Cybersecurity and Infrastructure Security Agency (CISA) as of March 2025, which may impact the agency's capacity to maintain the KEV catalog.

### 1. Facts, Statistics, and Objective Measurements
*   **Staffing Reductions:** Approximately 300 contract personnel have had their positions terminated. This includes over 100 people from one "red team" and support roles, followed by the termination of a second red team.
*   **Probationary Firing:** In mid-February 2025, the Department of Government Efficiency (DOGE) requested the firing of 130 probationary CISA workers.
*   **Funding Cuts:** CISA terminated a $10 million cooperative agreement with the Center for Internet Security (CIS).
*   **Program Terminations:** Funding has been cut for two major cyber-threat information-sharing hubs: the Multi-State Information Sharing & Analysis Center (MS-ISAC) and the Election Infrastructure Information Sharing & Analysis Center (EI-ISAC).
*   **Leadership Change:** Sean Plankey (former Navy CIO and US Cyber Command official) has been nominated by President Trump to serve as the new Director of CISA.

### 2. Opinions from Reliable and Named Sources
*   **Christopher Chenoweth (Senior Pentester, CISA):** Stated via LinkedIn that DOGE cut "mission-critical" red teams and support roles, leading to a loss of experienced operators.
*   **CISA Spokesperson:** 
    *   Characterized the staff reductions as "contracting issues" rather than employee layoffs.
    *   Claimed the red team remains "fully operational" despite the cuts.
    *   Stated that the termination of the $10 million CIS agreement was intended to "save taxpayers," "eliminate redundancies," and focus on "mission-critical areas" that align with the new administration's priorities.
*   **Jen Easterly (Former CISA Director):** Endorsed nominee Sean Plankey, stating he brings "great cyber expertise" and "steady leadership" to the agency.

### 3. Potentially Useful Opinions from Less Reliable/Not-Named Sources
*   **Eric Geller (Independent Journalist):** Reported on the termination of the $10 million CIS agreement on March 11, 2025 (later confirmed by CISA).
*   **CBS Reporting:** Cited as the source for the claim that DOGE requested the firing of 130 probationary workers.
*   **DOGE Status:** The article notes that while it is called the "Department of Government Efficiency," it is actually a temporary, contracted entity operating under the US DOGE Service (USDS), not a formal executive branch department.
</Summary>

<Agent_report>
Query: How many vulnerabilities were added to the CISA Known Exploited Vulnerabilities (KEV) catalog in January 2026 and the first half of February 2026? Please check the CISA KEV JSON feed or any security industry reports that track monthly KEV addition counts for early 2026.
Objective
Determine how many entries CISA inserted into the Known Exploited Vulnerabilities (KEV) catalog  
1) during January 2026 and  
2) during the first half of February 2026 ( 1 – 15 February inclusive).

January 2026
• Loginsoft’s “Threat and Vulnerabilities Report – January 2026” states explicitly: “Over the month, 17 vulnerabilities were added to the CISA Known Exploited Vulnerabilities (KEV) catalog” (Loginsoft, January 2026 report).  
• Additional spot evidence aligns with that figure:
   – Qualys notes CISA’s addition of CVE-2018-14634 on 26 January 2026 (Qualys blog, 2 Feb 2026).  
   – Rapid7 chronicles the 29 January 2026 addition of CVE-2026-1281 (Rapid7 blog, 30 Jan 2026).  
   The Loginsoft total (17) necessarily already counts these individual cases and all other January additions.

Because Loginsoft summarises the full month and no contradictory totals appear in any of the other January sources, the best-supported count for January 2026 KEV insertions is:
 January 2026 → 17 vulnerabilities added.

1 – 15 February 2026
Open-source reporting during the first half of February is much sparser, but the evidence we do have is consistent and points to a single KEV update:
• Rapid7 reports that CVE-2026-1731 (BeyondTrust Remote Support / Privileged Remote Access pre-auth RCE) “was added to the U.S. Cybersecurity and Infrastructure Security Agency’s (CISA) list of known exploited vulnerabilities (KEV) … on 13 February 2026.” (Rapid7 blog, 9 Feb 2026; update 16 Feb 2026).  
• No other blog posts, vendor advisories, or press items in the supplied search set mention any other CISA KEV additions between 1 and 15 February 2026.  
• The CISA catalog page excerpt included in the results shows the next chronological entry after 13 February as a Cisco SD-WAN vulnerability added on 25 February – after the window we are examining.

On that basis the supported count for the first half of February 2026 is:
 1 – 15 February 2026 → 1 vulnerability added (CVE-2026-1731).

Combined result
• January 2026: 17 new KEV entries  
• 1 – 15 February 2026: 1 new KEV entry  
Therefore a total of 18 vulnerabilities were added to CISA’s KEV catalog across the period 1 January – 15 February 2026.

Information Gaps / Confidence
The Loginsoft monthly report is the only source that gives a precise January total of 17. While corroborated by individual item reporting and no contradicting evidence, the definitive way to validate the figure would be by enumerating the “dateAdded” fields for 2026-01-01 → 2026-01-31 in the official kev-data JSON feed on GitHub. The same direct-feed check would confirm whether any early-February additions other than CVE-2026-1731 exist. Because the GitHub dataset itself was not enumerated in the supplied material, a small residual uncertainty (±1-2) remains. Still, given the convergence of all publicly available narrative sources, the most defensible counts with current evidence are 17 for January and 1 for 1-15 February 2026.</Agent_report>
<Summary query="CISA KEV monthly additions rate 2026 slowdown">No URLs returned from Google.</Summary>
