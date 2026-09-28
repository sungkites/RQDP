"""Create manuscript figures and their source-data tables."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle, Polygon


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "v16"
FIGURE_ROOT = Path(os.environ.get("RQDP_FIGURE_ROOT", ROOT / "artifacts" / "figures"))
METHOD_DIR = FIGURE_ROOT / "method"
EXP_DIR = FIGURE_ROOT / "experiment"
SOURCE_DIR = EXP_DIR / "source_data"
for directory in (METHOD_DIR, EXP_DIR, SOURCE_DIR):
    directory.mkdir(parents=True, exist_ok=True)


COLORS = {
    "blue": "#557A95",
    "orange": "#C17C54",
    "green": "#6E8B74",
    "slate": "#6B7280",
    "light_blue": "#DCE7EC",
    "light_green": "#E0E9E1",
    "light_orange": "#EEE2D8",
    "light_gray": "#ECEDEF",
    "ink": "#263238",
    "grid": "#D6D9DC",
}


def style():
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 9,
            "axes.linewidth": 0.7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "lines.linewidth": 1.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def save(fig, directory, stem):
    for suffix in ("pdf", "svg", "png"):
        fig.savefig(
            directory / f"{stem}.{suffix}",
            dpi=600 if suffix in {"png", "tiff"} else None,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


def box(ax, xy, width, height, title, subtitle, face, edge=None):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.018,rounding_size=0.018",
        linewidth=0.9,
        edgecolor=edge or COLORS["slate"],
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height * 0.62, title, ha="center", va="center", weight="semibold", color=COLORS["ink"], fontsize=8.3)
    ax.text(x + width / 2, y + height * 0.30, subtitle, ha="center", va="center", color=COLORS["slate"], fontsize=6.8)
    return patch


def arrow(ax, start, end, color=None, connectionstyle="arc3"):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color=color or COLORS["slate"],
            connectionstyle=connectionstyle,
        )
    )


def method_pipeline():
    style()
    fig, ax = plt.subplots(figsize=(7.2, 3.25))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.1)
    ax.axis("off")

    xs = [0.35, 2.78, 5.21, 7.64]
    titles = ["Candidate states", "Residual queries", "Type reduction", "Adaptive plan"]
    subtitles = ["values & costs", "retire certified", "merge signatures", "minimax + anytime"]
    faces = [COLORS["light_gray"], COLORS["light_blue"], COLORS["light_green"], COLORS["light_orange"]]
    for x, title, subtitle, face in zip(xs, titles, subtitles, faces):
        box(ax, (x, 3.55), 1.85, 0.85, title, subtitle, face)
    for left, right in zip(xs[:-1], xs[1:]):
        arrow(ax, (left + 1.85, 3.98), (right - 0.08, 3.98))

    # Candidate records and query chips.
    for row, y in enumerate([2.63, 2.17, 1.71]):
        ax.add_patch(FancyBboxPatch((0.48, y), 1.46, 0.30, boxstyle="round,pad=0.01", facecolor="white", edgecolor=COLORS["slate"], linewidth=0.7))
        ax.text(0.62, y + 0.15, f"r{row+1}", va="center", fontsize=7, color=COLORS["ink"])
        for col in range(3):
            fill = COLORS["blue"] if (row + col) % 2 else "white"
            ax.add_patch(Circle((1.15 + col * 0.27, y + 0.15), 0.065, facecolor=fill, edgecolor=COLORS["blue"], linewidth=0.6))
    ax.text(1.21, 1.35, "record candidates", ha="center", fontsize=6.8, color=COLORS["slate"])

    # Projection panel: query chips, with one retired.
    for j, (label, fill, alpha) in enumerate([("q1", COLORS["light_gray"], 0.55), ("q2", COLORS["light_blue"], 1), ("q3", COLORS["light_blue"], 1)]):
        x = 3.05 + j * 0.55
        ax.add_patch(FancyBboxPatch((x, 2.30), 0.44, 0.36, boxstyle="round,pad=0.02", facecolor=fill, edgecolor=COLORS["slate"], linewidth=0.7, alpha=alpha))
        ax.text(x + 0.22, 2.48, label, ha="center", va="center", fontsize=7, alpha=alpha)
    ax.plot([3.07, 3.45], [2.66, 2.30], color=COLORS["slate"], linewidth=0.8)
    ax.plot([3.07, 3.45], [2.30, 2.66], color=COLORS["slate"], linewidth=0.8)
    ax.text(3.79, 1.85, "q1 certified", ha="center", fontsize=6.8, color=COLORS["slate"])
    arrow(ax, (3.78, 1.64), (3.78, 1.28))
    ax.text(3.78, 1.05, "rebuild types", ha="center", fontsize=7.1, weight="semibold", color=COLORS["ink"])

    # Dominance panel: two feedback branches converge to the larger allowed set.
    root = (6.13, 2.67)
    ax.add_patch(Circle(root, 0.12, facecolor=COLORS["green"], edgecolor=COLORS["ink"], linewidth=0.7))
    children = [(5.62, 1.92), (6.13, 1.92), (6.64, 1.92)]
    for child in children:
        arrow(ax, (root[0], root[1] - 0.13), (child[0], child[1] + 0.12))
        ax.add_patch(Circle(child, 0.11, facecolor="white", edgecolor=COLORS["green"], linewidth=0.8))
    ax.plot([6.54, 6.74], [1.82, 2.02], color=COLORS["orange"], linewidth=1.2)
    ax.plot([6.54, 6.74], [2.02, 1.82], color=COLORS["orange"], linewidth=1.2)
    ax.text(6.14, 1.38, "one dominated branch removed", ha="center", fontsize=6.8, color=COLORS["slate"])

    # Decision panel: short policy tree and feedback loop.
    nodes = [(8.58, 2.72), (8.16, 2.08), (9.00, 2.08), (7.95, 1.48), (8.37, 1.48), (8.79, 1.48), (9.21, 1.48)]
    for i, point in enumerate(nodes):
        if i:
            parent = nodes[(i - 1) // 2]
            ax.plot([parent[0], point[0]], [parent[1] - 0.08, point[1] + 0.08], color=COLORS["slate"], linewidth=0.7)
        ax.add_patch(Circle(point, 0.095 if i < 3 else 0.075, facecolor=COLORS["orange"] if i == 0 else "white", edgecolor=COLORS["orange"], linewidth=0.8))
    ax.text(8.58, 1.08, "verify selected record", ha="center", fontsize=7.1, weight="semibold", color=COLORS["ink"])

    # Bottom feedback loop.
    box(ax, (3.45, 0.12), 3.10, 0.55, "Evidence update", "filter states & certify queries", "white", COLORS["blue"])
    arrow(ax, (8.58, 0.98), (6.60, 0.46), COLORS["blue"], "arc3,rad=-0.18")
    arrow(ax, (3.40, 0.46), (2.03, 1.66), COLORS["blue"], "arc3,rad=-0.24")
    ax.text(7.63, 0.43, "feedback", color=COLORS["blue"], fontsize=6.8)
    ax.text(2.34, 0.74, "repeat until certified", color=COLORS["blue"], fontsize=6.8)
    save(fig, METHOD_DIR, "Fig1_RQDP_pipeline")


def compression_example():
    style()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.65), gridspec_kw={"wspace": 0.24})
    panel_titles = ["a  Initial state", "b  Residual quotient", "c  Feedback dominance"]
    for ax, title in zip(axes, panel_titles):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(title, loc="left", weight="semibold", pad=5)

    ax = axes[0]
    ax.text(0.04, 0.88, "record", color=COLORS["slate"], fontsize=6.7)
    ax.text(0.46, 0.88, "q1", color=COLORS["slate"], fontsize=6.7)
    ax.text(0.65, 0.88, "q2", color=COLORS["slate"], fontsize=6.7)
    for i, (bits, face) in enumerate([((0, 1), COLORS["light_blue"]), ((1, 1), COLORS["light_blue"]), ((0, 0), COLORS["light_green"]), ((1, 0), COLORS["light_green"])]):
        y = 0.72 - i * 0.16
        ax.add_patch(FancyBboxPatch((0.03, y - 0.06), 0.86, 0.12, boxstyle="round,pad=0.01", facecolor=face, edgecolor=COLORS["slate"], linewidth=0.6))
        ax.text(0.12, y, f"r{i+1}", va="center", fontsize=7)
        ax.text(0.49, y, str(bits[0]), ha="center", va="center", fontsize=7)
        ax.text(0.68, y, str(bits[1]), ha="center", va="center", fontsize=7)
    ax.text(0.46, 0.10, "4 initial types", ha="center", fontsize=7.2, weight="semibold", color=COLORS["ink"])

    ax = axes[1]
    ax.text(0.50, 0.86, "q1 is already fixed", ha="center", fontsize=7, color=COLORS["slate"])
    ax.plot([0.36, 0.64], [0.89, 0.80], color=COLORS["slate"], linewidth=0.8)
    ax.plot([0.36, 0.64], [0.80, 0.89], color=COLORS["slate"], linewidth=0.8)
    for i, (count, bit, face) in enumerate([(2, 1, COLORS["light_blue"]), (2, 0, COLORS["light_green"])]):
        y = 0.60 - i * 0.25
        ax.add_patch(FancyBboxPatch((0.13, y - 0.09), 0.74, 0.18, boxstyle="round,pad=0.015", facecolor=face, edgecolor=COLORS["slate"], linewidth=0.7))
        ax.text(0.26, y, f"×{count}", va="center", fontsize=8, weight="semibold")
        ax.text(0.57, y, f"q2={bit}", va="center", fontsize=7.5)
    ax.text(0.50, 0.10, "2 residual types", ha="center", fontsize=7.2, weight="semibold", color=COLORS["ink"])

    ax = axes[2]
    ax.add_patch(Circle((0.22, 0.70), 0.07, facecolor=COLORS["light_orange"], edgecolor=COLORS["orange"], linewidth=0.8))
    ax.text(0.22, 0.70, "a", ha="center", va="center", fontsize=7)
    for y, label, radius in [(0.50, "in", "r"), (0.26, "out", "r−1")]:
        arrow(ax, (0.29, 0.68), (0.55, y + 0.02))
        ax.add_patch(FancyBboxPatch((0.57, y - 0.07), 0.30, 0.14, boxstyle="round,pad=0.01", facecolor="white", edgecolor=COLORS["slate"], linewidth=0.7))
        ax.text(0.72, y, f"{label}; {radius}", ha="center", va="center", fontsize=6.8)
    ax.plot([0.58, 0.86], [0.19, 0.33], color=COLORS["orange"], linewidth=1.1)
    ax.plot([0.58, 0.86], [0.33, 0.19], color=COLORS["orange"], linewidth=1.1)
    ax.text(0.50, 0.10, "keep the larger allowed set", ha="center", fontsize=7.2, weight="semibold", color=COLORS["ink"])
    save(fig, METHOD_DIR, "Fig2_residual_compression")


def policy_recursion():
    """Illustrate minimax recursion, lexicographic tie-breaking, and execution."""
    style()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.65), gridspec_kw={"wspace": 0.22})
    titles = ["a  Worst-case recursion", "b  RQDP-A tie-break", "c  Evidence-preserving execution"]
    for ax, title in zip(axes, titles):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(title, loc="left", weight="semibold", pad=5)

    # Panel a: the adversarial branch fixes the value of each action.
    ax = axes[0]
    ax.add_patch(Circle((0.50, 0.84), 0.065, facecolor=COLORS["light_gray"], edgecolor=COLORS["slate"], linewidth=0.8))
    ax.text(0.50, 0.84, "s", ha="center", va="center", fontsize=7.5, weight="semibold")
    actions = [(0.25, "t1", "7"), (0.75, "t2", "8")]
    for x, label, value in actions:
        arrow(ax, (0.47 if x < 0.5 else 0.53, 0.79), (x, 0.68))
        ax.add_patch(FancyBboxPatch((x - 0.10, 0.58), 0.20, 0.11, boxstyle="round,pad=0.01", facecolor="white", edgecolor=COLORS["blue"], linewidth=0.8))
        ax.text(x, 0.635, label, ha="center", va="center", fontsize=7)
        for dx, cost in [(-0.10, int(value) - 1), (0.10, int(value))]:
            arrow(ax, (x, 0.57), (x + dx, 0.40))
            ax.add_patch(Circle((x + dx, 0.34), 0.052, facecolor=COLORS["light_blue"], edgecolor=COLORS["blue"], linewidth=0.7))
            ax.text(x + dx, 0.34, str(cost), ha="center", va="center", fontsize=6.5)
        ax.text(x, 0.18, f"max = {value}", ha="center", fontsize=7, color=COLORS["slate"])
    ax.text(0.50, 0.06, "choose t1", ha="center", fontsize=7.4, weight="semibold", color=COLORS["ink"])

    # Panel b: same primary value, smaller unresolved-query area wins.
    ax = axes[1]
    ax.text(0.50, 0.84, "pair = (primary cost, unresolved area)", ha="center", fontsize=6.5, color=COLORS["slate"])
    for y, label, pair, face in [
        (0.63, "t1", "(7, 19)", COLORS["light_gray"]),
        (0.38, "t2", "(7, 15)", COLORS["light_orange"]),
    ]:
        ax.add_patch(FancyBboxPatch((0.14, y - 0.08), 0.72, 0.16, boxstyle="round,pad=0.015", facecolor=face, edgecolor=COLORS["slate"], linewidth=0.8))
        ax.text(0.25, y, label, ha="center", va="center", fontsize=7.2, weight="semibold")
        ax.text(0.62, y, pair, ha="center", va="center", fontsize=8)
    ax.text(0.50, 0.18, "same 7; select smaller area 15", ha="center", fontsize=6.9, color=COLORS["slate"])
    arrow(ax, (0.50, 0.14), (0.50, 0.05), COLORS["orange"])
    ax.text(0.50, 0.01, "select t2", ha="center", fontsize=7.4, weight="semibold", color=COLORS["ink"])

    # Panel c: planning types are compressed, evidence remains record-specific.
    ax = axes[2]
    steps = [
        (0.72, "selected type", COLORS["light_green"]),
        (0.50, "original record", COLORS["light_blue"]),
        (0.28, "full feedback", COLORS["light_orange"]),
        (0.06, "update evidence + r", COLORS["light_gray"]),
    ]
    for idx, (y, label, face) in enumerate(steps):
        ax.add_patch(FancyBboxPatch((0.16, y), 0.68, 0.13, boxstyle="round,pad=0.012", facecolor=face, edgecolor=COLORS["slate"], linewidth=0.75))
        ax.text(0.50, y + 0.065, label, ha="center", va="center", fontsize=7)
        if idx < len(steps) - 1:
            arrow(ax, (0.50, y - 0.01), (0.50, steps[idx + 1][0] + 0.15))
    save(fig, METHOD_DIR, "Fig3_policy_recursion")


def quality_figure():
    path = RESULTS / "quality_summary.json"
    if not path.exists():
        return
    rows = json.loads(path.read_text(encoding="utf-8"))
    keep = ["ec2", "pairs", "rqdp", "rqdp_anytime"]
    labels = {"ec2": "EC²", "pairs": "Pairs", "rqdp": "RQDP", "rqdp_anytime": "RQDP-A"}
    colors = {"ec2": COLORS["blue"], "pairs": COLORS["green"], "rqdp": COLORS["slate"], "rqdp_anytime": COLORS["orange"]}
    marks = {"ec2": "o", "pairs": "s", "rqdp": "^", "rqdp_anytime": "D"}
    datasets = ["flights", "assets", "hospital", "beers"]
    style()
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2), sharex=True, sharey=True)
    source = []
    for ax, dataset, letter in zip(axes.flat, datasets, "abcd"):
        for method in keep:
            row = next(item for item in rows if item["dataset"] == dataset and item["method"] == method)
            x = [point["budget"] / 4 for point in row["curve"]]
            y = [point["f1"] for point in row["curve"]]
            ax.plot(x, y, marker=marks[method], markersize=3.4, color=colors[method], label=labels[method])
            source.extend({"dataset": dataset, "method": method, "cost_fraction": xx, "f1": yy} for xx, yy in zip(x, y))
        ax.set_title(f"{letter}  {dataset.capitalize()}", loc="left", weight="semibold")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    for ax in axes[-1, :]:
        ax.set_xlabel("Verified-cost fraction")
    for ax in axes[:, 0]:
        ax.set_ylabel("Query-output F1")
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.52, 1.01))
    fig.subplots_adjust(top=0.90, left=0.09, right=0.98, bottom=0.10, hspace=0.28, wspace=0.15)
    with (SOURCE_DIR / "Fig6_quality_curves.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["dataset", "method", "cost_fraction", "f1"])
        writer.writeheader(); writer.writerows(source)
    save(fig, EXP_DIR, "Fig6_quality_cost_curves")


def efficiency_figure():
    path = RESULTS / "efficiency.jsonl"
    if not path.exists():
        return
    raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    task_runs = defaultdict(list)
    task_status = defaultdict(list)
    for row in raw:
        key = (row["dataset"], row["kind"], row["size"], row["group"], row["method"])
        task_runs[key].append(1000 * row["seconds"])
        task_status[key].append(row["status"] == "complete")
    dataset_rows = []
    grouped = defaultdict(list)
    for (dataset, kind, size, group, method), values in task_runs.items():
        grouped[(dataset, size, method)].append(
            (statistics_median(values), any(task_status[(dataset, kind, size, group, method)]))
        )
    for (dataset, size, method), values in grouped.items():
        dataset_rows.append(
            {
                "dataset": dataset,
                "size": size,
                "method": method,
                "median_ms": statistics_median([value for value, _ in values]),
                "completion_rate": sum(done for _, done in values) / len(values),
            }
        )
    methods = ["static", "residual", "rqdp", "rqdp_anytime"]
    labels = {"static": "Static", "residual": "Residual", "rqdp": "RQDP", "rqdp_anytime": "RQDP-A"}
    colors = {"static": COLORS["slate"], "residual": COLORS["blue"], "rqdp": COLORS["green"], "rqdp_anytime": COLORS["orange"]}
    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.75))
    source = []
    for method in methods:
        subset = [row for row in dataset_rows if row["method"] == method]
        by_size = defaultdict(list)
        by_completion = defaultdict(list)
        for row in subset:
            by_size[row["size"]].append(row["median_ms"])
            by_completion[row["size"]].append(row["completion_rate"])
        xs = sorted(by_completion)
        medians = [statistics_median(by_size[x]) if by_size[x] else math.nan for x in xs]
        completion = [sum(by_completion[x]) / len(by_completion[x]) for x in xs]
        axes[0].plot(xs, medians, marker="o", markersize=3.5, color=colors[method], label=labels[method])
        axes[1].plot(xs, completion, marker="o", markersize=3.5, color=colors[method], label=labels[method])
        source.extend({"method": method, "size": x, "median_ms_across_datasets": y, "mean_completion_rate": z} for x, y, z in zip(xs, medians, completion))
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Median planning time (ms)")
    axes[1].set_ylabel("Completion rate")
    axes[1].set_ylim(-0.02, 1.02)
    for letter, ax in zip("ab", axes):
        ax.set_title(f"{letter}  " + ("Planning time" if letter == "a" else "Solved within limit"), loc="left", weight="semibold")
        ax.set_xlabel("Records per workload")
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.52, 1.04))
    fig.subplots_adjust(top=0.82, left=0.10, right=0.98, bottom=0.18, wspace=0.30)
    with (SOURCE_DIR / "Fig4_efficiency_scaling.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["method", "size", "median_ms_across_datasets", "mean_completion_rate"])
        writer.writeheader(); writer.writerows(source)
    save(fig, EXP_DIR, "Fig4_efficiency_scaling")


def ablation_size8_figure():
    """Dataset-level size-eight comparison of time and expanded states."""
    path = RESULTS / "efficiency.jsonl"
    if not path.exists():
        return
    raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    methods = ["identity", "static", "residual", "rqdp"]
    datasets = ["flights", "assets", "hospital", "beers"]
    labels = {"identity": "Record DP", "static": "Static", "residual": "Residual", "rqdp": "RQDP"}
    colors = {"identity": COLORS["slate"], "static": COLORS["blue"], "residual": COLORS["orange"], "rqdp": COLORS["green"]}
    task_runs = defaultdict(list)
    task_states = defaultdict(list)
    for row in raw:
        if row["size"] != 8 or row["method"] not in methods:
            continue
        key = (row["dataset"], row["kind"], row["group"], row["method"])
        task_runs[key].append(1000 * row["seconds"])
        task_states[key].append(row["states"])
    summary = []
    for dataset in datasets:
        for method in methods:
            keys = [key for key in task_runs if key[0] == dataset and key[3] == method]
            per_task_time = [statistics_median(task_runs[key]) for key in keys]
            per_task_states = [statistics_median(task_states[key]) for key in keys]
            summary.append({
                "dataset": dataset,
                "method": method,
                "median_ms": statistics_median(per_task_time),
                "median_states": statistics_median(per_task_states),
                "tasks": len(keys),
            })

    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85))
    x = list(range(len(datasets)))
    offsets = [-0.27, -0.09, 0.09, 0.27]
    for method, offset in zip(methods, offsets):
        subset = [next(row for row in summary if row["dataset"] == dataset and row["method"] == method) for dataset in datasets]
        axes[0].scatter([value + offset for value in x], [row["median_ms"] for row in subset], s=26, marker="o", color=colors[method], label=labels[method], zorder=3)
        axes[1].scatter([value + offset for value in x], [row["median_states"] for row in subset], s=26, marker="o", color=colors[method], label=labels[method], zorder=3)
    for letter, ax, ylabel, title in [
        ("a", axes[0], "Median planning time (ms)", "Planning time"),
        ("b", axes[1], "Median expanded states", "Search states"),
    ]:
        ax.set_yscale("log")
        ax.set_xticks(x, [name.capitalize() for name in datasets])
        ax.set_ylabel(ylabel)
        ax.set_title(f"{letter}  {title}", loc="left", weight="semibold")
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.52, 1.03))
    fig.subplots_adjust(top=0.82, left=0.10, right=0.98, bottom=0.18, wspace=0.32)
    with (SOURCE_DIR / "Fig5_ablation_size8.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["dataset", "method", "median_ms", "median_states", "tasks"])
        writer.writeheader(); writer.writerows(summary)
    save(fig, EXP_DIR, "Fig5_ablation_size8")


def quality_summary_figure():
    """Summarize the partial-verification quality and observed path cost."""
    path = RESULTS / "quality_summary.json"
    if not path.exists():
        return
    rows = json.loads(path.read_text(encoding="utf-8"))
    methods = ["ec2", "pairs", "rqdp", "rqdp_anytime"]
    datasets = ["flights", "assets", "hospital", "beers"]
    labels = {"ec2": "EC²", "pairs": "Pairs", "rqdp": "RQDP", "rqdp_anytime": "RQDP-A"}
    colors = {"ec2": COLORS["blue"], "pairs": COLORS["green"], "rqdp": COLORS["slate"], "rqdp_anytime": COLORS["orange"]}
    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.95))
    x = list(range(len(datasets)))
    width = 0.18
    for idx, method in enumerate(methods):
        subset = [next(row for row in rows if row["dataset"] == dataset and row["method"] == method) for dataset in datasets]
        offset = (idx - 1.5) * width
        axes[0].bar([value + offset for value in x], [row["f1_cost_auc"] for row in subset], width=width, color=colors[method], label=labels[method])
        axes[1].scatter([value + offset for value in x], [row["mean_reference_cost"] for row in subset], marker=["o", "s", "^", "D"][idx], s=28, color=colors[method], label=labels[method], zorder=3)
    axes[0].set_ylim(0.30, 0.90)
    axes[0].set_ylabel("F1-cost area")
    axes[0].set_title("a  Quality over verification cost", loc="left", weight="semibold")
    axes[1].set_ylabel("Mean reference-path cost")
    axes[1].set_title("b  Cost on reference feedback", loc="left", weight="semibold")
    for ax in axes:
        ax.set_xticks(x, [name.capitalize() for name in datasets])
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.52, 1.03))
    fig.subplots_adjust(top=0.82, left=0.10, right=0.98, bottom=0.18, wspace=0.30)
    source = [
        {
            "dataset": row["dataset"],
            "method": row["method"],
            "f1_cost_area": row["f1_cost_auc"],
            "coverage_cost_area": row["coverage_cost_auc"],
            "mean_reference_cost": row["mean_reference_cost"],
        }
        for row in rows if row["method"] in methods
    ]
    with (SOURCE_DIR / "Fig7_quality_summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["dataset", "method", "f1_cost_area", "coverage_cost_area", "mean_reference_cost"])
        writer.writeheader(); writer.writerows(source)
    save(fig, EXP_DIR, "Fig7_quality_summary")


def statistics_median(values):
    values = sorted(values)
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def synthetic_figure():
    path = RESULTS / "structured.jsonl"
    if not path.exists():
        return
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    # RQDP speedup over static for matched runs.  A static timeout supplies a
    # conservative lower bound because its observed runtime stops at the limit.
    matched = defaultdict(dict)
    keys = ("seed", "size", "retired_dimensions", "radius", "cost_regime")
    for row in rows:
        matched[tuple(row[key] for key in keys)][row["method"]] = row
    cells = defaultdict(list)
    sensitivity = defaultdict(list)
    for key, methods in matched.items():
        static = methods.get("static")
        rqdp = methods.get("rqdp")
        if static and rqdp and rqdp["status"] == "complete" and rqdp["seconds"] > 0:
            speedup = static["seconds"] / rqdp["seconds"]
            _, size, retired, radius, regime = key
            censored = static["status"] != "complete"
            if regime == "U":
                cells[(size, retired)].append((speedup, censored))
            sensitivity[(retired, regime)].append((speedup, censored))
    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85), gridspec_kw={"width_ratios": [1.1, 1]})
    sizes = [16, 24, 32, 48]
    retired_values = [0, 1, 2, 3]
    matrix = [[statistics_median([v for v, _ in cells.get((size, retired), [(math.nan, False)])]) for retired in retired_values] for size in sizes]
    image = axes[0].imshow(
        matrix,
        cmap=mpl.colors.LinearSegmentedColormap.from_list("muted", ["#F1F3F4", COLORS["light_blue"], COLORS["blue"]]),
        norm=mpl.colors.LogNorm(vmin=1, vmax=max(v for row in matrix for v in row if not math.isnan(v))),
        aspect="auto",
    )
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            values = cells[(sizes[i], retired_values[j])]
            censored_fraction = sum(c for _, c in values) / len(values)
            prefix = ">" if censored_fraction >= 0.5 else ""
            label = f"{prefix}{value:.0f}×" if value >= 10 else f"{prefix}{value:.1f}×"
            axes[0].text(j, i, label, ha="center", va="center", fontsize=7.4, color="white" if value > 40 else COLORS["ink"])
    axes[0].set_xticks(range(len(retired_values)), retired_values)
    axes[0].set_yticks(range(len(sizes)), sizes)
    axes[0].set_xlabel("Resolved query dimensions")
    axes[0].set_ylabel("Records per workload")
    axes[0].set_title("a  Median speedup over static DP", loc="left", weight="semibold")
    cbar = fig.colorbar(image, ax=axes[0], fraction=0.045, pad=0.03)
    cbar.set_label("Speedup (×)")

    x = retired_values
    for regime, color, marker in [("U", COLORS["blue"], "o"), ("H", COLORS["orange"], "s")]:
        y = [statistics_median([v for v, _ in sensitivity.get((retired, regime), [(math.nan, False)])]) for retired in x]
        axes[1].plot(x, y, marker=marker, markersize=4, color=color, label="Unit cost" if regime == "U" else "Heterogeneous cost")
    axes[1].set_xticks(x)
    axes[1].set_xlabel("Resolved query dimensions")
    axes[1].set_ylabel("Median speedup over static DP (×)")
    axes[1].set_title("b  Effect of heterogeneous costs", loc="left", weight="semibold")
    axes[1].set_yscale("log")
    axes[1].grid(axis="y", color=COLORS["grid"], linewidth=0.6)
    axes[1].spines[["top", "right"]].set_visible(False)
    axes[1].legend(frameon=False, loc="best")
    fig.subplots_adjust(top=0.88, left=0.09, right=0.97, bottom=0.18, wspace=0.36)
    source = []
    for (size, retired), values in sorted(cells.items()):
        source.append({"panel": "heatmap", "size": size, "retired_dimensions": retired, "cost_regime": "U", "median_speedup": statistics_median([v for v, _ in values]), "censored_fraction": sum(c for _, c in values) / len(values), "runs": len(values)})
    for (retired, regime), values in sorted(sensitivity.items()):
        source.append({"panel": "cost_regime", "size": "", "retired_dimensions": retired, "cost_regime": regime, "median_speedup": statistics_median([v for v, _ in values]), "censored_fraction": sum(c for _, c in values) / len(values), "runs": len(values)})
    with (SOURCE_DIR / "Fig8_controlled_scaling.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["panel", "size", "retired_dimensions", "cost_regime", "median_speedup", "censored_fraction", "runs"])
        writer.writeheader(); writer.writerows(source)
    save(fig, EXP_DIR, "Fig8_controlled_scaling")


def _average_ranks(values):
    """Return one-based average ranks, including ties."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


