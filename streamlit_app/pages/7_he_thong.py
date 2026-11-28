"""Hệ thống: /health, nhà cung cấp LLM, RAG_MODE, giới hạn, Postgres/Qdrant. KHÔNG bao giờ hiển thị .env, key, token.
Chế độ công khai: chỉ hiển thị API có hoạt động hay không."""
import streamlit as st

from api import ApiError
from logic import api_base_url
from ui import client, is_public

st.title("Hệ thống")
api = client()
try:
    health = api.health()
    st.success(f"API hoạt động: {health.get('status')}")
except ApiError as error:
    st.error(error.message)
    st.stop()

if is_public():
    st.info("Chế độ công khai: thông tin cấu hình được ẩn.")
    st.stop()

try:
    status = api.system_status()
except ApiError as error:
    st.error(f"{error.message} (mã: {error.code})")
    st.stop()
c1, c2, c3, c4 = st.columns(4)
c1.metric("LLM", status["llm_provider"])
c2.metric("RAG_MODE", status["rag_mode"])
c3.metric("PostgreSQL", status["database"])
c4.metric("Qdrant", status["qdrant"])
st.subheader("Giới hạn đang áp dụng")
st.table({"giới hạn": list(status["limits"]), "giá trị": [str(v) for v in status["limits"].values()]})
st.caption(f"Console gọi API tại: {api_base_url()}")
