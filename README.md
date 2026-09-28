# RQDP: Residual Query Dynamic Programming

Research code and predicate-level data accompanying **Adaptive Verification of Multi-source Data for Reliable Count Queries** (Chinese title: 面向可信计数查询的多源数据自适应核验方法).

RQDP computes an exact verification policy that minimizes worst-case inspection cost for multiple count-threshold queries. Records may share candidate predicate sets, and a bounded number of true predicate vectors may fall outside those sets. As queries become determined, RQDP projects onto the remaining queries, merges equivalent record types, and removes dominated feedback branches. RQDP-A preserves this primary optimum and uses unresolved-query area to select among cost-optimal actions.

## Current evaluation

The expanded evaluation covers Flights, Hospital, Beers, and de-identified asset predicates. At eight records per workload, RQDP is 4.06–45.09 times faster than record-level dynamic programming. RQDP-A improves or matches RQDP's F1-cost area on all four datasets and attains the highest area on Beers. Controlled workloads vary the number of already resolved query dimensions to show when residual equivalence produces additional compression.

The timing runs used a dual Intel Xeon Gold 6330 server with 100 CPU cores available and 117 GiB RAM. Independent tasks were distributed across 72 processes; each solve used one CPU core. The host also contained an NVIDIA A100, but the exact search is CPU-bound and did not use the GPU.

## Reproduce the expanded evaluation

Python 3.12 is recommended. The experiments require no database connection and use only the Python standard library. Figure generation also requires Matplotlib.

```bash
python src/v16_experiments.py check
python src/v16_experiments.py quality --workers 32
python src/v16_experiments.py efficiency --workers 32
python src/v16_structured.py 32
python src/v16_figures.py
```

The figure command writes PDF, SVG, PNG, and source-data CSV files to `artifacts/figures/`. Archived measurements are already available in `results/v16/`; rerunning timing experiments on another machine will not reproduce the same wall-clock values exactly.

The earlier two-dataset evaluation remains available through `reproduce.py`:

```bash
python reproduce.py check
python reproduce.py quality
python reproduce.py primary
python reproduce.py baselines
python reproduce.py scale
python reproduce.py additional
```

## Contents

| Path | Contents |
| --- | --- |
| `src/dominance.py` | Full RQDP implementation |
| `src/kernel.py` | Record-level, static, and residual compression variants |
| `src/anytime.py` | RQDP-A lexicographic early-certification tie-break |
| `src/robust.py` | Independent explicit minimax reference |
| `src/solver.py`, `src/robust_baselines.py` | Adapted baseline selection rules |
| `src/v16_experiments.py` | Four-dataset quality and efficiency experiments |
| `src/v16_structured.py` | Controlled residual-equivalence study |
| `src/v16_figures.py` | Five manuscript figures and source-data tables |
| `data/` | Identifier-free predicate candidates and evaluation references |
| `results/paper/` | Archived measurements for the earlier manuscript |
| `results/v16/` | Archived measurements for the expanded manuscript |
| `artifacts/figures/` | Manuscript figures and plotted source data |
| `DATA_CARD.md` | Provenance, preprocessing, privacy, and interpretation |
| `PROTOCOL.md` | Workloads, metrics, and measurement settings |

The reference state is used as an evaluation oracle, not as input to policy selection. Baseline rules are adapted to the same allowed states, record feedback, and stopping condition; they are not runs of the original authors' complete systems. RQDP targets minimum worst-case verification cost and exact planning efficiency. RQDP-A adds a secondary objective for earlier certification, but it is not expected to dominate task-specific heuristics on every partial-budget quality curve.

## Expanded manuscript results

| Manuscript result | File in `results/v16/` |
| --- | --- |
| Exactness checks and experiment settings | `protocol.json` |
| F1 and confirmation trajectories | `quality_paths.jsonl`; summary in `quality_summary.json` |
| Planning-time and scale comparisons | `efficiency.jsonl`; summary in `efficiency_summary.json` |
| Controlled residual-equivalence study | `structured.jsonl` |
| Additional random workloads retained for audit | `synthetic.jsonl` |

The release contains a research artifact for a manuscript; it does not imply publication or acceptance. Funding: Zhejiang Province University Laboratory Research Project, grant ZB202677.
