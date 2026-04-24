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
