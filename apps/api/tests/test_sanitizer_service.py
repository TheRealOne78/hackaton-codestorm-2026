"""Unit tests for OCR sanitization and table dictionary extraction."""

from app.schemas.blockers import OcrTable
from app.services.sanitizer_service import sanitize_payload


def test_sanitize_payload_detects_plan_and_extracts_rows() -> None:
    text = (
        "Universitatea X\n"
        "ANUL II\n"
        "Nr, Discipline obligatorii (impuse)\n"
        "1. Algoritmica grafurilor DF IT31-ID E 5\n"
    )
    tables = [
        OcrTable(
            page_number=1,
            rows=[
                ["Nr", "Discipline obligatorii (impuse)", "Codul", "Semestrul I"],
                ["1.", "Algoritmica grafurilor", "IT31-ID", "E", "5"],
            ],
        )
    ]

    result = sanitize_payload(text=text, tables=tables, doc_type="auto")

    assert result["document_type"] == "plan"
    assert result["stats"]["mandatory_rows"] >= 1
    assert result["rows"]["mandatory"][0]["name"].startswith("Algoritmica")


def test_sanitize_payload_removes_signature_lines() -> None:
    text = "Conf. dr. Ion Popescu\nCoordonatorul CIDIFR\nText util\n"
    result = sanitize_payload(text=text, tables=[], doc_type="fisa")

    assert "Text util" in result["clean_text"]
    assert any("Conf. dr." in line for line in result["removed_lines"])


def test_sanitize_payload_plan_line_parser_filters_noisy_rows() -> None:
    text = (
        "ANUL II\n"
        "Nr, Discipline obligatorii (impuse)\n"
        "1. | Algoritmica grafurilor DF | ITT31-ID | 28 28 | 69 E | 5\n"
        "Nr, Discipline optionale (la alegere)\n"
        "12, - 0S 28 28 | 69 C | 5\n"
    )
    result = sanitize_payload(text=text, tables=[], doc_type="plan")

    mandatory = result["rows"]["mandatory"]
    optional = result["rows"]["optional"]

    assert len(mandatory) == 1
    assert mandatory[0]["code"] == "IT31-ID"
    assert optional == []
