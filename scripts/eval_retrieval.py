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

QUERY_FILES = {"v1": ROOT / "data" / "evaluation" / "rag_queries_v1.json",
               "v2": ROOT / "data" / "evaluation" / "rag_queries_v2.json"}
BOOTSTRAP_ROUNDS = 1000
BOOTSTRAP_SEED = 20261128
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
    rows = [r for r in rows if r.get("gold")]  # nhóm expected=none không tính Recall/MRR
    n = len(rows)
    out = {"n": n}
    for k in KS:
        out[f"recall@{k}"] = round(sum(1 for r in rows if r["gold_rank"] and r["gold_rank"] <= k) / n, 4) if n else None
    out["mrr@10"] = round(sum(1 / r["gold_rank"] for r in rows if r["gold_rank"]) / n, 4) if n else None
    return out


def load_queries(split: str, version: str = "v1") -> list[dict]:
    data = json.loads(QUERY_FILES[version].read_text(encoding="utf-8"))
    queries = data["queries"] if isinstance(data, dict) else data
    return [q for q in queries if q["split"] == split]


def per_query_scores(rows: list[dict]) -> tuple[list[float], list[float]]:
    """(hit@3, reciprocal rank) cho từng truy vấn có đáp án — đầu vào của bootstrap."""
    rows = [r for r in rows if r.get("gold")]
    return ([1.0 if r["gold_rank"] and r["gold_rank"] <= 3 else 0.0 for r in rows],
            [1.0 / r["gold_rank"] if r["gold_rank"] else 0.0 for r in rows])


def bootstrap_ci(values: list[float], rounds: int = BOOTSTRAP_ROUNDS, seed: int = BOOTSTRAP_SEED) -> dict:
    import random

    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(rounds))
    return {"mean": round(sum(values) / n, 4), "ci95": [round(means[int(0.025 * rounds)], 4), round(means[int(0.975 * rounds) - 1], 4)]}


def paired_bootstrap(a: list[float], b: list[float], rounds: int = BOOTSTRAP_ROUNDS, seed: int = BOOTSTRAP_SEED) -> dict:
    """Khác biệt trung bình (a − b) trên CÙNG các truy vấn được lấy mẫu lại; p hai phía ≈ 2·min(P(Δ≤0), P(Δ≥0))."""
    import random

    rng = random.Random(seed)
    n = len(a)
    diffs = []
    for _ in range(rounds):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    p = 2 * min(sum(d <= 0 for d in diffs), sum(d >= 0 for d in diffs)) / rounds
    return {"diff": round(sum(x - y for x, y in zip(a, b)) / n, 4),
            "ci95": [round(diffs[int(0.025 * rounds)], 4), round(diffs[int(0.975 * rounds) - 1], 4)],
            "p_two_sided": round(min(1.0, p), 4), "significant_at_0.05": min(1.0, p) < 0.05}


def none_stats(rows: list[dict]) -> dict | None:
    """Nhóm expected=none: chỉ ĐO điểm top-1 so với nhóm có đáp án (chưa đặt ngưỡng từ chối)."""
    none = sorted(r["top1_score"] for r in rows if not r.get("gold") and r["top1_score"] is not None)
    answerable = sorted(r["top1_score"] for r in rows if r.get("gold") and r["top1_score"] is not None)
    if not none or not answerable:
        return None
    median = percentile(answerable, 0.5)
    p25 = percentile(answerable, 0.25)
    return {"n_none": len(none), "none_top1_median": round(percentile(none, 0.5), 4),
            "answerable_top1_median": round(median, 4), "answerable_top1_p25": round(p25, 4),
            "share_none_ge_answerable_median": round(sum(s >= median for s in none) / len(none), 4),
            "share_none_ge_answerable_p25": round(sum(s >= p25 for s in none) / len(none), 4)}


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
        gold = q.get("document_id")
        rows.append({
            "query_id": q["query_id"], "query_type": q["query_type"], "language": q["language"],
            "gold": gold, "gold_rank": ids.index(gold) + 1 if gold in ids else None,
            "top1_score": docs[0].score if docs else None, "top3": ids[:3],
        })
    by_type = {t: metrics([r for r in rows if r["query_type"] == t]) for t in sorted({r["query_type"] for r in rows})}
    by_lang = {t: metrics([r for r in rows if r["language"] == t]) for t in sorted({r["language"] for r in rows})}
    return {
        "overall": metrics(rows), "by_query_type": by_type, "by_language": by_lang, "none_group": none_stats(rows),
        "latency_ms": {"p50": round(percentile(latencies, 0.5), 1), "p95": round(percentile(latencies, 0.95), 1)},
        "per_query": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--methods", default="bm25,dense,hybrid")
    parser.add_argument("--keywords", choices=["settings", "off", "on", "both"], default="settings")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--queries", default="v1", choices=["v1", "v2"], help="bộ truy vấn (v2: 109 truy vấn, có nhóm expected=none)")
    parser.add_argument(TEST_FLAG, dest="allow_test", action="store_true", help="bắt buộc khi --split test")
    parser.add_argument("--note", default="", help="ghi chú lý do của lần chạy (lưu vào nhật ký)")
    args = parser.parse_args()
    if args.split == "test" and not args.allow_test:
        print(f"TỪ CHỐI: test split chỉ chạy khi có {TEST_FLAG} (Tuần 4 không chạy test split).", file=sys.stderr)
        return 2

    base = get_settings()
    variants = {"settings": [base.rag_index_keywords_vi], "off": [False], "on": [True], "both": [False, True]}[args.keywords]
    queries = load_queries(args.split, args.queries)
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

    # Khoảng tin cậy bootstrap (Recall@3, MRR) và so sánh cặp Hybrid − Dense trên CÙNG truy vấn.
    bootstrap = {"rounds": BOOTSTRAP_ROUNDS, "seed": BOOTSTRAP_SEED, "per_config": {}, "hybrid_vs_dense": {}}
    by_key = {(r["method"], r["index_keywords_vi"]): per_query_scores(r["per_query"]) for r in results}
    for (method, kw), (hits, rr) in by_key.items():
        bootstrap["per_config"][f"{method}{'+kw' if kw else ''}"] = {"recall@3": bootstrap_ci(hits), "mrr@10": bootstrap_ci(rr)}
    for kw in variants:
        if ("hybrid", kw) in by_key and ("dense", kw) in by_key:
            (h3, hrr), (d3, drr) = by_key[("hybrid", kw)], by_key[("dense", kw)]
            bootstrap["hybrid_vs_dense"][f"keywords_vi={kw}"] = {"recall@3": paired_bootstrap(h3, d3), "mrr@10": paired_bootstrap(hrr, drr)}

    run = {
        "run_at": started_at.isoformat(timespec="seconds"), "split": args.split, "n_queries": len(queries),
        "queries_file": QUERY_FILES[args.queries].name, "bootstrap": bootstrap,
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
