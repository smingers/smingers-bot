# Refactoring Plan: Multi-Source Question Abstraction

## Overview

This plan outlines how to encapsulate Metaculus-specific elements so the forecasting pipeline can support multiple question sources (Metaculus, Polymarket, etc.) in the future. The goal is to achieve **zero functional changes** for Metaculus forecasting while creating clean abstractions for adding new sources.

## Current Architecture Analysis

### Metaculus-Specific Touch Points

After analyzing the codebase, here are all the Metaculus-specific integration points:

| Layer | File(s) | Metaculus-Specific Elements |
|-------|---------|----------------------------|
| **API Client** | `src/utils/metaculus_api.py` | Token auth, `/api/posts/` endpoints, question parsing, submission payloads |
| **Data Models** | `src/utils/metaculus_api.py` | `MetaculusQuestion` dataclass with Metaculus-specific field names |
| **Orchestrator** | `src/bot/forecaster.py` | Direct `MetaculusClient` usage, `MetaculusQuestion` type hints |
| **CLI** | `main.py`, `run_bot.py` | Tournament IDs, URL parsing, `--tournament` flags |
| **Submission** | `src/utils/metaculus_api.py` | 3 submit methods with Metaculus payload formats |
| **Database** | `src/storage/database.py` | `tournament_id` field in `ForecastRecord` |

### Source-Agnostic Elements (Already Clean)

These components are already source-agnostic and require no changes:

- **Search Pipeline** (`src/bot/search.py`) - Uses generic `QuestionDetails` dataclass
- **Base Forecaster** (`src/bot/base_forecaster.py`) - Generic 5-agent ensemble logic
- **Type Handlers** (`binary.py`, `numeric.py`, `multiple_choice.py`) - Work with generic parameters
- **Prompts** (`src/bot/prompts.py`) - Template-based, use generic placeholders
- **Extractors** (`src/bot/extractors.py`) - Parse LLM output, source-agnostic
- **LLM Client** (`src/utils/llm.py`) - No source dependencies
- **Artifact Storage** (`src/storage/artifact_store.py`) - Generic file storage

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI Layer                                   │
│  main.py, run_bot.py (source-aware routing)                        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────┐
│                      Forecaster Orchestrator                        │
│  src/bot/forecaster.py (works with abstract Question)              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│ Question Source │    │ Question Source │    │ Question Source │
│   (Metaculus)   │    │  (Polymarket)   │    │    (Future)     │
│                 │    │                 │    │                 │
│ - API Client    │    │ - API Client    │    │ - API Client    │
│ - Q Parser      │    │ - Q Parser      │    │ - Q Parser      │
│ - Submitter     │    │ - Submitter     │    │ - Submitter     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Implementation Plan

### Phase 1: Define Abstract Question Model

**New File: `src/models/question.py`**

Create a source-agnostic question model that captures all the information the forecasting pipeline needs:

```python
from dataclasses import dataclass
from typing import Optional, Literal, Any
from datetime import datetime

@dataclass
class Question:
    """
    Source-agnostic question model.

    This is the canonical representation of a forecasting question,
    independent of which platform it originated from.
    """
    # Universal identifiers
    id: str                                    # Unique ID (could be string or int depending on source)
    source: str                                # "metaculus", "polymarket", etc.

    # Core question content
    title: str
    description: str                           # Main question text/background
    question_type: Literal["binary", "numeric", "multiple_choice"]

    # Resolution details
    resolution_criteria: str
    fine_print: str

    # Timing
    open_time: Optional[datetime]
    close_time: Optional[datetime]
    resolve_time: Optional[datetime]

    # Type-specific fields
    # Binary: none needed
    # Numeric:
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    open_lower_bound: Optional[bool] = None
    open_upper_bound: Optional[bool] = None
    unit_of_measure: Optional[str] = None
    # Multiple choice:
    options: Optional[list[str]] = None

    # Source-specific data (preserved for submission)
    source_data: Optional[dict] = None        # Raw API response, source-specific IDs, etc.

    # Community/market data (optional)
    community_prediction: Optional[float] = None

    @property
    def source_id(self) -> Any:
        """Get the source-specific ID needed for submission."""
        return self.source_data.get("source_id") if self.source_data else self.id
```

**New File: `src/models/prediction.py`**

Define prediction types that are source-agnostic:

```python
from dataclasses import dataclass
from typing import Union

@dataclass
class BinaryPrediction:
    probability: float  # 0.0 to 1.0

@dataclass
class NumericPrediction:
    cdf: list[float]    # 201-point CDF
    percentiles: dict[int, float]  # Key percentiles for display

@dataclass
class MultipleChoicePrediction:
    probabilities: dict[str, float]  # option -> probability

Prediction = Union[BinaryPrediction, NumericPrediction, MultipleChoicePrediction]
```

