# Reviewer-robustness file inventory

## New implementation and test files

- `analysis/reviewer_robustness/protocol_v1.json`
- `paper_scripts/reviewer_robustness/run_reviewer_robustness.py`
- `src/qroute_dilution/reviewer_robustness/__init__.py`
- `src/qroute_dilution/reviewer_robustness/alpha_sensitivity.py`
- `src/qroute_dilution/reviewer_robustness/audit.py`
- `src/qroute_dilution/reviewer_robustness/classical_rcsp.py`
- `src/qroute_dilution/reviewer_robustness/common.py`
- `src/qroute_dilution/reviewer_robustness/depth_budget.py`
- `src/qroute_dilution/reviewer_robustness/finite_shot.py`
- `src/qroute_dilution/reviewer_robustness/manifests.py`
- `src/qroute_dilution/reviewer_robustness/optimization.py`
- `src/qroute_dilution/reviewer_robustness/optimizer_robustness.py`
- `src/qroute_dilution/reviewer_robustness/registry.py`
- `src/qroute_dilution/reviewer_robustness/selection.py`
- `src/qroute_dilution/reviewer_robustness/statistical_audit.py`
- `src/qroute_dilution/reviewer_robustness/statistics.py`
- `src/qroute_dilution/reviewer_robustness/synthesis.py`
- `tests/test_reviewer_robustness.py`

Python bytecode caches created while testing are confined to these new directories and are not scientific artifacts.

## New isolated result tree

- `results/reviewer_robustness/R0/`: audit, protocol inventory, and graph-cluster comparison.
- `results/reviewer_robustness/B1_depth_budget/`: 432 trajectory records, 1,296 checkpoints, summaries, contrasts, figure data, PNG, PDF, and report.
- `results/reviewer_robustness/A1_optimizer/`: 2,016 run records, 1,008 nested diagnostics, PASS-only analysis, summaries, plot, and report.
- `results/reviewer_robustness/A2_alpha/`: 1,224 run records, task/graph summaries, neighborhood contrasts, plot, and report.
- `results/reviewer_robustness/A3_finite_shot/`: endpoint audit, 200 training records, 5,400 estimator records, summaries, heatmap data, two figures, and reports.
- `results/reviewer_robustness/B2_classical/`: 140 exact-solver records, summary table, and report.
- `results/reviewer_robustness/manifests/`: five frozen experiment manifests and seven append-only code amendments.
- `results/reviewer_robustness/provenance/`: pre-existing snapshots, environment inventories, final tests, canonical integrity, and final worktree audit.
- `results/reviewer_robustness/summaries/`: phase reports, Table R1/R2 data, claim-status table, resource ledger, master summary, and revision plan.
- `results/reviewer_robustness/run_registry.csv`, `RESUME_INSTRUCTIONS.md`, `PAPER_REVISION_PLAN.md`, and master/inventory documents.

The manifest/protocol location is intentional: placing reviewer files below the existing canonical `configs/` tree would enter recursive Phase-3 configuration enumeration. Keeping them in the isolated results/analysis namespaces preserves the frozen configuration boundary while still providing machine-readable, pre-execution-frozen manifests.

## Explicitly untouched by this pass

No canonical/frozen manifest, canonical CSV/JSON result, original task assignment, original seed, manuscript source, or pre-existing tracked/untracked work item was modified or overwritten. The final protected inventory is 1,399/1,399 files with no changed hash.
