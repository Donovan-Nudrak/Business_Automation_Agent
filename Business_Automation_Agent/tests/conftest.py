"""Shared pytest fixtures for Business Automation Agent."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from stripe import WebhookSignature

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/business_automation_test",
)
TEST_STRIPE_WEBHOOK_SECRET = "whsec_test_secret_for_pytest_suite"


def _configure_test_environment() -> None:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["STRIPE_WEBHOOK_SECRET"] = TEST_STRIPE_WEBHOOK_SECRET
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
    os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
    os.environ.setdefault("RESEND_API_KEY", "re_test_key")
    os.environ.setdefault("RESEND_FROM_EMAIL", "test@example.com")
    os.environ.setdefault("ALERT_EMAIL", "alerts@example.com")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    os.environ.setdefault("AWS_S3_BUCKET", "test-bucket")
    os.environ.setdefault("AWS_REGION", "us-east-1")

    from app.core.config import get_settings

    get_settings.cache_clear()


def _ensure_test_database_exists() -> None:
    if not TEST_DATABASE_URL.startswith("postgresql"):
        return

    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[-1]
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()


_configure_test_environment()
_ensure_test_database_exists()

from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402,F401
    Action,
    Customer,
    Decision,
    Event,
    Report,
    User,
    Workflow,
)


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session, client: TestClient) -> dict[str, Any]:
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass123!"
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role="admin",
        active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": str(user.id),
    }


@pytest.fixture
def auth_user(db_session: Session, client: TestClient) -> dict[str, Any]:
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass123!"
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role="operator",
        active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": str(user.id),
    }


@pytest.fixture
def mock_celery_delay(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def _delay(event_id: str):
        calls.append(event_id)

    monkeypatch.setattr(
        "app.tasks.event_tasks.process_event_task.delay",
        _delay,
    )
    return calls


def build_stripe_event(stripe_event_id: str | None = None) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:12]
    return {
        "id": stripe_event_id or f"evt_test_{suffix}",
        "object": "event",
        "api_version": "2024-11-20.acacia",
        "created": int(time.time()),
        "livemode": False,
        "pending_webhooks": 1,
        "type": "payment_intent.payment_failed",
        "data": {
            "object": {
                "id": f"pi_test_{suffix}",
                "object": "payment_intent",
                "amount": 10000,
                "currency": "usd",
                "status": "requires_payment_method",
                "customer": f"cus_test_{suffix}",
            }
        },
    }


def sign_stripe_payload(payload_bytes: bytes, secret: str = TEST_STRIPE_WEBHOOK_SECRET) -> str:
    timestamp = int(time.time())
    payload_str = payload_bytes.decode("utf-8")
    signed_payload = f"{timestamp}.{payload_str}"
    signature = WebhookSignature._compute_signature(signed_payload, secret)
    return f"t={timestamp},v1={signature}"


def post_stripe_webhook(
    client: TestClient,
    stripe_event: dict[str, Any],
    *,
    include_signature: bool = True,
    signature: str | None = None,
) -> Any:
    payload_bytes = json.dumps(stripe_event, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if include_signature:
        headers["Stripe-Signature"] = signature or sign_stripe_payload(payload_bytes)
    return client.post("/webhooks/stripe", content=payload_bytes, headers=headers)
