"""V16 evaluation: real-data quality, exact planning, and controlled scaling."""

from __future__ import annotations

import argparse
import gc
import hashlib
import itertools
import json
import math
import multiprocessing as mp
import os
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

from anytime import AnytimeDominance
from dominance import Dominance
from kernel import Kernel
from metrics import certification_metrics, query_metrics
from robust_baselines import Finite, model
from workloads import groups


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "v16"
OUT.mkdir(parents=True, exist_ok=True)
FINITE_METHODS = ("ig", "ec2", "pairs", "asr", "minimax_rollout", "minimax_exact")
ALL_METHODS = FINITE_METHODS + ("rqdp", "rqdp_anytime")


def finite_trace(engine, truth, method):
    state = engine.full
    path = []
    while True:
        labels = [engine.labels[i] for i in engine.indices(state)]
        answer = []
        for j in range(len(labels[0])):
            values = {label[j] for label in labels}
            answer.append(next(iter(values)) if len(values) == 1 else None)
        path.append(answer)
        if all(value is not None for value in answer):
            return path
        action = engine.action(state, method)
        state = sum(
            1 << i
            for i in engine.indices(state)
            if engine.worlds[i][action] == truth[action]
        )
        if not state:
            raise AssertionError("reference feedback removed every allowed state")


def rqdp_trace(engine, truth):
    counts = list(engine.start[0])
    totals = [0] * engine.J
    radius = engine.start[2]
    remaining = set(range(len(truth)))
    path = []
    while True:
        state = (tuple(counts), tuple(totals), radius)
        answers = [
            1 if low >= threshold else 0 if high < threshold else None
            for (low, high), threshold in zip(engine.bounds(state), engine.k)
        ]
        path.append(answers)
        if all(value is not None for value in answers):
            return path
        decision, canonical = engine.plan(state)
        action_type = decision[-1]
        active = tuple(j for j, value in enumerate(canonical[1]) if value >= 0)
        signature = engine.signature(action_type, active, canonical[2] > 0)
        record = min(
            i
            for i in remaining
            if engine.signature(engine.record_types[i], active, canonical[2] > 0)
            == signature
        )
        record_type = engine.record_types[record]
        outcome = truth[record]
        extra = int(outcome not in engine.types[record_type][0])
        if extra > radius:
            raise RuntimeError("support violation")
        remaining.remove(record)
        counts[record_type] -= 1
        radius -= extra
        totals = [
            min(threshold, total + value)
            for threshold, total, value in zip(engine.k, totals, engine.omega[outcome])
        ]


def real_quality_jobs():
    for meta, omega, records in groups((4,)):
        for threshold in range(1, 5):
            yield meta, omega, records, threshold


def run_quality_job(job):
    meta, omega, records, threshold = job
    domains = [record["domain"] for record in records]
    truth = [record["truth"] for record in records]
    costs = [1] * len(records)
    thresholds = [threshold] * len(omega[0])
    reference = tuple(
        int(sum(omega[outcome][j] for outcome in truth) >= thresholds[j])
        for j in range(len(thresholds))
    )
    if sum(outcome not in domain for outcome, domain in zip(truth, domains)) > 1:
        return [meta | {"threshold": threshold, "status": "support_violation"}]

    worlds, labels, costs = model(domains, costs, omega, thresholds, 1)
    rows = []
    for method in FINITE_METHODS:
        engine = Finite(worlds, labels, costs)
        stats, _ = engine.evaluate(method)
        path = finite_trace(engine, truth, method)
        rows.append(
            meta
            | {
                "threshold": threshold,
                "method": method,
                "status": "complete",
                "truth": reference,
                "path": path,
                "reference_cost": len(path) - 1,
                "worst_cost": stats["worst"],
                "mean_model_cost": stats["mean"],
            }
        )
    for method, cls in (("rqdp", Dominance), ("rqdp_anytime", AnytimeDominance)):
        engine = cls(domains, costs, omega, thresholds, 1, time_limit=30, limit=500000)
        decision, _ = engine.plan(engine.start)
        path = rqdp_trace(engine, truth)
        rows.append(
            meta
            | {
                "threshold": threshold,
                "method": method,
                "status": "complete",
                "truth": reference,
                "path": path,
                "reference_cost": len(path) - 1,
                "worst_cost": decision[0],
                "secondary_area": decision[1] if len(decision) == 3 else None,
                "states": engine.expanded,
            }
        )
    return rows


