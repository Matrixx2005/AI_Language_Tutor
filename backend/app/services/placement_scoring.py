"""Chấm bài placement (hàm thuần: không DB, không HTTP, không LLM).

Không chứa mã trình độ cố định: trình độ và ngưỡng lấy từ languages/<code>.yaml (PlacementConfig).
So sánh ngưỡng bằng số nguyên (đúng × 100 ≥ ngưỡng × tổng) để không sai ở ranh giới do dấu phẩy động.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.core.languages import PlacementConfig

# Quyết định Tuần 3, mục 6: nhóm (trình độ × loại câu hỏi) đúng dưới ngưỡng này là "yếu".
WEAK_GROUP_THRESHOLD_PERCENT = 60


class PlacementAnswerError(ValueError):
    def __init__(self, code: str, question_ids: Sequence[str]) -> None:
        super().__init__(code)
        self.code = code
        self.question_ids = list(question_ids)


@dataclass(frozen=True)
class ScoringQuestion:
    question_id: str
    level_code: str
    category: str
    topic: str
    options: tuple[str, ...]
    correct_answer: str


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    selected: str | None
    is_correct: bool


@dataclass(frozen=True)
class GroupResult:
    level_code: str
    category: str
    correct: int
    total: int
    weak: bool

    @property
    def percent(self) -> float:
        return round(100 * self.correct / self.total, 1) if self.total else 0.0


@dataclass(frozen=True)
class PlacementOutcome:
    correct: int
    total: int
    level_code: str
    groups: tuple[GroupResult, ...]
    missed_topics: tuple[str, ...]  # chủ đề của câu sai/bỏ trống, theo thứ tự câu hỏi, không trùng
    results: tuple[QuestionResult, ...]

    @property
    def percent(self) -> float:
        return round(100 * self.correct / self.total, 1) if self.total else 0.0

    @property
    def weak_groups(self) -> tuple[GroupResult, ...]:
        return tuple(group for group in self.groups if group.weak)


def _check_answers(questions: Sequence[ScoringQuestion], answers: Mapping[str, str | None]) -> None:
    known = {q.question_id: q for q in questions}
    unknown = [qid for qid in answers if qid not in known]
    if unknown:
        raise PlacementAnswerError("unknown_question", unknown)
    invalid = [
        qid for qid, value in answers.items()
        if value not in (None, "") and value not in known[qid].options
    ]
    if invalid:
        raise PlacementAnswerError("invalid_option", invalid)


def assign_level(correct: int, total: int, placement: PlacementConfig) -> str:
    """Trình độ CAO NHẤT có ngưỡng ≤ điểm phần trăm (so sánh nguyên, không làm tròn)."""
    level = placement.thresholds[0][0]
    for level_code, threshold in placement.thresholds:
        if total > 0 and correct * 100 >= threshold * total:
            level = level_code
    return level


def score_placement(
    questions: Sequence[ScoringQuestion],
    answers: Mapping[str, str | None],
    placement: PlacementConfig,
    *,
    weak_threshold_percent: float = WEAK_GROUP_THRESHOLD_PERCENT,
) -> PlacementOutcome:
    """`answers`: question_id → lựa chọn; thiếu, None hoặc "" = bỏ trống (tính sai).
    Câu hỏi lạ → `unknown_question`; lựa chọn không có trong đề → `invalid_option`."""
    _check_answers(questions, answers)

    results = tuple(
        QuestionResult(q.question_id, answers.get(q.question_id) or None, answers.get(q.question_id) == q.correct_answer)
        for q in questions
    )
    correct = sum(r.is_correct for r in results)

    level_order = [code for code, _ in placement.thresholds]
    tally: dict[tuple[str, str], list[int]] = {}
    for question, result in zip(questions, results, strict=True):
        counts = tally.setdefault((question.level_code, question.category), [0, 0])
        counts[0] += result.is_correct
        counts[1] += 1
    order = {code: index for index, code in enumerate(level_order)}
    groups = tuple(
        GroupResult(level, category, ok, total, ok * 100 < weak_threshold_percent * total)
        for (level, category), (ok, total) in sorted(
            tally.items(), key=lambda item: (order.get(item[0][0], len(order)), item[0][1])
        )
    )

    missed: list[str] = []
    for question, result in zip(questions, results, strict=True):
        if not result.is_correct and question.topic not in missed:
            missed.append(question.topic)

    return PlacementOutcome(
        correct=correct,
        total=len(questions),
        level_code=assign_level(correct, len(questions), placement),
        groups=groups,
        missed_topics=tuple(missed),
        results=results,
    )
