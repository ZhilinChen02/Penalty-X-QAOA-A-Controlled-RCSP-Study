# Phase 1.1 — Optimization Attribution Diagnostic

This diagnostic preserves the immutable Phase 1 pilot and does not replace any original p=3 row. It separates optimizer adequacy, Hamiltonian-objective alignment, and depth response descriptively.

## Nested ansatz

All 168 p2-to-p3 zero-layer embeddings passed. Maximum state, probability, and objective differences were 0, 0, and 0.

## Original p3 optimizer adequacy

Original p3 was objectively worse than the embedded p2 point in 29 / 168 runs (17.3%). The median objective gap was -0.199582; Spearman gap versus dilution was -0.3136.

Continuation recovered a lower objective for 29 / 29 of those direct failures and a higher G_feas for 27 / 29.

## Continuation

Relative to the embedded start, median changes were objective improvement 0.101824, P_feas 0.00219193, G_feas 0.152973, and P_opt 0.00102541.

Median paired original-minus-continuation objective was -0.0972751; its negative sign means continuation had the higher objective on the median pair. Median continuation-minus-random changes were P_feas 0.00497691, G_feas 0.433302, and P_opt 0.00161083.

Random p3 had lower objective than continuation in 108 / 168 pairs, and simultaneously lower G_feas in 82 pairs. This is direct objective/feasibility non-equivalence, not an optimizer failure label by itself.

Continuation classifications:

- `OBJECTIVE_AND_FEASIBILITY_IMPROVE`: 151
- `OBJECTIVE_IMPROVES_FEASIBILITY_WORSENS`: 17

## Compensation

Median within-base kappa changed from -0.539995 for frozen random p3 to 0.367232 for three-seed continuation. Objective-selected B2 and B4 medians were 0.0777146 and -0.0110957.

The median p3-minus-p2 gain changed from -0.257208 for random p3 to 0.178018 for continuation.

## Budget and optimizer controls

Median objective gains were B1-to-B2 0.0319738 and B2-to-B4 0.0138629; median G changes were 0.0819554 and 0.0240996.

Objective improved while G_feas worsened in 4 / 56 B1-to-B2 pairs and 10 / 56 B2-to-B4 pairs.

Under the matched B1 budget, median Nelder–Mead minus COBYLA objective was -8.95191e-05; Nelder–Mead had lower objective on 29 / 56 tasks. Median G difference was -0.116783.

Nelder–Mead combined a lower objective with a lower G_feas in 15 / 56 matched tasks.

Primary `objective_final` fields retain the raw SciPy terminal point; `best_evaluated_objective` is stored separately and never silently substituted. The terminal point was worse than the tracked best by more than 1e-10 in 0 / 168 COBYLA continuation runs and 7 / 56 Nelder–Mead runs.

## Objective decomposition

For paired random-p3 minus continuation states, median objective difference was -0.0972751. Its routing, flow-penalty, and resource-penalty differences were -0.0223091, 0.00267585, and -0.0572974. Random p3 placed 0.00497691 less probability on valid resource-feasible states, 0.0084685 more on flow-invalid states, and 0.0542534 less on resource-violating states. Thus lower expected energy often came from lower-cost/lower-resource-penalty still-infeasible mass rather than uniformly greater feasible recovery.

## New-layer response slices

The 15 deterministic 41-by-41 slices had median grid objective gain 0.0564769, median grid G_feas gain 0.338866, and median G_feas change 0.180253 at the grid objective minimum. Original p3 new-layer coordinates lay inside the frozen symmetric slice window for 0 / 15 tasks; no off-window projection was drawn.

## Energy separation

Complete feasible/infeasible energy-class separation held for 56 / 56 pilot tasks and 140 / 140 full-v2 tasks. This does not make expected energy strictly monotonic in feasible probability.

## Attribution

`MIXED`

Better objective, better feasible probability, and better optimal probability remain distinct outcomes throughout this report.

## Next recommendation

`INVESTIGATE_OBJECTIVE_DESIGN`
