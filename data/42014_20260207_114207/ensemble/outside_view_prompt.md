
You are currently analyzing a forecasting question to generate an outside view prediction.

The forecasting question is:
Will the community prediction be higher than 82.00% on 2026-02-14 for the Metaculus question "Will the Community beat Nathan Young in the Metaculus Cup Spring 2026?"?

Question background:
Metaculus is a crowdsourced forecast aggregation platform where humans and bots compete to predict future events. Each question on Metaculus has a community prediction that aggregates all user's forecasts. As of this question launch, this aggregation is calculated as a median of user forecasts weighted by recency. 

--------------------------------

Below are some details about the original Metaculus question: 
- Question URL: https://www.metaculus.com/questions/41508
- Original question title: Will the Community beat Nathan Young in the Metaculus Cup Spring 2026?
- The current community prediction as of 2026-02-01: 82.00%

Original resolution criteria: 
> This question will resolve as **Yes** if, at the conclusion of the Metaculus Cup Spring 2026, the Community Prediction has a greater Total Score than Nathan Young in the tournament leaderboard.

Original fine print: 
> This question will resolve only after all other Metaculus Cup Spring 2026 questions have resolved and will not be included in the scoring used to determine whether the Community Prediction outperformed Nathan Young.

Original background: 
> The Metaculus Cup Spring 2026 launched with a base prize pool of \$5,000. According to the [tournament announcement](https://www.metaculus.com/notebooks/41477/spring-2026-cup-announcement/), an additional \$2,500 will be added to the prize pool if the Community Prediction outperforms Nathan Young, a designated benchmark forecaster, over the course of the tournament.
> 
> Specifically, the announcement states that:
> 
> > “New this season: the Community Prediction will go head-to-head against Nathan Young… Beat Nathan and an additional \$2,500 gets added to the forecasting prize pool.”
> 
> The same announcement also describes Nathan as follows:
> 
> > Nathan is the Director of [Goodheart Labs](https://goodheartlabs.com/), where he builds epistemic tools including the world's first AI-written community note on X. He works as a geopolitical forecaster with the Swift Centre, covering topics from elections to healthcare innovation. He previously served as Head of Forecasting at Zeitgeist, a crypto prediction market integrating futarchy governance, and has moderated for both Metaculus and Manifold Markets.

`{"format":"metaculus_binary_cp_rises","info":{"post_id":41508,"question_id":41255,"last_cp":0.82}}`

This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
This question will resolve based on the community prediction of the Metaculus question found [here](https://www.metaculus.com/questions/41508) (i.e. the 'target question'). If the community prediction of the target question on 2026-02-14 16:20:16 is higher than 82.00%, this question will resolve to 'Yes'. If it is lower or equal to 82.00%, this question will resolve to 'No'. If the target question has already resolved before this question opens, then this question will be annulled. If the target question resolves after this question opens, but before 2026-02-14 16:20:16, then this question will resolve to the same value as the target question.

Additional fine-print:


Question metadata:
- Opened for forecasting: 2026-02-07T10:46:52Z
- Resolves: 2026-02-14T16:20:16Z

IMPORTANT: Today's date is 2026-02-07. All dates before today's date are in the PAST. All dates after today's date are in the FUTURE. Use today's date to correctly evaluate whether sources describe past events or future predictions. Any information source which refers to events before today's date of 2026-02-07 should not be considered as speculative but rather an historical document.

Historical context:
<Summary query="Metaculus Cup community vs Nathan Young">No usable content extracted from any URL.</Summary>
<Summary query="Nathan Young Metaculus Cup interview">No URLs returned from Google.</Summary>

<Agent_report>
Query: Provide historical time-series of community prediction for Metaculus question 41508 and past Cup seasons; include any Metaculus notebooks comparing community performance to Nathan Young.
The newest round of crawling still fails to surface the three concrete deliverables that the original request asked for, but it does add a few important clues about where the data probably lives and how it can be accessed.

1. Community-prediction time-series for Metaculus question 41508  
   • None of the results exposes a CSV/JSON, screenshot, blog post or other public file that already contains the historical forecast curve for Q 41508.  
   • However, multiple Metaculus-maintained GitHub repositories now appear in the results and they all reference the same authenticated REST endpoint, /api2/questions/{id}/timeline/.  
     – The “metac-bot-template” repo shows the call sequence a bot uses to fetch a question object and then “timeline” data before writing a forecast (GitHub – Metaculus/metac-bot-template).  
     – The “forecasting-tools” package (GitHub – Metaculus/forecasting-tools) wraps the same endpoint and even contains an example notebook (README.ipynb) that calls get_question_timeline and converts the JSON to Pandas.  
   • These listings confirm that the timeline is accessible—just not publicly indexed—once a valid Metaculus token is supplied. What is still missing is the actual dump for question 41508; the user (or someone with an account) will have to execute the API call or use the notebook.

2. Archived leaderboards for past Metaculus Cup seasons  
   • None of the new hits contains historical Cup standings or season-aggregate files.  
   • There are no URLs showing “/api2/cups”, “/api2/tournaments”, “cup_results”, “leaderboard.csv”, etc.  
   • The open-source Metaculus web code base (GitHub – Metaculus/metaculus) does provide Django models named “Tournament”, “Cup”, and “Season”, suggesting that the production site serves that information by JSON just like questions and timelines, but the exact endpoint names are not documented in the public code or the docs returned.  
   • Bottom line: The data almost certainly exists in the Metaculus database, but no public snapshot or API example is discoverable in open search results; an authenticated scrape (or a request to Metaculus staff) is still required to retrieve past Cup results.

3. Public notebooks comparing Nathan Young’s forecasts to the community  
   • No new evidence appeared. None of the GitHub repositories, including the official Metaculus repos, contain an .ipynb file authored by or mentioning Nathan Young.  
   • Searches still do not reveal LessWrong, EA Forum, or personal-site posts that link to such notebooks.  
   • Therefore either (a) the notebooks do not exist, (b) they are private, or (c) they live under a non-obvious repository/filename that generic keyword search has not detected.

What the new results do provide  
• Open-source code that proves the timeline endpoint exists and shows exactly how to call it, lowering the effort needed to self-extract the Q 41508 history (Metaculus/forecasting-tools; Metaculus/metac-bot-template).  
• Confirmation from the site code (Metaculus/metaculus) that “Cup” and “Season” are first-class objects in the backend; that indicates that a parallel, undocumented API probably exists for Cup leaderboards even though no examples are indexed.  

Remaining information gaps  
• A file (CSV, JSON, or image) that actually contains the historical community forecast for question 41508.  
• Any machine-readable archive of one or more completed Cup seasons—scores, rank tables, or even a screenshot.  
• Any publicly accessible analysis notebook that benchmarks Nathan Young versus the Metaculus community.

Recommended next actions  
Because open web search appears exhausted, only targeted, authenticated steps are likely to close the gaps:

A. Log in to Metaculus (or create a free account), obtain the session token (METACULUS_TOKEN), and run:  
   https://www.metaculus.com/api2/questions/41508/timeline/  
   Save the returned JSON, flatten to CSV if needed, and plot the time-series.

B. While still logged in, visit the current Cup leaderboard page in a browser, open the Network tab, and look for calls whose paths start with /api2/. Copy those URLs and replay them with different season query strings (e.g., season=2024-spring) until the historical payload appears.

C. Use the code examples in the “forecasting-tools” or “metac-bot-template” repos to automate steps A and B; both repos already handle authentication tokens and JSON parsing.

D. Run focused GitHub searches for “api2/questions” + “ipynb” OR “cup leaderboard” + “ipynb” restricted to filetype:ipynb. Add author filters “user:nathanpsyoung” or “in:file Nathan Young” to locate any unpublished notebooks.

E. If these programmatic avenues still fail, the only remaining route is to email Metaculus support (support@metaculus.com) or Nathan Young directly and request the private exports.

Until at least one of these targeted, credential-based steps is carried out, the deliverables requested in the original query cannot be satisfied from publicly indexed material alone.</Agent_report>


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
