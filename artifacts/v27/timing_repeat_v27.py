"""Rotated-order repeat timing for the two action-selection algorithms."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import statistics
import time
from pathlib import Path

from experiment_v27 import Dominance, fixed_batches
from residual_bound_greedy import ResidualBoundGreedy


HERE = Path(__file__).resolve().parent


def run(job):
    meta, omega, records, repeat = job
    domains = [record["domain"] for record in records]
    costs = [1] * len(records)
    thresholds = [(len(records) + 1) // 2] * len(omega[0])
    order = ("rbg", "rqdp") if int(hashlib.sha256(
        f"order|{meta['dataset']}|{meta['size']}|{meta['group']}|{repeat}".encode()
    ).hexdigest(), 16) % 2 == 0 else ("rqdp", "rbg")
    results = []
    for method in order:
        start = time.perf_counter()
        if method == "rbg":
            engine = ResidualBoundGreedy(domains, costs, omega, thresholds, 1)
            action = engine.choose(engine.start)
            status = "complete"
        else:
            engine = Dominance(domains, costs, omega, thresholds, 1,
                               time_limit=2.0, limit=200000)
            try:
                action = engine.plan(engine.start)[0][-1]
                status = "complete"
            except RuntimeError:
                action = None
                status = "resource_limit"
        results.append(meta | {"repeat": repeat, "method": method, "order": "/".join(order),
                               "status": status, "action": action,
                               "seconds": time.perf_counter() - start})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    batches = [(meta, omega, records) for meta, omega, records in fixed_batches()
               if meta["size"] in (8, 16)]
    jobs = [(meta, omega, records, repeat) for meta, omega, records in batches
            for repeat in range(3)]
    print(f"Batches {len(batches)}; repeated pairs {len(jobs)}", flush=True)
    with mp.Pool(args.workers) as pool:
        rows = [row for pair in pool.imap_unordered(run, jobs, chunksize=1) for row in pair]
    rows.sort(key=lambda r: (r["size"], r["dataset"], r["kind"], r["group"], r["repeat"], r["method"]))
    out = HERE / "results" / "rbg_rotated_timing.jsonl"
    with out.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    for size in (8, 16):
        matched = {}
        for row in rows:
            if row["size"] == size:
                key = row["dataset"], row["kind"], row["group"], row["repeat"]
                matched.setdefault(key, {})[row["method"]] = row
        complete = [pair for pair in matched.values() if pair["rqdp"]["status"] == "complete"]
        print({"size": size, "pairs": len(matched), "rqdp_complete": len(complete),
               "median_paired_speedup": statistics.median(pair["rqdp"]["seconds"] / pair["rbg"]["seconds"]
                                                         for pair in complete)}, flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    main()
