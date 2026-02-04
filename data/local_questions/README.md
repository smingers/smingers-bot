# Local Questions

Store your custom forecasting questions here as YAML files.

## Quick Start

1. Copy an example from `examples/` to this directory
2. Rename and edit to match your question
3. Run: `python main.py --source local --question <filename> --mode test`

## File Format

```yaml
id: "my_question"           # Optional: defaults to filename
title: "Will X happen?"     # Required
question_type: binary       # binary, numeric, or multiple_choice
description: |
  Background context...
resolution_criteria: |
  Resolves YES if...
fine_print: |
  Edge cases...

# For numeric questions:
lower_bound: 0
upper_bound: 100
unit_of_measure: "units"

# For multiple choice:
options:
  - "Option A"
  - "Option B"
  - "Option C"
```

## Organization

You can organize questions into subdirectories (collections):

```
local_questions/
  my_question.yaml
  work/
    project_a.yaml
    project_b.yaml
  personal/
    question_1.yaml
```

## Examples

See the `examples/` directory for complete templates:
- `binary_example.yaml` - Yes/No questions
- `numeric_example.yaml` - Continuous value questions
- `multiple_choice_example.yaml` - Multiple option questions
