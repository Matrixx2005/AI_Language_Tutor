"""Smoke test RAG với TÀI NGUYÊN THẬT — mặc định BỎ QUA.

Cần: Qdrant đang chạy + đã nạp index (scripts/index_corpus.py), model BGE-M3 trong EMBEDDING_CACHE_DIR.
  $env:RUN_RAG_SMOKE = "1"; pytest backend/tests/test_rag_smoke.py -s          # chỉ truy xuất (không gọi LLM)
  $env:RUN_RAG_SMOKE_LLM = "1"  (thêm)                                          # + 2 lời gọi Gemini thật qua API chat
Lời gọi Gemini ép LLM_MAX_RETRIES=0 và không model dự phòng: đúng 1 lời gọi mỗi câu hỏi. Chỉ in metadata
và 300 ký tự đầu câu trả lời; không in key. Chạy trên DB test, rollback sau mỗi test.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_RAG_SMOKE") != "1", reason="smoke RAG dùng model/Qdrant thật; đặt RUN_RAG_SMOKE=1")

# Câu hỏi riêng cho smoke (KHÔNG lấy từ test split).
SMOKE_QUESTIONS = [
    ("hybrid", "Khi nào dùng 'an' thay vì 'a'? Cho ví dụ với từ 'hour'.", "gram-en-a1-articles-003"),
    ("dense", "Câu bị động ở thì quá khứ đơn được tạo như thế nào?", "gram-en-b1-passive-voice-028"),
]


@pytest.mark.parametrize(("mode", "question", "gold"), SMOKE_QUESTIONS)
def test_real_retrieval_finds_expected_lesson(mode, question, gold):
    from app.core.config import get_settings
    from app.retrieval.service import build_retriever

    hits = build_retriever(mode, get_settings()).search(question, "en", 3)
    print(f"\n[rag-smoke retrieval {mode}] top3={[(h.document_id, h.score) for h in hits]}")
    assert gold in [h.document_id for h in hits]


@pytest.mark.skipif(os.environ.get("RUN_RAG_SMOKE_LLM") != "1", reason="đặt thêm RUN_RAG_SMOKE_LLM=1 để gọi Gemini thật")
@pytest.mark.parametrize(("mode", "question", "gold"), SMOKE_QUESTIONS)
def test_real_rag_chat_end_to_end(client, register_and_login, monkeypatch, mode, question, gold):
    from app.api.deps import get_llm
    from app.core.config import get_settings
    from app.llm import build_llm_service

    settings = get_settings().model_copy(update={"llm_provider": "gemini", "llm_max_retries": 0, "llm_fallback_model_ids": ""})
    service = build_llm_service(settings)
    client.app.dependency_overrides[get_llm] = lambda: service
    headers = register_and_login("rag-smoke@example.com")
    sid = client.post("/api/v1/chat/sessions", headers=headers).json()["session_id"]

    response = client.post(f"/api/v1/chat/sessions/{sid}/messages", headers=headers, json={"content": question, "rag_mode": mode})

    assert response.status_code == 200, response.json()
    body = response.json()
    a = body["assistant_message"]
    print(f"\n[rag-smoke chat {mode}] rag_mode={a['rag_mode']} fallback={a['rag_fallback']} "
          f"sources={[(s['n'], s['document_id'], s['cited']) for s in a['sources'] or []]} has_citations={body['has_citations']}")
    labels = [lb for lb in ("Quy tắc:", "Cấu trúc:", "Ví dụ:", "Lỗi thường gặp:", "Tự kiểm tra:") if lb in a["content"]]
    print(f"[rag-smoke chat {mode}] chars={len(a['content'])} asterisks={a['content'].count('*')} labels={labels}")
    print(f"[rag-smoke chat {mode}] answer={a['content'][:900]!r}")
    assert a["rag_mode"] == mode and a["rag_fallback"] is False
    assert gold in [s["document_id"] for s in a["sources"]]
