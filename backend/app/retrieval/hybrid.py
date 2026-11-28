"""Hybrid: BM25 + dense, hợp nhất bằng RRF (k và top-N mỗi nhánh cấu hình được)."""
from __future__ import annotations

from app.retrieval.rrf import rrf_fuse
from app.retrieval.types import RetrievedDoc, Retriever


class HybridRetriever:
    name = "hybrid"

    def __init__(self, sparse: Retriever, dense: Retriever, k: int = 60, candidates: int = 20):
        self.sparse, self.dense, self.k, self.candidates = sparse, dense, k, candidates

    def search(self, query: str, language_code: str, top_k: int, level: str | None = None, *,
               sparse_query: str | None = None, dense_query: str | None = None) -> list[RetrievedDoc]:
        """sparse_query/dense_query: truy vấn riêng cho từng nhánh (ví dụ sau khi viết lại truy vấn); mặc định = query."""
        n = max(self.candidates, top_k)
        sparse = self.sparse.search(sparse_query or query, language_code, n, level)
        dense = self.dense.search(dense_query or query, language_code, n, level)  # lỗi dense → RetrievalError, không hạ cấp ngầm
        by_chunk = {d.chunk_id: d for d in dense} | {d.chunk_id: d for d in sparse}
        ranks = {
            "bm25": {d.chunk_id: d.rank for d in sparse},
            "dense": {d.chunk_id: d.rank for d in dense},
        }
        dense_scores = {d.chunk_id: d.score for d in dense}
        fused = rrf_fuse([[d.chunk_id for d in sparse], [d.chunk_id for d in dense]], k=self.k)[:top_k]
        return [
            RetrievedDoc(
                document_id=by_chunk[cid].document_id, title=by_chunk[cid].title, level=by_chunk[cid].level,
                score=round(score, 6), text=by_chunk[cid].text, rank=i, chunk_id=cid,
                extra={"bm25_rank": ranks["bm25"].get(cid), "dense_rank": ranks["dense"].get(cid), "dense_score": dense_scores.get(cid)},
            )
            for i, (cid, score) in enumerate(fused, start=1)
        ]
