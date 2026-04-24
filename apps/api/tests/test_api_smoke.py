from fastapi.testclient import TestClient

from app.main import app


def test_parse_endpoint_smoke() -> None:
    client = TestClient(app)
    response = client.post("/parse", json={"text": "Disciplina: Test\nCredite: 5"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["credits"] == 5


def test_validate_endpoint_smoke() -> None:
    client = TestClient(app)
    response = client.post(
        "/validate",
        json={
            "document": {
                "title": "Test",
                "credits": 5,
                "objectives": "Obj",
                "bibliography": ["Book"],
                "evaluation": [{"label": "Exam", "weight": 100}],
                "competencies": ["CP1"],
                "evidence": {},
            },
            "max_individual_weight": 60,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]["errors"]) == 0
    assert len(payload["data"]["warnings"]) == 1


def test_ocr_endpoint_with_text_upload() -> None:
    client = TestClient(app)
    response = client.post(
        "/ocr",
        files={"file": ("sample.txt", b"Denumirea disciplinei: Test\nCredite: 5", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["source_type"] == "text"
    assert payload["data"]["needs_ocr"] is False
    assert payload["data"]["engine"] == "raw-text"


def test_pipeline_endpoint_with_text_upload() -> None:
    client = TestClient(app)
    sample_text = (
        b"Denumirea disciplinei: Test\n"
        b"Credite: 5\n"
        b"Obiectivele disciplinei\n"
        b"Obj\n"
        b"Bibliografie:\n"
        b"Book 1\n"
        b"Evaluare\n"
        b"Examen 100%\n"
        b"CP1\n"
    )
    response = client.post(
        "/pipeline/run-blockers",
        files={
            "file": (
                "sample.txt",
                sample_text,
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "ocr" in payload["data"]
    assert "parsed" in payload["data"]
    assert "validation" in payload["data"]


def test_parse_structured_plan_endpoint_smoke() -> None:
    client = TestClient(app)
    response = client.post(
        "/parse-structured",
        json={
            "text": (
                "PLAN DE INVATAMANT\n"
                "Programul de studii universitare de licenta: Informatica\n"
                "Durata studiilor: 3 ani\n"
                "ANUL II\n"
            ),
            "tables": [
                {
                    "page_number": 1,
                    "rows": [
                        ["1.", "Algoritmica grafurilor", "IT31-ID", "E", "5"],
                        ["2.", "Baze de date", "IT34-ID", "E", "5"],
                    ],
                }
            ],
            "document_type": "plan",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["doc_type"] == "plan"
    assert payload["data"]["totals"]["courses_detected"] >= 2


def test_pipeline_structured_endpoint_with_text_upload() -> None:
    client = TestClient(app)
    response = client.post(
        "/pipeline/run-structured?document_type=plan",
        files={
            "file": (
                "plan.txt",
                b"PLAN DE INVATAMANT\nProgramul de studii universitare de licenta: Informatica\nANUL I\n1. Algoritmi 5",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["parsed"]["doc_type"] == "plan"
