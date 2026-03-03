"""
Analyst Tool — Code Execution for Quantitative Analysis

Takes a natural-language query describing a quantitative analysis task,
uses an LLM to generate Python code, executes it in a subprocess, and
returns the computed results.

Self-contained module with no pipeline dependencies beyond LLMClient.
"""

import asyncio
import logging
import os
import re
import sys
import tempfile

from ..utils.llm import LLMClient

logger = logging.getLogger(__name__)


ANALYST_CODE_PROMPT = """You are a quantitative analyst. Write Python code to answer this query, and optionally provide brief analysis around it.

Query: {query}

Available libraries: pandas, numpy, scipy, yfinance, fredapi

Your response MUST include a ```python code block. You may also include brief analysis before or after the code block to provide context, interpretation, or caveats — this prose will be included alongside the computed results.

Code rules:
- Print all results to stdout in a clear, structured format with labels and units
- Use yfinance to fetch market data (e.g., yf.download("^N225", period="10y"))
- Use fredapi.Fred(api_key=os.environ.get("FRED_API_KEY")) to fetch FRED data
- Handle errors gracefully with try/except around data fetches
- Do NOT create plots, save files, or display images
- Do NOT use interactive features (input(), plt.show(), etc.)
- Keep the code concise and focused on the computation requested
- If fetching data, suppress download progress bars (use progress=False for yfinance)
- If the query has qualitative aspects (e.g., "identify drivers"), handle those with print statements noting the relevant dates/values so a human can interpret them

```python
# your code here
```"""


ANALYST_RETRY_PROMPT = """Your previous code produced an error. Fix the code and try again.

Original query: {query}

Previous code:
```python
{code}
```

Error output:
{stderr}

Fix the issue. Your response MUST include a ```python code block.

```python
# your fixed code here
```"""


