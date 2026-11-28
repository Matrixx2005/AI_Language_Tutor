"""B1 (Tuần 5B): ablation viết lại truy vấn + tín hiệu "không tìm thấy" trên DEV v2. Không chạy test split.

  python scripts/eval_b1.py --dry-run          # số lời gọi Gemini dự kiến (viết lại truy vấn, gộp 10/lời gọi)
  python scripts/eval_b1.py --max-calls 20     # chạy: rewrite (cache) → ablation → AUC/ngưỡng → experiments/
Quy tắc quyết định đã ghi TRƯỚC trong experiments/README.md (mục 4); script chỉ áp dụng quy tắc, không chọn tay.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_retrieval import (  # noqa: E402
    BOOTSTRAP_ROUNDS, BOOTSTRAP_SEED, bootstrap_ci, git_commit, load_queries, metrics, paired_bootstrap, percentile, per_query_scores,
)
from llm_budget import BudgetedLLM, BudgetStop  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.retrieval.confidence import auc, cross_validated_rejection, rejection_metrics  # noqa: E402
from app.retrieval.hybrid import HybridRetriever  # noqa: E402
from app.retrieval.rewrite import Rewrite, branch_queries, build_rewrite_request, parse_rewrite_output  # noqa: E402
from app.retrieval.service import build_retriever  # noqa: E402

OUT = ROOT / "experiments"
BATCH = 10
DEPTH = 10


def rewrite_all(queries, max_calls, dry_run) -> tuple[dict[str, Rewrite], dict[str, float], BudgetedLLM]:
    from app.llm import build_llm_service

    llm = None if dry_run else build_llm_service(get_settings().model_copy(update={"llm_max_retries": 0, "llm_fallback_model_ids": ""}))
    budget = BudgetedLLM(llm, "query_rewrite", max_calls=max_calls, dry_run=dry_run)
    rewrites, latency = {}, {}
    for start in range(0, len(queries), BATCH):
        batch = [(q["query_id"], q["query"]) for q in queries[start:start + BATCH]]
        record = budget.generate(build_rewrite_request(batch))
        if record is None:
            continue
        rewrites.update(parse_rewrite_output(record["parsed"], [qid for qid, _ in batch]))
        for qid, _ in batch:
            # Trong chat mỗi câu hỏi chờ TRỌN một lời gọi LLM → cộng nguyên thời gian lời gọi (không chia cho lô, không tính
            # thời gian chờ giới hạn tần suất). Ước tính thận trọng; lời gọi gộp 10 câu có thể chậm hơn lời gọi 1 câu.
            latency[qid] = float(record.get("latency_ms") or 0.0)
    return rewrites, latency, budget


def run_config(method: str, rewrite_mode: str, queries, rewrites, rewrite_ms, retrievers) -> dict:
    retriever = retrievers[method]
    rows, lat, lat_total = [], [], []
    for q in queries:
        sparse_q, dense_q = branch_queries(q["query"], rewrites.get(q["query_id"]), rewrite_mode)
        t = time.perf_counter()
        if isinstance(retriever, HybridRetriever):
            docs = retriever.search(q["query"], "en", DEPTH, sparse_query=sparse_q, dense_query=dense_q)
        else:
            docs = retriever.search(sparse_q if method == "bm25" else dense_q, "en", DEPTH)
        ms = (time.perf_counter() - t) * 1000
        lat.append(ms)
        lat_total.append(ms + (rewrite_ms.get(q["query_id"], 0.0) if rewrite_mode != "none" else 0.0))
        ids = [d.document_id for d in docs]
        gold = q.get("document_id")
        rows.append({"query_id": q["query_id"], "query_type": q["query_type"], "language": q["language"], "gold": gold,
                     "gold_rank": ids.index(gold) + 1 if gold in ids else None, "top3": ids[:3],
                     "top1_score": docs[0].score if docs else None,
                     "dense_top": max((d.extra.get("dense_score") or 0 for d in docs), default=None) if method == "hybrid"
                     else (docs[0].score if docs and method == "dense" else None),
                     "gap12": (docs[0].score - docs[1].score) if len(docs) > 1 else None,
                     "bm25_norm": (docs[0].score / sum(d.score for d in docs[:5])) if method == "bm25" and docs and sum(d.score for d in docs[:5]) else 0.0})
    groups = lambda key: {g: metrics([r for r in rows if r[key] == g]) for g in sorted({r[key] for r in rows})}  # noqa: E731
    return {"method": method, "rewrite": rewrite_mode, "overall": metrics(rows), "by_query_type": groups("query_type"),
            "by_language": groups("language"),
            "latency_ms": {"p50": round(percentile(lat, 0.5), 1), "p95": round(percentile(lat, 0.95), 1)},
            "latency_with_rewrite_ms": {"p50": round(percentile(lat_total, 0.5), 1), "p95": round(percentile(lat_total, 0.95), 1)},
            "per_query": rows}


def decide(base: dict, cand: dict) -> dict:
    (b3, brr), (c3, crr) = per_query_scores(base["per_query"]), per_query_scores(cand["per_query"])
    r3, mrr = paired_bootstrap(c3, b3), paired_bootstrap(crr, brr)
    improves = r3["ci95"][0] > 0 or mrr["ci95"][0] > 0
    other_ok = (r3["diff"] >= -0.02) and (mrr["diff"] >= -0.02)
    latency_ok = cand["latency_with_rewrite_ms"]["p95"] - base["latency_ms"]["p95"] <= 2000
    return {"recall@3": r3, "mrr@10": mrr, "rule_i_ci_lower_gt_0": improves, "rule_ii_no_drop_gt_0.02": other_ok,
            "rule_iii_p95_delta_le_2s": latency_ok, "enable": improves and other_ok and latency_ok}


def confidence_analysis(rows: list[dict]) -> dict:
    labels = [1 if r["gold"] else 0 for r in rows]
    out = {"n_answerable": sum(labels), "n_none": len(labels) - sum(labels), "auc": {}}
    for feature in ("dense_top", "gap12", "top1_score", "bm25_norm"):
        vals = [r.get(feature) for r in rows]
        if any(v is None for v in vals):
            continue
        out["auc"][feature] = round(auc([v for v, y in zip(vals, labels) if y], [v for v, y in zip(vals, labels) if not y]), 4)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-calls", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    queries = load_queries("dev", "v2")
    try:
        rewrites, rewrite_ms, budget = rewrite_all(queries, args.max_calls, args.dry_run)
    except BudgetStop as stop:
        print(f"DỪNG: {stop}")
        return 3
    print(budget.report())
    if args.dry_run:
        return 0
    settings = get_settings()
    retrievers = {m: build_retriever(m, settings) for m in ("bm25", "dense", "hybrid")}
    for r in retrievers.values():
        r.search("warm-up", "en", 1)
    configs = [("bm25", "none"), ("bm25", "both"), ("dense", "none"), ("dense", "both"), ("hybrid", "none"), ("hybrid", "bm25"), ("hybrid", "both")]
    results = {f"{m}|{rw}": run_config(m, rw, queries, rewrites, rewrite_ms, retrievers) for m, rw in configs}

    bootstrap = {k: {"recall@3": bootstrap_ci(per_query_scores(v["per_query"])[0]), "mrr@10": bootstrap_ci(per_query_scores(v["per_query"])[1])}
                 for k, v in results.items()}
    decisions = {k: decide(results[f"{k.split('|')[0]}|none"], v) for k, v in results.items() if not k.endswith("|none")}

    # Tín hiệu "không tìm thấy": AUC các đặc trưng + ngưỡng chọn bằng CV 5-fold trên dense_top (cấu hình gốc).
    dense_rows = results["dense|none"]["per_query"]
    hybrid_rows = results["hybrid|none"]["per_query"]
    bm_rows = {r["query_id"]: r for r in results["bm25|none"]["per_query"]}
    merged = [r | {"bm25_norm": bm_rows[r["query_id"]]["bm25_norm"], "gap12": r["gap12"], "rrf_top": h["top1_score"]}
              for r, h in zip(dense_rows, hybrid_rows)]
    conf = confidence_analysis(merged)
    labels = [1 if r["gold"] else 0 for r in merged]
    conf["auc"]["rrf_top"] = round(auc([r["rrf_top"] for r in merged if r["gold"]], [r["rrf_top"] for r in merged if not r["gold"]]), 4)
    scores = [r["dense_top"] for r in merged]
    cv = cross_validated_rejection(scores, labels, k=5, seed=BOOTSTRAP_SEED)
    rej = rejection_metrics(cv["decisions"], labels)
    import random

    rng = random.Random(BOOTSTRAP_SEED)
    boot_recall, boot_fr = [], []
    for _ in range(BOOTSTRAP_ROUNDS):
        idx = [rng.randrange(len(labels)) for _ in labels]
        m = rejection_metrics([cv["decisions"][i] for i in idx], [labels[i] for i in idx])
        if m["recall"] is not None:
            boot_recall.append(m["recall"])
        boot_fr.append(m["false_reject_rate"] or 0)
    boot_recall.sort(); boot_fr.sort()
    ci = lambda v: [round(v[int(0.025 * len(v))], 4), round(v[int(0.975 * len(v)) - 1], 4)] if v else None  # noqa: E731
    threshold = {"feature": "dense_top", "cv_thresholds": [round(t, 4) for t in cv["thresholds"]], "rejection": rej,
                 "recall_ci95": ci(boot_recall), "false_reject_ci95": ci(boot_fr)}
    threshold["enable"] = bool(threshold["recall_ci95"] and threshold["recall_ci95"][0] > 0.5 and (rej["false_reject_rate"] or 0) <= 0.10)
    conf["threshold"] = threshold

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = {"run_at": stamp, "split": "dev", "queries_file": "rag_queries_v2.json", "n_queries": len(queries), "git_commit": git_commit(),
           "note": args.note, "rewrite_calls": budget.report(),
           "rewrite_ok": sum(1 for r in rewrites.values() if r.ok), "rewrite_total": len(rewrites),
           "config": {"rrf_k": settings.rag_rrf_k, "candidates": settings.rag_candidates, "keywords_vi": False, "batch": BATCH,
                      "rewrite_modes": {"none": "câu gốc", "bm25": "BM25 = gốc + query_en + keywords_en; dense = gốc",
                                        "both": "BM25 = gốc + query_en + keywords_en; dense = query_en + keywords_en"}},
           "results": list(results.values()), "bootstrap": bootstrap, "decisions": decisions, "confidence": conf,
           "rewrites": {qid: {"query_en": r.query_en, "keywords_en": list(r.keywords_en), "ok": r.ok} for qid, r in rewrites.items()}}
    (OUT / f"b1_dev_{stamp}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (OUT / "retrieval_runs.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"run_at": stamp, "split": "dev", "kind": "b1_ablation", "queries_file": "rag_queries_v2.json",
                              "git_commit": run["git_commit"], "note": args.note,
                              "results": [{"method": r["method"], "rewrite": r["rewrite"], **r["overall"], **r["latency_ms"],
                                           "p95_with_rewrite": r["latency_with_rewrite_ms"]["p95"]} for r in results.values()]},
                             ensure_ascii=False) + "\n")
    for k, r in results.items():
        o = r["overall"]
        print(f"{k:14s} R@1={o['recall@1']:.3f} R@3={o['recall@3']:.3f} R@5={o['recall@5']:.3f} MRR={o['mrr@10']:.3f} "
              f"p95={r['latency_ms']['p95']} p95+rw={r['latency_with_rewrite_ms']['p95']}")
    for k, d in decisions.items():
        print(f"QUYẾT ĐỊNH {k}: ΔR@3={d['recall@3']['diff']} {d['recall@3']['ci95']} ΔMRR={d['mrr@10']['diff']} {d['mrr@10']['ci95']} → bật={d['enable']}")
    print("AUC:", conf["auc"], "| ngưỡng:", threshold)
    print(f"Đã lưu experiments/b1_dev_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
