from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    data: Any | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class OcrPage(BaseModel):
    page_number: int
    text_length: int
    preview: str


class OcrBlock(BaseModel):
    page_number: int
    text: str
    bbox: list[float] | None = None


class OcrTable(BaseModel):
    page_number: int
    rows: list[list[str]] = Field(default_factory=list)


class OcrResult(BaseModel):
    full_text: str
    pages: list[OcrPage]
    blocks: list[OcrBlock] = Field(default_factory=list)
    tables: list[OcrTable] = Field(default_factory=list)
    needs_ocr: bool
    engine: str = "unknown"
    source_type: Literal["pdf", "image", "text", "unknown"] = "unknown"
    warnings: list[str] = Field(default_factory=list)


class ParseRequest(BaseModel):
    text: str


class ParseStructuredRequest(BaseModel):
    text: str
    tables: list[OcrTable] = Field(default_factory=list)
    document_type: Literal["auto", "fisa", "plan"] = "auto"


class EvaluationItem(BaseModel):
    label: str
    weight: float | None = None


class ParsedDocument(BaseModel):
    title: str | None = None
    credits: int | None = None
    objectives: str | None = None
    bibliography: list[str] | None = None
    evaluation: list[EvaluationItem] | None = None
    competencies: list[str] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    code: str
    path: str
    message: str
    severity: Literal["error", "warning"]
    suggested_fix: str


class ValidationResult(BaseModel):
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class ValidateRequest(BaseModel):
    document: ParsedDocument
    max_individual_weight: float = 60.0
