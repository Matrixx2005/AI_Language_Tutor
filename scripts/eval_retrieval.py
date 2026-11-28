"""Đánh giá truy xuất trên DEV split: Recall@1/3/5, MRR@10, độ trễ p50/p95, tách theo query_type và ngôn ngữ.

  python scripts/eval_retrieval.py                          # bm25, dense, hybrid; index_text theo .env
  python scripts/eval_retrieval.py --keywords both          # đo cả hai cấu hình index_text (có/không keywords_vi)

- Chỉ dùng truy vấn split=dev. Test split bị TỪ CHỐI trừ khi có --i-understand-this-uses-the-test-split
  (Tuần 4 không chạy test split).
- Không hạ cấp ngầm: Qdrant/model lỗi → dừng với lỗi rõ ràng (số liệu sai còn tệ hơn không có số liệu).
- Mỗi lần chạy lưu một file experiments/retrieval_dev_<thời gian>.json (cấu hình, phiên bản model, git commit,
  kết quả từng truy vấn) và thêm một dòng tóm tắt vào experiments/retrieval_runs.jsonl (nhật ký mọi lần thử).
- Cần đã nạp index: python scripts/index_corpus.py --keywords both
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.retrieval.service import build_retriever  # noqa: E402

QUERIES = ROOT / "data" / "evaluation" / "rag_queries_v1.json"
OUT_DIR = ROOT / "experiments"
TEST_FLAG = "--i-understand-this-uses-the-test-split"
KS = (1, 3, 5)
MRR_DEPTH = 10


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def metrics(rows: list[dict]) -> dict:
    n = len(rows)
    out = {"n": n}
    for k in KS:
        out[f"recall@{k}"] = round(sum(1 for r in rows if r["gold_rank"] and r["gold_rank"] <= k) / n, 4) if n else None
    out["mrr@10"] = round(sum(1 / r["gold_rank"] for r in rows if r["gold_rank"]) / n, 4) if n else None
    return out


def load_queries(split: str) -> list[dict]:
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))
    return [q for q in queries if q["split"] == split]


def git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"


def evaluate(method: str, settings, queries: list[dict]) -> dict:
    retriever = build_retriever(method, settings)
    retriever.search("warm-up", "en", 1)  # tải model / dựng index trước khi đo (không tính)
    rows, latencies = [], []
    for q in queries:
        started = time.perf_counter()
        docs = retriever.search(q["query"], "en", MRR_DEPTH)
        latencies.append((time.perf_counter() - started) * 1000)
        ids = [d.document_id for d in docs]
        rows.append({
            "query_id": q["query_id"], "query_type": q["query_type"], "language": q["language"],
            "gold": q["document_id"], "gold_rank": ids.index(q["document_id"]) + 1 if q["document_id"] in ids else None,
            "top3": ids[:3],
        })
    by_type = {t: metrics([r for r in rows if r["query_type"] == t]) for t in sorted({r["query_type"] for r in rows})}
    by_lang = {t: metrics([r for r in rows if r["language"] == t]) for t in sorted({r["language"] for r in rows})}
    return {
        "overall": metrics(rows), "by_query_type": by_type, "by_language": by_lang,
        "latency_ms": {"p50": round(percentile(latencies, 0.5), 1), "p95": round(percentile(latencies, 0.95), 1)},
        "per_query": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--methods", default="bm25,dense,hybrid")
    parser.add_argument("--keywords", choices=["settings", "off", "on", "both"], default="settings")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument(TEST_FLAG, dest="allow_test", action="store_true", help="bắt buộc khi --split test")
    parser.add_argument("--note", default="", help="ghi chú lý do của lần chạy (lưu vào nhật ký)")
    args = parser.parse_args()
    if args.split == "test" and not args.allow_test:
        print(f"TỪ CHỐI: test split chỉ chạy khi có {TEST_FLAG} (Tuần 4 không chạy test split).", file=sys.stderr)
        return 2

    base = get_settings()
    variants = {"settings": [base.rag_index_keywords_vi], "off": [False], "on": [True], "both": [False, True]}[args.keywords]
    queries = load_queries(args.split)
    started_at = datetime.now(timezone.utc)
    results = []
    for include in variants:
        settings = base.model_copy(update={"rag_index_keywords_vi": include})
        for method in [m.strip() for m in args.methods.split(",") if m.strip()]:
            result = evaluate(method, settings, queries)  # lỗi hạ tầng → exception, dừng (không hạ cấp)
            results.append({"method": method, "index_keywords_vi": include, **result})
            o = result["overall"]
            print(f"{method:7s} keywords_vi={str(include):5s} R@1={o['recall@1']:.2f} R@3={o['recall@3']:.2f} "
                  f"R@5={o['recall@5']:.2f} MRR={o['mrr@10']:.3f} p50={result['latency_ms']['p50']}ms p95={result['latency_ms']['p95']}ms")

    run = {
        "run_at": started_at.isoformat(timespec="seconds"), "split": args.split, "n_queries": len(queries),
        "git_commit": git_commit(), "note": args.note,
        "config": {"embedding_model": base.embedding_model, "embedding_revision": base.embedding_model_revision,
                   "rrf_k": base.rag_rrf_k, "candidates_per_branch": base.rag_candidates, "bm25": {"k1": 1.5, "b": 0.75},
                   "level_filter": False, "mrr_depth": MRR_DEPTH, "chunking": "1 bài = 1 chunk"},
        "results": results,
    }
    OUT_DIR.mkdir(exist_ok=True)
    stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    (OUT_DIR / f"retrieval_{args.split}_{stamp}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in run.items() if k != "results"} | {
        "results": [{"method": r["method"], "index_keywords_vi": r["index_keywords_vi"], **r["overall"], **r["latency_ms"]} for r in results]
    }
    with (OUT_DIR / "retrieval_runs.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(f"Đã lưu experiments/retrieval_{args.split}_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
