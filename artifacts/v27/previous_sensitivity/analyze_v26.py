"""Audit-friendly analyses for the expanded RQDP comparison."""

from __future__ import annotations

import csv
import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = Path(os.environ["RQDP_REPO"]) if os.environ.get("RQDP_REPO") else ROOT / "5实验代码" / "可信查询冲突治理_V16"
ARCHIVE = BASE / "results" / "v16"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)


def load_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def interval(values):
    return [round(float(x), 3) for x in np.quantile(values, (0.025, 0.5, 0.975))]


def dataset_profile():
    rows = []
    for dataset in ("flights", "assets", "hospital", "beers"):
        data = json.loads((BASE / "data" / f"{dataset}_predicates.json").read_text(encoding="utf-8"))
        records = [record for collection in data["collections"] for record in collection["records"]]
        domains = [tuple(record["domain"]) for record in records]
        domain_count = Counter(domains)
        rows.append({
            "dataset": dataset,
            "records": len(records),
            "queries": len(data["omega"][0]),
            "legal_vectors": len(data["omega"]),
            "candidate_domains": len(domain_count),
            "mean_candidates": round(statistics.fmean(map(len, domains)), 3),
            "multi_candidate_pct": round(100 * sum(len(x) > 1 for x in domains) / len(domains), 1),
            "reference_omissions": sum(record["truth"] not in record["domain"] for record in records),
        })
    return rows


def paired_sensitivity():
    rows = load_jsonl(OUT / "sensitivity_v26.jsonl")
    runs = defaultdict(list)
    for row in rows:
        key = (row["dataset"], row["kind"], row["group"], row["radius"], row["cost_regime"], row["method"])
        runs[key].append(row)
    tasks = {}
    for key, subset in runs.items():
        done = [r for r in subset if r["status"] == "complete"]
        tasks[key] = {
            "complete": len(done) == len(subset),
            "median_seconds": statistics.median(r["seconds"] for r in done) if len(done) == len(subset) else None,
            "worst_cost": done[0]["worst_cost"] if len(done) == len(subset) else None,
            "median_states": statistics.median(r["states"] for r in done) if len(done) == len(subset) else None,
        }
    output = []
    for dataset in ("flights", "assets", "hospital", "beers"):
        for radius in (0, 1, 2):
            for costs in ("unit", "heterogeneous"):
                keys = [key for key in tasks if key[0] == dataset and key[3] == radius and key[4] == costs and key[5] == "static"]
                pairs = []
                agreement = []
                for key in keys:
                    static = tasks[key]
                    rqdp = tasks[key[:-1] + ("rqdp",)]
                    if static["complete"] and rqdp["complete"]:
                        pairs.append(static["median_seconds"] / rqdp["median_seconds"])
                        agreement.append(static["worst_cost"] == rqdp["worst_cost"])
                output.append({
                    "dataset": dataset,
                    "radius": radius,
                    "cost_regime": costs,
                    "tasks": len(keys),
                    "paired_complete": len(pairs),
                    "static_complete": sum(tasks[key]["complete"] for key in keys),
                    "rqdp_complete": sum(tasks[key[:-1] + ("rqdp",)]["complete"] for key in keys),
                    "median_static_over_rqdp": round(statistics.median(pairs), 3) if pairs else None,
                    "all_optima_agree": all(agreement),
                })
    return output


def original_speedup_bootstrap(reps=2000):
    rows = load_jsonl(ARCHIVE / "efficiency.jsonl")
    by_task = defaultdict(dict)
    for row in rows:
        if row["size"] != 8:
            continue
        key = row["dataset"], row["kind"], row["group"]
        by_task[key].setdefault(row["method"], []).append(row)
    output = []
    rng = np.random.default_rng(260929)
    for dataset in ("flights", "assets", "hospital", "beers"):
        ratios = []
        for key, methods in by_task.items():
            if key[0] != dataset:
                continue
            left = methods["identity"]
            right = methods["rqdp"]
            if all(r["status"] == "complete" for r in left + right):
                ratios.append(statistics.median(r["seconds"] for r in left) / statistics.median(r["seconds"] for r in right))
        arr = np.asarray(ratios)
        boot = [float(np.median(rng.choice(arr, len(arr), replace=True))) for _ in range(reps)]
        output.append({
            "dataset": dataset,
            "paired_tasks": len(arr),
            "median_speedup": round(float(np.median(arr)), 3),
            "bootstrap_95_ci": [round(float(x), 3) for x in np.quantile(boot, (0.025, 0.975))],
            "fraction_faster": round(float(np.mean(arr > 1)), 3),
        })
    return output


