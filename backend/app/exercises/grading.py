"""Chấm bài (hàm thuần, trừ phần gọi LLM ở services).

- mcq, cloze, reorder: quy tắc, không AI.
- error_correction: khớp danh sách câu sửa chấp nhận; không khớp nhưng "có vẻ hợp lệ" → cần LLM phán quyết.
- translate_vi_en: luôn cần LLM chấm theo rubric.
Kết quả LLM được kiểm tra schema chặt: verdict hợp lệ, điểm kẹp trong [0, 1] và khớp verdict, error_type ngoài taxonomy → "other".
Câu trả lời của người học chỉ đi vào prompt chấm dưới dạng DỮ LIỆU trong khối phân cách, đã cắt độ dài.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from app.core.languages import LanguageConfig
from app.exercises.normalize import normalize_answer

ANSWER_OPEN = "<<<BAI_LAM>>>"
ANSWER_CLOSE = "<<<HET_BAI_LAM>>>"
MAX_ANSWER_CHARS = 400
PLAUSIBLE_RATIO = 0.6  # câu sửa không khớp nhưng gần câu chuẩn ≥ 60% → hỏi LLM


@dataclass
class RuleOutcome:
    is_correct: bool | None  # None = cần LLM
    score: float | None
    needs_llm: bool = False
    reason: str = ""


def answer_text(answer: dict) -> str:
    value = answer.get("text") if isinstance(answer, dict) else None
    return value if isinstance(value, str) else ""


def grade_rule(exercise_type: str, payload: dict, key: dict, answer: dict, config: LanguageConfig) -> RuleOutcome:
    norm = config.exercises.normalization
    given = normalize_answer(answer_text(answer), norm)
    if not given:
        return RuleOutcome(False, 0.0, reason="empty_answer")
    if exercise_type == "mcq":
        ok = given == normalize_answer(str(key.get("answer", "")), norm)
        return RuleOutcome(ok, 1.0 if ok else 0.0)
    if exercise_type in {"cloze", "reorder"}:
        ok = given in {normalize_answer(a, norm) for a in key.get("accepted", [])}
        return RuleOutcome(ok, 1.0 if ok else 0.0)
    if exercise_type == "error_correction":
        accepted = [normalize_answer(a, norm) for a in key.get("accepted", [])]
        if given in accepted:
            return RuleOutcome(True, 1.0)
        if given == normalize_answer(str(payload.get("sentence", "")), norm):
            return RuleOutcome(False, 0.0, reason="unchanged")
        best = max((difflib.SequenceMatcher(a=given.split(), b=a.split()).ratio() for a in accepted), default=0.0)
        if best >= PLAUSIBLE_RATIO:
            return RuleOutcome(None, None, needs_llm=True, reason="plausible_alternative")
        return RuleOutcome(False, 0.0, reason="far_from_accepted")
    if exercise_type == "translate_vi_en":
        return RuleOutcome(None, None, needs_llm=True, reason="translation")
    return RuleOutcome(False, 0.0, reason="unknown_type")


def clean_answer(text: str) -> str:
    """Bài làm là DỮ LIỆU: xóa chuỗi phân cách (không cho đóng khối sớm) rồi cắt độ dài."""
    return (text or "").replace(ANSWER_OPEN, "").replace(ANSWER_CLOSE, "")[:MAX_ANSWER_CHARS]


def fence_answer(text: str) -> str:
    return f"{ANSWER_OPEN}\n{clean_answer(text)}\n{ANSWER_CLOSE}"


# ---------- Kết quả LLM chấm ----------


class GraderError(BaseModel):
    error_type: str = Field(max_length=64)
    span: str = Field(default="", max_length=200)
    correction: str = Field(default="", max_length=200)
    explanation_vi: str = Field(default="", max_length=400)


class GraderOutput(BaseModel):
    verdict: Literal["correct", "partially", "incorrect"]
    score: float
    errors: list[GraderError] = Field(default_factory=list, max_length=10)
    feedback_vi: str = Field(default="", max_length=800)


@dataclass
class LlmGrade:
    verdict: str
    score: float
    errors: list[dict] = field(default_factory=list)
    feedback_vi: str = ""


# Khoảng điểm hợp lệ theo verdict (rubric): điểm ngoài khoảng bị kẹp lại.
SCORE_RANGE = {"correct": (0.8, 1.0), "partially": (0.3, 0.79), "incorrect": (0.0, 0.29)}


def finalize_llm_grade(output: GraderOutput, config: LanguageConfig) -> LlmGrade:
    lo, hi = SCORE_RANGE[output.verdict]
    score = min(hi, max(lo, float(output.score)))
    errors = [
        {"error_type": config.normalize_error_type(e.error_type), "span": e.span, "correction": e.correction,
         "explanation_vi": e.explanation_vi}
        for e in output.errors
    ]
    if output.verdict == "correct":
        errors = []
    return LlmGrade(output.verdict, round(score, 2), errors, output.feedback_vi)
