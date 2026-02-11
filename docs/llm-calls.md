# LLM Calls in the Forecasting Pipeline

| # | Name | Model (live) | What it does |
|---|------|-------------|--------------|
| 1 | **Query Generator (historical)** | o3 | Reads the question and writes a list of search queries to find historical/background info |
| 2 | **Query Generator (current)** | o3 | Reads the question and writes a list of search queries to find recent news |
| 3 | **Article Summarizer** (N calls) | Claude Sonnet 4.5 | Summarizes each scraped web article into key facts relevant to the question. Called once per article — could be 10-20+ times across all searches including question URLs |
| 4 | **Agentic Search** (N calls per invocation) | o3 | Iterative researcher: generates queries, reads results, decides what to search next, up to 7 steps per invocation. Each step is one LLM call. Can be invoked multiple times if the Query Generator requested multiple `(Agent)` queries |
| 5-9 | **Forecasters 1-5 (outside view)** | Sonnet 4.5, Sonnet 4.5, GPT-5.2, o3, o3 | Each forecaster analyzes historical search results and makes an initial prediction |
| 10-14 | **Forecasters 1-5 (inside view)** | Sonnet 4.5, Sonnet 4.5, GPT-5.2, o3, o3 | Each forecaster gets current news + another forecaster's outside view, then makes a final prediction |

At minimum **12 LLM calls** (2 query gen + 5 outside view + 5 inside view), and in practice **20-40+** depending on how many articles get summarized and how many agentic search steps run.
