# Final Scientific Audit and Paper Revision Summary

Date: 2026-09-04

## Final status

The final scientific audit and manuscript revision are complete. The revision
integrates the completed B1/A1/A2/A3/B2 evidence without changing the frozen
56-task discovery assignment, 84-task held-out assignment, alpha=0.10 choice,
H1/H2 family, canonical numerical results, or Phase-3 conclusions. B3 and all
hardware-noise or structured-mixer experiments remain unexecuted by design.

The revised manuscript is `overleaf/main.tex`. A clean compiled copy is at
`results/reviewer_robustness/paper_revision/Q-RouteDilution_reviewer_robustness.pdf`.

## Final sanity audits

### S1: alpha=1 versus matched O0

Status: **PASS_WITH_PROTOCOL_QUALIFICATION**.

- Across all 222 executed alpha=1 rows, the maximum direct discrepancy between
  exact weighted CVaR at alpha=1 and mean energy is
  `2.4202861936828413e-13`.
- The closest historical O0 comparison contains 168 discovery cells. Task,
  depth, seed, embedded-p2 initialization, optimizer name, nominal 120-call
  budget, `rhobeg=0.5`, and `catol=1e-8` match; the maximum initial-objective
  discrepancy is `2.0228263508670352e-13`.
- The execution protocol is not fully identical: the historical run used the
  Phase-1.1 wrapper with SciPy 1.17.0, whereas A2 used the strict reviewer
  wrapper with SciPy 1.18.0. Actual nfev matches in 164/168 cells, and complete
  evaluation trajectories were not saved.
- Terminal theta is not equal within `1e-12` in any of the 168 pairs. The
  median/maximum absolute differences are 0.190695/1.63224 for theta,
  0.0091399/0.31204 for terminal objective, 0.000782593/0.0417349 for
  P_feas, 0.0347145/0.424697 for G_feas, and 0.000378762/0.0333827 for P_opt.

The licensed manuscript statement is therefore: at alpha=1, the CVaR
objective numerically recovers mean energy to machine precision. The revision
does not claim that the optimization trajectories or endpoints must coincide.

Artifacts:

- `results/reviewer_robustness/final_audits/ALPHA1_O0_EQUIVALENCE_AUDIT.md`
- `results/reviewer_robustness/final_audits/alpha1_o0_equivalence.csv`

### S2: nested failures versus evaluation budget

Status: **PASS**.

- All 16 structural checks of nfev accounting, prefix semantics, task/seed
  mapping, objective mapping, regret direction, tolerance, and zero-angle
  nesting passed.
- The B1 checkpoints are best evaluated incumbents within genuine
  120/240/480-call prefixes of one verified 480-call trajectory. They are not
  reconstructed continuations or presumed last iterates.
- Twenty-four deterministically selected cases cover every transition x
  budget x objective x PASS/FAIL cell. All classifications agree on exact
  recomputation.
- Maximum recomputation errors are `1.5543122344752192e-15` for the deeper
  objective, `2.220446049250313e-16` for the embedded objective, and
  `1.4155343563970746e-15` for signed regret. The selected embedding-identity
  error is zero at stored precision.
- Reconfirmed pooled failure rates are 20.8%, 21.5%, and 26.4% for p2->p3,
  and 31.2%, 31.2%, and 32.6% for p3->p4, at 120, 240, and 480 calls.

The frozen interpretation is: increasing the tested classical evaluation
budget did not monotonically reduce certified nested-ansatz failures. This is
limited to the frozen 24-task subset, COBYLA, O0/O3, p=2/3/4, the three fixed
seeds, and the tested budgets; it does not imply that more optimization never
helps.

Artifacts:

- `results/reviewer_robustness/final_audits/DEPTH_BUDGET_NESTED_AUDIT.md`
- `results/reviewer_robustness/final_audits/nested_audit_cases.csv`

## Manuscript revision

### Sections changed

- **Abstract:** preserves the frozen held-out and Phase-3 story, then adds only
  the cross-optimizer diagnostic, local alpha robustness, and qualified
  finite-shot boundary.
