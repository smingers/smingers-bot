"""
Tests for URL extraction from question text fields.

Tests the SearchPipeline.extract_urls_from_question_text() static method which
parses resolution_criteria, fine_print, and description fields to find scrapable URLs.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bot.search import QuestionDetails, SearchPipeline


def _make_question(
    resolution_criteria: str = "",
    fine_print: str = "",
    description: str = "",
) -> QuestionDetails:
    """Helper to create a QuestionDetails with only the text fields we care about."""
    return QuestionDetails(
        title="Test Question",
        resolution_criteria=resolution_criteria,
        fine_print=fine_print,
        description=description,
    )


class TestBareURLExtraction:
    """Tests for extracting bare (non-markdown) URLs."""

    def test_single_bare_url(self):
        q = _make_question(resolution_criteria="Check https://example.com/data for results.")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_multiple_bare_urls(self):
        q = _make_question(
            resolution_criteria="See https://example.com/a and https://example.com/b"
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/a", "https://example.com/b"]

    def test_http_url(self):
        q = _make_question(resolution_criteria="See http://example.com/data for info.")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["http://example.com/data"]

    def test_url_with_query_params(self):
        q = _make_question(resolution_criteria="https://api.example.com/data?key=value&other=123")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://api.example.com/data?key=value&other=123"]


class TestMarkdownLinkExtraction:
    """Tests for extracting URLs from markdown-style [text](url) links."""

    def test_single_markdown_link(self):
        q = _make_question(
            resolution_criteria="See [EIA data](https://www.eia.gov/data/series) for details."
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://www.eia.gov/data/series"]

    def test_multiple_markdown_links(self):
        q = _make_question(
            resolution_criteria=(
                "Based on [Source A](https://a.com/data) and [Source B](https://b.com/data)."
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://a.com/data", "https://b.com/data"]

    def test_markdown_link_url_not_duplicated_as_bare(self):
        """A URL inside a markdown link should not also be extracted as a bare URL."""
        q = _make_question(resolution_criteria="[EIA](https://www.eia.gov/data)")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://www.eia.gov/data"]
        # Should NOT have duplicates
        assert len(urls) == 1


class TestMetaculusURLFiltering:
    """Tests that metaculus.com URLs are filtered out."""

    def test_metaculus_url_filtered(self):
        q = _make_question(
            resolution_criteria="See https://www.metaculus.com/questions/12345 for context."
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == []

    def test_metaculus_without_www_filtered(self):
        q = _make_question(
            resolution_criteria="See https://metaculus.com/questions/12345 for context."
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == []

    def test_metaculus_filtered_but_other_kept(self):
        q = _make_question(
            resolution_criteria=(
                "See https://metaculus.com/questions/12345 "
                "and https://example.com/data for context."
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_metaculus_markdown_link_filtered(self):
        q = _make_question(
            resolution_criteria="See [this question](https://www.metaculus.com/questions/12345)."
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == []


class TestDeduplication:
    """Tests for URL deduplication across fields."""

    def test_same_url_in_two_fields(self):
        q = _make_question(
            resolution_criteria="See https://example.com/data",
            description="Also at https://example.com/data",
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_same_url_in_all_fields(self):
        q = _make_question(
            resolution_criteria="https://example.com/data",
            fine_print="https://example.com/data",
            description="https://example.com/data",
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_markdown_and_bare_same_url_deduped(self):
        q = _make_question(
            resolution_criteria=(
                "[Data](https://example.com/data) available at https://example.com/data"
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]


class TestEscapedUnderscores:
    """Tests for handling escaped underscores (Metaculus markdown rendering)."""

    def test_escaped_underscores_cleaned(self):
        q = _make_question(
            resolution_criteria=(
                "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?"
                "n=pet&s=emm\\_epmr\\_pte\\_nus\\_dpg&f=a"
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert len(urls) == 1
        assert "\\_" not in urls[0]
        assert "emm_epmr_pte_nus_dpg" in urls[0]

    def test_markdown_link_with_escaped_underscores(self):
        q = _make_question(
            resolution_criteria=("[EIA data](https://www.eia.gov/data?series\\_id=test\\_value)")
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert len(urls) == 1
        assert "series_id=test_value" in urls[0]


class TestEmptyFields:
    """Tests for handling empty/None fields."""

    def test_all_empty(self):
        q = _make_question()
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == []

    def test_no_urls_in_text(self):
        q = _make_question(
            resolution_criteria="This question resolves based on official data.",
            fine_print="No special conditions.",
            description="A question about economic data.",
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == []

    def test_only_resolution_criteria(self):
        q = _make_question(resolution_criteria="See https://example.com/data")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_only_fine_print(self):
        q = _make_question(fine_print="See https://example.com/data")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_only_description(self):
        q = _make_question(description="See https://example.com/data")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]


class TestPriorityOrdering:
    """Tests that URLs from resolution_criteria appear before fine_print before description."""

    def test_resolution_criteria_first(self):
        q = _make_question(
            resolution_criteria="https://resolution.example.com/data",
            fine_print="https://fineprint.example.com/data",
            description="https://description.example.com/data",
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == [
            "https://resolution.example.com/data",
            "https://fineprint.example.com/data",
            "https://description.example.com/data",
        ]

    def test_fine_print_before_description(self):
        q = _make_question(
            fine_print="https://fineprint.example.com/data",
            description="https://description.example.com/data",
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == [
            "https://fineprint.example.com/data",
            "https://description.example.com/data",
        ]


class TestTrailingPunctuation:
    """Tests that trailing punctuation is stripped from URLs."""

    def test_trailing_period(self):
        q = _make_question(resolution_criteria="See https://example.com/data.")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_trailing_comma(self):
        q = _make_question(resolution_criteria="Sources: https://example.com/data, and more.")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_trailing_semicolon(self):
        q = _make_question(resolution_criteria="See https://example.com/data;")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]

    def test_trailing_colon(self):
        q = _make_question(resolution_criteria="Source: https://example.com/data:")
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://example.com/data"]


class TestRealWorldURLPatterns:
    """Tests using URL patterns commonly seen in Metaculus questions."""

    def test_eia_url_with_query_params(self):
        """Real EIA URL pattern from Q42037."""
        q = _make_question(
            resolution_criteria=(
                "This question will resolve as the value reported by "
                "[this EIA series](https://www.eia.gov/dnav/pet/hist/"
                "LeafHandler.ashx?n=pet&s=emm_epmr_pte_nus_dpg&f=a)."
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert len(urls) == 1
        assert "eia.gov" in urls[0]
        assert "emm_epmr_pte_nus_dpg" in urls[0]

    def test_fred_url(self):
        """FRED data URL pattern."""
        q = _make_question(
            resolution_criteria=(
                "Based on [FRED CPI data](https://fred.stlouisfed.org/series/CPIAUCSL)."
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert urls == ["https://fred.stlouisfed.org/series/CPIAUCSL"]

    def test_mixed_markdown_and_bare_different_urls(self):
        """Mix of markdown links and bare URLs pointing to different pages."""
        q = _make_question(
            resolution_criteria=(
                "Resolution based on [official report](https://gov.example.com/report). "
                "Also see https://data.example.com/api/v2/values for raw data."
            )
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        assert len(urls) == 2
        assert "https://gov.example.com/report" in urls
        assert "https://data.example.com/api/v2/values" in urls

    def test_urls_across_all_fields(self):
        """URLs appearing in different fields, some overlapping."""
        q = _make_question(
            resolution_criteria="Primary: https://primary.example.com/data",
            fine_print=(
                "See also https://primary.example.com/data and https://secondary.example.com/info"
            ),
            description=(
                "Background: https://background.example.com/context "
                "and https://secondary.example.com/info"
            ),
        )
        urls = SearchPipeline.extract_urls_from_question_text(q)
        # Deduplication: primary appears once (from resolution_criteria),
        # secondary once (from fine_print), background once (from description)
        assert urls == [
            "https://primary.example.com/data",
            "https://secondary.example.com/info",
            "https://background.example.com/context",
        ]
