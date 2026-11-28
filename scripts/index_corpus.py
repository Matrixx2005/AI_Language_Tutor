"""Nạp corpus bài học vào Qdrant (dense, BGE-M3). Idempotent: chỉ nhúng lại chunk đổi hash.

  python scripts/index_corpus.py                      # theo .env (RAG_INDEX_KEYWORDS_VI)
  python scripts/index_corpus.py --keywords both      # nạp cả hai cấu hình index_text (để đánh giá)
  python scripts/index_corpus.py --recreate           # xóa collection rồi nhúng lại toàn bộ (đổi model)

Cần: Qdrant đang chạy (docker compose up -d qdrant) và model đã có trong EMBEDDING_CACHE_DIR.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.retrieval.corpus import corpus_chunks  # noqa: E402
from app.retrieval.dense import DenseRetriever  # noqa: E402
from app.retrieval.embedder import get_sentence_embedder  # noqa: E402
from app.retrieval.service import collection_prefix, qdrant_client  # noqa: E402
from app.retrieval.types import RetrievalError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--language", default="en")
    parser.add_argument("--keywords", choices=["settings", "off", "on", "both"], default="settings")
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    variants = {"settings": [settings.rag_index_keywords_vi], "off": [False], "on": [True], "both": [False, True]}[args.keywords]
    embedder = get_sentence_embedder(settings.embedding_model, settings.embedding_model_revision, str(settings.embedding_cache_path))
    client = qdrant_client(settings.qdrant_url, settings.qdrant_timeout_seconds)
    try:
        for include in variants:
            started = time.perf_counter()
            chunks = corpus_chunks(args.language, include)
            report = DenseRetriever(client, embedder, prefix=collection_prefix(include)).index(chunks, args.language, args.recreate)
            print(f"{report.collection}: {len(chunks)} chunk — thêm {report.inserted}, cập nhật {report.updated}, "
                  f"không đổi {report.unchanged}, xóa {report.deleted} ({time.perf_counter() - started:.1f}s)")
    except RetrievalError as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Qdrant không chạy...
        print(f"LỖI: không nạp được index ({type(exc).__name__}: {exc}). Qdrant đã chạy chưa? docker compose up -d qdrant",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
