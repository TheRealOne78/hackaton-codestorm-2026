#!/usr/bin/env python3
"""Slice sample PDFs into smaller units for OCR/parser iteration.

- fisa_disciplina.pdf: split by detected entry boundaries ("FISA/FIȘA DISCIPLINEI")
- plan_invatamant.pdf: split by page (image-based sample)

Requires CLI tools available on Linux:
- pdfinfo
- pdftotext
- qpdf
"""

from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "samples"
OUT_DIR = SAMPLES_DIR / "sliced"

FISA_INPUT = SAMPLES_DIR / "fisa_disciplina.pdf"
PLAN_INPUT = SAMPLES_DIR / "plan_invatamant.pdf"

ENTRY_MARKER = "FISA DISCIPLINEI"


@dataclass
class SliceSegment:
    source: str
    output: str
    start_page: int
    end_page: int


def run_cmd(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def get_page_count(pdf_path: Path) -> int:
    output = run_cmd(["pdfinfo", str(pdf_path)])
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not read page count for {pdf_path}")
    return int(match.group(1))


def extract_page_text(pdf_path: Path, page: int) -> str:
    output = run_cmd(["pdftotext", "-f", str(page), "-l", str(page), str(pdf_path), "-"])
    return output


def normalize_text(value: str) -> str:
    no_diacritics = "".join(
        ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch)
    )
    collapsed = re.sub(r"\s+", " ", no_diacritics).strip().upper()
    return collapsed


def detect_fisa_starts(pdf_path: Path, pages: int) -> list[int]:
    starts: list[int] = []
    for page in range(1, pages + 1):
        text = extract_page_text(pdf_path, page)
        preview = normalize_text(text[:2000])
        if ENTRY_MARKER in preview:
            starts.append(page)

    if not starts:
        return [1]
    if starts[0] != 1:
        starts.insert(0, 1)

    # Deduplicate while preserving order
    deduped: list[int] = []
    seen: set[int] = set()
    for page in starts:
        if page not in seen:
            deduped.append(page)
            seen.add(page)
    return deduped


def build_ranges(starts: list[int], total_pages: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] - 1 if idx + 1 < len(starts) else total_pages
        if start <= end:
            ranges.append((start, end))
    return ranges


def split_with_qpdf(input_pdf: Path, output_pdf: Path, start_page: int, end_page: int) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "qpdf",
            "--warning-exit-0",
            "--empty",
            "--pages",
            str(input_pdf),
            f"{start_page}-{end_page}",
            "--",
            str(output_pdf),
        ],
        check=True,
    )


def split_fisa() -> list[SliceSegment]:
    pages = get_page_count(FISA_INPUT)
    starts = detect_fisa_starts(FISA_INPUT, pages)
    ranges = build_ranges(starts, pages)

    segments: list[SliceSegment] = []
    out_dir = OUT_DIR / "fisa_disciplina"

    for idx, (start, end) in enumerate(ranges, start=1):
        output_pdf = out_dir / f"fisa_entry_{idx:03d}_p{start:03d}-{end:03d}.pdf"
        split_with_qpdf(FISA_INPUT, output_pdf, start, end)
        segments.append(
            SliceSegment(
                source=str(FISA_INPUT.relative_to(ROOT)),
                output=str(output_pdf.relative_to(ROOT)),
                start_page=start,
                end_page=end,
            )
        )

    return segments


def split_plan_per_page() -> list[SliceSegment]:
    pages = get_page_count(PLAN_INPUT)
    segments: list[SliceSegment] = []
    out_dir = OUT_DIR / "plan_invatamant"

    for page in range(1, pages + 1):
        output_pdf = out_dir / f"plan_page_{page:03d}.pdf"
        split_with_qpdf(PLAN_INPUT, output_pdf, page, page)
        segments.append(
            SliceSegment(
                source=str(PLAN_INPUT.relative_to(ROOT)),
                output=str(output_pdf.relative_to(ROOT)),
                start_page=page,
                end_page=page,
            )
        )

    return segments


def write_manifest(segments: list[SliceSegment]) -> Path:
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_by": "scripts/slice_sample_pdfs.py",
        "segments": [segment.__dict__ for segment in segments],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def write_summary(segments: list[SliceSegment]) -> Path:
    summary_path = OUT_DIR / "README.md"

    by_source: dict[str, list[SliceSegment]] = {}
    for segment in segments:
        by_source.setdefault(segment.source, []).append(segment)

    lines: list[str] = [
        "# Sliced Samples",
        "",
        "Auto-generated by `scripts/slice_sample_pdfs.py`.",
        "",
    ]

    for source, source_segments in by_source.items():
        lines.append(f"## {source}")
        lines.append("")
        lines.append(f"- Segments: {len(source_segments)}")
        lines.append(f"- Page ranges: {', '.join(f'{s.start_page}-{s.end_page}' for s in source_segments)}")
        lines.append("")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def main() -> None:
    if not FISA_INPUT.exists() or not PLAN_INPUT.exists():
        raise FileNotFoundError("Expected samples/fisa_disciplina.pdf and samples/plan_invatamant.pdf")

    fisa_segments = split_fisa()
    plan_segments = split_plan_per_page()
    segments = [*fisa_segments, *plan_segments]

    manifest_path = write_manifest(segments)
    summary_path = write_summary(segments)

    print(f"Created {len(fisa_segments)} slices for {FISA_INPUT.name}")
    print(f"Created {len(plan_segments)} slices for {PLAN_INPUT.name}")
    print(f"Manifest: {manifest_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
