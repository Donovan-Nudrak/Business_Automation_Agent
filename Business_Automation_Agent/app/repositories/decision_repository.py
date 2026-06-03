import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.decision import Decision


class DecisionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_decision(
        self,
        *,
        event_id: uuid.UUID,
        priority: str,
        classification: str,
        summary: str,
        recommendations: list[Any] | None,
        rule_triggered: str | None,
    ) -> Decision:
        decision = Decision(
            event_id=event_id,
            priority=priority,
            classification=classification,
            summary=summary,
            recommendations=recommendations,
            rule_triggered=rule_triggered,
        )
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def get_decision(self, decision_id: uuid.UUID) -> Decision | None:
        return self.db.get(Decision, decision_id)

    def get_decision_by_event_id(self, event_id: uuid.UUID) -> Decision | None:
        return self.db.scalar(
            select(Decision).where(Decision.event_id == event_id)
        )


def get_decision_repository(db: Session) -> DecisionRepository:
    return DecisionRepository(db)
