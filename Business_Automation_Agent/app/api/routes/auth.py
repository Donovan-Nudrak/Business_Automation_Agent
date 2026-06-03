from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(db: Session = Depends(get_db)) -> AuthService:
    return get_auth_service(db)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UserCreate,
    _: User = Depends(require_admin),
    auth_service: AuthService = Depends(_service),
) -> User:
    return auth_service.register(user_in)


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(_service),
) -> Token:
    return auth_service.login(credentials)
