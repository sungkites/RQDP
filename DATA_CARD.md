# Released data

The release contains derived predicate inputs, not raw asset registers or raw Flights tables. Each record has exactly three fields: `domain` (candidate indices into `omega`), `truth` (evaluation reference index), and `cost_h` (a fixed experimental cost from 1 to 4). Uniform-cost experiments assign cost 1. Collection order preserves the original workload boundaries.

## Asset predicates

There are 1,163 objects: 241 equipment, 920 furniture, and 2 low-value objects. Historical and saved current versions provide candidates; the current register provides the evaluation reference. The two predicates express whether location matches an archived target and whether both location and custody information match their targets. The semantic universe is `(0,0), (1,0), (1,1)`.

Only predicate indices and costs are released. Personal names, contact details, custody text, locations, department names, original object identifiers, timestamps, database connection information, and identifier-to-record mappings are excluded. `cost_h` preserves the previously assigned experimental cost but does not publish the identifier or its hash. This is a data-minimized abstraction, not a claim of formal differential privacy.

Current versions are included in candidate construction, so reference coverage is partly guaranteed by construction. Historical versions are not independent contemporaneous sources, and the register reference is not a separate physical inspection. The data evaluate the solver on business-derived structure.

## Flights predicates

The upstream dataset is the Flights dataset distributed in the [Raha repository](https://github.com/BigDaMa/raha/tree/master/datasets/flights), also used in Baran evaluations. The original collection contains 2,376 source records describing 100 flights from 38 sources. This release preserves the 80-flight evaluation subset used by these experiments; the other 20 flights were used in earlier development.

For each flight, parsable actual departure and arrival times are converted into minutes of the day. Candidate predicate values are formed separately and combined by Cartesian product. Each predicate tests whether the actual clock time reaches the planned clock time plus 15 minutes, modulo 1,440. Planned times use the mode in the dirty file; references use the clean file. These are clock predicates, not an elapsed-delay analysis accounting for date changes. Raw upstream rows are not redistributed here.

Upstream input SHA-256 checksums:

* `dirty.csv`: `1b5c1afa10aa0e7c20fd7e14d05c56772715b2771aa0f5fa67ed1709e1eecd46`
* `clean.csv`: `0acfcfd8985b06fdd363965c9e8d9522c43e7589a93d79ae7dc311e1c37fdf3b`

Both datasets informed method development. The evaluation is exploratory; the preserved split is not a fresh independent test set. The release supports reproduction from predicate inputs onward; reconstructing those inputs from private business records requires access to the original records.
