# QAOA query accounting

## Fixed schedules

For the binary feasibility Hamiltonian
(H_{\mathcal F}=I-\Pi_{\mathcal F}), exponentiation gives

\[
e^{-i\gamma H_{\mathcal F}}=e^{-i\gamma}
[I+(e^{i\gamma}-1)\Pi_{\mathcal F}].
\]

The outer scalar is a global phase. The bracket is exactly one marked-set phase
query with angle (-\gamma). A (p)-layer schedule has (q=p) only when:

- each layer contains exactly one such relevant cost query;
- initialization is independent of the particular ℱ;
- mixers and all other gates are independent of the particular ℱ; and
- phases are fixed independently of the particular ℱ.

If a layer contains at most (c) relevant queries, (q\le cp). Combining this
with (q\ge\tfrac12(\sqrt{\tau/\phi}-1)) gives

\[
p\ge\max\left\{0,\frac1{2c}(\sqrt{\tau/\phi}-1)\right\}.
\]

The relation (p=q) is not a generic identity for all implementations.

## Instance-trained variational procedures

Training makes later parameters depend on ℱ through earlier oracle-mediated
measurement results. The fixed-schedule theorem therefore does not directly
lower-bound final circuit depth. The relevant resource is the complete number
of ℱ-dependent oracle uses in:

- all parameter-training circuit evaluations;
- every measurement shot and repeated sample;
- adaptive classical feedback loops;
- validation or model-selection evaluations; and
- final execution.

To reduce a bounded adaptive procedure to the pure query theorem, one must
purify randomness, store measurement outcomes coherently, defer measurement,
implement feedback as controlled unitaries, and pad all branches to the same
finite worst-case number of oracle calls. The final classical success predicate
must become a final projective measurement. This is classified
`VALID_STANDARD_REDUCTION_NOT_FORMALIZED` here. Expected-query guarantees,
postselection, or unbounded stopping rules require additional analysis.

## Structure-preserving QAOA

A feasible-subspace initial state or feasibility-preserving mixer can avoid
full-space dilution. It is outside the direct theorem because feasible structure
has already entered the computation. Honest resource comparisons must account
for state-preparation depth, mixer synthesis, classical preprocessing, compiled
instance data, and any oracle stronger than membership.

## Rich cost Hamiltonians

A natural cost oracle may encode values for every basis state rather than one
binary membership phase. Such an oracle can reveal more information. The binary
theorem applies only after an explicit reduction showing how each rich-oracle
call is simulated by a bounded number of marked-set phase queries, or through a
separate lower bound for the richer oracle model.
