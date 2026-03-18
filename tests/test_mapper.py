"""Tests for src/mapper/style_mapper.StyleMapper.

Document objects are constructed directly in code — no .docx fixture files
are needed for these tests.
"""

from __future__ import annotations

import copy
import sys

import pytest

from src.mapper.style_mapper import StyleMapper
from src.models.content import Document, Footnote, Paragraph, Run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(
    para_style: str = "Normal",
    runs: list[tuple[str, str | None]] | None = None,
) -> Document:
    """Build a minimal one-paragraph Document for testing."""
    if runs is None:
        runs = [("Hello", None)]
    return Document(
        paragraphs=[
            Paragraph(
                runs=[Run(text=t, style=s) for t, s in runs],
                style=para_style,
                footnotes=[],
            )
        ]
    )


# ---------------------------------------------------------------------------
# Paragraph style mapping
# ---------------------------------------------------------------------------

class TestParagraphStyleMapping:
    def test_heading1_maps_to_chapter_title(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Heading 1")
        result = mapper.map_document(doc)
        assert result.paragraphs[0].style == "Chapter Title"

    def test_normal_maps_to_body_text(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Normal")
        result = mapper.map_document(doc)
        assert result.paragraphs[0].style == "Body Text"

    def test_heading2_maps_to_section_head(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Heading 2")
        result = mapper.map_document(doc)
        assert result.paragraphs[0].style == "Section Head"

    def test_body_text_maps_to_body_text(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Body Text")
        result = mapper.map_document(doc)
        assert result.paragraphs[0].style == "Body Text"

    def test_unknown_para_style_falls_back(self, style_map_path, capsys):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="UnknownStyle")
        result = mapper.map_document(doc)
        assert result.paragraphs[0].style == "Body Text"

    def test_unknown_para_style_warns_stderr(self, style_map_path, capsys):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="UnknownStyle")
        mapper.map_document(doc)
        captured = capsys.readouterr()
        assert "UnknownStyle" in captured.err
        assert "Warning" in captured.err


# ---------------------------------------------------------------------------
# Character style mapping
# ---------------------------------------------------------------------------

class TestCharacterStyleMapping:
    def test_strong_maps_to_bold(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", "Strong")])
        result = mapper.map_document(doc)
        assert result.paragraphs[0].runs[0].style == "Bold"

    def test_emphasis_maps_to_italic(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", "Emphasis")])
        result = mapper.map_document(doc)
        assert result.paragraphs[0].runs[0].style == "Italic"

    def test_none_style_stays_none(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", None)])
        result = mapper.map_document(doc)
        assert result.paragraphs[0].runs[0].style is None

    def test_none_style_no_warning(self, style_map_path, capsys):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", None)])
        mapper.map_document(doc)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_unknown_char_style_maps_to_none(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", "NonExistentCharStyle")])
        result = mapper.map_document(doc)
        assert result.paragraphs[0].runs[0].style is None

    def test_unknown_char_style_warns_stderr(self, style_map_path, capsys):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", "NonExistentCharStyle")])
        mapper.map_document(doc)
        captured = capsys.readouterr()
        assert "NonExistentCharStyle" in captured.err
        assert "Warning" in captured.err


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_config_raises_file_not_found(self, tmp_path):
        missing = str(tmp_path / "no_such_config.json")
        with pytest.raises(FileNotFoundError):
            StyleMapper(missing)


# ---------------------------------------------------------------------------
# Immutability: map_document must not mutate the input Document
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_map_document_does_not_mutate_input(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Heading 1", runs=[("text", "Strong")])

        # Record originals
        original_para_style = doc.paragraphs[0].style
        original_run_style = doc.paragraphs[0].runs[0].style

        mapper.map_document(doc)

        assert doc.paragraphs[0].style == original_para_style
        assert doc.paragraphs[0].runs[0].style == original_run_style

    def test_map_document_returns_new_document(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Normal")
        result = mapper.map_document(doc)
        assert result is not doc

    def test_map_document_paragraphs_are_new_objects(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(para_style="Normal")
        result = mapper.map_document(doc)
        assert result.paragraphs[0] is not doc.paragraphs[0]

    def test_map_document_runs_are_new_objects(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        doc = _make_doc(runs=[("text", "Strong")])
        result = mapper.map_document(doc)
        assert result.paragraphs[0].runs[0] is not doc.paragraphs[0].runs[0]

    def test_footnotes_mapped_without_mutating_input(self, style_map_path):
        mapper = StyleMapper(style_map_path)
        footnote = Footnote(ref_index=1, runs=[Run(text="note", style="Strong")])
        doc = Document(
            paragraphs=[
                Paragraph(
                    runs=[Run(text="body", style=None)],
                    style="Normal",
                    footnotes=[footnote],
                )
            ]
        )
        original_fn_style = doc.paragraphs[0].footnotes[0].runs[0].style
        result = mapper.map_document(doc)
        # Input unchanged
        assert doc.paragraphs[0].footnotes[0].runs[0].style == original_fn_style
        # Output mapped
        assert result.paragraphs[0].footnotes[0].runs[0].style == "Bold"
