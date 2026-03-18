"""Tests for src/parser/docx_parser.parse().

All tests use real .docx fixture files created by conftest.py — no mocking.
"""

from __future__ import annotations

import pytest

from src.parser.docx_parser import parse


class TestHeadings:
    """Paragraph style names are preserved verbatim from the Word file."""

    def test_heading1_style(self, docx_headings):
        doc = parse(str(docx_headings))
        styles = [p.style for p in doc.paragraphs]
        assert "Heading 1" in styles

    def test_heading2_style(self, docx_headings):
        doc = parse(str(docx_headings))
        styles = [p.style for p in doc.paragraphs]
        assert "Heading 2" in styles

    def test_heading_paragraph_count(self, docx_headings):
        doc = parse(str(docx_headings))
        # Fixture creates exactly 2 paragraphs (Heading 1 + Heading 2)
        assert len(doc.paragraphs) == 2

    def test_heading1_text(self, docx_headings):
        doc = parse(str(docx_headings))
        h1 = next(p for p in doc.paragraphs if p.style == "Heading 1")
        text = "".join(r.text for r in h1.runs)
        assert text == "Chapter One"

    def test_heading2_text(self, docx_headings):
        doc = parse(str(docx_headings))
        h2 = next(p for p in doc.paragraphs if p.style == "Heading 2")
        text = "".join(r.text for r in h2.runs)
        assert text == "Section One"


class TestBodyText:
    """Normal-style paragraphs are parsed with correct style name."""

    def test_normal_style_name(self, docx_normal):
        doc = parse(str(docx_normal))
        for para in doc.paragraphs:
            assert para.style == "Normal"

    def test_paragraph_count(self, docx_normal):
        doc = parse(str(docx_normal))
        assert len(doc.paragraphs) == 2

    def test_paragraph_text(self, docx_normal):
        doc = parse(str(docx_normal))
        texts = ["".join(r.text for r in p.runs) for p in doc.paragraphs]
        assert "First paragraph." in texts
        assert "Second paragraph." in texts


class TestRuns:
    """Multiple runs within a single paragraph are captured correctly."""

    def test_single_paragraph_returned(self, docx_runs):
        doc = parse(str(docx_runs))
        assert len(doc.paragraphs) == 1

    def test_two_runs(self, docx_runs):
        doc = parse(str(docx_runs))
        para = doc.paragraphs[0]
        assert len(para.runs) == 2

    def test_run_texts(self, docx_runs):
        doc = parse(str(docx_runs))
        para = doc.paragraphs[0]
        texts = [r.text for r in para.runs]
        assert texts == ["Hello ", "World"]

    def test_run_styles_are_none_for_no_named_style(self, docx_runs):
        """Runs using only direct formatting (bold=True) have style=None."""
        doc = parse(str(docx_runs))
        para = doc.paragraphs[0]
        # Both runs were given no named character style; the fixture uses
        # run.bold which is direct formatting, not a named character style.
        for run in para.runs:
            assert run.style is None


class TestEmptyParagraph:
    """A paragraph with no text produces a Paragraph with an empty runs list."""

    def test_empty_paragraph_parsed(self, docx_empty_paragraph):
        doc = parse(str(docx_empty_paragraph))
        assert len(doc.paragraphs) == 1

    def test_empty_paragraph_has_no_runs(self, docx_empty_paragraph):
        doc = parse(str(docx_empty_paragraph))
        para = doc.paragraphs[0]
        assert para.runs == []

    def test_empty_paragraph_style(self, docx_empty_paragraph):
        doc = parse(str(docx_empty_paragraph))
        assert doc.paragraphs[0].style == "Normal"

    def test_empty_paragraph_no_footnotes(self, docx_empty_paragraph):
        doc = parse(str(docx_empty_paragraph))
        assert doc.paragraphs[0].footnotes == []


class TestFileNotFound:
    """parse() raises FileNotFoundError for a non-existent path."""

    def test_missing_file_raises(self, tmp_path):
        missing = str(tmp_path / "does_not_exist.docx")
        with pytest.raises(FileNotFoundError):
            parse(missing)