### Phase 2: Define Question Source Interface

**New File: `src/sources/base.py`**

Define the abstract interface that all question sources must implement:

```python
from abc import ABC, abstractmethod
from typing import Optional
from ..models.question import Question
from ..models.prediction import Prediction

class QuestionSource(ABC):
    """
    Abstract base class for question sources.

    Each source (Metaculus, Polymarket, etc.) implements this interface
    to provide question fetching and prediction submission capabilities.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the source name (e.g., 'metaculus', 'polymarket')."""
        pass

    @abstractmethod
    async def get_question(self, question_id: str) -> Question:
        """Fetch a single question by ID."""
        pass

    @abstractmethod
    async def get_questions(
        self,
        collection_id: Optional[str] = None,  # tournament, market, etc.
        status: Optional[str] = "open",
        limit: int = 100,
    ) -> list[Question]:
        """Fetch questions, optionally filtered by collection/status."""
        pass

    @abstractmethod
    async def get_forecasted_questions(
        self,
        collection_id: Optional[str] = None,
    ) -> set[str]:
        """Get IDs of questions already forecasted by the current user."""
        pass

    @abstractmethod
    async def submit_prediction(
        self,
        question: Question,
        prediction: Prediction,
    ) -> dict:
        """Submit a prediction. Returns API response."""
        pass

    @abstractmethod
    def parse_question_url(self, url: str) -> str:
        """Extract question ID from a URL."""
        pass

    async def close(self):
        """Clean up resources."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
```

### Phase 3: Implement Metaculus Source

**New File: `src/sources/metaculus.py`**

Refactor the existing `metaculus_api.py` to implement the `QuestionSource` interface:

```python
from typing import Optional
from datetime import datetime
import re

from .base import QuestionSource
from ..models.question import Question
from ..models.prediction import Prediction, BinaryPrediction, NumericPrediction, MultipleChoicePrediction

class MetaculusSource(QuestionSource):
    """
    Metaculus implementation of QuestionSource.

    Wraps the Metaculus API to provide question fetching and submission.
    """

    def __init__(self, token: Optional[str] = None):
        # ... existing MetaculusClient init logic ...
        self._client = ...  # httpx client

    @property
    def name(self) -> str:
        return "metaculus"

    async def get_question(self, question_id: str) -> Question:
        """Fetch question and convert to canonical Question model."""
        # Fetch from Metaculus API
        response = await self._client.get(f"/posts/{question_id}/")
        data = response.json()

        # Convert to canonical Question
        return self._parse_question(data)

    def _parse_question(self, data: dict) -> Question:
        """Convert Metaculus API response to canonical Question."""
        question_data = data.get("question", data)

        # Map Metaculus fields to canonical fields
        q_type = question_data.get("type", "binary")
        if q_type == "multiple_choice":
            question_type = "multiple_choice"
        elif q_type in ("numeric", "continuous"):
            question_type = "numeric"
        else:
            question_type = "binary"

        # Extract options for multiple choice
        options = None
        if question_type == "multiple_choice":
            raw_options = question_data.get("options", [])
            options = [
                opt.get("label") if isinstance(opt, dict) else opt
                for opt in raw_options
            ]

        # Extract numeric bounds
        scaling = question_data.get("scaling", {}) or {}

        return Question(
            id=str(data.get("id")),
            source="metaculus",
            title=data.get("title", ""),
            description=data.get("description") or question_data.get("description") or "",
            question_type=question_type,
            resolution_criteria=data.get("resolution_criteria") or question_data.get("resolution_criteria") or "",
            fine_print=data.get("fine_print") or question_data.get("fine_print") or "",
            open_time=self._parse_datetime(data.get("open_time")),
            close_time=self._parse_datetime(data.get("scheduled_close_time")),
            resolve_time=self._parse_datetime(data.get("scheduled_resolve_time")),
            lower_bound=scaling.get("range_min"),
            upper_bound=scaling.get("range_max"),
            open_lower_bound=question_data.get("open_lower_bound"),
            open_upper_bound=question_data.get("open_upper_bound"),
            unit_of_measure=question_data.get("unit"),
            options=options,
            source_data={
                "source_id": question_data.get("id"),  # Question ID for submission
                "post_id": data.get("id"),              # Post ID for URLs
                "raw": data,                            # Full response for debugging
            },
            community_prediction=self._extract_community_prediction(question_data),
        )

    async def submit_prediction(
        self,
        question: Question,
        prediction: Prediction,
    ) -> dict:
        """Convert canonical prediction to Metaculus format and submit."""
        question_id = question.source_data["source_id"]

        if isinstance(prediction, BinaryPrediction):
            payload = [{
                "question": question_id,
                "source": "api",
                "probability_yes": max(0.001, min(0.999, prediction.probability)),
            }]
        elif isinstance(prediction, NumericPrediction):
            payload = [{
                "question": question_id,
                "source": "api",
                "continuous_cdf": self._validate_cdf(prediction.cdf),
            }]
        elif isinstance(prediction, MultipleChoicePrediction):
            payload = [{
                "question": question_id,
                "source": "api",
                "probability_yes_per_category": prediction.probabilities,
            }]
        else:
            raise ValueError(f"Unknown prediction type: {type(prediction)}")

        response = await self._client.post("/questions/forecast/", json=payload)
        response.raise_for_status()
        return response.json()

    def parse_question_url(self, url: str) -> str:
        """Extract question ID from Metaculus URL."""
        match = re.search(r"/questions/(\d+)", url)
        if not match:
            raise ValueError(f"Could not extract question ID from URL: {url}")
        return match.group(1)

    # ... existing helper methods (_validate_cdf, _parse_datetime, etc.) ...
```

