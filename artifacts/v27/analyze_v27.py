"""Aggregate the pre-specified RBG comparison without dropping timed-out tasks."""

from __future__ import annotations

import csv
import json
import os
import random
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = Path(os.environ["RQDP_REPO"]) if os.environ.get("RQDP_REPO") else (
    ROOT if (ROOT / "src" / "workloads.py").exists() else ROOT / "5实验代码" / "可信查询冲突治理_V16"
)
OUT = HERE / "results"
V16 = REPO / "results" / "v16"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def csv_out(name, rows):
    if not rows:
        return
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def batch_key(row):
    return row["dataset"], row["kind"], row["size"], row["group"]


def percentile_interval(values):
    return [round(float(v), 4) for v in np.quantile(values, [0.025, 0.5, 0.975])]


def bootstrap_by_batch(rows, metric, seed, replicates=1500):
    batches = defaultdict(list)
    for row in rows:
        batches[batch_key(row)].append(row)
    keys = sorted(batches)
    rng = random.Random(seed)
    samples = []
    for _ in range(replicates):
        draw = [row for key in rng.choices(keys, k=len(keys)) for row in batches[key]]
        samples.append(metric(draw))
    return percentile_interval(samples)


def main():
    rows = read_jsonl(OUT / "rbg_scaling.jsonl")
    new_quality = json.loads((OUT / "rbg_quality_summary.json").read_text(encoding="utf-8"))
    old_quality = json.loads((V16 / "quality_summary.json").read_text(encoding="utf-8"))
    methods = ("ec2", "pairs", "rqdp", "rqdp_anytime", "rbg")
    curves = []
    quality_table = []
    for row in old_quality + new_quality:
        if row["method"] not in methods:
            continue
        method = "RQDP-A" if row["method"] == "rqdp_anytime" else row["method"].upper()
        quality_table.append({"dataset": row["dataset"], "method": method,
                              "workloads": row["workloads"], "f1_cost_auc": row["f1_cost_auc"],
                              "mean_reference_cost": row["mean_reference_cost"],
                              "mean_worst_cost": row["mean_worst_cost"]})
        for point in row["curve"]:
            curves.append({"dataset": row["dataset"], "method": method,
                           "budget": point["budget"], "f1": point["f1"],
                           "coverage": point["coverage"]})

    scaling = []
    intervals = []
    for size in (8, 16, 24, 32):
        part = [row for row in rows if row["size"] == size]
        completed = [row for row in part if row["rqdp_status"] == "complete"]
        valid = [row for row in completed if row["reference_valid"]]
        ratios = [row["rqdp_plan_seconds"] / row["rbg_plan_seconds"] for row in completed]
        normalized_gaps = [
            (row["rbg_reference_cost"] - row["rqdp_reference_cost"])
            / max(1.0, row["rqdp_reference_cost"])
            for row in valid
        ]
        summary = {
            "size": size, "tasks": len(part), "exact_completed": len(completed),
            "rqdp_completion_rate": len(completed) / len(part), "rbg_completion_rate": 1.0,
            "median_rbg_first_action_ms": statistics.median(row["rbg_plan_seconds"] for row in part) * 1000,
            "median_rqdp_first_action_ms_completed": statistics.median(row["rqdp_plan_seconds"] for row in completed) * 1000,
            "median_paired_speedup_completed": statistics.median(ratios),
            "mean_ref_cost_difference_completed": statistics.fmean(row["rbg_reference_cost"] - row["rqdp_reference_cost"] for row in valid),
            "mean_normalized_ref_gap_completed": statistics.fmean(normalized_gaps),
            "paired_valid_paths": len(valid),
            "equal_reference_paths": sum(row["rbg_reference_cost"] == row["rqdp_reference_cost"] for row in valid),
        }
        if size == 8:
            summary.update(rbg_optimal_worst_count=sum(row["rbg_worst_cost"] == row["rqdp_worst_cost"] for row in completed),
                           mean_worst_excess=statistics.fmean(row["rbg_worst_cost"] - row["rqdp_worst_cost"] for row in completed),
                           max_worst_excess=max(row["rbg_worst_cost"] - row["rqdp_worst_cost"] for row in completed))
        scaling.append(summary)
        intervals.append({
            "size": size,
            "paired_speedup_95_interval": bootstrap_by_batch(
                completed, lambda sample: statistics.median(row["rqdp_plan_seconds"] / row["rbg_plan_seconds"] for row in sample), 9270 + size),
            "mean_normalized_reference_gap_95_interval": bootstrap_by_batch(
                valid, lambda sample: statistics.fmean(
                    (row["rbg_reference_cost"] - row["rqdp_reference_cost"])
                    / max(1.0, row["rqdp_reference_cost"])
                    for row in sample), 1190 + size),
        })

    dataset_completion = []
    for size in (8, 16, 24, 32):
        for dataset in ("flights", "assets", "hospital", "beers"):
            part = [row for row in rows if row["size"] == size and row["dataset"] == dataset]
            dataset_completion.append({"size": size, "dataset": dataset, "tasks": len(part),
                                       "rbg_complete": len(part),
                                       "rqdp_complete": sum(row["rqdp_status"] == "complete" for row in part)})

    timing = read_jsonl(OUT / "rbg_rotated_timing.jsonl")
    timing_pairs = defaultdict(dict)
    for row in timing:
        timing_pairs[(row["size"], row["dataset"], row["kind"], row["group"], row["repeat"])][row["method"]] = row
    rotated_timing = []
    for size in (8, 16):
        for order in ("all", "rbg/rqdp", "rqdp/rbg"):
            pairs = [pair for key, pair in timing_pairs.items() if key[0] == size and
                     (order == "all" or pair["rbg"]["order"] == order)]
            completed = [pair for pair in pairs if pair["rqdp"]["status"] == "complete"]
            rotated_timing.append({"size": size, "order": order, "pairs": len(pairs),
                                   "rqdp_completed": len(completed),
                                   "median_paired_speedup": statistics.median(
                                       pair["rqdp"]["seconds"] / pair["rbg"]["seconds"] for pair in completed)})

    result = {
        "new_quality_workloads": sum(row["workloads"] for row in new_quality),
        "scaling_condition_runs": len(rows),
        "rbg_reference_paths_checked": sum(row["reference_valid"] for row in rows),
        "exact_completed": sum(row["rqdp_status"] == "complete" for row in rows),
        "quality_summary": quality_table,
        "scaling_summary": scaling,
        "scaling_intervals": intervals,
        "dataset_completion": dataset_completion,
        "rotated_timing": rotated_timing,
    }
    (OUT / "analysis_v27.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    csv_out("quality_comparison_v27.csv", quality_table)
    csv_out("quality_curves_v27.csv", curves)
    csv_out("scaling_summary_v27.csv", scaling)
    csv_out("dataset_completion_v27.csv", dataset_completion)
    csv_out("rotated_timing_v27.csv", rotated_timing)
    print(json.dumps({k: result[k] for k in ("new_quality_workloads", "scaling_condition_runs", "rbg_reference_paths_checked", "exact_completed", "scaling_summary", "scaling_intervals")}, indent=2))


if __name__ == "__main__":
    main()
