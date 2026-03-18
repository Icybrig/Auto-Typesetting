"""
CLI entry point for the Auto-Typesetting tool.

Orchestrates the pipeline: parse Word document → map styles → build IDML.

Usage:
    python main.py \\
      --input  book.docx \\
      --output book.idml \\
      --template templates/novel.indt \\
      --config  config/style_map.json
"""

import sys
import argparse

from src.parser.docx_parser import parse
from src.mapper.style_mapper import StyleMapper
from src.generator.idml_builder import IDMLBuilder


def main():
    """Parse CLI args and orchestrate the typesetting pipeline."""
    parser = argparse.ArgumentParser(
        description="Automate book typesetting from Word documents to InDesign IDML."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input Word document (.docx)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output InDesign file (.idml)",
    )
    parser.add_argument(
        "--template",
        required=True,
        help="Path to the InDesign template (.indt or .idml)",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the style mapping configuration file (JSON)",
    )

    args = parser.parse_args()

    try:
        # Step 1: Parse the Word document
        document = parse(args.input)

        # Step 2: Map styles from Word to InDesign
        mapper = StyleMapper(args.config)
        mapped_document = mapper.map_document(document)

        # Step 3: Build the IDML output
        builder = IDMLBuilder(args.template)
        builder.build(mapped_document, args.output)

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
