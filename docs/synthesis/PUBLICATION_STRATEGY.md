# Publication Strategy

Primary recommendation: `EMPIRICAL_PRIMARY_PAPER_RECOMMENDED`.

Scores in `publication_strategy_matrix.csv` use 5 as most favorable for every
criterion. Thus a high `reviewer_risk` score means low/manageable risk, a high
`manuscript_length` score means manageable length, and a high
`chance_of_overclaim` score means low overclaim exposure.

## Option A: integrated paper

An integrated theory plus RCSP case-study paper has breadth, but its central
theory overlaps strongly with established search and advice literature while
the exact contribution priority remains unresolved. It would also ask one
manuscript to reconcile membership-only, explicit attribute-query, and rich
Hamiltonian-access models; reproduce a long discovery/confirmation chain; and
fit eleven theorems plus the resource ledger. That produces the highest scope
drift, proof burden, and reviewer-risk concentration. It is not recommended.

## Option B: two-paper split

A split produces cleaner internal models. The empirical paper is mature, while
the theory paper could focus on posterior concentration, advice, representation
dependence, and access models. However, the theory component should not become
a standalone submission until independent proof and prior-art reviews determine
whether its potentially distinct formulas support a defensible central
contribution. This remains the contingency if those reviews strengthen the
theory case.

## Option C: empirical primary paper

The strongest current publication unit centers the controlled empirical chain:
representation and scale audits, optimizer attribution, objective discovery,
preregistered held-out CVaR confirmation, and the heterogeneous/resource-
censored scaling response. The theory appears as a rigorous boundary and cost-
accounting lens. This framing does not depend on priority for Grover-like
search, does not claim the black-box theorem directly lower-bounds rich RCSP,
and gives the Phase-2 held-out result its appropriate evidential weight.

The recommended paper is therefore empirical-primary, not empirical-only. It
retains the raw-density counterexample, the explicit attribute-query subclass,
the membership-only bound, and the posterior/cost taxonomy in a compact main
section with full proofs in an externally reviewable appendix.

## Frozen story

Central research question: **In a controlled edge-bit RCSP benchmark, how do
optimizer and objective choices alter feasible-state concentration as the
feasible subspace dilutes, and which information-access costs limit the scope of
that evidence?**

Main thesis: Controlled RCSP experiments show that feasible-state dilution is
not merely a state-counting effect: Hamiltonian scale and optimization quality
must be controlled, and objective alignment materially changes feasible entry.
After discovery-stage attribution, preregistered held-out tests show that
CVaR improves Penalty-X p=3 compensation over mean energy and is noninferior to
an exact-feasibility capacity ceiling at the frozen margin, while larger-size
evidence is heterogeneous and resource-censored. Search-theoretic results then
bound only specified membership/access models and show why structure must be
charged through information, preprocessing, state preparation, richer queries,
or related resources rather than treated as free.

## Contributions (maximum six)

1. A distinct-cardinality, scale-controlled RCSP dilution design with immutable
   stage separation (`C-E0-UNIVERSE`, `C-E1-SCALE`).
2. Mechanistic attribution of the original p=3 anomaly to optimizer failure and
   objective--feasibility misalignment (`C-E2-PILOT`, `C-E3-OPT`).
3. An exploratory capacity-ceiling comparison that selected CVaR without using
   held-out data (`C-E4-OBJDISC`).
4. Preregistered graph-level confirmation that CVaR improves compensation over
   mean optimization and is noninferior to the exact-feasibility ceiling at the
   frozen margin (`C-E5-H1`, `C-E5-H2`, `C-E5-POPT`).
5. A larger-size response study that exposes an m=20 reversal and m=22 resource
   ceiling instead of asserting a global scaling law (`C-E6-SCALING`,
   `C-E6-BOTTLENECK`).
6. A scoped information-access boundary separating raw edge-bit density,
   attribute-query complexity, posterior structure, and implementation cost
   (`C-T5`, `C-T7`, `C-T8`, `C-T11`, `C-COST`).

## Explicit nonclaims

- No general quantum advantage.
- No universal explicit-RCSP lower bound from raw edge-bit density.
- No confirmed global empirical scaling law.
- No claim that CVaR breaks the membership-only black-box barrier.
- No free structure injection.
- No theorem-priority claim while prior art remains unresolved.
- No generalization beyond the controlled Penalty-X, shallow-depth,
  exact-statevector, synthetic-DAG setting without further evidence.
