"""Corpus: 33 bài, cấp độ, chủ đề, trạng thái duyệt (docs/CORPUS_REVIEW.md); lọc và tìm kiếm."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from logic import parse_review_status
from ui import plain

ROOT = Path(__file__).resolve().parents[2]
st.title("Corpus bài ngữ pháp")
lessons = json.loads((ROOT / "data/processed/grammar_lessons_v1.json").read_text(encoding="utf-8"))
review = ROOT / "docs/CORPUS_REVIEW.md"
status = parse_review_status(review.read_text(encoding="utf-8")) if review.exists() else {}

levels = st.multiselect("Cấp độ", sorted({x["level"] for x in lessons}), default=sorted({x["level"] for x in lessons}))
search = st.text_input("Tìm (tiêu đề, chủ đề, nội dung)").strip().lower()
rows = [x for x in lessons if x["level"] in levels and
        (not search or search in (x["title"] + " " + x["topic"] + " " + x["content"]).lower())]
st.caption(f"{len(rows)}/{len(lessons)} bài")
st.dataframe(pd.DataFrame([{"document_id": x["document_id"], "cấp": x["level"], "chủ đề": x["topic"], "tiêu đề": x["title"],
                            "phiên bản": x["version"], "trạng thái duyệt": status.get(x["document_id"], "—")} for x in rows]),
             hide_index=True, width="stretch")
pick = st.selectbox("Xem nội dung", [""] + [x["document_id"] for x in rows])
if pick:
    lesson = next(x for x in rows if x["document_id"] == pick)
    st.subheader(lesson["title"])
    plain(lesson["content"])
    st.caption(f"{lesson['source']} · {lesson['license']}")
