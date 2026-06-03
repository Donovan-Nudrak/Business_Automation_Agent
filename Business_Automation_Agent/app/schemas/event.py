import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    event_type: str
    source: str
    payload: dict[str, Any]
    customer_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    customer_id: uuid.UUID | None
    stripe_event_id: str | None
    source: str
    payload: dict[str, Any] | None
    status: str
    workflow_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int = Field(ge=0)
