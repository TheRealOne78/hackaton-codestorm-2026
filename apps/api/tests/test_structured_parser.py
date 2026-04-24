"""Unit tests for plan/fisa structured parser routing and output shape."""

from app.schemas.blockers import OcrTable
from app.services.structured_parser_service import detect_document_type, parse_structured


def test_detect_document_type_plan() -> None:
    text = "PLAN DE INVATAMANT\nValabil in anul universitar 2025-2026"
    assert detect_document_type(text) == "plan"


def test_parse_structured_plan_with_tables() -> None:
    text = (
        "PLAN DE INVATAMANT\n"
        "Facultatea: Matematica si Informatica\n"
        "Programul de studii universitare de licenta: Informatica\n"
        "Durata studiilor: 3 ani\n"
        "ANUL II\n"
    )
    tables = [
        OcrTable(
            page_number=1,
            rows=[
                ["Nr.", "Discipline obligatorii (impuse)", "Codul", "Semestrul I"],
                ["1.", "Algoritmica grafurilor", "IT31-ID", "E", "5"],
                ["2.", "Baze de date", "IT34-ID", "E", "5"],
            ],
        )
    ]

    parsed = parse_structured(text=text, tables=tables, document_type="plan")

    assert parsed["doc_type"] == "plan"
    assert parsed["metadata"]["program_name"] == "Informatica"
    assert parsed["totals"]["courses_detected"] >= 2
    assert parsed["courses"][0]["credits_guess"] == 5


def test_parse_structured_fisa_uses_existing_parser() -> None:
    text = "Denumirea disciplinei: Algoritmi\nCredite: 6\nCP1 Programare"

    parsed = parse_structured(text=text, tables=[], document_type="fisa")

    assert parsed["doc_type"] == "fisa"
    assert parsed["credits"] == 6
