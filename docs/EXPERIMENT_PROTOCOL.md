# Experiment protocol

## Frozen task universe

Graphs are directed and layered. Edges span one layer or, when sampled, skip one
layer. Every edge has a positive integer cost and one positive integer resource
value. Stable edge indices are assigned by sorting `(source, target)`. Seeds are
derived with SHA-256 from `master_seed`, size stratum, and base index, so Python
hash randomization cannot change an instance.

The Phase 0 v1 edge targets are 7, 10, 13, 16, and 19 (S1–S5). Each contains five
independent base graphs. Each graph is reused at all seven tightness levels, so a
budget comparison holds graph topology and attributes fixed.

Budgets are derived only from the frozen candidate-route resource distribution.
The quantiles from loose to tight are `1.00, 0.85, 0.70, 0.55, 0.40, 0.20, 0.00`,
using NumPy's `lower` quantile method. The budget is never modified using QAOA
outcomes. Repeated budgets and repeated feasible sets are retained and marked by
`duplicate_budget` and `duplicate_feasible_set`.

## Exact references and representation validation

All directed simple source-target routes are enumerated. Exact feasible routes,
all tied minimum-cost feasible routes, and exact optimal cost follow directly.

For every base graph, all `2^m` edge-bit states are inspected. Validation applies:

1. source `out-in=+1`, target `out-in=-1`, intermediate `out-in=0`;
2. reconstruction from source with exactly one selected next edge;
3. directed connectivity to target without revisiting a vertex;
4. equality between reconstructed and complete selected edge sets;
5. resource consumption at or below the task budget.

The exhaustive structural pass is shared across budgets on the same graph. Every
state is still checked; budget filtering is then exact using its recorded resource.
Counts are asserted equal to independently enumerated route sets.

## Frozen Penalty-X contract

The primary contract is `lambda_flow=50.0` and `lambda_resource=20.0`. Optional
future sensitivity contracts are weak `(12.5, 5.0)`, medium/default `(50, 20)`,
and strong `(200, 80)`, but the smoke and primary analysis use only the frozen
default. The three named contracts are config-selectable; only `medium` is active
in both committed primary configs. These constants are not selected per instance.

The resource penalty is the slack-free squared hinge
`max(0, R(x)-B)^2`. It is evaluated exactly on the diagonal. Because this form is
not generally a pure quadratic polynomial without auxiliary variables, it is not
called an exact QUBO. This phase studies ideal statevector probability mechanisms,
not gate decomposition.

The initial state is uniform. Each layer applies the diagonal cost phase and an X
mixer via pairwise amplitude updates; no dense mixer matrix is built. COBYLA
minimizes expected diagonal energy with a fixed evaluation budget. Parameters are
initialized from fixed seeds. Reported recovery probabilities do not enter the
optimizer objective.

Smoke uses depth 1, 48 evaluations, and two seeds. The full Phase 1 projection uses
depths 1–3, 120 evaluations, and five seeds. No deeper sweep is part of v1.

## Failure and restart policy

Canonical rows are keyed by deterministic `run_id`. Writes are atomic, and restart
logic appends only missing IDs. No status is filtered from stored results. Supported
statuses include `TIMEOUT`, `OOM`, `NO_FEASIBLE_ROUTE`, `NO_FEASIBLE_STATE`,
`OPTIMIZER_FAILURE`, `NUMERICAL_FAILURE`, `ZERO_P_FEAS`, `ZERO_P_OPT`, and
`RESOURCE_CENSORED`. A zero feasible-state fraction produces NaN amplification.
The optimizer checks a frozen wall-clock limit between objective evaluations
(`60 s` in smoke; `1800 s` in the full projection) and writes `TIMEOUT` rather
than discarding that run.

Runtime fields are observational and need not be bitwise reproducible. Task data,
initial/optimized parameters, objective values, and probability metrics are expected
to reproduce under the same software stack and seed.
