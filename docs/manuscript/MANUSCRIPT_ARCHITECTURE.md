# Manuscript Architecture Freeze

Architecture: `EMPIRICAL_PRIMARY_PAPER_RECOMMENDED`.

This is a structured plan, not a manuscript draft. Every claim token below
resolves in `results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv`.

## Central research question

In a controlled edge-bit RCSP benchmark, how do optimizer and objective choices
alter feasible-state concentration as the feasible subspace dilutes, and which
information-access costs limit the scope of that evidence?

## Main thesis

Controlled RCSP evidence shows that feasible-space dilution must be interpreted
together with Hamiltonian scale, optimization adequacy, and objective alignment:
after discovery-stage diagnosis, preregistered held-out tests support CVaR over
mean-energy optimization and against a mechanistic feasibility-capacity ceiling
for shallow Penalty-X p=3, while high-size response is heterogeneous and
resource-censored; query theory then supplies scoped boundaries and a cost
ledger, not a direct universal runtime lower bound for rich explicit RCSP.

## Contributions

1. Frozen distinct-cardinality and scale-control design (`C-E0-UNIVERSE`,
   `C-E1-SCALE`).
2. Optimizer and objective attribution (`C-E2-PILOT`, `C-E3-OPT`).
3. Capacity-ceiling discovery and held-out objective choice (`C-E4-OBJDISC`).
4. Preregistered H1/H2 confirmation with route-quality audit (`C-E5-H1`,
   `C-E5-H2`, `C-E5-POPT`, `C-E5-TAIL`).
5. Heterogeneous and resource-censored scaling response (`C-E6-SCALING`,
   `C-E6-BOTTLENECK`).
6. Scoped access-model and cost-relocation boundary (`C-T5`, `C-T7`, `C-T8`,
   `C-T11`, `C-COST`).

## Frozen section sequence

### 1. Introduction

Lead with the empirical question and held-out answer, then state the scaling
limit. Introduce theory as a boundary against overinterpreting raw state density.
Claims: `C-E5-H1`, `C-E5-H2`, `C-E6-SCALING`, `C-LIM-NOADV`.

### 2. RCSP representations and access models

Separate the explicit graph problem, edge-bit Hilbert space, and candidate-route
attribute-query domain. Present the unique-chain/padding counterexample before
the parallel-branch query subclass. Claims: `C-T5`, `C-T6`, `C-T7`,
`C-LIM-MODELS`.

### 3. Controlled design and frozen evidence

Define task construction, distinct-cardinality correction, scale contract,
Penalty-X ansatz, O0--O3 objectives, analysis units, and discovery/holdout
separation. Claims: `C-E0-UNIVERSE`, `C-E1-SCALE`.

### 4. Discovery-stage optimizer and objective attribution

Report the exploratory depth anomaly, nested identity, continuation repair,
energy/feasibility misalignment, and O3 selection. Claims: `C-E2-PILOT`,
`C-E3-OPT`, `C-E4-OBJDISC`.

### 5. Preregistered held-out results

Present H1 and H2 at the graph unit, then secondary \(P_{\rm opt}\) and tail
audits. Label O2 a mechanistic ceiling. Claims: `C-E5-H1`, `C-E5-H2`,
`C-E5-POPT`, `C-E5-TAIL`.

### 6. Scaling response and resource ceiling

Show development, interpolation, m=20 extrapolation reversal, and m=22
censoring. Keep post-holdout decomposition descriptive. Claims:
`C-E6-SCALING`, `C-E6-BOTTLENECK`.

### 7. Membership-only boundary and structure costs

State T1/T2 compactly, explain total-query and expected-query scope, summarize
posterior/advice tradeoffs, and attach the orthogonal cost ledger. Full proofs
remain in the appendix. Claims: `C-T1`, `C-T2`, `C-T3`, `C-T4`, `C-T8`,
`C-T9`, `C-T10`, `C-T11`, `C-COST`.

### 8. Related work

Separate search/advice, constrained QAOA/mixers, CVaR, and RCSP/graph-query
literature. State that CVaR, amplitude amplification, and cost shifting
preexist. Claims: `C-E4-OBJDISC`, `C-COST`, `C-LIM-MODELS`.

### 9. Limitations and open problems

Freeze empirical, model, resource, priority, and external-review limitations.
Claims: `C-LIM-NOADV`, `C-LIM-MODELS`, `C-E6-SCALING`.

### 10. Conclusion

Return to the held-out empirical result, size limitation, and the principle that
structure access must be named and charged. Claims: `C-E5-H1`, `C-E5-H2`,
`C-E6-SCALING`, `C-COST`.

Detailed purposes, evidence, visuals, budgets, appendix routing, and reviewer
risks are frozen in `results/synthesis_v1/manuscript_section_matrix.csv`.

## Explicit nonclaims

- no general quantum advantage;
- no universal explicit-RCSP lower bound from raw edge-bit density;
- no confirmed global scaling law;
- no claim that CVaR breaks a membership-only barrier;
- no free structure injection;
- no theorem novelty or priority claim while review is unresolved;
- no hardware, natural-instance, ansatz-family, or asymptotic generalization.

## Drafting gate

The structure is ready, but theorem statements and prior-art positioning must be
sent for independent human review before a submission-ready prose freeze.
