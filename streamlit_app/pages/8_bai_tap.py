"""Bài tập: chọn chủ đề/dạng → làm → nộp → xem chấm, giải thích, nguồn. Lớp mỏng qua REST API."""
import streamlit as st

from api import ApiError
from logic import EXERCISE_TYPE_LABELS, exercise_types_allowed
from ui import client, is_public, plain, require_login, show_error

st.title("Bài tập")
require_login()
api = client()
try:
    provider = api.system_status().get("llm_provider")
except ApiError:
    provider = None
types = exercise_types_allowed(is_public(), provider)
if len(types) < 5:
    st.info("Chế độ công khai: chỉ hiện dạng bài chấm tự động (không dùng AI).")

c1, c2 = st.columns(2)
kind = c1.selectbox("Dạng bài", ["", *types], format_func=lambda t: "Bất kỳ" if not t else EXERCISE_TYPE_LABELS[t])
topic = c2.text_input("Chủ đề (document_id, để trống = gợi ý tự động)")
if st.button("Lấy bài tiếp theo"):
    try:
        ex = api.next_exercise(topic.strip() or None, kind or (types[0] if len(types) < 5 else None))
        if ex["exercise_type"] not in types:
            st.warning("Bài gợi ý cần AI chấm, không khả dụng ở chế độ công khai. Hãy chọn dạng bài khác.")
        else:
            st.session_state["exercise"], st.session_state["result"] = ex, None
    except ApiError as error:
        show_error(error, "exercise")

ex = st.session_state.get("exercise")
if ex:
    p = ex["prompt"]
    st.subheader(f"{EXERCISE_TYPE_LABELS.get(ex['exercise_type'], ex['exercise_type'])} · {ex['level_code']} · {ex['topic']}")
    if ex["review_status"] != "approved":
        st.caption("Bài do AI soạn, CHƯA được giáo viên duyệt.")
    answer = ""
    if ex["exercise_type"] == "mcq":
        plain(p["question"])
        answer = st.radio("Chọn đáp án", p["options"], index=None, key=f"mcq_{ex['exercise_id']}") or ""
    elif ex["exercise_type"] == "cloze":
        plain(p["sentence"])
        answer = st.text_input("Từ điền vào chỗ trống", key=f"cloze_{ex['exercise_id']}")
    elif ex["exercise_type"] == "error_correction":
        plain(p["sentence"])
        answer = st.text_input("Viết lại câu đúng", key=f"ec_{ex['exercise_id']}")
    elif ex["exercise_type"] == "reorder":
        plain(" / ".join(p["tokens"]))
        answer = st.text_input("Sắp xếp thành câu hoàn chỉnh", key=f"ro_{ex['exercise_id']}")
    else:
        plain(p["source_vi"])
        answer = st.text_area("Dịch sang tiếng Anh", key=f"tr_{ex['exercise_id']}")
    if st.button("Nộp bài", disabled=not answer.strip()):
        try:
            st.session_state["result"] = api.submit_exercise(ex["exercise_id"], answer)
        except ApiError as error:
            show_error(error, "exercise")
            st.caption("Bài làm đã được lưu; có thể bấm chấm lại ở trang Lỗi của tôi → Lịch sử khi AI sẵn sàng.")

result = st.session_state.get("result")
if result:
    if result["grading_status"] == "pending":
        st.warning("Bài làm đang chờ chấm.")
        if st.button("Chấm lại"):
            try:
                st.session_state["result"] = api.regrade(result["attempt_id"])
                st.rerun()
            except ApiError as error:
                show_error(error, "exercise")
    else:
        (st.success if result["is_correct"] else st.error)(
            f"{'Đúng' if result['is_correct'] else 'Chưa đúng'} · điểm {result['score']} · chấm bằng {'AI' if result['graded_by'] == 'llm' else 'quy tắc'}")
        fb = result.get("feedback") or {}
        if fb.get("feedback_vi"):
            plain(fb["feedback_vi"])
        for e in fb.get("errors", []):
            plain(f"- {e['error_type']}: {e.get('span', '')} → {e.get('correction', '')}. {e.get('explanation_vi', '')}")
    sol = result["solution"]
    st.markdown("**Đáp án**")
    for a in sol["correct_answers"]:
        plain(a)
    st.markdown("**Giải thích**")
    plain(sol["explanation"])
    st.caption(f"Bài học nguồn: {sol['source']['title']} ({sol['source']['document_id']})")
