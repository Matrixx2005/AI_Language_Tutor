"""Phần dùng chung cho Retrieval Lab: nạp truy vấn DEV (không bao giờ test) và retriever (cache một lần)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from logic import dev_only

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "data" / "evaluation"


def dev_queries() -> list[dict]:
    """Truy vấn mẫu: bộ v2 nếu có, không thì v1 — CHỈ split=dev."""
    path = EVAL_DIR / "rag_queries_v2.json"
    if not path.exists():
        path = EVAL_DIR / "rag_queries_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    queries = data["queries"] if isinstance(data, dict) else data
    return dev_only(queries)


def load_retriever(mode: str):
    """Import trực tiếp backend/app/retrieval (cùng code với API). Lỗi → exception để trang hiển thị hướng dẫn."""
    backend = str(ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.core.config import get_settings
    from app.retrieval.service import build_retriever

    return build_retriever(mode, get_settings())
