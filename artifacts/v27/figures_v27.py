"""Replace bar/heatmap experiment panels with print-safe line graphics."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = Path(os.environ["RQDP_REPO"]) if os.environ.get("RQDP_REPO") else (
    ROOT if (ROOT / "src" / "workloads.py").exists() else ROOT / "5实验代码" / "可信查询冲突治理_V16"
)
V16 = REPO / "results" / "v16"
SOURCE = REPO / "artifacts" / "figures" / "experiment" / "source_data"
V27 = json.loads((HERE / "results" / "analysis_v27.json").read_text(encoding="utf-8"))
V26 = json.loads((HERE / "results" / "analysis_v26.json").read_text(encoding="utf-8"))
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

INK = "#24292d"
MID = "#606c74"
LIGHT = "#9aa6ad"
PALE = "#c6cdd1"
GRID = "#e4e8ea"
DATASETS = ("flights", "assets", "hospital", "beers")
LABELS = ("Flights", "UniAssets", "Hospital", "Beers")
PALETTE = (INK, MID, LIGHT, "#7f878a", PALE)
MARKERS = ("o", "s", "^", "D", "v")
LINES = ("-", "--", "-.", ":", "-")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9,
    "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5, "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK,
})


def style(ax, axis="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=axis, color=GRID, linewidth=0.55)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, width=0.7)


def save(fig, number):
    for ext in ("pdf", "png", "svg"):
        fig.savefig(OUT / f"Fig{number}.{ext}", dpi=320 if ext == "png" else None,
                    bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def figure5():
    rows = json.loads((V16 / "efficiency_summary.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.75), constrained_layout=True)
    methods = ("identity", "static", "residual", "rqdp")
    labels = ("Record DP", "Static", "Residual", "RQDP")
    for di, dataset in enumerate(DATASETS):
        part = [next(r for r in rows if r["dataset"] == dataset and r["size"] == 8 and r["method"] == method)
                for method in methods]
        for ax, key, ylabel in zip(axes, ("median_ms", "mean_states"),
                                   ("Median planning time (ms)", "Mean expanded states")):
            ax.plot(range(4), [r[key] for r in part], color=PALETTE[di], marker=MARKERS[di],
                    linestyle=LINES[di], markersize=4, linewidth=1.35, label=LABELS[di])
            ax.set_ylabel(ylabel)
    for ax in axes:
        ax.set_xticks(range(4), labels, rotation=25, ha="right")
        ax.set_yscale("log")
        style(ax)
    axes[0].set_title("(a) Planning time", loc="left", fontweight="bold")
    axes[1].set_title("(b) Search states", loc="left", fontweight="bold")
    axes[0].legend(frameon=False, loc="upper right", ncol=2)
    save(fig, 5)


def figure7():
    rows = V27["quality_summary"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), constrained_layout=True)
    methods = ("EC2", "PAIRS", "RQDP", "RQDP-A")
    for mi, method in enumerate(methods):
        part = [next(r for r in rows if r["dataset"] == dataset and r["method"] == method)
                for dataset in DATASETS]
        for ax, key in zip(axes, ("f1_cost_auc", "mean_reference_cost")):
            ax.plot(range(4), [r[key] for r in part], color=PALETTE[mi],
                    linestyle=LINES[mi], marker=MARKERS[mi], linewidth=1.25,
                    markersize=3.8, label=method)
    axes[0].set_ylabel("F1-cost area")
    axes[0].set_ylim(0.3, 0.9)
    axes[0].set_title("(a) Quality through verification", loc="left", fontweight="bold")
    axes[1].set_ylabel("Mean reference-path cost")
    axes[1].set_title("(b) Cost on reference feedback", loc="left", fontweight="bold")
    for ax in axes:
        ax.set_xticks(range(4), LABELS, rotation=20, ha="right")
        style(ax)
    axes[0].legend(frameon=False, ncol=2, loc="lower left")
    save(fig, 7)


def figure8():
    rows = [r for r in read_csv(SOURCE / "Fig8_controlled_scaling.csv") if r["panel"] == "heatmap"]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.5), sharex=True, sharey=True, constrained_layout=True)
    for ax, size, letter in zip(axes.flat, (16, 24, 32, 48), "abcd"):
        part = sorted((r for r in rows if int(r["size"]) == size),
                      key=lambda r: int(r["retired_dimensions"]))
        x = [int(r["retired_dimensions"]) for r in part]
        y = [float(r["median_speedup"]) for r in part]
        ax.plot(x, y, color=INK, marker="o", linewidth=1.35, markersize=3.8)
        for xx, yy, row in zip(x, y, part):
            if float(row["censored_fraction"]) >= 0.5:
                ax.plot(xx, yy, marker="o", markerfacecolor="white", markeredgecolor=INK,
                        markersize=5.2, linestyle="None")
        ax.axhline(1, color=PALE, linewidth=0.8)
        ax.set_yscale("log")
        ax.set_xticks((0, 1, 2, 3))
        ax.set_title(f"({letter}) {size} records", loc="left", fontweight="bold")
        style(ax)
    for ax in axes[1]:
        ax.set_xlabel("Resolved query dimensions")
    for ax in axes[:, 0]:
        ax.set_ylabel("Static / RQDP time")
    save(fig, 8)


def figure9():
    rows = read_csv(SOURCE / "Fig9_task_level_analysis.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85), constrained_layout=True)
    for di, dataset in enumerate(DATASETS):
        subset = [r for r in rows if r["dataset"] == dataset]
        speeds = np.sort([float(r["time_speedup"]) for r in subset])
        if not len(speeds):
            continue
        axes[0].plot(speeds, np.arange(1, len(speeds) + 1) / len(speeds),
                     color=PALETTE[di], linestyle=LINES[di], linewidth=1.35, label=LABELS[di])
        ordered = sorted(subset, key=lambda r: float(r["state_reduction"]))
        bins = np.array_split(ordered, 4)
        xx = [float(np.median([float(r["state_reduction"]) for r in b])) for b in bins]
        yy = [float(np.median([float(r["time_speedup"]) for r in b])) for b in bins]
        axes[1].plot(xx, yy, color=PALETTE[di], linestyle=LINES[di], marker=MARKERS[di],
                     markersize=3.5, linewidth=1.25, label=LABELS[di])
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Record DP / RQDP time")
    axes[0].set_ylabel("Fraction of workloads at or below")
    axes[0].set_title("(a) Speedup distribution", loc="left", fontweight="bold")
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Reduction in expanded states")
    axes[1].set_ylabel("Median planning speedup")
    axes[1].set_title("(b) State-reduction quartiles", loc="left", fontweight="bold")
    for ax in axes:
        style(ax)
    axes[0].legend(frameon=False, loc="lower right", ncol=2)
    save(fig, 9)


def figure10():
    fig, ax = plt.subplots(figsize=(7.2, 2.75), constrained_layout=True)
    for di, dataset in enumerate(DATASETS):
        raw = json.loads((REPO / "data" / f"{dataset}_predicates.json").read_text(encoding="utf-8"))
        lengths = np.array([len(r["domain"]) for c in raw["collections"] for r in c["records"]])
        x = np.arange(1, max(8, int(lengths.max())) + 1)
        y = [100 * np.mean(lengths <= k) for k in x]
        ax.step(x, y, where="post", color=PALETTE[di], linewidth=1.45,
                linestyle=LINES[di], label=LABELS[di])
        ax.plot(x, y, color=PALETTE[di], marker=MARKERS[di], linestyle="None", markersize=3)
    ax.set_xlabel("Candidate vectors per record")
    ax.set_ylabel("Cumulative share of records (%)")
    ax.set_ylim(0, 103)
    ax.set_xticks(range(1, 9))
    ax.legend(frameon=False, ncol=4, loc="lower right")
    style(ax)
    save(fig, 10)


def figure13():
    rows = V26["synthetic_boundary"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True, constrained_layout=True)
    for ax, method, title in zip(axes, ("static", "rqdp"), ("(a) Static grouping", "(b) RQDP")):
        for qi, query_count in enumerate((2, 3, 4)):
            part = sorted((r for r in rows if r["method"] == method and r["queries"] == query_count),
                          key=lambda r: r["size"])
            ax.plot([r["size"] for r in part], [r["completion_rate"] for r in part],
                    color=PALETTE[qi], marker=MARKERS[qi], linestyle=LINES[qi],
                    linewidth=1.35, markersize=4, label=f"{query_count} queries")
        ax.set_xlabel("Records per task")
        ax.set_xticks((8, 16, 24, 32))
        ax.set_ylim(0, 1.05)
        ax.set_title(title, loc="left", fontweight="bold")
        style(ax)
    axes[0].set_ylabel("Completed within limit")
    axes[0].legend(frameon=False, loc="lower left")
    save(fig, 13)


def figure14():
    curves = read_csv(HERE / "results" / "quality_curves_v27.csv")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.45), sharex=True, sharey=True, constrained_layout=True)
    methods = ("EC2", "RQDP", "RQDP-A", "RBG")
    for ax, dataset, name, letter in zip(axes.flat, DATASETS, LABELS, "abcd"):
        for mi, method in enumerate(methods):
            part = sorted((r for r in curves if r["dataset"] == dataset and r["method"] == method),
                          key=lambda r: int(r["budget"]))
            ax.plot([int(r["budget"]) / 4 for r in part], [float(r["f1"]) for r in part],
                    color=PALETTE[mi], linestyle=LINES[mi], marker=MARKERS[mi],
                    linewidth=1.2, markersize=3.2, label=method)
        ax.set_title(f"({letter}) {name}", loc="left", fontweight="bold")
        ax.set_ylim(0, 1.03)
        ax.set_xticks((0, 0.25, 0.5, 0.75, 1))
        style(ax)
    axes[0, 0].legend(frameon=False, loc="lower right", ncol=2)
    for ax in axes[1]:
        ax.set_xlabel("Fraction of full inspection cost")
    for ax in axes[:, 0]:
        ax.set_ylabel("Query-output F1")
    save(fig, 14)


def figure15():
    rows = V27["scaling_summary"]
    x = [row["size"] for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85), constrained_layout=True)
    for mi, (label, key) in enumerate((("RBG", "median_rbg_first_action_ms"),
                                        ("RQDP, completed", "median_rqdp_first_action_ms_completed"))):
        axes[0].plot(x, [row[key] for row in rows], color=PALETTE[mi], marker=MARKERS[mi],
                     linestyle=LINES[mi], linewidth=1.4, markersize=4, label=label)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Median first-action time (ms)")
    axes[0].set_title("(a) Planning time", loc="left", fontweight="bold")
    for mi, (label, key) in enumerate((("RBG", "rbg_completion_rate"),
                                        ("RQDP", "rqdp_completion_rate"))):
        axes[1].plot(x, [row[key] for row in rows], color=PALETTE[mi], marker=MARKERS[mi],
                     linestyle=LINES[mi], linewidth=1.4, markersize=4, label=label)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel("Completed within 2 s")
    axes[1].set_title("(b) Returned a first action", loc="left", fontweight="bold")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xlabel("Records per batch")
        style(ax)
    axes[0].legend(frameon=False, loc="upper left")
    axes[1].legend(frameon=False, loc="lower left")
    save(fig, 15)


def figure16():
    raw = [json.loads(line) for line in (HERE / "results" / "rbg_scaling.jsonl").read_text(encoding="utf-8").splitlines()]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85), constrained_layout=True)
    for mi, (label, dataset) in enumerate((("All datasets", None), ("Flights", "flights"))):
        xx, yy = [], []
        for radius in (0, 1, 2):
            part = [r for r in raw if r["size"] == 8 and r["radius"] == radius and
                    (dataset is None or r["dataset"] == dataset)]
            xx.append(radius)
            yy.append(100 * sum(r["rbg_worst_cost"] == r["rqdp_worst_cost"] for r in part) / len(part))
        axes[0].plot(xx, yy, color=PALETTE[mi], marker=MARKERS[mi], linestyle=LINES[mi],
                     linewidth=1.35, markersize=4, label=label)
    axes[0].set_xticks((0, 1, 2))
    axes[0].set_ylim(0, 103)
    axes[0].set_xlabel("Omission allowance r")
    axes[0].set_ylabel("RBG matches optimal worst cost (%)")
    axes[0].set_title("(a) Small-task cost", loc="left", fontweight="bold")
    axes[0].legend(frameon=False, loc="lower left")
    intervals = V27["scaling_intervals"]
    x = [row["size"] for row in intervals]
    low = [100 * row["mean_normalized_reference_gap_95_interval"][0] for row in intervals]
    mid = [100 * row["mean_normalized_reference_gap_95_interval"][1] for row in intervals]
    high = [100 * row["mean_normalized_reference_gap_95_interval"][2] for row in intervals]
    axes[1].plot(x, mid, color=INK, marker="o", linewidth=1.35, markersize=4)
    axes[1].fill_between(x, low, high, color=PALE, alpha=0.45, linewidth=0)
    axes[1].axhline(0, color=MID, linewidth=0.7)
    axes[1].set_xticks(x)
    axes[1].set_xlabel("Records per batch")
    axes[1].set_ylabel("RBG relative reference-cost gap (%)")
    axes[1].set_title("(b) Paired completed tasks", loc="left", fontweight="bold")
    for ax in axes:
        style(ax)
    save(fig, 16)


if __name__ == "__main__":
    for function in (figure5, figure7, figure8, figure9, figure10,
                     figure13, figure14, figure15, figure16):
        function()
    print(f"Created 9 line-based figures in {OUT}")
