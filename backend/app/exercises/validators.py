"""Bộ kiểm tra bài tập do AI sinh (hàm thuần). Kết quả: danh sách mã lý do loại (rỗng = hợp lệ).

Dạng bài và dữ liệu (prompt_payload công khai / answer_key chỉ phía máy chủ):
  mcq              payload {question, options[4]}           key {answer}
  cloze            payload {sentence có đúng 1 "___"}       key {accepted[]}
  error_correction payload {sentence có đúng 1 lỗi}         key {accepted[], wrong_span, correction}
  reorder          payload {tokens[]}                        key {accepted[]}
  translate_vi_en  payload {source_vi}                       key {reference, rubric[]}
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass

from app.core.languages import LanguageConfig
from app.exercises.normalize import normalize_answer, words

BLANK = re.compile(r"_{3,}")


@dataclass(frozen=True)
class Draft:
    exercise_type: str
    level_code: str
    error_type: str
    document_id: str
    payload: dict
    answer_key: dict
    explanation: str


def content_hash(language_code: str, exercise_type: str, payload: dict, config: LanguageConfig) -> str:
    """Khử trùng lặp: băm phần đề đã chuẩn hóa (không phân biệt hoa thường, khoảng trắng, dấu câu cuối)."""
    norm = config.exercises.normalization
    canonical = json.dumps({k: (normalize_answer(v, norm) if isinstance(v, str) else
                                sorted(normalize_answer(x, norm) for x in v) if isinstance(v, list) else v)
                            for k, v in sorted(payload.items())}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(f"{language_code}|{exercise_type}|{canonical}".encode("utf-8")).hexdigest()


def _text_fields(payload: dict) -> list[str]:
    out = []
    for value in payload.values():
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            out.extend(str(v) for v in value)
    return out


def _accepted(key: dict) -> list[str]:
    acc = key.get("accepted")
    return [a for a in acc if isinstance(a, str) and a.strip()] if isinstance(acc, list) else []


def validate_draft(draft: Draft, config: LanguageConfig, lesson_document_ids: set[str],
                   existing_hashes: set[str] | frozenset = frozenset()) -> list[str]:
    ex_cfg = config.exercises
    norm = ex_cfg.normalization
    reasons: list[str] = []
    t, p, k = draft.exercise_type, draft.payload or {}, draft.answer_key or {}

    # Chung: dạng, trình độ, taxonomy, chủ đề, độ dài, nội dung.
    if t not in ex_cfg.types:
        return ["unknown_type"]
    if draft.level_code not in config.level_codes:
        reasons.append("invalid_level")
    if draft.error_type not in config.error_type_ids:
        reasons.append("error_type_not_in_taxonomy")
    if draft.document_id not in lesson_document_ids:
        reasons.append("unknown_document")
    else:
        topics = next((et.topics for et in config.error_taxonomy if et.id == draft.error_type), ())
        if topics and draft.document_id not in topics:
            reasons.append("topic_mismatch")
    fields = _text_fields(p)
    if not fields or any(not f.strip() for f in fields):
        reasons.append("empty_field")
    if any(len(f) > ex_cfg.max_prompt_chars for f in fields):
        reasons.append("prompt_too_long")
    if not draft.explanation.strip():
        reasons.append("missing_explanation")
    elif len(draft.explanation) > ex_cfg.max_explanation_chars:
        reasons.append("explanation_too_long")
    blob = " ".join(fields + [draft.explanation]).lower()
    if any(re.search(rf"\b{re.escape(w)}\b", blob) for w in ex_cfg.blocked_keywords):
        reasons.append("blocked_content")
    limit = ex_cfg.max_words_by_level.get(draft.level_code)
    main_text = p.get("question") or p.get("sentence") or " ".join(p.get("tokens") or []) or p.get("source_vi") or ""
    if limit and len(words(main_text)) > limit:
        reasons.append("too_hard_for_level")

    # Theo dạng.
    if t == "mcq":
        options = p.get("options")
        answer = k.get("answer")
        if not isinstance(options, list) or len(options) != 4:
            reasons.append("mcq_needs_4_options")
        else:
            normalized = [normalize_answer(str(o), norm) for o in options]
            if len(set(normalized)) != 4:
                reasons.append("mcq_duplicate_options")
            if not isinstance(answer, str) or normalized.count(normalize_answer(answer, norm)) != 1:
                reasons.append("mcq_not_exactly_one_correct")
            elif len(normalize_answer(answer, norm)) >= 2 and normalize_answer(answer, norm) in words(str(p.get("question", ""))):
                reasons.append("answer_leaked_in_prompt")
    elif t == "cloze":
        sentence = str(p.get("sentence", ""))
        accepted = _accepted(k)
        if len(BLANK.findall(sentence)) != 1:
            reasons.append("cloze_not_exactly_one_blank")
        if not accepted:
            reasons.append("missing_accepted_answers")
        elif any(len(words(a)) > 4 for a in accepted):
            reasons.append("cloze_answer_too_long")
        elif any(re.search(rf"\b{re.escape(normalize_answer(a, norm))}\b", normalize_answer(BLANK.sub(" ", sentence), norm))
                 for a in accepted if len(normalize_answer(a, norm)) > 2):
            reasons.append("answer_leaked_in_prompt")
    elif t == "error_correction":
        wrong = str(p.get("sentence", ""))
        accepted = _accepted(k)
        if not accepted:
            reasons.append("missing_accepted_answers")
        else:
            w_tokens = normalize_answer(wrong, norm).split()
            for a in accepted:
                a_tokens = normalize_answer(a, norm).split()
                if a_tokens == w_tokens:
                    reasons.append("correction_equals_wrong")
                    break
                regions = [op for op in difflib.SequenceMatcher(a=w_tokens, b=a_tokens).get_opcodes() if op[0] != "equal"]
                if len(regions) != 1:
                    reasons.append("not_exactly_one_error")
                    break
    elif t == "reorder":
        tokens = p.get("tokens")
        accepted = _accepted(k)
        if not isinstance(tokens, list) or len(tokens) < 3:
            reasons.append("reorder_too_few_tokens")
        elif not accepted:
            reasons.append("missing_accepted_answers")
        else:
            bag = Counter(words(" ".join(tokens)))
            if any(Counter(words(a)) != bag for a in accepted):
                reasons.append("reorder_tokens_mismatch")
            elif any(normalize_answer(" ".join(tokens), norm) == normalize_answer(a, norm) for a in accepted):
                reasons.append("answer_leaked_in_prompt")
    elif t == "translate_vi_en":
        reference = k.get("reference")
        rubric = k.get("rubric")
        if not isinstance(reference, str) or not reference.strip():
            reasons.append("missing_reference")
        if not isinstance(rubric, list) or not 1 <= len(rubric) <= 5:
            reasons.append("rubric_needs_1_to_5_points")
        if isinstance(reference, str) and limit and len(words(reference)) > limit:
            reasons.append("too_hard_for_level")

    h = content_hash(config.language_code, t, p, config)
    if h in existing_hashes:
        reasons.append("duplicate")
    return sorted(set(reasons))
