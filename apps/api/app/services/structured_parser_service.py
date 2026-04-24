"""Structured parser for Plan de Învățământ and Fișa Disciplinei payloads."""

from __future__ import annotations

import re
from typing import Any, Literal

from app.schemas.blockers import OcrTable, ParsedDocument
from app.services.parse_service import parse_ocr_text
from app.services.sanitizer_service import detect_document_type_sanitized


def _norm(text: str) -> str:
    """Normalize whitespace for stable downstream parsing."""
    return re.sub(r"\s+", " ", text).strip()


def detect_document_type(text: str) -> Literal["fisa", "plan"]:
    """Infer document type from lexical markers."""
    return detect_document_type_sanitized(text)


def _extract_first(text: str, pattern: str) -> str | None:
    """Return first regex capture normalized as a single-line value."""
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    return _norm(m.group(1))


def _extract_int(text: str, pattern: str) -> int | None:
    """Return first integer capture for a pattern."""
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _is_header_or_total_row(row: list[str]) -> bool:
    """Detect non-data rows in parsed plan tables."""
    line = _norm(" ".join(row)).lower()
    header_tokens = [
        "discipline obligatorii",
        "discipline optionale",
        "semestrul",
        "codul",
        "total ore",
        "total",
        "crt",
    ]
    return any(token in line for token in header_tokens)


def _extract_course_name(row: list[str]) -> str | None:
    """Extract best-effort course title from a noisy table row."""
    if not row:
        return None

    cleaned_cells: list[str] = []
    for cell in row:
        c = _norm(cell)
        if not c:
            continue
        if re.search(r"\b[A-Z]{1,4}\d{2,3}\s*-?\s*ID\b", c):
            continue
        if re.fullmatch(r"[\d\s\|/%+\-]+", c):
            continue
        if c.upper() in {"DF", "DS", "DC", "DO", "DI", "E", "C", "V", "AR", "COL", "PR"}:
            continue
        cleaned_cells.append(c)

    if not cleaned_cells:
        return None

    line = max(cleaned_cells, key=len)
    line = re.sub(r"^\d+\.?\s*", "", line)
    line = re.sub(r"^(?:Nr\.?|crt\.?)\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\b(DF|DS|DC|DO|DI)\b.*$", "", line).strip()
    line = re.sub(r"\s{2,}", " ", line).strip()

    if len(line) < 3:
        return None

    # Avoid keeping pure numeric/admin lines
    if re.fullmatch(r"[\d\s\|\-+=%]+", line):
        return None

    return line[:180]


def _extract_course_code(row: list[str]) -> str | None:
    """Extract course code from a row when present."""
    line = _norm(" ".join(row))
    m = re.search(r"\b([A-Z]{1,4}\d{2,3}\s*-?\s*ID|[A-Z]{1,4}\d{2,3}-[A-Z]{1,3})\b", line)
    if not m:
        return None
    return m.group(1).replace(" ", "")


def _extract_verification_form(row: list[str]) -> str | None:
    """Extract verification form token (E/C/V/AR/COL/PR)."""
    line = _norm(" ".join(row))
    m = re.search(r"\b(E|C|V|AR|COL|PR)\b", line, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1).upper()


def _extract_credits_guess(row: list[str]) -> int | None:
    """Infer credits from small numeric tokens in a row."""
    nums = [int(x) for x in re.findall(r"\b\d{1,3}\b", " ".join(row))]
    small = [n for n in nums if 1 <= n <= 10]
    return small[-1] if small else None


def _extract_year_context(line: str) -> int | None:
    """Extract year marker (roman or arabic) from a text line."""
    low = line.lower()
    roman_map = {"i": 1, "ii": 2, "iii": 3, "iv": 4}
    m = re.search(r"anul\s+([ivxl]+|\d+)", low)
    if not m:
        return None
    token = m.group(1).replace("l", "i")
    if token.isdigit():
        return int(token)
    return roman_map.get(token)


