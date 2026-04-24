# Task 0 Notes (Initial Work)

## Sample Inspection

- `samples/fisa_disciplina.pdf`
  - 99 pages
  - Contains multiple entries (`FIȘA DISCIPLINEI` appears repeatedly)
- `samples/plan_invatamant.pdf`
  - 7 pages
  - Text extraction is mostly empty (image-based / OCR needed)

## Slicing Output

Generated with:

```bash
scripts/slice_sample_pdfs.py
```

Outputs:
- `samples/sliced/fisa_disciplina/` -> 24 entry-level PDFs
- `samples/sliced/plan_invatamant/` -> 7 page-level PDFs
- `samples/sliced/manifest.json` -> machine-readable page ranges
- `samples/sliced/README.md` -> quick summary

## Why this helps

- OCR can run on smaller chunks.
- Parser/validator can be tested on isolated entries.
- Failures become easier to triage (exact segment/page known).
