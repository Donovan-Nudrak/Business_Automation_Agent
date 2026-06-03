import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.documents.pdf_generator import generate_pdf
from app.documents.report_generator import generate_json
from app.integrations.s3_client import S3Client, get_s3_client
from app.models.decision import Decision
from app.models.report import Report
from app.repositories.report_repository import ReportRepository, get_report_repository
from app.schemas.report import ReportListResponse, ReportResponse

logger = logging.getLogger(__name__)


class ReportService:
    REPORT_TYPE_JSON = "json"
    REPORT_TYPE_PDF = "pdf"

    def __init__(
        self,
        report_repository: ReportRepository,
        s3_client: S3Client,
    ) -> None:
        self.report_repository = report_repository
        self.s3_client = s3_client

    def generate(self, decision: Decision) -> Report:
        existing = self.report_repository.get_report_by_event_id(decision.event_id)
        if existing is not None:
            logger.info(
                "Report already exists for event %s, skipping generation",
                decision.event_id,
            )
            return self._attach_presigned_url(existing)

        existing_by_decision = self.report_repository.get_report_by_decision_id(
            decision.id
        )
        if existing_by_decision is not None:
            logger.info(
                "Report already exists for decision %s, skipping generation",
                decision.id,
            )
            return self._attach_presigned_url(existing_by_decision)

        _ = generate_json(decision)
        pdf_content = generate_pdf(decision)
        object_key = self.s3_client.generate_object_key(
            decision.event_id,
            self.REPORT_TYPE_PDF,
        )
        s3_url = self.s3_client.upload_pdf(pdf_content, object_key)

        report = self.report_repository.create_report(
            event_id=decision.event_id,
            decision_id=decision.id,
            type=self.REPORT_TYPE_PDF,
            s3_url=s3_url,
        )
        logger.info(
            "PDF report %s uploaded to S3 for event %s",
            report.id,
            decision.event_id,
        )
        return self._attach_presigned_url(report, object_key=object_key)

    def _attach_presigned_url(
        self,
        report: Report,
        *,
        object_key: str | None = None,
    ) -> Report:
        key = object_key or self.s3_client.extract_key_from_url(report.s3_url or "")
        if not key:
            return report

        report.presigned_url = self.s3_client.generate_presigned_url(key)
        logger.info(
            "Presigned URL generated for report %s (expires in %ss)",
            report.id,
            settings.PRESIGNED_URL_EXPIRE_SECONDS,
        )
        return report

    def get_report(self, report_id: uuid.UUID) -> ReportResponse:
        report = self.report_repository.get_report(report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )
        return ReportResponse.model_validate(report)

    def get_report_by_event_id(self, event_id: uuid.UUID) -> ReportResponse:
        report = self.report_repository.get_report_by_event_id(event_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found for event",
            )
        return ReportResponse.model_validate(report)

    def list_reports(
        self,
        *,
        page: int = 0,
        limit: int = 20,
    ) -> ReportListResponse:
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

        items, total = self.report_repository.list_reports(page=page, limit=limit)
        return ReportListResponse(
            items=[ReportResponse.model_validate(item) for item in items],
            total=total,
            page=page,
        )


def get_report_service(db: Session) -> ReportService:
    return ReportService(
        report_repository=get_report_repository(db),
        s3_client=get_s3_client(),
    )
