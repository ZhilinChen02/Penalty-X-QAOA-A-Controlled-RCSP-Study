# Data schema

One canonical result row represents one `task × algorithm × depth × seed`. Uniform
is analytic and uses `depth=0, seed=0`. Missing numerical values are stored as NaN;
rows are never dropped because of missing values or failure status.

## Identity and task fields

| Field | Meaning |
|---|---|
| `run_id` | Deterministic row identity used for restart/deduplication |
| `task_id`, `graph_id`, `base_instance_id` | Task, attributed graph, shared budget-family identity |
| `size_stratum`, `tightness_level` | Controlled experimental cells |
| `seed`, `algorithm`, `depth` | Algorithm identity |
| `n_nodes`, `n_edges`, `n_qubits` | Graph and edge-bit representation size (`n_qubits=n_edges`) |
| `resource_count`, `budget` | RCSP constraint (`resource_count=1` in v1) |
| `n_candidate_routes`, `n_feasible_routes` | Path-pool counts |
| `route_feasible_fraction` | `n_feasible_routes / n_candidate_routes` |
| `state_space_size` | `2^n_qubits` |
| `n_feasible_states` | Strictly valid, budget-feasible edge-bit states |
| `feasible_state_fraction` | `n_feasible_states / state_space_size` |
| `n_optimal_states`, `optimal_cost` | All tied exact optima and their cost |

## Algorithm and response fields

| Field | Meaning |
|---|---|
| `flow_penalty_strength`, `resource_penalty_strength` | Frozen diagonal penalty coefficients |
| `optimizer`, `eval_budget`, `nfev`, `status` | Optimizer contract and return information |
| `initial_parameters`, `optimized_parameters` | JSON arrays; gammas followed by betas |
| `objective_initial`, `objective_final`, `expected_energy` | Expected diagonal energy |
| `p_feas` | Total probability on exact feasible states |
| `p_opt` | Total probability on all exact optimal states |
| `p_opt_given_feasible` | `p_opt / p_feas`, NaN when `p_feas=0` |
| `feasibility_amplification` | `p_feas / feasible_state_fraction`, NaN when denominator is zero |
| `uniform_p_feas`, `uniform_p_opt` | Analytic uniform references |
| `uniform_feasibility_amplification` | One unless no feasible state, then NaN |

## Runtime and status fields

`task_build_time_s`, `exact_reference_time_s`, `energy_build_time_s`,
`optimization_time_s`, `optimizer_runtime_s`, `total_time_s`, and `peak_memory_mb`
record observational resource use. `execution_status` is the canonical status;
`failure_reason` preserves details. Boolean flags are `zero_feasible`,
`zero_optimal_probability`, and `resource_censored`.

The Phase 0 characterization table additionally records target versus actual edge
count, budget quantile, duplicate-budget/feasible-set indicators, exhaustive
enumeration time, and the structural path-state count.

## Prospective dilution-stress extension

Phase 0.5 v2 characterization adds `stress_level`, intended and actual feasible-route
counts, selection reason, unique resource-consumption count, achievable/effective
distinct-level counts, `stress_status`, resource support, and

```text
dilution_score = -log10(feasible_state_fraction).
```

It is NaN when `feasible_state_fraction <= 0`. Prospective Phase 1 v2 diagnostics
also define, without replacing `feasibility_amplification`,

```text
log_feasibility_gain = log10(p_feas / feasible_state_fraction)
```

only when both inputs are positive. Zero means uniform-equivalent concentration;
positive means amplification and negative means concentration below uniform.
