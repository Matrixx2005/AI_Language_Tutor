"""Retrieval Lab: BM25 | Dense | Hybrid song song. Truy vấn mẫu CHỈ từ dev split."""
import time

import pandas as pd
import streamlit as st

from lab import dev_queries, load_retriever

st.title("Retrieval Lab")
st.caption("So sánh BM25, Dense (BGE-M3 + Qdrant), Hybrid (RRF) trên corpus bài ngữ pháp. "
           "Truy vấn mẫu lấy từ DEV split; test split không hiển thị ở bất kỳ đâu.")


@st.cache_resource(show_spinner="Đang nạp model nhúng và index (lần đầu khoảng 10–15 giây)…")
def retriever(mode: str):
    return load_retriever(mode)


samples = dev_queries()
sample = st.selectbox("Truy vấn mẫu (dev)", [""] + [q["query_id"] for q in samples],
                      format_func=lambda qid: "— tự nhập —" if qid == "" else
                      next(f"{q['query_id']} · {q['language']}/{q['query_type']} · {q['query'][:70]}" for q in samples if q["query_id"] == qid))
picked = next((q for q in samples if q["query_id"] == sample), None)
query = st.text_input("Truy vấn", value=picked["query"] if picked else "")
top_k = st.slider("top-k", 1, 10, 5)
if picked:
    st.caption(f"Đáp án (dev): {picked.get('document_id') or 'không có trong tài liệu (expected=none)'}")

if query:
    columns = st.columns(3)
    for column, mode in zip(columns, ["bm25", "dense", "hybrid"]):
        with column:
            st.subheader(mode)
            try:
                r = retriever(mode)
                started = time.perf_counter()
                hits = r.search(query, "en", top_k)
                latency = (time.perf_counter() - started) * 1000
            except Exception as exc:  # thiếu gói, Qdrant tắt, chưa có index...
                st.error(f"Không chạy được {mode}: {type(exc).__name__}. Kiểm tra: `docker compose up -d qdrant`, "
                         "`python scripts/index_corpus.py`, model trong `models/hf` (xem README).")
                continue
            st.caption(f"Độ trễ: {latency:.0f} ms")
            gold = picked.get("document_id") if picked else None
            st.dataframe(pd.DataFrame([{
                "rank": h.rank, "score": round(h.score, 4), "tiêu đề": h.title, "cấp": h.level,
                "đúng": "✅" if gold and h.document_id == gold else "",
            } for h in hits]), hide_index=True, width="stretch")
