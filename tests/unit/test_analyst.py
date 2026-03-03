"""
Tests for the Analyst tool (code execution for quantitative analysis).

Tests cover:
- Code block extraction from LLM responses
- Subprocess execution with known Python code
- Full run with mocked LLM (success, retry, exhausted retries)
- Output formatting (XML wrapping)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.analyst import AnalystTool

# ============================================================================
# Helper: fake LLMResponse
# ============================================================================


def _make_response(content: str, cost: float = 0.001) -> MagicMock:
    """Create a mock LLMResponse with the given content."""
    resp = MagicMock()
    resp.content = content
    resp.cost = cost
    return resp


# ============================================================================
# Code Block Extraction Tests
# ============================================================================


class TestExtractCodeBlock:
    """Tests for _extract_code_block static method."""

    def test_extracts_python_block(self):
        response = '```python\nprint("hello")\n```'
        assert AnalystTool._extract_code_block(response) == 'print("hello")'

    def test_extracts_with_surrounding_text(self):
        response = "Here is the code:\n```python\nx = 42\nprint(x)\n```\nThis should work."
        assert AnalystTool._extract_code_block(response) == "x = 42\nprint(x)"

    def test_returns_none_for_no_block(self):
        response = "I cannot write code for this query."
        assert AnalystTool._extract_code_block(response) is None

    def test_takes_first_block(self):
        response = "```python\nprint(1)\n```\n\n```python\nprint(2)\n```"
        assert AnalystTool._extract_code_block(response) == "print(1)"

    def test_handles_generic_code_block(self):
        response = "```\nimport numpy as np\nprint(np.pi)\n```"
        assert AnalystTool._extract_code_block(response) == "import numpy as np\nprint(np.pi)"

    def test_prefers_python_over_generic(self):
        response = '```python\nprint("python")\n```\n\n```\nprint("generic")\n```'
        assert AnalystTool._extract_code_block(response) == 'print("python")'

    def test_handles_multiline_code(self):
        response = '```python\nimport pandas as pd\ndf = pd.DataFrame({"a": [1,2,3]})\nprint(df.describe())\n```'
        code = AnalystTool._extract_code_block(response)
        assert "import pandas" in code
        assert "df.describe()" in code

    def test_strips_whitespace(self):
        response = '```python\n\n  print("hello")  \n\n```'
        assert AnalystTool._extract_code_block(response) == 'print("hello")'

    def test_fallback_raw_python_import(self):
        response = "import numpy as np\nprint(np.mean([1,2,3]))"
        assert AnalystTool._extract_code_block(response) == response

    def test_fallback_raw_python_from_import(self):
        response = "from datetime import datetime\nprint(datetime.now())"
        assert AnalystTool._extract_code_block(response) == response

    def test_fallback_raw_python_comment(self):
        response = '# Compute stats\nimport pandas as pd\nprint("done")'
        assert AnalystTool._extract_code_block(response) == response

    def test_no_fallback_for_prose(self):
        response = "The analysis shows that returns are normally distributed."
        assert AnalystTool._extract_code_block(response) is None


# ============================================================================
# Subprocess Execution Tests
# ============================================================================


class TestExecuteCode:
    """Tests for _execute_code method with real subprocess execution."""

    @pytest.fixture
    def tool(self):
        llm = MagicMock()
        return AnalystTool(llm=llm, model="test-model", timeout=10)

    def test_successful_execution(self, tool):
        stdout, stderr, returncode = asyncio.run(tool._execute_code('print("hello world")'))
        assert returncode == 0
        assert "hello world" in stdout
        assert stderr == "" or "warning" in stderr.lower() or stderr.strip() == ""

    def test_syntax_error(self, tool):
        stdout, stderr, returncode = asyncio.run(tool._execute_code("print("))
        assert returncode != 0
        assert "SyntaxError" in stderr

    def test_runtime_error(self, tool):
        stdout, stderr, returncode = asyncio.run(tool._execute_code("x = 1/0"))
        assert returncode != 0
        assert "ZeroDivisionError" in stderr

    def test_import_error(self, tool):
        stdout, stderr, returncode = asyncio.run(
            tool._execute_code("import nonexistent_module_xyz")
        )
        assert returncode != 0
        assert "ModuleNotFoundError" in stderr or "ImportError" in stderr

    def test_timeout(self):
        llm = MagicMock()
        tool = AnalystTool(llm=llm, model="test-model", timeout=2)
        stdout, stderr, returncode = asyncio.run(tool._execute_code("import time; time.sleep(10)"))
        assert returncode == -1
        assert "timed out" in stderr.lower()

    def test_multiline_output(self, tool):
        code = 'for i in range(5):\n    print(f"value_{i} = {i*10}")'
        stdout, stderr, returncode = asyncio.run(tool._execute_code(code))
        assert returncode == 0
        assert "value_0 = 0" in stdout
        assert "value_4 = 40" in stdout

    def test_computation(self, tool):
        code = "import math\nprint(f'pi = {math.pi:.4f}')\nprint(f'e = {math.e:.4f}')"
        stdout, stderr, returncode = asyncio.run(tool._execute_code(code))
        assert returncode == 0
        assert "pi = 3.1416" in stdout
        assert "e = 2.7183" in stdout


# ============================================================================
# Full Run Tests (mocked LLM)
# ============================================================================


class TestAnalystRun:
    """Tests for the full run() method with mocked LLM calls."""

    @pytest.fixture
    def mock_llm(self):
        return AsyncMock()

    def test_successful_run(self, mock_llm):
        """LLM generates valid code that runs successfully."""
        mock_llm.complete.return_value = _make_response('```python\nprint("result = 42")\n```')
        tool = AnalystTool(llm=mock_llm, model="test-model")
        result = asyncio.run(tool.run("compute something"))

        assert "<AnalystReport" in result
        assert "result = 42" in result
        assert "Code executed successfully" in result
        assert mock_llm.complete.call_count == 1

    def test_retry_on_error(self, mock_llm):
        """First code fails, retry produces working code."""
        mock_llm.complete.side_effect = [
            _make_response('```python\nraise ValueError("oops")\n```'),
            _make_response('```python\nprint("fixed = 99")\n```'),
        ]
        tool = AnalystTool(llm=mock_llm, model="test-model", max_retries=2)
        result = asyncio.run(tool.run("compute something"))

        assert "fixed = 99" in result
        assert "Code executed successfully" in result
        assert mock_llm.complete.call_count == 2

    def test_all_retries_exhausted(self, mock_llm):
        """All attempts produce failing code."""
        mock_llm.complete.return_value = _make_response(
            '```python\nraise RuntimeError("always fails")\n```'
        )
        tool = AnalystTool(llm=mock_llm, model="test-model", max_retries=1)
        result = asyncio.run(tool.run("compute something"))

        assert "<AnalystReport" in result
        assert "Error:" in result
        assert "All 2 attempts failed" in result
        # 1 initial + 1 retry = 2 LLM calls
        assert mock_llm.complete.call_count == 2

    def test_no_code_block_in_response(self, mock_llm):
        """LLM returns text without a code block."""
        mock_llm.complete.return_value = _make_response("I cannot perform this analysis because...")
        tool = AnalystTool(llm=mock_llm, model="test-model")
        result = asyncio.run(tool.run("impossible query"))

        assert "<AnalystReport" in result
        assert "Error:" in result
        assert "Failed to generate code" in result

    def test_no_code_block_on_retry(self, mock_llm):
        """First attempt fails, retry returns no code block."""
        mock_llm.complete.side_effect = [
            _make_response('```python\nraise ValueError("fail")\n```'),
            _make_response("I cannot fix this code."),
        ]
        tool = AnalystTool(llm=mock_llm, model="test-model", max_retries=1)
        result = asyncio.run(tool.run("some query"))

        assert "Error:" in result
        assert "Failed to generate fixed code" in result

    def test_code_with_no_output(self, mock_llm):
        """Code runs successfully but prints nothing."""
        mock_llm.complete.side_effect = [
            _make_response("```python\nx = 42\n```"),  # No print
            _make_response('```python\nprint("fixed")\n```'),
        ]
        tool = AnalystTool(llm=mock_llm, model="test-model", max_retries=1)
        result = asyncio.run(tool.run("compute something"))

        assert "fixed" in result

    def test_cost_tracking(self, mock_llm):
        """Total cost is accumulated across LLM calls."""
        mock_llm.complete.side_effect = [
            _make_response('```python\nraise ValueError("fail")\n```', cost=0.005),
            _make_response('```python\nprint("ok")\n```', cost=0.003),
        ]
        tool = AnalystTool(llm=mock_llm, model="test-model", max_retries=1)
        asyncio.run(tool.run("query"))

        assert abs(tool.total_cost - 0.008) < 1e-9

    def test_last_code_stored(self, mock_llm):
        """The _last_code attribute holds the most recent code."""
        mock_llm.complete.return_value = _make_response('```python\nprint("hello")\n```')
        tool = AnalystTool(llm=mock_llm, model="test-model")
        asyncio.run(tool.run("query"))

        assert tool._last_code == 'print("hello")'


# ============================================================================
# Output Formatting Tests
# ============================================================================


class TestExtractCodeBlockTruncated:
    """Tests for truncated code blocks (no closing fence)."""

    def test_truncated_python_block(self):
        response = "```python\nimport numpy as np\nprint(np.pi)"
        code = AnalystTool._extract_code_block(response)
        assert code is not None
        assert "import numpy" in code

    def test_truncated_generic_block(self):
        response = '```\nprint("hello")\nx = 42'
        code = AnalystTool._extract_code_block(response)
        assert code is not None
        assert 'print("hello")' in code

    def test_prefers_closed_over_truncated(self):
        response = '```python\nprint("closed")\n```\n\nMore text'
        code = AnalystTool._extract_code_block(response)
        assert code == 'print("closed")'


class TestExtractProse:
    """Tests for _extract_prose static method."""

    def test_extracts_prose_before_code(self):
        response = 'Here is my analysis of the problem.\n\n```python\nprint("hi")\n```'
        prose = AnalystTool._extract_prose(response)
        assert prose is not None
        assert "analysis of the problem" in prose

    def test_extracts_prose_after_code(self):
        response = '```python\nprint("hi")\n```\n\nThe results show that the mean is positive, indicating upward drift.'
        prose = AnalystTool._extract_prose(response)
        assert prose is not None
        assert "mean is positive" in prose

    def test_no_prose_for_code_only(self):
        response = '```python\nprint("hi")\n```'
        prose = AnalystTool._extract_prose(response)
        assert prose is None

    def test_no_prose_for_short_fragments(self):
        response = 'OK:\n```python\nprint("hi")\n```'
        prose = AnalystTool._extract_prose(response)
        assert prose is None


class TestFormatResult:
    """Tests for _format_result and _format_error."""

    @pytest.fixture
    def tool(self):
        llm = MagicMock()
        return AnalystTool(llm=llm, model="test-model")

    def test_format_result_wraps_in_xml(self, tool):
        result = tool._format_result("my query", "output data", "print('hi')")
        assert '<AnalystReport query="my query">' in result
        assert "Code executed successfully" in result
        assert "output data" in result
        assert result.strip().endswith("</AnalystReport>")

    def test_format_result_truncates_long_output(self, tool):
        long_output = "x" * 15000
        result = tool._format_result("q", long_output, "code")
        assert "truncated" in result
        assert len(result) < 12000

    def test_format_result_includes_prose(self, tool):
        tool._last_prose = "The distribution is right-skewed with fat tails."
        result = tool._format_result("my query", "output data", "code")
        assert "Analyst notes:" in result
        assert "right-skewed" in result

    def test_format_result_no_prose_section_when_none(self, tool):
        tool._last_prose = None
        result = tool._format_result("my query", "output data", "code")
        assert "Analyst notes:" not in result

    def test_format_error_wraps_in_xml(self):
        result = AnalystTool._format_error("my query", "something went wrong")
        assert result.startswith('<AnalystReport query="my query">')
        assert "Error: something went wrong" in result
        assert result.endswith("</AnalystReport>")

    def test_format_result_truncates_long_query(self, tool):
        long_query = "q" * 500
        result = tool._format_result(long_query, "output", "code")
        # Query in XML attribute is truncated to 200 chars
        assert len(long_query[:200]) == 200
        assert 'query="' + "q" * 200 + '"' in result
