# Scientific question

> How does representation-induced feasible-space dilution affect the ability of
> shallow QAOA to recover feasible and optimal solutions in resource-constrained
> shortest-path problems?

The controlled causal chain under study is:

```text
problem structure → representation size → feasible-state density
                  → probability concentration → feasible/optimal recovery
```

The primary independent diagnostic is

```text
phi_state = |F| / |Omega| = n_feasible_states / 2^m,
```

not the fraction of candidate paths satisfying the budget. The response variables
are `p_feas`, `p_opt`, `p_opt_given_feasible`, and
`feasibility_amplification = p_feas / phi_state`.

An amplification near one is consistent with uniform state-space sampling. An
amplification above one shows relative concentration but must always be read next
to absolute `p_feas`. Early curves may be described as response curves, collapse
regions, or candidate transitions only. Without a scaling analysis, this project
does not use “critical threshold”, “phase transition”, “universal boundary”, or
“exponential” as conclusions.