def quality_bootstrap(reps=1500):
    rows = load_jsonl(ARCHIVE / "quality_paths.jsonl")
    # Cluster by the source batch, not by its four reused thresholds.
    clusters = defaultdict(lambda: defaultdict(lambda: np.zeros((4, 3), dtype=np.int64)))
    for row in rows:
        if row.get("status") != "complete" or row["method"] not in ("rqdp", "rqdp_anytime", "ec2"):
            continue
        key = row["dataset"], row["kind"], row["group"]
        truth = row["truth"]
        for budget in range(4):
            answers = row["path"][min(budget, len(row["path"]) - 1)]
            pred = [int(answer == 1) for answer in answers]
            counts = (
                sum(a == b == 1 for a, b in zip(truth, pred)),
                sum(a == 0 and b == 1 for a, b in zip(truth, pred)),
                sum(a == 1 and b == 0 for a, b in zip(truth, pred)),
            )
            clusters[key][row["method"]][budget] += counts

    def score(counts):
        tp, fp, fn = counts[:, 0], counts[:, 1], counts[:, 2]
        p = np.divide(tp, tp + fp, out=np.ones_like(tp, dtype=float), where=(tp + fp) != 0)
        r = np.divide(tp, tp + fn, out=np.ones_like(tp, dtype=float), where=(tp + fn) != 0)
        f = np.divide(2 * p * r, p + r, out=np.zeros_like(p), where=(p + r) != 0)
        return float(np.mean(f))

    output = []
    rng = np.random.default_rng(260930)
    for dataset in ("flights", "assets", "hospital", "beers"):
        keys = [key for key in clusters if key[0] == dataset]
        data = {method: np.stack([clusters[key][method] for key in keys]) for method in ("rqdp", "rqdp_anytime", "ec2")}
        observed = {method: score(arr.sum(axis=0)) for method, arr in data.items()}
        draws = {method: [] for method in data}
        for _ in range(reps):
            idx = rng.integers(0, len(keys), len(keys))
            for method, arr in data.items():
                draws[method].append(score(arr[idx].sum(axis=0)))
        diff = np.asarray(draws["rqdp_anytime"]) - np.asarray(draws["rqdp"])
        output.append({
            "dataset": dataset,
            "independent_batches": len(keys),
            "rqdp_area": round(observed["rqdp"], 3),
            "rqdp_a_area": round(observed["rqdp_anytime"], 3),
            "ec2_area": round(observed["ec2"], 3),
            "rqdp_a_minus_rqdp": round(observed["rqdp_anytime"] - observed["rqdp"], 3),
            "paired_bootstrap_95_ci": [round(float(x), 3) for x in np.quantile(diff, (0.025, 0.975))],
        })
    return output


def synthetic_boundary():
    rows = load_jsonl(ARCHIVE / "synthetic.jsonl")
    output = []
    for size in (8, 16, 24, 32):
        for queries in (2, 3, 4):
            for method in ("static", "rqdp"):
                part = [r for r in rows if r["size"] == size and r["queries"] == queries and r["method"] == method]
                output.append({
                    "size": size,
                    "queries": queries,
                    "method": method,
                    "runs": len(part),
                    "completion_rate": round(sum(r["status"] == "complete" for r in part) / len(part), 3),
                    "median_states_completed": round(statistics.median(r["states"] for r in part if r["status"] == "complete"), 1) if any(r["status"] == "complete" for r in part) else None,
                })
    return output


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    results = {
        "dataset_profile": dataset_profile(),
        "paired_sensitivity": paired_sensitivity(),
        "original_speedup_bootstrap": original_speedup_bootstrap(),
        "quality_bootstrap": quality_bootstrap(),
        "synthetic_boundary": synthetic_boundary(),
    }
    (OUT / "analysis_v26.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    for name, rows in results.items():
        write_csv(OUT / f"{name}.csv", rows)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
