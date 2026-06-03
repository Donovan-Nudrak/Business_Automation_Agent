import logging
import uuid

from app.agents.business_agent import BusinessAgent
from app.decision_engine.gemini_client import GeminiClient
from app.models.event import Event
from app.repositories.decision_repository import DecisionRepository
from app.repositories.event_repository import EventRepository
from app.rules.rule_engine import RuleEngine
from app.services.action_service import ActionService

logger = logging.getLogger(__name__)


class EventProcessor:
    PROCESSING_STATUS = "processing"
    COMPLETED_STATUS = "completed"
    FAILED_STATUS = "failed"

    def __init__(
        self,
        event_repository: EventRepository,
        business_agent: BusinessAgent,
        decision_repository: DecisionRepository,
        action_service: ActionService,
    ) -> None:
        self.event_repository = event_repository
        self.business_agent = business_agent
        self.decision_repository = decision_repository
        self.action_service = action_service

    def process(self, event_id: uuid.UUID) -> None:
        logger.info("Starting processing for event %s", event_id)

        event = self.event_repository.get_event(event_id)
        if event is None:
            logger.error("Event %s not found", event_id)
            raise ValueError(f"Event {event_id} not found")

        existing_decision = self.decision_repository.get_decision_by_event_id(event_id)
        if existing_decision is not None:
            logger.info(
                "Decision already exists for event %s, marking as completed",
                event_id,
            )
            self.event_repository.update_status(event_id, self.COMPLETED_STATUS)
            return

        self.event_repository.update_status(event_id, self.PROCESSING_STATUS)

        try:
            self._run_pipeline_in_transaction(event)
            self.event_repository.update_status(event_id, self.COMPLETED_STATUS)
            logger.info("Successfully completed processing for event %s", event_id)
        except Exception:
            self._mark_event_failed(event_id)
            logger.exception("Failed processing event %s", event_id)
            raise

    def _run_pipeline_in_transaction(self, event: Event) -> None:
        db = self.event_repository.db
        original_commit = db.commit

        def commit_as_flush() -> None:
            db.flush()

        db.commit = commit_as_flush  # type: ignore[method-assign]
        try:
            self._run_pipeline(event)
            original_commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.commit = original_commit

    def _mark_event_failed(self, event_id: uuid.UUID) -> None:
        db = self.event_repository.db
        if db.in_transaction():
            db.rollback()
        self.event_repository.update_status(event_id, self.FAILED_STATUS)

    def _run_pipeline(self, event: Event) -> None:
        logger.info("Running Business Agent for event %s", event.id)
        agent_decision = self.business_agent.analyze(event)

        decision = self.decision_repository.create_decision(
            event_id=event.id,
            priority=agent_decision.priority,
            classification=agent_decision.classification,
            summary=agent_decision.summary,
            recommendations=agent_decision.recommendations,
            rule_triggered=agent_decision.rule_triggered,
        )
        logger.info(
            "Decision created for event %s with priority=%s rule=%s",
            event.id,
            agent_decision.priority,
            agent_decision.rule_triggered,
        )

        actions = self.action_service.execute_for_decision(decision)
        logger.info(
            "Created and executed %s actions for event %s",
            len(actions),
            event.id,
        )


def process_event(event_id: str) -> None:
    from app.core.config import settings
    from app.database.session import SessionLocal
    from app.services.action_service import get_action_service

    db = SessionLocal()
    try:
        processor = EventProcessor(
            event_repository=EventRepository(db),
            business_agent=BusinessAgent(
                rule_engine=RuleEngine(),
                gemini_client=GeminiClient(
                    api_key=settings.GEMINI_API_KEY,
                    model_name=settings.GEMINI_MODEL,
                ),
            ),
            decision_repository=DecisionRepository(db),
            action_service=get_action_service(db),
        )
        processor.process(uuid.UUID(event_id))
    finally:
        db.close()
