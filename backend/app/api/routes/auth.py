from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.profile import ProfileRead
from app.services import auth as auth_service
from app.services.profile import to_profile_read

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ProfileRead)
def register(data: RegisterRequest, session: DbSession) -> ProfileRead:
    """Tạo tài khoản và hồ sơ học tập. Không trả token: người dùng đăng nhập riêng."""
    return to_profile_read(auth_service.register_user(session, data))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: DbSession) -> TokenResponse:
    user = auth_service.authenticate(session, data)
    token, expires_in = create_access_token(user.user_id)
    return TokenResponse(access_token=token, expires_in=expires_in)
