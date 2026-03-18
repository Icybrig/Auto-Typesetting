"""
Mapper for converting Word style names to InDesign style names.

Takes a Document with Word-native style names and returns a new Document
with InDesign style names applied. Never mutates the input Document.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.models.content import Document, Footnote, Paragraph, Run


class StyleMapper:
    """Maps Word style names to InDesign style names using a configuration file."""

    def __init__(self, config_path: str):
        """
        Initialize the StyleMapper by loading a style_map.json configuration file.

        Args:
            config_path: Path to the style_map.json configuration file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            json.JSONDecodeError: If the config file is malformed JSON.
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Style map configuration file not found: {config_path}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as exc:
            raise json.JSONDecodeError(
                f"Malformed JSON in {config_path}: {exc.msg}",
                exc.doc,
                exc.pos,
            ) from exc

        # Load the three required keys from the config
        self.paragraph_styles: dict[str, str] = config.get("paragraph_styles", {})
        self.character_styles: dict[str, str] = config.get("character_styles", {})
        self.fallback_paragraph_style: str = config.get("fallback_paragraph_style", "Body Text")

    def map_document(self, doc: Document) -> Document:
        """
        Map a Document from Word style names to InDesign style names.

        Returns a NEW Document with mapped style names. Does not mutate the input.

        Args:
            doc: A Document with Word-native style names.

        Returns:
            A new Document with InDesign style names applied.
        """
        mapped_paragraphs: list[Paragraph] = []

        for paragraph in doc.paragraphs:
            # Map paragraph style
            mapped_para_style = self._map_paragraph_style(paragraph.style)

            # Map runs within the paragraph
            mapped_runs: list[Run] = []
            for run in paragraph.runs:
                mapped_char_style = self._map_character_style(run.style)
                mapped_runs.append(Run(text=run.text, style=mapped_char_style))

            # Map footnotes within the paragraph
            mapped_footnotes: list[Footnote] = []
            for footnote in paragraph.footnotes:
                mapped_footnote_runs: list[Run] = []
                for fn_run in footnote.runs:
                    mapped_fn_char_style = self._map_character_style(fn_run.style)
                    mapped_footnote_runs.append(Run(text=fn_run.text, style=mapped_fn_char_style))
                mapped_footnotes.append(
                    Footnote(ref_index=footnote.ref_index, runs=mapped_footnote_runs)
                )

            mapped_paragraphs.append(
                Paragraph(runs=mapped_runs, style=mapped_para_style, footnotes=mapped_footnotes)
            )

        return Document(paragraphs=mapped_paragraphs)

    def _map_paragraph_style(self, word_style: str) -> str:
        """
        Map a Word paragraph style name to an InDesign paragraph style name.

        If the Word style is not found in the mapping, warns to stderr and
        returns the fallback paragraph style.

        Args:
            word_style: The Word paragraph style name.

        Returns:
            The mapped InDesign paragraph style name.
        """
        if word_style in self.paragraph_styles:
            return self.paragraph_styles[word_style]

        # Unmapped style — warn and use fallback
        print(
            f"Warning: Unmapped paragraph style '{word_style}', "
            f"falling back to '{self.fallback_paragraph_style}'",
            file=sys.stderr,
        )
        return self.fallback_paragraph_style

    def _map_character_style(self, word_style: str | None) -> str | None:
        """
        Map a Word character style name to an InDesign character style name.

        If the Word style is not found in the mapping, warns to stderr and
        returns None (no character style applied).

        Args:
            word_style: The Word character style name, or None.

        Returns:
            The mapped InDesign character style name, or None if unmapped or
            if the input was None.
        """
        if word_style is None:
            return None

        if word_style in self.character_styles:
            return self.character_styles[word_style]

        # Unmapped character style — warn and return None
        print(
            f"Warning: Unmapped character style '{word_style}', setting to None",
            file=sys.stderr,
        )
        return None
