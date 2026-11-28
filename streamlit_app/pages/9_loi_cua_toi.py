"""Lỗi của tôi: loại lỗi, độ chính xác theo chủ đề/dạng, xu hướng, chủ đề nên luyện, lịch sử (chấm lại bài pending)."""
import pandas as pd
import streamlit as st

from api import ApiError
from ui import client, require_login, show_error

st.title("Lỗi của tôi")
require_login()
api = client()
try:
    s = api.error_summary()
    history = api.exercise_history()
except ApiError as error:
    show_error(error, "errors")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Bài đã làm (30 ngày)", s["attempts"])
c2.metric("Đã chấm", s["graded"])
c3.metric("Đúng", s["correct"])
if s["top_error_types"]:
    st.subheader("Loại lỗi hay gặp")
    st.bar_chart(pd.DataFrame(s["top_error_types"]).set_index("error_type")["count"])
if s["accuracy_by_topic"]:
    st.subheader("Độ chính xác theo chủ đề")
    st.dataframe(pd.DataFrame([{"chủ đề": k, "tỷ lệ đúng": v} for k, v in s["accuracy_by_topic"].items()]), hide_index=True, width="stretch")
st.subheader("Xu hướng 30 ngày")
st.line_chart(pd.DataFrame(s["trend_30d"]).set_index("date")[["attempts", "correct", "errors"]])
st.subheader("Nên luyện")
if s["needs_practice"]:
    st.dataframe(pd.DataFrame(s["needs_practice"]), hide_index=True, width="stretch")
else:
    st.caption("Chưa có dữ liệu lỗi.")

st.subheader("Lịch sử")
for a in history[:20]:
    label = "chờ chấm" if a["grading_status"] == "pending" else ("đúng" if a["is_correct"] else "sai")
    cols = st.columns([4, 1])
    cols[0].caption(f"{a['created_at'][:16]} · {a['solution']['source']['title']} · {label}")
    if a["grading_status"] == "pending" and cols[1].button("Chấm lại", key=a["attempt_id"]):
        try:
            api.regrade(a["attempt_id"])
            st.rerun()
        except ApiError as error:
            show_error(error, "errors")
