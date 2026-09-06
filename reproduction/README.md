# Paper-Level Reproduction

This package rebuilds the publication's numerical conclusions from frozen
row-level CSV/JSON evidence. It does **not** run QAOA optimization. Execution
by the authors or Codex is a reproducibility check, not independent external
reproduction; that status remains pending until a separate person runs and
reviews it.

## 1. Clean environment

From the repository root, with Python 3.10 or newer:

```bash
python -m venv .venv-reproduction
source .venv-reproduction/bin/activate
python -m pip install --upgrade pip
python -m pip install -r reproduction/requirements.txt
```

The exact package versions here record the earlier environment used to create the checked
hashes. The root `requirements-dev.txt` instead pins the separately validated
release CPU stack; see `docs/ENVIRONMENT.md`. The project itself supports the broader version bounds in
`pyproject.toml`; if a different numerical stack is used, compare numeric
values with the stated `5e-12` absolute tolerance before interpreting an
output-file hash difference.

## 2. Frozen evidence locations

The scripts read, but never write, these canonical roots:

- `data/manifests/`
- `configs/`
- `results/phase0_v2_dilution_stress/`
- `results/phase1_1_optimization_diagnostic/`
- `results/phase1_2_objective_alignment/`
- `results/phase2_confirmatory_v1/`
- `results/phase3_scaling_v1/`

The exact input list and SHA-256 values are written to
`reproduction/rebuilt/canonical_input_hashes.txt`. Missing per-task generator
JSON files are not required for this paper-level reconstruction; the retained
manifests, configurations, and canonical result rows are the inputs used here.

## 3. Rebuild and verify headlines

```bash
python reproduction/reproduce_headlines.py --verify
python reproduction/reproduce_heldout.py --verify
python reproduction/reproduce_scaling_verdict.py --verify
sha256sum -c reproduction/expected_hashes.txt
```

These commands verify:

- the 140-task controlled universe and zero duplicate primary feasible sets;
- the 168 nested-ansatz comparisons and optimizer-attribution counts;
- the discovery O2/O3 capacity-gap summaries;
- held-out H1/H2 graph-level effects, grouped bootstrap bounds, exact sign-flip
  tests, and Holm correction;
- the 80/84 O3-vs-O0 optimal-route wins;
- the 79/84 joint feasibility/optimal-route wins;
- the completed \(m=20\) exponent means and O3/O0 ordering reversal;
- the 180 planned \(m=22\) rows being resource-censored with no scientific
  outcomes.

Reproduction JSON uses 12 decimal places for portable hashes. The full audit
keeps unrounded values and enforces an absolute comparison tolerance of
`5e-12`; counts and logical verdicts are exact.

## 4. Regenerate Figure 6 and Table 4

```bash
python scripts/validate_release.py --from-existing-results --assets
```

This deterministic publication entry point first reconstructs and checks all
headline values, then regenerates the paper assets. In particular it writes:

- `overleaf/figures/fig06_heldout_confirmation.pdf`
- `overleaf/tables/table04_heldout_results.tex`

The wrapper writes these paths inside a new disposable `asset-workspace/`, whose
location is printed. It also rebuilds the other publication figures/tables and runs the manuscript
claim/evidence audit. It never imports or calls an optimizer. A mismatch stops
asset generation rather than overwriting the discrepancy.

## 5. Interpret the outputs

Expected successful terminal messages begin with `HEADLINE PASS`,
`HELD-OUT PASS`, and `SCALING PASS`. Inspect the generated JSON/CSV files in
`reproduction/rebuilt/`; do not rely on terminal messages alone. In
particular, confirm that:

- `heldout.json` reports analysis unit `base_graph_id`, 84 tasks, 15 graphs,
  and the preregistered H1/H2 margins;
- `scaling_verdict.json` reports `m20_O3_vs_O0_ordering_reversed: true`,
  `m22_resource_censored: true`, and
  `global_scaling_law_supported: false`;
- `canonical_input_hashes.txt` matches the checked reference.

If a hash fails, preserve the output, record Python/package/platform versions,
and compare numeric fields before rerunning anything. Do not alter a canonical
row or rerun optimization to force agreement.
