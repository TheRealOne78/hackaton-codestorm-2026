#!/usr/bin/env python3
"""Check OCR runtime dependencies and required language packs."""

from __future__ import annotations

import shutil
import subprocess
import sys


def has_cmd(name: str) -> bool:
    """Return True when a command is available on PATH."""
    return shutil.which(name) is not None


def tesseract_langs() -> set[str]:
    """Return installed tesseract language identifiers."""
    if not has_cmd("tesseract"):
        return set()
    result = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, check=False)
    langs = set()
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if line:
            langs.add(line)
    return langs


def main() -> None:
    """Run OCR environment checks and exit non-zero when critical deps are missing."""
    required = ["pdftotext", "pdfinfo", "pdftoppm", "tesseract", "qpdf", "ghostscript"]
    optional = ["ocrmypdf"]

    missing_required = [cmd for cmd in required if not has_cmd(cmd)]
    missing_optional = [cmd for cmd in optional if not has_cmd(cmd)]

    langs = tesseract_langs()
    missing_langs = [lang for lang in ["eng", "ron"] if lang not in langs]

    print("OCR Environment Check")
    print("---")
    print(f"Required commands: {required}")
    print(f"Missing required: {missing_required}")
    print(f"Missing optional: {missing_optional}")
    print(f"Tesseract languages: {sorted(langs)}")
    print(f"Missing tesseract langs (eng, ron): {missing_langs}")

    if missing_required or missing_langs:
        sys.exit(1)


if __name__ == "__main__":
    main()
