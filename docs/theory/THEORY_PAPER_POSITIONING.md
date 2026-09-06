# Theory paper positioning after v2

## Decision

[INFERENCE] The evidence supports:

```text
KNOWN_SEARCH_THEORY_WITH_NEW_DILUTION_APPLICATION
```

## Rationale

[PRIOR_ART_SOURCE] The quadratic unstructured-search query barrier, exact
singleton optimality, multiple-mark amplitude amplification, arbitrary-phase
amplitude amplification, average-case query complexity, and QAOA search lower
bounds all have clear prior art.

[OPEN_GAP] The exact v1 phase-sensitive expression was not matched in
the inspected primary sources, but absence from one search cannot establish
novelty.

[V2_NEW_PROOF] The adaptive hard-cap and trained-total-query specialization is
now formally proved for membership-only access. Its useful contribution may be
clarifying precisely how training shots, measurements, stopping, and selected
transcript outputs enter a single query account.

[INFERENCE] The feasible-dilution framing, structure-injection taxonomy, and
integration with the project's RCSP experiments may be useful application and
interpretation contributions.

[OPEN_GAP] A stand-alone general theory paper would require stronger independent
novelty verification or a new structured/rich-oracle lower bound. The current
theory is best positioned as known search theory, a carefully audited
membership-oracle reformulation, and a boundary for interpreting the empirical
RCSP case study.

## Conservative level-specific wording

### Level 1: direct black-box theorem

[V1_THEOREM] For a feasible subset drawn uniformly among all size-$M$ subsets
and accessed only through fixed phase-membership queries, the average
feasibility probability of any $q$-query algorithm with instance-independent
initialization and inter-query unitaries is at most the audited phase-sensitive
bound, and hence at most $\min\{1,(2q+1)^2M/N\}$.

### Level 2: adaptive total-query theorem

[V2_NEW_PROOF] The same coarse average bound holds under intermediate
measurements, classical feed-forward, mixed states, and early stopping when the
complete oracle-only interaction has a deterministic hard cap of $q$
membership queries; history-dependent phases use the supremum phase coefficient
in each coherent query slot.

### Level 3: fixed-schedule QAOA

[V1_THEOREM] A fixed, instance-independent QAOA schedule with exactly one
binary feasibility query per layer requires
$\Omega(\phi^{-1/2})$ layers for constant average or uniform worst-case
success in the unstructured marked-set family.

### Level 4: trained QAOA

[V2_NEW_PROOF] If same-instance training receives all instance dependence only
through membership queries and has a deterministic total cap, the adaptive
bound applies to the sum of queries across every training shot, circuit
evaluation, feedback round, and final output—not to final trained depth alone.

### Level 5: RCSP

[INFERENCE] The result applies directly to oracle-RCSP, where route feasibility
is hidden behind membership access. No direct lower bound for standard
explicit-input RCSP is established; the project's explicit RCSP results remain
a case study whose relation to the oracle theorem is interpretive.