- **Introduction:** separates representation dilution, scale, optimizer
  inadequacy, objective misalignment, depth--budget interaction, and sampling
  variation; updates the contribution list; states explicitly that the
  benchmark is classically tractable and mechanistic rather than an advantage
  benchmark.
- **Problem definition:** distinguishes the exact primary experiment from the
  post-hoc finite-sampling studies and excludes device noise.
- **Methods:** adds a compact robustness/sensitivity protocol covering A1,
  A2, A3, B1, and B2; records graph-level inference, actual-call accounting,
  prefix semantics, exact final-state evaluation, and the role of the exact
  classical solver.
- **Optimizer attribution:** adds the cross-optimizer dual-PASS mechanism
  analysis and the p=2/3/4 by 120/240/480-call ablation.
- **Objective alignment:** adds the post-hoc alpha scan, the 54/56
  non-monotonicity result, and the qualified alpha=1 endpoint audit.
- **Held-out results:** adds fixed-endpoint sampling and end-to-end
  finite-shot-training results while preserving the original alpha=0.10
  confirmatory family.
- **Scaling:** changes no scientific result; only the surrounding depth claim
  is narrowed and PDF bookmark formatting is repaired.
- **Related work, discussion, limitations, conclusion:** replace any simple
  “deeper is worse” story with the observed separation between representational
  opportunity, optimizer success, and terminal feasible mass. They also state
  the finite-shot and classical-scope boundaries.
- **Theory:** no theorem is expanded. The existing statement that a
  membership-only lower bound does not lower-bound the rich-energy CVaR
  experiment remains intact.

### Claims narrowed or removed

- The original p2-to-p3 terminal regression is no longer presented as evidence
  that deeper QAOA is intrinsically worse. It certifies optimizer inadequacy
  only for the identified runs.
- Increased evaluation budget is not described as a monotonic repair: it did
  not monotonically reduce the tested nested-failure rates.
- CVaR is described as substantial compensation under exact training and as
  locally robust around alpha=0.10, not as a universally superior objective.
- Fixed-endpoint sampling stability is not conflated with finite-shot
  retraining. The latter is described as suggestive but mixed.
- No hardware readiness, device/noise robustness, broad constrained-QAOA
  limitation, structured-mixer ranking, or quantum-advantage claim is made.

## Numerical headlines incorporated

### Optimizer robustness

- COBYLA O0/O3 failures: 28/168 and 38/168; dual-PASS effect CI
  `[0.5770,0.9971]`; O0 lower-energy/lower-feasibility pairs 103/113.
- Nelder--Mead: 54/168 and 61/168; CI `[0.5796,1.2473]`; 65/72 pairs.
- SLSQP: 46/168 and 72/168; CI `[0.6096,1.3458]`; 58/70 pairs.
- The historical 29/168 observation remains frozen. The post-hoc COBYLA/O0
  count is explicitly identified as a separate strict-cap rerun, not a
  replacement.

### Alpha sensitivity

Discovery equal-weight graph means of G_feas for alpha
`.02/.05/.10/.25/.50/1.00` are
`1.8982/1.9503/1.9889/1.9560/1.8445/1.6867`. The nearby 0.05 and 0.25
responses support a local robustness neighborhood, while 54/56 task responses
are non-monotone. Every non-primary held-out alpha remains explicitly marked
`POST_HOC_SENSITIVITY`.

### Depth and budget

At 120 calls, graph-mean p4-minus-p3 G_feas is +0.7206 for O0 and +0.2021
for O3, positive on 10/10 graphs in both arms. Nested failures are more common
for p3->p4 than p2->p3, but terminal p4 feasibility is not worse in the tested
matrix. Optimizer success and terminal feasible mass therefore do not move
together monotonically.

### Finite shots

- Fixed-endpoint P_feas ordering recovery is 94.8%, 99.3%, and 100.0% at
  1k, 10k, and 100k shots.
- The mean of separately computed O0 and O3 alpha=.10 CVaR RMSE values is
  0.04839, 0.01570, and 0.00486. This wording avoids mislabelling the
  arithmetic mean of two objective-specific RMSEs as one pooled RMSE.
