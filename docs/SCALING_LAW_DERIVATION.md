# Feasibility-recovery scaling identities

Let `N_feasible` be the number of feasible computational-basis states in an `m`-edge-bit
representation. The exact representation identity is

`phi_state = N_feasible / 2^m`,

so

`log10(phi_state) = log10(N_feasible) - m log10(2)`.

Define `D=-log10(phi_state)`. The empirical candidate relation

`P_feas = A phi_state^eta`

is equivalent to

`log10(P_feas) = log10(A) + eta log10(phi_state) = log10(A) - eta D`.

Feasibility amplification in decades is

`G_feas = log10(P_feas/phi_state)`

`= log10(P_feas) - log10(phi_state)`

`= log10(A) - eta D + D`

`= log10(A) + (1-eta)D`.

Therefore, if `kappa=dG_feas/dD` is estimated on exactly the same rows as `eta`, then

`kappa = 1-eta`, and equivalently `eta=1-kappa`.

This identity is tested numerically for every base-graph/objective fit. It is an algebraic
consequence of the definitions, not an empirical scaling result.

## Conditional composition result

**Proposition (conditional).** If, in some separately justified instance ensemble,
feasible-state dilution obeys `phi(m) approximately exp(-lambda m)` and an algorithm's
recovery obeys `P_feas approximately A phi^eta`, then substitution gives

`P_feas(m) approximately A exp(-eta lambda m)`.

Thus the conditional absolute feasibility-decay rate is the product of a representation
dilution rate `lambda` and an empirical recovery exponent `eta`.

Phase 3 deliberately manipulates feasible cardinality, so it does not test or establish
exponential `phi(m)` scaling. Its primary empirical relation is `P_feas` versus
`phi_state`, within the tested Penalty-X QAOA / controlled-RCSP regime.
