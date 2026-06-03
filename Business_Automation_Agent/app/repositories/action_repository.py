import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.action import Action


class ActionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_action(
        self,
        *,
        event_id: uuid.UUID,
        decision_id: uuid.UUID,
        action_type: str,
        status: str = "pending",
    ) -> Action:
        action = Action(
            event_id=event_id,
            decision_id=decision_id,
            action_type=action_type,
            status=status,
        )
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        return action

    def get_action(self, action_id: uuid.UUID) -> Action | None:
        return self.db.get(Action, action_id)

    def list_actions(
        self,
        *,
        page: int = 0,
        limit: int = 20,
        status: str | None = None,
        action_type: str | None = None,
    ) -> tuple[list[Action], int]:
        query = select(Action)

        if status is not None:
            query = query.where(Action.status == status)
        if action_type is not None:
            query = query.where(Action.action_type == action_type)

        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        total = total or 0

        items = self.db.scalars(
            query.order_by(Action.created_at.desc())
            .offset(page * limit)
            .limit(limit)
        ).all()

        return list(items), total

    def update_action_status(
        self,
        action_id: uuid.UUID,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        executed_at: datetime | None = None,
    ) -> Action | None:
        action = self.get_action(action_id)
        if action is None:
            return None

        action.status = status
        if result is not None:
            action.result = result
        if executed_at is not None:
            action.executed_at = executed_at

        self.db.commit()
        self.db.refresh(action)
        return action


def get_action_repository(db: Session) -> ActionRepository:
    return ActionRepository(db)
