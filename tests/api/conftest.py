from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-thirty-two-bytes")
    get_settings.cache_clear()

    from app.db import session as db_session

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        db_session,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )

    from app.api.main import app

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def register_and_login(client: TestClient) -> Callable[[str], str]:
    def _register_and_login(email: str) -> str:
        password = "correct horse battery staple"
        register_response = client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        return login_response.json()["access_token"]

    return _register_and_login
