import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    decision_id: uuid.UUID
    action_type: str
    status: str
    result: dict[str, Any] | None
    executed_at: datetime | None
    created_at: datetime


class ActionListResponse(BaseModel):
    items: list[ActionResponse]
    total: int
    page: int = Field(ge=0)
