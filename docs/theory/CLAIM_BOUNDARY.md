# Claim boundary for the global dilution theorem

## G1 — direct black-box theorem

**Proved.** The theorem applies to arbitrary size-(M) marked subsets when the
initial state, phases, and all inter-query unitaries are independent of the
particular subset and every piece of subset information enters through counted
phase-membership queries. The upper bound is a uniform-random-set average. It
allows arbitrary fixed unitaries, arbitrary ancillas, and entanglement.

## G2 — worst-case global-QAOA corollary

**Proved after scope refinement.** If a global-QAOA method claims a uniform
success guarantee over a class containing every binary Hamiltonian
(H_{\mathcal F}=I-\Pi_{\mathcal F}), and its schedule is fixed independently of
ℱ, then one cost layer is one marked-set phase query up to global phase. The
existential hard set converts the average theorem into a worst-case depth lower
bound for that class. The identity (p=q) is specific to one relevant query per
layer; with at most (c) queries per layer use (q\le cp).

## G3 — structured RCSP statement

**Unproved.** The theorem does not show that every natural RCSP cost Hamiltonian
obeys the same pointwise bound. RCSP inputs expose graph, cost, resource, and
constraint structure, and their feasible sets are not arbitrary marked subsets.
An RCSP claim requires either an explicit embedding of a sufficiently
unstructured marked-set family into the RCSP instance class or a separate
structural lower bound.

## Allowed wording

“For fixed-query algorithms whose only information about an unknown size-(M)
feasible set is supplied by phase-membership queries, the average feasible
probability over uniformly random marked sets is at most
[the phase-sensitive bound]. Hence constant average success, or a uniform
guarantee over that black-box family, requires order
√(N/M) counted queries. Fixed instance-independent binary-feasibility QAOA is
a special case.”

## Prohibited wording

“Every QAOA or every RCSP instance needs depth Ω(φ⁻¹⁄²), regardless of
initialization, mixers, training, preprocessing, or structured oracle access.”

The prohibited sentence changes an average black-box result into a pointwise,
structure-independent statement and hides potentially dominant resources.

## Explicit nonclaims

- no pointwise upper bound for every feasible set;
- no lower bound for feasible-set-dependent initialization or mixers;
- no final-depth-only claim for instance-trained variational procedures;
- no direct lower bound for rich value oracles;
- no direct structured-RCSP theorem;
- no exact universal Grover upper bound or exact optimality proof;
- no novelty or prior-art claim.
