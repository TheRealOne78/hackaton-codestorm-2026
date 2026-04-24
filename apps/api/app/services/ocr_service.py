"""OCR service with multi-engine fallback and text/table sanitization."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import os
import unicodedata
from collections import Counter
from pathlib import Path

from app.schemas.blockers import OcrBlock, OcrPage, OcrResult, OcrTable


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def _run(cmd: list[str], timeout: int = 90) -> str:
    """Run a command and return stdout, raising on failure."""
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return completed.stdout


def _safe_run(cmd: list[str], timeout: int = 90) -> tuple[str | None, str | None]:
    """Run a command and return either output or an error message."""
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
    """Read PDF page count using `pdfinfo`."""
    output, _ = _safe_run(["pdfinfo", str(pdf_path)])
    if not output:
        return 1
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    return int(match.group(1)) if match else 1


def _extract_pdf_text_pages(pdf_path: Path, page_count: int) -> list[str]:
    """Extract plain text page-by-page from a PDF."""
    pages: list[str] = []
    for page in range(1, page_count + 1):
        output, _ = _safe_run(["pdftotext", "-f", str(page), "-l", str(page), str(pdf_path), "-"])
        pages.append(output or "")
    return pages


def _extract_pdf_layout_pages(pdf_path: Path, page_count: int) -> list[str]:
    """Extract layout-preserving text page-by-page from a PDF."""
    pages: list[str] = []
    for page in range(1, page_count + 1):
        output, _ = _safe_run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf_path), "-"])
        pages.append(output or "")
    return pages


def _extract_table_rows_from_layout(layout_text: str) -> list[list[str]]:
    """Heuristically detect table-like rows from layout text."""
    rows: list[list[str]] = []
    for raw_line in layout_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # Heuristic: treat lines with multiple aligned columns (2+ spaces) as potential table rows.
        cells = [cell.strip() for cell in re.split(r"\s{2,}", line) if cell.strip()]
        if len(cells) < 3:
            continue

        # Keep rows that look tabular (contain at least one numeric token or short code-like cell).
        looks_tabular = any(re.search(r"\d", cell) for cell in cells) or any(len(cell) <= 5 for cell in cells)
        if looks_tabular:
            rows.append(cells)

    return rows


def _sanitize_text_line(line: str) -> str:
    """Normalize unicode and whitespace for a single line."""
    value = unicodedata.normalize("NFKC", line)
    value = (
        value.replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
        .replace("’", "'")
        .replace("`", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("—", "-")
    )
    value = value.replace("|", " | ")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+\|\s+", " | ", value)
    return value


def _looks_like_noise_line(line: str) -> bool:
    """Return True when a line appears to be OCR noise."""
    if not line:
        return True
    # Mostly symbols or short OCR garbage
    if len(line) <= 2:
        return True
    alnum = sum(ch.isalnum() for ch in line)
    if alnum == 0:
        return True
    ratio = alnum / max(1, len(line))
    return ratio < 0.35


def _detect_repeated_headers_footers(pages_text: list[str]) -> set[str]:
    """Detect recurring header/footer lines across pages."""
    if len(pages_text) < 2:
        return set()

    normalized_lines: list[str] = []
    for page_text in pages_text:
        lines = [line.strip() for line in page_text.splitlines()]
        # Header/footer candidates: top/bottom few non-empty lines
        top = [ln for ln in lines[:6] if ln]
        bottom = [ln for ln in lines[-6:] if ln]
        # Avoid double counting the same line from short pages.
        candidates = list(dict.fromkeys([*top, *bottom]))
        normalized_lines.extend(_sanitize_text_line(ln).lower() for ln in candidates)

    counts = Counter(normalized_lines)
    threshold = max(2, len(pages_text) // 2)
    repeated = {
        line
        for line, count in counts.items()
        if count >= threshold and len(line) > 6 and not _looks_like_noise_line(line)
    }
    return repeated


def _sanitize_pages_text(pages_text: list[str]) -> list[str]:
    """Clean OCR page text and remove repeated noise lines."""
    repeated_noise = _detect_repeated_headers_footers(pages_text)
    sanitized_pages: list[str] = []

    for page_text in pages_text:
        clean_lines: list[str] = []
        for raw in page_text.splitlines():
            line = _sanitize_text_line(raw)
            if not line:
                continue
            if line.lower() in repeated_noise:
                continue
            if _looks_like_noise_line(line):
                continue
            clean_lines.append(line)

        # Collapse excessive blank lines and keep readable structure
        joined = "\n".join(clean_lines)
        joined = re.sub(r"\n{3,}", "\n\n", joined).strip()
        sanitized_pages.append(joined)

    return sanitized_pages


def _sanitize_table_rows(rows: list[list[str]]) -> list[list[str]]:
    """Clean and deduplicate heuristic table rows."""
    sanitized: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    for row in rows:
        clean_cells = []
        for cell in row:
            value = _sanitize_text_line(cell)
            value = re.sub(r"^[\W_]+|[\W_]+$", "", value)
            if value:
                clean_cells.append(value)

        if len(clean_cells) < 2:
            continue

        # Drop very noisy rows
        row_text = " ".join(clean_cells)
        if _looks_like_noise_line(row_text):
            continue

        key = tuple(clean_cells)
        if key in seen:
            continue
        seen.add(key)
        sanitized.append(clean_cells)

    return sanitized


def _ocr_pdf_with_ocrmypdf(pdf_path: Path) -> tuple[list[str] | None, list[str] | None, str | None]:
    """Run OCRmyPDF and return sidecar text pages plus layout pages."""
    if shutil.which("ocrmypdf") is None:
        return None, None, "OCRmyPDF not available"

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
            return None, None, f"OCRmyPDF failed: {error}"

        text = sidecar.read_text(encoding="utf-8", errors="ignore") if sidecar.exists() else ""
        page_count = _pdf_page_count(out_pdf) if out_pdf.exists() else 1
        layout_pages = _extract_pdf_layout_pages(out_pdf, page_count) if out_pdf.exists() else [""]
        return text.split("\f") if text else [""], layout_pages, None


def _ocr_image_with_tesseract(image_path: Path) -> tuple[str | None, str | None]:
    """Run tesseract OCR for a single image."""
    if shutil.which("tesseract") is None:
        return None, "tesseract not available"

    lang = os.getenv("OCR_TESSERACT_LANG", "ron+eng")
    output, error = _safe_run(["tesseract", str(image_path), "stdout", "-l", lang], timeout=120)
    return output, error


def _ocr_pdf_with_pdftoppm_tesseract(pdf_path: Path, page_count: int) -> tuple[list[str] | None, str | None]:
    """Render PDF pages to images and OCR each page with tesseract."""
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
    layout_pages: list[str],
    page_count: int,
    needs_ocr: bool,
    source_type: str,
    engine: str,
    warnings: list[str],
) -> OcrResult:
    """Assemble the final OCR result model from intermediate artifacts."""
    normalized_pages = _sanitize_pages_text(pages_text)
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

    tables: list[OcrTable] = []
    for i, layout_text in enumerate(layout_pages[:page_count]):
        table_rows = _sanitize_table_rows(_extract_table_rows_from_layout(layout_text))
        if table_rows:
            tables.append(OcrTable(page_number=i + 1, rows=table_rows))

    return OcrResult(
        full_text="\f".join(normalized_pages),
        pages=pages,
        blocks=blocks,
        tables=tables,
        needs_ocr=needs_ocr,
        engine=engine,
        source_type=source_type,  # type: ignore[arg-type]
        warnings=warnings,
    )


def ocr_from_path(file_path: Path) -> OcrResult:
    """Run OCR for a file path using the best available extraction chain."""
    suffix = file_path.suffix.lower()
    warnings: list[str] = []

    if suffix == ".pdf":
        source_type = "pdf"
        page_count = _pdf_page_count(file_path)
        text_pages = _extract_pdf_text_pages(file_path, page_count)
        layout_pages = _extract_pdf_layout_pages(file_path, page_count)
        extracted_len = sum(len(p.strip()) for p in text_pages)

        if extracted_len >= 200:
            return _build_result(
                text_pages,
                layout_pages,
                page_count,
                needs_ocr=False,
                source_type=source_type,
                engine="pdftotext",
                warnings=warnings,
            )

        ocrmypdf_pages, ocrmypdf_layout_pages, ocrmypdf_error = _ocr_pdf_with_ocrmypdf(file_path)
        if ocrmypdf_error:
            warnings.append(ocrmypdf_error)

        if ocrmypdf_pages and sum(len(p.strip()) for p in ocrmypdf_pages) >= 50:
            return _build_result(
                ocrmypdf_pages,
                ocrmypdf_layout_pages or layout_pages,
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
                layout_pages,
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
            layout_pages,
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
            [text],
            1,
            needs_ocr=False,
            source_type=source_type,
            engine="raw-text",
            warnings=warnings,
        )

    return _build_result(
        [""],
        [""],
        1,
        needs_ocr=False,
        source_type="unknown",
        engine="unsupported",
        warnings=[f"Unsupported extension: {suffix}"],
    )
