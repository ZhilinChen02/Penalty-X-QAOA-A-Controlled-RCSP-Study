# B1 — Depth × optimization-budget ablation

**Execution status: COMPLETE.** Completed 432/432 optimizer trajectories; failed records: 0; checkpoint rows: 1296.

## Protocol

The outcome-blind manifest freezes 24 discovery tasks spanning 10 graphs, p=2/3/4, O0/O3 (alpha=0.10), three original seeds, COBYLA, and nfev checkpoints 120/240/480. The resource unit is actual objective calls, not iterations.

One deterministic 480-call trajectory is used only because the smoke gate verified that its first 120 and 240 calls are exactly identical to separately capped trajectories. Each checkpoint is the best evaluated incumbent in that genuine prefix; early solver termination is explicitly carried and flagged.

Manifest: `results/reviewer_robustness/manifests/manifest_depth_budget.json`.

## Numerical findings

- p2->p3 at 120 nfev: 30/144 nested failures (0.208).
- p2->p3 at 240 nfev: 31/144 nested failures (0.215).
- p2->p3 at 480 nfev: 38/144 nested failures (0.264).
- p3->p4 at 120 nfev: 45/144 nested failures (0.312).
- p3->p4 at 240 nfev: 45/144 nested failures (0.312).
- p3->p4 at 480 nfev: 47/144 nested failures (0.326).
- p=4, 120 nfev: graph mean O3−O0 G_feas=0.2845, 95% graph-cluster bootstrap CI [0.1742, 0.3822].
- p=4, 240 nfev: graph mean O3−O0 G_feas=0.3058, 95% graph-cluster bootstrap CI [0.1901, 0.4062].
- p=4, 480 nfev: graph mean O3−O0 G_feas=0.2813, 95% graph-cluster bootstrap CI [0.1726, 0.3720].

## Interpretation and limitations

Depth comparisons are optimization-budget-conditioned. If p=4 remains below p=3 at 480 evaluations, the only licensed wording is that increased depth was not recovered within the tested classical evaluation budgets; this experiment does not diagnose a barren plateau or intrinsic depth disadvantage.

Task rows are descriptive. Robustness intervals use paired task effects averaged within graph, then equal-weight graph resampling. These post-hoc results neither replace frozen headlines nor enter the preregistered H1/H2 family.

## Claim impact

The claim impact is assessable from the complete matrix above.

<!-- REVIEWER_ROBUSTNESS_SYNTHESIS -->

## Completed-result interpretation

- O0, 120 nfev: p4−p3 graph-mean G_feas=0.7206 (95% graph bootstrap CI [0.5785, 0.8623]); terminal loss difference=-0.0230 (negative favors p4).
- O0, 240 nfev: p4−p3 graph-mean G_feas=0.7843 (95% graph bootstrap CI [0.6074, 0.9511]); terminal loss difference=-0.0293 (negative favors p4).
- O0, 480 nfev: p4−p3 graph-mean G_feas=0.8683 (95% graph bootstrap CI [0.6428, 1.0747]); terminal loss difference=-0.0253 (negative favors p4).
- O3, 120 nfev: p4−p3 graph-mean G_feas=0.2021 (95% graph bootstrap CI [0.1404, 0.2598]); terminal loss difference=-0.1510 (negative favors p4).
- O3, 240 nfev: p4−p3 graph-mean G_feas=0.2074 (95% graph bootstrap CI [0.1434, 0.2687]); terminal loss difference=-0.1292 (negative favors p4).
- O3, 480 nfev: p4−p3 graph-mean G_feas=0.1970 (95% graph bootstrap CI [0.1290, 0.2620]); terminal loss difference=-0.1081 (negative favors p4).

At 120 evaluations p=4 is not worse than p=3 on the reported state-quality metrics: the G_feas contrast is positive for all ten graphs under both O0 and O3. Raising the budget from 120 to 480 modestly improves p=4 mean G_feas, but nested failures do not decline. Thus the experiment does not support an intrinsic p=4 disadvantage or a simple claim that more budget cures the nested diagnostic; depth behavior is objective- and diagnostic-dependent.

**Claim impact:** mixed for a generic budget-dependent depth-degradation statement, but supportive that p=4 adds information beyond the frozen p=2/p=3 study.
