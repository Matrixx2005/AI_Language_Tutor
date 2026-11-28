"""Gọi LLM trong ngân sách cho các script hàng loạt (Tuần 5B).

- Cache theo sha256 của (task, system prompt, tin nhắn, schema) trong data/cache/llm/<task>/ → chạy lại = resume, không tốn lượt.
- --max-calls: trần số lời gọi THẬT của lần chạy; --dry-run: không gọi API, chỉ đếm số lời gọi dự kiến (cache miss).
- Tối đa `per_minute` lời gọi/phút (mặc định 8).
- 429 / hết hạn mức → dừng (BudgetStop) kèm thời điểm thử lại; tiến độ đã cache được giữ.
- Sổ ghi data/cache/llm/ledger.jsonl: mỗi lời gọi thật một dòng {task, at, model, ok} — để báo cáo số lời gọi thực tế.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.llm.errors import LLMError, LLMQuotaExhaustedError, LLMRateLimitError  # noqa: E402

CACHE = ROOT / "data" / "cache" / "llm"
LEDGER = CACHE / "ledger.jsonl"


class BudgetStop(RuntimeError):
    """Dừng có chủ đích: hết --max-calls, gặp 429/hết hạn mức. Tiến độ đã cache được giữ."""


def request_key(task: str, request) -> str:
    schema = request.response_schema.model_json_schema() if request.response_schema else None
    blob = json.dumps({"task": task, "system": request.system_prompt, "messages": [[m.role, m.content] for m in request.messages],
                       "schema": schema}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class BudgetedLLM:
    def __init__(self, llm, task: str, *, max_calls: int, dry_run: bool = False, per_minute: int = 8, sleep=time.sleep):
        self.llm, self.task, self.max_calls, self.dry_run = llm, task, max_calls, dry_run
        self.min_interval = 60.0 / per_minute if per_minute else 0.0
        self.sleep = sleep
        self.real_calls = 0
        self.cache_hits = 0
        self.planned = 0  # dry-run: số lời gọi sẽ cần
        self._last = 0.0
        (CACHE / task).mkdir(parents=True, exist_ok=True)

    def generate(self, request):
        """Trả về dict {"parsed": <dict|None>, "text": str, "model": str} (cache) hoặc None khi dry-run."""
        key = request_key(self.task, request)
        path = CACHE / self.task / f"{key}.json"
        if path.exists():
            self.cache_hits += 1
            return json.loads(path.read_text(encoding="utf-8"))
        if self.dry_run:
            self.planned += 1
            return None
        if self.real_calls >= self.max_calls:
            raise BudgetStop(f"Đã dùng hết --max-calls={self.max_calls} cho '{self.task}'. Chạy lại để tiếp tục (đã cache).")
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            self.sleep(wait)
        self._last = time.monotonic()
        self.real_calls += 1
        started = time.perf_counter()
        try:
            result = self.llm.generate(request)
            ok = True
        except (LLMRateLimitError, LLMQuotaExhaustedError) as error:
            self._ledger(None, False, error.code)
            retry = datetime.now(timezone.utc) + timedelta(seconds=error.retry_after or 60)
            raise BudgetStop(f"Gặp {error.code}: dừng để không tiêu thêm hạn mức. Thử lại sau khoảng "
                             f"{retry.astimezone().strftime('%H:%M')} (giờ máy).") from None
        except LLMError as error:
            self._ledger(None, False, error.code)
            raise
        # latency_ms: CHỈ thời gian lời gọi (không tính thời gian chờ giới hạn tần suất).
        record = {"parsed": result.parsed.model_dump() if result.parsed is not None else None, "text": result.text, "model": result.model,
                  "latency_ms": round((time.perf_counter() - started) * 1000, 1)}
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        self._ledger(result.model, ok, None)
        return record

    def _ledger(self, model, ok, code):
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"task": self.task, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "model": model, "ok": ok, "error": code}) + "\n")

    def report(self) -> str:
        if self.dry_run:
            return f"[{self.task}] DRY-RUN: {self.planned} lời gọi sẽ cần (đã có cache: {self.cache_hits})"
        return f"[{self.task}] lời gọi thật: {self.real_calls}, dùng cache: {self.cache_hits}"


def ledger_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                task = json.loads(line)["task"]
                counts[task] = counts.get(task, 0) + 1
    return counts
