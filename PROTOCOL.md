# Experimental protocol

## Main comparisons

Records are grouped consecutively within each data category. Incomplete trailing groups are excluded by batch size. Flights supplies 20 batches of size 4 and 10 of size 8; assets supply 290 and 145 respectively. Asset batches cover 1,160 objects at either size. The remaining three objects are retained in the released input file. No batch is removed because of a method's result.

Two queries share the records and use threshold `ceil(n/2)`. Record cost is 1 and the omission allowance is 1. Baselines use identical allowed states, full-record feedback, and deterministic answer confirmation. EC² and ASR use uniform state weights as an experimental convention. Pairs chooses by worst-case pair-disagreement reduction per unit cost; rollout uses Pairs continuations. These are selection-rule adaptations.

Identity, static, residual, and full RQDP share bounds, action ordering, memoization, and branch-and-bound. All avoid explicit enumeration of database worlds; the explicit solver is used as an independent small-model reference and for finite baseline rules.

## Quality

Every size-four batch is evaluated at `k=1,2,3,4`, with both query thresholds equal to `k`. This is a four-point shared-threshold grid, not all sixteen independent threshold pairs. It yields 80 Flights workloads and 1,160 asset workloads. Micro Precision, Recall, and F1 are computed by pooling output counts within each dataset. Unconfirmed positive outputs count as missed positives. If no positive answer is released, precision is set to 1; recall and confirmation coverage are also reported. Certification error is computed only over confirmed answers.

The normalized F1-cost area is a right-continuous step integral over cost fraction 0 to 1; it is not ROC-AUC. Different thresholds and repeated runs share records and are not independent data samples.

## Cost and time

Worst-case cost is evaluated over all allowed states per workload, then averaged. Reference-path cost is a separate quantity. Timings include solver construction and the first optimal value/action, excluding input parsing, garbage collection, and later trace checks. Main experiments rotate method order over three serial repeats, take a median per task, then average across tasks.

Archived measurements used an Intel Core i7-10750H, 15.86 GiB RAM, Windows 11, and Python 3.12.14. Main solves use a 10-second soft deadline and a 200,000-expanded-state limit; scale and parameter solves use 3 seconds and the same state limit. Deadline checks are periodic. Resource-limit outcomes remain in the archived files.

Scale tests reconstruct records from complete size-four batches before forming sizes 16, 32, 64, and 128. Parameter tests use original size-sixteen batches, omission allowances 0, 1, and 2, and either uniform or precomputed heterogeneous costs. The historical heterogeneous cost assignment is preserved numerically without releasing identifiers.
