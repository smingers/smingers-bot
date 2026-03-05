"""
Tests for PDF and JSON parsing in the content extractor.

Tests SpreadsheetParser.parse_pdf() and SpreadsheetParser.parse_json(),
plus _fetch_url() routing for application/pdf and application/json content types.
"""

import io
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bot.content_extractor import ConcurrentContentExtractor, SpreadsheetParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf_bytes(pages: list[str]) -> bytes:
    """Create a minimal multi-page PDF in memory using pymupdf."""
    import fitz

    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# SpreadsheetParser.parse_pdf
# ---------------------------------------------------------------------------


class TestParsePdf:
    def test_basic_text_extraction(self):
        data = _make_pdf_bytes(["Hello world from page one."])
        result = SpreadsheetParser.parse_pdf(data)
        assert "Hello world" in result
        assert "[Page 1]" in result

    def test_multipage_with_markers(self):
        data = _make_pdf_bytes(["First page content.", "Second page content."])
        result = SpreadsheetParser.parse_pdf(data)
        assert "[Page 1]" in result
        assert "[Page 2]" in result
        assert "First page" in result
        assert "Second page" in result

    def test_truncation_note_when_over_limit(self):
        pages = [f"Page {i} content here." for i in range(25)]
        data = _make_pdf_bytes(pages)
        result = SpreadsheetParser.parse_pdf(data, max_pages=20)
        assert "[Showing 20 of 25 pages]" in result

    def test_no_truncation_note_when_within_limit(self):
        data = _make_pdf_bytes(["Only page."])
        result = SpreadsheetParser.parse_pdf(data, max_pages=20)
        assert "Showing" not in result

    def test_invalid_bytes_returns_error_message(self):
        result = SpreadsheetParser.parse_pdf(b"not a pdf")
        assert "error" in result.lower() or "parsing" in result.lower()

    def test_pymupdf_unavailable(self):
        with patch("src.bot.content_extractor.HAS_PYMUPDF", False):
            result = SpreadsheetParser.parse_pdf(b"anything")
        assert "unavailable" in result.lower() or "not installed" in result.lower()


# ---------------------------------------------------------------------------
# SpreadsheetParser.parse_json
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_simple_object(self):
        text = json.dumps({"name": "Alice", "age": 30})
        result = SpreadsheetParser.parse_json(text)
        assert "Alice" in result
        assert "age" in result

    def test_simple_array_with_header(self):
        text = json.dumps([1, 2, 3])
        result = SpreadsheetParser.parse_json(text)
        assert "3 items" in result
        assert "1" in result

    def test_large_array_truncated_to_50_items(self):
        text = json.dumps(list(range(100)))
        result = SpreadsheetParser.parse_json(text)
        assert "100 items" in result
        assert "50 more items" in result

    def test_small_array_no_more_items_note(self):
        text = json.dumps([1, 2, 3])
        result = SpreadsheetParser.parse_json(text)
        assert "more items" not in result

    def test_nested_object(self):
        text = json.dumps({"outer": {"inner": "value"}})
        result = SpreadsheetParser.parse_json(text)
        assert "inner" in result
        assert "value" in result

    def test_truncation_at_max_chars(self):
        # Build a large object that will exceed max_chars
        big = {"key_" + str(i): "x" * 100 for i in range(200)}
        text = json.dumps(big)
        result = SpreadsheetParser.parse_json(text, max_chars=1000)
        assert "[truncated]" in result
        assert len(result) <= 1000 + len("\n...[truncated]")

    def test_invalid_json_returns_error_message(self):
        result = SpreadsheetParser.parse_json("not valid json {{{")
        assert "error" in result.lower() or "parsing" in result.lower()

    def test_empty_object(self):
        result = SpreadsheetParser.parse_json("{}")
        assert result.strip() == "{}"

    def test_empty_array(self):
        result = SpreadsheetParser.parse_json("[]")
        assert "0 items" in result

    def test_null_value(self):
        result = SpreadsheetParser.parse_json("null")
        assert "null" in result

    def test_unicode_preserved(self):
        text = json.dumps({"city": "São Paulo"})
        result = SpreadsheetParser.parse_json(text)
        assert "São Paulo" in result


# ---------------------------------------------------------------------------
# ConcurrentContentExtractor._fetch_url — PDF and JSON routing
# ---------------------------------------------------------------------------


class TestFetchUrlPdfJsonDetection:
    def _make_response(self, content_type: str, text: str = "", content: bytes = b"") -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": content_type}
        resp.text = text
        resp.content = content
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.asyncio
    async def test_pdf_content_type_routed_to_pdf_parser(self):
        pdf_bytes = _make_pdf_bytes(["Resolution: the value exceeded 50%."])
        response = self._make_response("application/pdf", content=pdf_bytes)

        extractor = ConcurrentContentExtractor()
        extractor._client = MagicMock()
        extractor._client.get = AsyncMock(return_value=response)

        result = await extractor._fetch_url("https://example.com/report.pdf")

        assert result["method"] == "pdf"
        assert result["success"] is True
        assert "Resolution" in result["content"]

    @pytest.mark.asyncio
    async def test_pdf_url_extension_routed_to_pdf_parser(self):
        pdf_bytes = _make_pdf_bytes(["Some data here."])
        response = self._make_response("application/octet-stream", content=pdf_bytes)

        extractor = ConcurrentContentExtractor()
        extractor._client = MagicMock()
        extractor._client.get = AsyncMock(return_value=response)

        result = await extractor._fetch_url("https://example.com/data.pdf")

        assert result["method"] == "pdf"

    @pytest.mark.asyncio
    async def test_json_content_type_routed_to_json_parser(self):
        payload = {"indicator": "GDP", "value": 25000, "year": 2024}
        response = self._make_response("application/json; charset=utf-8", text=json.dumps(payload))

        extractor = ConcurrentContentExtractor()
        extractor._client = MagicMock()
        extractor._client.get = AsyncMock(return_value=response)

        result = await extractor._fetch_url("https://api.example.com/data")

        assert result["method"] == "json"
        assert result["success"] is True
        assert "GDP" in result["content"]

    @pytest.mark.asyncio
    async def test_json_url_extension_routed_to_json_parser(self):
        payload = [{"id": 1}, {"id": 2}]
        response = self._make_response("application/octet-stream", text=json.dumps(payload))

        extractor = ConcurrentContentExtractor()
        extractor._client = MagicMock()
        extractor._client.get = AsyncMock(return_value=response)

        result = await extractor._fetch_url("https://example.com/export.json")

        assert result["method"] == "json"

    @pytest.mark.asyncio
    async def test_text_json_content_type_routed_to_json_parser(self):
        payload = {"status": "ok"}
        response = self._make_response("text/json", text=json.dumps(payload))

        extractor = ConcurrentContentExtractor()
        extractor._client = MagicMock()
        extractor._client.get = AsyncMock(return_value=response)

        result = await extractor._fetch_url("https://example.com/status")

        assert result["method"] == "json"

    @pytest.mark.asyncio
    async def test_html_not_routed_to_pdf_or_json(self):
        html = "<html><body><article>Some article content here with enough words</article></body></html>"
        response = self._make_response("text/html", text=html)

        extractor = ConcurrentContentExtractor()
        extractor._client = MagicMock()
        extractor._client.get = AsyncMock(return_value=response)

        result = await extractor._fetch_url("https://example.com/article")

        assert result.get("method") not in ("pdf", "json")
