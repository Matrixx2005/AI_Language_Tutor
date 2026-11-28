"""Các bộ giới hạn của ứng dụng, tạo một lần mỗi app (app.state.limits) từ Settings.

Tách khỏi biến toàn cục để mỗi app (và mỗi test) có trạng thái riêng, và để test thay đồng hồ.
"""
from __future__ import annotations

import ipaddress
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Request

from app.core.config import Settings
from app.core.errors import AppError
from app.core.rate_limit import Clock, ConcurrencyGuard, Cooldown, SlidingWindowLimiter

security_logger = logging.getLogger("app.security")

LLM_COOLDOWN_MAX_SECONDS = 60.0  # trần cho llm_rate_limited (giới hạn theo phút)
LLM_COOLDOWN_DEFAULT_SECONDS = 30.0  # khi nhà cung cấp không báo retry_after
LLM_QUOTA_COOLDOWN_HARD_MAX_SECONDS = 3600.0  # trần cứng của bộ tạm khóa (khớp giới hạn cấu hình)


def llm_cooldown_seconds(error_code: str, retry_after: float | None, quota_cooldown_seconds: int) -> float | None:
    """Thời gian tạm khóa toàn hệ thống sau lỗi giới hạn thật từ nhà cung cấp (None = không khóa).

    - `llm_rate_limited` (theo phút): theo retry_after, mặc định 30s, tối đa 60s.
    - `llm_quota_exhausted` (hết hạn mức NGÀY, đã thử cả model dự phòng): khóa
      `LLM_QUOTA_COOLDOWN_SECONDS` để không tiếp tục gọi API vô ích; 0 = dùng cách tính như rate_limited.
    """
    short = min(retry_after or LLM_COOLDOWN_DEFAULT_SECONDS, LLM_COOLDOWN_MAX_SECONDS)
    if error_code == "llm_rate_limited":
        return short
    if error_code == "llm_quota_exhausted":
        return float(quota_cooldown_seconds) if quota_cooldown_seconds > 0 else short
    return None


def utcnow() -> datetime:
    """Đồng hồ thật (giờ tường, có múi giờ). Test thay bằng monkeypatch."""
    return datetime.now(UTC)


@dataclass
class AppLimits:
    settings: Settings
    clock: Clock = time.monotonic
    chat_user_minute: SlidingWindowLimiter = field(init=False)
    exercise_submit_minute: SlidingWindowLimiter = field(init=False)
    llm_global_minute: SlidingWindowLimiter = field(init=False)
    login_email: SlidingWindowLimiter = field(init=False)
    login_ip: SlidingWindowLimiter = field(init=False)
    register_ip: SlidingWindowLimiter = field(init=False)
    chat_in_flight: ConcurrencyGuard = field(init=False)
    llm_cooldown: Cooldown = field(init=False)

    def __post_init__(self) -> None:
        s, c = self.settings, self.clock
        self.chat_user_minute = SlidingWindowLimiter(s.chat_user_per_minute, 60, clock=c)
        self.exercise_submit_minute = SlidingWindowLimiter(s.exercise_submit_per_minute, 60, clock=c)
        self.llm_global_minute = SlidingWindowLimiter(s.llm_global_per_minute, 60, clock=c)
        self.login_email = SlidingWindowLimiter(s.auth_login_fails_per_email, s.auth_login_window_seconds, clock=c)
        self.login_ip = SlidingWindowLimiter(s.auth_login_fails_per_ip, s.auth_login_window_seconds, clock=c)
        self.register_ip = SlidingWindowLimiter(s.auth_register_per_ip_per_hour, 3600, clock=c)
        self.chat_in_flight = ConcurrencyGuard()
        self.llm_cooldown = Cooldown(clock=c, max_seconds=LLM_QUOTA_COOLDOWN_HARD_MAX_SECONDS)


def get_limits(request: Request) -> AppLimits:
    return request.app.state.limits


def rate_limit_error(status: int, code: str, message: str, retry_after: float | None) -> AppError:
    headers = None
    if retry_after is not None:
        headers = {"Retry-After": str(max(1, math.ceil(retry_after)))}
    return AppError(status, code, message, headers=headers)


def log_rejection(kind: str, *, user_id: object | None = None, ip: str | None = None, retry_after: float | None = None) -> None:
    """Log metadata khi từ chối: loại giới hạn, user_id rút gọn hoặc IP rút gọn, thời gian chờ.
    KHÔNG ghi email, mật khẩu, nội dung tin nhắn."""
    who = f"user={str(user_id)[:8]}" if user_id is not None else f"ip={mask_ip(ip or '')}"
    wait = f"{retry_after:.0f}" if retry_after is not None else "-"
    security_logger.warning("rate_limited kind=%s %s retry_after=%s", kind, who, wait)


# ------------------------------------------------------------------ IP client


def client_ip(request: Request, trusted_proxy_count: int) -> str:
    """IP của client. Mặc định (0) KHÔNG đọc X-Forwarded-For vì ai cũng giả được header này.

    Khi đứng sau `n` proxy tin cậy, mỗi proxy nối IP nó nhận được vào cuối X-Forwarded-For → IP
    client là phần tử thứ n tính từ cuối. Thiếu phần tử thì dùng IP kết nối.
    """
    peer = request.client.host if request.client else "unknown"
    if trusted_proxy_count <= 0:
        return peer
    chain = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if len(chain) < trusted_proxy_count:
        return peer
    candidate = chain[-trusted_proxy_count]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return peer


def mask_ip(ip: str) -> str:
    """Rút gọn IP để log (không ghi đủ địa chỉ): IPv4 a.b.c.x, IPv6 4 nhóm đầu."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return "unknown"
    if address.version == 4:
        return ".".join(ip.split(".")[:3]) + ".x"
    return ":".join(address.exploded.split(":")[:4]) + ":x"


# ------------------------------------------------------------------ ngày địa phương


def local_day_bounds(now_utc: datetime, timezone: str) -> tuple[datetime, datetime]:
    """[đầu ngày, đầu ngày kế tiếp) theo múi giờ cấu hình, trả về dạng UTC để so với DB."""
    zone = ZoneInfo(timezone)
    local = now_utc.astimezone(zone)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = (start_local + timedelta(days=1)).replace(tzinfo=zone)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def seconds_until_local_midnight(now_utc: datetime, timezone: str) -> int:
    _, end = local_day_bounds(now_utc, timezone)
    return max(1, int((end - now_utc).total_seconds() + 0.999))
