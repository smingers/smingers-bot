# Local Questions

This directory contains locally-defined questions for the forecasting bot.

## Usage

```bash
# Forecast a specific question by ID (filename stem)
python main.py --source local --question binary_example --mode test

# Forecast a question by file path
python main.py --source local --question examples/numeric_example.yaml --mode test

# List available questions
python -c "from src.sources.local import LocalSource; s = LocalSource(); print(s.list_questions())"
```

## Creating Questions

Copy one of the example templates and modify for your question:

- `examples/binary_example.yaml` - Yes/No questions
- `examples/numeric_example.yaml` - Continuous value questions
- `examples/multiple_choice_example.yaml` - Multiple option questions

### Required Fields

All question types:
- `title` - The question text
- `question_type` - One of: `binary`, `numeric`, `multiple_choice`
- `description` - Background context
- `resolution_criteria` - How the question will be resolved

Type-specific:
- **numeric**: `lower_bound`, `upper_bound`
- **multiple_choice**: `options` (list of strings)

### Optional Fields

- `id` - Question identifier (defaults to filename)
- `fine_print` - Edge cases and clarifications
- `background_info` - Additional context
- `scheduled_close_time` - When forecasting closes (ISO 8601)
- `scheduled_resolve_time` - When question resolves (ISO 8601)
- `collection_id` - Group questions into collections

For numeric questions:
- `open_lower_bound` / `open_upper_bound` - Whether bounds can be exceeded
- `nominal_lower_bound` / `nominal_upper_bound` - Suggested tighter range
- `unit_of_measure` - Units for display (e.g., "USD", "people")
- `zero_point` - Reference point for log-scale questions

## Collections

Organize questions into subdirectories:

```
local_questions/
├── examples/
│   ├── binary_example.yaml
│   └── numeric_example.yaml
├── work/
│   └── project_forecast.yaml
└── personal/
    └── my_prediction.yaml
```

Forecast all questions in a collection:
```bash
python main.py --source local --tournament work --mode test
```
