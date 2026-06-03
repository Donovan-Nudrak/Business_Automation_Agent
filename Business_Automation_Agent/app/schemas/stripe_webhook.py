from dataclasses import dataclass

from app.schemas.event import EventResponse


@dataclass(frozen=True)
class StripeIngestResult:
    event: EventResponse
    already_processed: bool
