import uuid

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User


def test_register_success(client: TestClient, admin_user: dict):
    email = f"register_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass123!"},
        headers=admin_user["headers"],
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "operator"
    assert "id" in data


def test_login_success(client: TestClient, auth_user: dict):
    response = client.post(
        "/auth/login",
        json={"email": auth_user["email"], "password": auth_user["password"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_valid_token_allows_protected_route(client: TestClient, auth_user: dict):
    response = client.get("/events", headers=auth_user["headers"])

    assert response.status_code == 200
    assert "items" in response.json()


def test_invalid_token_returns_401(client: TestClient):
    response = client.get(
        "/events",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_inactive_user_returns_403(client: TestClient, db_session: Session):
    email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("SecurePass123!"),
        role="operator",
        active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


def test_duplicate_email_returns_error(
    client: TestClient,
    auth_user: dict,
    admin_user: dict,
):
    response = client.post(
        "/auth/register",
        json={"email": auth_user["email"], "password": "AnotherPass123!"},
        headers=admin_user["headers"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_inactive_user_token_returns_403(client: TestClient, db_session: Session):
    user = User(
        email=f"inactive_token_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("SecurePass123!"),
        role="operator",
        active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = jwt.encode(
        {"sub": str(user.id), "exp": 9999999999},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get(
        "/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
