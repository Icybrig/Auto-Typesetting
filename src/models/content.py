"""
Data models representing parsed and style-mapped document content.

These models represent the document structure AFTER style mapping
(InDesign style names are already applied).
"""

from dataclasses import dataclass


@dataclass
class Run:
    """A run of text with optional character styling."""

    text: str
    style: str | None  # InDesign character style name (post-mapping), None for plain text


@dataclass
class Footnote:
    """A footnote reference with its content."""

    ref_index: int  # Position/index of the footnote reference
    runs: list[Run]  # Content of the footnote


@dataclass
class Paragraph:
    """A paragraph with runs, style, and associated footnotes."""

    runs: list[Run]  # Text runs within this paragraph
    style: str  # InDesign paragraph style name (post-mapping)
    footnotes: list[Footnote]  # Footnotes referenced within this paragraph


@dataclass
class Document:
    """A complete document structure."""

    paragraphs: list[Paragraph]  # All paragraphs in the document
