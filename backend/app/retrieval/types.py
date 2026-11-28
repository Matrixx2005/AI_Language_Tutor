"""Kiểu dữ liệu dùng chung của lớp truy xuất (Tuần 4). Không phụ thuộc ngôn ngữ hay CEFR."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class RetrievalError(RuntimeError):
    """Hạ tầng truy xuất không dùng được (model chưa tải được, Qdrant không kết nối, chưa có index...).

    Trong chat: hạ cấp về llm_only (rag_fallback=true). Trong script đánh giá: dừng (không hạ cấp ngầm)."""


@dataclass(frozen=True)
class Chunk:
    """Một đơn vị được index. Mặc định 1 bài = 1 chunk (bài ngắn ≤ ~150 từ)."""

    chunk_id: str  # "<document_id>#<số thứ tự>"
    document_id: str
    title: str
    level: str
    topic: str
    language_code: str
    text: str  # nội dung hiển thị/đưa vào prompt (phần nội dung bài)
    index_text: str  # văn bản dùng để nhúng/BM25 (title + topic + nội dung [+ keywords_vi])
    content_hash: str  # sha256 của index_text: index lại chỉ khi đổi


@dataclass(frozen=True)
class RetrievedDoc:
    document_id: str
    title: str
    level: str
    score: float
    text: str
    rank: int  # 1 = cao nhất
    chunk_id: str = ""
    extra: dict = field(default_factory=dict, compare=False)


class Retriever(Protocol):
    name: str

    def search(self, query: str, language_code: str, top_k: int, level: str | None = None) -> list[RetrievedDoc]:
        """Trả tối đa top_k tài liệu CÙNG language_code (bắt buộc), sắp theo điểm giảm dần."""
        ...
