# Edge-subdivision representation-padding lemma

```text
EDGE_SUBDIVISION_REPRESENTATION_PADDING_LEMMA
```

## Statement

Let `I` be an explicit directed RCSP instance with additive rational objective
costs and nonnegative rational resource vectors. Select a directed edge
`e=(u,v)` and an integer `r>=1`. Form `I^(r)` by deleting `e`, adding `r-1`
private vertices of indegree and outdegree one, and inserting the serial chain

\[
u=w_0\to w_1\to\cdots\to w_{r-1}\to w_r=v.
\]

If `e` has objective coefficient `c_e` and resource coefficients `a_{e,j}`,
give every segment coefficients `c_e/r` and `a_{e,j}/r`. Budgets and all other
edges are unchanged.

Then:

1. original and subdivided simple source-target paths are in bijection;
2. every paired path has identical objective and resource totals;
3. feasibility and objective ordering are preserved;
4. the feasible optimum, including ties, is preserved;
5. the number of valid feasible route bitstrings is preserved; and
6. the edge count increases by exactly `r-1`.

Consequently,

\[
\boxed{
\phi_{\rm state}(I^{(r)})=2^{-(r-1)}\phi_{\rm state}(I).
}
\]

## Proof

Every new internal vertex has exactly one incoming and one outgoing chain
edge and is incident to no other edge. A simple source-target path avoiding
`e` is unchanged. A path using `e` maps to the path replacing `e` by all `r`
segments. Conversely, any path entering the chain must traverse every
remaining segment and therefore contracts uniquely to `e`. These maps are
mutual inverses.

For a route using `e`, the new contribution is

\[
\sum_{k=1}^{r}\frac{c_e}{r}=c_e,
\qquad
\sum_{k=1}^{r}\frac{a_{e,j}}{r}=a_{e,j}
\quad\text{for every resource }j.
\]

Routes not using `e` are unchanged. Thus paired totals, feasibility,
objective comparisons, and the optimum are identical. The route bijection
preserves the numerator of `phi_state`; its raw edge-bit denominator gains a
factor `2^(r-1)`, proving the displayed identity.

## Exact representation growth

Write a rational coefficient as `p/q` in lowest terms and measure its encoding
by the binary lengths of numerator and denominator. Before reduction,

\[
\frac{p/q}{r}=\frac{p}{qr},
\]

so subdivision increases coefficient bit length by at most
`ceil(log2 r)+O(1)`. The implementation uses exact rational arithmetic and the
validator checks this bound.

The topology is still explicit: listing `r` serial edges and `r-1` vertices
costs `Theta(r)` entries. The lemma does **not** treat an explicit length-`r`
chain as an `O(log r)`-bit succinct graph. Building `I^(r)` takes
`O(|I|+r)` output time. Expanding or contracting a returned route is linear in
the respective route length.

## Consequence and nonclaim

Raw edge-bit feasible-state density is representation-dependent. Serial
subdivision can reduce it by an arbitrarily chosen factor while leaving the
logical route set, feasibility relation, and optimization order unchanged and
adding only the explicit linear padding/output overhead. Therefore this
density cannot alone be a semantic hardness parameter for standard explicit
RCSP.

This does not claim that edge subdivision leaves a specific edge-qubit circuit
unchanged. It generally adds qubits, constraints, state-preparation work, and
mixing/compilation overhead. Those are representation-specific algorithmic
resources and belong in the structure-cost ledger.
