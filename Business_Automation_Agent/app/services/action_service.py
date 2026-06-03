import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.action_executor.action_executor import ActionExecutor
from app.models.action import Action
from app.models.decision import Decision
from app.repositories.action_repository import ActionRepository, get_action_repository
from app.schemas.action import ActionListResponse, ActionResponse
from app.services.email_service import get_email_service
from app.services.report_service import get_report_service


class ActionService:
    def __init__(
        self,
        action_repository: ActionRepository,
        action_executor: ActionExecutor,
    ) -> None:
        self.action_repository = action_repository
        self.action_executor = action_executor

    def execute_for_decision(self, decision: Decision) -> list[Action]:
        return self.action_executor.execute(decision)

    def get_action(self, action_id: uuid.UUID) -> ActionResponse:
        action = self.action_repository.get_action(action_id)
        if action is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )
        return ActionResponse.model_validate(action)

    def list_actions(
        self,
        *,
        page: int = 0,
        limit: int = 20,
        status: str | None = None,
        action_type: str | None = None,
    ) -> ActionListResponse:
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

        items, total = self.action_repository.list_actions(
            page=page,
            limit=limit,
            status=status,
            action_type=action_type,
        )
        return ActionListResponse(
            items=[ActionResponse.model_validate(item) for item in items],
            total=total,
            page=page,
        )


def get_action_service(db: Session) -> ActionService:
    action_repository = get_action_repository(db)
    report_service = get_report_service(db)
    email_service = get_email_service()
    return ActionService(
        action_repository=action_repository,
        action_executor=ActionExecutor(
            action_repository,
            report_service=report_service,
            email_service=email_service,
        ),
    )
