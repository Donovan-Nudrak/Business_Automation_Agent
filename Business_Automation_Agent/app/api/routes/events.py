import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.event import EventCreate, EventListResponse, EventResponse
from app.services.event_service import EventService, get_event_service

router = APIRouter(prefix="/events", tags=["events"])


def _service(db: Session = Depends(get_db)) -> EventService:
    return get_event_service(db)


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event_in: EventCreate,
    _: User = Depends(get_current_user),
    event_service: EventService = Depends(_service),
) -> EventResponse:
    return event_service.create_event(event_in)


@router.get("", response_model=EventListResponse)
def list_events(
    page: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    event_type: str | None = Query(None),
    _: User = Depends(get_current_user),
    event_service: EventService = Depends(_service),
) -> EventListResponse:
    return event_service.list_events(
        page=page,
        limit=limit,
        status=status,
        event_type=event_type,
    )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: uuid.UUID,
    _: User = Depends(get_current_user),
    event_service: EventService = Depends(_service),
) -> EventResponse:
    return event_service.get_event(event_id)
