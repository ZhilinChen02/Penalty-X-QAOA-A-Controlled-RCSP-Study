# Phase 1 Pilot Execution Protocol

The Phase 1 pilot measures shallow Penalty-X QAOA response to the frozen v2
representation-dilution trajectories. It is exploratory and mechanistic. It is
not a test of quantum advantage, a phase transition, or a universal scaling law.

## Hamiltonian contract

The prospective execution contract is

```text
P_resource = 1[excess > 0]
             + min((excess / sum_edge_resources)^2, 1)

P_flow = 1[flow_raw > 0]
         + min(flow_raw / max_x(flow_raw), 1)

E_raw = routing_cost + 172 P_flow + 172 P_resource
E_qaoa = E_raw / 172
```

The global factor 172 is fixed for every task before pilot execution. It is one
greater than the declared generator-wide routing-cost bound, 19 edges times a
maximum edge cost of 9. The factor is not fitted per task. Raw energy is retained
for auditing, while both QAOA phases and the COBYLA objective use `E_qaoa`.

Before optimization, exhaustive enumeration over all 140 v2 tasks must establish
that raw and normalized argmin sets are identical, every normalized ground state
is an exact original RCSP optimum, and constraint classifications are unchanged.
Failure of any check stops execution.

## Frozen task and optimizer design

The two lowest `base_index` values in each size stratum are selected without
reading QAOA outcomes. All distinct stress levels belonging to each selected base
graph are retained, producing 56 complete within-graph trajectories. The manifest
and config SHA256 values are frozen before execution.

Penalty-X is run at depths 1, 2, and 3 with seeds 1103, 2207, and 3301. COBYLA has
a fixed 120-evaluation budget, `rhobeg=0.5`, and `catol=1e-8`. Poor results do not
receive extra evaluations or replacement seeds. Uniform is analytic and adds one
row per task.

## Aggregation without metric leakage

The primary task-depth view reports metricwise median, mean, minimum, and maximum
across the three seeds. Its figures use the median view. A secondary operational
multistart view selects the seed only by minimum optimized normalized energy and
then reports that seed's recovery metrics. Neither feasible nor optimal
probability participates in seed selection.

Compensation slopes are fit within each base graph:

```text
G_feas = kappa * dilution_score + intercept
log10(P_feas) = absolute_feasibility_log_slope * dilution_score + intercept
```

Only graphs with at least three distinct dilution levels are used. The identity
`absolute_feasibility_log_slope = kappa - 1` is checked numerically. Slopes are
then summarized descriptively across base graphs; no p-values or confirmatory
threshold claims are made.

## Persistence and failures

Rows have deterministic identities derived from task, algorithm, depth, seed,
and the frozen config hash. Writes are atomic and resume-safe. TIMEOUT, OOM,
OPTIMIZER_FAILURE, NUMERICAL_FAILURE, ZERO_P_FEAS, ZERO_P_OPT, and
RESOURCE_CENSORED statuses remain in the planned denominator and are never
replaced with new seeds.
