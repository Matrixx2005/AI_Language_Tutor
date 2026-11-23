"""Giới hạn tần suất trong bộ nhớ, an toàn đa luồng, không cần thư viện ngoài.

Thuật toán: CỬA SỔ TRƯỢT dạng nhật ký (sliding window log). Mỗi khóa giữ thời điểm của tối đa
`limit` lần đã ghi nhận trong `window_seconds` gần nhất. Lý do chọn (thay vì token bucket):
- đúng nghĩa "N lần trong X giây" như cấu hình (.env) và như thông báo cho người dùng;
- Retry-After chính xác = lần cũ nhất + cửa sổ − bây giờ;
- bộ nhớ mỗi khóa bị chặn bởi `limit`; số khóa bị chặn bởi `max_keys` (dọn khóa hết hạn, rồi LRU).

GIỚI HẠN: trạng thái nằm trong bộ nhớ của MỘT tiến trình. Chạy nhiều worker (uvicorn --workers,
gunicorn) hoặc nhiều máy thì mỗi tiến trình đếm riêng → cần Redis (việc Tuần 8 nếu triển khai).
Khởi động lại tiến trình thì bộ đếm phút/IP bị xóa (giới hạn NGÀY đếm từ DB nên không mất).
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass

Clock = Callable[[], float]


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: float = 0.0  # giây cần chờ (0 khi được phép)


ALLOW = Decision(True)


class SlidingWindowLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float,
        *,
        clock: Clock = time.monotonic,
        max_keys: int = 10_000,
        sweep_every: int = 1_000,
    ) -> None:
        self.limit = limit  # 0 = tắt
        self.window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._sweep_every = sweep_every
        self._ops = 0
        self._lock = threading.Lock()
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._hits)

    # ------------------------------------------------------------------ public

    def check(self, key: str) -> Decision:
        """Chỉ kiểm tra, không ghi nhận."""
        if self.limit <= 0:
            return ALLOW
        with self._lock:
            return self._decide(key, self._clock())

    def record(self, key: str) -> None:
        """Ghi nhận một lần (dù có vượt ngưỡng hay không) — dùng cho đếm đăng nhập sai."""
        if self.limit <= 0:
            return
        with self._lock:
            now = self._clock()
            self._append(key, now)
            self._housekeeping(now)

    def hit(self, key: str) -> Decision:
        """Kiểm tra và ghi nhận NGUYÊN TỬ: chỉ ghi khi được phép."""
        if self.limit <= 0:
            return ALLOW
        with self._lock:
            now = self._clock()
            decision = self._decide(key, now)
            if decision.allowed:
                self._append(key, now)
            self._housekeeping(now)
            return decision

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    # ----------------------------------------------------------------- private

    def _decide(self, key: str, now: float) -> Decision:
        hits = self._hits.get(key)
        if hits is None:
            return ALLOW
        self._prune(hits, now)
        if len(hits) < self.limit:
            return ALLOW
        return Decision(False, max(0.0, hits[0] + self.window - now))

    def _append(self, key: str, now: float) -> None:
        hits = self._hits.get(key)
        if hits is None:
            hits = deque(maxlen=self.limit)  # không bao giờ giữ quá `limit` mốc
            self._hits[key] = hits
        self._prune(hits, now)
        hits.append(now)
        self._hits.move_to_end(key)  # LRU: khóa vừa dùng nằm cuối

    def _prune(self, hits: deque[float], now: float) -> None:
        while hits and hits[0] <= now - self.window:
            hits.popleft()

    def _housekeeping(self, now: float) -> None:
        self._ops += 1
        if self._ops % self._sweep_every == 0 or len(self._hits) > self._max_keys:
            for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= now - self.window]:
                del self._hits[key]
        while len(self._hits) > self._max_keys:  # vẫn quá nhiều khóa còn hiệu lực: bỏ khóa cũ nhất
            self._hits.popitem(last=False)


class ConcurrencyGuard:
    """Đếm số yêu cầu đang xử lý theo khóa (ví dụ: tin chat chưa có trả lời của một người dùng)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._active)

    def acquire(self, key: str, limit: int) -> bool:
        with self._lock:
            current = self._active.get(key, 0)
            if current >= limit:
                return False
            self._active[key] = current + 1
            return True

    def release(self, key: str) -> None:
        with self._lock:
            current = self._active.get(key, 0)
            if current <= 1:
                self._active.pop(key, None)  # không giữ khóa rỗng, không âm
            else:
                self._active[key] = current - 1


class Cooldown:
    """Tạm khóa toàn hệ thống (ví dụ sau khi nhà cung cấp LLM trả 429)."""

    def __init__(self, *, clock: Clock = time.monotonic, max_seconds: float = 60.0) -> None:
        self._clock = clock
        self._max = max_seconds
        self._until = 0.0
        self._lock = threading.Lock()

    def block(self, seconds: float) -> None:
        with self._lock:
            until = self._clock() + max(0.0, min(seconds, self._max))
            self._until = max(self._until, until)  # không rút ngắn khóa đang có

    def remaining(self) -> float:
        with self._lock:
            return max(0.0, self._until - self._clock())
