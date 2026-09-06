# Raw edge-bit dilution is not a universal explicit-RCSP hardness parameter

## Input, output, and density models

An **explicit RCSP input** is an adjacency-list representation of a finite
directed graph, explicitly listed rational objective/resource coefficients,
explicit rational budgets, and designated vertices `s,t`. Coefficient bit
length and every listed vertex, edge, and resource entry contribute to input
length. A solution is output as the ordered list of edge identifiers of a
simple feasible `s`-to-`t` path. Writing the output therefore costs at least
its path length in the ordinary word/RAM or Turing model.

For a graph with `m=|E|` edge variables, the raw edge-bit density used here is

\[
\phi_{\rm state}(I)=
\frac{\#\{\text{edge selections encoding valid feasible simple }s\!\!-
t\text{ paths}\}}{2^m}.
\]

Disconnected, cyclic, branched, empty, and otherwise flow-invalid selections
remain in the denominator. This is deliberately a representation statistic,
not the fraction of candidate paths that are feasible.

## Unique-chain counterexample theorem

**Theorem (unique chain).** For every integer `m>=1`, there is an explicit
RCSP instance `I_m` with `m+1` vertices and `m` directed edges such that

\[
\phi_{\rm state}(I_m)=2^{-m},
\]

while a deterministic explicit-input algorithm returns the exact optimum in
`O(m)` time and emits an output of length `m`.

**Construction.** Let

\[
s=v_0\longrightarrow v_1\longrightarrow\cdots\longrightarrow v_m=t.
\]

Give every edge objective cost and resource consumption one, and set the
resource budget to `m`. The only source-target path consists of all `m` edges;
it is feasible and optimal. Exactly one of the `2^m` edge selections encodes
that path, so `phi_state=2^{-m}`. An adjacency-list traversal starting at `s`
follows the unique outgoing edge at each internal vertex, checks the additive
totals, and outputs the `m` edge identifiers. Its work is `O(m)`, which is also
the output-length order.

## Impossibility consequence

Let `T*(I)` be the minimum worst-case running time of an explicit-input
algorithm in the preceding model. Suppose constants `c>0` and a universal
claim asserted

\[
T^*(I)\ge c\,\phi_{\rm state}(I)^{-1/2}
\quad\text{for every explicit RCSP instance }I.
\]

The chain algorithm gives `T*(I_m)<=a m+a` for a model-dependent constant
`a`, while the proposed right side is `c 2^{m/2}`. Since
`(a m+a)/2^{m/2}->0`, sufficiently large `m` contradicts the claim. The same
family disproves any universal lower bound that grows asymptotically faster
than the unavoidable linear input/output work merely because raw edge-bit
density shrinks exponentially.

This proves:

```text
RAW_PHI_STATE_LOWER_BOUND_IMPOSSIBLE
```

## Exact boundary

The theorem concerns **explicit problem complexity**. It does not say that raw
edge-bit dilution is irrelevant to an edge-qubit QAOA implementation. A
full-space initial state, penalty landscape, or mixer may behave poorly because
almost all edge-bit basis states are structurally invalid. Such behavior is
**representation-specific quantum-algorithm behavior**, and its cost must be
analyzed for that encoding and information-access model. It cannot be promoted
to a universal explicit-RCSP lower bound from `phi_state` alone.
