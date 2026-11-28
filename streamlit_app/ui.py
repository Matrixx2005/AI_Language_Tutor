"""Thành phần giao diện dùng chung (có import streamlit). Token chỉ nằm trong st.session_state, không ghi ra đĩa."""
from __future__ import annotations

import time

import streamlit as st

from api import ApiClient, ApiError
from logic import LIMIT_CODES, format_wait, plain_markdown, public_mode, seconds_left


def client() -> ApiClient:
    return ApiClient(token=st.session_state.get("token"))


def logged_in() -> bool:
    return bool(st.session_state.get("token"))


def require_login() -> None:
    if not logged_in():
        st.info("Hãy đăng nhập ở trang **Tài khoản** trước.")
        st.stop()


def show_error(error: ApiError, key: str) -> None:
    """Lỗi tiếng Việt; lỗi giới hạn có Retry-After → nhớ mốc hết hạn để đếm ngược."""
    if error.code in {"invalid_token", "token_expired"}:
        st.session_state.pop("token", None)
    if error.code in LIMIT_CODES and error.retry_after:
        st.session_state[f"wait_until_{key}"] = time.time() + error.retry_after
    st.error(f"{error.message} (mã: {error.code})")


def wait_remaining(key: str) -> int:
    return seconds_left(st.session_state.get(f"wait_until_{key}"), time.time())


@st.fragment(run_every=1)
def countdown(key: str) -> None:
    left = wait_remaining(key)
    if left > 0:
        st.warning(f"Vui lòng thử lại sau {format_wait(left)}.")


def plain(text: str) -> None:
    """Hiển thị văn bản NGUYÊN VĂN (escape markdown/HTML). Không bao giờ dùng unsafe_allow_html."""
    st.markdown(plain_markdown(text))


def is_public() -> bool:
    return public_mode()
