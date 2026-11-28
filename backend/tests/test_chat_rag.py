"""Chat với RAG qua HTTP (DB test, FakeLLM, Qdrant :memory: + bộ nhúng giả trên corpus THẬT)."""
import logging

import pytest
from qdrant_client import QdrantClient
from sqlalchemy import select

from app.api.deps import get_llm, get_retriever_for
from app.core.config import get_settings
from app.llm.fake import FakeLLM, Reply
from app.llm.service import LLMService
from app.models import ChatMessageRow
from app.retrieval.citations import CONTEXT_OPEN
from app.retrieval.corpus import corpus_chunks
from app.retrieval.dense import DenseRetriever
from app.retrieval.embedder import HashingEmbedder
from app.retrieval.service import build_retriever
from app.retrieval.types import RetrievalError

SESSIONS = "/api/v1/chat/sessions"


@pytest.fixture(scope="module")
def memory_dense() -> DenseRetriever:
    dense = DenseRetriever(QdrantClient(":memory:"), HashingEmbedder(dim=128))
    dense.index(corpus_chunks("en", include_keywords=False), "en")
    return dense


@pytest.fixture
def fake_llm(client) -> FakeLLM:
    provider = FakeLLM()
    client.app.dependency_overrides[get_llm] = lambda: LLMService(provider, model="fake-model", max_retries=0, sleep=lambda _: None)
    return provider


@pytest.fixture
def rag(client, memory_dense):
    """Retriever thật (BM25 + RRF) với nhánh dense dùng Qdrant :memory:. Trả về dict để test thay hành vi."""
    state = {"broken": False}

    def retriever_for(mode):
        if state["broken"]:
            raise RetrievalError("Qdrant không kết nối (giả lập)")
        return build_retriever(mode, get_settings(), dense=memory_dense)

    client.app.dependency_overrides[get_retriever_for] = lambda: retriever_for
    return state


def session(client, headers):
    return client.post(SESSIONS, headers=headers).json()["session_id"]


def send(client, headers, sid, content, mode=None):
    body = {"content": content} | ({"rag_mode": mode} if mode else {})
    return client.post(f"{SESSIONS}/{sid}/messages", headers=headers, json=body)


@pytest.mark.parametrize("mode", ["dense", "hybrid"])
def test_rag_answer_returns_sources_and_only_valid_citations(client, register_and_login, fake_llm, rag, mode, db_session):
    headers = register_and_login()
    sid = session(client, headers)
    fake_llm.queue(Reply("Dùng **an** trước nguyên âm [1]. Theo sách ngoài [9]. Xem thêm [2, 7]."))

    response = send(client, headers, sid, "When do I use an before a vowel sound?", mode)

    assert response.status_code == 200, response.text
    body = response.json()
    assistant = body["assistant_message"]
    assert assistant["rag_mode"] == mode and assistant["rag_fallback"] is False
    assert len(assistant["sources"]) == 3  # RAG_TOP_K mặc định
    assert [s["n"] for s in assistant["sources"]] == [1, 2, 3]
    assert {s["n"] for s in assistant["sources"] if s["cited"]} == {1, 2}
    assert "[9]" not in assistant["content"] and "[2, 7]" not in assistant["content"] and "[2]" in assistant["content"]
    assert body["has_citations"] is True
    assert all(s["document_id"].startswith("gram-en-") for s in assistant["sources"])
    # Ngữ cảnh nằm trong system prompt (khối phân cách); câu hỏi người dùng thì KHÔNG.
    request = fake_llm.calls[-1].request
    assert CONTEXT_OPEN in request.system_prompt and "[1] " in request.system_prompt
    assert "vowel sound?" not in request.system_prompt
    row = db_session.scalars(select(ChatMessageRow).where(ChatMessageRow.role == "assistant")).one()
    assert row.citations == {"valid": [1, 2], "invalid": [7, 9]} and row.rag_mode == mode
    assert assistant["invalid_citations"] == [7, 9]
    # Lịch sử trả nguồn y như lúc gửi.
    history = client.get(f"{SESSIONS}/{sid}/messages", headers=headers).json()
    assert history[1]["sources"] == assistant["sources"]


