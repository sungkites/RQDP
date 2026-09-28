"""Controlled workloads with equivalence hidden in already resolved queries."""

from __future__ import annotations

import itertools
import json
import multiprocessing as mp
import os
import random
import sys
import time
from pathlib import Path

from dominance import Dominance
from kernel import Kernel


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "v16" / "structured.jsonl"


def instance(seed, n, retired, radius, heterogeneous):
    queries = 4
    omega = list(itertools.product((0, 1), repeat=queries))
    index = {value: i for i, value in enumerate(omega)}
    prefixes = list(itertools.product((0, 1), repeat=retired)) or [()]
    rng = random.Random(seed)
    assigned = [prefixes[i % len(prefixes)] for i in range(n)]
    rng.shuffle(assigned)
    domains = []
    costs = []
    for prefix in assigned:
        domain = tuple(
            index[prefix + suffix]
            for suffix in itertools.product((0, 1), repeat=queries - retired)
        )
        domains.append(domain)
        costs.append(1 + (sum(prefix) % 3) if heterogeneous else 1)
    thresholds = []
    for j in range(retired):
        fixed_ones = sum(prefix[j] for prefix in assigned)
        thresholds.append(max(1, fixed_ones - radius))
    thresholds.extend([(n + 1) // 2] * (queries - retired))
    return domains, costs, omega, thresholds


def run(job):
    seed, n, retired, radius, heterogeneous, method = job
    domains, costs, omega, thresholds = instance(seed, n, retired, radius, heterogeneous)
    start = time.perf_counter()
    if method == "rqdp":
        engine = Dominance(domains, costs, omega, thresholds, radius, time_limit=5, limit=300000)
    else:
        engine = Kernel(domains, costs, omega, thresholds, radius, mode=method, time_limit=5, limit=300000)
    base = {
        "seed": seed,
        "size": n,
        "queries": 4,
        "retired_dimensions": retired,
        "initial_types": len(engine.types),
        "radius": radius,
        "cost_regime": "H" if heterogeneous else "U",
        "method": method,
    }
    try:
        decision, canonical = engine.plan(engine.start)
        return base | {
            "status": "complete",
            "seconds": time.perf_counter() - start,
            "worst_cost": decision[0],
            "states": engine.expanded,
            "residual_types": sum(count > 0 for count in canonical[0]),
            "active_queries": sum(value >= 0 for value in canonical[1]),
        }
    except RuntimeError as error:
        return base | {
            "status": "resource_limit",
            "seconds": time.perf_counter() - start,
            "states": engine.expanded,
            "error": str(error),
        }


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else min(32, os.cpu_count() or 1)
    methods = ("static", "residual", "rqdp")
    jobs = [
        (seed, n, retired, radius, heterogeneous, method)
        for seed in range(10)
        for n in (16, 24, 32, 48)
        for retired in (0, 1, 2, 3)
        for radius in (0, 1, 2)
        for heterogeneous in (False, True)
        for method in methods
    ]
    with mp.Pool(workers) as pool:
        rows = list(pool.imap_unordered(run, jobs, chunksize=1))
    rows.sort(key=lambda row: (row["seed"], row["size"], row["retired_dimensions"], row["radius"], row["cost_regime"], row["method"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    print(f"wrote {len(rows)} structured runs")


if __name__ == "__main__":
    mp.freeze_support()
    main()