def _extract_courses_from_text(text: str, year_guess: int | None) -> list[dict[str, Any]]:
    """Extract plan courses from numbered text lines as primary source."""
    records: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = _norm(raw_line)
        if not line:
            continue
        if not re.match(r"^\d{1,2}\.?\s*", line):
            continue

        line_body = re.sub(r"^\d{1,2}\.?\s*\|?\s*", "", line)
        code = _extract_course_code([line_body])
        verification = _extract_verification_form([line_body])

        # Prefer name before category token (DF/DS/DC/DO/DI) or before code.
        name: str | None = None
        m_cat = re.search(r"^(.*?)(?:\s+\b(?:DF|DS|DC|DO|DI)\b)", line_body)
        if m_cat:
            name = _norm(m_cat.group(1))
        elif code:
            name = _norm(line_body.split(code, 1)[0])
        else:
            name = _norm(line_body)

        if not name or len(name) < 3:
            continue
        if re.fullmatch(r"[\d\s\|/%+\-]+", name):
            continue

        credits_guess = _extract_credits_guess([line_body])
        records.append(
            {
                "name": name[:180],
                "code": code,
                "verification": verification,
                "credits_guess": credits_guess,
                "year_guess": year_guess,
                "raw": [line],
            }
        )

    return records


def parse_plan(text: str, tables: list[OcrTable]) -> dict[str, Any]:
    """Parse Plan de Învățământ text and OCR table hints into structured data."""
    program_name = _extract_first(text, r"programul\s+de\s+studii[^:\n]*:\s*([^\n]+)")
    faculty = _extract_first(text, r"facultatea\s*:\s*([^\n]+)")
    domain_fundamental = _extract_first(text, r"domeniul\s+fundamental\s*:\s*([^\n]+)")
    domain_licenta = _extract_first(text, r"domeniul\s+de\s+licen[țt]?[aă]\s*:\s*([^\n]+)")
    study_form = _extract_first(text, r"forma\s+de\s+[îi]nv[ăa]?[țt]?[aă]m[âa]nt\s*:\s*([^\n]+)")
    duration_years = _extract_int(text, r"durata\s+studiilor\s*:\s*(\d+)")
    valid_year = _extract_first(text, r"valabil\s+[îi]n\s+anul\s+universitar\s*([^\n]+)")

    current_year: int | None = None
    courses: list[dict[str, Any]] = []

    for line in text.splitlines():
        y = _extract_year_context(line)
        if y is not None:
            current_year = y

    courses = _extract_courses_from_text(text, current_year)

    # Fallback/augmentation from table rows when text extraction yields too few courses.
    if len(courses) < 4:
        for table in tables:
            for row in table.rows:
                if _is_header_or_total_row(row):
                    continue

                name = _extract_course_name(row)
                if not name:
                    continue

                record = {
                    "name": name,
                    "code": _extract_course_code(row),
                    "verification": _extract_verification_form(row),
                    "credits_guess": _extract_credits_guess(row),
                    "year_guess": current_year,
                    "raw": row,
                }
                courses.append(record)

    if not courses:
        for line in text.splitlines():
            line_n = _norm(line)
            if not re.match(r"^\d+\.?", line_n):
                continue
            numbers = [int(x) for x in re.findall(r"\b\d{1,3}\b", line_n)]
            course = {
                "name": re.sub(r"^\d+\.?\s*", "", line_n),
                "code": _extract_course_code([line_n]),
                "verification": _extract_verification_form([line_n]),
                "credits_guess": (next((n for n in reversed(numbers) if 1 <= n <= 10), None) if numbers else None),
                "year_guess": current_year,
                "raw": [line_n],
            }
            courses.append(course)

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for course in courses:
        key = (course.get("name") or "", course.get("code"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(course)
    courses = deduped

    return {
        "doc_type": "plan",
        "metadata": {
            "program_name": program_name,
            "faculty": faculty,
            "domain_fundamental": domain_fundamental,
            "domain_licenta": domain_licenta,
            "study_form": study_form,
            "duration_years": duration_years,
            "valid_year": valid_year,
        },
        "courses": courses,
        "totals": {
            "courses_detected": len(courses),
        },
        "evidence": {
            "tables_count": len(tables),
            "parser": "structured-plan-v1",
        },
    }


def parse_fisa(text: str) -> dict[str, Any]:
    """Parse Fișa text via baseline parser and attach structured metadata."""
    # Reuse existing deterministic parser and annotate with document type.
    parsed: ParsedDocument = parse_ocr_text(text)
    data = parsed.model_dump()
    data["doc_type"] = "fisa"
    data["evidence"] = {
        **(data.get("evidence") or {}),
        "parser": "structured-fisa-v1",
    }
    return data


def parse_structured(
    text: str,
    tables: list[OcrTable] | None = None,
    document_type: Literal["auto", "fisa", "plan"] = "auto",
) -> dict[str, Any]:
    """Dispatch to plan/fisa parser with optional automatic type detection."""
    selected = detect_document_type(text) if document_type == "auto" else document_type
    tables = tables or []

    if selected == "plan":
        return parse_plan(text, tables)
    return parse_fisa(text)
