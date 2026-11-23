"""Nạp prompt theo ngôn ngữ từ prompts/<language_code>/<name>.md. Không hardcode prompt trong code.

Biến dạng `{{ten_bien}}` được thay bằng giá trị truyền vào; thiếu biến hoặc thừa placeholder → lỗi,
để prompt không bao giờ được gửi đi với chỗ trống. Nội dung người dùng KHÔNG đi qua hàm này:
nó chỉ nằm trong danh sách tin nhắn, không bao giờ được ghép vào system prompt.

Điểm nối cho RAG (Tuần 4): thêm file prompt mới hoặc biến `{{context}}` khi có ngữ cảnh truy xuất;
chưa cài đặt ở Tuần 3.
"""
from __future__ import annotations

import re
from functools import lru_cache

from app.core.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"
_SAFE_NAME = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")
_SAFE_PROMPT = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")


class PromptNotFoundError(LookupError):
    pass


@lru_cache
def _read_template(language_code: str, name: str) -> str:
    if not _SAFE_NAME.fullmatch(language_code) or not _SAFE_PROMPT.fullmatch(name):
        raise PromptNotFoundError("tên prompt hoặc mã ngôn ngữ không hợp lệ")
    path = PROMPTS_DIR / language_code / f"{name}.md"
    if not path.is_file():
        raise PromptNotFoundError(f"chưa có prompt {name!r} cho ngôn ngữ {language_code!r}")
    return path.read_text(encoding="utf-8").strip()


def render_prompt(language_code: str, name: str, **variables: str) -> str:
    template = _read_template(language_code, name)
    needed = set(_PLACEHOLDER.findall(template))
    missing = needed - variables.keys()
    if missing:
        raise ValueError(f"thiếu biến cho prompt {name!r}: {sorted(missing)}")
    return _PLACEHOLDER.sub(lambda match: str(variables[match.group(1)]), template)
