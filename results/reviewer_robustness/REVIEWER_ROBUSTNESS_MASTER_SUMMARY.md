# Reviewer-robustness master summary

## Repository integrity

- Starting tree: intentionally dirty with 70 pre-existing status entries, captured before this pass. They were preserved.
- This pass added only the reviewer protocol, reviewer execution/analysis modules, one reviewer CLI, reviewer tests, and isolated reviewer results. No `overleaf/main.tex` or canonical result/manifests were edited by this pass.
- Canonical protection: **PASS**, 1399/1399 protected files, aggregate SHA-256 `0ef9ef8dc2a1f5cd062af2d8d1bef251a8d879e4139c95a23cf2225acacc5987`.
- Final tests: 178 passed, 0 failed, 0 skipped in 5.11 s; legacy suite independently re-run: 165 passed, 0 failed, 0 skipped in 4.51 s.
- Pre-existing modifications and this pass are separated by the provenance snapshot and `THIS_PASS_MODIFICATIONS.md`.
- Namespace decision: frozen reviewer manifests are under `results/reviewer_robustness/manifests/` and the protocol under `analysis/reviewer_robustness/`, rather than below the canonical `configs/` tree, because existing Phase-3 validation recursively interprets that tree as experiment configuration. This avoids contaminating frozen config enumeration; B1 and A3 also carry execution-local manifest copies.

## R0 — clustering and frozen inference

Discovery contains 56 tasks/10 base graphs; held-out contains 84/15; Phase 3 contains 180/30 with six tasks per graph. Existing Phase-2 H1/H2 inference already averages within graph, uses the 15 graphs as the sampling unit, performs whole-graph bootstrap/exact paired sign flips, and applies Holm correction to the frozen two-hypothesis family. **Existing confirmatory inference is already graph-level and does not require correction.** New task rows are descriptive; new uncertainty is based on paired equal-weight graph effects.

## B1 — depth × budget

B1 completed 432/432 trajectories and 1,296 genuine prefix checkpoint rows on 24 outcome-blind tasks/10 graphs, with no failed run. The 480-call single-trajectory design was licensed only after exact prefix equivalence against independently capped smoke runs.
At 120 calls, p4−p3 graph-mean G_feas is 0.7206 for O0 (CI [0.5785, 0.8623]) and 0.2021 for O3 (CI [0.1404, 0.2598]); all ten graph contrasts are positive in both arms. Thus p4 is not worse than p3 in this matrix.
From 120 to 480 calls, p4 graph-mean G_feas changes by 0.1031 (O0) and 0.0999 (O3): modest improvement, not a qualitative rescue.
- p2->p3 nested failures — 120: 30/144 (0.208); 240: 31/144 (0.215); 480: 38/144 (0.264).
- p3->p4 nested failures — 120: 45/144 (0.312); 240: 45/144 (0.312); 480: 47/144 (0.326).
Nested failure is higher for p3→p4 than p2→p3 and does not decrease with budget. This is not evidence of a barren plateau or intrinsic depth harm; it means the deeper terminal run sometimes fails to beat the simultaneously improving embedded shallower incumbent within the tested call budgets.

## A1 — optimizer robustness and mechanism separation

A1 completed all 2,016 runs (56 tasks × 3 optimizers × 2 objectives × 2 depths × 3 seeds), with 1,008 nested comparisons and no failures/timeouts.
- COBYLA: nested failures O0 28/168 and O3 38/168; 113 paired runs pass both diagnostics; PASS-only graph mean O3−O0 G_feas=0.7809, CI [0.5770, 0.9971].
- Nelder-Mead: nested failures O0 54/168 and O3 61/168; 72 paired runs pass both diagnostics; PASS-only graph mean O3−O0 G_feas=0.9271, CI [0.5796, 1.2473].
- SLSQP: nested failures O0 46/168 and O3 72/168; 70 paired runs pass both diagnostics; PASS-only graph mean O3−O0 G_feas=0.9938, CI [0.6096, 1.3458].
**Q1:** The frozen 29/168 observation is not mechanically redefined, but its mechanism is not COBYLA-only: both Nelder–Mead and SLSQP also show certified nested failures at the same call budget.
**Q2:** Yes. Within dual-PASS pairs, O0 has lower energy but lower feasibility than O3 in 103/113 COBYLA, 65/72 Nelder–Mead, and 58/70 SLSQP comparisons. Optimizer inadequacy and objective misalignment remain empirically distinct within this scope.

## A2 — CVaR alpha sensitivity

A2 completed the full 1,008-run discovery grid plus 216 explicitly post-hoc held-out sensitivity runs; no run failed. Alpha=0.10 remains the only historical confirmatory choice.
Discovery equal-weight graph means for G_feas are: alpha=.02 1.8982, .05 1.9503, .10 1.9889, .25 1.9560, .50 1.8445, 1.00 1.6867.
**Q3:** Alpha=0.10 lies in a reasonable robustness neighborhood: 0.05 and 0.25 are close, while 0.02 and 0.50 retain smaller advantages over alpha=1. The optimized response is non-monotone for 54/56 tasks, which was allowed rather than hidden.
**Q4:** Yes. Across all executed alpha=1 rows, max |CVaR−mean energy| is 2.420e-13.

## A3 — finite-shot estimation and training

