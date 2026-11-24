"""Chấm placement (hàm thuần). Điểm kỳ vọng tính TAY ở chú thích từng test."""
import json
from pathlib import Path

import pytest

from app.core.languages import UnknownLanguageError, _parse_placement, get_language_config
from app.services.placement_scoring import (
    PlacementAnswerError,
    ScoringQuestion,
    assign_level,
    score_placement,
)

EN = get_language_config("en").placement  # A1: 0, A2: 40, B1: 70 (tạm thời)
LEVELS = ["A1", "A2", "B1"]


def bank() -> list[ScoringQuestion]:
    """30 câu như bộ thật: mỗi trình độ 5 ngữ pháp + 5 từ vựng; đáp án đúng luôn là "dung"."""
    questions = []
    for level in LEVELS:
        for category in ("grammar", "vocabulary"):
            for i in range(5):
                questions.append(ScoringQuestion(
                    f"{level}-{category}-{i}", level, category, f"{level} {category} topic {i}",
                    ("dung", "sai1", "sai2", "sai3"), "dung",
                ))
    return questions


def answer_first(n: int, questions=None) -> dict[str, str]:
    """Trả lời đúng n câu đầu, sai các câu còn lại."""
    questions = questions or bank()
    return {q.question_id: ("dung" if i < n else "sai1") for i, q in enumerate(questions)}


# ---------- Ngưỡng ở ranh giới (30 câu: A2 ≥ 40% = 12 câu, B1 ≥ 70% = 21 câu) ----------


@pytest.mark.parametrize(
    ("correct", "expected_level"),
    [
        (0, "A1"),
        (11, "A1"),  # 36,7% — thiếu một câu so với ngưỡng A2
        (12, "A2"),  # 40,0% — vừa đủ ngưỡng A2
        (20, "A2"),  # 66,7% — thiếu một câu so với ngưỡng B1
        (21, "B1"),  # 70,0% — vừa đủ ngưỡng B1
        (30, "B1"),
    ],
)
def test_level_at_threshold_boundaries(correct, expected_level):
    outcome = score_placement(bank(), answer_first(correct), EN)
    assert (outcome.correct, outcome.total, outcome.level_code) == (correct, 30, expected_level)


def test_exact_percent_boundary_without_float_error():
    # 7/10 = 70% đúng ngưỡng: không được rơi xuống do 0.7 * 100 = 70.00000000000001
    assert assign_level(7, 10, EN) == "B1"
    assert assign_level(4, 10, EN) == "A2"
    assert assign_level(0, 0, EN) == "A1"


# ---------- Toàn đúng / toàn sai / bỏ trống ----------


def test_all_correct():
    outcome = score_placement(bank(), answer_first(30), EN)
    assert (outcome.correct, outcome.percent, outcome.level_code) == (30, 100.0, "B1")
    assert outcome.weak_groups == () and outcome.missed_topics == ()


def test_all_wrong():
    outcome = score_placement(bank(), answer_first(0), EN)
    assert (outcome.correct, outcome.level_code) == (0, "A1")
    assert len(outcome.weak_groups) == 6


@pytest.mark.parametrize("answers", [{}, {"A1-grammar-0": None}, {"A1-grammar-0": ""}])
def test_blank_answers_count_as_wrong(answers):
    outcome = score_placement(bank(), answers, EN)
    assert outcome.correct == 0 and outcome.level_code == "A1"
    assert outcome.results[0].selected is None and not outcome.results[0].is_correct


# ---------- Nhóm yếu và chủ đề cần ôn (tính tay) ----------


