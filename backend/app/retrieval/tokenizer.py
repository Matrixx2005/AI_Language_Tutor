"""Tokenizer cho BM25, cấu hình theo ngôn ngữ (languages/<code>.yaml → retrieval.tokenizer).

Áp dụng GIỐNG HỆT cho tài liệu và truy vấn: chuẩn hóa Unicode, chữ thường, (tùy chọn) bỏ dấu tiếng Việt
— để "động từ" và "dong tu" (gõ thiếu dấu) khớp nhau — rồi tách theo ký tự chữ/số, bỏ từ dừng.
"""
from __future__ import annotations

import re
import unicodedata

from app.core.languages import TokenizerConfig

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def strip_diacritics(text: str) -> str:
    # "đ"/"Đ" không phải dấu kết hợp nên NFD không tách được → thay riêng.
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def tokenize(text: str, config: TokenizerConfig) -> list[str]:
    text = unicodedata.normalize(config.unicode_form, text)
    if config.lowercase:
        text = text.lower()
    if config.strip_diacritics:
        text = strip_diacritics(text)
    return [
        token
        for token in _TOKEN.findall(text)
        if len(token) >= config.min_token_length and token not in config.stopwords
    ]
