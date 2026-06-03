import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.models.action import Action
from app.models.decision import Decision
from app.repositories.action_repository import ActionRepository
from app.services.email_service import EmailService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


class ActionExecutor:
    RECOMMENDATION_MAP: dict[str, str] = {
        "send_email": "email",
        "generate_report": "report",
        "notify_team": "notification",
    }

    SIMULATED_RESULTS: dict[str, dict[str, str]] = {
        "notification": {"message": "notification simulated"},
        "manual_review": {"message": "manual review required"},
    }

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    ACTION_EXECUTION_ORDER: dict[str, int] = {
        "report": 0,
        "email": 1,
        "notification": 2,
        "manual_review": 3,
    }

    def __init__(
        self,
        action_repository: ActionRepository,
        report_service: ReportService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.action_repository = action_repository
        self.report_service = report_service
        self.email_service = email_service

    def execute(self, decision: Decision) -> list[Action]:
        recommendations = self._normalize_recommendations(decision.recommendations)
        ordered_recommendations = self._order_recommendations_for_execution(
            recommendations
        )
        actions: list[Action] = []

        for recommendation in ordered_recommendations:
            action_type = self._resolve_action_type(recommendation)
            action = self.action_repository.create_action(
                event_id=decision.event_id,
                decision_id=decision.id,
                action_type=action_type,
                status=self.STATUS_PENDING,
            )
            executed_action = self._execute_action(action, decision)
            actions.append(executed_action)

        logger.info(
            "Executed %s actions for decision %s",
            len(actions),
            decision.id,
        )
        return actions

    def _order_recommendations_for_execution(
        self,
        recommendations: list[Any],
    ) -> list[Any]:
        return sorted(
            recommendations,
            key=lambda recommendation: self.ACTION_EXECUTION_ORDER.get(
                self._resolve_action_type(recommendation),
                99,
            ),
        )

    def _normalize_recommendations(
        self,
        recommendations: list[Any] | dict[str, Any] | None,
    ) -> list[Any]:
        if recommendations is None:
            return ["manual_review"]
        if isinstance(recommendations, dict):
            return [recommendations]
        if isinstance(recommendations, list):
            return recommendations or ["manual_review"]
        return [recommendations]

    def _resolve_action_type(self, recommendation: Any) -> str:
        normalized = self._recommendation_key(recommendation)

        for pattern, action_type in self.RECOMMENDATION_MAP.items():
            if pattern in normalized:
                return action_type

        return "manual_review"

    def _recommendation_key(self, recommendation: Any) -> str:
        if isinstance(recommendation, dict):
            raw = (
                recommendation.get("action")
                or recommendation.get("type")
                or recommendation.get("recommendation")
                or ""
            )
        else:
            raw = str(recommendation)

        return re.sub(r"[\s\-]+", "_", raw.lower())

    def _execute_action(self, action: Action, decision: Decision) -> Action:
        self.action_repository.update_action_status(
            action.id,
            self.STATUS_PROCESSING,
        )

        if action.action_type == "email":
            return self._execute_email_action(action, decision)

        try:
            result = self._build_result(action, decision)
            updated = self.action_repository.update_action_status(
                action.id,
                self.STATUS_COMPLETED,
                result=result,
                executed_at=datetime.now(UTC),
            )
            if updated is None:
                raise RuntimeError(f"Action {action.id} not found after processing")
            return updated
        except Exception:
            self.action_repository.update_action_status(action.id, self.STATUS_FAILED)
            logger.exception("Failed executing action %s", action.id)
            raise

    def _execute_email_action(self, action: Action, decision: Decision) -> Action:
        if self.email_service is None:
            result = {
                "provider": "resend",
                "status": "failed",
                "error": "EmailService is not configured",
            }
            return self._finalize_action(action.id, self.STATUS_FAILED, result)

        result = self.email_service.send_decision_email(decision)
        if result.get("status") == "sent":
            return self._finalize_action(action.id, self.STATUS_COMPLETED, result)

        return self._finalize_action(action.id, self.STATUS_FAILED, result)

    def _finalize_action(
        self,
        action_id: Any,
        status: str,
        result: dict[str, Any],
    ) -> Action:
        updated = self.action_repository.update_action_status(
            action_id,
            status,
            result=result,
            executed_at=datetime.now(UTC),
        )
        if updated is None:
            raise RuntimeError(f"Action {action_id} not found after processing")
        return updated

    def _build_result(self, action: Action, decision: Decision) -> dict[str, Any]:
        if action.action_type == "report":
            if self.report_service is None:
                raise RuntimeError("ReportService is not configured")

            report = self.report_service.generate(decision)
            return {
                "message": "report generated",
                "report_id": str(report.id),
                "s3_url": report.s3_url,
                "type": report.type,
            }

        return self.SIMULATED_RESULTS.get(
            action.action_type,
            self.SIMULATED_RESULTS["manual_review"],
        )
