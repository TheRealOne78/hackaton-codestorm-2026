from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.blockers import Envelope, ParseRequest, ValidateRequest
from app.services.ocr_service import ocr_from_path
from app.services.parse_service import parse_ocr_text
from app.services.validation_service import validate_document

router = APIRouter(tags=["blockers"])


@router.post("/ocr", response_model=Envelope)
async def run_ocr(file: UploadFile = File(...)) -> Envelope:
    suffix = Path(file.filename or "input.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        result = ocr_from_path(Path(tmp.name))

    return Envelope(data=result.model_dump(), meta={"endpoint": "/ocr"})


@router.post("/parse", response_model=Envelope)
def run_parse(payload: ParseRequest) -> Envelope:
    parsed = parse_ocr_text(payload.text)
    return Envelope(data=parsed.model_dump(), meta={"endpoint": "/parse"})


@router.post("/validate", response_model=Envelope)
def run_validate(payload: ValidateRequest) -> Envelope:
    result = validate_document(payload.document, max_individual_weight=payload.max_individual_weight)
    return Envelope(data=result.model_dump(), meta={"endpoint": "/validate"})


@router.post("/pipeline/run-blockers", response_model=Envelope)
async def run_pipeline(file: UploadFile = File(...)) -> Envelope:
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
