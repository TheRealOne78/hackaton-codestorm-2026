"""HTTP routes for OCR, parsing, validation, and pipeline orchestration."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas.blockers import Envelope, ParseRequest, ParseStructuredRequest, SpellcheckRequest, ValidateRequest
from app.services.ocr_service import ocr_from_path
from app.services.parse_service import parse_ocr_text
from app.services.sanitizer_service import sanitize_payload
from app.services.spellcheck_service import spellcheck_text_ro
from app.services.structured_parser_service import parse_structured
from app.services.validation_service import validate_document

router = APIRouter(tags=["blockers"])


@router.post("/ocr", response_model=Envelope)
async def run_ocr(file: UploadFile = File(...)) -> Envelope:
    """Run OCR extraction for an uploaded file."""
    suffix = Path(file.filename or "input.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        result = ocr_from_path(Path(tmp.name))

    return Envelope(data=result.model_dump(), meta={"endpoint": "/ocr"})


@router.post("/parse", response_model=Envelope)
def run_parse(payload: ParseRequest) -> Envelope:
    """Parse raw text into the baseline Fișa-oriented schema."""
    parsed = parse_ocr_text(payload.text)
    return Envelope(data=parsed.model_dump(), meta={"endpoint": "/parse"})


@router.post("/parse-structured", response_model=Envelope)
def run_parse_structured(payload: ParseStructuredRequest) -> Envelope:
    """Parse text (and optional table rows) into a structured Plan/Fișa payload."""
    sanitized = sanitize_payload(
        text=payload.text,
        tables=payload.tables,
        doc_type=payload.document_type,
    )
    parsed = parse_structured(
        text=sanitized["clean_text"],
        tables=payload.tables,
        document_type=sanitized["document_type"],
    )
    return Envelope(
        data={"sanitized": sanitized, "parsed": parsed},
        meta={"endpoint": "/parse-structured", "document_type": payload.document_type},
    )


@router.post("/sanitize", response_model=Envelope)
def run_sanitize(payload: ParseStructuredRequest) -> Envelope:
    """Sanitize OCR text/tables and return normalized dictionaries."""
    sanitized = sanitize_payload(
        text=payload.text,
        tables=payload.tables,
        doc_type=payload.document_type,
    )
    return Envelope(data=sanitized, meta={"endpoint": "/sanitize", "document_type": payload.document_type})


@router.post("/validate", response_model=Envelope)
def run_validate(payload: ValidateRequest) -> Envelope:
    """Validate a parsed Fișa document against integrity and math rules."""
    result = validate_document(payload.document, max_individual_weight=payload.max_individual_weight)
    return Envelope(data=result.model_dump(), meta={"endpoint": "/validate"})


@router.post("/spellcheck", response_model=Envelope)
def run_spellcheck(payload: SpellcheckRequest) -> Envelope:
    """Run Romanian spell-check over a text payload."""
    result = spellcheck_text_ro(
        text=payload.text,
        language=payload.language,
        max_issues=payload.max_issues,
        include_corrected_text=payload.include_corrected_text,
    )
    return Envelope(data=result.model_dump(), meta={"endpoint": "/spellcheck", "language": payload.language})


@router.post("/pipeline/run-blockers", response_model=Envelope)
async def run_pipeline(file: UploadFile = File(...)) -> Envelope:
    """Execute OCR -> parse -> validate in a single request."""
    suffix = Path(file.filename or "input.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        ocr_result = ocr_from_path(Path(tmp.name))

    if not ocr_result.full_text.strip():
        raise HTTPException(status_code=422, detail="OCR produced empty text. Provide a clearer input or OCR engine.")

    parsed = parse_ocr_text(ocr_result.full_text)
    validation = validate_document(parsed)

    return Envelope(
        data={
            "ocr": ocr_result.model_dump(),
            "parsed": parsed.model_dump(),
            "validation": validation.model_dump(),
        },
        meta={"endpoint": "/pipeline/run-blockers"},
    )


@router.post("/pipeline/run-structured", response_model=Envelope)
async def run_pipeline_structured(
    file: UploadFile = File(...),
    document_type: str = Query("auto"),
    spellcheck: bool = Query(True),
) -> Envelope:
    """Execute OCR -> structured parser in a single request."""
    suffix = Path(file.filename or "input.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        ocr_result = ocr_from_path(Path(tmp.name))

    if not ocr_result.full_text.strip():
        raise HTTPException(status_code=422, detail="OCR produced empty text. Provide a clearer input or OCR engine.")

    safe_doc_type = document_type if document_type in {"auto", "fisa", "plan"} else "auto"
    sanitized = sanitize_payload(
        text=ocr_result.full_text,
        tables=ocr_result.tables,
        doc_type=safe_doc_type,  # type: ignore[arg-type]
    )
    parsed = parse_structured(
        text=sanitized["clean_text"],
        tables=ocr_result.tables,
        document_type=sanitized["document_type"],
    )
    spell = (
        spellcheck_text_ro(text=sanitized["clean_text"], language="ro-RO", max_issues=120, include_corrected_text=False)
        if spellcheck
        else None
    )

    return Envelope(
        data={
            "ocr": ocr_result.model_dump(),
            "sanitized": sanitized,
            "parsed": parsed,
            "spellcheck": spell.model_dump() if spell is not None else None,
        },
        meta={"endpoint": "/pipeline/run-structured", "document_type": document_type, "spellcheck": spellcheck},
    )
