"""
Generates IDML Story XML content from a Document model.

Produces a valid idPkg:Story XML element containing ParagraphStyleRange and
CharacterStyleRange elements for each paragraph and run in the document.
Footnotes are emitted as simplified <Note> elements after the last run in a
paragraph.
"""

from lxml import etree

from src.models.content import Document, Paragraph, Run, Footnote


# XML namespace used by IDML packaging
IDPKG_NS = "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"
IDPKG_PREFIX = "idPkg"

NO_CHAR_STYLE = "CharacterStyle/$ID/[No character style]"


def _char_style_value(style: str | None) -> str:
    """Return the full AppliedCharacterStyle attribute value for a run."""
    if style is None:
        return NO_CHAR_STYLE
    return f"CharacterStyle/{style}"


def _para_style_value(style: str) -> str:
    """Return the full AppliedParagraphStyle attribute value for a paragraph."""
    return f"ParagraphStyle/{style}"


def _build_character_style_range(parent: etree._Element, run: Run) -> None:
    """Append a CharacterStyleRange element with a Content child to *parent*."""
    csr = etree.SubElement(
        parent,
        "CharacterStyleRange",
        AppliedCharacterStyle=_char_style_value(run.style),
    )
    content = etree.SubElement(csr, "Content")
    content.text = run.text


def _build_note(parent: etree._Element, footnote: Footnote) -> None:
    """
    Append a simplified <Note> element representing a footnote to *parent*.

    This is a simplification — real InDesign footnotes use a dedicated
    <Footnote> structure inside the CharacterStyleRange.  For MVP purposes the
    footnote text is preserved here so it is not silently dropped.
    """
    note = etree.SubElement(parent, "Note")
    for run in footnote.runs:
        _build_character_style_range(note, run)


def _build_paragraph_style_range(
    story: etree._Element, paragraph: Paragraph
) -> None:
    """Append a ParagraphStyleRange (with its children) to *story*."""
    psr = etree.SubElement(
        story,
        "ParagraphStyleRange",
        AppliedParagraphStyle=_para_style_value(paragraph.style),
    )

    # Emit all text runs
    for run in paragraph.runs:
        _build_character_style_range(psr, run)

    # Emit footnotes as simplified Note elements after the last run
    for footnote in paragraph.footnotes:
        _build_note(psr, footnote)

    # Paragraph break — required by IDML so InDesign knows where each
    # paragraph ends and can apply the correct ParagraphStyle to each one.
    # Without <Br/>, InDesign treats the entire story as a single paragraph.
    br_csr = etree.SubElement(
        psr,
        "CharacterStyleRange",
        AppliedCharacterStyle=NO_CHAR_STYLE,
    )
    etree.SubElement(br_csr, "Br")


class StoryWriter:
    """Converts a Document into IDML Story XML bytes."""

    def write(self, doc: Document, story_id: str) -> bytes:
        """
        Build and serialise an IDML Story XML document.

        Parameters
        ----------
        doc:
            The fully style-mapped document to serialise.
        story_id:
            The value used for the Story element's ``Self`` attribute (e.g.
            ``"uf1b"``).  This must match the story's filename stem and the
            reference in ``designmap.xml``.

        Returns
        -------
        bytes
            UTF-8 encoded XML with an XML declaration.
        """
        # Root element: <idPkg:Story …>
        nsmap = {IDPKG_PREFIX: IDPKG_NS}
        root = etree.Element(
            f"{{{IDPKG_NS}}}Story",
            nsmap=nsmap,
            DOMVersion="16.0",
        )

        # <Story Self="…">
        story = etree.SubElement(root, "Story", Self=story_id)

        for paragraph in doc.paragraphs:
            _build_paragraph_style_range(story, paragraph)

        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
            pretty_print=True,
        )
