"""Sinh bài tập từ MỘT bài học (ngữ cảnh = đúng nội dung bài, không cần truy xuất) + kiểm tra độc lập.

Không chạm DB: script gọi các hàm này rồi mới ghi DB (không giữ giao dịch khi gọi LLM)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.core.languages import LanguageConfig
from app.core.prompts import render_prompt
from app.exercises.grading import grade_rule
from app.exercises.validators import Draft
from app.llm.service import LLMService
from app.llm.types import ChatMessage, LLMRequest
from app.retrieval.corpus import Lesson

PROMPT_VERSION = "exercise_generate_v1.1"  # v1.1: bắt buộc "accepted" (sửa 1 lần sau vòng 1, 15 bài thiếu đáp án)
ExerciseType = Literal["mcq", "cloze", "error_correction", "reorder", "translate_vi_en"]


class GeneratedItem(BaseModel):
    exercise_type: ExerciseType
    error_type: str = Field(max_length=64)
    question: str | None = None
    options: list[str] | None = None
    answer: str | None = None
    sentence: str | None = None
    accepted: list[str] | None = None
    wrong_span: str | None = None
    correction: str | None = None
    tokens: list[str] | None = None
    source_vi: str | None = None
    reference: str | None = None
    rubric: list[str] | None = None
    explanation_vi: str = ""


class GenerationOutput(BaseModel):
    items: list[GeneratedItem] = Field(max_length=10)


def allowed_error_types(config: LanguageConfig, document_id: str) -> list[str]:
    """Loại lỗi gắn với bài (theo topics trong taxonomy); luôn kèm loại không gắn chủ đề cụ thể."""
    linked = [t.id for t in config.error_taxonomy if document_id in t.topics]
    generic = [t.id for t in config.error_taxonomy if not t.topics]
    return linked + generic


def types_for(lesson_index: int, count: int, types: tuple[str, ...]) -> list[str]:
    """Xoay vòng dạng bài theo chỉ số bài học → mọi dạng đều có, phân bố đều trên toàn corpus."""
    return [types[(lesson_index + i) % len(types)] for i in range(count)]


def build_generation_request(lesson: Lesson, config: LanguageConfig, exercise_types: list[str]) -> LLMRequest:
    level = next((lv for lv in config.levels if lv.code == lesson.level), None)
    prompt = render_prompt(
        config.language_code, "exercise_generate", count=str(len(exercise_types)), document_id=lesson.document_id,
        title=lesson.title, topic=lesson.topic, level_code=lesson.level, level_name=level.display_name_vi if level else lesson.level,
        lesson=lesson.content.replace("<<<", "").replace(">>>", ""), types=", ".join(exercise_types),
        error_types=", ".join(allowed_error_types(config, lesson.document_id)),
        max_words=str(config.exercises.max_words_by_level[lesson.level]),
    )
    return LLMRequest(system_prompt=prompt, messages=(ChatMessage("user", "Create the exercises now."),),
                      response_schema=GenerationOutput, max_output_tokens=4096)


def to_draft(item: GeneratedItem, lesson: Lesson) -> Draft:
    t = item.exercise_type
    if t == "mcq":
        payload, key = {"question": item.question or "", "options": item.options or []}, {"answer": item.answer or ""}
    elif t == "cloze":
        payload, key = {"sentence": item.sentence or ""}, {"accepted": item.accepted or []}
    elif t == "error_correction":
        payload = {"sentence": item.sentence or ""}
        key = {"accepted": item.accepted or [], "wrong_span": item.wrong_span or "", "correction": item.correction or ""}
    elif t == "reorder":
        payload, key = {"tokens": item.tokens or []}, {"accepted": item.accepted or []}
    else:
        payload, key = {"source_vi": item.source_vi or ""}, {"reference": item.reference or "", "rubric": item.rubric or []}
    return Draft(exercise_type=t, level_code=lesson.level, error_type=item.error_type, document_id=lesson.document_id,
                 payload=payload, answer_key=key, explanation=item.explanation_vi.strip())


def generation_meta(model: str, rag_mode: str = "lesson_context") -> dict:
    return {"model_id": model, "prompt_version": PROMPT_VERSION, "rag_mode": rag_mode,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def generate_for_lesson(llm: LLMService, lesson: Lesson, config: LanguageConfig, exercise_types: list[str]) -> tuple[list[Draft], str]:
    result = llm.generate(build_generation_request(lesson, config, exercise_types))
    output: GenerationOutput = result.parsed
    return [to_draft(item, lesson) for item in output.items], result.model


# ---------- Kiểm tra độc lập ----------

SOLVABLE = {"mcq", "cloze", "error_correction", "reorder"}


class SolvedItem(BaseModel):
    id: str
    answer: str = Field(max_length=300)


class SolveOutput(BaseModel):
    answers: list[SolvedItem]


def build_solve_request(drafts: list[tuple[str, Draft]], config: LanguageConfig) -> LLMRequest:
    lines = []
    for item_id, d in drafts:
        p = d.payload
        body = {"mcq": lambda: f"{p['question']} | options: {' / '.join(p['options'])}",
                "cloze": lambda: p["sentence"], "error_correction": lambda: p["sentence"],
                "reorder": lambda: " / ".join(p["tokens"])}[d.exercise_type]()
        lines.append(f"{item_id} [{d.exercise_type}]: {body}".replace("<<<", "").replace(">>>", ""))
    prompt = render_prompt(config.language_code, "exercise_solve", items="\n".join(lines))
    return LLMRequest(system_prompt=prompt, messages=(ChatMessage("user", "Solve the exercises."),),
                      response_schema=SolveOutput, max_output_tokens=2048)


def independent_matches(drafts: list[tuple[str, Draft]], solved: SolveOutput, config: LanguageConfig) -> dict[str, bool]:
    """True khi lời giải độc lập khớp answer_key theo đúng bộ chấm quy tắc. Thiếu/AMBIGUOUS → False."""
    answers = {s.id: s.answer for s in solved.answers}
    out = {}
    for item_id, d in drafts:
        given = answers.get(item_id, "")
        if not given or given.strip().upper() == "AMBIGUOUS":
            out[item_id] = False
            continue
        outcome = grade_rule(d.exercise_type, d.payload, d.answer_key, {"text": given}, config)
        out[item_id] = bool(outcome.is_correct)
    return out