### Phase 4: Update Forecaster to Use Abstractions

**Modify: `src/bot/forecaster.py`**

Update the Forecaster class to work with the abstract `Question` model:

```python
from ..models.question import Question
from ..models.prediction import BinaryPrediction, NumericPrediction, MultipleChoicePrediction
from ..sources.base import QuestionSource
from ..sources.metaculus import MetaculusSource

class Forecaster:
    def __init__(
        self,
        config: Union[ResolvedConfig, dict],
        source: Optional[QuestionSource] = None,  # NEW: allow injecting source
    ):
        # ... existing init ...

        # Default to Metaculus for backward compatibility
        self.source = source or MetaculusSource()

    async def forecast_question(
        self,
        question_id: Optional[str] = None,
        question_url: Optional[str] = None,
        question: Optional[Question] = None,  # Now uses abstract Question
    ) -> dict:
        """Run the full forecasting pipeline for a question."""

        # Get question using the source
        if question is None:
            if question_url:
                question_id = self.source.parse_question_url(question_url)
            if question_id:
                question = await self.source.get_question(question_id)
            else:
                raise ValueError("Must provide question_id, question_url, or question object")

        # ... rest of pipeline unchanged, just use Question instead of MetaculusQuestion ...

        # Route to type-specific handler
        if question.question_type == "binary":
            forecast_result = await self._forecast_binary(question, scoped_store)
        # ... etc ...

        # Submit using the source
        if not self.dry_run:
            submission_result = await self._submit_prediction(question, forecast_result)

    async def _submit_prediction(
        self,
        question: Question,
        forecast_result: dict,
    ) -> dict:
        """Submit prediction using the question's source."""

        # Convert forecast_result to canonical Prediction
        if question.question_type == "binary":
            prediction = BinaryPrediction(probability=forecast_result["final_prediction"])
        elif question.question_type == "numeric":
            prediction = NumericPrediction(
                cdf=forecast_result["final_cdf"],
                percentiles=forecast_result["final_percentiles"],
            )
        elif question.question_type == "multiple_choice":
            prediction = MultipleChoicePrediction(
                probabilities=forecast_result["final_probabilities"]
            )

        return await self.source.submit_prediction(question, prediction)
```

### Phase 5: Update CLI for Source Selection

**Modify: `main.py`**

Add source selection while maintaining backward compatibility:

```python
from src.sources import get_source, MetaculusSource

def main():
    parser = argparse.ArgumentParser(...)

    # New: source selection (defaults to metaculus)
    parser.add_argument(
        "--source", "-s",
        type=str,
        default="metaculus",
        choices=["metaculus"],  # Add more as implemented
        help="Question source (default: metaculus)"
    )

    # ... existing args ...

    args = parser.parse_args()

    # Get appropriate source
    source = get_source(args.source)

    # Pass source to forecaster
    async with Forecaster(resolved, source=source) as forecaster:
        # ... existing logic ...
```

### Phase 6: File Structure

After refactoring, the new file structure will be:

