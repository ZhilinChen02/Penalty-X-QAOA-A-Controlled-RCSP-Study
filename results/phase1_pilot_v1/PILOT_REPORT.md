# Phase 1 Scale-Controlled Dilution Pilot

This is an exploratory, mechanistic pilot. It does not establish a critical threshold, phase transition, scaling law, or quantum advantage.

## Frozen execution identity

- Pre-run commit: `a626aa64a341daa8a26bcdb8c464a2ce64676250`
- Manifest SHA256: `b27089081b6e298956b6a6c192053c5cdfdac06280d440d3c5549fe8237349de`
- Config SHA256: `578f9277d133d8ceb301a69b51ff3f2c04030194549f26296b2b80536697e0d5`
- Tasks: 56
- Optimized rows: 504 / 504

## Validation

- pytest: 44 passed in 1.86s
- Global normalization and exact optimum: 140 / 140
- Execution preflight: PASS
- Optimization failures: 0
- ZERO_P_FEAS rows: 0
- ZERO_P_OPT rows: 0

## Descriptive result

Scientific verdict: `MIXED_STRUCTURE_DEPENDENT_RESPONSE`.

| depth | median P_feas | median P_opt | median G_feas | median objective improvement | median runtime (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.0050892 | 0.00232924 | 1.67589 | 0.650893 | 0.756019 |
| 2 | 0.00598388 | 0.00188125 | 1.63659 | 1.06982 | 2.4045 |
| 3 | 0.00319006 | 0.00157285 | 1.51929 | 0.650791 | 3.42349 |

## Dilution compensation

| depth | Spearman D vs P_feas | Spearman D vs G_feas | median kappa | IQR | range | negative / 0-to-1 / >=1 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | -0.6353 | 0.9236 | 0.5418 | 0.8884 | [-0.7119, 1.5323] | 2 / 5 / 3 |
| 2 | -0.8672 | 0.9423 | 0.4125 | 0.3907 | [-0.6422, 1.9976] | 1 / 7 / 2 |
| 3 | -0.6197 | 0.7607 | -0.5400 | 2.0025 | [-2.7846, 0.4387] | 8 / 2 / 0 |

The positive all-task D-versus-gain correlations include size and graph-structure differences. The within-base kappa distribution is the primary compensation diagnostic and shows a mixed, depth-dependent response.

The absolute-slope identity was satisfied numerically: the maximum absolute residual in `absolute_feasibility_log_slope = kappa - 1` was below 1.2e-13.

## Depth effect

Median Delta_G values were p2-p1=0.0217502, p3-p2=-0.257208, and p3-p1=-0.299988. Their Spearman associations with D were all negative, so depth benefit descriptively tended to shrink as dilution increased in this pilot.

## Objective alignment

The objective-selected multistart seed had lower P_feas than the metricwise median seed in 46 / 168 task-depth cells (27.4%). Alignment was mixed and depth-dependent rather than uniformly tracking feasible recovery; the optimizer objective remains unchanged.

## Hamiltonian scale sanity

Normalized spans ranged from 2.97815 to 4.32657 (median 3.66769). The overall Spearman D-versus-span association was 0.8025, reflecting size as well as budget. Within a frozen base graph, span relative ranges were 2.7% to 10.2% (median 6.8%); numerical scale is controlled but not perfectly invariant and remains a residual diagnostic covariate.

Primary figures use metricwise medians across the three frozen seeds. The secondary `objective_selected_multistart` view selects only by minimum optimized Hamiltonian objective and never by feasible or optimal probability.

Compensation slopes were fit separately within each base graph before cross-graph summaries. All reported associations are descriptive and are not interpreted as causal or confirmatory.

## Next recommendation

`ADD_OPTIMIZATION_DIAGNOSTIC`
