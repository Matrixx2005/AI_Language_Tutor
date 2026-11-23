"""Bộ giới hạn trong bộ nhớ: đồng hồ giả, không ngủ thật."""
import threading
import time
from collections import OrderedDict

import pytest

from app.core.rate_limit import ConcurrencyGuard, Cooldown, SlidingWindowLimiter


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ---------- Cửa sổ trượt ----------


def test_allows_up_to_limit_then_rejects_with_retry_after():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60, clock=clock)

    decisions = []
    for _ in range(3):
        decisions.append(limiter.hit("u1"))
        clock.advance(10)  # t = 0, 10, 20
    rejected = limiter.hit("u1")  # t = 30

    assert all(d.allowed for d in decisions)
    assert not rejected.allowed
    assert rejected.retry_after == pytest.approx(30)  # lần đầu (t=0) hết hạn ở t=60


def test_allows_again_after_window_slides():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60, clock=clock)
    limiter.hit("u1")
    limiter.hit("u1")
    assert not limiter.hit("u1").allowed

    clock.advance(60)

    assert limiter.hit("u1").allowed


def test_rejected_hits_are_not_recorded():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60, clock=clock)
    limiter.hit("u1")
    for _ in range(10):
        clock.advance(1)
        assert not limiter.hit("u1").allowed  # thử lại liên tục không kéo dài thời gian chờ
    clock.advance(50)  # t = 60 tính từ lần được chấp nhận
    assert limiter.hit("u1").allowed


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60, clock=FakeClock())
    assert limiter.hit("a").allowed
    assert not limiter.hit("a").allowed
    assert limiter.hit("b").allowed  # người A bị chặn không ảnh hưởng người B


def test_check_record_and_reset():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=900, clock=clock)
    assert limiter.check("k").allowed  # check không ghi nhận
    limiter.record("k")
    limiter.record("k")
    blocked = limiter.check("k")
    assert not blocked.allowed and blocked.retry_after == pytest.approx(900)
    limiter.reset("k")
    assert limiter.check("k").allowed


def test_zero_limit_means_disabled():
    limiter = SlidingWindowLimiter(limit=0, window_seconds=60, clock=FakeClock())
    assert all(limiter.hit("k").allowed for _ in range(1000))
    assert len(limiter) == 0


def test_expired_keys_are_swept_and_memory_is_bounded():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=5, window_seconds=60, clock=clock, max_keys=100)
    for i in range(1000):
        limiter.hit(f"ip-{i}")
    assert len(limiter) <= 100  # không phình quá max_keys

    clock.advance(61)
    limiter.hit("moi")
    assert len(limiter) == 1  # khóa hết hạn đã bị dọn


class SlowDict(OrderedDict):
    """Đọc giá trị RỒI mới ngủ: mở khe hở giữa "đọc" và "ghi" để lộ race condition nếu thiếu Lock.
    (Ngủ TRƯỚC khi đọc không đủ: các luồng thức dậy lần lượt và đọc giá trị đã cập nhật.)"""

    def get(self, key, default=None):
        value = super().get(key, default)
        time.sleep(0.002)
        return value


def _run_in_threads(target, count=20):
    barrier = threading.Barrier(count)

    def worker():
        barrier.wait()
        target()

    threads = [threading.Thread(target=worker) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_limiter_is_thread_safe():
    limiter = SlidingWindowLimiter(limit=5, window_seconds=60, clock=FakeClock())
    limiter._hits = SlowDict()
    allowed = []
    _run_in_threads(lambda: allowed.append(limiter.hit("k").allowed))
    assert allowed.count(True) == 5


# ---------- Giới hạn đồng thời ----------


def test_concurrency_guard_acquire_release():
    guard = ConcurrencyGuard()
    assert guard.acquire("u1", limit=1)
    assert not guard.acquire("u1", limit=1)
    assert guard.acquire("u2", limit=1)  # người khác không bị ảnh hưởng
    guard.release("u1")
    assert guard.acquire("u1", limit=1)
    guard.release("u1")
    guard.release("u2")
    assert len(guard) == 0  # khóa rỗng bị xóa, không phình bộ nhớ


def test_concurrency_guard_is_thread_safe():
    guard = ConcurrencyGuard()
    guard._active = SlowDict()
    acquired = []
    _run_in_threads(lambda: acquired.append(guard.acquire("u1", limit=1)))
    assert acquired.count(True) == 1


def test_release_never_goes_negative():
    guard = ConcurrencyGuard()
    guard.release("u1")
    assert guard.acquire("u1", limit=1)
    assert not guard.acquire("u1", limit=1)


# ---------- Tạm khóa toàn hệ thống ----------


def test_cooldown_blocks_then_expires_and_is_capped():
    clock = FakeClock()
    cooldown = Cooldown(clock=clock, max_seconds=60)
    assert cooldown.remaining() == 0

    cooldown.block(999)  # bị chặn tối đa 60 giây
    assert cooldown.remaining() == pytest.approx(60)
    clock.advance(30)
    assert cooldown.remaining() == pytest.approx(30)
    cooldown.block(5)  # không rút ngắn thời gian đang khóa
    assert cooldown.remaining() == pytest.approx(30)
    clock.advance(30)
    assert cooldown.remaining() == 0
