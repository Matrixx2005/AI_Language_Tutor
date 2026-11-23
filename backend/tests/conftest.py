"""Fixture dùng chung. Test DB chạy trên POSTGRES_TEST_DB, không bao giờ chạm DB chính."""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.limits import AppLimits
from app.db.session import get_db
from app.main import create_app


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    try:
        url = settings.database_url(test=True)
    except RuntimeError as exc:
        pytest.skip(f"Không có cấu hình DB test: {exc}")
    assert url.database == settings.postgres_test_db != settings.postgres_db

    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect():
            pass
    except OperationalError:
        engine.dispose()
        pytest.skip("PostgreSQL chưa chạy (docker compose up -d)")
    if not inspect(engine).has_table("users"):
        engine.dispose()
        pytest.fail("DB test chưa migrate: cd backend && alembic -x db=test upgrade head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Mỗi test một transaction, rollback khi kết thúc: DB test luôn sạch."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API client dùng DB test; session.commit() trong service chỉ giải phóng savepoint."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client


class FakeClock:
    """Đồng hồ đơn điệu giả cho bộ giới hạn: test tua thời gian thay vì ngủ thật."""

    def __init__(self, start: float = 10_000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def limited(client: TestClient, monkeypatch):
    """Đặt ngưỡng riêng cho test: `clock = limited(chat_user_per_minute=2, ...)`.

    Thay AppLimits của app (đồng hồ giả) và Settings mà service/route đọc; không đụng .env."""

    def _apply(**overrides) -> FakeClock:
        settings = get_settings().model_copy(update=overrides)
        clock = FakeClock()
        client.app.state.limits = AppLimits(settings, clock=clock)
        monkeypatch.setattr("app.services.chat.get_settings", lambda: settings)
        monkeypatch.setattr("app.api.routes.auth.get_settings", lambda: settings)
        return clock

    return _apply


@pytest.fixture
def register_and_login(client: TestClient):
    """Đăng ký rồi đăng nhập, trả header Authorization."""

    def _register_and_login(
        email: str = "learner@example.com", password: str = "mat-khau-an-toan"
    ) -> dict[str, str]:
        assert client.post(
            "/api/v1/auth/register", json={"email": email, "password": password}
        ).status_code == 201
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _register_and_login
