"""Smoke test BÀI TẬP với Gemini THẬT — mặc định BỎ QUA. Đặt RUN_EXERCISE_SMOKE=1.

2 lời gọi: (1) sinh bài cho 1 bài học (không ghi DB); (2) nộp 1 bài dịch qua API trên DB test → LLM chấm.
max_retries=0, không model dự phòng. Chỉ in metadata + tóm tắt ngắn, không in key.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_EXERCISE_SMOKE") != "1", reason="smoke bài tập gọi Gemini thật; đặt RUN_EXERCISE_SMOKE=1")


def _llm():
    from app.core.config import get_settings
    from app.llm import build_llm_service

    return build_llm_service(get_settings().model_copy(update={"llm_provider": "gemini", "llm_max_retries": 0, "llm_fallback_model_ids": ""}))


def test_real_generation_produces_valid_exercises():
    from app.core.languages import get_language_config
    from app.exercises.validators import validate_draft
    from app.retrieval.corpus import load_lessons
    from app.services.exercise_generation import generate_for_lesson

    config = get_language_config("en")
    lesson = next(x for x in load_lessons("en") if x.document_id == "gram-en-a2-past-simple-006")
    drafts, model = generate_for_lesson(_llm(), lesson, config, ["mcq", "cloze", "error_correction"])
    reasons = [validate_draft(d, config, {x.document_id for x in load_lessons("en")}) for d in drafts]
    print(f"\n[exercise-smoke generate] model={model} drafts={len(drafts)} reasons={reasons}")
    assert len(drafts) == 3 and sum(1 for r in reasons if not r) >= 2


def test_real_llm_grading_through_api(client, register_and_login, db_session):
    from app.api.routes.exercises import get_grader_llm
    from app.core.languages import get_language_config
    from app.exercises.validators import content_hash
    from app.models import Exercise

    payload, key = {"source_vi": "Tôi chưa bao giờ đi máy bay."}, {"reference": "I have never traveled by plane.", "rubric": ["thì hiện tại hoàn thành"]}
    ex = Exercise(language_code="en", level_code="A2", exercise_type="translate_vi_en", document_id="gram-en-a2-present-perfect-011",
                  topic="present perfect", error_type="tense_form", prompt_payload=payload, answer_key=key, explanation="Dùng have never + V3.",
                  content_hash=content_hash("en", "translate_vi_en", payload, get_language_config("en")), validation_status="validated")
    db_session.add(ex)
    db_session.flush()
    llm = _llm()
    client.app.dependency_overrides[get_grader_llm] = lambda: llm
    headers = register_and_login("exercise-smoke@example.com")
    r = client.post(f"/api/v1/exercises/{ex.exercise_id}/attempts", headers=headers, json={"answer": {"text": "I never go by plane."}})
    body = r.json()
    print(f"\n[exercise-smoke grade] status={r.status_code} graded_by={body.get('graded_by')} verdict={body.get('feedback', {}).get('verdict')} "
          f"score={body.get('score')} error_types={body.get('error_types')}")
    assert r.status_code == 201 and body["graded_by"] == "llm" and body["is_correct"] is False
