"""Streamlit test console (Tuần 5A): hàm thuần + AppTest (không mạng, không backend, không key)."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "streamlit_app"
sys.path.insert(0, str(APP_DIR))

import lab  # noqa: E402
import logic  # noqa: E402


def test_error_messages_retry_after_and_wait_format():
    assert logic.message_for_code("chat_rate_limited", "x") == "Bạn đang gửi tin hơi nhanh."
    assert logic.message_for_code("la", "Thông điệp máy chủ") == "Thông điệp máy chủ"
    assert logic.message_for_code(None) == "Yêu cầu chưa thành công. Vui lòng thử lại."
    assert logic.parse_retry_after("60") == 60 and logic.parse_retry_after("-5") is None
    assert logic.parse_retry_after(None) is None and logic.parse_retry_after("1.5") is None
    assert [logic.format_wait(s) for s in (0, 12, 125, 900, 3780, 7199)] == [
        "0 giây", "12 giây", "2 phút 5 giây", "15 phút", "1 giờ 3 phút", "2 giờ"]
    assert logic.seconds_left(None, 100) == 0 and logic.seconds_left(105.2, 100) == 6


def test_access_code_gate_is_constant_time_and_off_when_unset():
    env = {"STREAMLIT_ACCESS_CODE": "ma-bi-mat-123"}
    assert logic.access_code_required(env) and not logic.access_code_required({})
    assert logic.check_access_code("ma-bi-mat-123", env) and logic.check_access_code(" ma-bi-mat-123 ", env)
    assert not logic.check_access_code("sai", env) and not logic.check_access_code("", env)
    assert logic.check_access_code("bat-ky", {})  # không đặt mã → không chặn
    assert "compare_digest" in (APP_DIR / "logic.py").read_text(encoding="utf-8")


def test_public_mode_blocks_chat_unless_backend_is_fake():
    assert logic.public_mode({"STREAMLIT_PUBLIC_MODE": "true"}) and not logic.public_mode({})
    assert logic.chat_allowed(True, "fake")[0] is True
    assert logic.chat_allowed(True, "gemini")[0] is False and "gemini" in logic.chat_allowed(True, "gemini")[1]
    assert logic.chat_allowed(True, None)[0] is False
    assert logic.chat_allowed(False, "gemini")[0] is True


def test_dev_only_never_returns_test_split():
    queries = [{"query_id": "a", "split": "dev"}, {"query_id": "b", "split": "test"}, {"query_id": "c"}, {"query_id": "d", "split": "DEV"}]
    assert [q["query_id"] for q in logic.dev_only(queries)] == ["a"]
    samples = lab.dev_queries()
    assert samples and all(q["split"] == "dev" for q in samples)
    for name in ("rag_queries_v1.json", "rag_queries_v2.json"):
        path = ROOT / "data" / "evaluation" / name
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            test_ids = {q["query_id"] for q in (data["queries"] if isinstance(data, dict) else data) if q["split"] == "test"}
            assert test_ids and not test_ids & {q["query_id"] for q in samples}


def test_plain_markdown_escapes_html_and_markdown():
    out = logic.plain_markdown("<script>alert(1)</script> **đậm** # tiêu đề [1](http://x)\ndòng 2")
    assert "<script>" not in out and "\\<script\\>" in out
    assert "\\*\\*đậm\\*\\*" in out and "\\# tiêu đề" in out and "\\[1\\]\\(http://x\\)" in out
    assert "  \ndòng 2" in out


def test_console_source_never_enables_html_or_contains_secrets():
    sources = {p: p.read_text(encoding="utf-8") for p in APP_DIR.rglob("*.py")}
    assert len(sources) >= 11
    for path, text in sources.items():
        assert not re.search(r"unsafe_allow_html\s*=", text), path
        assert not re.search(r"AIza[0-9A-Za-z_-]{20,}", text), path
        assert "STREAMLIT_ACCESS_CODE\"," not in text.replace(" ", "") or path.name == "logic.py"
    # Chat và nguồn hiển thị qua plain() (escape), không st.markdown trực tiếp nội dung LLM.
    chat = sources[APP_DIR / "pages" / "2_chat.py"]
    assert "plain(m[\"content\"])" in chat and "plain(s[\"text\"])" in chat


def test_parse_review_status_reads_corpus_table():
    status = logic.parse_review_status((ROOT / "docs" / "CORPUS_REVIEW.md").read_text(encoding="utf-8"))
    assert len(status) == 33 and status["gram-en-b1-zero-conditional-033"].startswith("Đã duyệt")


# ---------- AppTest (chạy app thật trong tiến trình, không trình duyệt) ----------

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_access_gate_blocks_every_page_until_correct_code(monkeypatch):
    monkeypatch.setenv("STREAMLIT_ACCESS_CODE", "mo-cua-42")
    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "AI Language Tutor — Console" and at.text_input[0].label == "Mã truy cập"
    assert not [t for t in at.title if t.value == "Tài khoản"]  # trang mặc định chưa chạy
    at.text_input[0].input("sai")
    at.button[0].click().run()
    assert any("không đúng" in e.value for e in at.error) and "access_ok" not in at.session_state
    at.text_input[0].input("mo-cua-42")
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["access_ok"] is True
    assert any(t.value == "Tài khoản" for t in at.title)  # đã vào trang mặc định


def test_app_does_not_crash_when_backend_is_down(monkeypatch):
    monkeypatch.delenv("STREAMLIT_ACCESS_CODE", raising=False)
    monkeypatch.setenv("STREAMLIT_API_BASE_URL", "http://127.0.0.1:9/api/v1")  # cổng chết
    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=30).run()
    assert not at.exception and at.title[0].value == "Tài khoản"
    at.switch_page("pages/7_he_thong.py").run()
    assert not at.exception
    assert any("Không kết nối được backend" in e.value for e in at.error)
