#!/usr/bin/env python3
"""
Scan a .docx file and compare its styles against style_map.json.

Usage:
    python scan_styles.py --input book.docx
    python scan_styles.py --input book.docx --config config/style_map.json
    python scan_styles.py --input book.docx --update   # auto-add unmapped styles
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import docx


def scan(docx_path: str, config_path: str, update: bool) -> None:
    # ── Load Word document ────────────────────────────────────────────────────
    doc = docx.Document(docx_path)

    para_styles: Counter = Counter()
    char_styles: Counter = Counter()

    for para in doc.paragraphs:
        name = para.style.name if para.style else "Normal"
        para_styles[name] += 1
        for run in para.runs:
            if run.style and run.style.name and run.style.name != "Default Paragraph Font":
                char_styles[run.style.name] += 1

    # ── Load config ───────────────────────────────────────────────────────────
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "paragraph_styles": {},
            "character_styles": {},
            "fallback_paragraph_style": "Body Text",
        }

    p_map: dict = config.get("paragraph_styles", {})
    c_map: dict = config.get("character_styles", {})
    fallback: str = config.get("fallback_paragraph_style", "Body Text")

    # ── Report: paragraph styles ──────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Word file : {docx_path}")
    print(f"  Config    : {config_path}")
    print(f"{'='*60}")

    print(f"\nPARAGRAPH STYLES  ({len(para_styles)} unique)\n")
    unmapped_para = []
    for style, count in para_styles.most_common():
        if style in p_map:
            tag = f"-> \"{p_map[style]}\""
        else:
            tag = f"[UNMAPPED — falls back to \"{fallback}\"]"
            unmapped_para.append(style)
        print(f"  {count:5}x  \"{style}\"  {tag}")

    print(f"\nCHARACTER STYLES  ({len(char_styles)} unique)\n")
    unmapped_char = []
    for style, count in char_styles.most_common():
        if style in c_map:
            tag = f"-> \"{c_map[style]}\""
        else:
            tag = "[UNMAPPED — set to None]"
            unmapped_char.append(style)
        print(f"  {count:5}x  \"{style}\"  {tag}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if not unmapped_para and not unmapped_char:
        print("  All styles are mapped. No changes needed.")
        print(f"{'='*60}\n")
        return

    if unmapped_para:
        print(f"  Unmapped paragraph styles ({len(unmapped_para)}):")
        for s in unmapped_para:
            print(f"    \"{s}\"")
    if unmapped_char:
        print(f"  Unmapped character styles ({len(unmapped_char)}):")
        for s in unmapped_char:
            print(f"    \"{s}\"")
    print(f"{'='*60}\n")

    # ── Auto-update mode ──────────────────────────────────────────────────────
    if update:
        changed = False
        print("Auto-update mode: adding unmapped styles to config.\n")
        print("For each unmapped style, enter the InDesign style name to map to,")
        print("or press Enter to keep the fallback (Body Text for paragraphs, None for chars).\n")

        for style in unmapped_para:
            try:
                answer = input(f"  Paragraph \"{style}\" -> ").strip()
            except EOFError:
                answer = ""
            if answer:
                p_map[style] = answer
                changed = True
                print(f"    Added: \"{style}\" -> \"{answer}\"")
            else:
                print(f"    Skipped (will use fallback \"{fallback}\")")

        for style in unmapped_char:
            try:
                answer = input(f"  Character \"{style}\" -> ").strip()
            except EOFError:
                answer = ""
            if answer:
                c_map[style] = answer
                changed = True
                print(f"    Added: \"{style}\" -> \"{answer}\"")
            else:
                print(f"    Skipped (will set to None)")

        if changed:
            config["paragraph_styles"] = p_map
            config["character_styles"] = c_map
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"\nSaved: {config_path}")
        else:
            print("\nNo changes made.")
    else:
        print("Run with --update to interactively map the missing styles.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan Word styles vs style_map.json")
    parser.add_argument("--input",  required=True, help="Path to .docx file")
    parser.add_argument("--config", default="config/style_map.json",
                        help="Path to style_map.json (default: config/style_map.json)")
    parser.add_argument("--update", action="store_true",
                        help="Interactively add missing styles to config")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    scan(args.input, args.config, args.update)


if __name__ == "__main__":
    main()
