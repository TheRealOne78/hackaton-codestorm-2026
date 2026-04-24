# API (Task 0 + Blockers Vertical Slice)

## Run

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Routes

- `GET /` root status
- `GET /health` healthcheck
- `POST /ocr` upload file (pdf/image/txt) and extract text
- `POST /parse` parse text into internal JSON
- `POST /validate` validate parsed JSON
- `POST /pipeline/run-blockers` upload file and run OCR -> Parse -> Validate
- `GET /docs` OpenAPI docs

## Notes

- OCR currently relies on system tools when available:
  - `pdftotext` for digital PDFs
  - `ocrmypdf` for scanned PDFs
  - `tesseract` for images
- If OCR binaries are missing, API still returns structured output with warnings.

## Tests

```bash
cd apps/api
pytest -q
```
