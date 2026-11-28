"""Dựng khối ngữ cảnh đánh số [1], [2]... cho prompt và kiểm tra trích dẫn sau khi sinh (hàm thuần).

Quy tắc kiểm tra: chỉ [n] với 1 ≤ n ≤ số tài liệu ĐÃ TRUY XUẤT là hợp lệ. [n] ngoài tập đó bị xóa khỏi
câu trả lời và ghi vào `invalid` — không bao giờ hiển thị một nguồn không có thật.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.retrieval.types import RetrievedDoc

CONTEXT_OPEN = "<<<TAI_LIEU>>>"
CONTEXT_CLOSE = "<<<HET_TAI_LIEU>>>"
# [1] hoặc [1, 2] / [1,2]; không bắt [abc] hay liên kết markdown [text](url).
_CITATION = re.compile(r"\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\](?!\()")


def format_context(docs: Sequence[RetrievedDoc]) -> str:
    """Đoạn ngữ cảnh đánh số; xóa chuỗi phân cách nếu lỡ xuất hiện trong nội dung (không cho đóng khối sớm)."""
    blocks = []
    for n, doc in enumerate(docs, start=1):
        text = doc.text.replace(CONTEXT_OPEN, "").replace(CONTEXT_CLOSE, "")
        title = doc.title.replace(CONTEXT_OPEN, "").replace(CONTEXT_CLOSE, "")
        blocks.append(f"[{n}] {title} (trình độ {doc.level})\n{text}")
    return f"{CONTEXT_OPEN}\n" + "\n\n".join(blocks) + f"\n{CONTEXT_CLOSE}"


@dataclass(frozen=True)
class CitationCheck:
    text: str  # câu trả lời sau khi bỏ trích dẫn không hợp lệ
    valid: tuple[int, ...]  # các n hợp lệ được dùng (tăng dần, không trùng)
    invalid: tuple[int, ...]  # các n bị loại vì không thuộc tập đã truy xuất


def check_citations(answer: str, n_sources: int) -> CitationCheck:
    valid: set[int] = set()
    invalid: set[int] = set()

    def replace(match: re.Match) -> str:
        numbers = [int(x) for x in re.split(r"\s*,\s*", match.group(1))]
        kept = [n for n in numbers if 1 <= n <= n_sources]
        valid.update(kept)
        invalid.update(n for n in numbers if n not in kept)
        return f"[{', '.join(str(n) for n in kept)}]" if kept else ""

    cleaned = _CITATION.sub(replace, answer)
    if invalid:
        cleaned = re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned)  # bỏ khoảng trắng thừa trước dấu câu
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return CitationCheck(cleaned, tuple(sorted(valid)), tuple(sorted(invalid)))
