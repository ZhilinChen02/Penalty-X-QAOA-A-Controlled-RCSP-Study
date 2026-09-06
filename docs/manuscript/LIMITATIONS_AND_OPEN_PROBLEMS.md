# Limitations and Open Problems

## Proven limitations

- Raw edge-bit state density is representation-dependent and cannot alone imply
  universal explicit-RCSP complexity (`C-T5`, `C-T6`).
- The explicit parallel-branch RCSP result is a counted random-access input-query
  theorem, not an explicit-RAM runtime or compact-description lower bound
  (`C-T7`).
- Membership-only theory assumes that all remaining feasible-set dependence is
  charged through the specified oracle (`C-T1`, `C-T2`, `C-T8`).
- Effective advice bits and effective support give necessary posterior
  concentration, not an implementation or sufficiency theorem (`C-T11`).
- One-shot quantum advice does not cover refreshed or interactive advice
  (`C-T10`).

## Empirical limitations

- The confirmatory method is Penalty-X QAOA at p=3.
- Tasks are controlled synthetic directed acyclic graphs.
- Simulation is exact statevector on CPU; there is no hardware/noise evidence.
- Depth is shallow and no feasible-subspace mixer family was empirically tested.
- Phase 3 completes only through m=20; m=22 is resource-censored.
- The m=20 response reverses the earlier mean-versus-CVaR ordering, precluding a
  global scaling-law claim.
- Phase 3B is pending outside Synthesis v1 and contributes no evidence.

## Open theory problems

- Lower bounds for rich cost/energy oracles relevant to CVaR.
- Natural explicit-RCSP structural lower bounds beyond the constructed
  attribute-query subclass.
- Computational, statistical, memory, and gate cost of producing a useful
  structure variable \(S\).
- Repeated, refreshed, or interactive quantum advice.
- Sharper expected-query theorems than the current truncation bound.
- End-to-end bounds that jointly charge structure generation, reuse, and
  validation without collapsing orthogonal resources to an arbitrary scalar.

## Required external validation

- Independent human review of every central theorem, especially T2 and T8--T10.
- Independent primary-source/priority review with forward citation tracing.
- External reproduction of the canonical empirical rows and figures.
- Assessment on natural RCSP instances and, separately, hardware/noise studies.

Until those steps occur, the artifact is ready for structured drafting and
external review, not submission-ready proof or generality claims.
