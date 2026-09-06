# Reproducing the frozen study

Install the pinned dependencies and editable package as described in the root
README. `python scripts/verify_release.py` is the read-only entry point. It checks
compact evidence hashes, CSV schemas and row counts, the discovery/held-out
partition, 21 headline values, graph-level H1/H2 inference, stored scaling
exponents, censoring, theory residuals and the four figures' inputs.

The paired inference functions retain the original floating-point operations,
group order, bootstrap seed and exact sign-flip enumeration. The scaling check
reads stored graph exponents and verifies their aggregate ordering; it does not
refit a model. Plotting reads stored intervals, including the original displayed
precision of the depth/budget report. No command below changes canonical files.

```bash
python scripts/verify_release.py
python scripts/reproduce_core_results.py
python scripts/reproduce_figures.py --output-dir dist/replotted
pytest -q
```

For a byte/value comparison against a separately available original research
checkout, use `python scripts/verify_release.py --original-checkout /path/to/research`.
This optional check is not needed by tests or ordinary verification. It compares
original bytes and the headline CSV's exact column projection. Previously
published hostname redactions are allowed only in JSON `host` fields; numerical,
Boolean, array and missing-value semantics must agree. The manifest also records
source hashes for the few previously redacted scientific Markdown reports.

## Benchmark generation

The corrected benchmark and Phase-3 manifests contain task IDs, base graph IDs,
generation seeds, graph templates, budgets and split labels. Recreate all 320
instance JSON files in a new external directory with:

```bash
python scripts/materialize_release_tasks.py --output-dir /path/to/new-instance-directory
```

This uses the original generator and exact route solver, verifies frozen graph
and task identities, feasible/optimal counts and optimal costs, and runs no QAOA
optimizer. Generated instance timing fields are new measurements, not replacements
for frozen results. The full JSON instances need not be individually Git tracked.

## Tests and numerical scope

Public tests cover feasibility, edge-bit encoding, Hamiltonians, scale control,
exact statevectors, X mixing, nested embedding, O0/O1/O2/O3, fractional-cutoff
CVaR, optimizer evaluation budgets, deterministic seeds, graph-level inference,
censoring and theory assumptions. Historical private-worktree/Git inventory and
obsolete manuscript-packaging tests were replaced by public manifest and result
checks. The optional GPU test may skip on CPU-only installations.

The scientific backend is CPU NumPy. Linux/Python 3.11 with the pinned pip stack
is tested; a separate conda solve and native Windows execution are not asserted.
Full optimization and scaling campaigns were not rerun for this repository
cleanup. See EXPERIMENTS.md for the original stage interfaces and their limits.

## Data retention

Compact tables are copied unchanged from frozen evidence; the headline table
is an exact four-column projection of the frozen claim table. All formal rows
in the retained run matrices remain, including negative comparisons, failures,
optimizer termination messages and resource-censored rows. Consolidated tables
replace thousands of separate run receipts and iteration traces in the current
checkout. No failed experiment was removed from a retained matrix.

The initial public commit `dc4106f03905b8ea86a0596fa2f007a094cfa4b1` remains in
Git history and contains the earlier complete bundle, including optional raw
receipts and extra intermediate artifacts. They are unnecessary for the main
verification/replot commands. For example, `git show COMMIT:path/to/file` reads
an archived file without replacing the current checkout. The original research
working directory is also retained separately; no history was rewritten.
