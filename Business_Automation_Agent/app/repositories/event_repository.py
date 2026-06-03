import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.event import Event


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_event(
        self,
        *,
        event_type: str,
        source: str,
        payload: dict | None,
        status: str,
        customer_id: uuid.UUID | None = None,
        workflow_id: uuid.UUID | None = None,
        stripe_event_id: str | None = None,
    ) -> Event:
        event = Event(
            event_type=event_type,
            source=source,
            payload=payload,
            status=status,
            customer_id=customer_id,
            workflow_id=workflow_id,
            stripe_event_id=stripe_event_id,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event_by_stripe_event_id(self, stripe_event_id: str) -> Event | None:
        return self.db.scalar(
            select(Event).where(Event.stripe_event_id == stripe_event_id)
        )

    def get_event(self, event_id: uuid.UUID) -> Event | None:
        return self.db.get(Event, event_id)

    def list_events(
        self,
        *,
        page: int = 0,
        limit: int = 20,
        status: str | None = None,
        event_type: str | None = None,
    ) -> tuple[list[Event], int]:
        query = select(Event)

        if status is not None:
            query = query.where(Event.status == status)
        if event_type is not None:
            query = query.where(Event.event_type == event_type)

        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        total = total or 0

        items = self.db.scalars(
            query.order_by(Event.created_at.desc())
            .offset(page * limit)
            .limit(limit)
        ).all()

        return list(items), total

    def update_status(self, event_id: uuid.UUID, status: str) -> Event | None:
        event = self.get_event(event_id)
        if event is None:
            return None

        event.status = status
        self.db.commit()
        self.db.refresh(event)
        return event


def get_event_repository(db: Session) -> EventRepository:
    return EventRepository(db)