def aggregate_quality(rows):
    summary = []
    complete = [row for row in rows if row.get("status") == "complete"]
    for dataset in sorted({row["dataset"] for row in complete}):
        for method in ALL_METHODS:
            subset = [
                row for row in complete if row["dataset"] == dataset and row["method"] == method
            ]
            if not subset:
                continue
            curve = []
            max_cost = 4
            for budget in range(max_cost + 1):
                truth = []
                answers = []
                workload_coverage = []
                for row in subset:
                    current = row["path"][min(budget, len(row["path"]) - 1)]
                    truth.extend(row["truth"])
                    answers.extend(current)
                    workload_coverage.append(sum(v is not None for v in current) / len(current))
                prediction = [int(value == 1) for value in answers]
                quality = query_metrics(truth, prediction)
                quality.pop("accuracy", None)
                certificate = certification_metrics(truth, answers)
                curve.append(
                    {
                        "budget": budget,
                        **quality,
                        **certificate,
                        "mean_workload_coverage": statistics.fmean(workload_coverage),
                    }
                )
            summary.append(
                {
                    "dataset": dataset,
                    "method": method,
                    "workloads": len(subset),
                    "outputs": sum(len(row["truth"]) for row in subset),
                    "mean_reference_cost": statistics.fmean(row["reference_cost"] for row in subset),
                    "mean_worst_cost": statistics.fmean(row["worst_cost"] for row in subset),
                    "f1_cost_auc": sum(point["f1"] for point in curve[:-1]) / max_cost,
                    "coverage_cost_auc": sum(point["coverage"] for point in curve[:-1]) / max_cost,
                    "curve": curve,
                }
            )
    return summary


