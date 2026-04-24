"""Unit tests for deterministic parsing and validation rules."""

from app.services.parse_service import parse_ocr_text
from app.services.validation_service import validate_document


SAMPLE_TEXT = """
FIȘA DISCIPLINEI
Denumirea disciplinei: Algoritmi si Structuri de Date
Credite: 6

7. Obiectivele disciplinei
Formarea gandirii algoritmice si a abilitatilor de implementare.

Bibliografie:
- Cormen et al. Introduction to Algorithms
- Sedgewick, Algorithms

10. Evaluare
Examen final 70%
Activitate laborator 30%

CP1 Programarea in limbaje de nivel inalt
CT1 Munca in echipa
""".strip()


def test_parse_extracts_basic_fields() -> None:
    parsed = parse_ocr_text(SAMPLE_TEXT)

    assert parsed.title is not None
    assert parsed.credits == 6
    assert parsed.bibliography is not None and len(parsed.bibliography) >= 2
    assert parsed.evaluation is not None and len(parsed.evaluation) == 2
    assert parsed.competencies is not None and "CP1" in parsed.competencies


def test_validation_detects_weight_limit_warning() -> None:
    parsed = parse_ocr_text(SAMPLE_TEXT)
    result = validate_document(parsed, max_individual_weight=60)

    assert len(result.errors) == 0
    assert any(issue.code == "EVAL_WEIGHT_ABOVE_LIMIT" for issue in result.warnings)


def test_validation_detects_missing_mandatory_sections() -> None:
    parsed = parse_ocr_text("Disciplina: Test\nCredite: 5")
    result = validate_document(parsed)

    assert any(issue.code == "MISSING_FIELD" for issue in result.errors)
