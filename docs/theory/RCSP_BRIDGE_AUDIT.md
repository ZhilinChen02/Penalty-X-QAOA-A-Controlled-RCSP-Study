# RCSP bridge audit

## Explicit target model

[PRIOR_ART_SOURCE] The audited standard RCSP input is an explicitly listed
directed graph $G=(V,E)$, source $s$, target $t$, additive objective costs
$c_e$, additive nonnegative resource vectors
$r_e\in\mathbb Q_{\ge 0}^{K}$, and explicit budgets $B_k$. A feasible solution
is a simple $s$–$t$ path satisfying

\[
\sum_{e\in P}r_{e,k}\le B_k
\quad\text{for every }k.
\]

[V2_NEW_PROOF] The audit measures input length using explicitly listed vertices,
edges, resource entries, budgets, and coefficient bit lengths. $K$ may vary,
but a claimed polynomial reduction must keep all these quantities polynomial in
$n=\log_2N$. Feasibility is fully determined by—and therefore in principle
recoverable from—the explicit input.

## Bridge requirements

[V2_NEW_PROOF] A valid transfer from arbitrary marked-set search would require
a polynomial-size transformation that maps every label to a path, preserves
marked membership as feasibility, hides no oracle inside the explicit input,
does not reveal the marked set for free, and does not replace a path-index
domain by an unrelated edge-bit denominator. No attempted construction met all
requirements.

## C1: explicit parallel paths

[V2_NEW_PROOF] Create one two-edge path $s\to v_x\to t$ per label $x$.
Assign resource zero to marked paths and resource one to unmarked paths, with
budget zero.

| Property | Result |
|---|---|
| Graph size | $N+2$ vertices and $2N$ edges |
| Coefficient count | $\Theta(N)$ |
| Marked-set visibility | Directly readable from path coefficients |
| Size in $n=\log_2N$ | Exponential |
| Status | `VALID_BUT_EXPLICIT_SIZE_THETA_N` |

[INFERENCE] This is an explicit reduction of size $\Theta(N)$, not a
polynomial-in-$n$ bridge and not a meaningful $\Omega(2^{n/2})$ lower bound in
the explicit input length.

## C2: layered binary-choice graph

[V2_NEW_PROOF] A chain of $n$ binary choices has $n+1$ vertices, $2n$
choice edges, and exactly $2^n$ logical paths. It compactly supplies the label
to path bijection.

[V2_NEW_PROOF] An arbitrary subset can be encoded with one resource for each
unmarked word $y$. Resource $y$ counts positions where candidate $x$
matches $y$; budget $n-1$ excludes exactly $x=y$. This uses $N-M$
resources and $2n(N-M)$ explicit coefficients. It is exact but exponential
for typical arbitrary subsets, and the table reconstructs feasibility.

[INFERENCE] No polynomial-size family of additive upper-bound resources capable
of representing every arbitrary subset was found. Description counting proves
that no polynomial-length explicit representation can represent all
constant-density subsets, independently of this construction.

Status: `NO_POLYNOMIAL_ARBITRARY_SUBSET_ENCODING_FOUND`.

## C3: circuit verifier or automaton

[V2_NEW_PROOF] A polynomial-size Boolean predicate describes a structured
subset succinctly. A branching program or automaton can sometimes be compiled
into a polynomial graph, but a general polynomial-size circuit was not compiled
here into standard additive, nonnegative RCSP resources with all bridge
properties preserved.

[INFERENCE] Arbitrary truth tables require exponential circuit descriptions in
the worst case. When a predicate is compact, its explicit circuit is
$\mathcal F$-dependent side information that a structured algorithm may exploit;
the black-box theorem cannot ignore it.

Status: `SUCCINCT_PREDICATE_NOT_STANDARD_ADDITIVE_RCSP_BRIDGE`.

## C4: hidden singleton route

[V2_NEW_PROOF] A singleton $y\in\{0,1\}^n$ has a compact one-resource layered
encoding: at each layer give the edge matching $y_i$ weight zero and the other
edge weight one; budget zero leaves only path $y$ feasible.

[COUNTEREXAMPLE] Reading which edge has zero weight at every layer recovers
$y$ in $O(n)$ input reads. The algorithm then outputs $y$ with zero oracle
queries. The encoding is compact but does not preserve hidden search hardness.

Status: `COMPACT_BUT_EXPLICIT_INPUT_REVEALS_SINGLETON`.

## C5: oracle-RCSP

[V2_NEW_PROOF] Define route labels $x\in\{0,1\}^n$, a label-to-logical-route
decoder, and supply feasibility only through a membership oracle. Then the v1
and adaptive theorems apply directly with $N=2^n$ and $M$ feasible route
indices.

Status: `ORACLE_RCSP_COROLLARY`.

[INFERENCE] This is a nonstandard oracle-RCSP problem. It must not be relabeled
as ordinary explicit-input RCSP.

## Edge-bit space versus path-index space

[V2_NEW_PROOF] The domain must be selected before defining $\phi$:

| Domain | $N$ | $M$ | Invalid states |
|---|---:|---:|---|
| Raw edge-bit strings | $2^{|E|}$ | feasible encoded edge selections | disconnected, cyclic, branched, or flow-invalid selections remain in the denominator |
| Valid source-target paths | number of valid paths | feasible paths | excluded before the search model starts |
| Feasible-path basis | number of feasible paths | all basis states | feasibility dilution is absent; preparation already injects structure |
| Route-index oracle | number of route labels | marked route labels | decoder-specific invalid indices must be declared |

[COUNTEREXAMPLE] In the $n$-layer binary graph there are $2^n$ candidate
paths but $2^{2n}$ raw edge-bit strings. Hence $M/2^n$ and $M/2^{2n}$ are
different feasible fractions. The latter additionally counts invalid edge
selections and cannot silently replace the former.

## Rich cost oracle

[OPEN_GAP] Standard penalty Hamiltonians can reveal objective cost,
flow-violation magnitude, resource-violation magnitude, and local correlations.
No constant-query simulation of this multilevel information by binary
membership was established. A binary subfamily gives a lower bound only for a
problem class that genuinely contains that oracle subfamily under the same
access model.

Status: `RICH_COST_ORACLE_EXTENSION_OPEN`.

## Construction verdicts

| Construction | Verdict |
|---|---|
| `PARALLEL_PATH_CONSTRUCTION` | `VALID_BUT_EXPLICIT_SIZE_THETA_N` |
| `LAYERED_BINARY_GRAPH` | `NO_POLYNOMIAL_ARBITRARY_SUBSET_ENCODING_FOUND` |
| `CIRCUIT_VERIFIER_CONSTRUCTION` | `OPEN_GAP` |
| `HIDDEN_SINGLETON` | `EXPLICIT_INPUT_REVEALS_MARKED_SET` |
| `ORACLE_RCSP` | `ORACLE_RCSP_COROLLARY` |
| `RICH_COST_ORACLE` | `RICH_COST_ORACLE_EXTENSION_OPEN` |
| `EDGE_BIT_SPACE_MAPPING` | `VALID_AFTER_REFINEMENT` for domain bookkeeping; no reduction |

## Primary verdict

[INFERENCE] The only direct bridge found retains membership-oracle access:

```text
ORACLE_RCSP_ONLY
```

[OPEN_GAP] A polynomial explicit-input RCSP reduction preserving black-box
marked-set hardness remains unproved.
