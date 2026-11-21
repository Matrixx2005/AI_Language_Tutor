from typing import Annotated

from fastapi import APIRouter, Body

from app.api.deps import CurrentUser, DbSession
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services import profile as profile_service

# Chỉ có /me: URL không chứa user_id nên không thể đọc/sửa hồ sơ người khác.
router = APIRouter(prefix="/profile", tags=["profile"])

PROFILE_UPDATE_EXAMPLES = {
    "muc_tieu_va_trinh_do": {
        "summary": "Sửa mục tiêu và trình độ",
        "value": {"learning_goal": "Giao tiếp khi đi du lịch", "current_level_code": "A2"},
    },
    "chi_muc_tieu": {
        "summary": "Chỉ sửa mục tiêu (trường khác giữ nguyên)",
        "value": {"learning_goal": "Luyện thi IELTS"},
    },
    "ten_hien_thi": {
        "summary": "Đổi tên hiển thị",
        "value": {"display_name": "Minh"},
    },
    "xoa_muc_tieu": {
        "summary": "Xóa mục tiêu (gửi null)",
        "value": {"learning_goal": None},
    },
}


@router.get("/me", response_model=ProfileRead)
def read_my_profile(user: CurrentUser) -> ProfileRead:
    return profile_service.to_profile_read(user)


@router.patch("/me", response_model=ProfileRead)
def update_my_profile(
    data: Annotated[ProfileUpdate, Body(openapi_examples=PROFILE_UPDATE_EXAMPLES)],
    user: CurrentUser,
    session: DbSession,
) -> ProfileRead:
    """Chỉ cập nhật trường được gửi. `current_level_code` phải thuộc cấu hình ngôn ngữ
    (tiếng Anh: A1, A2, B1). Không sửa được email hay ngôn ngữ học."""
    return profile_service.update_profile(session, user, data)
