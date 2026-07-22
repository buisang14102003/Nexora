import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import verify_password
from app.db.models import User


def test_register_creates_user_with_hashed_password(client: TestClient) -> None:
    from app.db import session as db_session

    response = client.post(
        "/auth/register",
        json={"email": "user@example.test", "password": "correct horse battery staple"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.test"

    with db_session.SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "user@example.test"))

    assert user is not None
    assert verify_password("correct horse battery staple", user.password_hash)


def test_login_returns_bearer_token_for_valid_credentials(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.test", "password": "correct horse battery staple"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "user@example.test", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_registration_and_login_normalize_email(client: TestClient) -> None:
    registration = client.post(
        "/auth/register",
        json={"email": "  User@Example.Test  ", "password": "correct horse battery staple"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "USER@EXAMPLE.TEST", "password": "correct horse battery staple"},
    )

    assert registration.status_code == 201
    assert registration.json()["email"] == "user@example.test"
    assert login.status_code == 200


def test_token_without_expiry_is_rejected(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.test", "password": "correct horse battery staple"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.test", "password": "correct horse battery staple"},
    )
    payload = jwt.decode(
        login_response.json()["access_token"], options={"verify_signature": False}
    )
    token_without_expiry = jwt.encode(
        {"sub": payload["sub"]},
        "test-secret-with-at-least-thirty-two-bytes",
        algorithm="HS256",
    )

    response = client.get(
        "/workspaces", headers={"Authorization": f"Bearer {token_without_expiry}"}
    )

    assert response.status_code == 401
