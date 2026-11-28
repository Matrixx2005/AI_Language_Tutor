"""Bộ nhúng văn bản.

- SentenceTransformerEmbedder: BGE-M3 (dense, CLS pooling + chuẩn hóa L2 theo cấu hình của model), chạy CPU.
  Singleton theo (model, revision, cache), tải LƯỜI ở lần dùng đầu (khóa để không tải hai lần khi nhiều
  request cùng đến). Route chat là hàm đồng bộ nên FastAPI chạy trong thread pool — việc nhúng không chặn
  event loop.
- HashingEmbedder: bộ nhúng giả TẤT ĐỊNH cho test (băm từ → vector), không mạng, không model.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import threading
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from app.retrieval.types import RetrievalError


class Embedder(Protocol):
    model_name: str
    revision: str

    @property
    def dim(self) -> int: ...

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, revision: str, cache_dir: str, batch_size: int = 16):
        self.model_name, self.revision, self.cache_dir, self.batch_size = model_name, revision, cache_dir, batch_size
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    # Chỉ đọc từ cache cục bộ khi chạy app: không tự tải 2 GB giữa một request chat.
                    os.environ.setdefault("HF_HUB_OFFLINE", "1")
                    try:
                        from sentence_transformers import SentenceTransformer

                        self._model = SentenceTransformer(
                            self.model_name, revision=self.revision, cache_folder=self.cache_dir, device="cpu"
                        )
                    except Exception as exc:  # thiếu gói, thiếu file model, hỏng cache...
                        raise RetrievalError(f"Không tải được model nhúng ({type(exc).__name__})") from exc
        return self._model

    @property
    def dim(self) -> int:
        return int(self._load().get_embedding_dimension())

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._load().encode(list(texts), batch_size=self.batch_size, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


@lru_cache
def get_sentence_embedder(model_name: str, revision: str, cache_dir: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(model_name, revision, cache_dir)


class HashingEmbedder:
    """Vector = túi từ đã băm vào `dim` chiều, chuẩn hóa L2. Cùng văn bản → cùng vector (tất định)."""

    def __init__(self, dim: int = 64, model_name: str = "hashing-test", revision: str = "v1"):
        self._dim, self.model_name, self.revision = dim, model_name, revision

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self._dim
            for token in re.findall(r"\w+", text.lower()):
                h = int.from_bytes(hashlib.md5(token.encode()).digest()[:4], "little")
                vec[h % self._dim] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out
