"""Dựng retriever theo chế độ (dense/hybrid/bm25) từ Settings; giữ singleton cho model, client, index BM25.

Mọi lỗi hạ tầng được chuẩn hóa thành RetrievalError. Chat bắt lỗi này để hạ cấp về llm_only.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.languages import get_language_config
from app.retrieval.bm25 import BM25Index, BM25Retriever
from app.retrieval.corpus import corpus_chunks
from app.retrieval.dense import DenseRetriever
from app.retrieval.embedder import get_sentence_embedder
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.tokenizer import tokenize
from app.retrieval.types import RetrievalError, Retriever

RAG_MODES = ("llm_only", "dense", "hybrid")


def collection_prefix(include_keywords: bool) -> str:
    """Mỗi cấu hình index_text một collection riêng (không trộn vector của hai cấu hình)."""
    return "lessons_kwvi" if include_keywords else "lessons"


@lru_cache
def bm25_index(language_code: str, include_keywords: bool) -> BM25Index:
    config = get_language_config(language_code).retrieval
    if config is None:
        raise RetrievalError(f"Ngôn ngữ {language_code!r} chưa cấu hình retrieval")
    return BM25Index(corpus_chunks(language_code, include_keywords), lambda text: tokenize(text, config.tokenizer))


@lru_cache
def qdrant_client(url: str, timeout: int):
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        raise RetrievalError("Chưa cài qdrant-client") from exc
    return QdrantClient(url=url, timeout=timeout, check_compatibility=False)


def build_retriever(mode: str, settings: Settings | None = None, *, dense: DenseRetriever | None = None) -> Retriever:
    """mode: 'bm25' | 'dense' | 'hybrid'. `dense` cho phép test truyền DenseRetriever dùng Qdrant :memory:."""
    settings = settings or get_settings()
    include = settings.rag_index_keywords_vi
    sparse = BM25Retriever(lambda code: bm25_index(code, include))
    if mode == "bm25":
        return sparse
    if dense is None:
        embedder = get_sentence_embedder(settings.embedding_model, settings.embedding_model_revision,
                                         str(settings.embedding_cache_path))
        dense = DenseRetriever(qdrant_client(settings.qdrant_url, settings.qdrant_timeout_seconds), embedder,
                               prefix=collection_prefix(include))
    if mode == "dense":
        return dense
    if mode == "hybrid":
        return HybridRetriever(sparse, dense, k=settings.rag_rrf_k, candidates=settings.rag_candidates)
    raise ValueError(f"Chế độ truy xuất không hợp lệ: {mode!r}")
