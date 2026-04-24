"""Pydantic schemas shared by OCR, parsing, and validation endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    """Standard API envelope used by all endpoints."""

    data: Any | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class OcrPage(BaseModel):
    """Per-page OCR summary."""

    page_number: int
    text_length: int
    preview: str


class OcrBlock(BaseModel):
    """Text block hint extracted from a page preview."""

    page_number: int
    text: str
    bbox: list[float] | None = None


class OcrTable(BaseModel):
    """Heuristic table rows associated with a page."""

    page_number: int
    rows: list[list[str]] = Field(default_factory=list)


class OcrResult(BaseModel):
    """Unified OCR output payload."""

    full_text: str
    pages: list[OcrPage]
    blocks: list[OcrBlock] = Field(default_factory=list)
    tables: list[OcrTable] = Field(default_factory=list)
    needs_ocr: bool
    engine: str = "unknown"
    source_type: Literal["pdf", "image", "text", "unknown"] = "unknown"
    warnings: list[str] = Field(default_factory=list)


class ParseRequest(BaseModel):
    """Request body for baseline text parser."""

    text: str


class ParseStructuredRequest(BaseModel):
    """Request body for structured Plan/Fișa parser."""

    text: str
    tables: list[OcrTable] = Field(default_factory=list)
    document_type: Literal["auto", "fisa", "plan"] = "auto"


class EvaluationItem(BaseModel):
    """Evaluation component with optional percentage weight."""

    label: str
    weight: float | None = None


class ParsedDocument(BaseModel):
    """Baseline parsed Fișa representation used by validator."""

    title: str | None = None
    credits: int | None = None
    objectives: str | None = None
    bibliography: list[str] | None = None
    evaluation: list[EvaluationItem] | None = None
    competencies: list[str] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    """Validation issue with machine-readable code and path."""

    code: str
    path: str
    message: str
    severity: Literal["error", "warning"]
    suggested_fix: str


class ValidationResult(BaseModel):
    """Validation outcome split into errors and warnings."""

    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class ValidateRequest(BaseModel):
    """Request body for validation endpoint."""

    document: ParsedDocument
    max_individual_weight: float = 60.0
