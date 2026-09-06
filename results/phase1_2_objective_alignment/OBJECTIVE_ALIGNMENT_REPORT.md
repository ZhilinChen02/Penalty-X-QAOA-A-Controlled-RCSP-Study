# Phase 1.2 — Objective Alignment and Feasibility-Capacity Diagnostic

## Evidence contract

This is a new objective-design diagnostic over exactly the frozen 56 Phase-1 pilot tasks. It uses the same scale-controlled penalties, global normalization by 172, p=3 Penalty-X statevector ansatz, validator, unbounded periodic phase parameters, objective-selected p=2 seed, embedded zero third layer, COBYLA optimizer class, and matched 240-evaluation budget. The cost-phase Hamiltonian remains the frozen normalized mean-energy Hamiltonian in every arm; only the classical training loss changes.

O0 reuses all 56 exact Phase-1.1 continuation-B2 cells. O1–O3 comprise 168 new cells. O2 is labeled `STATEVECTOR_MECHANISTIC_CONTROL`; it is not a deployment-ready objective and uses feasibility membership only, never the optimum or `p_opt`. O1 is a mechanistic feasibility surrogate, not a complete routing objective. No 140-task optimization expansion, Warm-start arm, shot sampling, result-based rerun, or raw-statevector persistence occurred.

## FEASIBILITY_PENALTY_BOUND

For every one of the 140 frozen v2 tasks, feasible states have total controlled penalty zero, every infeasible basis state has `P_total >= 1`, and every basis state has `P_total <= 4`. Therefore, pointwise bounds integrated against any probability distribution give

`1 - P_feas <= E[P_total] <= 4 * (1 - P_feas)`.

All 140 basis-state task audits, 140 deterministic Haar-distribution audits, and 224 produced optimization-state audits passed. This explains why O1 is more directly aligned with feasible mass than O0, but it does **not** make expected-penalty minimization equivalent to maximizing `P_feas`: O1 also weights violation severity within the infeasible sector.

## CVaR energy-separation audit

Strict `min(infeasible energy) > max(feasible energy)` separation passed for 140/140 tasks. Consequently, if `P_feas >= alpha`, the lowest-energy alpha tail is entirely feasible; if `P_feas < alpha`, some infeasible mass is necessary. Exact weighted CVaR uses fractional probability at the cutoff. The per-result condition passed for 56/56 O3 cells; 14/56 final O3 tails were fully feasible. This condition does not guarantee that CVaR maximizes `P_feas`, and its direct feasibility pressure can weaken once feasible mass exceeds alpha.

## Main objective comparison

| Arm | Median P_feas | Median G_feas | Median P_opt | Median P_opt given feasible | Median E[C given feasible] | Median kappa |
|---|---:|---:|---:|---:|---:|---:|
| O0 Mean Energy | 0.0216781 | 2.1161 | 0.00956306 | 0.437314 | 13.0425 | 0.0777 |
| O1 Expected Penalty | 0.0233574 | 2.1728 | 0.00950921 | 0.434727 | 13.0131 | 0.0457 |
| O2 Exact Feasibility | 0.0399154 | 2.3209 | 0.0164578 | 0.434474 | 12.9871 | 0.1885 |
| O3 CVaR-0.10 | 0.0427875 | 2.4275 | 0.0166965 | 0.408153 | 13.0241 | 0.1726 |

The aggregate Spearman `(D, P_feas / G_feas / P_opt)` triples are O0 `(-0.872, 0.901, -0.896)`, O1 `(-0.897, 0.909, -0.918)`, O2 `(-0.891, 0.965, -0.848)`, and O3 `(-0.860, 0.968, -0.876)`. Full within-base slopes, R2 values, D ranges, level counts, IQRs, ranges, and sign counts are in `compensation_by_objective.csv`.

## Capacity, surrogate, and routing-quality gaps

The median O2–O0 feasibility-capacity gap is 0.2193 decades (IQR 0.2928); the median P_feas gap is 0.0152188. The corresponding residual G gaps are 0.2417 for O1 and 0.0069 for O3. The median O2–O0 P_opt gap is 0.00489873, so feasibility recovery is not treated as universal routing superiority.

The O2–O0 capacity gap increases with dilution (Spearman rho 0.662, n=56). The residual O2–O1 gap also increases with dilution (rho 0.672), whereas the O2–O3 residual does not (rho -0.184).

O1 improved its own expected-penalty loss in 56/56 cells, so its gap is not explained by simple terminal regression. In 51/56 paired tasks, O1 had lower expected penalty than O2 but also lower `P_feas`. That direction is direct evidence that severity weighting within `P_total` can prefer lower-severity infeasible mass; it is consistent with remaining landscape effects and flow/resource allocation, but this phase does not identify a unique causal decomposition or tune their weights.

Relative to O0, O2 improved `P_feas` on 53/56 tasks and `P_opt` on 50/56. O3 improved them on 50/56 and 51/56, respectively. For O3, `P_opt_given_feasible` improved / was unchanged / worsened on 27/10/19 tasks, while conditional route cost improved / was unchanged / worsened on 26/10/20. Thus the route-quality response is heterogeneous rather than collapsed into a feasibility-only ranking.

With the thresholds frozen before execution (0.10-decade material gap and 50% substantial closure), tags occurred on 56 tasks as follows: OBJECTIVE_LIMITED 44, CAPACITY_LIMITED 7, PENALTY_SURROGATE_SUCCESS 2, and CVAR_PARTIAL_ALIGNMENT 7. Tags are descriptive, nonexclusive, and continuous gaps remain canonical.

On the descriptive two-axis Pareto view maximizing both `P_feas` and `P_opt_given_feasible`, nondominated counts were O0 15, O1 20, O2 38, and O3 39. No weighted score was constructed.

## Scientific verdict

**CVAR_PARTIALLY_CLOSES_GAP**

This verdict is specific to the fixed 56-task, p=3, exact-statevector diagnostic and does not establish a universally superior objective.

## Next recommendation

**PREREGISTER_FEASIBILITY_ALIGNED_PHASE2**

This recommendation is recorded only and was not executed. The optional alpha=0.25 sensitivity and response-slice extension were not enabled in the frozen configuration.

## Verification

- Test result: `60 passed in 1.95s`
- Historical predecessor hashes: verified after analysis
- Required objective cells: 224/224 successful (56 reused O0 + 168 new O1/O2/O3)
- Raw statevectors: not persisted
