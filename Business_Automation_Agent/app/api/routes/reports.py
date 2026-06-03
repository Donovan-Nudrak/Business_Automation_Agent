import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.report import ReportListResponse, ReportResponse
from app.services.report_service import ReportService, get_report_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _service(db: Session = Depends(get_db)) -> ReportService:
    return get_report_service(db)


@router.get("", response_model=ReportListResponse)
def list_reports(
    page: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_user),
    report_service: ReportService = Depends(_service),
) -> ReportListResponse:
    return report_service.list_reports(page=page, limit=limit)


@router.get("/event/{event_id}", response_model=ReportResponse)
def get_report_by_event(
    event_id: uuid.UUID,
    _: User = Depends(get_current_user),
    report_service: ReportService = Depends(_service),
) -> ReportResponse:
    return report_service.get_report_by_event_id(event_id)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: uuid.UUID,
    _: User = Depends(get_current_user),
    report_service: ReportService = Depends(_service),
) -> ReportResponse:
    return report_service.get_report(report_id)
