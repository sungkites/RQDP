# RQDP / RBG V27 manuscript and experiments

This version adds **Residual Bound Greedy (RBG)** as a fast verification policy alongside exact RQDP. RBG selects the next record type from query-count bounds. It does not guarantee minimum verification cost. It still certifies an answer only when the answer is shared by all states allowed by the evidence and omission bound.

## Manuscripts

- `面向可信计数查询的多源数据自适应核验方法_V27.docx`: Chinese manuscript.
- `Adaptive_Verification_RQDP_V27_English.docx`: English manuscript.
- `RQDP_V27_English_Overleaf_20260929.zip`: English Overleaf project; compile `main.tex` with XeLaTeX.
- `Overleaf_RQDP_V27/main.pdf`: locally compiled review PDF (25 pages). The PDF is **not** included inside the Overleaf ZIP.

All heatmaps and bar charts have been replaced with line-based analyses. The revised manuscript contains 16 figures and 6 three-line tables. Figures 1–3 are method diagrams; Figures 4–16 display experimental results.
The repository artifact includes the final PDFs of all 16 figures; the revised line-figure generator is `figures_v27.py`.

## New experimental records

The underlying identifier-free predicate data and the original V16 evaluation are in the [RQDP repository](https://github.com/sungkites/RQDP). The current package contains the new code and numerical results. In `results/`:

- `rbg_quality_paths.jsonl`: all 3,976 size-four query tasks. Every model-valid reference path was certified correctly.
- `rbg_scaling.jsonl`: 375 fixed batches of 8, 16, 24, and 32 records, crossed with omission allowances 0/1/2 and unit/heterogeneous costs, giving 2,250 conditions. RBG produced a first action in all conditions; RQDP completed 1,790 within two seconds. Eight reference paths exceed the chosen omission allowance and are excluded from reference-path cost comparisons, not from planning-completion counts.
- `rbg_rotated_timing.jsonl`: three repeated, order-alternated paired timings on 195 size-eight and size-sixteen batches at omission allowance 1 and unit cost (585 pairs, 1,170 method measurements).
- `rbg_quality_summary.json`, `analysis_v27.json`, and companion CSV files: pooled quality, paired cost and time summaries, batch-resampled intervals, and source values for the new figures.
- `analysis_v26.json`: source values needed to regenerate the V26 computational-boundary line figure.
- `previous_sensitivity/` in the repository artifact: the archived V26 omission/cost sensitivity script and its 5,400 raw solve records. These underpin the retained Figure 11 analysis.

The 600 size-eight scaling conditions all yielded an exact RQDP result. RBG matched the same minimum worst-case cost in 586 conditions. The other 14 were Flights conditions at omission allowance 1; the maximum excess was four cost units. For larger tasks, comparisons of reference-path cost use only conditions where RQDP completed, because timed-out exact runs have no certified optimum.

## Reproduce

Use Python 3.12 and NumPy. Matplotlib is additionally needed for the figures. Set `RQDP_REPO` to a clone of the RQDP repository, or place this folder under `artifacts/v27` in that repository. Execute these commands from the V27 folder:

```powershell
python check_rbg.py
python experiment_v27.py quality --workers 8
python experiment_v27.py scaling --workers 8 --limit-seconds 2
python timing_repeat_v27.py --workers 8
python analyze_v27.py
python figures_v27.py
```

The scaling batch selection uses SHA-256 over dataset, category, size, and batch index, taking at most 30 batches per dataset-size. Selection does not use outcomes or timings. `check_rbg.py` exhaustively evaluates 3,448 admissible reference states across 100 seeded small models; it checks answer correctness and agreement between tree cost and traced worst cost.

New scaling experiments ran on an Intel Core i7-10750H workstation using Python 3.12.14. The archived V16 experiments used a dual-Xeon server. The manuscript does not compare their absolute wall-clock times. All new results are exploratory and depend on the released predicate constructions and declared omission model.
