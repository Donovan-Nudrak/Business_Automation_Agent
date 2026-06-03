import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.action import ActionListResponse, ActionResponse
from app.services.action_service import ActionService, get_action_service

router = APIRouter(prefix="/actions", tags=["actions"])


def _service(db: Session = Depends(get_db)) -> ActionService:
    return get_action_service(db)


@router.get("", response_model=ActionListResponse)
def list_actions(
    page: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    action_type: str | None = Query(None),
    _: User = Depends(get_current_user),
    action_service: ActionService = Depends(_service),
) -> ActionListResponse:
    return action_service.list_actions(
        page=page,
        limit=limit,
        status=status,
        action_type=action_type,
    )


@router.get("/{action_id}", response_model=ActionResponse)
def get_action(
    action_id: uuid.UUID,
    _: User = Depends(get_current_user),
    action_service: ActionService = Depends(_service),
) -> ActionResponse:
    return action_service.get_action(action_id)
