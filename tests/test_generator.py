"""Tests for src/generator/story_writer.StoryWriter and
src/generator/idml_builder.IDMLBuilder.

The .indt template fixture is a minimal ZIP created by conftest.py.
"""

from __future__ import annotations

import zipfile

import pytest
from lxml import etree

from src.generator.idml_builder import IDMLBuilder
from src.generator.story_writer import StoryWriter
from src.models.content import Document, Paragraph, Run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IDPKG_NS = "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"


def _make_doc(
    paragraphs: list[tuple[str, str, str | None]] | None = None,
) -> Document:
    """Build a Document from a list of (text, para_style, char_style) tuples."""
    if paragraphs is None:
        paragraphs = [("Hello InDesign", "Body Text", None)]
    return Document(
        paragraphs=[
            Paragraph(
                runs=[Run(text=text, style=char_style)],
                style=para_style,
                footnotes=[],
            )
            for text, para_style, char_style in paragraphs
        ]
    )


# ---------------------------------------------------------------------------
# StoryWriter.write()
# ---------------------------------------------------------------------------

class TestStoryWriter:
    def test_returns_bytes(self):
        writer = StoryWriter()
        result = writer.write(_make_doc(), story_id="s1")
        assert isinstance(result, bytes)

    def test_valid_xml(self):
        writer = StoryWriter()
        result = writer.write(_make_doc(), story_id="s1")
        # Should not raise
        root = etree.fromstring(result)
        assert root is not None

    def test_root_element_is_idpkg_story(self):
        writer = StoryWriter()
        result = writer.write(_make_doc(), story_id="s1")
        root = etree.fromstring(result)
        assert root.tag == f"{{{IDPKG_NS}}}Story"

    def test_story_self_attribute(self):
        writer = StoryWriter()
        result = writer.write(_make_doc(), story_id="myid")
        root = etree.fromstring(result)
        story_elem = root.find("Story")
        assert story_elem is not None
        assert story_elem.get("Self") == "myid"

    def test_paragraph_style_range_present(self):
        writer = StoryWriter()
        doc = _make_doc([("text", "Chapter Title", None)])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        psrs = root.findall(".//ParagraphStyleRange")
        assert len(psrs) == 1

    def test_paragraph_style_attribute(self):
        writer = StoryWriter()
        doc = _make_doc([("text", "Chapter Title", None)])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        psr = root.find(".//ParagraphStyleRange")
        assert psr.get("AppliedParagraphStyle") == "ParagraphStyle/Chapter Title"

    def test_character_style_range_present(self):
        writer = StoryWriter()
        doc = _make_doc([("text", "Body Text", None)])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        csrs = root.findall(".//CharacterStyleRange")
        assert len(csrs) == 1

    def test_no_char_style_uses_no_character_style(self):
        writer = StoryWriter()
        doc = _make_doc([("text", "Body Text", None)])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        csr = root.find(".//CharacterStyleRange")
        assert csr.get("AppliedCharacterStyle") == \
            "CharacterStyle/$ID/[No character style]"

    def test_named_char_style_in_attribute(self):
        writer = StoryWriter()
        doc = _make_doc([("text", "Body Text", "Bold")])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        csr = root.find(".//CharacterStyleRange")
        assert csr.get("AppliedCharacterStyle") == "CharacterStyle/Bold"

    def test_content_text(self):
        writer = StoryWriter()
        doc = _make_doc([("Hello InDesign", "Body Text", None)])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        content = root.find(".//Content")
        assert content is not None
        assert content.text == "Hello InDesign"

    def test_xml_declaration_present(self):
        writer = StoryWriter()
        result = writer.write(_make_doc(), story_id="s1")
        assert result.startswith(b"<?xml")

    def test_utf8_encoding(self):
        writer = StoryWriter()
        result = writer.write(_make_doc(), story_id="s1")
        # Should decode cleanly as UTF-8
        result.decode("utf-8")

    def test_multiple_paragraphs(self):
        writer = StoryWriter()
        doc = _make_doc([
            ("Para one", "Chapter Title", None),
            ("Para two", "Body Text", None),
        ])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        psrs = root.findall(".//ParagraphStyleRange")
        assert len(psrs) == 2

    def test_empty_document(self):
        writer = StoryWriter()
        doc = Document(paragraphs=[])
        result = writer.write(doc, story_id="s1")
        root = etree.fromstring(result)
        psrs = root.findall(".//ParagraphStyleRange")
        assert psrs == []


# ---------------------------------------------------------------------------
# IDMLBuilder.build()
# ---------------------------------------------------------------------------

class TestIDMLBuilder:
    def test_build_creates_file(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        out = str(tmp_path / "out.idml")
        builder.build(_make_doc(), out)
        assert (tmp_path / "out.idml").exists()

    def test_output_is_valid_zip(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        out = str(tmp_path / "out.idml")
        builder.build(_make_doc(), out)
        assert zipfile.is_zipfile(out)

    def test_output_contains_stories_directory(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        out = str(tmp_path / "out.idml")
        builder.build(_make_doc(), out)
        with zipfile.ZipFile(out, "r") as zf:
            names = zf.namelist()
        story_entries = [n for n in names if n.startswith("Stories/")]
        assert len(story_entries) > 0

    def test_output_contains_story_xml(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        out = str(tmp_path / "out.idml")
        builder.build(_make_doc(), out)
        with zipfile.ZipFile(out, "r") as zf:
            names = zf.namelist()
        assert "Stories/Story_test.xml" in names

    def test_output_story_has_paragraph_style(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        doc = _make_doc([("text", "Chapter Title", None)])
        out = str(tmp_path / "out.idml")
        builder.build(doc, out)
        with zipfile.ZipFile(out, "r") as zf:
            story_bytes = zf.read("Stories/Story_test.xml")
        root = etree.fromstring(story_bytes)
        psr = root.find(".//ParagraphStyleRange")
        assert psr is not None
        assert psr.get("AppliedParagraphStyle") == "ParagraphStyle/Chapter Title"

    def test_output_contains_designmap(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        out = str(tmp_path / "out.idml")
        builder.build(_make_doc(), out)
        with zipfile.ZipFile(out, "r") as zf:
            names = zf.namelist()
        assert "designmap.xml" in names

    def test_zip_integrity(self, indt_template, tmp_path):
        builder = IDMLBuilder(str(indt_template))
        out = str(tmp_path / "out.idml")
        builder.build(_make_doc(), out)
        with zipfile.ZipFile(out, "r") as zf:
            bad = zf.testzip()
        assert bad is None

    def test_missing_template_raises_file_not_found(self, tmp_path):
        missing = str(tmp_path / "no_template.indt")
        with pytest.raises(FileNotFoundError):
            IDMLBuilder(missing)

    def test_non_zip_template_raises_value_error(self, not_a_zip):
        builder = IDMLBuilder(str(not_a_zip))
        # ValueError is raised at build-time when we try to open the ZIP
        with pytest.raises(ValueError, match="not a valid ZIP"):
            builder.build(_make_doc(), str(not_a_zip.parent / "out.idml"))
