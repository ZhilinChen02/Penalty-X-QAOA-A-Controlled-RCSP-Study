# Frozen results

Canonical tables retain the original phase-directory names to preserve source
and manifest references. `manifest.json` records their hashes, schemas, row counts
and original provenance. `headline_results.csv` is an exact column projection of
the frozen headline table; `canonical/headlines.json` is the unchanged reference.

Use `python scripts/verify_release.py` to reconstruct/check the main claims and
`python scripts/reproduce_figures.py` to replot. Neither command reruns optimization
or refits scaling. All formal rows in the compact matrices, including negative
comparisons, optimizer termination information and resource censoring, remain.
No absent m=22 outcome is filled with zero or extrapolated.

The post-hoc reviewer directories contain scientific robustness studies, separate
from held-out H1/H2. Detailed provenance is in `docs/RESULT_PROVENANCE.md`.
Thousands of redundant run receipts and iteration traces are archived in the
initial public commit; they are not needed for these commands.
