from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import os
from pathlib import Path

from app.schemas.blockers import OcrBlock, OcrPage, OcrResult


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def _run(cmd: list[str], timeout: int = 90) -> str:
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return completed.stdout


def _safe_run(cmd: list[str], timeout: int = 90) -> tuple[str | None, str | None]:
    try:
        return _run(cmd, timeout=timeout), None
    except FileNotFoundError:
        return None, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return None, f"Command timeout: {' '.join(cmd)}"
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        return None, f"Command failed ({exc.returncode}): {' '.join(cmd)} {stderr}".strip()


def _pdf_page_count(pdf_path: Path) -> int:
    output, _ = _safe_run(["pdfinfo", str(pdf_path)])
    if not output:
        return 1
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    return int(match.group(1)) if match else 1


def _extract_pdf_text_pages(pdf_path: Path, page_count: int) -> list[str]:
    pages: list[str] = []
    for page in range(1, page_count + 1):
        output, _ = _safe_run(["pdftotext", "-f", str(page), "-l", str(page), str(pdf_path), "-"])
        pages.append(output or "")
    return pages


def _ocr_pdf_with_ocrmypdf(pdf_path: Path) -> tuple[list[str] | None, str | None]:
    if shutil.which("ocrmypdf") is None:
        return None, "OCRmyPDF not available"

    with tempfile.TemporaryDirectory(prefix="ocr-") as tmp:
        tmpdir = Path(tmp)
        out_pdf = tmpdir / "ocr_out.pdf"
        sidecar = tmpdir / "ocr.txt"
        cmd = [
            "ocrmypdf",
            "--skip-text",
            "--sidecar",
            str(sidecar),
            str(pdf_path),
            str(out_pdf),
        ]
        _, error = _safe_run(cmd, timeout=240)
        if error:
            return None, f"OCRmyPDF failed: {error}"

        text = sidecar.read_text(encoding="utf-8", errors="ignore") if sidecar.exists() else ""
        return text.split("\f") if text else [""], None


def _ocr_image_with_tesseract(image_path: Path) -> tuple[str | None, str | None]:
    if shutil.which("tesseract") is None:
        return None, "tesseract not available"

    lang = os.getenv("OCR_TESSERACT_LANG", "ron+eng")
    output, error = _safe_run(["tesseract", str(image_path), "stdout", "-l", lang], timeout=120)
    return output, error


def _ocr_pdf_with_pdftoppm_tesseract(pdf_path: Path, page_count: int) -> tuple[list[str] | None, str | None]:
    if shutil.which("pdftoppm") is None:
        return None, "pdftoppm not available"
    if shutil.which("tesseract") is None:
        return None, "tesseract not available"

    pages_text: list[str] = []

    with tempfile.TemporaryDirectory(prefix="ocr-pages-") as tmp:
        tmpdir = Path(tmp)
        for page in range(1, page_count + 1):
            ppm_prefix = tmpdir / f"page_{page:04d}"
            cmd = [
                "pdftoppm",
                "-f",
                str(page),
                "-l",
                str(page),
                "-png",
                str(pdf_path),
                str(ppm_prefix),
            ]
            _, render_error = _safe_run(cmd, timeout=120)
            if render_error:
                return None, f"pdftoppm failed on page {page}: {render_error}"

            png_path = tmpdir / f"page_{page:04d}-1.png"
            text, ocr_error = _ocr_image_with_tesseract(png_path)
            if ocr_error:
                return None, f"tesseract failed on page {page}: {ocr_error}"
            pages_text.append(text or "")

    return pages_text, None


def _build_result(
    pages_text: list[str],
    page_count: int,
    needs_ocr: bool,
    source_type: str,
    engine: str,
    warnings: list[str],
) -> OcrResult:
    normalized_pages = pages_text[:]
    if len(normalized_pages) < page_count:
        normalized_pages.extend([""] * (page_count - len(normalized_pages)))

    normalized_pages = normalized_pages[:page_count]

    pages = [
        OcrPage(
            page_number=i + 1,
            text_length=len(page_text.strip()),
            preview=page_text.strip().replace("\n", " ")[:180],
        )
        for i, page_text in enumerate(normalized_pages)
    ]

    blocks = [OcrBlock(page_number=page.page_number, text=page.preview) for page in pages if page.preview]

    return OcrResult(
        full_text="\f".join(normalized_pages),
        pages=pages,
        blocks=blocks,
        tables=[],
        needs_ocr=needs_ocr,
        engine=engine,
        source_type=source_type,  # type: ignore[arg-type]
        warnings=warnings,
    )


def ocr_from_path(file_path: Path) -> OcrResult:
    suffix = file_path.suffix.lower()
    warnings: list[str] = []

    if suffix == ".pdf":
        source_type = "pdf"
        page_count = _pdf_page_count(file_path)
        text_pages = _extract_pdf_text_pages(file_path, page_count)
        extracted_len = sum(len(p.strip()) for p in text_pages)

        if extracted_len >= 200:
            return _build_result(
                text_pages,
                page_count,
                needs_ocr=False,
                source_type=source_type,
                engine="pdftotext",
                warnings=warnings,
            )

        ocrmypdf_pages, ocrmypdf_error = _ocr_pdf_with_ocrmypdf(file_path)
        if ocrmypdf_error:
            warnings.append(ocrmypdf_error)

        if ocrmypdf_pages and sum(len(p.strip()) for p in ocrmypdf_pages) >= 50:
            return _build_result(
                ocrmypdf_pages,
                page_count,
                needs_ocr=False,
                source_type=source_type,
                engine="ocrmypdf",
                warnings=warnings,
            )

        tesseract_pages, tesseract_error = _ocr_pdf_with_pdftoppm_tesseract(file_path, page_count)
        if tesseract_error:
            warnings.append(tesseract_error)

        if tesseract_pages and sum(len(p.strip()) for p in tesseract_pages) >= 30:
            return _build_result(
                tesseract_pages,
                page_count,
                needs_ocr=False,
                source_type=source_type,
                engine="pdftoppm+tesseract",
                warnings=warnings,
            )

        warnings.append("OCR produced very low text")
        fallback_pages = tesseract_pages or ocrmypdf_pages or text_pages
        return _build_result(
            fallback_pages,
            page_count,
            needs_ocr=True,
            source_type=source_type,
            engine="fallback",
            warnings=warnings,
        )

    if suffix in IMAGE_SUFFIXES:
        source_type = "image"
        text, error = _ocr_image_with_tesseract(file_path)
        if error:
            warnings.append(error)
        page_text = text or ""
        needs_ocr = len(page_text.strip()) < 30
        return _build_result(
            [page_text],
            1,
            needs_ocr=needs_ocr,
            source_type=source_type,
            engine="tesseract",
            warnings=warnings,
        )

    if suffix == ".txt":
        source_type = "text"
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return _build_result(
            [text],
            1,
            needs_ocr=False,
            source_type=source_type,
            engine="raw-text",
            warnings=warnings,
        )

    return _build_result(
        [""],
        1,
        needs_ocr=False,
        source_type="unknown",
        engine="unsupported",
        warnings=[f"Unsupported extension: {suffix}"],
    )
