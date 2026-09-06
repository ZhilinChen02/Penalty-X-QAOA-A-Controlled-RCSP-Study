# Result provenance

`results/manifest.json` records SHA-256, CSV columns/row counts, original paths
and baseline-commit hashes for the compact evidence, benchmarks, scientific
source, theory statements and final figures. Original phase paths are retained
to preserve source imports and frozen references. These phase directories are
the canonical data store; moving them into another nested layout would duplicate
data or require unnecessary changes to the scientific code.

All retained CSVs and numerical JSON payloads keep their frozen values.
`results/headline_results.csv` selects and renames four columns from the original
frozen claim table, without changing the stored strings. Its projection is
recorded in the manifest. `results/canonical/headlines.json` is an unchanged
copy of the frozen reconstruction reference, which uses 12 decimal places.
Full-precision inference is checked against the original confirmatory JSON.

| Result | Frozen source below `results/` unless stated otherwise | Analysis / figure |
| --- | --- | --- |
| 140 corrected tasks / 25 graphs | `phase0_v2_dilution_stress/task_characterization.csv`; `data/manifests/phase0_v2_dilution_stress.json` | Original graph generator and exact RCSP solver; Figure 1 |
| Discovery 56/10; held-out 84/15 | `data/manifests/phase1_pilot_v1.json`, `phase2_confirmatory_v1.json` | Public split verification, graph-level analysis |
| Scale audit | `phase0_v2_dilution_stress/hamiltonian_scale_audit.csv`, `penalty_contract_comparison.csv` | Hamiltonian invariant tests; Figure 1 |
| Phase-1 diagnostics | `phase1_pilot_v1/master_seed_level_results.csv`, `task_depth_summary.csv` | Original `phase1_analysis.py` and unit tests |
| Nested identities and 29/168 failures | `phase1_1_optimization_diagnostic/nested_ansatz_identity.csv`, `p3_random_vs_embedded.csv` | `publication.reconstruct_optimizer`; Figure 2 |
| Continuation repairs 29/29; feasibility gains 27/29 | `phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv`, `p3_continuation_seed_level.csv` | Same reconstruction; Figure 2 |
| O0/O1/O2/O3 and CVaR capacity-gap closure | `phase1_2_objective_alignment/objective_results.csv`, `capacity_gap.csv` | Original `phase1_2_objectives.py`; `publication.reconstruct_discovery` |
| Frozen held-out evaluation | `phase2_confirmatory_v1/PREREGISTRATION.md`, `p2_initialization_runs.csv`, `p3_objective_results.csv` | `publication.reconstruct_heldout` |
| H1/H2, lower bounds and Holm significance | `phase2_confirmatory_v1/graph_level_contrasts.csv`, `confirmatory_statistics.json` | Original sign flips and grouped bootstrap preserved in `publication.py`; Figure 3 |
| O3 P_opt improvement counts | `phase2_confirmatory_v1/p3_objective_results.csv`, `task_level_contrasts.csv` | Complete taskwise contrasts; verification |
| Phase-3 task/split design | `data/manifests/phase3_scaling_v1/`; `phase3_scaling_v1/PREREGISTRATION.md` | 180 tasks / 30 graphs, m=12–22 |
| m=20 reversal / m=22 censoring | `phase3_scaling_v1/canonical_results.csv`, `base_graph_exponents.csv`, `resource_preflight.csv`, `failure_census.csv` | Stored exponent aggregation and status checks; no model refit |
| Optimizer and alpha robustness | `reviewer_robustness/A1_optimizer/`, `A2_alpha/` compact run/graph tables | Original post-hoc analysis modules; retained negative outcomes |
| Depth / budget boundary | `reviewer_robustness/B1_depth_budget/depth_budget_runs.csv`, `nested_diagnostics.csv`, graph summaries and `B1_DEPTH_BUDGET.md` | Figure 4; stored intervals retain the report's four-decimal precision |
| Fixed-endpoint finite-shot sampling | `posthoc_finite_shot_endpoint_v1/aggregate.csv`, `exact_reference.csv`, manifest/config | Distinct post-hoc endpoint experiment |
| Finite-shot training | `reviewer_robustness/A3_finite_shot/finite_shot_training_runs.csv`, task/graph/effect summaries | Supplementary finite-shot plot; two noisy intervals cross zero |
| Theory numerical validation | `theory_validation_v1/finite_case_summary.csv`; `theory_validation_v2/adaptive_finite_case_summary.csv`; `theory_validation_v3/posterior_advice_validation.csv` and explicit RCSP tables | `publication.reconstruct_theory`, original theorem modules/tests, `docs/theory/` |

The default figure driver is `scripts/reproduce_figures.py`; its single plotting
implementation is `scripts/_plot_figures.py`. `INPUTS` lists all numerical inputs.
Final assets are `figures/main/fig1` through `fig4` (PDF/PNG) and
`figures/supplementary/finite_shot` (PDF/PNG). The figure functions preserve the
reviewed v3 layouts and data; only public filenames and export formats changed.

## Finite-shot grouping caveat

The historical finite-shot aggregate caller passes a runs-only table with two
shot regimes to its plotting helper. The published terminal-distribution boxes
match the frozen task-summary table: 20 task–objective summaries in each of three
regimes, including exact training. The public plot explicitly uses this table.
The historical scientific helper and all results remain unchanged. Individual
training runs and task summaries must not be treated as the same analysis unit.

## Complete rows and archived detail

The compact matrices retain every formal row they originally contained:
2016 optimizer-robustness rows, 1224 alpha rows, 1296 depth/budget checkpoint rows,
200 finite-shot training rows, and the 1080-row Phase-3 canonical matrix. Negative
comparisons and termination/censoring fields remain. Phase 3's 180 planned tasks
and the 180 m=22 planned run rows are different units; the latter contain no
scientific outcomes. Initializations and seed/budget metadata are retained in
tables/configs/manifests rather than thousands of repeated JSON receipts.

Raw receipt/iteration detail and older packaging material remain recoverable
from initial commit `dc4106f03905b8ea86a0596fa2f007a094cfa4b1`. The current checkout
retains the compact evidence needed for the paper; no Git history was rewritten.
