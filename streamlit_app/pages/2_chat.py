"""Chat: chọn chế độ, nguồn, trích dẫn hợp lệ/không hợp lệ, rag_fallback, độ trễ phía client. Văn bản thuần."""
import time

import streamlit as st

from api import ApiError
from logic import chat_allowed
from ui import client, countdown, is_public, plain, require_login, show_error, wait_remaining

st.title("Chat với gia sư AI")
st.warning("Quyền riêng tư: khi backend dùng Gemini (gói miễn phí), Google có thể xử lý và lưu nội dung để cải thiện "
           "sản phẩm. Không nhập thông tin cá nhân thật.")
require_login()

api = client()
try:
    status = api.system_status()
    config = api.rag_config()
except ApiError as error:
    show_error(error, "chat")
    st.stop()

allowed, reason = chat_allowed(is_public(), status.get("llm_provider"))
if not allowed:
    st.error(reason)
if not is_public():
    st.caption(f"LLM: {status['llm_provider']} · RAG mặc định: {config['default_mode']} · top-k: {config['top_k']}")

try:
    sessions = api.sessions()
except ApiError as error:
    show_error(error, "chat")
    st.stop()

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("Cuộc trò chuyện mới"):
        try:
            st.session_state["chat_session"] = api.create_session()["session_id"]
            st.rerun()
        except ApiError as error:
            show_error(error, "chat")
ids = [s["session_id"] for s in sessions]
current = st.session_state.get("chat_session") or (ids[0] if ids else None)
with col1:
    if ids:
        current = st.selectbox("Cuộc trò chuyện", ids, index=ids.index(current) if current in ids else 0,
                               format_func=lambda sid: next((s["title"] or "Cuộc trò chuyện mới") for s in sessions if s["session_id"] == sid))
        st.session_state["chat_session"] = current

modes = ["", *config["modes"]]
mode = st.radio("Chế độ trả lời", modes, horizontal=True,
                format_func=lambda m: f"Mặc định ({config['default_mode']})" if m == "" else m)


def show_message(m: dict) -> None:
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        if m["status"] == "error":
            st.error(f"Lỗi: {m['error_code']}")
            return
        plain(m["content"])
        if m["role"] != "assistant":
            return
        meta = [f"chế độ: {m.get('rag_mode')}"]
        if m.get("rag_fallback"):
            meta.append("HẠ CẤP về llm_only (không truy xuất được tài liệu)")
        if m.get("truncated"):
            meta.append("có thể bị cắt")
        valid = [s["n"] for s in m.get("sources") or [] if s["cited"]]
        meta.append(f"trích dẫn hợp lệ: {valid or 'không có'}")
        if m.get("invalid_citations"):
            meta.append(f"trích dẫn KHÔNG hợp lệ đã bị loại: {m['invalid_citations']}")
        st.caption(" · ".join(meta))
        for s in m.get("sources") or []:
            with st.expander(f"[{s['n']}] {s['title']} · {s['level']} · rank {s['rank']} · score {s['score']:.4f}"
                             + ("" if s["cited"] else " · không được trích dẫn")):
                plain(s["text"])


if current:
    try:
        for message in api.messages(current):
            show_message(message)
    except ApiError as error:
        show_error(error, "chat")

countdown("chat")
prompt = st.chat_input("Hỏi về ngữ pháp, từ vựng…", disabled=not allowed or wait_remaining("chat") > 0)
if prompt:
    try:
        if not current:
            current = api.create_session()["session_id"]
            st.session_state["chat_session"] = current
        started = time.perf_counter()
        turn = api.send(current, prompt, mode or None)
        st.session_state["last_latency"] = (time.perf_counter() - started) * 1000
        st.rerun()
    except ApiError as error:
        show_error(error, "chat")
if "last_latency" in st.session_state:
    st.caption(f"Độ trễ tin gần nhất (phía client): {st.session_state['last_latency']:.0f} ms")
