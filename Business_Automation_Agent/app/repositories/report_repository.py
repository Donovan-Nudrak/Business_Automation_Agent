import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.report import Report


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_report(
        self,
        *,
        event_id: uuid.UUID,
        decision_id: uuid.UUID,
        type: str,
        s3_url: str,
    ) -> Report:
        report = Report(
            event_id=event_id,
            decision_id=decision_id,
            type=type,
            s3_url=s3_url,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report(self, report_id: uuid.UUID) -> Report | None:
        return self.db.get(Report, report_id)

    def get_report_by_event_id(self, event_id: uuid.UUID) -> Report | None:
        return self.db.scalar(select(Report).where(Report.event_id == event_id))

    def get_report_by_decision_id(self, decision_id: uuid.UUID) -> Report | None:
        return self.db.scalar(
            select(Report).where(Report.decision_id == decision_id)
        )

    def list_reports(
        self,
        *,
        page: int = 0,
        limit: int = 20,
    ) -> tuple[list[Report], int]:
        query = select(Report)
        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        total = total or 0

        items = self.db.scalars(
            query.order_by(Report.created_at.desc())
            .offset(page * limit)
            .limit(limit)
        ).all()

        return list(items), total


def get_report_repository(db: Session) -> ReportRepository:
    return ReportRepository(db)
