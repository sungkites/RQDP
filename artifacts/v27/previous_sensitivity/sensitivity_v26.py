"""Predeclared real-workload sensitivity experiment for the RQDP manuscript.

The script reads only released predicate-level inputs. It varies the omission
allowance and inspection-cost regime on fixed size-eight batches. No reference
answer is used to select a batch or to construct a planning task.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import statistics
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = Path(os.environ["RQDP_REPO"]) if os.environ.get("RQDP_REPO") else ROOT / "5实验代码" / "可信查询冲突治理_V16"
sys.path.insert(0, str(SOURCE / "src"))

from dominance import Dominance  # noqa: E402
from kernel import Kernel  # noqa: E402
from workloads import groups  # noqa: E402


def fixed_tasks():
    by_dataset = {}
    for meta, omega, records in groups((8,)):
        by_dataset.setdefault(meta["dataset"], []).append((meta, omega, records))
    selected = []
    for dataset, entries in sorted(by_dataset.items()):
        entries.sort(
            key=lambda item: hashlib.sha256(
                f"v26|{item[0]['dataset']}|{item[0]['kind']}|{item[0]['group']}".encode()
            ).hexdigest()
        )
        selected.extend(entries[: min(30, len(entries))])
    return selected


def solve(job):
    meta, omega, records, radius, cost_regime, method, repeat = job
    domains = [tuple(record["domain"]) for record in records]
    costs = [1 if cost_regime == "unit" else record["cost_h"] for record in records]
    thresholds = [4] * len(omega[0])
    start = time.perf_counter()
    if method == "rqdp":
        engine = Dominance(domains, costs, omega, thresholds, radius, time_limit=3, limit=200000)
    else:
        engine = Kernel(
            domains, costs, omega, thresholds, radius,
            mode=method, time_limit=3, limit=200000,
        )
    row = {
        **meta,
        "radius": radius,
        "cost_regime": cost_regime,
        "method": method,
        "repeat": repeat,
        "initial_types": len(engine.types),
        "total_cost": sum(costs),
    }
    try:
        decision, _ = engine.plan(engine.start)
        row.update(status="complete", worst_cost=decision[0])
    except RuntimeError as exc:
        row.update(status="resource_limit", error=str(exc))
    row.update(seconds=time.perf_counter() - start, states=engine.expanded)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    tasks = fixed_tasks()
    jobs = [
        (meta, omega, records, radius, cost_regime, method, repeat)
        for meta, omega, records in tasks
        for radius in (0, 1, 2)
        for cost_regime in ("unit", "heterogeneous")
        for method in ("static", "residual", "rqdp")
        for repeat in range(args.repeats)
    ]
    print(f"Fixed batches: {len(tasks)}; solves: {len(jobs)}", flush=True)
    results = []
    with mp.Pool(args.workers) as pool:
        for i, row in enumerate(pool.imap_unordered(solve, jobs, chunksize=3), 1):
            results.append(row)
            if i % 300 == 0:
                print(f"Completed {i}/{len(jobs)}", flush=True)
    results.sort(
        key=lambda row: (
            row["dataset"], row["kind"], row["group"], row["radius"],
            row["cost_regime"], row["method"], row["repeat"],
        )
    )
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    with (out / "sensitivity_v26.jsonl").open("w", encoding="utf-8") as stream:
        for row in results:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "dataset_batches": {
            dataset: sum(meta["dataset"] == dataset for meta, _, _ in tasks)
            for dataset in sorted({meta["dataset"] for meta, _, _ in tasks})
        },
        "selection": "SHA-256 sort of dataset, category, and batch index; first 30 per dataset or all if fewer",
        "size": 8,
        "thresholds": "4 for every query",
        "radii": [0, 1, 2],
        "costs": ["unit", "released fixed cost_h"],
        "repeats": args.repeats,
        "limits": "3 seconds and 200000 expanded states per solve",
        "timing": "solver construction plus the first completed optimal value and action",
        "reference_used_for_selection": False,
        "results": len(results),
    }
    (out / "manifest_v26.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    complete = [row for row in results if row["status"] == "complete"]
    print(
        "Median completed solve time (ms):",
        {
            method: round(1000 * statistics.median(row["seconds"] for row in complete if row["method"] == method), 3)
            for method in ("static", "residual", "rqdp")
        },
        flush=True,
    )


if __name__ == "__main__":
    mp.freeze_support()
    main()