def quality(workers):
    jobs = list(real_quality_jobs())
    with mp.Pool(processes=workers) as pool:
        nested = list(pool.imap_unordered(run_quality_job, jobs, chunksize=2))
    rows = [row for batch in nested for row in batch]
    rows.sort(key=lambda r: (r["dataset"], r["kind"], r["group"], r["threshold"], r.get("method", "")))
    with (OUT / "quality_paths.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    summary = aggregate_quality(rows)
    (OUT / "quality_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps([{k: v for k, v in row.items() if k != "curve"} for row in summary], indent=2))


def efficiency_job(job):
    meta, omega, records, method, radius, cost_regime, repeat = job
    domains = [record["domain"] for record in records]
    costs = [1 if cost_regime == "U" else record["cost_h"] for record in records]
    thresholds = [(len(records) + 1) // 2] * len(omega[0])
    cls = AnytimeDominance if method == "rqdp_anytime" else Dominance if method == "rqdp" else Kernel
    mode = method if method in {"identity", "static", "residual"} else "residual"
    start = time.perf_counter()
    engine = cls(
        domains,
        costs,
        omega,
        thresholds,
        radius,
        mode=mode,
        time_limit=5,
        limit=300000,
    ) if cls is Kernel else cls(
        domains, costs, omega, thresholds, radius, time_limit=5, limit=300000
    )
    row = meta | {
        "method": method,
        "radius": radius,
        "cost_regime": cost_regime,
        "repeat": repeat,
        "types": len(engine.types),
    }
    try:
        decision, _ = engine.plan(engine.start)
        row |= {
            "status": "complete",
            "seconds": time.perf_counter() - start,
            "worst_cost": decision[0],
            "states": engine.expanded,
            "cached_states": engine.value.cache_info().currsize,
        }
    except RuntimeError as error:
        row |= {
            "status": "resource_limit",
            "seconds": time.perf_counter() - start,
            "states": engine.expanded,
            "error": str(error),
        }
    return row


def efficiency(workers):
    methods = ("identity", "static", "residual", "rqdp", "rqdp_anytime")
    jobs = []
    for meta, omega, records in groups((4, 8, 16, 32)):
        for method in methods:
            for repeat in range(3 if meta["size"] <= 8 else 1):
                jobs.append((meta, omega, records, method, 1, "U", repeat))
    with mp.Pool(processes=workers) as pool:
        rows = list(pool.imap_unordered(efficiency_job, jobs, chunksize=1))
    rows.sort(key=lambda r: (r["dataset"], r["size"], r["group"], r["method"], r["repeat"]))
    with (OUT / "efficiency.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    summarize_efficiency(rows)


def summarize_efficiency(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["size"], row["method"])].append(row)
    summary = []
    for (dataset, size, method), subset in sorted(grouped.items()):
        complete = [row for row in subset if row["status"] == "complete"]
        summary.append(
            {
                "dataset": dataset,
                "size": size,
                "method": method,
                "tasks": len(subset),
                "completion_rate": len(complete) / len(subset),
                "median_ms": 1000 * statistics.median(row["seconds"] for row in complete) if complete else None,
                "mean_states": statistics.fmean(row["states"] for row in complete) if complete else None,
            }
        )
    (OUT / "efficiency_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def synthetic_instance(seed, n, queries, type_count, radius, heterogeneous):
    random.seed(seed)
    omega = list(itertools.product((0, 1), repeat=queries))
    templates = []
    for _ in range(type_count):
        center = random.randrange(len(omega))
        alternatives = {center}
        while len(alternatives) < min(3, len(omega)):
            alternatives.add(random.randrange(len(omega)))
        templates.append(tuple(sorted(alternatives)))
    domains = [templates[i % len(templates)] for i in range(n)]
    random.shuffle(domains)
    costs = [1 + random.randrange(4) if heterogeneous else 1 for _ in range(n)]
    thresholds = [max(1, round(n * fraction)) for fraction in [0.35, 0.5, 0.65, 0.45][:queries]]
    return domains, costs, omega, thresholds, radius


def synthetic_job(job):
    seed, n, queries, type_count, radius, heterogeneous, method = job
    domains, costs, omega, thresholds, radius = synthetic_instance(
        seed, n, queries, type_count, radius, heterogeneous
    )
    meta = {
        "seed": seed,
        "size": n,
        "queries": queries,
        "type_count": type_count,
        "radius": radius,
        "cost_regime": "H" if heterogeneous else "U",
        "method": method,
    }
    cls = AnytimeDominance if method == "rqdp_anytime" else Dominance if method == "rqdp" else Kernel
    mode = method if method in {"static", "residual"} else "residual"
    start = time.perf_counter()
    engine = cls(domains, costs, omega, thresholds, radius, mode=mode, time_limit=4, limit=300000) if cls is Kernel else cls(domains, costs, omega, thresholds, radius, time_limit=4, limit=300000)
    try:
        decision, _ = engine.plan(engine.start)
        return meta | {
            "status": "complete",
            "seconds": time.perf_counter() - start,
            "worst_cost": decision[0],
            "states": engine.expanded,
            "types": len(engine.types),
        }
    except RuntimeError as error:
        return meta | {
            "status": "resource_limit",
            "seconds": time.perf_counter() - start,
            "states": engine.expanded,
            "types": len(engine.types),
            "error": str(error),
        }


def synthetic(workers):
    methods = ("static", "residual", "rqdp", "rqdp_anytime")
    jobs = [
        (seed, n, queries, type_count, radius, heterogeneous, method)
        for seed in range(10)
        for n in (8, 16, 24, 32)
        for queries in (2, 3, 4)
        for type_count in (2, 4, 8)
        for radius in (0, 1, 2)
        for heterogeneous in (False, True)
        for method in methods
        if type_count <= n
    ]
    with mp.Pool(processes=workers) as pool:
        rows = list(pool.imap_unordered(synthetic_job, jobs, chunksize=1))
    rows.sort(key=lambda r: (r["seed"], r["size"], r["queries"], r["type_count"], r["radius"], r["cost_regime"], r["method"]))
    with (OUT / "synthetic.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    print(f"wrote {len(rows)} controlled runs")


def check():
    for seed in range(100):
        rng = random.Random(seed)
        n = rng.randint(2, 5)
        queries = rng.randint(1, 3)
        omega = list(itertools.product((0, 1), repeat=queries))
        domains = []
        for _ in range(n):
            domain = tuple(sorted(rng.sample(range(len(omega)), rng.randint(1, len(omega)))))
            domains.append(domain)
        costs = [rng.randint(1, 3) for _ in range(n)]
        thresholds = [rng.randint(1, n) for _ in range(queries)]
        radius = rng.randint(0, 1)
        exact = Finite(*model(domains, costs, omega, thresholds, radius)).ex(
            Finite(*model(domains, costs, omega, thresholds, radius)).full
        )[0]
        rqdp = Dominance(domains, costs, omega, thresholds, radius, time_limit=30).plan(
            Dominance(domains, costs, omega, thresholds, radius, time_limit=30).start
        )[0][0]
        anytime_engine = AnytimeDominance(domains, costs, omega, thresholds, radius, time_limit=30)
        anytime = anytime_engine.plan(anytime_engine.start)[0][0]
        if not exact == rqdp == anytime:
            raise AssertionError((seed, exact, rqdp, anytime))
    print("100 exhaustive primary-value checks passed")


def write_protocol():
    protocol = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "quality": "All complete size-4 batches from Flights, assets, Hospital and Beers; thresholds k=1..4; radius 1; unit costs; no outcome-based task removal.",
        "efficiency": "All complete size 4/8/16/32 batches; five exact variants; three serial-equivalent repeats at sizes 4/8 and one run at 16/32; 5 s and 300000-state soft limits.",
        "controlled": "10 fixed seeds across n, query count, initial type count, omission radius and cost regime; all failures retained.",
        "public_split": "SHA-256 identifier split fixed before evaluation. Candidate correction patterns use development rows only.",
        "timing": "Solver construction plus first action and exact primary value. Independent tasks are process-parallel; each task uses one process.",
        "hardware_note": "The algorithm is CPU-bound. The A100 host is used for its multi-core CPU; no GPU acceleration is claimed.",
        "methods": list(ALL_METHODS),
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).resolve().parent.glob("*.py"))
        },
    }
    (OUT / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("check", "quality", "efficiency", "synthetic"))
    parser.add_argument("--workers", type=int, default=max(1, min(32, os.cpu_count() or 1)))
    args = parser.parse_args()
    write_protocol()
    if args.stage == "check":
        check()
    elif args.stage == "quality":
        quality(args.workers)
    elif args.stage == "efficiency":
        efficiency(args.workers)
    else:
        synthetic(args.workers)


if __name__ == "__main__":
    mp.freeze_support()
    main()

