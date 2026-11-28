"""Reciprocal Rank Fusion (Cormack và cộng sự, 2009): hàm thuần.

  RRF(d) = Σ_nhánh 1 / (k + rank_nhánh(d))     (rank bắt đầu từ 1; tài liệu vắng mặt ở nhánh nào thì không cộng)

Chỉ dùng THỨ HẠNG, không dùng điểm gốc (BM25 và cosine không cùng thang đo). Hòa điểm: ưu tiên thứ hạng
tốt nhất ở bất kỳ nhánh nào, rồi theo id để kết quả tất định.
"""
from __future__ import annotations

from collections.abc import Sequence


def rrf_scores(rankings: Sequence[Sequence[str]], k: int = 60) -> dict[str, float]:
    if k < 1:
        raise ValueError("k phải ≥ 1")
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def rrf_fuse(rankings: Sequence[Sequence[str]], k: int = 60) -> list[tuple[str, float]]:
    scores = rrf_scores(rankings, k)
    best_rank = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            best_rank[doc_id] = min(best_rank.get(doc_id, rank), rank)
    return sorted(scores.items(), key=lambda item: (-item[1], best_rank[item[0]], item[0]))
