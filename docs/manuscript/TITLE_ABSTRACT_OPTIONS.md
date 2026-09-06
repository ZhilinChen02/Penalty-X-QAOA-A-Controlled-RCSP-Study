# Title and Abstract Options

Package B is selected because the frozen architecture is empirical-primary.
Packages A and C remain alternatives if external review changes the balance.

## Package A -- theory-led integrated

**Title:** Feasible-Space Dilution in Quantum Optimization: Access-Model
Boundaries and a Controlled RCSP Case Study

**Abstract (DRAFT_FOR_REVIEW):**

Feasible solutions can occupy a small fraction of a full binary state space,
but that fraction is representation-dependent and does not by itself determine
the complexity of an explicit optimization problem. We separate three settings:
membership-only search over random feasible subsets, random-access queries to
explicit route attributes, and rich energy access in variational optimization.
For the first setting, we review phase-sensitive and adaptive hard-cap bounds
and formulate structure dependence through posterior projector concentration;
finite classical advice then yields a necessary advice--query tradeoff. A chain
and serial-padding construction rule out a universal explicit-RCSP lower bound
based only on raw edge-bit density, whereas a parallel-branch subclass inherits
multiple-marked search complexity under counted attribute access. We connect
these boundaries to a controlled exact-statevector study of shallow Penalty-X
QAOA for resource-constrained shortest paths. Discovery-stage diagnostics
separate Hamiltonian scale, optimizer failure, and objective--feasibility
misalignment. On preregistered held-out graphs, CVaR optimization improves
feasibility compensation over mean-energy optimization and is noninferior, at
the frozen margin, to a mechanistic exact-feasibility capacity objective. A
larger-size study shows heterogeneous response, including a reversal at the
largest completed size, while the next size is resource-censored. The results
support explicit accounting for preprocessing, state preparation, structured
mixers, richer queries, and validation; they do not establish general quantum
advantage, a universal RCSP lower bound, or theorem priority.

## Package B -- empirical objective/CVaR (selected)

**Title:** Feasible-Space Dilution and Objective Alignment in Shallow QAOA: A
Controlled RCSP Study

**Abstract (DRAFT_FOR_REVIEW):**

Small feasible subspaces create a practical concentration problem for
full-space quantum optimization, but raw feasible-state density can be
confounded by representation, Hamiltonian scale, classical optimization, and
objective choice. We isolate these factors in a controlled exact-statevector
study of shallow Penalty-X QAOA for resource-constrained shortest-path tasks.
A distinct-cardinality task construction removes repeated feasible-set levels,
and a scale-controlled Hamiltonian contract preserves every task optimum.
Discovery-stage diagnostics show that the original depth-three anomaly is
partly attributable to optimizer failure and that lower penalty energy need not
imply higher feasible probability. An exact-feasibility objective defines a
mechanistic capacity ceiling and motivates a CVaR objective without using the
held-out data. On 84 preregistered held-out tasks from 15 base graphs, CVaR at
depth three improves graph-level dilution compensation over mean-energy
optimization and is noninferior to the capacity ceiling at the frozen margin;
secondary audits show that feasible-entry gains generally retain optimal-route
concentration. A separate scaling study is deliberately reported as
heterogeneous and resource-censored: the objective ordering reverses at the
largest completed size, and the next size is excluded by the resource guard.
Search-theoretic counterexamples and query bounds clarify why edge-bit density
is not universal explicit-RCSP hardness and why useful structure must be charged
through information or implementation resources. We claim neither general
quantum advantage nor that CVaR evades membership-only search bounds.

## Package C -- structure-cost tradeoff

**Title:** Structure Is Not Free: Feasible-Space Dilution, Cost Relocation, and
Controlled Quantum Routing Evidence

**Abstract (DRAFT_FOR_REVIEW):**

Constraint-aware quantum optimization can escape a full-space feasibility
bottleneck only by receiving or constructing useful structure, yet different
methods charge that structure to different resources. We develop a common
accounting view that keeps posterior information, classical preprocessing,
state preparation, mixer construction, oracle access, validation, and dynamic
reuse separate. In a membership-query model with random fixed-cardinality
feasible sets, posterior projector concentration determines a necessary
structure--query tradeoff; finite advice gives a corresponding support-size
bound. These statements do not convert advice bits into runtime. For explicit
resource-constrained shortest paths, a unique-chain and serial-padding family
shows that raw edge-bit feasible density cannot alone imply problem hardness,
while a parallel-branch subclass has multiple-marked-search query complexity
when its explicit attribute array is accessed at counted cost. We use this
model separation to interpret a controlled shallow-QAOA study. Discovery-stage
audits identify scale, optimizer, and objective effects. Preregistered held-out
tests show that CVaR improves Penalty-X feasibility compensation over mean
energy and is noninferior to an exact-feasibility capacity ceiling at the frozen
margin. The larger-size response is heterogeneous: the ordering reverses at the
largest completed size and the next size is resource-censored. The resulting
framework explains where burden may move when feasibility structure is
injected, without claiming general quantum advantage, free mixers, universal
runtime lower bounds, or priority for the underlying search theory.
