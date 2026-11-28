"""GET /api/v1/system/status: chỉ thông tin không bí mật (dùng cho Streamlit console)."""
from app.core.config import get_settings


def test_status_reports_modes_limits_and_database_without_secrets(client):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["llm_provider"] in {"fake", "gemini"} and body["rag_mode"] == "llm_only"  # conftest ép llm_only
    assert body["database"] == "ok" and body["qdrant"] in {"ok", "unavailable", "error"}
    assert body["limits"]["chat_user_per_minute"] == get_settings().chat_user_per_minute
    settings = get_settings()
    secrets = [settings.jwt_secret.get_secret_value() if hasattr(settings.jwt_secret, "get_secret_value") else str(settings.jwt_secret),
               settings.postgres_password.get_secret_value() if hasattr(settings.postgres_password, "get_secret_value") else str(settings.postgres_password)]
    for secret in filter(None, secrets):
        assert secret not in response.text
    for word in ("password", "secret", "api_key", "postgresql", "6333"):
        assert word not in response.text.lower()
