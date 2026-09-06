# Entry-point inventory

All executable Python entry points discovered in the release tree are listed below.
Legacy scripts can write fixed result/paper paths and may start expensive work.
Use `release_smoke.py`, `validate_release.py` and `materialize_release_tasks.py` for
safe temporary-output validation. For other commands, consult the pipeline guide
and their source before execution. An argparse CLI supports `--help`; scripts
without argparse may execute their full workflow even when given that flag.

| Script | Purpose from source | argparse CLI |
|---|---|---|
| `scripts/audit_public_snapshot.py` | Read-only release scan. Report locations/types, never credential values. | yes |
| `scripts/audit_rcsp_bridge.py` | Generate the explicit-input RCSP bridge and description audits. | yes |
| `scripts/build_prior_art_matrix.py` | Build the inspected-primary-source matrix and reproducible search log. | no — may execute immediately |
| `scripts/build_public_snapshot.py` | Build a separate, traceable public candidate without Git history or local metadata. | yes |
| `scripts/build_structure_cost_matrix.py` | Build the structure-cost method matrix, full ledger, and Figure 8. | yes |
| `scripts/build_synthesis_assets.py` | Build auditable Synthesis-v1 CSV assets from frozen predecessor evidence. | no — may execute immediately |
| `scripts/characterize_tasks.py` | Legacy entry point; see phase protocol and source. | yes |
| `scripts/generate_tasks.py` | Legacy entry point; see phase protocol and source. | yes |
| `scripts/materialize_release_tasks.py` | Recreate missing instance JSON in a new external directory, verifying frozen identities. | yes |
| `scripts/release_smoke.py` | Run the original 12-task smoke optimization in a new temporary workspace. | yes |
| `scripts/run_grover_tightness_validation.py` | Run the offline Grover achievability/formula validation. | no — may execute immediately |
| `scripts/run_phase0.py` | Legacy entry point; see phase protocol and source. | yes |
| `scripts/run_phase05.py` | Legacy entry point; see phase protocol and source. | yes |
| `scripts/run_phase06.py` | Legacy entry point; see phase protocol and source. | no — may execute immediately |
| `scripts/run_phase1.py` | Legacy entry point; see phase protocol and source. | yes |
| `scripts/run_phase1_1_diagnostic.py` | Explicit stage runner for the immutable Phase 1.1 diagnostic. | yes |
| `scripts/run_phase1_2_objective_alignment.py` | Stage-gated runner for the immutable Phase 1.2 objective diagnostic. | yes |
| `scripts/run_phase1_pilot_v1.py` | Explicit stage runner for the frozen Phase 1 pilot. | yes |
| `scripts/run_phase2_confirmatory_v1.py` | Stage-gated runner for preregistered held-out Phase 2. | yes |
| `scripts/run_phase3_scaling_v1.py` | Stage-gated command-line runner for Phase 3 empirical dilution scaling. | yes |
| `scripts/run_smoke.py` | Legacy entry point; see phase protocol and source. | yes |
| `scripts/validate_adaptive_dilution_bound.py` | Deterministic finite-case audit of adaptive hard-cap query bounds. | yes |
| `scripts/validate_explicit_rcsp_query_constructions.py` | Validate the v3 explicit-RCSP constructions and generate Figures 1--4. | yes |
| `scripts/validate_global_dilution_bound.py` | Run the offline finite-case and hybrid-step theorem validations. | no — may execute immediately |
| `scripts/validate_release.py` | Verify frozen paper results; optionally rebuild assets in a disposable copy. | yes |
| `scripts/validate_structure_advice_bound.py` | Finite posterior/advice stress test and Figures 5--7. | yes |
| `paper_scripts/audit_manuscript.py` | Audit the manuscript against frozen evidence and its self-contained package. | no — may execute immediately |
| `paper_scripts/build_paper_assets.py` | Build manuscript figures, tables, and compact supplements from frozen evidence. | no — may execute immediately |
| `paper_scripts/build_sncs_submission_final.py` | Build and independently reproduce the SN Computer Science submission bundle. | no — may execute immediately |
| `paper_scripts/build_sncs_submission_v3.py` | Build and validate the SN Computer Science v3 submission package. | no — may execute immediately |
| `paper_scripts/build_sncs_submission_v4.py` | Build the metadata-only SN Computer Science v4 submission derivative. | no — may execute immediately |
| `paper_scripts/package_overleaf.py` | Create and validate the clean, self-contained Overleaf archive. | no — may execute immediately |
| `paper_scripts/rebuild_publication_results.py` | Rebuild publication statistics and assets from frozen row-level evidence. | yes |
| `paper_scripts/reviewer_robustness/audit_paper_numbers.py` | Trace every reviewer-robustness manuscript headline to formal artifacts. | no — may execute immediately |
| `paper_scripts/reviewer_robustness/build_revision_assets.py` | Build manuscript assets for the frozen reviewer-robustness results. | yes |
| `paper_scripts/reviewer_robustness/compile_revision.py` | Compile the revised manuscript in an isolated clean directory and audit logs. | yes |
| `paper_scripts/reviewer_robustness/run_reviewer_robustness.py` | Resumable command-line entry point for isolated reviewer experiments. | yes |
| `paper_scripts/run_posthoc_finite_shot_endpoint.py` | Run post-hoc finite-shot sampling at frozen held-out O0/O3 endpoints. | no — may execute immediately |
| `paper_scripts/write_sncs_submission_audits.py` | Write final SN Computer Science delivery audits without changing science. | no — may execute immediately |
| `reproduction/reproduce_headlines.py` | Reconstruct all paper headline statistics from canonical result rows. | yes |
| `reproduction/reproduce_heldout.py` | Rebuild preregistered held-out inference and task-level win counts. | yes |
| `reproduction/reproduce_scaling_verdict.py` | Rebuild the resource-censored scaling verdict from canonical rows. | yes |
