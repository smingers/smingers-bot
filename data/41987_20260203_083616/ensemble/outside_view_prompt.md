
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
Will the community prediction be higher than 46.00% on 2026-02-12 for the Metaculus question "Will an AI-created song chart in the top 20 of the Billboard Hot 100 before 2027?"?

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question will resolve based on the community prediction of the Metaculus question found [here](https://www.metaculus.com/questions/40969) (i.e. the 'target question'). If the community prediction of the target question on 2026-02-12 05:12:06 is higher than 46.00%, this question will resolve to 'Yes'. If it is lower or equal to 46.00%, this question will resolve to 'No'. If the target question has already resolved before this question opens, then this question will be annulled. If the target question resolves after this question opens, but before 2026-02-12 05:12:06, then this question will resolve to the same value as the target question.

Additional fine-print:


Question metadata:
- Opened for forecasting: 2026-02-03T08:27:39Z
- Resolves: 2026-02-12T05:12:06Z

IMPORTANT: Today's date is 2026-02-03. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-02-03 should not be considered as speculative but rather an historical document.

Historical context:

<Summary source="https://rethinkpriorities.org/research-area/an-examination-of-metaculus-resolved-ai-predictions/">
## Summary of Article

**Title:** An examination of Metaculus' resolved AI predictions and their implications for AI timelines

**Source:** Rethink Priorities

**Date:** July 20, 2021

### Key Facts and Findings:

**Data Collection:**
- Analysis covered 259 questions on Metaculus with the category "Computer Science – AI and Machine Learning" (169 questions) or on the AI subdomain (90 additional questions with some overlap)
- Community predictions were taken at 25% of the way through each question's lifetime (from opening to closing)
- AI subdomain questions had fewer predictions in the median case: 12 vs 39 predictions

**Date-Based Questions (41 total, 7 resolved):**
- 6 out of 7 resolved date questions resolved early
- 5 out of 6 resolved very early (before their predicted 25th percentile time)
- Of questions predicted to be >75% likely to resolve by the analysis date, only 2 out of 5 did resolve
- Of questions predicted to be 50-75% likely to resolve, 1 out of 2 did
- Of questions predicted to be 25-50% likely to resolve, 1 out of 4 did
- **Interpretation:** Suggests predictors were "somewhat overconfident that things would happen," though sample size is small

**Numeric Range Questions (16 resolved):**
- 8 resolved as faster/less safe than predicted
- 8 resolved as slower/more safe than predicted
- **Interpretation:** Predictors were "too confident in their understanding" and were surprised in both directions

**Binary Questions:**
- Brier Score: 0.2027 (lower is better; 0.25 is baseline for always predicting 50%)
- Overconfidence score: -0.57% (negligible)
- Predictors expected 13.65 to 21.16 propositions to resolve positively (depending on percentile), but only 11 actually did
- Using probability analysis: 11 or fewer positive resolutions had only 2.48% probability based on median predictions
- **Interpretation:** "Community was somewhat biased to think events will happen when predicting on these questions" - suggesting expectations of more AI progress than actually occurred

**Overall Conclusion:**
The article states there was "weak evidence to suggest the community expected more AI progress than actually occurred, but this was not conclusive."

### Relevance to Target Question:
This analysis suggests historical patterns on Metaculus AI questions show a tendency toward overestimating AI progress, though the evidence is weak and not conclusive. This could be relevant context for predicting whether the community prediction will rise above 46% for an AI song charting question.
</Summary>

<Summary source="https://forum.effectivealtruism.org/posts/e9htD7txe8RDdcehm/exploring-metaculus-s-ai-track-record">
# Summary of "Exploring Metaculus's AI Track Record" (EA Forum, May 1, 2023)

## Key Facts and Statistics:

**Dataset analyzed:**
- 64 resolved binary AI questions (10,497 forecasts by 2,052 users)
- 88 resolved continuous AI questions (13,683 predictions by 1,114 users)
- Questions drawn from categories: "Computer Science: AI and Machine Learning"; "Computing: Artificial Intelligence"; "Computing: AI"; and "Series: Forecasting AI Progress"

**Performance metrics (lower scores are better):**
- **Binary questions - Community Prediction Brier score:** 0.207
- **Binary questions - Metaculus Prediction Brier score:** 0.182
- **Continuous questions - Community Prediction CRPS:** 0.096
- **Continuous questions - Metaculus Prediction CRPS:** 0.103

**Baseline comparisons:**
- Predicting 50% on all binary questions yields Brier score of 0.25 (19% worse than Community Prediction)
- Random guessing yields Brier score of 0.33 (57% worse than Community Prediction)
- Uniform distribution on continuous questions yields CRPS of 0.172 (significantly worse than both Community and Metaculus predictions)

## Key Arguments/Analysis:

The article argues that claims of Metaculus AI forecasts being "near chance" are incorrect. The analysis demonstrates that:

1. A Brier score of 0.207 is substantially better than chance, as even a perfectly calibrated forecaster would achieve worse than 0.207 when questions have true probabilities between 30-70%

2. Simulations show that if Community Predictions were perfectly calibrated, they would still get a Brier score worse than 0.207 nearly 25% of the time due to natural variation

3. Both Community and Metaculus predictions "robustly outperform naïve baselines" on both binary and continuous questions

4. Performance on continuous questions was "considerably better" than on binary questions

5. Statistical analysis (p<0.1%) suggests the results cannot be attributed to luck

## Platform Methodology Context:

- Community Prediction: time-weighted median of all forecasts
- Metaculus Prediction: weights forecasts based on past performance and "extremises" to compensate for systematic human cognitive biases
</Summary>

<Summary source="https://www.theguardian.com/technology/2025/nov/13/ai-music-spotify-billboard-charts">
# Summary of "AI slop tops Billboard and Spotify charts as synthetic music spreads"

**Source:** The Guardian  
**Date:** November 13, 2025  
**Author:** Aisha Down

## Key Facts and Statistics:

1. **Chart Performance:** Three AI-generated songs topped music charts in the week of the article:
   - "Walk My Walk" and "Livin' on Borrowed Time" by Breaking Rust topped Spotify's "Viral 50" chart in the US
   - "We Say No, No, No to an Asylum Center" by JW "Broken Veteran" reached the top position on Spotify's global viral chart
   - Breaking Rust also appeared in the top five on the global chart

2. **Music Volume:** The article cites "50,000 tracks a day" of AI-generated music competing with human musicians

3. **Quality Assessment:** A Deezer survey of 9,000 people across eight countries found that 97% could not distinguish between AI-generated music and human-written music

4. **Previous AI Music Success:** Over the summer (2025), AI-generated songs from Velvet Sundown amassed over a million streams on Spotify

## Named Source Opinions:

**Ed Newton-Rex** (musician and founder of a non-profit certifying AI companies' data training practices):
- Attributes AI music's rise to "very rapid trend of AI music gaining in popularity essentially because it's spreading in volume"
- States: "There's no denying it. I think it's fair to say you can't distinguish the best AI music from human-composed music now"
- Describes AI music as "a new, hyperscalable competitor" built "by exploitation"

**Chris Dalla Riva** (author of "Uncharted Territory" on music virality data):
- Notes: "Basically every piece of AI music you see isn't distributed by a regular label. They're made by a person in their bedroom and uploaded to these distribution sites"

## Less Reliable/Anonymous Source Opinions:

**"Broken Veteran"** (AI music creator, declined to give real name):
- Views AI as "just another tool for expression, particularly valuable for people like me who have something to say but lack traditional musical training"
- Claims the technology has "democratized music creation"
- States his songs "express frustration with governmental policies, not with migrants as individuals"

## Additional Context:

- The Dutch song and other Broken Veteran music disappeared from Spotify and YouTube shortly after charting; Spotify stated the rights owners removed it, not the platform
- Distribution services like DistroKid, Amuse, Landr, and CDBaby help creators place AI music on major platforms, with varied policies on AI-generated content
- DistroKid is described by blogs as having "more lenient" policies on AI content
- Breaking Rust's hits appear to be distributed by DistroKid
</Summary>

<Summary source="https://ca.billboard.com/business/streaming/anne-murray-ai-songs">
# Summary of Article: "Spotify Removes Seemingly AI-Generated Songs Uploaded to Anne Murray's Profile"

**Source:** Billboard Canada  
**Date:** January 30, 2026

## Key Facts:

1. **Incident Details:**
   - Four songs were fraudulently uploaded to Canadian music legend Anne Murray's Spotify account on January 26, 2026
   - Song titles: "When You Say My Name," "Time Has Been Kind," "Just the Way You Say," and "If Love Is Single"
   - The vocals featured a high-pitched voice that did not match Murray's, instead resembling country singers Carrie Underwood and Miranda Lambert
   - Artwork appeared to be AI-generated versions of stock photos (microphones and boombox)
   - Spotify removed the tracks after four days

2. **Spotify's Response:**
   - The company stated they are taking increasing measures to protect artists' identities and prevent unofficial uploads
   - Measures include: controls with distributors to block bad submissions before going live, faster review through content mismatch process, and tools allowing artists to report issues prior to release

3. **Related AI Controversies:**
   - **HAVEN.'s "I Run." (last year/2025):** Featured AI-manipulated vocals similar to British singer Jorja Smith's voice. The duo used Smith's name in hashtags to promote the track despite her non-involvement. The song was withheld from Billboard charts due to the dispute, then re-recorded with singer Kaitlin Aragon's vocals and subsequently entered and climbed the Canadian Hot 100.

4. **Public Opinion:**
   - A Leger study found that 85% of Canadians favor government enforcement of fair, ethical use of AI, indicating broad public concerns

**Note:** The article also contains an unrelated announcement about Post Malone and Jelly Roll's tour dates, which is not relevant to AI-generated music.
</Summary>

<Summary source="https://www.billboard.com/pro/ai-music-artist-xania-monet-multimillion-dollar-record-deal/">
# Summary of Billboard Article on AI Artist Xania Monet

**Date:** September 16, 2025  
**Author:** Hannah Karp  
**Source:** Billboard

## Key Facts and Statistics:

1. **Xania Monet's Identity and Creation:**
   - Xania Monet is an AI-created artist project by Telisha Jones (goes by "Nikki"), a 31-year-old design studio owner from Olive Branch, Mississippi
   - Jones used Suno (an AI music generation platform) to create the music from her own lyrics
   - Jones claims full ownership of songwriting and production credits
   - 90% of lyrics are Jones's own true stories, 10% inspired by friends and community

2. **Record Deal:**
   - Multiple labels bid on signing Xania Monet
   - Bidding reached $3 million
   - Hallwood Media (led by former Interscope executive Neil Jacobson) signed her with a "multimillion-dollar agreement"
   - Major labels backed by the majors abstained from making offers due to Suno being sued for copyright infringement by major record companies in 2024
   - One major label did make a top offer despite the Suno connection

3. **Chart Performance (as of week dated Sept. 20, 2025):**
   - No. 25 on Billboard Emerging Artists chart (debut)
   - No. 21 on Hot Gospel Songs with "Let Go, Let God" (debut)
   - "How Was I Supposed to Know" hit No. 1 on R&B Digital Song Sales
   - No. 3 on R&B/Hip-Hop Digital Song Sales
   - No. 22 on Digital Song Sales
   - **9.8 million total on-demand official U.S. streams across catalog**
   - **5.4 million streams in most recent tracking week (Sept. 5-11)**

4. **Other Context:**
   - Hallwood Media previously signed imoliver (top-streaming "music designer" on Suno) in July 2025, marking the first signing of a Suno creator to a record label
   - Jones plans to work with additional human producers on upcoming projects
   - Manager Romel Murphy is planning Xania's first live performance and fielding publishing deal offers

## Source Reliability:
All information comes from named sources (Hannah Karp/Billboard, manager Romel Murphy) and official chart data from Luminate, making this a highly reliable account.
</Summary>

<Agent_report>
Query: Summarize historical prediction data for Metaculus question 40969, highlight notable jumps and their causes; list any AI-created songs that have reached Billboard charts or are projected to debut soon; include recent Billboard policy statements on AI music.
This update revisits each element of the original brief in light of the newest hits returned by Google and Google News.  Where nothing new surfaced, the earlier findings are confirmed.

1.  Metaculus question 40969 – can the historical prediction record be reconstructed?  
•  A second sweep that included explicit “archive screenshot”, “Wayback”, “webcache” and similar terms still yields no copy of https://metaculus.com/questions/40969 — neither live nor in any archival service.  
•  No derivative databases (EA Forum dumps, Rethink Priorities spreadsheets) or social-media screen-shots mention an internal ID 40969.  
•  The two PDF-heavy hits returned in this round (ir.mmc.co.jp and hal.science) are unrelated documents whose binary strings merely matched the numeric pattern.  
Conclusion: the underlying prediction graph and discussion thread remain inaccessible to the open web.  Therefore no timeline, no “notable jumps”, and no attribution of those jumps to particular comments can be produced without privileged access to Metaculus’ backend or to the question writer.  This gap is unchanged.

2.  AI-created (or strongly AI-assisted) songs that have already appeared on Billboard-compiled charts  
The three independent news reports in the fresh corpus all point to the same set of chart entries:

•  Breaking Rust – “Walk My Walk”  
  – No. 1 Country Digital Song Sales, chart dated 4 Nov 2025 [Mashable, 14 Nov 2025].  
•  Breaking Rust – “Livin’ on Borrowed Time”  
  – Top-10 Country Digital Song Sales; over 4 million Spotify streams [Theregister, 10 Nov 2025].  
•  Cain Walker – three separate titles sitting at Nos. 3, 9 and 11 on the same chart week [The Week, 21 Nov 2025 citing Billboard].  

All three outlets state that the acts are fully AI-generated (artist images, vocals and songwriting).  The Register adds that Breaking Rust had already logged 2 million monthly Spotify listeners when it first cracked Billboard.

Previously documented AI chart appearances (Xania Monet, Juno Skye, Ennly Blue, etc.) are not contradicted by the new material; they simply are not mentioned in the current news cycle.

3.  Forward‐looking: AI songs projected to debut soon  
The new articles still stop at retrospective coverage.  No Luminate pre-release sales forecasts, label press statements or Billboard “chart preview” columns identify an upcoming AI single with an expected debut week.  This portion of the brief therefore remains unfulfilled.

4.  Recent Billboard policy statements or industry actions on AI music  
None of the latest hits is itself a Billboard article, but all three reference Billboard’s earlier reporting.  Cross-checking with the catalogue compiled in the prior research step shows no additions since January 2026.  The most consequential Billboard-reported actions remain:

•  Bandcamp blanket ban on wholly-AI tracks (Billboard, 14 Jan 2026).  
•  Spotify rule update: mandatory AI-disclosure tags; removal of 75 million “spammy” tracks (Billboard podcast, 23 Oct 2025).  
•  Deezer: visible “AI-generated” badge and exclusion of pure-AI tracks from recommendations (Billboard, 11 Dec 2025).  
•  iHeart Radio “Guaranteed Human” pledge (Billboard, Nov 2025 wrap-up).  
•  SOCAN, ASCAP, BMI registration rules; Universal Music Group’s position on training data; NO FAKES Act re-introduction; Suno/Udio settlement framework and lawsuit update (various Billboard pieces Oct 2025 – Jan 2026).

No fresher Billboard policy article surfaced in the current crawl, so the list above stands as the most recent public guidance tracked by the magazine.

5.  Remaining information gaps  
•  Metaculus 40969 history and comment-triggered jumps — still unattainable without direct assistance from Metaculus.  
•  Specific, data-supported projections for imminent AI singles — still absent from Billboard and industry trades.  
•  Billboard coverage of Apple Music, Amazon Music, YouTube or TikTok AI-policies remains to be verified.

Until one of these items becomes publicly available, the analysis above is the fullest reconstruction possible from open-web sources.</Agent_report>


The information has been sourced from the internet/language models (for agent reports), so it is advisable to exercise healthy skepticism at your discretion.

Your analysis should have the following components, refering the above historical context:
(a) Source analysis: Briefly summarize each information source (either web article or Agent report), evaluate source quality and data.
**Opinions are commonplace in writing. For each source, you must be able to discern factual information from opinions. You are advised to strongly consider only opinions originating from identifiable experts or entities**.
(b) Reference class analysis: Identify a few possible reference classes and evaluate respective suitabilities to the forecasting question. If applicable, choose the most suitable one.
(c) Timeframe analysis: State the prediction timeframe (e.g., how many days/months from now?) and examine historical patterns over similar periods
(d) Justification: Integrate the above factors with other points you found relevant to write a justification for your outside view prediction.

You are free to include other components to deepen the analysis, at your discretion.

Subsequently, calibrate your outside view prediction, considering:
(a) You aim to predict the true probability of an event occuring, not a hedged or overconfident projection of your beliefs.
(b) Is there a rough figure in the sources you can tether your prediction to?
(c) Small differences in probabilities can be significant: 90% is a 9:1 odds and 99% is a 99:1 odds.

Format you answer as below:

Analysis:
{Insert your analysis here}

Outside view calibration:
{Insert your calibration of your outside view prediction here.}

Outside View Prediction:
[Provide your outside view prediction here to a 1% significance. It is not necessary for the prediction to be a neat multiple of 5%.]
