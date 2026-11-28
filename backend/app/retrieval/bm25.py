"""BM25 (Okapi) thuần Python — tự viết (~50 dòng) thay cho thư viện ngoài để kiểm soát tokenizer theo
ngôn ngữ và test được công thức.

  IDF(t)  = ln( (N − df + 0.5) / (df + 0.5) + 1 )            (luôn > 0)
  score   = Σ_t IDF(t) · tf·(k1+1) / ( tf + k1·(1 − b + b·|d|/avgdl) )
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence

from app.retrieval.types import Chunk, RetrievedDoc


def idf(n_docs: int, doc_freq: int) -> float:
    return math.log((n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)


class BM25Index:
    def __init__(self, chunks: Sequence[Chunk], tokenize: Callable[[str], list[str]], k1: float = 1.5, b: float = 0.75):
        self.chunks = list(chunks)
        self.tokenize = tokenize
        self.k1, self.b = k1, b
        self.doc_tokens = [Counter(tokenize(c.index_text)) for c in self.chunks]
        self.doc_len = [sum(t.values()) for t in self.doc_tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        df: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            df.update(tokens.keys())
        self.idf = {term: idf(len(self.chunks), freq) for term, freq in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = self.tokenize(query)
        out = []
        for tokens, length in zip(self.doc_tokens, self.doc_len):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * length / self.avgdl) if self.avgdl else self.k1
            for term in terms:
                tf = tokens.get(term, 0)
                if tf:
                    s += self.idf[term] * tf * (self.k1 + 1) / (tf + norm)
            out.append(s)
        return out


class BM25Retriever:
    name = "bm25"

    def __init__(self, index_for: Callable[[str], BM25Index]):
        self._index_for = index_for  # language_code → BM25Index (mỗi ngôn ngữ một index riêng)

    def search(self, query: str, language_code: str, top_k: int, level: str | None = None) -> list[RetrievedDoc]:
        index = self._index_for(language_code)
        ranked = sorted(
            (
                (score, chunk)
                for score, chunk in zip(index.scores(query), index.chunks)
                # Lọc ngôn ngữ BẮT BUỘC (kể cả khi index lẫn ngôn ngữ); lọc trình độ là tùy chọn.
                if score > 0 and chunk.language_code == language_code and (level is None or chunk.level == level)
            ),
            key=lambda pair: (-pair[0], pair[1].chunk_id),
        )[:top_k]
        return [
            RetrievedDoc(document_id=c.document_id, title=c.title, level=c.level, score=round(s, 6), text=c.text,
                         rank=i, chunk_id=c.chunk_id)
            for i, (s, c) in enumerate(ranked, start=1)
        ]
