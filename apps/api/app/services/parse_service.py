from __future__ import annotations

import re

from app.schemas.blockers import EvaluationItem, ParsedDocument


def _match_block(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            value = m.group(1).strip()
            if value:
                return value
    return None


def _extract_credits(text: str) -> int | None:
    m = re.search(r"credite?\s*[:\-]?\s*(\d{1,2})", text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_bibliography(text: str) -> list[str] | None:
    section = _match_block(
        text,
        [
            r"bibliografi[ea]\s*[:\-]?\s*(.+?)(?:\n\s*10\.|\n\s*evaluare|$)",
            r"repere bibliografice\s*[:\-]?\s*(.+?)(?:\n\s*10\.|\n\s*evaluare|$)",
        ],
    )
    if not section:
        return None

    items = [re.sub(r"^[\-•\d\.)\s]+", "", line).strip() for line in section.splitlines()]
    items = [item for item in items if item]
    return items or None


def _extract_competencies(text: str) -> list[str] | None:
    matches = re.findall(r"\b(CP\s*\d+|CT\s*\d+)\b[^\n]*", text, flags=re.IGNORECASE)
    cleaned = [m.upper().replace(" ", "") for m in matches]
    return sorted(set(cleaned)) or None


def _extract_evaluation(text: str) -> list[EvaluationItem] | None:
    items: list[EvaluationItem] = []
    for line in text.splitlines():
        if "%" not in line:
            continue
        m = re.search(r"([A-Za-zĂÂÎȘȚăâîșț \-/]+?)\s*(\d{1,3})\s*%", line)
        if not m:
            continue
        label = re.sub(r"\s+", " ", m.group(1)).strip(" -:")
        weight = float(m.group(2))
        if label:
            items.append(EvaluationItem(label=label, weight=weight))

    return items or None


def parse_ocr_text(text: str) -> ParsedDocument:
    normalized = text.replace("\r\n", "\n")

    title = _match_block(
        normalized,
        [
            r"denumirea\s+disciplinei\s*[:\-]?\s*(.+)",
            r"disciplina\s*[:\-]?\s*(.+)",
            r"^\s*fi[șs]a\s+disciplinei\s*(.+)$",
        ],
    )

    objectives = _match_block(
        normalized,
        [
            r"obiectivele\s+disciplinei.*?\n(.+?)(?:\n\s*8\.|\n\s*conținuturi|$)",
            r"obiectivul\s+general.*?\n(.+?)(?:\n\s*8\.|\n\s*conținuturi|$)",
        ],
    )

    parsed = ParsedDocument(
        title=title,
        credits=_extract_credits(normalized),
        objectives=objectives,
        bibliography=_extract_bibliography(normalized),
        evaluation=_extract_evaluation(normalized),
        competencies=_extract_competencies(normalized),
        evidence={
            "text_length": len(normalized),
            "parser": "deterministic-regex-v1",
        },
    )
    return parsed
