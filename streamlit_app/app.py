"""AI Language Tutor — Streamlit test console (Tuần 5A).

Chạy: streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8501
Lớp mỏng: mọi nghiệp vụ qua REST API (streamlit_app/api.py); riêng Retrieval Lab import backend/app/retrieval.
Cổng mã truy cập (STREAMLIT_ACCESS_CODE) chặn MỌI trang; STREAMLIT_PUBLIC_MODE=true ẩn cấu hình và chặn Gemini.
"""
import streamlit as st

from logic import access_code_required, check_access_code, public_mode

st.set_page_config(page_title="AI Language Tutor — Console", page_icon="📘", layout="wide")


def access_gate() -> None:
    """Chặn toàn app cho đến khi nhập đúng mã (so sánh hằng thời gian). Mã không bao giờ nằm trong mã nguồn."""
    if not access_code_required() or st.session_state.get("access_ok"):
        return
    st.title("AI Language Tutor — Console")
    st.write("Ứng dụng đang ở chế độ chia sẻ. Nhập mã truy cập để tiếp tục.")
    with st.form("access"):
        code = st.text_input("Mã truy cập", type="password")
        if st.form_submit_button("Vào"):
            if check_access_code(code):
                st.session_state["access_ok"] = True
                st.rerun()
            st.error("Mã truy cập không đúng.")
    st.stop()


access_gate()

pages = [
    st.Page("pages/1_tai_khoan.py", title="Tài khoản", icon="👤", default=True),
    st.Page("pages/2_chat.py", title="Chat", icon="💬"),
    st.Page("pages/3_placement.py", title="Kiểm tra đầu vào", icon="📝"),
    st.Page("pages/4_retrieval_lab.py", title="Retrieval Lab", icon="🔎"),
    st.Page("pages/5_thi_nghiem.py", title="Thí nghiệm", icon="📊"),
    st.Page("pages/6_corpus.py", title="Corpus", icon="📚"),
    st.Page("pages/7_he_thong.py", title="Hệ thống", icon="⚙️"),
]
with st.sidebar:
    if public_mode():
        st.caption("Chế độ công khai: chỉ cho phép LLM giả lập (fake); cấu hình bị ẩn.")
    st.caption("Đã đăng nhập" if st.session_state.get("token") else "Chưa đăng nhập")
st.navigation(pages).run()
