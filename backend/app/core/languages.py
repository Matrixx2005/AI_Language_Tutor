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
class TokenizerConfig:
    unicode_form: str = "NFKC"
    lowercase: bool = True
    strip_diacritics: bool = False
    min_token_length: int = 1
    stopwords: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RetrievalConfig:
    """Khối `retrieval` trong languages/<code>.yaml (Tuần 4). Đường dẫn tính từ thư mục gốc dự án."""

    corpus_file: str
    keywords_file: str | None = None
    tokenizer: TokenizerConfig = TokenizerConfig()


@dataclass(frozen=True)
class ErrorType:
    id: str
    name_vi: str
    description_vi: str
    topics: tuple[str, ...]
    example_wrong: str
    example_right: str


@dataclass(frozen=True)
class NormalizationConfig:
    unicode_form: str = "NFC"
    lowercase: bool = True
    apostrophes: tuple[str, ...] = ()
    quotes: tuple[str, ...] = ()
    strip_final_punctuation: bool = True


@dataclass(frozen=True)
class ExerciseConfig:
    types: tuple[str, ...]
    max_words_by_level: dict
    max_prompt_chars: int = 300
    max_explanation_chars: int = 600
    blocked_keywords: tuple[str, ...] = ()
    normalization: NormalizationConfig = NormalizationConfig()


@dataclass(frozen=True)
class LanguageConfig:
    language_code: str
    display_name: str
    display_name_vi: str
    levels: tuple[LevelConfig, ...]
    placement: PlacementConfig | None = None
    retrieval: RetrievalConfig | None = None
    error_taxonomy: tuple[ErrorType, ...] = ()
    exercises: ExerciseConfig | None = None

    @property
    def error_type_ids(self) -> tuple[str, ...]:
        return tuple(t.id for t in self.error_taxonomy)

    def normalize_error_type(self, value: object) -> str:
        """Mã lỗi (thường do LLM trả) phải thuộc taxonomy; nếu không → "other"."""
        return value if isinstance(value, str) and value in self.error_type_ids else "other"

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
        retrieval=_parse_retrieval(data.get("retrieval"), path.name),
        error_taxonomy=_parse_taxonomy(data.get("error_taxonomy"), path.name),
        exercises=_parse_exercises(data.get("exercises"), tuple(level.code for level in levels), path.name),
    )


def _parse_taxonomy(raw, filename: str) -> tuple[ErrorType, ...]:
    if raw is None:
        return ()
    try:
        types = tuple(
            ErrorType(id=t["id"], name_vi=t["name_vi"], description_vi=t.get("description_vi", ""),
                      topics=tuple(t.get("topics") or ()), example_wrong=t["example"]["wrong"], example_right=t["example"]["right"])
            for t in raw["types"]
        )
    except (KeyError, TypeError) as exc:
        raise UnknownLanguageError(f"File {filename}: error_taxonomy sai cấu trúc") from exc
    ids = [t.id for t in types]
    if len(ids) != len(set(ids)) or "other" not in ids:
        raise UnknownLanguageError(f"File {filename}: error_taxonomy cần id duy nhất và có 'other'")
    return types


def _parse_exercises(raw, level_codes: tuple[str, ...], filename: str) -> ExerciseConfig | None:
    if raw is None:
        return None
    limits = dict(raw.get("max_words_by_level") or {})
    if set(limits) != set(level_codes):
        raise UnknownLanguageError(f"File {filename}: exercises.max_words_by_level phải có đủ mọi trình độ")
    norm = raw.get("normalization") or {}
    return ExerciseConfig(
        types=tuple(raw["types"]),
        max_words_by_level=limits,
        max_prompt_chars=int(raw.get("max_prompt_chars", 300)),
        max_explanation_chars=int(raw.get("max_explanation_chars", 600)),
        blocked_keywords=tuple(str(w).lower() for w in raw.get("blocked_keywords", [])),
        normalization=NormalizationConfig(
            unicode_form=norm.get("unicode_form", "NFC"), lowercase=bool(norm.get("lowercase", True)),
            apostrophes=tuple(norm.get("apostrophes", [])), quotes=tuple(norm.get("quotes", [])),
            strip_final_punctuation=bool(norm.get("strip_final_punctuation", True)),
        ),
    )


def _parse_retrieval(raw, filename: str) -> RetrievalConfig | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("corpus_file"), str):
        raise UnknownLanguageError(f"File {filename}: retrieval cần corpus_file")
    tok = raw.get("tokenizer") or {}
    form = tok.get("unicode_form", "NFKC")
    if form not in {"NFC", "NFKC", "NFD", "NFKD"}:
        raise UnknownLanguageError(f"File {filename}: unicode_form không hợp lệ")
    return RetrievalConfig(
        corpus_file=raw["corpus_file"],
        keywords_file=raw.get("keywords_file"),
        tokenizer=TokenizerConfig(
            unicode_form=form,
            lowercase=bool(tok.get("lowercase", True)),
            strip_diacritics=bool(tok.get("strip_diacritics", False)),
            min_token_length=int(tok.get("min_token_length", 1)),
            stopwords=frozenset(str(w) for w in tok.get("stopwords", [])),
        ),
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
