# RQDP: Residual Query Dynamic Programming

Research code and predicate-level data accompanying **Adaptive Verification of Multi-source Data for Reliable Count Queries** (Chinese title: 面向可信计数查询的多源数据自适应核验方法).

RQDP computes an exact verification policy that minimizes worst-case inspection cost for multiple count-threshold queries. Records may share candidate predicate sets, and a bounded number of true predicate vectors may fall outside those sets. As queries become determined, RQDP projects onto the remaining queries, merges equivalent record types, and removes dominated feedback branches. Actual verification retains complete feedback for updating the omission allowance.

## Abstract

Conflicting multi-source records can leave query answers uncertain, while inspecting every record incurs unnecessary cost. Residual Query Dynamic Programming (RQDP) computes minimum worst-case-cost verification policies for multiple count-threshold queries sharing records. The model permits a bounded number of true predicate vectors to be absent from their candidate sets. RQDP initially groups records with identical candidates and costs, then updates the grouping as queries become determined. Feedback branches with identical effects on the remaining queries are reduced using dominance in continuation cost. Full feedback is retained during policy execution. Under a valid omission bound and correct verification feedback, these reductions preserve optimal cost and reliable answers. Experiments on Flights and asset-register predicate data show speedups of 11.19 and 35.11 over record-level dynamic programming for batches of eight records. On Flights, RQDP reduces computation time by a further 55.5% relative to static compression and reduces mean worst-case inspection cost by 5.33% relative to the implemented EC², ASR, and Pairs selection rules. These results show how shared record effects on unresolved queries can reduce the cost of exact policy computation.

## Run

Python 3.12 is recommended. No third-party Python dependencies or database connection are required.

```bash
python reproduce.py check       # independent exhaustive correctness checks
python reproduce.py quality     # all size-four threshold-grid quality curves
python reproduce.py primary     # all size-four/eight compression comparisons
python reproduce.py baselines   # natural-candidate verification-cost comparisons
python reproduce.py scale       # larger batches; resource limits are retained
python reproduce.py additional  # heterogeneous costs and omission-bound sensitivity
python src/summarize.py         # summarize the archived main measurements
```

Fresh outputs are written to `results/runs/`. Primary, scale, additional, and quality runs resume existing output files; use a clean output directory for an independent rerun. Run timing experiments serially, without other benchmarks running concurrently. The baseline runner replaces its own output file. Larger experiments may take substantially longer than the correctness and quality checks.

## Contents

| Path | Contents |
| --- | --- |
| `src/dominance.py` | Full RQDP implementation |
| `src/kernel.py` | Identity, static, and residual compression variants |
| `src/robust.py` | Independent explicit minimax reference and symbolic implementation |
| `src/solver.py`, `src/robust_baselines.py` | Adapted baseline selection rules |
| `data/` | Identifier-free predicate candidates and evaluation references |
| `results/paper/` | Archived numerical measurements used in the manuscript |
| `paper/abstract_zh.md` | Chinese title, abstract, and keywords |
| `DATA_CARD.md` | Provenance, preprocessing, privacy, and interpretation |
| `PROTOCOL.md` | Workloads, metrics, and measurement settings |

The reference state is used as an evaluation oracle, not as input to policy selection. Archived timings are measurements on the original machine, not expected runtimes on every machine. Baseline rules are adapted to the same allowed states, record feedback, and stopping condition; they are not runs of the original authors' complete systems. RQDP targets worst-case verification cost and exact computation efficiency, not uniformly best partial-budget F1 or mean observed cost.

This repository is a research artifact for a manuscript; it does not imply publication or acceptance. Funding: Zhejiang Province University Laboratory Research Project, grant ZB202677.
