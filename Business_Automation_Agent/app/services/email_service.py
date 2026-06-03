import logging
from typing import Any

from sqlalchemy.orm import object_session

from app.core.config import settings
from app.documents.email_templates import (
    build_decision_email_html,
    build_decision_email_subject,
)
from app.integrations.resend_client import ResendClient, get_resend_client
from app.integrations.s3_client import S3Client, get_s3_client
from app.models.decision import Decision
from app.models.report import Report

logger = logging.getLogger(__name__)


class EmailService:
    PROVIDER = "resend"

    def __init__(
        self,
        resend_client: ResendClient,
        s3_client: S3Client | None = None,
    ) -> None:
        self.resend_client = resend_client
        self.s3_client = s3_client or get_s3_client()

    def _get_report_for_decision(self, decision: Decision) -> Report | None:
        if decision.report is not None:
            return decision.report

        session = object_session(decision)
        if session is None:
            return None

        return (
            session.query(Report)
            .filter(Report.decision_id == decision.id)
            .first()
        )

    def _get_report_access_url(self, report: Report) -> str | None:
        presigned_url = getattr(report, "presigned_url", None)
        if presigned_url:
            return presigned_url

        if not report.s3_url:
            return None

        object_key = self.s3_client.extract_key_from_url(report.s3_url)
        if not object_key:
            return None

        return self.s3_client.generate_presigned_url(object_key)

    def send_decision_email(self, decision: Decision) -> dict[str, Any]:
        if not settings.ALERT_EMAIL:
            return {
                "provider": self.PROVIDER,
                "status": "failed",
                "error": "ALERT_EMAIL is not configured",
            }

        try:
            report = self._get_report_for_decision(decision)
            report_access_url = (
                self._get_report_access_url(report) if report is not None else None
            )
            subject = build_decision_email_subject(decision)
            html = build_decision_email_html(
                decision,
                report=report,
                report_access_url=report_access_url,
            )
            response = self.resend_client.send_email(
                to=settings.ALERT_EMAIL,
                subject=subject,
                html=html,
            )
            return {
                "provider": self.PROVIDER,
                "email_id": response["id"],
                "status": "sent",
            }
        except Exception as exc:
            logger.exception(
                "Failed to send decision email for event %s",
                decision.event_id,
            )
            return {
                "provider": self.PROVIDER,
                "status": "failed",
                "error": str(exc),
            }


def get_email_service() -> EmailService:
    return EmailService(get_resend_client())
