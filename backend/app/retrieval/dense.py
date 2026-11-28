"""Truy xuất dense: vector (cosine) trong Qdrant, mỗi ngôn ngữ một collection `lessons_<language_code>`.

Metadata của index (tên + revision model, số chiều, hash nội dung từng chunk) lưu ở collection
`index_meta` (mỗi collection một điểm). Nạp idempotent: chỉ nhúng lại chunk đổi hash; xóa chunk không
còn trong corpus. Đổi model/số chiều → từ chối (phải chạy lại với --recreate), tránh trộn vector khác model.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from app.retrieval.embedder import Embedder
from app.retrieval.types import Chunk, RetrievalError, RetrievedDoc

META_COLLECTION = "index_meta"
_NAMESPACE = uuid.UUID("6f1c3a52-2d7e-4f0b-9a51-0c4be0d3a7e1")


def collection_name(language_code: str, prefix: str = "lessons") -> str:
    return f"{prefix}_{language_code}"


def point_id(key: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, key))


@dataclass(frozen=True)
class IndexReport:
    collection: str
    inserted: int
    updated: int
    unchanged: int
    deleted: int


class DenseRetriever:
    name = "dense"

    def __init__(self, client, embedder: Embedder, prefix: str = "lessons"):
        self.client, self.embedder, self.prefix = client, embedder, prefix
        self._checked: set[str] = set()

    # ---------- nạp index ----------

    def _read_meta(self, collection: str) -> dict | None:
        from qdrant_client import models

        if not self.client.collection_exists(META_COLLECTION):
            self.client.create_collection(META_COLLECTION, vectors_config=models.VectorParams(size=1, distance=models.Distance.DOT))
        found = self.client.retrieve(META_COLLECTION, ids=[point_id(collection)], with_payload=True)
        return dict(found[0].payload) if found else None

    def index(self, chunks: Sequence[Chunk], language_code: str, recreate: bool = False) -> IndexReport:
        from qdrant_client import models

        if any(c.language_code != language_code for c in chunks):
            raise ValueError("Mọi chunk phải cùng language_code với collection")
        collection = collection_name(language_code, self.prefix)
        dim = self.embedder.dim
        meta = self._read_meta(collection)
        if recreate and self.client.collection_exists(collection):
            self.client.delete_collection(collection)
            meta = None
        if meta and (meta.get("model") != self.embedder.model_name or meta.get("revision") != self.embedder.revision
                     or meta.get("dim") != dim):
            raise RetrievalError(
                f"Collection {collection} được nhúng bằng {meta.get('model')}@{meta.get('revision')} ({meta.get('dim')} chiều); "
                "chạy lại với --recreate để nhúng lại toàn bộ"
            )
        if not self.client.collection_exists(collection):
            self.client.create_collection(collection, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
            meta = None
        old_hashes: dict[str, str] = dict((meta or {}).get("chunk_hashes", {}))

        wanted = {c.chunk_id: c for c in chunks}
        to_embed = [c for c in chunks if old_hashes.get(c.chunk_id) != c.content_hash]
        if to_embed:
            vectors = self.embedder.encode([c.index_text for c in to_embed])
            self.client.upsert(collection, points=[
                models.PointStruct(id=point_id(c.chunk_id), vector=v, payload={
                    "chunk_id": c.chunk_id, "document_id": c.document_id, "title": c.title, "level": c.level,
                    "topic": c.topic, "language_code": c.language_code, "text": c.text, "content_hash": c.content_hash,
                }) for c, v in zip(to_embed, vectors)
            ])
        stale = [cid for cid in old_hashes if cid not in wanted]
        if stale:
            self.client.delete(collection, points_selector=models.PointIdsList(points=[point_id(cid) for cid in stale]))
        self.client.upsert(META_COLLECTION, points=[models.PointStruct(id=point_id(collection), vector=[1.0], payload={
            "collection": collection, "model": self.embedder.model_name, "revision": self.embedder.revision,
            "dim": dim, "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "chunk_hashes": {c.chunk_id: c.content_hash for c in chunks},
        })])
        self._checked.discard(collection)
        inserted = sum(1 for c in to_embed if c.chunk_id not in old_hashes)
        return IndexReport(collection, inserted, len(to_embed) - inserted, len(chunks) - len(to_embed), len(stale))

    # ---------- truy vấn ----------

    def _ensure_compatible(self, collection: str) -> None:
        if collection in self._checked:
            return
        if not self.client.collection_exists(collection):
            raise RetrievalError(f"Chưa có index {collection} (chạy scripts/index_corpus.py)")
        meta = self._read_meta(collection)
        if not meta or meta.get("model") != self.embedder.model_name or meta.get("revision") != self.embedder.revision:
            raise RetrievalError(f"Index {collection} không khớp model nhúng hiện tại")
        self._checked.add(collection)

    def search(self, query: str, language_code: str, top_k: int, level: str | None = None) -> list[RetrievedDoc]:
        from qdrant_client import models

        collection = collection_name(language_code, self.prefix)
        try:
            self._ensure_compatible(collection)
            vector = self.embedder.encode([query])[0]
            must = [models.FieldCondition(key="language_code", match=models.MatchValue(value=language_code))]
            if level is not None:
                must.append(models.FieldCondition(key="level", match=models.MatchValue(value=level)))
            hits = self.client.query_points(
                collection, query=vector, query_filter=models.Filter(must=must), limit=top_k, with_payload=True
            ).points
        except RetrievalError:
            raise
        except Exception as exc:  # Qdrant không kết nối/timeout, lỗi model...
            raise RetrievalError(f"Truy xuất dense lỗi ({type(exc).__name__})") from exc
        return [
            RetrievedDoc(document_id=h.payload["document_id"], title=h.payload["title"], level=h.payload["level"],
                         score=round(float(h.score), 6), text=h.payload["text"], rank=i, chunk_id=h.payload["chunk_id"])
            for i, h in enumerate(hits, start=1)
        ]
