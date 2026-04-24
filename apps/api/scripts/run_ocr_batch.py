#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running the script directly from repo root or apps/api
API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.ocr_service import ocr_from_path


def discover_files(input_dir: Path) -> list[Path]:
    exts = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".txt"}
    return sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OCR over a folder and save JSONL results")
    parser.add_argument(
        "--input-dir",
        default=str((REPO_ROOT / "samples" / "sliced").resolve()),
        help="Folder containing pdf/image/txt files",
    )
    parser.add_argument(
        "--output",
        default=str((API_ROOT / "ocr_batch_results.jsonl").resolve()),
        help="Output JSONL path",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = discover_files(input_dir)
    if not files:
        print(f"No OCR-able files found in {input_dir}")
        return

    total = len(files)
    needs_ocr_count = 0
    warning_count = 0

    with output_path.open("w", encoding="utf-8") as fp:
        for idx, file_path in enumerate(files, start=1):
            result = ocr_from_path(file_path)
            payload = {
                "file": str(file_path),
                "source_type": result.source_type,
                "needs_ocr": result.needs_ocr,
                "text_length": len(result.full_text.strip()),
                "pages": len(result.pages),
                "warnings": result.warnings,
            }
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

            if result.needs_ocr:
                needs_ocr_count += 1
            if result.warnings:
                warning_count += 1

            print(
                f"[{idx}/{total}] {file_path.name}: type={result.source_type} "
                f"text={payload['text_length']} needs_ocr={result.needs_ocr}"
            )

    print("---")
    print(f"Processed: {total}")
    print(f"Marked needs_ocr: {needs_ocr_count}")
    print(f"With warnings: {warning_count}")
    print(f"Results: {output_path}")


if __name__ == "__main__":
    main()
