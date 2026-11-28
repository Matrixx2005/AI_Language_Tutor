"""Bước 1 Tuần 4 — đo BGE-M3 trên CPU (Windows, không CUDA).

Mỗi lần đo chạy trong MỘT TIẾN TRÌNH RIÊNG (để RAM đỉnh và thời gian tải là của lần đó):
  - thời gian tải model (từ cache cục bộ models/hf, không mạng),
  - RAM đỉnh của tiến trình (PeakWorkingSetSize, Windows),
  - thời gian nhúng 45 văn bản theo batch (15 bài hiện có × 3 — corpus mở rộng làm SAU cổng này),
  - độ trễ nhúng 1 truy vấn cho từng truy vấn DEV (20 truy vấn; không dùng test split), p50/p95,
  - kích thước vector.

Chạy:  python scripts/bench_bge_m3.py --runs 3
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "BAAI/bge-m3"
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
CACHE = ROOT / "models" / "hf"
OUT = ROOT / "experiments" / "bge_m3_cpu_benchmark.json"


def peak_rss_bytes() -> int:
    if sys.platform != "win32":
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    counters = PMC()
    counters.cb = ctypes.sizeof(PMC)
    kernel32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE  # handle 64-bit: thiếu restype thì bị cắt → đo sai
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError("GetProcessMemoryInfo thất bại")
    return int(counters.PeakWorkingSetSize)


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def one_run() -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    t0 = time.perf_counter()
    import torch
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL, revision=REVISION, cache_folder=str(CACHE), device="cpu")
    load_s = time.perf_counter() - t0

    lessons = json.loads((ROOT / "data/processed/grammar_lessons_v1.json").read_text(encoding="utf-8"))
    texts = [f"{x['title']}\n{x['topic']}\n{x['content']}" for x in lessons] * 3
    queries = [q["query"] for q in json.loads((ROOT / "data/evaluation/rag_queries_v1.json").read_text(encoding="utf-8"))
               if q["split"] == "dev"]

    model.encode(["khởi động"], normalize_embeddings=True)  # warm-up (không tính)
    t1 = time.perf_counter()
    doc_vecs = model.encode(texts, batch_size=16, normalize_embeddings=True)
    batch_s = time.perf_counter() - t1

    latencies = []
    for q in queries:
        t = time.perf_counter()
        model.encode([q], normalize_embeddings=True)
        latencies.append((time.perf_counter() - t) * 1000)

    return {
        "load_seconds": round(load_s, 2),
        "peak_rss_gb": round(peak_rss_bytes() / 1024**3, 2),
        "batch_texts": len(texts),
        "batch_seconds": round(batch_s, 2),
        "query_count": len(latencies),
        "query_ms_p50": round(percentile(latencies, 0.5), 1),
        "query_ms_p95": round(percentile(latencies, 0.95), 1),
        "query_ms_max": round(max(latencies), 1),
        "vector_dim": int(doc_vecs.shape[1]),
        "torch_threads": torch.get_num_threads(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        print(json.dumps(one_run()))
        return

    runs = []
    for i in range(args.runs):
        out = subprocess.run([sys.executable, __file__, "--child"], capture_output=True, text=True, check=True,
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        runs.append(json.loads(out.stdout.strip().splitlines()[-1]))
        print(f"lần {i + 1}: {runs[-1]}")

    import platform

    import sentence_transformers
    import torch

    p95_worst = max(r["query_ms_p95"] for r in runs)
    ram_worst = max(r["peak_rss_gb"] for r in runs)
    result = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL, "revision": REVISION, "device": "cpu",
        "machine": {"platform": platform.platform(), "processor": platform.processor(), "cpu_count": os.cpu_count()},
        "versions": {"python": platform.python_version(), "torch": torch.__version__,
                     "sentence_transformers": sentence_transformers.__version__},
        "notes": ("45 văn bản = 15 bài hiện có × 3 (đo trước khi mở rộng corpus). "
                  "Truy vấn: 20 truy vấn DEV (bộ dev chỉ có 20), mỗi truy vấn nhúng riêng sau 1 lần warm-up. "
                  "Thời gian tải đọc từ cache cục bộ (lần 1 có thể chậm hơn vì cache ổ đĩa của hệ điều hành)."),
        "thresholds": {"query_ms_p95_max": 2000, "peak_rss_gb_max": 6},
        "runs": runs,
        "summary": {
            "query_ms_p50_median": statistics.median(r["query_ms_p50"] for r in runs),
            "query_ms_p95_worst": p95_worst,
            "peak_rss_gb_worst": ram_worst,
            "batch_seconds_median": statistics.median(r["batch_seconds"] for r in runs),
            "load_seconds_median": statistics.median(r["load_seconds"] for r in runs),
            "vector_dim": runs[0]["vector_dim"],
        },
        "gate_passed": p95_worst <= 2000 and ram_worst <= 6,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False), "gate_passed =", result["gate_passed"])


if __name__ == "__main__":
    main()