def test_llm_only_mode_has_no_sources_and_uses_plain_prompt(client, register_and_login, fake_llm, rag):
    headers = register_and_login()
    sid = session(client, headers)
    body = send(client, headers, sid, "Hi [1]", "llm_only").json()
    assistant = body["assistant_message"]
    assert assistant["rag_mode"] == "llm_only" and assistant["sources"] is None and body["has_citations"] is False
    assert CONTEXT_OPEN not in fake_llm.calls[-1].request.system_prompt


def test_server_default_mode_is_used_when_request_has_none(client, register_and_login, fake_llm, rag):
    headers = register_and_login()
    sid = session(client, headers)
    assert send(client, headers, sid, "hello").json()["assistant_message"]["rag_mode"] == get_settings().rag_mode == "llm_only"
    assert client.get("/api/v1/chat/rag-config", headers=headers).json() == {
        "default_mode": "llm_only", "modes": ["llm_only", "dense", "hybrid"], "top_k": 3}


def test_retrieval_failure_falls_back_to_llm_only_and_is_flagged(client, register_and_login, fake_llm, rag, caplog):
    rag["broken"] = True
    headers = register_and_login()
    sid = session(client, headers)
    with caplog.at_level(logging.DEBUG):
        response = send(client, headers, sid, "Câu hỏi bí mật về mạo từ", "hybrid")
    assert response.status_code == 200
    assistant = response.json()["assistant_message"]
    assert (assistant["rag_mode"], assistant["rag_fallback"], assistant["sources"]) == ("llm_only", True, None)
    assert CONTEXT_OPEN not in fake_llm.calls[-1].request.system_prompt
    assert "rag_fallback" in caplog.text and "bí mật" not in caplog.text


def test_invalid_rag_mode_is_rejected(client, register_and_login, fake_llm, rag):
    headers = register_and_login()
    sid = session(client, headers)
    response = send(client, headers, sid, "hello", "bm25_secret")
    assert response.status_code == 422
    assert fake_llm.calls == []


def test_owner_check_and_sources_do_not_leak_across_users(client, register_and_login, fake_llm, rag):
    alice = register_and_login("alice@example.com")
    bob = register_and_login("bob@example.com")
    sid = session(client, alice)
    fake_llm.queue(Reply("Theo bài [1]."))
    assert send(client, alice, sid, "plural nouns", "hybrid").status_code == 200

    read = client.get(f"{SESSIONS}/{sid}/messages", headers=bob)
    write = send(client, bob, sid, "plural nouns", "hybrid")
    assert read.status_code == write.status_code == 404
    assert "sources" not in read.text and "gram-en-" not in read.text
    assert len(fake_llm.calls) == 1  # Bob không kích hoạt truy xuất hay gọi LLM


def test_rag_logs_have_metadata_but_no_question_answer_or_context(client, register_and_login, fake_llm, rag, caplog):
    headers = register_and_login()
    sid = session(client, headers)
    fake_llm.queue(Reply("Câu trả lời riêng tư [1]."))
    with caplog.at_level(logging.DEBUG):
        send(client, headers, sid, "Câu hỏi riêng tư về plural nouns", "hybrid")
    assert "rag_mode=hybrid" in caplog.text and "sources=3" in caplog.text
    for secret in ("riêng tư", "plural nouns", "Most nouns", CONTEXT_OPEN):
        assert secret not in caplog.text


def test_history_sent_to_llm_drops_old_citation_numbers(client, register_and_login, fake_llm, rag):
    headers = register_and_login()
    sid = session(client, headers)
    fake_llm.queue(Reply("Dùng an [1]."), Reply("Tiếp."))
    send(client, headers, sid, "an or a?", "hybrid")
    send(client, headers, sid, "and plurals?", "hybrid")
    previous = [m.content for m in fake_llm.calls[-1].request.messages if m.role == "assistant"]
    assert previous == ["Dùng an."]
