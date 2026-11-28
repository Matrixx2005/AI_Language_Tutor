"""Duyệt bài tập: chỉ khi backend bật EXERCISE_ADMIN_ENABLED và console đặt STREAMLIT_ACCESS_CODE.
Ghi người duyệt + thời gian qua API; không tự duyệt."""
import json

import streamlit as st

from api import ApiError
from logic import admin_page_enabled
from ui import client, is_public, plain, require_login, show_error

st.title("Duyệt bài tập")
if is_public() or not admin_page_enabled():
    st.info("Trang này chỉ dùng khi đặt STREAMLIT_ACCESS_CODE, không ở chế độ công khai, và backend bật EXERCISE_ADMIN_ENABLED=true.")
    st.stop()
require_login()
api = client()
status = st.selectbox("Trạng thái duyệt", ["unreviewed", "approved", "rejected_by_human"])
try:
    queue = api.admin_queue(status)
except ApiError as error:
    if error.status == 404:
        st.info("Backend chưa bật EXERCISE_ADMIN_ENABLED=true.")
    else:
        show_error(error, "admin")
    st.stop()
reviewer = st.text_input("Người duyệt (tên/ký hiệu)")
st.caption(f"{len(queue)} bài")
for ex in queue:
    with st.expander(f"{ex['exercise_type']} · {ex['level_code']} · {ex['document_id']} · {ex['validation_status']}"):
        st.markdown("**Đề**")
        plain(json.dumps(ex["prompt_payload"], ensure_ascii=False))
        st.markdown("**Đáp án**")
        plain(json.dumps(ex["answer_key"], ensure_ascii=False))
        st.markdown("**Giải thích**")
        plain(ex["explanation"])
        st.caption(f"Lý do loại: {ex['reject_reasons'] or '—'} · kiểm tra độc lập: {ex['generation_meta'].get('independent_check')} "
                   f"· duyệt: {ex['review_status']} {ex['reviewer'] or ''} {ex['reviewed_at'] or ''}")
        edited = st.text_area("Sửa đáp án (JSON, tùy chọn)", value="", key=f"edit_{ex['exercise_id']}")
        c1, c2, c3 = st.columns(3)
        for col, decision, label in ((c1, "approve", "Duyệt"), (c2, "reject", "Từ chối"), (c3, "edit", "Sửa và duyệt")):
            if col.button(label, key=f"{decision}_{ex['exercise_id']}", disabled=not reviewer.strip()):
                try:
                    edits = {"answer_key": json.loads(edited)} if decision == "edit" and edited.strip() else None
                    api.admin_review(ex["exercise_id"], decision, reviewer.strip(), edits)
                    st.rerun()
                except (ApiError, ValueError) as error:
                    st.error(str(error))
