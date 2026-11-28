"""Chuẩn hóa câu trả lời theo cấu hình ngôn ngữ (languages/<code>.yaml → exercises.normalization). Hàm thuần."""
from __future__ import annotations

import re
import unicodedata

from app.core.languages import NormalizationConfig

_SPACE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")
_FINAL_PUNCT = re.compile(r"[\s.!?;:,]+$")


def normalize_answer(text: str, config: NormalizationConfig, *, keep_case: bool = False) -> str:
    """NFC → thống nhất dấu nháy (’ ‘ ` ´ → ') và ngoặc kép (“ ” → ") → chữ thường (trừ keep_case) →
    gộp khoảng trắng → bỏ khoảng trắng trước dấu câu → bỏ dấu câu cuối câu."""
    value = unicodedata.normalize(config.unicode_form, text or "")
    for ch in config.apostrophes:
        value = value.replace(ch, "'")
    for ch in config.quotes:
        value = value.replace(ch, '"')
    if config.lowercase and not keep_case:
        value = value.lower()
    value = _SPACE.sub(" ", value).strip()
    value = _SPACE_BEFORE_PUNCT.sub(r"\1", value)
    if config.strip_final_punctuation:
        value = _FINAL_PUNCT.sub("", value)
    return value


def words(text: str) -> list[str]:
    """Từ (giữ dấu nháy trong từ như I'm, don't) — dùng cho đếm độ dài và so tập từ."""
    return re.findall(r"[\w']+", text.lower())
