# OCR / Table Extraction Prior Art (2026-04-24)

This list captures mature implementations we can borrow patterns from instead of hardcoding OCR typo dictionaries.

## 1) OCRmyPDF
- Link: https://ocrmypdf.readthedocs.io/
- Why useful:
  - Standard scanned-PDF OCR pipeline (deskew, clean, sidecar text, searchable PDF).
  - Good fit for our `pdf -> OCR fallback` stage.
- How we already use it:
  - Preferred OCR fallback engine for scanned PDFs before `pdftoppm+tesseract`.

## 2) pdfplumber
- Link: https://github.com/jsvine/pdfplumber
- Why useful:
  - Character-level extraction + table extraction controls.
  - Better than plain whitespace-split for many rule-heavy PDFs.
- Suggested use in this project:
  - Optional extractor path for digital PDFs or OCRed searchable PDFs.

## 3) pypdf-table-extraction (Camelot)
- Link: https://pypdf-table-extraction.readthedocs.io/
- Why useful:
  - Dedicated PDF table extraction with lattice/stream modes.
  - Can significantly improve semester/course table extraction if lines are detectable.
- Caveat:
  - Works best on text-based PDFs (less reliable on heavily noisy scans).

## 4) Unstructured
- Link: https://docs.unstructured.io/open-source/core-functionality/partitioning
- Why useful:
  - Higher-level document partitioning (titles, tables, text chunks).
  - Useful for modular parser stages and fallback extraction logic.

## 5) PaddleOCR / PP-Structure
- Link: https://www.paddleocr.ai/
- Why useful:
  - End-to-end OCR + layout/table structure recognition models.
  - Strong option for difficult scanned tables where deterministic splitting fails.

## 6) docTR
- Link: https://mindee.github.io/doctr/
- Why useful:
  - Deep-learning OCR pipeline with detection + recognition.
  - Alternative OCR engine if Tesseract quality is insufficient.

## Adoption recommendation for current hackathon scope
1. Keep current deterministic pipeline (`pdftotext` -> `ocrmypdf` -> `pdftoppm+tesseract`).
2. Add optional `pdfplumber` extraction path for table-rich pages.
3. If table quality is still poor, evaluate `pypdf-table-extraction` for digital/searchable PDFs.
4. Keep ML-heavy table recognition (`PaddleOCR`) as a phase-2 fallback due to setup/time cost.
