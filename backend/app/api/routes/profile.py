from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services import profile as profile_service

# Chỉ có /me: URL không chứa user_id nên không thể đọc/sửa hồ sơ người khác.
router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileRead)
def read_my_profile(user: CurrentUser) -> ProfileRead:
    return profile_service.to_profile_read(user)


@router.patch("/me", response_model=ProfileRead)
def update_my_profile(data: ProfileUpdate, user: CurrentUser, session: DbSession) -> ProfileRead:
    return profile_service.update_profile(session, user, data)
