"""Thí nghiệm: đọc experiments/*.json và retrieval_runs.jsonl (CHỈ đọc)."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

EXP = Path(__file__).resolve().parents[2] / "experiments"
st.title("Thí nghiệm")

bench = EXP / "bge_m3_cpu_benchmark.json"
if bench.exists():
    b = json.loads(bench.read_text(encoding="utf-8"))
    st.subheader("BGE-M3 trên CPU")
    st.write(f"Cổng đạt: **{b['gate_passed']}** · p95 tệ nhất {b['summary']['query_ms_p95_worst']} ms · "
             f"RAM {b['summary']['peak_rss_gb_worst']} GB · {b['summary']['vector_dim']} chiều")
    st.dataframe(pd.DataFrame(b["runs"]), hide_index=True)

runs = sorted(EXP.glob("retrieval_dev_*.json"), reverse=True)
if not runs:
    st.info("Chưa có kết quả đánh giá (chạy scripts/eval_retrieval.py).")
    st.stop()
path = st.selectbox("Lần chạy", runs, format_func=lambda p: p.name)
run = json.loads(path.read_text(encoding="utf-8"))
st.caption(f"{run['run_at']} · split={run['split']} · {run['n_queries']} truy vấn · commit {run['git_commit'][:12]} · "
           f"bộ truy vấn: {run.get('queries_file', 'rag_queries_v1.json')} · ghi chú: {run.get('note', '')}")

rows = [{"phương pháp": r["method"], "keywords_vi": r["index_keywords_vi"], **r["overall"],
         "p50 ms": r["latency_ms"]["p50"], "p95 ms": r["latency_ms"]["p95"]} for r in run["results"]]
table = pd.DataFrame(rows)
st.subheader("Tổng thể")
st.dataframe(table, hide_index=True, width="stretch")
chart = table.assign(cấu_hình=[f"{m}{' +kw' if kw else ''}" for m, kw in zip(table["phương pháp"], table["keywords_vi"])])
st.bar_chart(chart.set_index("cấu_hình")[["recall@1", "recall@3", "mrr@10"]])

if run.get("bootstrap"):
    st.subheader("Khoảng tin cậy (bootstrap)")
    st.json(run["bootstrap"])

for key, label in [("by_query_type", "Theo loại truy vấn"), ("by_language", "Theo ngôn ngữ")]:
    st.subheader(label)
    st.dataframe(pd.DataFrame([{"phương pháp": r["method"], "keywords_vi": r["index_keywords_vi"], "nhóm": g, **m}
                               for r in run["results"] for g, m in r[key].items()]), hide_index=True, width="stretch")

st.subheader("Truy vấn thất bại (đáp án không ở hạng 1)")
fails = [{"phương pháp": r["method"], "keywords_vi": r["index_keywords_vi"], **{k: q[k] for k in ("query_id", "language", "query_type", "gold", "gold_rank")},
          "top3": ", ".join(q["top3"])} for r in run["results"] for q in r["per_query"] if q.get("gold") and q["gold_rank"] != 1]
st.dataframe(pd.DataFrame(fails), hide_index=True, width="stretch")

log = EXP / "retrieval_runs.jsonl"
if log.exists():
    with st.expander("Nhật ký mọi lần chạy (retrieval_runs.jsonl)"):
        st.dataframe(pd.DataFrame([json.loads(line) | {"results": len(json.loads(line)["results"])}
                                   for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]), hide_index=True)
