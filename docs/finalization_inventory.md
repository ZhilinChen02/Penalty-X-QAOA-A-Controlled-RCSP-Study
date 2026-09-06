# Publication-finalization inventory

Audit date: 2026-08-31 (Europe/Copenhagen)  
Baseline commit: `4d1111f3661f4b2df852eec2b382555a63e434d2`  
Baseline branch: `manuscript/overleaf-full-v1`  
Working branch: `paper-finalization-v3-sncs`

## Scope and freeze

This inventory covers the existing manuscript, *Feasible-Space Dilution and
Objective Alignment in Shallow QAOA: A Controlled RCSP Study*. The protected
scientific scope is the controlled RCSP benchmark, uniform-state full-space
Penalty-X QAOA, transverse-X mixer, globally normalized scale-controlled
diagonal Hamiltonian, exact-statevector experiments through primary depth
`p=3`, the four frozen objectives O0--O3, the discovery/held-out split, and the
resource-censored scaling study.

All files under the canonical result roots listed below are inputs, not edit
targets. Publication rebuilds write only to
`results/finalization_audit_v1/`, `overleaf/` presentation assets, and the
separate post-hoc directory if its preflight passes.

The worktree already contained a staged `KEY.txt` and untracked local SQLite
state files before finalization began. They are unrelated user files and are
excluded from this work.

## Manuscript and publication package

- Entry point: `overleaf/main.tex`.
- Main sections: `overleaf/sections/01_introduction.tex` through
  `overleaf/sections/12_conclusion.tex`.
- Appendices: `overleaf/appendices/appendix_*.tex`.
- Bibliography: `overleaf/references.bib` (21 entries at baseline).
- Numerical tables: `overleaf/tables/*.tex`.
- Publication figures: `overleaf/figures/*.pdf`.
- Supplementary release files: `overleaf/supplementary/*`.
- Package instructions: `overleaf/README.md`.

The SN Computer Science v3 submission is a deterministic journal-specific
derivative of this audited source:

- flat manuscript entry point:
  `submission/sn_computer_science_v3/main.tex`;
- official vendor files:
  `paper_assets/springer_nature_latex_2024_12/sn-jnl.cls` and
  `sn-mathphys-num.bst`;
- target-specific builder:
  `paper_scripts/build_sncs_submission_v3.py`;
- source and supplementary archives:
  `dist/Q-RouteDilution_SNCS_v3.zip` and
  `dist/Q-RouteDilution_SNCS_v3_supplementary.zip`;
- journal-requirements map: `docs/sncs_v3_journal_requirements.md`.

The v3 builder expands every section, appendix, and table into one `main.tex`;
it changes publication formatting and front/back matter only. It does not run
optimization or write to a canonical scientific result root.

## Canonical scientific result roots

| Root | Scientific role | Inference tier |
|---|---|---|
| `results/phase0/` | Original construction audit | Descriptive |
| `results/phase0_v2_dilution_stress/` | 140-task distinct-cardinality universe and Hamiltonian scale audit | Controlled/mechanistic |
| `results/phase1_pilot_v1/` | 56-task, 10-graph discovery pilot | Exploratory |
| `results/phase1_1_optimization_diagnostic/` | Nested-ansatz and continuation attribution | Mechanistic |
| `results/phase1_2_objective_alignment/` | O1/O2/O3 objective discovery | Exploratory |
| `results/phase2_confirmatory_v1/` | 84-task, 15-graph preregistered held-out evaluation | Confirmatory |
| `results/phase3_scaling_v1/` | Development/interpolation/extrapolation response; `m=22` resource censoring | Resource-censored scaling response |
| `results/theory_validation_v1/`--`v3/` | Finite-case checks and access-model audits | Formal-model support, not empirical confirmation |
| `results/synthesis_v1/` | Existing claim/evidence synthesis and protected-file inventory | Provenance |

The direct row-level inputs for publication reconstruction are:

