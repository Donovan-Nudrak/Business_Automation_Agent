import logging

from app.services.event_processor import process_event
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_event")
def process_event_task(event_id: str) -> None:
    logger.info("Celery task received for event %s", event_id)
    process_event(event_id)