class AnalystTool:
    """
    Executes quantitative analysis via LLM-generated Python code.

    Usage:
        tool = AnalystTool(llm=client, model="openrouter/anthropic/claude-3.5-haiku")
        result = await tool.run("Compute 7-day return distribution for ^N225")
        print(result)  # XML-wrapped output with computed statistics
    """

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        max_retries: int = 2,
        timeout: int = 30,
    ):
        self.llm = llm
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.total_cost = 0.0
        self._last_code: str | None = None  # For inspection/debugging
        self._last_raw_response: str | None = None  # Raw LLM output for diagnostics
        self._last_prose: str | None = None  # Prose analysis from LLM (outside code block)

    async def run(self, query: str) -> str:
        """
        Execute a quantitative analysis query.

        Generates Python code via LLM, executes in a subprocess, and returns
        XML-wrapped results. Retries on execution failure.

        Args:
            query: Natural-language description of the analysis to perform.

        Returns:
            XML-wrapped string with results or error message.
        """
        logger.info(f"[analyst] Starting analysis: {query[:80]}...")

        # Generate initial code
        code = await self._generate_code(query)
        if not code:
            logger.warning("[analyst] LLM returned no code block")
            return self._format_error(query, "Failed to generate code from query.")

        self._last_code = code

        # Execute with retries
        for attempt in range(1 + self.max_retries):
            stdout, stderr, returncode = await self._execute_code(code)

            if returncode == 0 and stdout.strip():
                logger.info(
                    f"[analyst] Success on attempt {attempt + 1} ({len(stdout)} chars output)"
                )
                return self._format_result(query, stdout, code)

            if returncode == 0 and not stdout.strip():
                # Code ran but produced no output
                error_msg = "Code executed but produced no output."
                if stderr.strip():
                    error_msg += f"\nStderr: {stderr.strip()}"
                logger.warning(f"[analyst] No output on attempt {attempt + 1}")
            else:
                error_msg = stderr.strip() if stderr.strip() else f"Exit code {returncode}"
                logger.warning(
                    f"[analyst] Execution failed on attempt {attempt + 1}: {error_msg[:200]}"
                )

            # Retry if attempts remain
            if attempt < self.max_retries:
                logger.info(f"[analyst] Retrying ({attempt + 2}/{1 + self.max_retries})...")
                code = await self._generate_code(query, error_context=error_msg, previous_code=code)
                if not code:
                    return self._format_error(query, "Failed to generate fixed code after error.")
                self._last_code = code

        return self._format_error(
            query, f"All {1 + self.max_retries} attempts failed. Last error: {error_msg}"
        )

    async def _generate_code(
        self,
        query: str,
        error_context: str | None = None,
        previous_code: str | None = None,
    ) -> str | None:
        """
        Call LLM to generate Python code for the query.

        Also extracts any prose analysis surrounding the code block and stores
        it in self._last_prose for inclusion in the final output.

        Args:
            query: The analysis query.
            error_context: If retrying, the error from the previous attempt.
            previous_code: If retrying, the code that failed.

        Returns:
            Extracted Python code string, or None if no code block found.
        """
        if error_context and previous_code:
            prompt = ANALYST_RETRY_PROMPT.format(
                query=query, code=previous_code, stderr=error_context
            )
        else:
            prompt = ANALYST_CODE_PROMPT.format(query=query)

        response = await self.llm.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.2,
        )
        self.total_cost += response.cost
        self._last_raw_response = response.content

        code = self._extract_code_block(response.content)
        if code:
            self._last_prose = self._extract_prose(response.content)
        return code

    async def _execute_code(self, code: str) -> tuple[str, str, int]:
        """
        Execute Python code in a subprocess.

        Args:
            code: Python source code to execute.

        Returns:
            Tuple of (stdout, stderr, returncode).
        """
        tmpfile = None
        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, prefix="analyst_"
            ) as f:
                f.write(code)
                tmpfile = f.name

            # Execute in subprocess
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                tmpfile,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ},  # Inherit env (for API keys like FRED_API_KEY)
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )

            return (
                stdout_bytes.decode("utf-8", errors="replace"),
                stderr_bytes.decode("utf-8", errors="replace"),
                proc.returncode,
            )

        except TimeoutError:
            logger.warning(f"[analyst] Code execution timed out after {self.timeout}s")
            if proc:
                proc.kill()
                await proc.wait()
            return ("", f"Execution timed out after {self.timeout} seconds", -1)

        except Exception as e:
            logger.error(f"[analyst] Subprocess error: {e}")
            return ("", f"Failed to execute code: {e}", -1)

        finally:
            if tmpfile and os.path.exists(tmpfile):
                os.unlink(tmpfile)

    @staticmethod
    def _extract_code_block(response: str) -> str | None:
        """
        Extract the first ```python code block from an LLM response.

        Handles multiple cases:
        1. Normal fenced block: ```python ... ```
        2. Truncated block (no closing fence): ```python ... <end of response>
        3. Generic fenced block: ``` ... ```
        4. Raw Python without any fences (starts with import/from/#/etc.)

        Returns None if no code block is found.
        """
        # Case 1: normal fenced python block
        match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Case 2: truncated python block (opening fence but no closing fence)
        match = re.search(r"```python\s*\n(.+)", response, re.DOTALL)
        if match:
            logger.info("[analyst] Found truncated code block (no closing fence)")
            return match.group(1).strip()

        # Case 3: generic fenced block
        match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Case 4: truncated generic block
        match = re.search(r"```\s*\n(.+)", response, re.DOTALL)
        if match:
            logger.info("[analyst] Found truncated code block (no closing fence)")
            return match.group(1).strip()

        # Case 5: raw Python without fence markers
        # (some models, especially reasoning models, may omit the fences)
        stripped = response.strip()
        if stripped and re.match(r"^(import |from |#|def |class |if |for |while |try:)", stripped):
            logger.info("[analyst] No code fences found, treating response as raw Python")
            return stripped

        return None

    @staticmethod
    def _extract_prose(response: str) -> str | None:
        """
        Extract prose analysis from around the code block in an LLM response.

        Returns any text before or after the code block, stripped and joined.
        Returns None if there is no meaningful prose.
        """
        # Remove code block(s) from response
        cleaned = re.sub(r"```(?:python)?\s*\n.*?```", "", response, flags=re.DOTALL)
        # Also handle truncated blocks
        cleaned = re.sub(r"```(?:python)?\s*\n.*$", "", cleaned, flags=re.DOTALL)
        prose = cleaned.strip()
        # Only return if there's meaningful content (not just whitespace or short fragments)
        if prose and len(prose) > 20:
            return prose
        return None

    def _format_result(self, query: str, stdout: str, code: str) -> str:
        """Wrap successful output in XML tags, including any prose analysis."""
        # Truncate long outputs
        if len(stdout) > 10000:
            stdout = stdout[:10000] + "\n... (output truncated)"

        parts = [
            f'<AnalystReport query="{query[:200]}">',
            "Code executed successfully.\n",
            stdout.strip(),
        ]

        if self._last_prose:
            parts.append(f"\nAnalyst notes:\n{self._last_prose}")

        parts.append("</AnalystReport>")
        return "\n".join(parts)

    @staticmethod
    def _format_error(query: str, error: str) -> str:
        """Wrap error in XML tags."""
        return f'<AnalystReport query="{query[:200]}">\nError: {error}\n</AnalystReport>'