def _correlation(left, right):
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_scale = math.sqrt(sum((x - left_mean) ** 2 for x in left))
    right_scale = math.sqrt(sum((y - right_mean) ** 2 for y in right))
    return numerator / (left_scale * right_scale)


def task_level_analysis_figure():
    """Show speedup distributions and their relation to state reduction."""
    path = RESULTS / "efficiency.jsonl"
    if not path.exists():
        return
    raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    methods = {"identity", "rqdp"}
    task_runs = defaultdict(list)
    task_states = defaultdict(list)
    for row in raw:
        if row["size"] != 8 or row["method"] not in methods or row["status"] != "complete":
            continue
        key = (
            row["dataset"], row["kind"], row["group"], row["remainder"],
            row["radius"], row["cost_regime"], row["method"],
        )
        task_runs[key].append(row["seconds"])
        task_states[key].append(row["states"])

    paired = []
    base_keys = sorted({key[:-1] for key in task_runs})
    for base in base_keys:
        identity_key = base + ("identity",)
        rqdp_key = base + ("rqdp",)
        if identity_key not in task_runs or rqdp_key not in task_runs:
            continue
        identity_seconds = statistics_median(task_runs[identity_key])
        rqdp_seconds = statistics_median(task_runs[rqdp_key])
        identity_states = statistics_median(task_states[identity_key])
        rqdp_states = statistics_median(task_states[rqdp_key])
        paired.append({
            "dataset": base[0],
            "kind": base[1],
            "group": base[2],
            "remainder": base[3],
            "radius": base[4],
            "cost_regime": base[5],
            "time_speedup": identity_seconds / rqdp_seconds,
            "state_reduction": identity_states / rqdp_states,
        })

    datasets = ["flights", "assets", "hospital", "beers"]
    dataset_colors = {
        "flights": COLORS["blue"], "assets": COLORS["green"],
        "hospital": COLORS["slate"], "beers": COLORS["orange"],
    }
    speedups = [row["time_speedup"] for row in paired]
    state_reductions = [row["state_reduction"] for row in paired]
    rho = _correlation(_average_ranks(state_reductions), _average_ranks(speedups))

    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.95), gridspec_kw={"width_ratios": [0.92, 1.08]})
    grouped = [[row["time_speedup"] for row in paired if row["dataset"] == dataset] for dataset in datasets]
    boxplot = axes[0].boxplot(
        grouped, positions=range(1, len(datasets) + 1), widths=0.52,
        patch_artist=True, showfliers=False,
        medianprops={"color": COLORS["ink"], "linewidth": 1.1},
        whiskerprops={"color": COLORS["slate"], "linewidth": 0.8},
        capprops={"color": COLORS["slate"], "linewidth": 0.8},
        boxprops={"color": COLORS["slate"], "linewidth": 0.8},
    )
    for patch, dataset in zip(boxplot["boxes"], datasets):
        patch.set_facecolor(dataset_colors[dataset])
        patch.set_alpha(0.28)
    for dataset_index, (dataset, values) in enumerate(zip(datasets, grouped), start=1):
        jitter = [((index * 37) % 101 - 50) / 390 for index in range(len(values))]
        axes[0].scatter(
            [dataset_index + value for value in jitter], values,
            s=7, color=dataset_colors[dataset], alpha=0.22, linewidths=0, zorder=2,
        )
    axes[0].axhline(1, color=COLORS["slate"], linewidth=0.8, linestyle="--")
    axes[0].set_yscale("log")
    axes[0].set_xticks(range(1, len(datasets) + 1), [name.capitalize() for name in datasets])
    axes[0].set_ylabel("Task-level speedup over record DP (×)")
    axes[0].set_title("a  Distribution across workloads", loc="left", weight="semibold")

    for dataset in datasets:
        subset = [row for row in paired if row["dataset"] == dataset]
        axes[1].scatter(
            [row["state_reduction"] for row in subset],
            [row["time_speedup"] for row in subset],
            s=11, color=dataset_colors[dataset], alpha=0.48,
            edgecolors="none", label=dataset.capitalize(),
        )
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Reduction in expanded states (×)")
    axes[1].set_ylabel("Task-level speedup (×)")
    axes[1].set_title("b  Search reduction and runtime", loc="left", weight="semibold")
    axes[1].text(
        0.04, 0.94, f"Spearman ρ = {rho:.3f}\nn = {len(paired)}",
        transform=axes[1].transAxes, va="top", ha="left", fontsize=7,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": COLORS["grid"], "linewidth": 0.6},
    )
    axes[1].legend(frameon=False, loc="lower right", ncol=2, columnspacing=0.8, handletextpad=0.3)
    for ax in axes:
        ax.grid(which="major", axis="y", color=COLORS["grid"], linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(top=0.89, left=0.10, right=0.98, bottom=0.19, wspace=0.34)

    with (SOURCE_DIR / "Fig9_task_level_analysis.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["dataset", "kind", "group", "remainder", "radius", "cost_regime", "time_speedup", "state_reduction"])
        writer.writeheader(); writer.writerows(paired)
    save(fig, EXP_DIR, "Fig9_task_level_analysis")


def main():
    method_pipeline()
    compression_example()
    policy_recursion()
    efficiency_figure()
    ablation_size8_figure()
    quality_figure()
    quality_summary_figure()
    synthetic_figure()
    task_level_analysis_figure()


if __name__ == "__main__":
    main()
