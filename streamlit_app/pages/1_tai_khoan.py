"""Đăng nhập / Đăng ký / Hồ sơ (đổi trình độ) — qua REST API."""
import streamlit as st

from api import ApiError
from ui import client, countdown, logged_in, show_error, wait_remaining

st.title("Tài khoản")

if not logged_in():
    login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])
    with login_tab:
        countdown("login")
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Đăng nhập", disabled=wait_remaining("login") > 0):
                try:
                    st.session_state["token"] = client().login(email, password)
                    st.rerun()
                except ApiError as error:
                    show_error(error, "login")
    with register_tab:
        countdown("register")
        with st.form("register"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Mật khẩu (8–128 ký tự)", type="password", key="reg_password")
            if st.form_submit_button("Tạo tài khoản", disabled=wait_remaining("register") > 0):
                try:
                    client().register(email, password)
                    st.session_state["token"] = client().login(email, password)
                    st.success("Đã tạo tài khoản và đăng nhập.")
                    st.rerun()
                except ApiError as error:
                    show_error(error, "register")
    st.stop()

try:
    profile = client().profile()
    levels = client().language(profile["language_code"])["levels"]
except ApiError as error:
    show_error(error, "profile")
    st.stop()

st.write(f"Email: {profile['email']}")
st.write(f"Ngôn ngữ học: {profile['language_code']} · Trình độ hiện tại: **{profile['current_level_code']}**")
codes = [lv["code"] for lv in levels]
with st.form("profile"):
    level = st.selectbox("Trình độ", codes, index=codes.index(profile["current_level_code"]),
                         format_func=lambda c: next(f"{lv['code']} — {lv['display_name_vi']}" for lv in levels if lv["code"] == c))
    if st.form_submit_button("Lưu trình độ"):
        try:
            client().update_profile(current_level_code=level)
            st.success("Đã cập nhật trình độ.")
        except ApiError as error:
            show_error(error, "profile")
if st.button("Đăng xuất"):
    st.session_state.pop("token", None)
    st.rerun()
