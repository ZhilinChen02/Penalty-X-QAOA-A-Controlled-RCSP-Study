# Result provenance

All paths below name existing frozen evidence. The release does not move these
files into a new `canonical/` layout because historical references use their
current locations. The source/analysis/figure relationships reuse the existing
manifests and `paper_audit/figure_manifest.csv`; Figure v3's explicit input ledger
is produced by `paper_scripts/redesign_main_figures_v3.py`.

| Paper result | Frozen source | Analysis / verification | Plot / presentation |
| --- | --- | --- | --- |
| Benchmark construction: corrected 140 tasks / 25 graphs | `data/manifests/phase0_v2_dilution_stress.json`; `results/phase0_v2_dilution_stress/task_characterization.csv` | `src/qroute_dilution/graph_generator.py`, `rcsp.py`, `stress.py`; `scripts/materialize_release_tasks.py` | Figure v3 1a/1b, `paper_scripts/redesign_main_figures_v3.py` |
| Scale audit and preserved optima | `results/phase0_v2_dilution_stress/penalty_contract_comparison.csv`; `configs/penalty_contract_v2_scale_controlled.yaml` | `src/qroute_dilution/hamiltonian_audit.py`; `scripts/run_phase06.py`; scale regression tests | Figure v3 1c; historical `paper_scripts/build_paper_assets.py` |
| Nested p=2 → p=3 identities; 29/168 failures | `results/phase1_1_optimization_diagnostic/nested_ansatz_identity.csv`; `results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv` | `src/qroute_dilution/phase1_1_diagnostic.py`; `reproduction/reproduce_headlines.py` | Figure v3 2a |
| Continuation: objective 29/29, feasibility 27/29 | `results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv` | `paper_scripts/rebuild_publication_results.py` (`reconstruct_optimizer`); `reproduction/reproduce_headlines.py` | Figure v3 2b |
| Mean energy versus feasible-mass mismatch | `results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv`; Phase-1.1 analysis tables | `src/qroute_dilution/phase1_1_analysis.py`; `paper_scripts/rebuild_publication_results.py` | Existing main-text paragraph and supplementary optimizer analysis |
| O0 / O1 / O2 / O3 definitions | `src/qroute_dilution/phase1_2_objectives.py`; `configs/phase1_2_objective_alignment.yaml` | Objective/CVaR regression tests; `src/qroute_dilution/phase1_2_analysis.py` | `overleaf/tables/table02_objectives.tex` and discovery assets |
| Discovery set and O2–O0 capacity gap / CVaR gap closure | `data/manifests/phase1_pilot_v1.json`; `results/phase1_2_objective_alignment/capacity_gap.csv`; `results/phase1_2_objective_alignment/objective_results.csv` | `paper_scripts/rebuild_publication_results.py` (`reconstruct_discovery`) | Historical `fig05_objective_discovery.pdf` and discovery tables from `paper_scripts/build_paper_assets.py` |
| Held-out set: 84 tasks / 15 graphs | `data/manifests/phase2_confirmatory_v1.json`; `results/phase2_confirmatory_v1/p3_objective_results.csv`; `results/phase2_confirmatory_v1/PREREGISTRATION.md` | `reproduction/reproduce_heldout.py` | Figure v3 3; generated paper Table 2 (source `table04_heldout_results.tex`) |
| H1: O3–O0 superiority | `results/phase2_confirmatory_v1/graph_level_contrasts.csv`; `results/phase2_confirmatory_v1/confirmatory_statistics.json` | Graph-level sign flips, grouped bootstrap and Holm reconstruction in `reproduction/reproduce_heldout.py` | Figure v3 3a |
| H2: O3–O2 noninferiority | Same frozen graph contrasts/statistics; frozen margin −0.10 | Same held-out script; independent claim audit in `paper_scripts/rebuild_publication_results.py` | Figure v3 3b; one-sided lower bound, not a two-sided CI |
| Phase-3 scaling, m=20 reversal and m=22 censoring | `results/phase3_scaling_v1/canonical_results.csv`; `results/phase3_scaling_v1/base_graph_exponents.csv`; `results/phase3_scaling_v1/failure_census.csv`; `results/phase3_scaling_v1/resource_preflight.csv` | `reproduction/reproduce_scaling_verdict.py`; `protocols/phase3_scaling_v1/` | Main-text scaling paragraph, supplementary scaling table/figure; no synthetic m=22 outcomes |
| Depth / budget robustness | `results/reviewer_robustness/B1_depth_budget/figure_data_nested_failure.csv`; `results/reviewer_robustness/B1_depth_budget/depth_budget_summary_graph.csv`; `results/reviewer_robustness/B1_depth_budget/B1_DEPTH_BUDGET.md` | Existing reviewer depth-budget analysis; graph means verified against the frozen table | Figure v3 4; six CIs read at the existing report's four-decimal precision |
| Finite-shot training | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv`; `results/reviewer_robustness/A3_finite_shot/finite_shot_training_summary_task.csv` | Existing `src/qroute_dilution/reviewer_robustness/finite_shot.py`; provenance caveat below | Figure v3 finite-shot supplement; both noisy-training intervals cross zero |
| Membership/global theory numerical checks | `results/theory_validation_v1/finite_case_summary.csv`; `results/theory_validation_v1/numerical_validation_summary.json` | `scripts/validate_global_dilution_bound.py`; read-only residual reconstruction in `scripts/validate_release.py` | Theory summaries and scoped proof statements |
| Adaptive / membership theory | `results/theory_validation_v2/adaptive_finite_case_summary.csv`; `results/theory_validation_v2/adaptive_validation_summary.json` | `scripts/validate_adaptive_dilution_bound.py`; `scripts/validate_release.py` | Supplementary theory and bridge audits |
| Advice / explicit-RCSP theory | `results/theory_validation_v3/posterior_advice_validation.csv`; `results/theory_validation_v3/posterior_advice_validation_summary.json`; explicit-RCSP CSVs in the same directory | `scripts/validate_structure_advice_bound.py`; `scripts/validate_explicit_rcsp_query_constructions.py`; `scripts/validate_release.py` | Theory scope, padding counterexamples and structure/advice ledger |

O0 is mean energy; O1 is expected flow plus resource penalty; O2 is the exact
`1-P_feas` mechanistic capacity control; O3 is exact weighted lower-tail CVaR
with the historically selected alpha=0.10 and fractional cutoff mass. All use
the original ansatz/Hamiltonian contract. The generator, feasibility definition,
seeds, order, objective implementation and frozen inference are unchanged.

Discovery, held-out and post-hoc evidence must not be pooled. Phase 3 contains
180 planned tasks / 30 graphs, while the 180 m=22 **run rows** are a different
unit; those rows have resource-censored status and no scientific outcomes.
Failures and all completed formal run receipts are retained.

## Known plotting provenance issue

The historical finite-shot PDF has three terminal-distribution groups, matching
20 task–objective summaries per regime in `finite_shot_training_summary_task.csv`.
The current aggregate caller passes a runs-only table with two shot regimes to
its helper. Calling it directly therefore does not reproduce the same boxes.
Figure v3 explicitly uses the summary table verified against the existing PDF;
no scientific table or helper was silently changed. See `OPEN_SOURCE_AUDIT.md`
and `docs/FIGURE_REDESIGN.md`. This is the existing known provenance discrepancy,
not a discrepancy in the headline numeric checks.

## Integrity chain

`reproduction/expected_hashes.txt` and all golden files are unchanged.
`release_manifest.json` in the public package records original/public hashes and
privacy-only redactions. Historical hash inventories stay intact. Public tests
skip only the documented unredacted-Git/worktree checks and validate the public
manifest plus retained historical scientific hashes separately.