The pre-existing all-held-out endpoint study (84 tasks/15 graphs, O0/O3, 1k/10k/100k, 20 repeats) passed its hashes and was reused without rerunning. It establishes fixed-theta estimator convergence only: P_feas ordering recovery is 0.948/0.993/1.000 at 1k/10k/100k.
The new alpha×shots grid adds 5,400 records (18 tasks/15 graphs, 50 repeats). At alpha=.10, pooled O0/O3 CVaR RMSE is 0.04839/0.01570/0.00486 and exact objective-order preservation is 0.901/0.967/0.992 at 1k/10k/100k. Alpha=.02 is costlier (RMSE 0.08217/0.02718/0.00813), supporting the expected sampling trade-off without assuming monotonic optimized performance.
- EXACT_CANONICAL: graph mean O3−O0 G_feas=0.3599, CI [0.1641, 0.5697], positive graphs 9/10.
- SHOT_10000: graph mean O3−O0 G_feas=0.1706, CI [-0.0106, 0.3862], positive graphs 8/10.
- SHOT_1000: graph mean O3−O0 G_feas=0.1246, CI [-0.0050, 0.3351], positive graphs 6/10.
**Q5:** Fixed-endpoint estimation is materially more stable by 10k shots and near-converged by 100k in this grid; 1k remains visibly noisy, especially for aggressive alpha=.02.
**Q6:** Exact training gives a robust positive ordering. Both 10k and 1k shot-trained means retain the sign, but their graph CIs include zero; graphwise consistency is 8/10 at 10k and 6/10 at 1k. The correct conclusion is mostly preserved at 10k and unstable/attenuated at 1k, not hardware readiness.

## B2 — classical context

The exact label-setting solver matches 140/140 frozen optima. Median solve time is 50.0 μs, p95 95.4 μs, maximum 188.1 μs; median/max generated labels are 13/30.
**Q10:** These instances are classically trivial by design. They support controlled exact-statevector attribution, not a quantum-advantage or wall-clock comparison.

## Direct answers to remaining depth questions

- **Q7:** p4 is not worse than p3 on terminal loss, G_feas, P_feas, or P_opt in the aggregate matrix; extra budget gives modest p4 improvement, so no 'recovery from worse' is required.
- **Q8:** Yes for the pooled diagnostic: p3→p4 failure rates exceed p2→p3 at every budget.
- **Q9:** No. Failure rates do not decrease from 120 to 480; they are flat/slightly higher.

## Paper-writable conclusion levels

| Claim | Level |
|---|---|
| optimizer failure is not COBYLA-specific | **SUPPORTED** |
| objective misalignment is distinct from certified optimizer failure | **SUPPORTED** |
| CVaR alpha=0.10 is not a brittle isolated choice | **SUPPORTED** |
| finite-shot estimator is stable at tested shot counts | **SUPPORTED_WITH_QUALIFICATION** |
| finite-shot training preserves O3-vs-O0 ordering | **MIXED** |
| depth degradation is optimization-budget dependent | **MIXED** |
| p=4 provides additional evidence beyond p=2/p=3 | **SUPPORTED** |
| current benchmark is classically easy by design | **SUPPORTED** |

## What strengthens, what limits

The optimizer and PASS-only analyses strengthen the two-mechanism attribution; the alpha scan strengthens the non-cherry-picking response; p4 removes the superficial concern that the paper stops at p3; and B2 makes the mechanistic/non-advantage framing explicit. Finite-shot training is the main limiting result: the positive point ordering is attenuated and graph-level uncertainty crosses zero. The budget ablation also weakens any simple story that more evaluations monotonically remove nested failures.

## Main text versus appendix

Main text should receive a compact optimizer/PASS-only result, one alpha-neighborhood sentence plus alpha=1 control, the qualified finite-shot-training result, the p4/budget nuance, and the classically-tractable context. Full matrices, per-optimizer accounting, all alpha curves, alpha×shots heatmap, classical counters, selection rules, and rebalancing provenance belong in the appendix/artifact. The frozen primary claims and numbers must not be replaced.

## Scope boundary and B3

This pass does not support hardware robustness, device/noise robustness, quantum advantage, claims about all constrained QAOA, or rankings of feasibility-preserving methods. B3 was **NOT TESTED**. It is not recommended for this revision unless a reviewer specifically requires a non-layered-network external-validity check; adding a new family now would broaden scope after all four core reviewer questions are already answered.

## Resource and completion ledger

Formal records: 9,412; complete 9,412; failed 0; timeout 0. Optimizer-objective statevector calls recorded by wrappers: 573,989. Sampled bitstrings in newly executed A3 studies: 255,412,000. Sum of run-record wall durations (parallel-worker time, not elapsed wall clock): 39.45 h.
The formal execution wall-clock envelope was 8.41 h, including inter-phase gaps and parallelism. CPU time was not instrumented and is not estimated.
Post-run diagnostic/plot statevector evaluations are not centrally instrumented and are excluded rather than estimated. The reused pre-existing endpoint study is also excluded from this pass's compute totals.

All planned core formal runs completed. The only failed event was the pre-formal alpha×shots smoke wiring check; it created no formal record, was preserved as evidence, fixed with a regression test, and passed deterministically on rerun. B3 is the only intentionally unexecuted optional phase.
