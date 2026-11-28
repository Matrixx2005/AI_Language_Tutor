"""Phân tích lỗi và chọn bài tiếp theo (hàm thuần, tất định khi có seed). Chưa phải cá nhân hóa (Tuần 6)."""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class AttemptFact:
    exercise_id: str
    document_id: str
    exercise_type: str
    is_correct: bool | None
    created_at: datetime


@dataclass(frozen=True)
class ErrorFact:
    error_type: str
    document_id: str | None
    created_at: datetime


def _rate(correct: int, total: int) -> float | None:
    return round(correct / total, 4) if total else None


def summarize(attempts: list[AttemptFact], errors: list[ErrorFact], now: datetime, tz: str) -> dict:
    zone = ZoneInfo(tz)
    graded = [a for a in attempts if a.is_correct is not None]
    by_topic: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for a in graded:
        by_topic[a.document_id][0] += int(a.is_correct)
        by_topic[a.document_id][1] += 1
        by_type[a.exercise_type][0] += int(a.is_correct)
        by_type[a.exercise_type][1] += 1
    errors_by_topic = Counter(e.document_id for e in errors if e.document_id)

    def trend(days: int) -> list[dict]:
        today = now.astimezone(zone).date()
        start = today - timedelta(days=days - 1)
        buckets = {start + timedelta(days=i): [0, 0] for i in range(days)}
        for a in graded:
            day = a.created_at.astimezone(zone).date()
            if day in buckets:
                buckets[day][0] += int(a.is_correct)
                buckets[day][1] += 1
        err_days = Counter(e.created_at.astimezone(zone).date() for e in errors)
        return [{"date": d.isoformat(), "attempts": v[1], "correct": v[0], "errors": err_days.get(d, 0)} for d, v in buckets.items()]

    # "Nên luyện": nhiều lỗi trước, rồi tỷ lệ sai cao, rồi id (tất định). Chỉ chủ đề có lỗi hoặc làm sai.
    practice = []
    for topic, (correct, total) in by_topic.items():
        wrong = total - correct
        if wrong or errors_by_topic.get(topic):
            practice.append({"document_id": topic, "errors": errors_by_topic.get(topic, 0), "wrong": wrong, "attempts": total,
                             "error_rate": round(wrong / total, 4) if total else None})
    practice.sort(key=lambda x: (-x["errors"], -(x["error_rate"] or 0), x["document_id"]))
    return {
        "attempts": len(attempts), "graded": len(graded), "correct": sum(1 for a in graded if a.is_correct),
        "top_error_types": [{"error_type": t, "count": c} for t, c in sorted(Counter(e.error_type for e in errors).items(), key=lambda x: (-x[1], x[0]))],
        "accuracy_by_topic": {t: _rate(c, n) for t, (c, n) in sorted(by_topic.items())},
        "accuracy_by_type": {t: _rate(c, n) for t, (c, n) in sorted(by_type.items())},
        "trend_7d": trend(7), "trend_30d": trend(30),
        "needs_practice": practice[:5],
    }


@dataclass(frozen=True)
class Candidate:
    exercise_id: str
    document_id: str
    exercise_type: str


def choose_next(candidates: list[Candidate], *, weak_topics: list[str], recent_errors: list[str], recent_exercise_ids: list[str],
                topic: str | None = None, exercise_type: str | None = None, seed: int | None = None) -> Candidate | None:
    """Lọc theo chủ đề/dạng → bỏ bài vừa làm gần đây (nếu còn lựa chọn khác) → ưu tiên chủ đề có lỗi gần đây,
    rồi chủ đề yếu từ placement → chọn ngẫu nhiên trong nhóm ưu tiên cao nhất (seed → tất định)."""
    pool = [c for c in candidates if (topic is None or c.document_id == topic) and (exercise_type is None or c.exercise_type == exercise_type)]
    if not pool:
        return None
    fresh = [c for c in pool if c.exercise_id not in set(recent_exercise_ids)]
    pool = fresh or pool

    def priority(c: Candidate) -> int:
        if c.document_id in recent_errors:
            return 0
        if c.document_id in weak_topics:
            return 1
        return 2

    best = min(priority(c) for c in pool)
    group = sorted((c for c in pool if priority(c) == best), key=lambda c: c.exercise_id)
    return random.Random(seed).choice(group)
