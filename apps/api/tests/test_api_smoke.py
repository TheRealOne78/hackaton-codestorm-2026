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
