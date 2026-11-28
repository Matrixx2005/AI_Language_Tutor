"""Client REST DUY NHẤT của Streamlit console (httpx, timeout rõ ràng). Lỗi → ApiError(code, message, status, retry_after)
theo định dạng chung của backend {"error": {"code", "message"}}; không kết nối được → code "network_error"."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from logic import api_base_url, message_for_code, parse_retry_after

TIMEOUT = httpx.Timeout(10.0, read=90.0)  # chat có thể chờ LLM + tải model nhúng lần đầu


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status: int = 0
    retry_after: int | None = None

    def __str__(self) -> str:
        return self.message


class ApiClient:
    def __init__(self, token: str | None = None, base_url: str | None = None):
        self.base_url = (base_url or api_base_url()).rstrip("/")
        self.token = token

    def _request(self, method: str, path: str, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = httpx.request(method, f"{self.base_url}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
        except httpx.HTTPError:
            raise ApiError("network_error", message_for_code("network_error")) from None
        if response.status_code >= 400:
            try:
                error = response.json().get("error", {})
            except ValueError:
                error = {}
            code = error.get("code") or f"http_{response.status_code}"
            raise ApiError(code, message_for_code(code, error.get("message")), response.status_code,
                           parse_retry_after(response.headers.get("Retry-After")))
        return response.json() if response.content else None

    # Hệ thống
    def health(self):
        root = self.base_url.rsplit("/api/", 1)[0]
        try:
            return httpx.get(f"{root}/health", timeout=5).json()
        except (httpx.HTTPError, ValueError):
            raise ApiError("network_error", message_for_code("network_error")) from None

    def system_status(self):
        return self._request("GET", "/system/status")

    # Tài khoản
    def register(self, email: str, password: str):
        return self._request("POST", "/auth/register", json={"email": email, "password": password})

    def login(self, email: str, password: str) -> str:
        return self._request("POST", "/auth/login", json={"email": email, "password": password})["access_token"]

    def profile(self):
        return self._request("GET", "/profile/me")

    def update_profile(self, **fields):
        return self._request("PATCH", "/profile/me", json=fields)

    def language(self, code: str):
        return self._request("GET", f"/languages/{code}")

    # Chat
    def rag_config(self):
        return self._request("GET", "/chat/rag-config")

    def sessions(self):
        return self._request("GET", "/chat/sessions")

    def create_session(self):
        return self._request("POST", "/chat/sessions")

    def messages(self, session_id: str):
        return self._request("GET", f"/chat/sessions/{session_id}/messages")

    def send(self, session_id: str, content: str, rag_mode: str | None):
        body = {"content": content} | ({"rag_mode": rag_mode} if rag_mode else {})
        return self._request("POST", f"/chat/sessions/{session_id}/messages", json=body)

    # Placement
    def start_placement(self):
        return self._request("POST", "/placement/attempts")

    def attempts(self):
        return self._request("GET", "/placement/attempts")

    def attempt(self, attempt_id: str):
        return self._request("GET", f"/placement/attempts/{attempt_id}")

    def submit(self, attempt_id: str, answers: dict[str, str]):
        return self._request("POST", f"/placement/attempts/{attempt_id}/submit", json={"answers": answers})

    def apply(self, attempt_id: str):
        return self._request("POST", f"/placement/attempts/{attempt_id}/apply")


def _exercise_methods():
    """Bài tập (Tuần 5B) — gắn vào ApiClient."""

    def next_exercise(self, topic: str | None = None, exercise_type: str | None = None):
        params = {k: v for k, v in {"topic": topic, "type": exercise_type}.items() if v}
        return self._request("GET", "/exercises/next", params=params)

    def exercise(self, exercise_id: str):
        return self._request("GET", f"/exercises/{exercise_id}")

    def submit_exercise(self, exercise_id: str, text: str):
        return self._request("POST", f"/exercises/{exercise_id}/attempts", json={"answer": {"text": text}})

    def regrade(self, attempt_id: str):
        return self._request("POST", f"/exercises/attempts/{attempt_id}/regrade")

    def exercise_history(self):
        return self._request("GET", "/exercises/history")

    def error_summary(self):
        return self._request("GET", "/errors/summary")

    def admin_queue(self, review_status: str | None = None):
        return self._request("GET", "/exercises/admin/queue", params={"review_status": review_status} if review_status else None)

    def admin_review(self, exercise_id: str, decision: str, reviewer: str, edits: dict | None = None):
        return self._request("POST", f"/exercises/admin/{exercise_id}/review",
                             json={"decision": decision, "reviewer": reviewer, "edits": edits})

    for fn in (next_exercise, exercise, submit_exercise, regrade, exercise_history, error_summary, admin_queue, admin_review):
        setattr(ApiClient, fn.__name__, fn)


_exercise_methods()
