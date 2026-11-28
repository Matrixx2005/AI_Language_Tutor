"""Taxonomy lỗi + bộ grading_v1: validator, và chấm QUY TẮC tất định khớp 100% nhãn rõ ràng."""
import json
from pathlib import Path

import pytest

from app.core.languages import get_language_config
from app.exercises.grading import grade_rule
from scripts.validate_taxonomy_grading import GRADING, LESSONS, validate_grading, validate_taxonomy

CFG = get_language_config("en")
ITEMS = json.loads(GRADING.read_text(encoding="utf-8"))["items"]
LESSON_IDS = {r["document_id"] for r in json.loads(Path(LESSONS).read_text(encoding="utf-8"))}


def test_taxonomy_and_grading_files_are_valid():
    assert validate_taxonomy(CFG, LESSON_IDS) == []
    assert validate_grading({"items": ITEMS}, CFG) == []
    assert CFG.normalize_error_type("article") == "article" and CFG.normalize_error_type("lạ") == "other"
    assert CFG.normalize_error_type(None) == "other"


def test_taxonomy_validator_rejects_bad_references_and_duplicates():
    from dataclasses import replace

    bad = replace(CFG, error_taxonomy=CFG.error_taxonomy + (replace(CFG.error_taxonomy[0], topics=("gram-en-zz-nope-999",)),))
    errors = " | ".join(validate_taxonomy(bad, LESSON_IDS))
    assert "id trùng" in errors and "không tồn tại" in errors


@pytest.mark.parametrize("item", ITEMS, ids=[i["item_id"] for i in ITEMS])
def test_rule_grader_matches_clear_labels_exactly(item):
    outcome = grade_rule(item["exercise_type"], item["prompt"], item["answer_key"], {"text": item["learner_answer"]}, CFG)
    expected = item["rule_expected"]
    if expected == "needs_llm":
        assert outcome.needs_llm, item["case"]
    else:
        assert outcome.needs_llm is False and outcome.is_correct is (expected == "correct"), item["case"]
