import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def api() -> TestClient:
    return TestClient(create_app())  # không cần DB


def test_english_levels_listed_in_yaml_order(api):
    response = api.get("/api/v1/languages/en")

    assert response.status_code == 200
    body = response.json()
    assert body["language_code"] == "en"
    assert body["display_name_vi"] == "Tiếng Anh"
    assert [level["code"] for level in body["levels"]] == ["A1", "A2", "B1"]
    assert body["levels"][0]["display_name_vi"] == "Sơ cấp"
    assert "placement" not in body and "thresholds" not in response.text


@pytest.mark.parametrize("code", ["xx", "EN", "..%2F.env"])
def test_unknown_or_unsafe_language_returns_404(api, code):
    response = api.get(f"/api/v1/languages/{code}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] in {"language_not_found", "not_found"}


def test_levels_endpoint_needs_no_token(api):
    assert api.get("/api/v1/languages/en", headers={}).status_code == 200
