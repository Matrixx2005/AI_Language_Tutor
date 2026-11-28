"""Tín hiệu "không tìm thấy" (B1): đặc trưng điểm truy xuất, AUC, chọn ngưỡng bằng cross-validation phân tầng.
Hàm thuần, không phụ thuộc thư viện ngoài."""
from __future__ import annotations

import random
from collections.abc import Sequence


def auc(positive: Sequence[float], negative: Sequence[float]) -> float:
    """AUC = P(điểm dương > điểm âm) + 0,5·P(bằng nhau) (Mann–Whitney). Dương = có đáp án, âm = expected=none."""
    if not positive or not negative:
        raise ValueError("cần ít nhất một mẫu mỗi lớp")
    wins = 0.0
    for p in positive:
        for n in negative:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(positive) * len(negative))


def stratified_folds(labels: Sequence[int], k: int, seed: int) -> list[list[int]]:
    """Chia chỉ số thành k fold, mỗi lớp được trộn (seed) rồi chia vòng tròn → tỷ lệ lớp gần đều giữa các fold."""
    rng = random.Random(seed)
    folds: list[list[int]] = [[] for _ in range(k)]
    for label in sorted(set(labels)):
        idx = [i for i, y in enumerate(labels) if y == label]
        rng.shuffle(idx)
        for j, i in enumerate(idx):
            folds[j % k].append(i)
    return [sorted(f) for f in folds]


def choose_threshold(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Ngưỡng t: từ chối khi điểm < t. Chọn t tối đa hóa Youden J = TPR(từ chối none) − FPR(từ chối nhầm có đáp án);
    hòa → ngưỡng nhỏ hơn (thận trọng, ít từ chối nhầm)."""
    candidates = sorted(set(scores)) + [max(scores) + 1e-9]
    pos = sum(1 for y in labels if y == 1)
    neg = len(labels) - pos
    best_t, best_j = candidates[0], -2.0
    for t in candidates:
        rejected_none = sum(1 for s, y in zip(scores, labels) if y == 0 and s < t)
        rejected_ans = sum(1 for s, y in zip(scores, labels) if y == 1 and s < t)
        j = (rejected_none / neg if neg else 0) - (rejected_ans / pos if pos else 0)
        if j > best_j + 1e-12:
            best_t, best_j = t, j
    return best_t


def cross_validated_rejection(scores: Sequence[float], labels: Sequence[int], k: int = 5, seed: int = 20261128) -> dict:
    """Ngưỡng chọn trên k−1 fold, áp lên fold còn lại. Trả quyết định từ chối cho từng mẫu + ngưỡng từng fold."""
    decisions = [False] * len(scores)
    thresholds = []
    for fold in stratified_folds(labels, k, seed):
        train = [i for i in range(len(scores)) if i not in set(fold)]
        t = choose_threshold([scores[i] for i in train], [labels[i] for i in train])
        thresholds.append(t)
        for i in fold:
            decisions[i] = scores[i] < t
    return {"decisions": decisions, "thresholds": thresholds}


def rejection_metrics(decisions: Sequence[bool], labels: Sequence[int]) -> dict:
    tp = sum(1 for d, y in zip(decisions, labels) if d and y == 0)  # từ chối đúng (none)
    fp = sum(1 for d, y in zip(decisions, labels) if d and y == 1)  # từ chối nhầm câu có đáp án
    fn = sum(1 for d, y in zip(decisions, labels) if not d and y == 0)
    n_ans = sum(1 for y in labels if y == 1)
    return {"precision": round(tp / (tp + fp), 4) if tp + fp else None, "recall": round(tp / (tp + fn), 4) if tp + fn else None,
            "false_reject_rate": round(fp / n_ans, 4) if n_ans else None, "tp": tp, "fp": fp, "fn": fn}


def dense_top_score(docs) -> float | None:
    """Đặc trưng dùng trong chat: điểm cosine dense cao nhất. Hybrid lưu cosine ở extra['dense_score'];
    chế độ dense thì score chính là cosine."""
    if not docs:
        return None
    if any("dense_score" in (d.extra or {}) for d in docs):
        values = [d.extra["dense_score"] for d in docs if d.extra.get("dense_score") is not None]
        return max(values) if values else None
    return docs[0].score
