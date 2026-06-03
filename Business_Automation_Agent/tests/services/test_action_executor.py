import uuid
from unittest.mock import MagicMock

import pytest

from app.action_executor.action_executor import ActionExecutor
from app.models.decision import Decision
from app.models.event import Event
from app.models.report import Report
from app.repositories.action_repository import ActionRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.event_repository import EventRepository


@pytest.fixture
def decision_with_event(db_session):
    event_repo = EventRepository(db_session)
    decision_repo = DecisionRepository(db_session)

    event = event_repo.create_event(
        event_type="payment_intent.payment_failed",
        source="stripe",
        payload={"type": "payment_intent.payment_failed"},
        status="processing",
    )
    decision = decision_repo.create_decision(
        event_id=event.id,
        priority="high",
        classification="Payment Failure",
        summary="Payment failed for test customer",
        recommendations=["send_email", "generate_report", "notify_team"],
        rule_triggered="payment_failed",
    )
    return decision


def test_decision_generates_expected_actions(decision_with_event, db_session):
    action_repo = ActionRepository(db_session)
    report_service = MagicMock()
    report_service.generate.return_value = Report(
        id=uuid.uuid4(),
        event_id=decision_with_event.event_id,
        decision_id=decision_with_event.id,
        type="pdf",
        s3_url="https://example.com/report.pdf",
    )
    email_service = MagicMock()
    email_service.send_decision_email.return_value = {
        "provider": "resend",
        "status": "sent",
        "email_id": "email_test_123",
    }

    executor = ActionExecutor(
        action_repo,
        report_service=report_service,
        email_service=email_service,
    )
    actions = executor.execute(decision_with_event)

    action_types = [action.action_type for action in actions]
    assert action_types == ["report", "email", "notification"]
    assert all(action.status == "completed" for action in actions)


def test_report_action_generates_pdf_and_uploads_to_s3(decision_with_event, db_session):
    action_repo = ActionRepository(db_session)
    report_service = MagicMock()
    report_service.generate.return_value = Report(
        id=uuid.uuid4(),
        event_id=decision_with_event.event_id,
        decision_id=decision_with_event.id,
        type="pdf",
        s3_url="https://s3.example.com/reports/test.pdf",
    )
    email_service = MagicMock()
    email_service.send_decision_email.return_value = {
        "provider": "resend",
        "status": "sent",
        "email_id": "email_test_456",
    }

    executor = ActionExecutor(
        action_repo,
        report_service=report_service,
        email_service=email_service,
    )
    actions = executor.execute(decision_with_event)

    report_service.generate.assert_called_once_with(decision_with_event)
    report_action = next(action for action in actions if action.action_type == "report")
    assert report_action.result["type"] == "pdf"
    assert report_action.result["s3_url"] == "https://s3.example.com/reports/test.pdf"


def test_email_action_calls_resend(decision_with_event, db_session):
    action_repo = ActionRepository(db_session)
    report_service = MagicMock()
    report_service.generate.return_value = Report(
        id=uuid.uuid4(),
        event_id=decision_with_event.event_id,
        decision_id=decision_with_event.id,
        type="pdf",
        s3_url="https://s3.example.com/reports/test.pdf",
    )
    email_service = MagicMock()
    email_service.send_decision_email.return_value = {
        "provider": "resend",
        "status": "sent",
        "email_id": "email_test_789",
    }

    executor = ActionExecutor(
        action_repo,
        report_service=report_service,
        email_service=email_service,
    )
    executor.execute(decision_with_event)

    email_service.send_decision_email.assert_called_once_with(decision_with_event)


def test_email_failure_does_not_stop_other_actions(decision_with_event, db_session):
    action_repo = ActionRepository(db_session)
    report_service = MagicMock()
    report_service.generate.return_value = Report(
        id=uuid.uuid4(),
        event_id=decision_with_event.event_id,
        decision_id=decision_with_event.id,
        type="pdf",
        s3_url="https://s3.example.com/reports/test.pdf",
    )
    email_service = MagicMock()
    email_service.send_decision_email.return_value = {
        "provider": "resend",
        "status": "failed",
        "error": "Resend unavailable",
    }

    executor = ActionExecutor(
        action_repo,
        report_service=report_service,
        email_service=email_service,
    )
    actions = executor.execute(decision_with_event)

    action_map = {action.action_type: action for action in actions}
    assert action_map["report"].status == "completed"
    assert action_map["email"].status == "failed"
    assert action_map["notification"].status == "completed"