def test_weak_groups_and_missed_topics():
    questions = bank()
    answers = answer_first(30, questions)
    # A2 ngữ pháp: sai 3/5 → đúng 2/5 = 40% < 60% → YẾU
    for i in (0, 1, 2):
        answers[f"A2-grammar-{i}"] = "sai2"
    # B1 từ vựng: sai 2/5 → đúng 3/5 = 60% → KHÔNG yếu (ngưỡng là < 60%)
    for i in (0, 1):
        answers[f"B1-vocabulary-{i}"] = "sai3"

    outcome = score_placement(questions, answers, EN)

    assert outcome.correct == 25 and outcome.level_code == "B1"  # 25/30 = 83,3%
    assert [(g.level_code, g.category, g.correct, g.total) for g in outcome.weak_groups] == [("A2", "grammar", 2, 5)]
    groups = {(g.level_code, g.category): g for g in outcome.groups}
    assert groups[("B1", "vocabulary")].percent == 60.0 and not groups[("B1", "vocabulary")].weak
    assert outcome.missed_topics == (
        "A2 grammar topic 0", "A2 grammar topic 1", "A2 grammar topic 2",
        "B1 vocabulary topic 0", "B1 vocabulary topic 1",
    )
    assert [g.level_code for g in outcome.groups] == ["A1", "A1", "A2", "A2", "B1", "B1"]  # theo thứ tự trình độ


def test_missed_topics_are_unique():
    questions = [
        ScoringQuestion("q1", "A1", "grammar", "verb be", ("a", "b"), "a"),
        ScoringQuestion("q2", "A1", "grammar", "verb be", ("a", "b"), "a"),
    ]
    assert score_placement(questions, {"q1": "b", "q2": "b"}, EN).missed_topics == ("verb be",)


# ---------- Câu hỏi lạ / lựa chọn không hợp lệ ----------


def test_unknown_question_is_rejected():
    with pytest.raises(PlacementAnswerError) as caught:
        score_placement(bank(), {"cau-la": "dung"}, EN)
    assert caught.value.code == "unknown_question" and caught.value.question_ids == ["cau-la"]


def test_option_not_in_question_is_rejected():
    with pytest.raises(PlacementAnswerError) as caught:
        score_placement(bank(), {"A1-grammar-0": "khong-co-trong-de"}, EN)
    assert caught.value.code == "invalid_option"


# ---------- Bộ câu hỏi thật ----------


def test_real_placement_answer_key_scores_full_marks():
    data = json.loads((Path(__file__).resolve().parents[2] / "data/evaluation/placement_v1.json").read_text(encoding="utf-8"))
    questions = [
        ScoringQuestion(q["question_id"], q["level_code"], q["category"], q["topic"], tuple(q["options"]), q["correct_answer"])
        for q in data
    ]
    outcome = score_placement(questions, {q.question_id: q.correct_answer for q in questions}, EN)
    assert (outcome.correct, outcome.total, outcome.level_code) == (30, 30, "B1")


# ---------- Cấu hình ngưỡng ----------


def test_english_placement_config_is_loaded_and_provisional():
    assert EN.thresholds == (("A1", 0.0), ("A2", 40.0), ("B1", 70.0))
    assert EN.status == "provisional"


@pytest.mark.parametrize(
    "raw",
    [
        {"score_scale": "points", "assignment_rule": "highest_level_threshold_not_exceeded", "thresholds": {"A1": 0}},
        {"score_scale": "percent", "assignment_rule": "khac", "thresholds": {"A1": 0}},
        {"score_scale": "percent", "assignment_rule": "highest_level_threshold_not_exceeded", "thresholds": {"A2": 40}},
        {"score_scale": "percent", "assignment_rule": "highest_level_threshold_not_exceeded", "thresholds": {"A1": 0, "A2": 70, "B1": 40}},
        {"score_scale": "percent", "assignment_rule": "highest_level_threshold_not_exceeded", "thresholds": {"A1": 0, "C2": 90}},
        {"score_scale": "percent", "assignment_rule": "highest_level_threshold_not_exceeded", "thresholds": {"A1": 0, "B1": 120}},
    ],
)
def test_invalid_placement_config_is_rejected(raw):
    with pytest.raises(UnknownLanguageError):
        _parse_placement(raw, ("A1", "A2", "B1"), "test.yaml")


def test_shared_scoring_logic_has_no_hardcoded_levels():
    source = (Path(__file__).resolve().parents[1] / "app/services/placement_scoring.py").read_text(encoding="utf-8")
    for code in ("A1", "A2", "B1", "B2", "C1"):
        assert f'"{code}"' not in source and f"'{code}'" not in source
