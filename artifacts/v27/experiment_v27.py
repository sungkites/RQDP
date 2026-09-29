"""Pre-specified quality and scaling evaluation for residual-bound greedy.

Selection does not use reference outcomes or measured method performance.
Runs preserve all planned tasks, including time-limited exact searches.
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
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = Path(os.environ["RQDP_REPO"]) if os.environ.get("RQDP_REPO") else (
    ROOT if (ROOT / "src" / "workloads.py").exists() else ROOT / "5实验代码" / "可信查询冲突治理_V16"
)
sys.path.insert(0, str(SOURCE / "src"))

from dominance import Dominance  # noqa: E402
from metrics import certification_metrics, query_metrics  # noqa: E402
from workloads import groups  # noqa: E402
from residual_bound_greedy import ResidualBoundGreedy  # noqa: E402

OUT = HERE / "results"
OUT.mkdir(exist_ok=True)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def quality_job(job):
    meta, omega, records, threshold = job
    domains = [row["domain"] for row in records]
    truth = [row["truth"] for row in records]
    reference = tuple(
        int(sum(omega[outcome][j] for outcome in truth) >= threshold)
        for j in range(len(omega[0]))
    )
    start = time.perf_counter()
    engine = ResidualBoundGreedy(domains, [1] * 4, omega, [threshold] * len(omega[0]), 1)
    path = engine.reference_path(truth)
    if path["status"] != "certified":
        return meta | {"threshold": threshold, "status": path["status"]}
    assert path["answer"] == reference
    worst = engine.worst_cost(engine.start)
    assert worst >= path["reference_cost"]
    return meta | {
        "threshold": threshold, "method": "rbg", "status": "complete",
        "truth": reference, "path": [answers for _, answers in path["path"]],
        "reference_cost": path["reference_cost"], "worst_cost": worst,
        "seconds": time.perf_counter() - start, "policy_states": engine.worst_cost.cache_info().currsize,
    }


def quality_summary(rows):
    summaries = []
    for dataset in sorted({row["dataset"] for row in rows}):
        subset = [row for row in rows if row["dataset"] == dataset and row["status"] == "complete"]
        curve = []
        for budget in range(5):
            truth, answers = [], []
            for row in subset:
                truth.extend(row["truth"])
                answers.extend(row["path"][min(budget, len(row["path"]) - 1)])
            metric = query_metrics(truth, [int(answer == 1) for answer in answers])
            certificate = certification_metrics(truth, answers)
            curve.append({"budget": budget, "precision": metric["precision"],
                          "recall": metric["recall"], "f1": metric["f1"],
                          "coverage": certificate["coverage"]})
        summaries.append({
            "dataset": dataset, "method": "rbg", "workloads": len(subset),
            "outputs": sum(len(row["truth"]) for row in subset),
            "mean_reference_cost": statistics.fmean(row["reference_cost"] for row in subset),
            "mean_worst_cost": statistics.fmean(row["worst_cost"] for row in subset),
            "f1_cost_auc": sum(point["f1"] for point in curve[:-1]) / 4,
            "coverage_cost_auc": sum(point["coverage"] for point in curve[:-1]) / 4,
            "curve": curve,
        })
    return summaries


def quality(workers):
    jobs = [
        (meta, omega, records, threshold)
        for meta, omega, records in groups((4,))
        for threshold in range(1, 5)
    ]
    print(f"Quality workloads: {len(jobs)}", flush=True)
    with mp.Pool(workers) as pool:
        rows = list(pool.imap_unordered(quality_job, jobs, chunksize=4))
    rows.sort(key=lambda row: (row["dataset"], row["kind"], row["group"], row["threshold"]))
    write_jsonl(OUT / "rbg_quality_paths.jsonl", rows)
    summary = quality_summary(rows)
    (OUT / "rbg_quality_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps([{k: v for k, v in row.items() if k != "curve"} for row in summary], indent=2), flush=True)


def fixed_batches():
    by_size_dataset = defaultdict(list)
    for meta, omega, records in groups((8, 16, 24, 32)):
        by_size_dataset[(meta["size"], meta["dataset"])].append((meta, omega, records))
    selected = []
    for key in sorted(by_size_dataset):
        entries = by_size_dataset[key]
        entries.sort(key=lambda item: hashlib.sha256(
            f"v27|{item[0]['dataset']}|{item[0]['kind']}|{item[0]['size']}|{item[0]['group']}".encode()
        ).hexdigest())
        selected.extend(entries[: min(30, len(entries))])
    return selected


def scale_job(job):
    meta, omega, records, radius, cost_regime, limit_s = job
    domains = [record["domain"] for record in records]
    truth = [record["truth"] for record in records]
    costs = [1 if cost_regime == "unit" else record["cost_h"] for record in records]
    thresholds = [(len(records) + 1) // 2] * len(omega[0])
    reference = tuple(
        int(sum(omega[outcome][j] for outcome in truth) >= thresholds[j])
        for j in range(len(thresholds))
    )
    row = meta | {"radius": radius, "cost_regime": cost_regime, "thresholds": thresholds,
                  "reference_valid": sum(outcome not in domain for outcome, domain in zip(truth, domains)) <= radius}
    start = time.perf_counter()
    greedy = ResidualBoundGreedy(domains, costs, omega, thresholds, radius)
    action = greedy.choose(greedy.start)
    row.update(rbg_first_action=action, rbg_plan_seconds=time.perf_counter() - start,
               rbg_score_calls=greedy.score_calls)
    if row["reference_valid"]:
        reference_path = greedy.reference_path(truth)
        assert reference_path["status"] == "certified" and reference_path["answer"] == reference
        row.update(rbg_reference_cost=reference_path["reference_cost"],
                   rbg_inspections=reference_path["inspections"])
    if len(records) == 8:
        start_worst = time.perf_counter()
        row["rbg_worst_cost"] = greedy.worst_cost(greedy.start)
        row["rbg_worst_seconds"] = time.perf_counter() - start_worst
        row["rbg_policy_states"] = greedy.worst_cost.cache_info().currsize
    start = time.perf_counter()
    exact = Dominance(domains, costs, omega, thresholds, radius, time_limit=limit_s, limit=200000)
    try:
        decision, _ = exact.plan(exact.start)
        row.update(rqdp_status="complete", rqdp_worst_cost=decision[0],
                   rqdp_plan_seconds=time.perf_counter() - start,
                   rqdp_states=exact.expanded)
        if row["reference_valid"]:
            traced = exact.trace(truth)
            assert traced["status"] == "certified" and traced["answer"] == reference
            row["rqdp_reference_cost"] = traced["cost"]
    except RuntimeError as error:
        row.update(rqdp_status="resource_limit", rqdp_error=str(error),
                   rqdp_plan_seconds=time.perf_counter() - start,
                   rqdp_states=exact.expanded)
    if "rbg_worst_cost" in row and row["rqdp_status"] == "complete":
        assert row["rbg_worst_cost"] >= row["rqdp_worst_cost"]
    return row


def scaling(workers, limit_s):
    batches = fixed_batches()
    jobs = [(meta, omega, records, radius, regime, limit_s)
            for meta, omega, records in batches
            for radius in (0, 1, 2)
            for regime in ("unit", "heterogeneous")]
    print(f"Scale batches: {len(batches)}; condition runs: {len(jobs)}", flush=True)
    rows = []
    with mp.Pool(workers) as pool:
        for index, row in enumerate(pool.imap_unordered(scale_job, jobs, chunksize=1), 1):
            rows.append(row)
            if index % 100 == 0:
                print(f"Completed {index}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: (row["size"], row["dataset"], row["kind"], row["group"],
                               row["radius"], row["cost_regime"]))
    write_jsonl(OUT / "rbg_scaling.jsonl", rows)
    manifest = {
        "selection": "SHA-256 sort by dataset, category, size, and batch index; first 30 per dataset-size or all if fewer",
        "batches": len(batches), "runs": len(jobs), "sizes": [8, 16, 24, 32],
        "radii": [0, 1, 2], "cost_regimes": ["unit", "released fixed cost_h"],
        "exact_time_limit_seconds": limit_s, "exact_state_limit": 200000,
        "reference_used_for_selection": False,
        "counts_by_size_dataset": {f"{size}:{dataset}": sum(meta["size"] == size and meta["dataset"] == dataset for meta, _, _ in batches)
                                   for size, dataset in sorted({(meta["size"], meta["dataset"]) for meta, _, _ in batches})},
    }
    (OUT / "rbg_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": dict((status, sum(row["rqdp_status"] == status for row in rows))
                                     for status in sorted({row["rqdp_status"] for row in rows})),
                      "manifest": manifest}, indent=2), flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("quality", "scaling"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit-seconds", type=float, default=2.0)
    args = parser.parse_args()
    quality(args.workers) if args.phase == "quality" else scaling(args.workers, args.limit_seconds)
