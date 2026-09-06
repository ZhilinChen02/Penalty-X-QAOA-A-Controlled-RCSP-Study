# Phase 2 Preregistration — Held-Out CVaR Objective Confirmation

Evidence identity: `PREREGISTERED_HELDOUT_OBJECTIVE_CONFIRMATION`.

This document fixes the Phase 2 scientific and execution rules before any O0/O2/O3 optimization is run on the held-out tasks. Phase 1.2 is discovery evidence only and will not be pooled with Phase 2 inference.

## Hypotheses and exact endpoints

For task `t`, `G_feas(t,o) = log10(P_feas(t,o) / feasible_state_fraction(t))`. The independent analysis unit is the base graph. For each graph and objective, the task values are averaged over every planned dilution level. Each of the 15 held-out graphs then receives equal weight.

H1 tests whether the arithmetic mean across graphs of `Delta1_graph = mean_levels G_feas(O3) - mean_levels G_feas(O0)` is greater than zero.

H2 tests whether CVaR is non-inferior to the statevector mechanistic capacity control. It uses `Delta2_graph = mean_levels G_feas(O3) - mean_levels G_feas(O2)` and the frozen non-inferiority margin `-0.10` decades. The operational test is whether `Delta2_graph + 0.10` has positive grouped evidence. O2 is a `MECHANISTIC_CAPACITY_CONTROL`, not a deployment-ready objective, and uses feasibility membership but neither optimum identity nor `P_opt`.

The population location estimand for both hypotheses is the arithmetic mean of the 15 graph-level paired contrasts.

## Inference and multiplicity

The primary family contains exactly H1 and H2 with one-sided family alpha 0.05. Raw p-values use exact cluster-level sign flips of the 15 graph contrasts: all `2^15 = 32,768` sign assignments are enumerated, and the p-value is the fraction whose mean is at least the observed mean. H2 applies this procedure to `Delta2 + 0.10`.

The two raw p-values are adjusted with Holm's step-down rule. In parallel, 10,000 base-graph bootstrap samples are drawn with replacement using NumPy `default_rng(20261017)`. The one-sided 95% lower confidence bound is the fifth percentile of the bootstrap mean. Individual task rows are never bootstrapped.

H1 passes only if its Holm-adjusted p-value is below 0.05 and its grouped-bootstrap lower bound is greater than zero. H2 passes only if its Holm-adjusted p-value is below 0.05 and the grouped-bootstrap lower bound for unshifted `Delta2` is greater than `-0.10`. The inference implementation and pass rule will not change after held-out results are observed.

If any planned task lacks finite, scientifically valid O0/O2/O3 results, that task remains in the denominator and is marked ineligible. A graph enters the primary inference only when all its planned levels have finite paired results for all three arms. Missing levels are not replaced. Any incomplete graph makes the phase status `PARTIAL`; formal claims requiring all 15 graphs will not be made as if N remained 15.

## Power preflight

Power is estimated only from the 10 Phase-1.2 discovery base graphs. Their bivariate `(Delta1, Delta2)` mean and covariance parameterize a bivariate normal simulation of 100,000 experiments with 15 graphs, using seed `20260828`. Each simulation uses one-sided one-sample t p-values for H1 and shifted H2 and applies the full two-hypothesis Holm family. This is a planning approximation, distinct from the exact formal inference.

Minimum projected power is 0.80 and preferred power is 0.90 for each hypothesis after Holm. If either is below 0.80, execution stops for user direction and can continue only as `PREREGISTERED_HELDOUT_REPLICATION`; the effect, margin, task universe, and hypotheses will not be altered.

## Held-out set and stopping rules

The held-out manifest is derived mechanically as the base-graph and task set difference between the immutable 140-task v2 universe and the 56-task discovery manifest. It must contain 84 tasks on 15 complete base-graph trajectories with zero discovery overlap. Any nonzero overlap stops execution.

Held-out optimization cannot begin until code tests pass, the discovery-only two-task end-to-end preflight passes, the power gate is recorded, and the config, manifest, preregistration, universe manifest, penalty contract, and immutable predecessors have been hashed. A failed preflight, hash change, overlap, denominator mismatch, or theoretical energy-separation failure stops execution. There are no result-dependent extensions, bad-cell reruns, replacement seeds, alpha searches, or additional held-out tasks.

## Algorithm, initialization, and budgets

Every held-out task first receives exactly three p=2 mean-energy COBYLA preparations from deterministic seeds `1103`, `2207`, and `3301`, using the original Phase-1 maximum budget of 120 optimizer evaluations, the same stopping rule, and no parameter bounds. Selection uses minimum finite `objective_final` only, with ascending seed as a tie-break. `P_feas`, `P_opt`, and `G_feas` never enter selection.

The chosen parameters `[gamma1,gamma2,beta1,beta2]` are embedded as `[gamma1,gamma2,0,beta1,beta2,0]`. This identical point initializes O0 mean energy, O2 exact feasibility capacity control, and O3 exact weighted CVaR-0.10. Each p=3 arm receives a maximum of 240 COBYLA evaluations, resolved as twice the frozen original Phase-1 p=3 budget. The cost-phase Hamiltonian remains the globally normalized mean-energy Hamiltonian for all arms; only the classical training loss differs. Fractional probability at the CVaR cutoff is exact. No O1, alpha=0.25, Warm-start, different mixer, alternate ansatz, penalty tuning, or per-task hyperparameter tuning is permitted.

Planned optimized denominator: 252 p=2 preparations plus 252 p=3 comparisons, for 504 runs.

## Failure semantics

Every planned row is retained. Allowed terminal labels are `SUCCESS`, `TIMEOUT`, `OOM`, `OPTIMIZER_FAILURE`, `NUMERICAL_FAILURE`, `ZERO_P_FEAS`, `ZERO_P_OPT`, and `RESOURCE_CENSORED`. Zero-probability states are not silently discarded. When no p=2 preparation provides a finite objective, all three p=3 cells are retained as `RESOURCE_CENSORED`. No failure is replaced or rerun based on its result. Paired task and complete-graph eligibility are explicit output fields.

## Secondary analyses

Secondary endpoints are task-level capacity and residual gaps, numerically stable unbounded gap closure (denominator greater than `1e-6` decades), within-graph dilution slopes, routing quality including `P_opt`, `P_opt_given_feasible`, and `E[C|feasible]`, objective alignment, and the frozen CVaR-tail mechanism audit. These endpoints are not added to the primary multiplicity family. No continuous boundary, critical threshold, or phase transition will be inferred.

## Allowed and prohibited claims

If H1 and H2 pass, the allowed conclusion is that on held-out tasks CVaR improves feasibility concentration over mean energy and is non-inferior within 0.10 decades to the statevector capacity control on the graph-level endpoint. If only H1 passes, only improvement over mean energy is claimed. If H1 fails, the discovery improvement is not confirmed; H2 alone cannot support an improvement claim. Heterogeneity is reported as structure-dependent replication.

Regardless of outcome, this phase cannot claim quantum advantage, universal dilution solution, a critical dilution threshold, a phase transition, or general QAOA success/failure on RCSP.
