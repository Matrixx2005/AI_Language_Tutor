"""Chất lượng bài tập: đọc experiments/exercises_*.json và grader_eval_*.json (CHỈ đọc)."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

EXP = Path(__file__).resolve().parents[2] / "experiments"
st.title("Chất lượng bài tập")
runs = sorted(EXP.glob("exercises_*.json"), reverse=True)
if not runs:
    st.info("Chưa có báo cáo (chạy scripts/eval_exercises.py).")
    st.stop()
r = json.loads(st.selectbox("Báo cáo", runs, format_func=lambda p: p.name).read_text(encoding="utf-8"))
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tổng bài", r["total"])
c2.metric("Qua kiểm tra", r["validated"])
c3.metric("Tỷ lệ qua", f"{r['pass_rate']:.0%}")
c4.metric("Khớp kiểm tra độc lập", f"{r['independent_match_rate']:.0%}" if r.get("independent_match_rate") is not None else "—")
st.subheader("Theo dạng bài")
st.dataframe(pd.DataFrame(r["by_type"]).T, width="stretch")
st.subheader("Theo trình độ")
st.dataframe(pd.DataFrame(r["by_level"]).T, width="stretch")
st.subheader("Lý do loại")
if r["reject_reasons"]:
    st.bar_chart(pd.Series(r["reject_reasons"]))
st.subheader("Duyệt bởi người")
st.json(r["review_status"])
st.caption(r.get("note", ""))
grader = sorted(EXP.glob("grader_eval_*.json"), reverse=True)
if grader:
    g = json.loads(grader[0].read_text(encoding="utf-8"))
    st.subheader("Bộ chấm AI (grading_v1, nhãn CHƯA duyệt bởi người)")
    st.json(g["summary"])
