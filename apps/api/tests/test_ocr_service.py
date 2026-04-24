"""Unit tests for OCR service fallback and extraction behavior."""

from pathlib import Path

from app.services import ocr_service


def test_ocr_from_txt_file(tmp_path: Path) -> None:
    text_file = tmp_path / "sample.txt"
    text_file.write_text("Disciplina: Test\nCredite: 5", encoding="utf-8")

    result = ocr_service.ocr_from_path(text_file)

    assert result.source_type == "text"
    assert result.needs_ocr is False
    assert result.engine == "raw-text"
    assert "Credite" in result.full_text
    assert len(result.pages) == 1


def test_ocr_pdf_uses_digital_text(monkeypatch, tmp_path: Path) -> None:
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(ocr_service, "_pdf_page_count", lambda _p: 2)
    monkeypatch.setattr(
        ocr_service,
        "_extract_pdf_text_pages",
        lambda _p, _c: ["A" * 220, "B" * 220],
    )
    monkeypatch.setattr(
        ocr_service,
        "_extract_pdf_layout_pages",
        lambda _p, _c: [
            "Nr.  Disciplina  Cr\n1  Analiza matematica  5\n",
            "Nr.  Disciplina  Cr\n2  Algoritmi  6\n",
        ],
    )
    monkeypatch.setattr(
        ocr_service,
        "_ocr_pdf_with_ocrmypdf",
        lambda _p: (None, None, "OCRmyPDF not available"),
    )
    monkeypatch.setattr(
        ocr_service,
        "_ocr_pdf_with_pdftoppm_tesseract",
        lambda _p, _c: (None, "tesseract failed"),
    )

    result = ocr_service.ocr_from_path(pdf_file)

    assert result.source_type == "pdf"
    assert result.needs_ocr is False
    assert result.engine == "pdftotext"
    assert len(result.pages) == 2
    assert len(result.tables) >= 1
    assert result.warnings == []


def test_ocr_pdf_falls_back_to_tesseract(monkeypatch, tmp_path: Path) -> None:
    pdf_file = tmp_path / "scan.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(ocr_service, "_pdf_page_count", lambda _p: 2)
    monkeypatch.setattr(ocr_service, "_extract_pdf_text_pages", lambda _p, _c: ["", ""])
    monkeypatch.setattr(ocr_service, "_extract_pdf_layout_pages", lambda _p, _c: ["", ""])
    monkeypatch.setattr(
        ocr_service,
        "_ocr_pdf_with_ocrmypdf",
        lambda _p: (None, None, "OCRmyPDF not available"),
    )
    monkeypatch.setattr(
        ocr_service,
        "_ocr_pdf_with_pdftoppm_tesseract",
        lambda _p, _c: (["pagina unu cu text extins", "pagina doi cu text extins"], None),
    )

    result = ocr_service.ocr_from_path(pdf_file)

    assert result.source_type == "pdf"
    assert result.needs_ocr is False
    assert result.engine == "pdftoppm+tesseract"
    assert "pagina unu" in result.full_text
    assert any("OCRmyPDF not available" in warning for warning in result.warnings)


def test_table_row_heuristic_extracts_columns() -> None:
    layout = "Nr.  Disciplina  C  Cr\n1  Algoritmi fundamentali  DF  6\n"
    rows = ocr_service._extract_table_rows_from_layout(layout)
    assert rows
    assert rows[0][0] == "Nr."