- task universe: `results/phase0_v2_dilution_stress/task_characterization.csv`;
- optimizer attribution: `nested_ansatz_identity.csv`,
  `p3_random_vs_embedded.csv`, and
  `analysis/continuation_paired_comparison.csv` under the Phase 1.1 root;
- discovery objectives: `objective_results.csv`, `task_objective_summary.csv`,
  and `capacity_gap.csv` under the Phase 1.2 root;
- held-out objectives: `p3_objective_results.csv` under the Phase 2 root;
- scaling: `canonical_results.csv`, `base_graph_exponents.csv`,
  `resource_preflight.csv`, and `failure_census.csv` under the Phase 3 root.

Summary JSON files and pre-existing graph/task contrast CSVs are comparison
targets. The finalization rebuild does not use them as the source of headline
statistics.

## Frozen manifests, preregistrations, and configurations

- Universe manifests: `data/manifests/phase0_v2_dilution_stress.json`,
  `phase1_pilot_v1.json`, and `phase2_confirmatory_v1.json`.
- Scaling manifests: `data/manifests/phase3_scaling_v1/{development,
  interpolation_holdout,extrapolation_holdout,task_universe}.json` plus
  `manifest_hashes.json`.
- Held-out preregistration:
  `results/phase2_confirmatory_v1/PREREGISTRATION.md`.
- Scaling preregistration: identical copies at
  `results/phase3_scaling_v1/PREREGISTRATION.md` and
  `protocols/phase3_scaling_v1/PREREGISTRATION.md`.
- Frozen configurations: `configs/phase0_v2_dilution_stress.yaml`,
  `penalty_contract_v2_scale_controlled.yaml`, `phase1_pilot_v1.yaml`,
  `phase1_1_optimization_diagnostic.yaml`,
  `phase1_2_objective_alignment.yaml`, `phase2_confirmatory_v1.yaml`, and
  `phase3_scaling_v1.yaml`.
- Recorded identity/hash files include the Phase 1.1 and Phase 1.2
  `immutable_evidence_sha256.json` files, the Phase 2
  `execution_manifest_snapshot.json`, the Phase 3 execution/model freezes,
  `data/manifests/phase3_scaling_v1/manifest_hashes.json`, and
  `results/synthesis_v1/protected_hashes_before.sha256`.

At baseline, all 49 files covered by the Phase 1.1 immutable manifest, all 93
covered by the Phase 1.2 manifest, and all 117 historical files covered by the
Phase 2 execution snapshot matched their stored SHA-256 values.

## Claim/evidence maps

- Primary map: `results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv`.
- Stage map: `results/synthesis_v1/EVIDENCE_STAGE_MAP.md`.
- Input inventory: `results/synthesis_v1/SYNTHESIS_INPUT_INVENTORY.csv`.
- Manuscript claim use: `paper_audit/claim_usage.csv`.
- Manuscript numeric trace: `paper_audit/numeric_verification.csv`.
- Figure/table provenance: `paper_audit/figure_manifest.csv` and
  `paper_audit/table_manifest.csv`.
- Released compact copies: `overleaf/supplementary/claim_evidence_summary.csv`
  and `numeric_audit.csv`.

The baseline manuscript audit contains 178 traced numerical uses (111 exact,
67 correctly rounded), 63 scoped claim uses, and no mismatch or unsupported
row. The new reconstruction will re-evaluate the requested headline family
from row-level evidence before prose is changed.

## Evidence stage for manuscript numbers

