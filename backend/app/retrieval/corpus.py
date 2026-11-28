"""Nạp corpus theo ngôn ngữ, dựng index_text và chia chunk.

- Corpus và file từ khóa lấy từ languages/<code>.yaml (khối `retrieval`), không hardcode.
- index_text = title + topic + content (mặc định) hoặc + keywords_vi (RAG_INDEX_KEYWORDS_VI=true);
  dùng GIỐNG HỆT cho dense và BM25.
- Chunker: 1 bài = 1 chunk khi bài ngắn; bài dài hơn `max_words` tách theo câu thành các đoạn
  ≤ max_words (không cắt giữa câu), mỗi đoạn mang tiêu đề/chủ đề của bài.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.core.languages import get_language_config
from app.retrieval.types import Chunk, RetrievalError

DEFAULT_MAX_WORDS = 200  # bài hiện tại ≤ 160 từ (validator) → luôn 1 chunk
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Lesson:
    document_id: str
    title: str
    level: str
    topic: str
    language_code: str
    content: str
    keywords_vi: tuple[str, ...] = ()


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_END.split(text.strip()) if s]


def chunk_text(text: str, max_words: int = DEFAULT_MAX_WORDS) -> list[str]:
    """Gom câu thành đoạn ≤ max_words. Một câu dài hơn max_words đứng riêng (không cắt giữa câu)."""
    if max_words < 1:
        raise ValueError("max_words phải ≥ 1")
    if len(text.split()) <= max_words:
        return [text.strip()]
    parts: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in split_sentences(text):
        words = len(sentence.split())
        if current and count + words > max_words:
            parts.append(" ".join(current))
            current, count = [], 0
        current.append(sentence)
        count += words
    if current:
        parts.append(" ".join(current))
    return parts


def build_index_text(lesson: Lesson, chunk: str, include_keywords: bool) -> str:
    pieces = [lesson.title, lesson.topic, chunk]
    if include_keywords and lesson.keywords_vi:
        pieces.append(" ; ".join(lesson.keywords_vi))
    return "\n".join(pieces)


def lesson_chunks(lesson: Lesson, include_keywords: bool, max_words: int = DEFAULT_MAX_WORDS) -> list[Chunk]:
    chunks = []
    for i, part in enumerate(chunk_text(lesson.content, max_words), start=1):
        index_text = build_index_text(lesson, part, include_keywords)
        chunks.append(
            Chunk(
                chunk_id=f"{lesson.document_id}#{i}",
                document_id=lesson.document_id,
                title=lesson.title,
                level=lesson.level,
                topic=lesson.topic,
                language_code=lesson.language_code,
                text=part,
                index_text=index_text,
                content_hash=hashlib.sha256(index_text.encode("utf-8")).hexdigest(),
            )
        )
    return chunks


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


@lru_cache
def load_lessons(language_code: str) -> tuple[Lesson, ...]:
    config = get_language_config(language_code).retrieval
    if config is None:
        raise RetrievalError(f"Ngôn ngữ {language_code!r} chưa cấu hình retrieval")
    try:
        records = json.loads(_resolve(config.corpus_file).read_text(encoding="utf-8"))
        keywords = {}
        if config.keywords_file and _resolve(config.keywords_file).is_file():
            keywords = json.loads(_resolve(config.keywords_file).read_text(encoding="utf-8"))["keywords"]
    except (OSError, ValueError, KeyError) as exc:
        raise RetrievalError(f"Không đọc được corpus: {type(exc).__name__}") from exc
    return tuple(
        Lesson(
            document_id=r["document_id"], title=r["title"], level=r["level"], topic=r["topic"],
            language_code=r["language_code"], content=r["content"],
            keywords_vi=tuple(keywords.get(r["document_id"], ())),
        )
        for r in records
        if r["language_code"] == language_code
    )


def corpus_chunks(language_code: str, include_keywords: bool, max_words: int = DEFAULT_MAX_WORDS) -> list[Chunk]:
    return [c for lesson in load_lessons(language_code) for c in lesson_chunks(lesson, include_keywords, max_words)]
