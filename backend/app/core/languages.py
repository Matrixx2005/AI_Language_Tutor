"""Cấu hình ngôn ngữ/trình độ đọc từ languages/<code>.yaml. Không hardcode CEFR trong code."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.core.config import PROJECT_ROOT

LANGUAGES_DIR = PROJECT_ROOT / "languages"
_CODE_PATTERN = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")  # chặn path traversal


class UnknownLanguageError(ValueError):
    pass


@dataclass(frozen=True)
class LevelConfig:
    code: str
    display_name: str
    display_name_vi: str


@dataclass(frozen=True)
class PlacementConfig:
    """Ngưỡng xếp trình độ (phần trăm), theo thứ tự trình độ tăng dần. Quy tắc: trình độ CAO NHẤT
    có ngưỡng ≤ điểm (YAML gọi là `highest_level_threshold_not_exceeded`)."""

    thresholds: tuple[tuple[str, float], ...]
    status: str  # ví dụ "provisional": chưa hiệu chuẩn trên người học thật
    question_set: str | None = None  # bộ câu hỏi trong bảng `questions`; None = chưa có bài placement


@dataclass(frozen=True)
class LanguageConfig:
    language_code: str
    display_name: str
    display_name_vi: str
    levels: tuple[LevelConfig, ...]
    placement: PlacementConfig | None = None

    @property
    def level_codes(self) -> tuple[str, ...]:
        return tuple(level.code for level in self.levels)

    @property
    def default_level_code(self) -> str:
        """Trình độ thấp nhất (mục đầu tiên trong YAML) cho người học mới."""
        return self.levels[0].code

    def is_valid_level(self, level_code: str) -> bool:
        return level_code in self.level_codes


@lru_cache
def get_language_config(language_code: str) -> LanguageConfig:
    if not _CODE_PATTERN.fullmatch(language_code):
        raise UnknownLanguageError(f"Mã ngôn ngữ không hợp lệ: {language_code!r}")
    path = LANGUAGES_DIR / f"{language_code}.yaml"
    if not path.is_file():
        raise UnknownLanguageError(f"Chưa có cấu hình ngôn ngữ: {language_code!r}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        levels = tuple(
            LevelConfig(
                code=level["code"],
                display_name=level.get("display_name", level["code"]),
                display_name_vi=level.get("display_name_vi", level.get("display_name", level["code"])),
            )
            for level in data.get("levels", [])
        )
    except (KeyError, TypeError) as exc:
        raise UnknownLanguageError(f"File {path.name}: mỗi level cần có 'code'") from exc
    if data.get("language_code") != language_code or not levels:
        raise UnknownLanguageError(f"File {path.name} thiếu language_code hoặc levels")

    display_name = data.get("display_name", language_code)
    return LanguageConfig(
        language_code=language_code,
        display_name=display_name,
        display_name_vi=data.get("display_name_vi", display_name),
        levels=levels,
        placement=_parse_placement(data.get("placement"), tuple(level.code for level in levels), path.name),
    )


SUPPORTED_PLACEMENT_RULE = "highest_level_threshold_not_exceeded"


def _parse_placement(raw, level_codes: tuple[str, ...], filename: str) -> PlacementConfig | None:
    """Kiểm tra chặt: cấu hình sai thì báo lỗi ngay, không âm thầm chấm sai."""
    if raw is None:
        return None
    if raw.get("score_scale") != "percent" or raw.get("assignment_rule") != SUPPORTED_PLACEMENT_RULE:
        raise UnknownLanguageError(f"File {filename}: placement chỉ hỗ trợ score_scale=percent, "
                                   f"assignment_rule={SUPPORTED_PLACEMENT_RULE}")
    thresholds = raw.get("thresholds") or {}
    if set(thresholds) - set(level_codes):
        raise UnknownLanguageError(f"File {filename}: ngưỡng placement cho trình độ không tồn tại")
    ordered = tuple((code, float(thresholds[code])) for code in level_codes if code in thresholds)
    if not ordered or ordered[0] != (level_codes[0], 0.0):
        raise UnknownLanguageError(f"File {filename}: trình độ thấp nhất phải có ngưỡng 0")
    values = [value for _, value in ordered]
    if values != sorted(values) or len(set(values)) != len(values) or values[-1] > 100:
        raise UnknownLanguageError(f"File {filename}: ngưỡng placement phải tăng dần trong 0–100")
    question_set = raw.get("question_set")
    return PlacementConfig(
        thresholds=ordered,
        status=str(raw.get("status", "")),
        question_set=str(question_set) if question_set else None,
    )
