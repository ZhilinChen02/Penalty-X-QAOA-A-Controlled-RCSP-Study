# Phase 3 preregistration: empirical dilution scaling

This protocol was specified before any Phase-3 QAOA outcome was generated. Phase 0--2
results are historical motivation only and are excluded from Phase-3 task selection,
threshold selection, model selection, and fitting. The immutable predecessor is commit
`1729aa044a84dfb12b0edcacf4ea2d9d25c35b74`.

## Claim boundary

The strongest permitted statement is **an empirical feasibility-recovery scaling law
within the tested Penalty-X QAOA / RCSP regime**. The study cannot establish a universal,
asymptotic, complexity-theoretic, critical, quantum-advantage, or quantum-disadvantage
law. If a critical validity check fails, the result is called a `SCALING_RESPONSE`.

## Prospective design

Thirty independently seeded layered DAGs are generated: five at each exact edge-bit size
`m in {12,14,16,18,20,22}`. Topologies vary through frozen width templates, independently
sampled optional/skip edges, costs, and resources. Positive integer edge resources have
support `[1,1000]`. A graph is rejected only before QAOA and only if it has fewer than six
candidate routes or fewer than six constructible distinct feasible-set thresholds. Every
attempt and seed is retained. QAOA outcomes never enter construction.

For each accepted graph, six distinct feasible-route cardinalities are selected
deterministically near

`round(10 ** linspace(0, log10(M), 6))`,

with duplicate desired counts filled from unused order statistics and tied resource
thresholds mapped deterministically to unused achievable cumulative counts. Every chosen
budget must produce its intended cardinality exactly. At fixed `m`,

`phi_state = k / 2^m`, so `D = m log10(2) - log10(k)`.

Thus log-spacing in `k` provides approximately even within-graph coverage in `D`.

The split is frozen before QAOA: base indices 0--3 at sizes 12--18 form development
(16 graphs, 96 tasks); base index 4 at sizes 12--18 forms interpolation holdout
(4 graphs, 24 tasks); all graphs at sizes 20--22 form extrapolation holdout
(10 graphs, 60 tasks). There is no graph overlap.

## Hamiltonian and algorithm

The primary method is CPU/NumPy exact-statevector Penalty-X QAOA at fixed `p=3`. The
global raw penalty coefficient is `lambda_phase3=199`, prospectively exceeding the global
routing-cost bound `22*9=198`. For every state,

`E_raw = routing_cost + 199 P_flow + 199 P_resource`,

`E_qaoa = E_raw / 199`,

where each violated controlled penalty has a hard indicator plus bounded severity. There
is no task-specific normalization. All tasks must pass ground-state validity, resource
feasibility, exact-original optimality, and strict infeasible/feasible energy separation
before any QAOA optimization.

Each task uses three deterministic `p=2` mean-energy starts, seeds 1103, 2207, and 3301,
with 120 COBYLA evaluations. The minimum final mean-energy objective alone selects the
continuation. `[g1,g2,b1,b2]` is embedded as `[g1,g2,0,b1,b2,0]` and shared by O0, O2,
and O3. Their matched `p=3` budget is the frozen Phase-2 value, 240 evaluations. O0 is
mean energy; O2 is exact `1-P_feas` and is labelled only as a statevector mechanistic
capacity control; O3 is exact probability-weighted lower-tail CVaR at fixed alpha 0.10.

## Resource and execution gates

Before optimization, fixed-parameter kernel timing is measured at every size. A size is
allowed only if predicted worker RSS is at most 40% of available RAM, a single primary
optimization is predicted at most 20 minutes, and the statevector is numerically valid.
Failure at `m=22` censors every 22-qubit task. Failure at `m=20` stops the study with
`SCALING_RANGE_INSUFFICIENT`. Worker count may decrease by size but budgets do not.

Formal order is: structural universe, manifest/split freeze, resource preflight, tests,
two-task final-protocol preflight, development only, development budget sentinels, model
selection, model-freeze hash, interpolation execution, extrapolation execution, frozen
validation, then descriptive combined analysis. Holdout access is forbidden before the
model-freeze artifact exists.

## Response, identity, and zeros

The primary response is `Y=log10(P_feas)` and `D=-log10(phi_state)`. No epsilon is added.
Exact zero probability is retained as `ZERO_P_FEAS`, included in denominators and the
failure census, and excluded from ordinary log regression. A censored/floor-aware
sensitivity becomes mandatory if zeros exceed 5% of primary rows.

Within every graph/objective, `Y=a-eta D` is fitted with at least five valid levels. Since
`G_feas=log10(P_feas/phi_state)=Y+D=a+(1-eta)D`, its slope is
`kappa=1-eta`. The same rows must verify this numerical identity within `1e-10`.

## Frozen development model family

All fits use graph-centered `Yc=Y-mean_g(Y)` and `Dc=D-mean_g(D)`:

- M1: `Yc = -eta Dc`.
- M2: `Yc = -[eta_0 + eta_m(m-15)] Dc`.
- M3: `Yc = -eta Dc + q[Dc^2-mean_g(Dc^2)]`.
- M4: M2 plus the M3 curvature term.

No other model is permitted. For each objective, leave-one-base-graph-out CV reports
RMSE, MAE, fold-RMSE standard error, and secondary AICc. The lowest-RMSE model defines a
one-standard-error threshold; the simplest model in the frozen order M1<M2<M3<M4 within
that threshold is selected. Frozen coefficients and uncertainty are written before any
holdout QAOA. Holdout predictions are never refitted. Baselines are eta=1 (uniform) and
eta=0 (flat).

## Optimization adequacy

For each development size, the first graph and third of six dilution levels is evaluated
at B=240 and 2B=480 for O0/O2/O3, with B reused from the main matrix and both optimizations
starting from the identical common initialization. A cell is substantially sensitive if
`abs(G_feas(2B)-G_feas(B)) >= 0.10` decades. If any objective is substantial at m=16 or
m=18, the claim ceiling becomes `OPTIMIZATION_LIMITED_SCALING`; B is not changed.

## Preregistered hypotheses and inference

The independent unit is `base_graph_id`. Grouped bootstrap uses 10,000 resamples with
seed 20260828. The three-hypothesis family is Holm-corrected at family alpha 0.05 on the
untouched extrapolation graphs that complete the resource gate:

- S-H1: `eta_O0 > 0`.
- S-H2: `eta_O3 - eta_O0 < 0`.
- S-H3: `abs(eta_O3-eta_O2) < abs(eta_O0-eta_O2)`.

Development and interpolation estimates are reported separately and are not substituted
for the final extrapolation test. Per-objective summaries report mean, median, IQR,
bootstrap interval, and range; contrasts are paired within graph.

## Verdict logic

The primary verdict is exactly one of `GLOBAL_POWER_LAW_SUPPORTED`,
`CONDITIONAL_SIZE_DEPENDENT_SCALING_SUPPORTED`, `CURVED_RESPONSE_SUPPORTED`,
`NO_REPRODUCIBLE_SCALING`, `OPTIMIZATION_LIMITED_SCALING`, or
`RESOURCE_CENSORED_SCALING`, following the frozen gates in the configuration and final
validator. The objective verdict is exactly one of `CVAR_CHANGES_SCALING_EXPONENT`,
`CVAR_MATCHES_MEAN_SCALING`, `CVAR_APPROACHES_CAPACITY_SCALING`, or
`MIXED_OBJECTIVE_SCALING`. Negative and resource-censored outcomes are valid.
