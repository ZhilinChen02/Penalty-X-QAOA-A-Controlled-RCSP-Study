# Public inputs and storage policy

`manifests/` contains the frozen graph/task identities, generation parameters,
stress levels, discovery/held-out splits and Phase-3 schedule. `configs/` and
`protocols/` at repository root carry seeds, budgets and preregistration.
The inputs are synthetic RCSP constructions; no external dataset was downloaded.

Task JSON payloads were absent in the supplied working tree. Recreate all 140
corrected-v2 and 180 Phase-3 tasks, without optimization, using:

```bash
python scripts/materialize_release_tasks.py
```

The command writes to a new external directory and verifies task/graph IDs,
feasible/optimal counts and optimum cost against frozen result tables. Copy the
printed `data/tasks/` into a separate experimental workspace if rerunning a
phase. Timings in regenerated payloads are new provenance, not replacements for
reported scientific timings. Frozen figures/headlines do not need these files.

The original-tree and Git-history audit found no individual file/blob above
20 MiB (therefore none above 50 or 100 MiB). Private SQLite records, caches and
repeated `dist/` archives are excluded from the public candidate. Small formal
run receipts, failures and censoring records remain in `results/`; they support
provenance and regression checks. No statevector/checkpoint is needed for the
public frozen-result pipeline. Nothing unique was deleted. If future campaigns
produce large raw states or traces, archive them separately (for example Zenodo)
and record their hashes and scope; do not silently replace canonical tables.
