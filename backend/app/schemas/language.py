from pydantic import BaseModel


class LevelRead(BaseModel):
    code: str
    display_name: str
    display_name_vi: str


class LanguageRead(BaseModel):
    """Thông tin công khai của một ngôn ngữ (không gồm ngưỡng placement)."""

    language_code: str
    display_name: str
    display_name_vi: str
    levels: list[LevelRead]
