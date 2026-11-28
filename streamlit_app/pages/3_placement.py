"""Placement qua API: làm bài, nộp, xem kết quả, áp dụng trình độ. Đáp án chỉ ở session_state của phiên này."""
import streamlit as st

from api import ApiError
from ui import client, plain, require_login, show_error

st.title("Kiểm tra đầu vào")
require_login()
api = client()


def show_result(attempt: dict) -> None:
    r = attempt["result"]
    st.subheader(f"Trình độ đề xuất: {r['suggested_level_code']} — {r['suggested_level_name_vi']}")
    st.write(f"Điểm: {r['score']}/{r['max_score']} ({r['percent']:.1f}%)")
    st.info(r["disclaimer"])
    if r["weak_groups"]:
        st.write("Nhóm cần ôn: " + ", ".join(f"{g['level_code']} {g['category']} ({g['correct']}/{g['total']})" for g in r["weak_groups"]))
    if r["applied_at"]:
        st.success("Đã áp dụng trình độ này vào hồ sơ.")
    elif st.button("Dùng trình độ này"):
        try:
            api.apply(attempt["attempt_id"])
            st.rerun()
        except ApiError as error:
            show_error(error, "placement")
    with st.expander("Xem lại từng câu"):
        for i, item in enumerate(r["review"], 1):
            mark = "✅" if item["is_correct"] else "❌"
            plain(f"{i}. {item['prompt']}")
            st.caption(f"{mark} Bạn chọn: {item['selected'] or '(bỏ trống)'} · Đáp án: {item['correct_answer']}")


try:
    attempts = api.attempts()
except ApiError as error:
    show_error(error, "placement")
    st.stop()

doing = next((a for a in attempts if a["status"] == "in_progress"), None)
if st.button("Bắt đầu / tiếp tục bài kiểm tra" if doing else "Làm bài kiểm tra mới"):
    try:
        st.session_state["placement"] = api.start_placement()
        st.session_state["answers"] = {}
    except ApiError as error:
        show_error(error, "placement")

attempt = st.session_state.get("placement")
if attempt and attempt["status"] == "in_progress":
    answers = st.session_state.setdefault("answers", {})
    with st.form("placement"):
        for q in attempt["questions"]:
            choice = st.radio(f"{q['position']}. {q['prompt']}", q["options"], index=None, key=f"q_{q['question_id']}")
            if choice:
                answers[q["question_id"]] = choice
        st.caption(f"Đã trả lời {len(answers)}/{len(attempt['questions'])} (câu bỏ trống tính sai)")
        if st.form_submit_button("Nộp bài"):
            try:
                st.session_state["placement"] = api.submit(attempt["attempt_id"], answers)
                st.session_state["answers"] = {}
                st.rerun()
            except ApiError as error:
                show_error(error, "placement")
elif attempt and attempt["status"] == "completed":
    show_result(attempt)
elif attempts:
    latest = next((a for a in attempts if a["status"] == "completed"), None)
    if latest:
        try:
            show_result(api.attempt(latest["attempt_id"]))
        except ApiError as error:
            show_error(error, "placement")
