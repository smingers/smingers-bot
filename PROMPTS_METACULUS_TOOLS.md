# Metaculus Forecasting Tools - Prompts Documentation

This document catalogs all prompts used in the official Metaculus forecasting-tools framework, extracted from the repository at `~/Development/metaculus-forecasting-tools`.

## Pipeline Overview

The Metaculus forecasting-tools framework follows this structure:
1. **Research Stage** - Gather information (SmartSearcher, AskNews, or custom)
2. **Forecasting Stage** - Single-stage prediction (no separate outside/inside view)
3. **Parsing/Structuring** - Extract structured predictions from LLM responses

The framework emphasizes simplicity and flexibility - you override `run_research()` and `_run_forecast_on_*()` methods.

---

## 1. Research Stage

### 1.1 Template Bot Research Prompt

**Purpose:** Generate research summary for forecasting questions.

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_get_research_prompt()`

**Model:** Varies by `researcher` config (default: `asknews/news-summaries`, `smart-searcher/*`, or custom `GeneralLlm`)

**Temperature:** 0 (for SmartSearcher), varies for other researchers

**Prompt:**
```
You are an assistant to a superforecaster.
The superforecaster will give you a question they intend to forecast on.
To be a great assistant, you generate a concise but detailed rundown of the most relevant news, including if the question would resolve Yes or No based on current information.
You do not produce forecasts yourself.

Question:
{question.question_text}

This question's outcome will be determined by the specific criteria below:
{question.resolution_criteria}

{question.fine_print}
```

**Variables:**
- `{question.question_text}` - Full question text (includes background, resolution criteria, etc. in structured format)
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print/additional details

**Note:** If `researcher == "asknews/news-summaries"`, only `question.question_text` is passed (no prompt template).

---

### 1.2 Q2 Template Bot Research Prompt

**Purpose:** Simpler research prompt used in Q2 2025 template.

**Location:** `forecasting_tools/forecast_bots/official_bots/q2_template_bot.py::run_research()`

**Model:** Varies by `researcher` config

**Prompt:**
```
You are an assistant to a superforecaster.
The superforecaster will give you a question they intend to forecast on.
To be a great assistant, you generate a concise but detailed rundown of the most relevant news, including if the question would resolve Yes or No based on current information.
You do not produce forecasts yourself.

Question:
{question}
```

**Variables:**
- `{question}` - Full question object (passed as string representation, includes all question details in JSON format)

**Note:** The comment in the code notes: "The full question (not just question title) ended up being passed into the prompt in Q2 after a refactor at the beginning of the quarter. This includes the full question information (including background info, all in json format), which previous quarters did not include."

---

### 1.3 SmartSearcher - Query Generation

**Purpose:** Generate search queries from a research prompt.

**Location:** `forecasting_tools/agents_and_tools/research/smart_searcher.py::__create_basic_search_queries()`

**Model:** From SmartSearcher config (default: `gpt-4.1`)

**Temperature:** From SmartSearcher config (default: 0)

**Prompt:**
```
You have been given the following instructions. Instructions are included between <><><><><><><><><><><><> tags.

<><><><><><><><><><><><>
{prompt}
<><><><><><><><><><><><>

Generate {self.number_of_searches_to_run} google searches that will help you fulfill any questions in the instructions.
Make them each target different aspects of the question.
Please provide the searches as a list of strings like this:
["search 1", "search 2"]
Give no other text than the list of search terms.
```

**Variables:**
- `{prompt}` - The research prompt/question
- `{self.number_of_searches_to_run}` - Number of searches to generate (default: 2)

**Output:** Returns a list of strings (search queries)

---

### 1.4 SmartSearcher - Advanced Query Generation (with Filters)

**Purpose:** Generate search queries with domain/date/keyword filters.

**Location:** `forecasting_tools/agents_and_tools/research/smart_searcher.py::__create_search_queries_with_filters()`

**Model:** From SmartSearcher config

**Temperature:** From SmartSearcher config

**Prompt:**
```
You have been given the following instructions. Instructions are included between <><><><><><><><><><><><> tags.

<><><><><><>START INSTRUCTIONS<><><><><><>
{prompt}
<><><><><><>END INSTRUCTIONS<><><><><><>

Generate {self.number_of_searches_to_run} google searches that will help you fulfill any questions in the instructions.
Consider and walk through the following before giving your json answers:
- What are some possible search queries and strategies that would be useful?
- What are the aspects of the question that are most important? Are there multiple aspects?
- Where is the information you need likely to be found or what will good sources likely contain in them?
- Would it already be at the top of the search results, or should you filter for it?
- What filters would help you achieve this to increase the information density of the results?
- You have limited searches, which approaches would be highest priority?
Please only use the additional search fields ONLY IF it would return useful results.
Don't unnecessarily constrain results.
Remember today is {datetime.now().strftime("%Y-%m-%d")}.

{self.llm.get_schema_format_instructions_for_pydantic_type(SearchInput)}

Make sure to return a list of the search inputs as a list of JSON objects in this schema.
This should be a list, not a dict that contains a list. The list can be of one item.
```

**Variables:**
- `{prompt}` - The research prompt/question
- `{self.number_of_searches_to_run}` - Number of searches to generate
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{self.llm.get_schema_format_instructions_for_pydantic_type(SearchInput)}` - Pydantic schema instructions for SearchInput

**Output:** Returns a list of `SearchInput` objects with optional filters (domain, date_range, keywords, etc.)

---

### 1.5 SmartSearcher - Report Compilation

**Purpose:** Compile final research report from search results.

**Location:** `forecasting_tools/agents_and_tools/research/smart_searcher.py::__compile_report()`

**Model:** From SmartSearcher config (default: `gpt-4.1`)

**Temperature:** From SmartSearcher config

**Prompt:**
```
Today is {datetime.now().strftime("%Y-%m-%d")}.
You have been given the following instructions. Instructions are included between <><><><><><><><><><><><> tags.

<><><><><><><><><><><><>
{original_instructions}
<><><><><><><><><><><><>


After searching the internet, you found the following results. Results are included between <><><><><><><><><><><><> tags.
<><><><><><><><><><><><>
{search_result_context}
<><><><><><><><><><><><>

Please follow the instructions and use the search results to answer the question. Unless the instructions specifify otherwise, please cite your sources inline and use markdown formatting.

For instance, this quote:
> [1] "SpaceX successfully completed a full flight test of its Starship spacecraft on April 20, 2023"

Would be cited like this:
> SpaceX successfully completed a full flight test of its Starship spacecraft on April 20, 2023 [1].
```

**Variables:**
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{original_instructions}` - Original research prompt
- `{search_result_context}` - Formatted search results with citations (format: `[N] "quote text". [This quote is from {url} titled "{title}", published on {date}]`)

**Output:** Research report with inline citations

---

## 2. Forecasting Stage

The Metaculus framework uses a **single-stage** forecasting approach (no separate outside/inside view). The research is provided directly to the forecaster, who makes a final prediction.

### 2.1 Binary Questions - Forecasting

**Purpose:** Generate final probability prediction for binary questions.

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_run_forecast_on_binary()`

**Model:** `default` LLM from config (default: varies by bot)

**Temperature:** From model config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

Question background:
{question.background_info}


This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
{question.resolution_criteria}

{question.fine_print}


Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A brief description of a scenario that results in a No outcome.
(d) A brief description of a scenario that results in a Yes outcome.

You write your rationale remembering that good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time.
{self._get_conditional_disclaimer_if_necessary(question)}

The last thing you write is your final answer as: "Probability: ZZ%", 0-100
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{research}` - Research summary from research stage
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{self._get_conditional_disclaimer_if_necessary(question)}` - Conditional question disclaimer (if applicable)

**Output Format:** Must end with `Probability: ZZ%` where ZZ is 0-100.

**Post-processing:** Uses `structure_output()` to extract and validate the prediction into a `BinaryPrediction` Pydantic model.

---

### 2.2 Multiple Choice Questions - Forecasting

**Purpose:** Generate probability distribution across options.

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_run_forecast_on_multiple_choice()`

**Model:** `default` LLM from config

**Temperature:** From model config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

The options are: {question.options}


Background:
{question.background_info}

{question.resolution_criteria}

{question.fine_print}


Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A description of a scenario that results in an unexpected outcome.

{self._get_conditional_disclaimer_if_necessary(question)}
You write your rationale remembering that (1) good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time, and (2) good forecasters leave some moderate probability on most options to account for unexpected outcomes.

The last thing you write is your final probabilities for the N options in this order {question.options} as:
Option_A: Probability_A
Option_B: Probability_B
...
Option_N: Probability_N
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.options}` - List of options
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{research}` - Research summary
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{self._get_conditional_disclaimer_if_necessary(question)}` - Conditional disclaimer (if applicable)

**Output Format:** Must end with `Option_X: Probability_X` for each option.

**Post-processing:** Uses `structure_output()` with parsing instructions to extract into `PredictedOptionList` Pydantic model. Parsing instructions ensure:
- Option names match exactly
- "Option" prefix is removed if not part of actual option name
- 0% probabilities are included (not skipped)
- Probabilities are normalized to sum to 1.0

---

### 2.3 Numeric Questions - Forecasting

**Purpose:** Generate percentile estimates for numeric questions.

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_run_forecast_on_numeric()`

**Model:** `default` LLM from config

**Temperature:** From model config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

Background:
{question.background_info}

{question.resolution_criteria}

{question.fine_print}

Units for answer: {question.unit_of_measure if question.unit_of_measure else "Not stated (please infer this)"}

Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

{lower_bound_message}
{upper_bound_message}

Formatting Instructions:
- Please notice the units requested and give your answer in these units (e.g. whether you represent a number as 1,000,000 or 1 million).
- Never use scientific notation.
- Always start with a smaller number (more negative if negative) and then increase from there. The value for percentile 10 should always be less than the value for percentile 20, and so on.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The outcome if nothing changed.
(c) The outcome if the current trend continued.
(d) The expectations of experts and markets.
(e) A brief description of an unexpected scenario that results in a low outcome.
(f) A brief description of an unexpected scenario that results in a high outcome.

{self._get_conditional_disclaimer_if_necessary(question)}
You remind yourself that good forecasters are humble and set wide 90/10 confidence intervals to account for unknown unknowns.

The last thing you write is your final answer as:
"
Percentile 10: XX (lowest number value)
Percentile 20: XX
Percentile 40: XX
Percentile 60: XX
Percentile 80: XX
Percentile 90: XX (highest number value)
"
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{question.unit_of_measure}` - Units for the answer
- `{research}` - Research summary
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{lower_bound_message}` - Formatted lower bound message (e.g., "The outcome can not be lower than X units." or "The question creator thinks the number is likely not lower than X units.")
- `{upper_bound_message}` - Formatted upper bound message
- `{self._get_conditional_disclaimer_if_necessary(question)}` - Conditional disclaimer (if applicable)

**Output Format:** Must include percentiles 10, 20, 40, 60, 80, 90 in the specified format.

**Post-processing:** Uses `structure_output()` with parsing instructions to extract into `list[Percentile]`, then converts to `NumericDistribution`. Parsing instructions:
- Ensure values are in correct units
- Handle unit conversions (e.g., $500M → 0.5 if units are "B $")
- Convert scientific notation to regular numbers
- Require explicit percentiles (reject single-value answers)

**CDF Generation:** The `NumericDistribution.from_question()` method interpolates the 6 percentiles into a 201-point CDF using PCHIP interpolation.

---

### 2.4 Date Questions - Forecasting

**Purpose:** Generate date estimates for date questions.

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_run_forecast_on_date()`

**Model:** `default` LLM from config

**Temperature:** From model config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

Background:
{question.background_info}

{question.resolution_criteria}

{question.fine_print}

Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

{lower_bound_message}
{upper_bound_message}

Formatting Instructions:
- This is a date question, and as such, the answer must be expressed in terms of dates.
- The dates must be written in the format of YYYY-MM-DD. If hours matter, please append the date with the hour in UTC and military time: YYYY-MM-DDTHH:MM:SSZ. No other formatting is allowed.
- Always start with a lower date chronologically and then increase from there.
- Do NOT forget this. The dates must be written in chronological order starting at the earliest time at percentile 10 and increasing from there.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The outcome if nothing changed.
(c) The outcome if the current trend continued.
(d) The expectations of experts and markets.
(e) A brief description of an unexpected scenario that results in a low outcome.
(f) A brief description of an unexpected scenario that results in a high outcome.

{self._get_conditional_disclaimer_if_necessary(question)}
You remind yourself that good forecasters are humble and set wide 90/10 confidence intervals to account for unknown unknowns.

The last thing you write is your final answer as:
"
Percentile 10: YYYY-MM-DD (oldest date)
Percentile 20: YYYY-MM-DD
Percentile 40: YYYY-MM-DD
Percentile 60: YYYY-MM-DD
Percentile 80: YYYY-MM-DD
Percentile 90: YYYY-MM-DD (newest date)
"
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{research}` - Research summary
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{lower_bound_message}` - Formatted lower bound (date)
- `{upper_bound_message}` - Formatted upper bound (date)
- `{self._get_conditional_disclaimer_if_necessary(question)}` - Conditional disclaimer (if applicable)

**Output Format:** Must include dates in YYYY-MM-DD format (or YYYY-MM-DDTHH:MM:SSZ if hours matter) for percentiles 10, 20, 40, 60, 80, 90.

**Post-processing:** Converts dates to timestamps, then creates `NumericDistribution` for CDF submission.

---

### 2.5 Q2 Template Bot - Binary Forecasting

**Purpose:** Simpler binary forecasting prompt (Q2 2025 version).

**Location:** `forecasting_tools/forecast_bots/official_bots/q2_template_bot.py::_run_forecast_on_binary()`

**Model:** `default` LLM from config

**Temperature:** From model config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

Question background:
{question.background_info}


This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
{question.resolution_criteria}

{question.fine_print}


Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A brief description of a scenario that results in a No outcome.
(d) A brief description of a scenario that results in a Yes outcome.

You write your rationale remembering that good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time.

The last thing you write is your final answer as: "Probability: ZZ%", 0-100
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{research}` - Research summary
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date

**Post-processing:** Uses `PredictionExtractor.extract_last_percentage_value()` to extract probability, bounds to [0.01, 0.99].

---

### 2.6 Q2 Template Bot - Multiple Choice Forecasting

**Purpose:** Multiple choice forecasting (Q2 2025 version).

**Location:** `forecasting_tools/forecast_bots/official_bots/q2_template_bot.py::_run_forecast_on_multiple_choice()`

**Model:** `default` LLM from config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

The options are: {question.options}


Background:
{question.background_info}

{question.resolution_criteria}

{question.fine_print}


Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A description of an scenario that results in an unexpected outcome.

You write your rationale remembering that (1) good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time, and (2) good forecasters leave some moderate probability on most options to account for unexpected outcomes.

The last thing you write is your final probabilities for the N options in this order {question.options} as:
Option_A: Probability_A
Option_B: Probability_B
...
Option_N: Probability_N
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.options}` - List of options
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{research}` - Research summary
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date

**Post-processing:** Uses `PredictionExtractor.extract_option_list_with_percentage_afterwards()` to extract distribution.

---

### 2.7 Q2 Template Bot - Numeric Forecasting

**Purpose:** Numeric forecasting (Q2 2025 version).

**Location:** `forecasting_tools/forecast_bots/official_bots/q2_template_bot.py::_run_forecast_on_numeric()`

**Model:** `default` LLM from config

**Prompt:**
```
You are a professional forecaster interviewing for a job.

Your interview question is:
{question.question_text}

Background:
{question.background_info}

{question.resolution_criteria}

{question.fine_print}

Units for answer: {question.unit_of_measure if question.unit_of_measure else "Not stated (please infer this)"}

Your research assistant says:
{research}

Today is {datetime.now().strftime("%Y-%m-%d")}.

{lower_bound_message}
{upper_bound_message}

Formatting Instructions:
- Please notice the units requested (e.g. whether you represent a number as 1,000,000 or 1 million).
- Never use scientific notation.
- Always start with a smaller number (more negative if negative) and then increase from there

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The outcome if nothing changed.
(c) The outcome if the current trend continued.
(d) The expectations of experts and markets.
(e) A brief description of an unexpected scenario that results in a low outcome.
(f) A brief description of an unexpected scenario that results in a high outcome.

You remind yourself that good forecasters are humble and set wide 90/10 confidence intervals to account for unknown unknowns.

The last thing you write is your final answer as:
"
Percentile 10: XX
Percentile 20: XX
Percentile 40: XX
Percentile 60: XX
Percentile 80: XX
Percentile 90: XX
"
```

**Variables:**
- `{question.question_text}` - Question text
- `{question.background_info}` - Background information
- `{question.resolution_criteria}` - Resolution criteria
- `{question.fine_print}` - Fine print
- `{question.unit_of_measure}` - Units
- `{research}` - Research summary
- `{datetime.now().strftime("%Y-%m-%d")}` - Current date
- `{lower_bound_message}` - Lower bound message (empty if open bound)
- `{upper_bound_message}` - Upper bound message (empty if open bound)

**Post-processing:** Uses `PredictionExtractor.extract_numeric_distribution_from_list_of_percentile_number_and_probability()` to extract percentiles and create CDF.

---

## 3. Structured Output Parsing

The framework uses `structure_output()` to parse LLM responses into Pydantic models. This adds validation and retry logic.

### 3.1 Binary Prediction Parsing

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_binary_prompt_to_forecast()`

**Model:** `parser` LLM from config (default: `gpt-4o-mini`)

**Process:**
1. LLM generates reasoning with `Probability: ZZ%` at the end
2. `structure_output()` extracts into `BinaryPrediction` Pydantic model
3. Validates and bounds to [0.01, 0.99]

**No additional prompt** - uses the reasoning text directly.

---

### 3.2 Multiple Choice Parsing Instructions

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_multiple_choice_prompt_to_forecast()`

**Model:** `parser` LLM from config

**Parsing Instructions:**
```
Make sure that all option names are one of the following:
{question.options}

The text you are parsing may prepend these options with some variation of "Option" which you should remove if not part of the option names I just gave you.
Additionally, you may sometimes need to parse a 0% probability. Please do not skip options with 0% but rather make it an entry in your final list with 0% probability.
```

**Process:**
1. LLM generates reasoning with `Option_X: Probability_X` format
2. `structure_output()` extracts into `PredictedOptionList` with these parsing instructions
3. Validates option names match exactly
4. Normalizes probabilities to sum to 1.0

---

### 3.3 Numeric Parsing Instructions

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_numeric_prompt_to_forecast()`

**Model:** `parser` LLM from config

**Parsing Instructions:**
```
The text given to you is trying to give a forecast distribution for a numeric question.
- This text is trying to answer the numeric question: "{question.question_text}".
- When parsing the text, please make sure to give the values (the ones assigned to percentiles) in terms of the correct units.
- The units for the forecast are: {question.unit_of_measure}
- Your work will be shown publicly with these units stated verbatim after the numbers your parse.
- As an example, someone else guessed that the answer will be between {question.lower_bound} {question.unit_of_measure} and {question.upper_bound} {question.unit_of_measure}, so the numbers parsed from an answer like this would be verbatim "{question.lower_bound}" and "{question.upper_bound}".
- If the answer doesn't give the answer in the correct units, you should parse it in the right units. For instance if the answer gives numbers as $500,000,000 and units are "B $" then you should parse the answer as 0.5 (since $500,000,000 is $0.5 billion).
- If percentiles are not explicitly given (e.g. only a single value is given) please don't return a parsed output, but rather indicate that the answer is not explicitly given in the text.
- Turn any values that are in scientific notation into regular numbers.
```

**Process:**
1. LLM generates reasoning with percentiles
2. `structure_output()` extracts into `list[Percentile]` with unit conversion
3. Creates `NumericDistribution` from percentiles
4. Generates 201-point CDF via interpolation

---

## 4. Conditional Questions

### 4.1 Conditional Disclaimer

**Purpose:** Instructions for forecasting conditional (parent/child) questions.

**Location:** `forecasting_tools/forecast_bots/official_bots/template_bot_2026_spring.py::_get_conditional_disclaimer_if_necessary()`

**Added to prompts when:** `question.conditional_type in ["yes", "no"]`

**Disclaimer Text:**
```
As you are given a conditional question with a parent and child, you are to only forecast the **CHILD** question, given the parent question's resolution.
You never re-forecast the parent question under any circumstances, but you use probabilistic reasoning, strongly considering the parent question's resolution, to forecast the child question.
```

---

## Pipeline Flow Summary

### Standard Flow (Template Bot):
1. **Research:** `run_research()` → Research summary string
2. **Forecast:** `_run_forecast_on_*()` → LLM reasoning with prediction
3. **Parse:** `structure_output()` → Validated Pydantic model
4. **Aggregate:** Multiple forecasts aggregated (if `predictions_per_research_report > 1`)
5. **Submit:** Post to Metaculus (if `publish_reports_to_metaculus=True`)

### Research Options:
- **AskNews:** `asknews/news-summaries` or `asknews/deep-research/*` → Pre-formatted news summaries
- **SmartSearcher:** `smart-searcher/{model}` → Exa.ai search with LLM synthesis
- **Custom LLM:** Any `GeneralLlm` instance → Custom research logic

### Forecasting Options:
- **Single prediction:** `predictions_per_research_report=1`
- **Multiple predictions:** `predictions_per_research_report=5` → 5 independent forecasts aggregated
- **Multiple research reports:** `research_reports_per_question=3` → 3 research attempts, each with N predictions

---

## Model Configuration

**Default Models (Template Bot 2026 Spring):**
- **Forecasting:** Varies by bot (can be configured via `llms` parameter)
- **Research:** `asknews/news-summaries` (default) or `smart-searcher/*` or custom
- **Parser:** `gpt-4o-mini` (for structured output extraction)
- **Summarizer:** `gpt-4o-mini` (for report summarization)

**Q2 Template Bot Defaults:**
- **Forecasting:** Varies (configurable)
- **Research:** `asknews/news-summaries` (default)

**Main Bot (Q2TemplateBot2025):**
- **Forecasting:** `openai/o3` (temperature=1)
- **Research:** `asknews/news-summaries`
- **Summarizer:** `openai/gpt-4o` (temperature=0)

---

## Key Differences from Your Implementation

1. **Single-stage forecasting:** No separate outside/inside view - research is provided directly to forecaster
2. **Structured output parsing:** Uses LLM-based parsing with Pydantic validation instead of regex
3. **Flexible research:** Multiple research backends (AskNews, SmartSearcher, custom) with same interface
4. **Multiple independent forecasts:** Generates N independent predictions per research report, aggregates them
5. **No explicit ensemble roles:** All forecasters use the same prompt (diversity from multiple independent runs)
6. **Simpler prompts:** Less structured than your step-by-step approach - more conversational
7. **Conditional question support:** Built-in handling for parent/child conditional questions
8. **Date question support:** Special handling for date questions with date formatting requirements
9. **No calibration checklist:** No separate calibration stage - checklist items are implicit in the prompt
10. **Research-first approach:** Research is generated once, then multiple forecasts are made from it (vs. your approach of research → outside view → inside view)

---

## Prompt Philosophy

The Metaculus framework emphasizes:
- **Simplicity:** Single-stage forecasting with research provided upfront
- **Flexibility:** Easy to override and customize individual methods
- **Robustness:** Structured output parsing with validation and retry logic
- **Modularity:** Research and forecasting are separate, swappable components
- **Practicality:** Focus on getting working forecasts quickly, less emphasis on theoretical frameworks

Your implementation emphasizes:
- **Theoretical rigor:** Explicit outside view → inside view separation
- **Structured reasoning:** Step-by-step analysis with explicit evidence classification
- **Ensemble diversity:** Different agent roles/perspectives
- **Calibration:** Explicit checklist and calibration stage
- **Comprehensive documentation:** Detailed reasoning at each stage
