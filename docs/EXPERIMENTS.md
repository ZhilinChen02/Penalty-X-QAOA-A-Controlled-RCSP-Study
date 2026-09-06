# Experiment execution boundaries

Use the complete stage/command map in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
The public defaults are `scripts/smoke_test.py`, `reproduce_core_results.py` and
`reproduce_figures.py`. Only the bounded smoke executes small optimization.
Core reconstruction and plotting read frozen results.

The real full-run order is Phase 0 → corrected Phase 0.5 universe → Phase 0.6
scale audit → Phase-1 depth pilot → Phase-1.1 nested/continuation diagnosis →
Phase-1.2 O0/O1/O2/O3 discovery → Phase-2 frozen held-out → Phase-3 scaling.
Reviewer optimizer, tail-fraction, depth/budget and finite-shot analyses are
separate post-hoc studies, never a replacement confirmatory family.

Full drivers preserve historical root-relative outputs, resume semantics,
manifest/freeze hashes and prerequisite endpoints. Use an isolated working copy
with a planned empty stage output; a `full` call beside retained run IDs resumes
rather than independently reproduces those runs. Do not re-freeze the public
release or edit predecessor hashes to bypass a guard. Restore missing task JSON
using `materialize_release_tasks.py` before later-stage execution.

The original protocol files specify exact seeds, initialization, objectives,
resource budgets and task order. CPU/RAM are the actual experimental resources;
no GPU simulation implementation is provided. Larger optimization campaigns were
not rerun for release engineering. Different optimizer environments can change
trajectories; keep reruns separate and report discrepancies instead of updating
the frozen references.
