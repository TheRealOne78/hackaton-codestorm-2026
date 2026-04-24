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


class SpellcheckRequest(BaseModel):
    """Request body for spell-check endpoint."""

    text: str
    language: str = "ro-RO"
    max_issues: int = 200
    include_corrected_text: bool = False
    auto_apply_mode: Literal["off", "safe", "aggressive"] = "off"
    min_confidence: float = 0.84
    custom_dictionary: list[str] = Field(default_factory=list)


class SpellIssue(BaseModel):
    """Single spelling issue with suggestions and source offset."""

    token: str
    offset: int
    length: int
    message: str
    replacements: list[str] = Field(default_factory=list)
    rule_id: str
    category: str | None = None
    confidence: float = 0.0
    chosen_replacement: str | None = None
    auto_applied: bool = False


class SpellcheckResult(BaseModel):
    """Romanian spell-check output."""

    available: bool
    language: str
    issues: list[SpellIssue] = Field(default_factory=list)
    duplicate_tokens: list[dict[str, Any]] = Field(default_factory=list)
    corrected_text: str | None = None
    auto_apply_mode: Literal["off", "safe", "aggressive"] = "off"
    warnings: list[str] = Field(default_factory=list)
