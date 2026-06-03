import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    decision_id: uuid.UUID
    type: str
    s3_url: str | None
    sent_to: str | None
    sent_at: datetime | None
    created_at: datetime


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int = Field(ge=0)
