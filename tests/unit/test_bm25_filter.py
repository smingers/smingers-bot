"""Tests for BM25 content filtering in search.py."""

from src.bot.search import _bm25_filter_content


class TestBM25FilterPassthrough:
    """Content under max_chars should be returned unchanged."""

    def test_short_content_unchanged(self):
        content = "This is a short article about climate change."
        result = _bm25_filter_content(content, "climate change")
        assert result == content

    def test_empty_content(self):
        result = _bm25_filter_content("", "any query")
        assert result == ""

    def test_exact_limit_unchanged(self):
        content = "x" * 8000
        result = _bm25_filter_content(content, "query", max_chars=8000)
        assert result == content


class TestBM25FilterRelevanceSelection:
    """BM25 should select relevant chunks over irrelevant ones."""

    def test_relevant_paragraph_buried_deep(self):
        """Key test: relevant data past the 8000-char truncation point gets selected."""
        # Build content where the relevant paragraph is buried deep
        irrelevant = (
            "The weather today is sunny with clear skies in California. "
            "Temperatures are expected to reach 75 degrees Fahrenheit.\n\n"
        ) * 200
        relevant = (
            "The English Wikipedia article count reached 7,145,000 articles "
            "in February 2026, according to the Special:Statistics page."
        )
        content = irrelevant + relevant

        assert len(content) > 8000  # Confirm it would be truncated

        result = _bm25_filter_content(
            content,
            "Will the English Wikipedia have at least 7,145,000 articles?",
            max_chars=8000,
        )

        # The relevant paragraph should be in the result
        assert "7,145,000" in result
        assert "Wikipedia" in result

    def test_mixed_relevance_selects_best(self):
        """Among mixed content, the most relevant chunks should be selected."""
        chunks = [
            "The stock market closed higher today with gains across all sectors "
            "and investors saw major returns in technology companies.",
            "Hungary held parliamentary elections on April 12, 2026 with record turnout.",
            "The Fidesz party won 89 seats in the 199-seat parliament after a close race.",
            "New restaurant openings in downtown Manhattan drew large crowds "
            "with celebrity chefs offering diverse international cuisine.",
            "Opposition party Tisza secured 99 seats, denying any supermajority "
            "in the Hungarian parliament for the first time since 2010.",
        ]
        content = "\n\n".join(chunks)

        # Use a budget that can hold ~2-3 chunks but not all 5
        result = _bm25_filter_content(
            content,
            "Will any party acquire a supermajority in Hungarian parliamentary elections?",
            max_chars=250,
        )

        # Should prioritize the Hungarian election chunks
        assert "Fidesz" in result or "supermajority" in result or "Tisza" in result

    def test_all_content_relevant(self):
        """When all content is relevant, should select within budget."""
        chunks = [
            f"Wikipedia article count data point {i}: the count is {7_100_000 + i * 100} articles."
            for i in range(50)
        ]
        content = "\n\n".join(chunks)

        assert len(content) > 1000

        result = _bm25_filter_content(
            content,
            "Wikipedia article count",
            max_chars=1000,
        )

        assert len(result) <= 1000
        assert "Wikipedia" in result


class TestBM25FilterDocumentOrder:
    """Selected chunks should maintain original document order."""

    def test_preserves_document_order(self):
        chunks = [
            "First relevant: Wikipedia has over 7 million articles in English.",
            "Irrelevant filler about cooking recipes and kitchen gadgets for home chefs.",
            "Second relevant: The article count grows by 500 articles per day on average.",
            "More irrelevant content about sports scores and entertainment news updates.",
            "Third relevant: Special:Statistics shows the current Wikipedia count.",
        ]
        content = "\n\n".join(chunks)

        result = _bm25_filter_content(
            content,
            "Wikipedia article count statistics",
            max_chars=400,
        )

        # If multiple relevant chunks are selected, they should be in order
        parts = result.split("\n\n")
        if len(parts) > 1:
            first_idx = next((i for i, p in enumerate(parts) if "First" in p), None)
            second_idx = next((i for i, p in enumerate(parts) if "Second" in p), None)
            third_idx = next((i for i, p in enumerate(parts) if "Third" in p), None)

            indices = [x for x in [first_idx, second_idx, third_idx] if x is not None]
            assert indices == sorted(indices), "Chunks should be in document order"


class TestBM25FilterFallback:
    """BM25 should fall back to simple truncation in edge cases."""

    def test_no_token_overlap_falls_back(self):
        """Query with zero overlap should fall back to truncation."""
        content = "alpha beta gamma delta epsilon.\n\n" * 300
        assert len(content) > 8000

        result = _bm25_filter_content(
            content,
            "xylophone zebra quantum",
            max_chars=8000,
        )

        # Should return content within budget
        assert len(result) <= 8000
        # Should contain the beginning of the content (fallback behavior)
        assert result.startswith("alpha beta gamma")

    def test_empty_query(self):
        content = "Some content here.\n\nMore content." * 500
        result = _bm25_filter_content(content, "", max_chars=8000)
        assert len(result) <= 8000


class TestBM25FilterChunking:
    """Chunking behavior tests."""

    def test_paragraph_splitting(self):
        """Content should be split on double newlines."""
        p1 = "First paragraph discussing topic A in some detail with extra words."
        p2 = "Second paragraph about topic B with more specific information here."
        p3 = "Third paragraph covering topic C and other unrelated matters entirely."
        content = f"{p1}\n\n{p2}\n\n{p3}"

        # With a budget that fits only one chunk, should pick the most relevant
        result = _bm25_filter_content(content, "topic B specific information", max_chars=80)
        assert "topic B" in result

    def test_large_chunk_subsplit(self):
        """Chunks over 1000 chars should be sub-split on single newlines."""
        lines = [f"Line {i} about various unrelated topics." for i in range(50)]
        # Add one relevant line buried in the middle
        lines[25] = "The Wikipedia article count is 7,145,000 as of February 2026."
        large_chunk = "\n".join(lines)

        assert len(large_chunk) > 1000
        assert "\n\n" not in large_chunk  # It's one big chunk

        result = _bm25_filter_content(
            large_chunk,
            "Wikipedia article count",
            max_chars=500,
        )

        assert "7,145,000" in result

    def test_whitespace_only_chunks_ignored(self):
        """Chunks that are only whitespace should be skipped."""
        content = "Real content here.\n\n   \n\n\n\n   \n\nMore real content."
        result = _bm25_filter_content(content, "real content", max_chars=100)
        assert "Real content" in result or "More real" in result


class TestBM25FilterCharBudget:
    """Output should respect the character budget."""

    def test_respects_max_chars(self):
        chunks = [f"Paragraph {i} with enough words to matter here." for i in range(100)]
        content = "\n\n".join(chunks)

        result = _bm25_filter_content(content, "paragraph words", max_chars=500)
        assert len(result) <= 500

    def test_custom_max_chars(self):
        chunks = [f"Data point {i} about economics." for i in range(100)]
        content = "\n\n".join(chunks)

        result = _bm25_filter_content(content, "economics data", max_chars=15000)
        assert len(result) <= 15000

    def test_selects_small_relevant_chunk_over_large_irrelevant(self):
        """Should pick a small relevant chunk over a large irrelevant one."""
        # Large irrelevant chunk followed by small relevant one
        large_irrelevant = "Weather forecast: " + "sunny and warm. " * 600
        small_relevant = "Wikipedia now has 7,145,000 articles as of February 2026."
        content = f"{large_irrelevant}\n\n{small_relevant}"

        assert len(content) > 8000

        result = _bm25_filter_content(content, "Wikipedia articles", max_chars=8000)
        assert "Wikipedia" in result
