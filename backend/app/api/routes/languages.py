from fastapi import APIRouter

from app.core.errors import AppError
from app.core.languages import UnknownLanguageError, get_language_config
from app.schemas.language import LanguageRead, LevelRead

# Công khai (không cần token): chỉ là cấu hình, không có dữ liệu người dùng.
router = APIRouter(prefix="/languages", tags=["languages"])


@router.get("/{language_code}", response_model=LanguageRead)
def read_language(language_code: str) -> LanguageRead:
    """Danh sách trình độ hợp lệ của một ngôn ngữ, theo thứ tự trong languages/<code>.yaml."""
    try:
        language = get_language_config(language_code)
    except UnknownLanguageError:
        raise AppError(404, "language_not_found", "Không tìm thấy cấu hình ngôn ngữ.") from None
    return LanguageRead(
        language_code=language.language_code,
        display_name=language.display_name,
        display_name_vi=language.display_name_vi,
        levels=[
            LevelRead(code=level.code, display_name=level.display_name, display_name_vi=level.display_name_vi)
            for level in language.levels
        ],
    )