- Exact-trained O3-minus-O0 G_feas is 0.3599, CI `[0.1641,0.5697]`, with
  9/10 positive graphs.
- At 10k shots per evaluation it is 0.1706, CI `[-0.0106,0.3862]`, 8/10;
  at 1k it is 0.1246, CI `[-0.0050,0.3351]`, 6/10. Both finite-shot-training
  intervals cross zero.

### Classical context

The exact label-setting implementation matches 140/140 frozen optima. Median,
p95, and maximum per-task median solve times are 50.0, 95.4, and 188.1
microseconds; generated labels have median/maximum 13/30. These measurements
are descriptive context, not a simulator-versus-hardware comparison.

## Paper-writable conclusion levels

| Claim | Final level | Manuscript treatment |
|---|---|---|
| Optimizer failure is not COBYLA-specific | **SUPPORTED** | Main text and Table R1 |
| Objective misalignment is distinct from certified optimizer failure | **SUPPORTED** | Main text; dual-PASS analysis |
| Alpha=0.10 is not a brittle isolated choice | **SUPPORTED_WITH_QUALIFICATION** | Main text; local 0.05--0.25 neighborhood only |
| Fixed-endpoint finite-shot estimation is stable at tested counts | **SUPPORTED_WITH_QUALIFICATION** | Main text; strongest by 10k--100k |
| Finite-shot training preserves the O3--O0 ordering | **MIXED** | Positive point effects, intervals crossing zero |
| Depth degradation is optimization-budget dependent | **MIXED** | Simple degradation story rejected; budget does not monotonically repair failures |
| p=4 provides evidence beyond p=2/p=3 | **SUPPORTED_WITH_QUALIFICATION** | Tested 24-task COBYLA subset only |
| The benchmark is classically easy by design | **SUPPORTED** | Main scope statement and appendix context |

## Main text versus appendix

Main text receives one optimizer table, one depth--budget figure, compact alpha
and finite-shot result paragraphs, and the classical-scope sentence. The full
protocol matrix, optimizer figure, six-alpha table/figure, depth--budget table,
alpha-by-shots heat map, finite-shot-training table/figure, classical counters,
and audit qualifications are collected in the new reviewer-robustness
appendix. This keeps the original exact-statevector mechanism study central.

New manuscript assets:

- `overleaf/figures/fig12_reviewer_depth_budget.pdf`
- `overleaf/figures/fig13_reviewer_optimizer_robustness.pdf`
- `overleaf/figures/fig14_reviewer_alpha_sensitivity.pdf`
- `overleaf/figures/fig15_reviewer_finite_shot_training.pdf`
- `overleaf/figures/fig16_reviewer_alpha_shots.pdf`
- `overleaf/tables/table08_reviewer_optimizer.tex`
- `overleaf/tables/tableS6_reviewer_protocols.tex`
- `overleaf/tables/tableS7_depth_budget.tex`
- `overleaf/tables/tableS8_alpha_sensitivity.tex`
- `overleaf/tables/tableS9_finite_shot_training.tex`
- `overleaf/tables/tableS10_classical_context.tex`
- `overleaf/appendices/appendix_reviewer_robustness.tex`

## Repository integrity and provenance

- The intentionally dirty starting tree was captured before the original
  robustness pass in
  `results/reviewer_robustness/provenance/preexisting_git_status.txt` and
  `preexisting_git_diff_stat.txt`; all pre-existing tracked and untracked work
  remains present.
- A second source-level snapshot was taken immediately before manuscript
  revision at
  `results/reviewer_robustness/paper_revision/pre_revision_overleaf_snapshot.json`.
  It records 33 source files and aggregate SHA-256
  `359c4ad3cf5efe6a5ff1851149576c7fdc662fc3ce268c9a768804f0e07d2cab`.
- Final canonical protection check: **PASS**, 1399/1399 files unchanged.
  Expected and observed aggregate SHA-256 are both
  `0ef9ef8dc2a1f5cd062af2d8d1bef251a8d879e4139c95a23cf2225acacc5987`.
- No frozen result, task assignment, seed, manifest, H1/H2 definition,
  headline statistic, m=20 reversal, or m=22 censoring record was overwritten.
