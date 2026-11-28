"""Viết lại truy vấn (B1, Tuần 5B): LLM rút truy vấn + từ khóa TIẾNG ANH từ câu hỏi (Việt hoặc Anh) để BM25/dense
khớp corpus tiếng Anh. Tắt mặc định (RAG_QUERY_REWRITE) cho đến khi thỏa quy tắc quyết định trong experiments/README.md.

- Câu hỏi là DỮ LIỆU trong khối phân cách (chống prompt injection); giới hạn độ dài đầu vào và đầu ra.
- Lỗi LLM hoặc đầu ra sai định dạng → Rewrite(ok=False): truy xuất dùng câu gốc, không bao giờ làm hỏng truy xuất.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.prompts import render_prompt
from app.llm.errors import LLMError
from app.llm.types import ChatMessage, LLMRequest

OPEN, CLOSE = "<<<CAU_HOI>>>", "<<<HET_CAU_HOI>>>"
MAX_INPUT_CHARS = 300
MAX_QUERY_CHARS = 200
MAX_KEYWORDS = 6
MAX_KEYWORD_CHARS = 40


@dataclass(frozen=True)
class Rewrite:
    query_en: str = ""
    keywords_en: tuple[str, ...] = ()
    ok: bool = False
    error: str | None = None

    @property
    def text(self) -> str:
        return " ".join([self.query_en, *self.keywords_en]).strip()


class RewriteItem(BaseModel):
    id: str = Field(max_length=40)
    query_en: str = Field(max_length=2000)
    keywords_en: list[str] = Field(default_factory=list, max_length=50)


class RewriteOutput(BaseModel):
    items: list[RewriteItem]


class QueryRewriter(Protocol):
    def rewrite_batch(self, queries: list[tuple[str, str]]) -> dict[str, Rewrite]: ...


@dataclass
class FakeRewriter:
    """Cho test: ánh xạ cố định câu gốc → Rewrite; fail=True giả lập LLM lỗi."""

    mapping: dict[str, Rewrite] = field(default_factory=dict)
    fail: bool = False

    def rewrite_batch(self, queries):
        if self.fail:
            return {qid: Rewrite(ok=False, error="fake_failure") for qid, _ in queries}
        return {qid: self.mapping.get(text, Rewrite(ok=False, error="missing")) for qid, text in queries}


def _clean_input(text: str) -> str:
    return " ".join(text.replace(OPEN, "").replace(CLOSE, "").split())[:MAX_INPUT_CHARS]


def build_rewrite_request(queries: list[tuple[str, str]], language_code: str = "en") -> LLMRequest:
    lines = "\n".join(f"{qid}: {_clean_input(text)}" for qid, text in queries)
    prompt = render_prompt(language_code, "query_rewrite", questions=lines)
    return LLMRequest(system_prompt=prompt, messages=(ChatMessage("user", "Rewrite the questions."),),
                      response_schema=RewriteOutput, max_output_tokens=2048)


def parse_rewrite_output(parsed: object, ids: list[str]) -> dict[str, Rewrite]:
    """Kiểm tra chặt: sai định dạng → mọi id ok=False; cắt độ dài; id lạ bị bỏ; id thiếu → ok=False."""
    try:
        output = parsed if isinstance(parsed, RewriteOutput) else RewriteOutput.model_validate(parsed)
    except ValidationError:
        return {qid: Rewrite(ok=False, error="invalid_output") for qid in ids}
    found = {}
    for item in output.items:
        if item.id not in ids:
            continue
        query = " ".join(item.query_en.split())[:MAX_QUERY_CHARS]
        keywords = tuple(" ".join(k.split())[:MAX_KEYWORD_CHARS] for k in item.keywords_en if k.strip())[:MAX_KEYWORDS]
        found[item.id] = Rewrite(query, keywords, ok=bool(query or keywords))
    return {qid: found.get(qid, Rewrite(ok=False, error="missing")) for qid in ids}


class LLMRewriter:
    def __init__(self, llm, language_code: str = "en"):
        self.llm, self.language_code = llm, language_code

    def rewrite_batch(self, queries):
        ids = [qid for qid, _ in queries]
        try:
            result = self.llm.generate(build_rewrite_request(queries, self.language_code))
        except LLMError as error:
            return {qid: Rewrite(ok=False, error=error.code) for qid in ids}
        return parse_rewrite_output(result.parsed, ids)


def branch_queries(original: str, rewrite: Rewrite | None, mode: str) -> tuple[str, str]:
    """(truy vấn BM25, truy vấn dense) theo chế độ: none | bm25 (rewrite chỉ cho BM25) | both."""
    if rewrite is None or not rewrite.ok or mode == "none":
        return original, original
    sparse = f"{original} {rewrite.text}"
    return (sparse, original) if mode == "bm25" else (sparse, rewrite.text)
