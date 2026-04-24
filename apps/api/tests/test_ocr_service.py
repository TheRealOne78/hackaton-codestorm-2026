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
    monkeypatch.setattr(ocr_service, "_ocr_pdf_with_ocrmypdf", lambda _p: (None, "OCRmyPDF not available"))
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
    assert result.warnings == []


def test_ocr_pdf_falls_back_to_tesseract(monkeypatch, tmp_path: Path) -> None:
    pdf_file = tmp_path / "scan.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(ocr_service, "_pdf_page_count", lambda _p: 2)
    monkeypatch.setattr(ocr_service, "_extract_pdf_text_pages", lambda _p, _c: ["", ""])
    monkeypatch.setattr(ocr_service, "_ocr_pdf_with_ocrmypdf", lambda _p: (None, "OCRmyPDF not available"))
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
