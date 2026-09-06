# Theory-v3 claim boundary

## Independent research-question answers

### RQ-A — raw edge-bit density

No. `phi_state` alone cannot imply a universal time or query lower bound for
standard explicit-input RCSP. A unique explicit chain has
`phi_state=2^{-m}` and an `O(m)` exact traversal/output algorithm. Serial edge
subdivision multiplies raw density by `2^{-(r-1)}` while preserving the logical
route optimization problem.

```text
RAW_PHI_STATE_LOWER_BOUND_IMPOSSIBLE
```

### RQ-B — explicit attribute queries

Yes, with an explicit success/endpoint qualification. On the parallel-branch
subclass, topology and a length-`K` status array are explicit, but array cells
are accessed by counted quantum random-access queries. For any fixed target
`tau` in the nontrivial regime `M/K<tau`, average-case and uniform-worst-case
query complexity are `Theta_tau(sqrt(K/M))`. Exact success gives this order for
`1<=M<K`; `M=K` needs zero queries. Free delivery of the whole array is a
different model.

```text
EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND_VALID
```

The claim-matrix status is `VALID_AFTER_REFINEMENT` because the unqualified
bounded-error formula at `M=K` is false.

### RQ-C — instance-dependent structure

For uniform random size-`M` feasible subsets, classical structure advice is
summarized by

\[
\Lambda(S)=\mathbb E_S\left\|
\mathbb E[\Pi_F\mid S]
\right\|_\infty.
\]

With a hard cap of `q` membership queries,

\[
P_{\rm avg}\le\min\{1,(2q+1)^2\Lambda(S)\}.
\]

At most `b` classical advice bits give `Lambda<=min(1,2^b phi)`. Constant
success under exponential dilution and polynomial queries therefore needs
`b_eff=Omega(n)` up to logarithmic terms in this prior/model.

```text
POSTERIOR_STRUCTURE_BOUND_VALID
FINITE_ADVICE_TRADEOFF_VALID
QUANTUM_ADVICE_BOUND_VALID
```

The quantum verdict concerns one advice state of total Hilbert dimension `d`
and yields the factor `d phi`; it is not a free interactive structure oracle.

### RQ-D — burden relocation

A structure-injected QAOA method can leave the membership-only model by using
richer explicit energy values, advice, candidate restriction, feasible-state
loading, neighbor access, or a structured mixer. Its burden is relocated to
information, preprocessing, training, state preparation, compilation/gates,
oracle calls, validation, or dynamic reuse. The ledger keeps these resources
orthogonal and records unknowns rather than fabricating a runtime conversion.

```text
STRUCTURE_COST_CONTRACT_COMPLETE
```

## Result package audit

| Result | Status | Exact boundary |
|---|---|---|
| A: no raw-`phi_state` universal explicit-RCSP bound | `COUNTEREXAMPLE_ESTABLISHED` | Explicit adjacency-list/rational input and edge-list output |
| B: parallel-branch explicit-attribute query bound | `VALID_AFTER_REFINEMENT` | `Theta(sqrt(K/M))` for target success exceeding free-guess density; exact nontrivial promise |
| C: posterior structure theorem | `VALID_AS_STATED` | Classical advice before an oracle-only hard-cap interaction; conditional cap retained |
| D: finite advice/query tradeoff | `VALID_AS_STATED` | Random size-`M` prior, support at most `2^b`, hard query cap |
| E: effective support and cost accounting | `VALID_AS_STATED` | Necessary compression only; orthogonal costs remain separate |
| Quantum advice dimension extension | `VALID_AS_STATED` | One state of joint dimension `d`; subsequent dependence membership-query only |
| Rich cost oracle lower bound | `OPEN_GAP` | Membership theorem does not cover uncharged multilevel RCSP energy |

The rich-cost label remains:

```text
RICH_COST_ORACLE_EXTENSION_OPEN
```

## Allowed paper claims

### Claim level A

Raw edge-bit density is representation-dependent and cannot alone support a
universal lower bound for standard explicit RCSP. The unique-chain family and
edge-subdivision lemma establish this without denying representation-specific
dilution effects in edge-qubit algorithms.

### Claim level B

Under a counted quantum random-access model for an explicit length-`K` status
attribute array, a parallel-branch RCSP subclass has
`Theta(sqrt(K/M))` query complexity to reach a fixed target success above the
zero-query feasible density; equivalently this holds for exact success when
`1<=M<K`. The all-feasible endpoint costs zero queries.

### Claim level C

For random feasible subsets with classical structure advice `S`, the
membership-query barrier depends on posterior concentration

\[
\Lambda(S)=\mathbb E_S\left\|\mathbb E[\Pi_F\mid S]\right\|_\infty.
\]

The phase-sensitive conditional theorem and the coarse hard-cap corollary hold
after conditioning on each supported advice value.

### Claim level D

At most `b` bits of classical advice and a hard cap of `q` membership queries
imply

\[
P_{\rm avg}\le\min\{1,(2q+1)^2 2^b\phi\}.
\]

This is a necessary information/query tradeoff under the random-subset prior.

### Claim level E

Structure-injected QAOA can escape the original membership-only barrier by
receiving stronger information or paying for preprocessing, state preparation,
mixer construction, richer oracle access, validation, training, or equivalent
resources. This is an accounting framework, not a universal runtime theorem.

## Prohibited claims

The following statements are explicitly rejected:

> Every explicit RCSP instance requires
> `Omega(phi_state^(-1/2))` queries.

> Edge subdivision makes the underlying RCSP computationally exponentially
> harder.

> A feasibility-preserving mixer obtains structure for free.

> `b_eff` is automatically equal to implementation time or gate complexity.

> CVaR violates the membership-query lower bound.

> The parallel-branch result proves an exponential lower bound in compact
> graph-description size.

> A candidate set of size `K` always gives posterior membership probability
> `M/K`, even under a nonuniform posterior.

Also prohibited are moving `min(1,·)` through expectation as equality,
substituting mean query count into the hard-cap theorem, omitting training
queries, and treating a rich cost/neighbor oracle as binary membership without
a simulation.

## Paper-positioning boundary

Primary:

```text
THEORY_NOVELTY_UNRESOLVED
```

Secondary accurate descriptions:

```text
EXPLICIT_RCSP_QUERY_SUBCLASS_PLUS_EMPIRICAL_CASE_STUDY
POTENTIALLY_DISTINCT_POSTERIOR_PROJECTOR_FORM
```

Known Grover/multiple-mark search, search with prior advice, min-entropy
leakage, and preprocessing tradeoffs must be credited. External independent
proof and literature review remain open.

## Remaining gaps

- lower bounds for rich multilevel RCSP cost oracles;
- broader interactive/reusable quantum advice and quantum preprocessing;
- a natural structural lower bound for standard explicit RCSP;
- computational cost of producing useful `S` on natural instances;
- implementation-level state/mixer/loading costs and reuse;
- external independent proof and prior-art review.
