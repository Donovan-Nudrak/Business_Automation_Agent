import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Event
from app.repositories.event_repository import EventRepository, get_event_repository
from app.schemas.event import EventCreate, EventListResponse, EventResponse
from app.schemas.stripe_webhook import StripeIngestResult


class EventService:
    MANUAL_EVENT_STATUS = "received"
    STRIPE_EVENT_STATUS = "pending"
    PENDING_STATUS = "pending"

    def __init__(self, repository: EventRepository) -> None:
        self.repository = repository

    def create_event(self, event_in: EventCreate) -> EventResponse:
        self._validate_event_input(event_in)
        event = self.repository.create_event(
            event_type=event_in.event_type,
            source=event_in.source,
            payload=event_in.payload,
            status=self.MANUAL_EVENT_STATUS,
            customer_id=event_in.customer_id,
            workflow_id=event_in.workflow_id,
        )
        return EventResponse.model_validate(event)

    def ingest_stripe_webhook(self, stripe_event: dict[str, Any]) -> StripeIngestResult:
        stripe_event_id = stripe_event.get("id")
        if not isinstance(stripe_event_id, str) or not stripe_event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe event id is required",
            )

        existing = self.repository.get_event_by_stripe_event_id(stripe_event_id)
        if existing is not None:
            return StripeIngestResult(
                event=EventResponse.model_validate(existing),
                already_processed=True,
            )

        event_type = stripe_event.get("type")
        if not isinstance(event_type, str) or not event_type:
            event_type = "stripe.unknown"

        try:
            event = self.repository.create_event(
                event_type=event_type,
                source="stripe",
                payload=stripe_event,
                status=self.STRIPE_EVENT_STATUS,
                stripe_event_id=stripe_event_id,
            )
        except IntegrityError:
            self.repository.db.rollback()
            existing = self.repository.get_event_by_stripe_event_id(stripe_event_id)
            if existing is not None:
                return StripeIngestResult(
                    event=EventResponse.model_validate(existing),
                    already_processed=True,
                )
            raise

        self._enqueue_if_pending(event)
        return StripeIngestResult(
            event=EventResponse.model_validate(event),
            already_processed=False,
        )

    def get_event(self, event_id: uuid.UUID) -> EventResponse:
        event = self.repository.get_event(event_id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        return EventResponse.model_validate(event)

    def list_events(
        self,
        *,
        page: int = 0,
        limit: int = 20,
        status: str | None = None,
        event_type: str | None = None,
    ) -> EventListResponse:
        if page < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be greater than or equal to 0",
            )
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100",
            )

        items, total = self.repository.list_events(
            page=page,
            limit=limit,
            status=status,
            event_type=event_type,
        )
        return EventListResponse(
            items=[EventResponse.model_validate(item) for item in items],
            total=total,
            page=page,
        )

    def _enqueue_if_pending(self, event: Event) -> None:
        if event.status != self.PENDING_STATUS:
            return

        from app.tasks.event_tasks import process_event_task

        process_event_task.delay(str(event.id))

    def _validate_event_input(self, event_in: EventCreate) -> None:
        if not event_in.event_type.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="event_type is required",
            )
        if not event_in.source.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source is required",
            )
        if event_in.payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payload is required",
            )


def get_event_service(db: Session) -> EventService:
    return EventService(get_event_repository(db))
