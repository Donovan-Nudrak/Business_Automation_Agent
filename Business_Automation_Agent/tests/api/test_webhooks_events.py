import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.event import Event
from tests.conftest import build_stripe_event, post_stripe_webhook


def test_webhook_without_signature_returns_400(client: TestClient):
    stripe_event = build_stripe_event()
    response = post_stripe_webhook(client, stripe_event, include_signature=False)

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Stripe-Signature header"


def test_webhook_with_invalid_signature_returns_400(client: TestClient):
    stripe_event = build_stripe_event()
    response = post_stripe_webhook(
        client,
        stripe_event,
        signature="t=1234567890,v1=invalidsignature",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Stripe signature"


def test_valid_webhook_returns_201_and_creates_event(
    client: TestClient,
    db_session: Session,
    mock_celery_delay: list[str],
):
    stripe_event = build_stripe_event()
    response = post_stripe_webhook(client, stripe_event)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["event_id"]

    event = db_session.get(Event, uuid.UUID(data["event_id"]))
    assert event is not None
    assert event.source == "stripe"
    assert event.event_type == "payment_intent.payment_failed"
    assert event.stripe_event_id == stripe_event["id"]
    assert len(mock_celery_delay) == 1
    assert mock_celery_delay[0] == data["event_id"]


def test_duplicate_webhook_returns_already_processed(
    client: TestClient,
    mock_celery_delay: list[str],
):
    stripe_event = build_stripe_event(f"evt_duplicate_{uuid.uuid4().hex[:8]}")
    first = post_stripe_webhook(client, stripe_event)
    second = post_stripe_webhook(client, stripe_event)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"
    assert second.json()["event_id"] == first.json()["event_id"]
    assert len(mock_celery_delay) == 1


def test_manual_event_requires_jwt(client: TestClient, auth_user: dict):
    payload = {
        "event_type": "manual.test",
        "source": "manual",
        "payload": {"note": "manual event"},
    }

    unauthorized = client.post("/events", json=payload)
    assert unauthorized.status_code == 401

    authorized = client.post("/events", json=payload, headers=auth_user["headers"])
    assert authorized.status_code == 201
    assert authorized.json()["status"] == "received"
