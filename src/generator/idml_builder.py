"""
Coordinates the assembly of an IDML output file.

Workflow:
1. Open the designer-supplied .indt template as a ZIP archive.
2. Parse designmap.xml to find the filename of the main text-flow story.
3. Use StoryWriter to generate replacement Story XML from the Document.
4. Write a new .idml ZIP: copy every entry from the template unchanged,
   except replace the main story file with the freshly generated XML.
5. Validate the output ZIP and print a summary to stdout.
"""

import zipfile
import io
import re

from lxml import etree

from src.models.content import Document
from src.generator.story_writer import StoryWriter


# Namespace used in designmap.xml story references
IDPKG_NS = "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"

# Fallback story filename when the template contains no stories
_FALLBACK_STORY_NAME = "Stories/Story_main.xml"
_FALLBACK_STORY_ID = "main"


def _parse_main_story(designmap_bytes: bytes) -> tuple[str, str]:
    """
    Return (story_path, story_id) for the first story listed in designmap.xml.

    *story_path* is the ZIP-internal path, e.g. ``"Stories/Story_uf1b.xml"``.
    *story_id*  is derived from the filename stem, e.g. ``"uf1b"``.

    If no story is found the fallback constants are returned.
    """
    try:
        root = etree.fromstring(designmap_bytes)
    except etree.XMLSyntaxError:
        return _FALLBACK_STORY_NAME, _FALLBACK_STORY_ID

    # Look for the first <idPkg:Story src="Stories/Story_xxx.xml"/>
    tag = f"{{{IDPKG_NS}}}Story"
    for element in root.iter(tag):
        src = element.get("src", "")
        if src.startswith("Stories/"):
            # Derive story_id from filename: Stories/Story_uf1b.xml → uf1b
            filename = src.split("/")[-1]  # "Story_uf1b.xml"
            match = re.match(r"Story_(.+)\.xml$", filename)
            story_id = match.group(1) if match else filename.rsplit(".", 1)[0]
            return src, story_id

    return _FALLBACK_STORY_NAME, _FALLBACK_STORY_ID


def _count_footnotes(doc: Document) -> int:
    """Return the total number of footnotes across all paragraphs."""
    return sum(len(p.footnotes) for p in doc.paragraphs)


class IDMLBuilder:
    """Assembles an IDML file from a template and a Document."""

    def __init__(self, template_path: str) -> None:
        """
        Parameters
        ----------
        template_path:
            Path to the .indt (or .idml) template file.

        Raises
        ------
        FileNotFoundError
            If the template file does not exist.
        """
        import os

        if not os.path.exists(template_path):
            raise FileNotFoundError(template_path)

        self._template_path = template_path

    def build(self, doc: Document, output_path: str) -> None:
        """
        Generate an IDML file at *output_path* by injecting *doc* into the
        template.

        Parameters
        ----------
        doc:
            Fully style-mapped document to typeset.
        output_path:
            Destination path for the output .idml file.

        Raises
        ------
        ValueError
            If the template is not a valid ZIP archive, or if the generated
            output ZIP fails integrity validation.
        """
        # ------------------------------------------------------------------
        # 1. Open template
        # ------------------------------------------------------------------
        try:
            template_zip = zipfile.ZipFile(self._template_path, "r")
        except zipfile.BadZipFile:
            raise ValueError(
                f"Template file is not a valid ZIP archive: {self._template_path}"
            )

        with template_zip:
            template_names = template_zip.namelist()

            # ------------------------------------------------------------------
            # 2. Find the main story from designmap.xml
            # ------------------------------------------------------------------
            if "designmap.xml" in template_names:
                designmap_bytes = template_zip.read("designmap.xml")
                main_story_path, story_id = _parse_main_story(designmap_bytes)
            else:
                main_story_path = _FALLBACK_STORY_NAME
                story_id = _FALLBACK_STORY_ID

            # ------------------------------------------------------------------
            # 3. Generate replacement story XML
            # ------------------------------------------------------------------
            writer = StoryWriter()
            new_story_bytes = writer.write(doc, story_id)

            # ------------------------------------------------------------------
            # 4. Write output ZIP
            # ------------------------------------------------------------------
            output_buffer = io.BytesIO()
            with zipfile.ZipFile(
                output_buffer, "w", compression=zipfile.ZIP_DEFLATED
            ) as out_zip:
                # Copy all template entries, replacing the main story.
                # IMPORTANT: the "mimetype" entry must be first and uncompressed
                # (IDML / Open Container Format requirement). InDesign rejects
                # files where mimetype is deflate-compressed or out of order.
                def _write_entry(name: str, data: bytes) -> None:
                    if name == "mimetype":
                        zi = zipfile.ZipInfo("mimetype")
                        zi.compress_type = zipfile.ZIP_STORED
                        out_zip.writestr(zi, data)
                    else:
                        out_zip.writestr(name, data)

                # Write mimetype first if present
                if "mimetype" in template_names:
                    _write_entry("mimetype", template_zip.read("mimetype"))

                for name in template_names:
                    if name == "mimetype":
                        continue  # already written above
                    if name == main_story_path:
                        _write_entry(name, new_story_bytes)
                    else:
                        _write_entry(name, template_zip.read(name))

                # If the main story was not in the template, add it now
                if main_story_path not in template_names:
                    out_zip.writestr(main_story_path, new_story_bytes)

        # ------------------------------------------------------------------
        # 5. Write buffer to disk
        # ------------------------------------------------------------------
        output_bytes = output_buffer.getvalue()
        with open(output_path, "wb") as fh:
            fh.write(output_bytes)

        # ------------------------------------------------------------------
        # 6. Validate output ZIP integrity
        # ------------------------------------------------------------------
        try:
            with zipfile.ZipFile(output_path, "r") as check_zip:
                bad = check_zip.testzip()
            if bad is not None:
                raise ValueError(
                    f"Output IDML ZIP failed integrity check — bad entry: {bad}"
                )
        except zipfile.BadZipFile as exc:
            raise ValueError(
                f"Output IDML is not a valid ZIP archive: {output_path}"
            ) from exc

        # ------------------------------------------------------------------
        # 7. Print summary
        # ------------------------------------------------------------------
        para_count = len(doc.paragraphs)
        footnote_count = _count_footnotes(doc)
        print(
            f"IDML built successfully.\n"
            f"  Output:     {output_path}\n"
            f"  Paragraphs: {para_count}\n"
            f"  Footnotes:  {footnote_count}"
        )