```
src/
├── models/                     # NEW: Source-agnostic data models
│   ├── __init__.py
│   ├── question.py             # Question dataclass
│   └── prediction.py           # Prediction types
├── sources/                    # NEW: Question source implementations
│   ├── __init__.py             # get_source() factory function
│   ├── base.py                 # QuestionSource ABC
│   └── metaculus.py            # Metaculus implementation
├── bot/                        # Unchanged: forecasting pipeline
│   ├── forecaster.py           # MODIFIED: uses Question, QuestionSource
│   ├── base_forecaster.py      # Unchanged
│   ├── binary.py               # Unchanged
│   ├── numeric.py              # Unchanged
│   ├── multiple_choice.py      # Unchanged
│   ├── prompts.py              # Unchanged
│   └── ...
├── utils/
│   ├── metaculus_api.py        # DEPRECATED: functionality moved to sources/metaculus.py
│   └── llm.py                  # Unchanged
└── ...
```

## Migration Strategy

### Step 1: Add New Abstractions (Non-Breaking)
1. Create `src/models/` with `Question` and `Prediction` classes
2. Create `src/sources/` with `QuestionSource` ABC
3. Create `MetaculusSource` that wraps existing `MetaculusClient`

### Step 2: Update Forecaster (Backward Compatible)
1. Add optional `source` parameter to `Forecaster.__init__`
2. Default to `MetaculusSource` if not provided
3. Add conversion layer: `MetaculusQuestion` → `Question`
4. Keep existing `forecast_question` signature working

### Step 3: Update CLI (Backward Compatible)
1. Add `--source` flag with default `"metaculus"`
2. Existing CLI usage unchanged

### Step 4: Deprecate Old API Client
1. Mark `MetaculusClient` as deprecated
2. Point users to `MetaculusSource`
3. Keep `MetaculusClient` working for backward compatibility

### Step 5: Clean Up (Future)
1. Remove `MetaculusClient` after migration period
2. Update all imports to use new abstractions

## Testing Strategy

### Unit Tests
- `test_question_model.py`: Test `Question` creation, field access
- `test_metaculus_source.py`: Test parsing, submission format conversion
- `test_forecaster_abstraction.py`: Test forecaster works with abstract types

### Integration Tests
- Run existing Metaculus forecasts through new abstractions
- Verify identical outputs (predictions, artifacts, database records)

### Regression Testing
```bash
# Before refactor: save output
python main.py --question 41594 --mode dry_run > before.log

# After refactor: compare output
python main.py --question 41594 --mode dry_run > after.log
diff before.log after.log  # Should be empty
```

## Adding a New Source (Future Example: Polymarket)

Once the refactoring is complete, adding Polymarket support would involve:

1. **Create `src/sources/polymarket.py`**:
```python
class PolymarketSource(QuestionSource):
    @property
    def name(self) -> str:
        return "polymarket"

    async def get_question(self, question_id: str) -> Question:
        # Fetch from Polymarket API
        # Convert to canonical Question model
        pass

    async def submit_prediction(self, question: Question, prediction: Prediction) -> dict:
        # Convert prediction to Polymarket format
        # Submit via Polymarket API
        pass
```

2. **Register in `src/sources/__init__.py`**:
```python
def get_source(name: str) -> QuestionSource:
    if name == "metaculus":
        return MetaculusSource()
    elif name == "polymarket":
        return PolymarketSource()
    raise ValueError(f"Unknown source: {name}")
```

3. **Update CLI choices**:
```python
parser.add_argument("--source", choices=["metaculus", "polymarket"], ...)
```

That's it - the forecasting pipeline (research, agents, aggregation) works unchanged.

## Key Design Decisions

### 1. Question ID as String
The `Question.id` field is a string to accommodate different ID formats (Metaculus uses integers, others might use UUIDs or slugs).

### 2. Preserving Source Data
The `source_data` field on `Question` preserves source-specific information needed for submission (e.g., Metaculus's separate post_id vs question_id).

### 3. Datetime Objects
Using `datetime` objects instead of strings for timing fields enables proper comparisons and formatting.

### 4. Canonical Prediction Types
Separate `BinaryPrediction`, `NumericPrediction`, `MultipleChoicePrediction` classes make type handling explicit and enable source-specific formatting.

### 5. Factory Pattern for Sources
The `get_source()` factory function centralizes source instantiation and makes it easy to add new sources.

## Checklist

- [ ] Create `src/models/question.py`
- [ ] Create `src/models/prediction.py`
- [ ] Create `src/sources/base.py`
- [ ] Create `src/sources/metaculus.py`
- [ ] Update `src/bot/forecaster.py`
- [ ] Update `main.py`
- [ ] Update `run_bot.py`
- [ ] Add unit tests
- [ ] Run regression tests
- [ ] Update CLAUDE.md documentation