| Manuscript quantity | Direct evidence stage |
|---|---|
| 140 tasks and zero duplicate primary feasible sets | Phase 0 v2 task characterization |
| 168/168 identity, 29/168 certified failures, 29/29 and 27/29 continuation results, 82/168 mismatch | Phase 1.1 optimizer diagnostic |
| 56 tasks, 10 graphs, O3 alpha 0.10, capacity-gap closure | Phase 1.2 discovery |
| H1/H2 effects, bounds, exact sign flips, Holm adjustment, 80/84 and 79/84 | Phase 2 held-out rows plus frozen statistical protocol |
| Mean `eta` at `m=20`, ordering reversal, `m=22` censoring | Phase 3 exponent rows, resource preflight, and failure census |
| Representation and access-model scope claims | Theory v3 documents and validation rows |
| Diagnostic decompositions not in the primary family | Explicitly post-hoc/descriptive Phase 1.1, Phase 2, or Phase 3 analysis |

## Figure, table, and regeneration sources

- `paper_scripts/build_paper_assets.py` rebuilds manuscript Figures 1--10,
  numerical tables, and compact supplementary manifests from canonical rows.
- `paper_scripts/audit_manuscript.py` performs numeric/claim and static LaTeX
  checks.
- `paper_scripts/package_overleaf.py` builds and validates the Overleaf archive.
- `paper_scripts/build_sncs_submission_v3.py` creates the flat SN Computer
  Science source ZIP, the separate supplementary ZIP, journal metadata, and
  target-specific validation report without rerunning an experiment.
- `scripts/build_synthesis_assets.py` created the existing synthesis matrices.
- Phase-specific runners and analysis modules under `scripts/` and
  `src/qroute_dilution/` can regenerate historical stage analyses, but several
  also run optimization and therefore are **not** publication-rebuild entry
  points.
- Theory validation asset generators are
  `scripts/validate_global_dilution_bound.py`,
  `validate_adaptive_dilution_bound.py`,
  `validate_explicit_rcsp_query_constructions.py`,
  `validate_structure_advice_bound.py`,
  `run_grover_tightness_validation.py`,
  `build_structure_cost_matrix.py`, and `audit_rcsp_bridge.py`.
- The finalization entry point will be
  `paper_scripts/rebuild_publication_results.py`; it must never invoke an
  optimizer.

## Tests and QA

The baseline repository has 40 tracked pytest files under `tests/`, covering
graph/RCSP construction, representation, Penalty-X metrics, optimizer
diagnostics, held-out inference, scaling, Hamiltonian scale, and theory access
models. The existing manuscript audit reports balanced braces/environments,
no missing or duplicate labels, no unresolved citations, and no missing
figures. A TeX compiler was unavailable during that earlier audit; finalization
will check the current environment again.

## Supplementary and human-review material

- Existing reviewer package: `review_package/`.
- Existing theory/provenance documentation: `docs/theory/`,
  `docs/manuscript/`, and `docs/synthesis/`.
- Independent human proof review, independent prior-art judgment, independent
  external reproduction, affiliations, acknowledgments, funding, competing
  interests, and DOI/repository release remain human-only open items. The
  journal choice and base formatting are now fixed to SN Computer Science v3;
  final author metadata and portal-render approval remain open.

## Audit flags before reconstruction

1. **Canonical task-payload availability.** All 140 manifest-referenced JSON
   files under `data/tasks/phase0_v2_dilution_stress/` are absent because that
   path is git-ignored. The deterministic generator, master seed, generator
   source, task IDs, graph-content IDs, budgets, and characterization rows are
   present. No canonical path will be repopulated. An in-memory, outcome-blind
   regeneration must match every manifest and characterization identity before
   endpoint sampling can proceed.
2. **Finite-shot status.** Frozen O0/O3 terminal parameter vectors are present
   for all 84 held-out tasks in `p3_objective_results.csv`; admissibility still
   depends on the task/Hamiltonian reconstruction check above.
3. **Theory priority.** The baseline manuscript already says that the
   posterior/advice formulation is novelty-unresolved. This remains an open
   human-review item, not a supported novelty claim.
4. **External reproduction.** No independent external reproduction has yet
   occurred. The manuscript must continue to say it is pending.
5. **Untraceable manuscript claims.** The baseline audit flags none, but this
   status is provisional until the independent row-level rebuild and the
   post-rewrite audit both pass.
