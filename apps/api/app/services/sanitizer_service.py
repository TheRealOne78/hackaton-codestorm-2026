"""Sanitization engine for OCR text and table rows before structured parsing."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from app.schemas.blockers import OcrTable

DOC_TYPE = Literal["auto", "fisa", "plan"]


REPLACEMENTS: dict[str, str] = {
    "Informatics": "Informatica",
    "fnv&tdmant": "invatamant",
    "inv&tdmant": "invatamant",
    "Moqern": "Modern",
    "disciptinel": "disciplinelor",
    "lOT": "IoT",
    "lon": "Ion",
}

COLUMN_ALIASES: dict[str, str] = {
    "crt": "index",
    "nr": "index",
    "disciplina": "course",
    "discipline": "course",
    "codul": "code",
    "cod": "code",
    "fv": "verification",
    "forma verificare": "verification",
    "cr": "credits",
    "credite": "credits",
    "al": "hours_al",
    "at": "hours_at",
    "tc": "hours_tc",
    "aa": "hours_aa",
    "si": "hours_si",
}


def _ascii_fold(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFKC", text)
    for src, dst in REPLACEMENTS.items():
        value = value.replace(src, dst)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def detect_document_type_sanitized(text: str) -> Literal["fisa", "plan"]:
    """Infer document type using normalized OCR text."""
    low = _ascii_fold(_norm(text)).lower()
    if "plan de invatamant" in low:
        return "plan"
    if "fisa disciplinei" in low:
        return "fisa"

    if "discipline obligatorii" in low and ("semestr" in low or "anul" in low):
        return "plan"
    return "fisa"


def sanitize_text_lines(text: str, doc_type: DOC_TYPE = "auto") -> dict[str, Any]:
    """Clean OCR full_text and remove obvious non-content footer/signature noise."""
    selected = detect_document_type_sanitized(text) if doc_type == "auto" else doc_type
    lines = [_norm(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    removed: list[str] = []
    cleaned: list[str] = []

    footer_patterns = [
        r"^conf\.? dr\.?",
        r"^directorul",
        r"^decanul",
        r"^coordonatorul",
        r"^conform cu",
        r"^f\d{2}\.\d",
    ]

    for line in lines:
        low = _ascii_fold(line).lower()
        if any(re.search(pat, low) for pat in footer_patterns):
            removed.append(line)
            continue

        # Fix common OCR code corruption: -10 -> -ID in course codes
        line = re.sub(r"\b([A-Z]{1,4}\d{2,3})-10\b", r"\1-ID", line)
        line = re.sub(r"\b0P(\d{2})-ID\b", r"OP\1-ID", line)

        cleaned.append(line)

    return {
        "document_type": selected,
        "clean_text": "\n".join(cleaned),
        "removed_lines": removed,
        "stats": {
            "input_lines": len(lines),
            "removed_lines": len(removed),
            "kept_lines": len(cleaned),
        },
    }


def _is_header_row(row: list[str]) -> bool:
    line = _ascii_fold(_norm(" ".join(row))).lower()
    return ("disciplina" in line or "discipline" in line) and ("semestr" in line or "cod" in line)


def _normalize_header_cells(row: list[str]) -> list[dict[str, str]]:
    headers: list[dict[str, str]] = []
    for cell in row:
        c = _ascii_fold(_norm(cell)).lower().strip(".,:; ")
        if not c:
            continue
        mapped = None
        for key, alias in COLUMN_ALIASES.items():
            if key in c:
                mapped = alias
                break
        headers.append({"raw": cell, "normalized": c, "alias": mapped or "unknown"})
    return headers


def _classify_row(row: list[str]) -> Literal["mandatory", "optional", "other"]:
    line = _ascii_fold(_norm(" ".join(row))).lower()
    if "discipline obligatorii" in line:
        return "mandatory"
    if "discipline optionale" in line:
        return "optional"
    return "other"


def _extract_course_row_dict(row: list[str]) -> dict[str, Any] | None:
    line = _norm(" ".join(row))

    if not re.search(r"\b\d+\b", line):
        return None
    if "total ore" in _ascii_fold(line).lower():
        return None
    low = _ascii_fold(line).lower()
    if low.startswith("crt") or "cy:" in low or "disciplinel" in low:
        return None

    index_match = re.match(r"\s*(\d{1,2})\.?", line)
    index = int(index_match.group(1)) if index_match else None

    code_match = re.search(r"\b([A-Z]{1,4}\d{2,3}\s*-?\s*ID)\b", line)
    code = code_match.group(1).replace(" ", "") if code_match else None

    ver_match = re.search(r"\b(E|C|V|AR|COL|PR)\b", line, flags=re.IGNORECASE)
    verification = ver_match.group(1).upper() if ver_match else None

    credits_candidates = [int(v) for v in re.findall(r"\b\d{1,3}\b", line)]
    credits = next((n for n in reversed(credits_candidates) if 1 <= n <= 10), None)

    # Name heuristic: remove prefix index, remove known code/category tail.
    name = re.sub(r"^\s*\d{1,2}\.?\s*\|?\s*", "", line)
    name = re.sub(r"\b(DF|DS|DC|DO|DI)\b.*$", "", name).strip()
    if code:
        name = name.split(code, 1)[0].strip() if code in name else name
    name = name.strip("| -")
    name = _norm(name)

    if len(name) < 3:
        return None

    return {
        "index": index,
        "name": name,
        "code": code,
        "verification": verification,
        "credits_guess": credits,
        "raw": row,
    }


def sanitize_tables(tables: list[OcrTable]) -> dict[str, Any]:
    """Convert OCR table rows into normalized headers and row dictionaries."""
    headers: dict[str, list[dict[str, str]]] = {"mandatory": [], "optional": []}
    rows: dict[str, list[dict[str, Any]]] = {"mandatory": [], "optional": []}

    current_section: Literal["mandatory", "optional"] | None = None

    for table in tables:
        for row in table.rows:
            section_tag = _classify_row(row)
            if section_tag in {"mandatory", "optional"}:
                current_section = section_tag

            if _is_header_row(row):
                normalized_header = _normalize_header_cells(row)
                if current_section in {"mandatory", "optional"}:
                    headers[current_section] = normalized_header
                continue

            if current_section not in {"mandatory", "optional"}:
                continue

            course = _extract_course_row_dict(row)
            if course:
                rows[current_section].append(course)

    # Deduplicate by name+code
    for key in ("mandatory", "optional"):
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str | None]] = set()
        for item in rows[key]:
            uniq = (item.get("name", ""), item.get("code"))
            if uniq in seen:
                continue
            seen.add(uniq)
            deduped.append(item)
        rows[key] = deduped

    return {
        "headers": headers,
        "rows": rows,
        "totals": {
            "mandatory_rows": len(rows["mandatory"]),
            "optional_rows": len(rows["optional"]),
        },
        "dictionaries": {
            "replacements": REPLACEMENTS,
            "column_aliases": COLUMN_ALIASES,
        },
    }


def sanitize_payload(text: str, tables: list[OcrTable], doc_type: DOC_TYPE = "auto") -> dict[str, Any]:
    """Sanitize OCR payload and return normalized text + tabular dictionaries."""
    text_part = sanitize_text_lines(text, doc_type=doc_type)
    table_part = sanitize_tables(tables)

    return {
        "document_type": text_part["document_type"],
        "clean_text": text_part["clean_text"],
        "removed_lines": text_part["removed_lines"],
        "stats": {
            **text_part["stats"],
            **table_part["totals"],
        },
        "headers": table_part["headers"],
        "rows": table_part["rows"],
        "dictionaries": table_part["dictionaries"],
    }