- `git diff --check` passes. No destructive Git or filesystem command was used.

Files changed relative to the pre-revision source snapshot are `main.tex`,
`README.md`, the artifact/optimization/statistics appendices, Sections 1--7,
Sections 9--12, and the related-work table. Section 8 (the theory source) and
the bibliography are unchanged relative to that snapshot. The new reviewer
appendix, tables, and Figures 12--16 are additive. The exact pre-existing
versus revision boundary is preserved by the two snapshots above;
pre-existing figure, bibliography, audit, submission, and database changes
were not overwritten.

Exact manuscript-source files changed in this revision:

- `overleaf/README.md`
- `overleaf/main.tex`
- `overleaf/appendices/appendix_artifact.tex`
- `overleaf/appendices/appendix_optimization.tex`
- `overleaf/appendices/appendix_statistics.tex`
- `overleaf/sections/01_introduction.tex`
- `overleaf/sections/02_problem.tex`
- `overleaf/sections/03_methods.tex`
- `overleaf/sections/04_optimizer_attribution.tex`
- `overleaf/sections/05_objective_alignment.tex`
- `overleaf/sections/06_heldout_results.tex`
- `overleaf/sections/07_scaling.tex`
- `overleaf/sections/09_related_work.tex`
- `overleaf/sections/10_discussion.tex`
- `overleaf/sections/11_limitations.tex`
- `overleaf/sections/12_conclusion.tex`
- `overleaf/tables/table07_related_work.tex`

Exact manuscript files added in this revision are the appendix, five figures,
and six tables listed under “New manuscript assets” above.

Final-audit and revision support added in this stage:

- `src/qroute_dilution/reviewer_robustness/final_audits.py`
- `paper_scripts/reviewer_robustness/run_final_scientific_audits.py`
- `paper_scripts/reviewer_robustness/build_revision_assets.py`
- `paper_scripts/reviewer_robustness/audit_paper_numbers.py`
- `paper_scripts/reviewer_robustness/compile_revision.py`

## Validation

- Full test suite: **178 passed, 0 failed, 0 skipped**. The pre-robustness
  baseline was 165 passed.
- Paper-number audit: **PASS, 55/55 checks**. Every new displayed manuscript
  number is recomputed from and found in the formal result artifacts.
- Static Overleaf-tree validation: **PASS**; no missing inputs, figures,
  references, or citations, and no environment mismatch.
- Clean isolated Tectonic build: **PASS**, 55 pages.
- The main article text ends on page 31 and the appendices begin on page 32;
  the full robustness matrices remain outside the main narrative.
- Undefined references: 0; undefined citations: 0; duplicate labels: 0;
  overfull boxes: 0; bookmark warnings: 0; missing characters: 0.
- Eight non-fatal underfull-box warnings remain in compact tables/path listings;
  they do not hide content or change scientific meaning.
- Rendered main-text and appendix pages containing the new tables and figures
  were visually spot-checked for ordering, legibility, and clipping.
- Final PDF SHA-256:
  `cc33d9c6e05f8f1895bc023d5b1c5cef64ba5dc56be8f68d021960f79f4136e1`.
- Final TeX-source aggregate SHA-256:
  `911bd60e9408a47de1bdc023cc45d30a9039e0865fbbc2e1a22ca63fb18ceabf`.

Validation artifacts:

- `results/reviewer_robustness/PAPER_NUMBER_AUDIT.md`
- `results/reviewer_robustness/paper_revision/MANUSCRIPT_BUILD_AUDIT.md`
- `results/reviewer_robustness/paper_revision/manuscript_build_audit.json`
- `results/reviewer_robustness/paper_revision/main.log`

## Final scientific boundary

The revision supports a controlled exact-statevector mechanism study in which
representation dilution, optimizer inadequacy, objective misalignment,
depth--budget behavior, and finite-sampling effects are separately stressed.
It does not support hardware or device-noise robustness, quantum advantage,
universal CVaR superiority, a general constrained-QAOA limitation, or a
ranking against feasibility-preserving methods. External-validity B3 is
**NOT_TESTED** and is not recommended for this revision unless specifically
requested by a reviewer.
