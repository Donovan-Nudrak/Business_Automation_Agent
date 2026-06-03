import uuid

import pytest

from app.models.event import Event
from app.rules.rule_engine import RuleEngine


def _make_event(event_type: str) -> Event:
    return Event(
        id=uuid.uuid4(),
        event_type=event_type,
        source="stripe",
        payload={"type": event_type},
        status="pending",
    )


@pytest.mark.parametrize(
    ("event_type", "expected_priority", "expected_rule"),
    [
        ("payment_intent.payment_failed", "high", "payment_failed"),
        ("payment_intent.succeeded", "low", "payment_succeeded"),
        ("customer.created", "medium", "unknown"),
    ],
)
def test_rule_engine_priority_and_rule_triggered(
    event_type: str,
    expected_priority: str,
    expected_rule: str,
):
    engine = RuleEngine()
    result = engine.evaluate(_make_event(event_type))

    assert result.priority == expected_priority
    assert result.rule_triggered == expected_rule


def test_rule_engine_assigns_classification_for_failed_event():
    engine = RuleEngine()
    result = engine.evaluate(_make_event("payment_intent.payment_failed"))

    assert result.classification == "payment_failed"
