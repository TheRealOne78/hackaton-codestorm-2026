from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.schemas.blockers import OcrBlock, OcrPage, OcrResult


def _run(cmd: list[str], timeout: int = 90) -> str:
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return completed.stdout


def _extract_pdf_text(pdf_path: Path) -> str:
    return _run(["pdftotext", str(pdf_path), "-"])


def _pdf_page_count(pdf_path: Path) -> int:
    output = _run(["pdfinfo", str(pdf_path)])
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    return int(match.group(1)) if match else 1


def _ocr_pdf_with_ocrmypdf(pdf_path: Path) -> str | None:
    if shutil.which("ocrmypdf") is None:
        return None

    with tempfile.TemporaryDirectory(prefix="ocr-") as tmp:
        tmpdir = Path(tmp)
        out_pdf = tmpdir / "ocr_out.pdf"
        sidecar = tmpdir / "ocr.txt"
        subprocess.run(
            [
                "ocrmypdf",
                "--skip-text",
                "--sidecar",
                str(sidecar),
                str(pdf_path),
                str(out_pdf),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=240,
        )
        return sidecar.read_text(encoding="utf-8", errors="ignore") if sidecar.exists() else None


def _ocr_image_with_tesseract(image_path: Path) -> str | None:
    if shutil.which("tesseract") is None:
        return None
    output = subprocess.run(
        ["tesseract", str(image_path), "stdout"],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return output.stdout


def ocr_from_path(file_path: Path) -> OcrResult:
    suffix = file_path.suffix.lower()
    source_type = "unknown"
    full_text = ""
    warnings: list[str] = []

    if suffix == ".pdf":
        source_type = "pdf"
        text = _extract_pdf_text(file_path)
        if len(text.strip()) >= 200:
            full_text = text
            needs_ocr = False
        else:
            needs_ocr = True
            ocr_text = _ocr_pdf_with_ocrmypdf(file_path)
            if ocr_text:
                full_text = ocr_text
                needs_ocr = False if len(ocr_text.strip()) >= 50 else True
            else:
                full_text = text
                warnings.append("OCR not executed: ocrmypdf not available or OCR failed")

        page_count = _pdf_page_count(file_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        source_type = "image"
        needs_ocr = True
        ocr_text = _ocr_image_with_tesseract(file_path)
        if ocr_text:
            full_text = ocr_text
            needs_ocr = False if len(ocr_text.strip()) >= 30 else True
        else:
            warnings.append("OCR not executed: tesseract not available or OCR failed")
        page_count = 1
    elif suffix == ".txt":
        source_type = "text"
        full_text = file_path.read_text(encoding="utf-8", errors="ignore")
        needs_ocr = False
        page_count = 1
    else:
        source_type = "unknown"
        needs_ocr = False
        page_count = 1
        warnings.append(f"Unsupported extension: {suffix}")

    page_slices = full_text.split("\f") if full_text else [""] * page_count
    if len(page_slices) < page_count:
        page_slices.extend([""] * (page_count - len(page_slices)))

    pages = [
        OcrPage(page_number=i + 1, text_length=len(p.strip()), preview=p.strip().replace("\n", " ")[:180])
        for i, p in enumerate(page_slices[:page_count])
    ]

    blocks = [
        OcrBlock(page_number=page.page_number, text=page.preview)
        for page in pages
        if page.preview
    ]

    return OcrResult(
        full_text=full_text,
        pages=pages,
        blocks=blocks,
        tables=[],
        needs_ocr=needs_ocr,
        source_type=source_type,  # type: ignore[arg-type]
        warnings=warnings,
    )
