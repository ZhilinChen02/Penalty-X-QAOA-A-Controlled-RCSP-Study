# Synthesis v1 Report

Audit label: `SECOND_PASS_MACHINE_AUDIT`

Source: `0657e603434cf7a7b7f9b7d1f5756dc1f85ae882`
Stage verdict: `COMPLETE` (subject to the explicitly required future human
reviews; those are readiness limitations, not missing Synthesis-v1 outputs).

## A. SYNTHESIS STATUS

`COMPLETE`

Synthesis v1 reconstructs and adversarially compares T1--T11, positions them
against 23 close primary sources across 25 logged search families, freezes a
1,403-file protected input inventory, maps empirical evidence and every
headline number, selects an empirical-primary publication architecture, and
prepares a claim-linked LaTeX scaffold and future-review package. It runs no new
QAOA optimization and uses no unfinished Phase 3B evidence.

## B. WORKTREE SAFETY

Initial details are frozen in `worktree_safety_baseline.json`; final details are
in `worktree_safety_final.json`.

| Worktree | Initial HEAD | Initial state | Final result |
|---|---|---|---|
| original empirical | `b9922aad...` | preserved dirty Phase 3B state; status hash `5846a0e4...`; diff hash `8a7dadaa...` | same HEAD/status/diff fingerprint; Phase 3B excluded |
| Theory-v2 | `68d0799b...` | clean | same HEAD, clean |
| Theory-v3 | `0657e603...` | clean | same HEAD, clean |
| Synthesis-v1 | base `0657e603...` | new isolated branch | only synthesis branch modified and committed |

All 1,403 protected files verify against
`protected_hashes_before.sha256`. No predecessor merge or push occurred.

## C. THEORY SECOND PASS

Primary verdict: `SECOND_PASS_PASS_WITH_CLARIFICATIONS`.

| ID | Status | Finding |
|---|---|---|
| T1 | `PASS` | The fixed-query phase-sensitive average bound reconstructs using an identity reference and two L2 Minkowski steps. |
| T2 | `PASS_WITH_CLARIFICATION` | Purification, feed-forward, early stopping and mixed states are covered under the counted direct-sum membership interface and a pathwise hard cap. |
| T3 | `PASS_WITH_CLARIFICATION` | Total membership access includes training, sampling, feedback and final calls; final trained depth is not bounded. |
| T4 | `PASS_WITH_CLARIFICATION` | The valid expected-query result is the integer truncation-plus-tail inequality, not substitution of the mean. |
| T5 | `PASS` | The explicit chain refutes raw-edge-density-only universal explicit-RCSP lower bounds. |
| T6 | `PASS_WITH_CLARIFICATION` | Route bijection and density factor are exact; coefficient bits grow O(log r), but explicit topology grows Theta(r). |
| T7 | `PASS_WITH_CLARIFICATION` | The branch reduction is a length-K random-access input-query theorem in the nontrivial target-success regime, not RAM time or compact-size hardness. |
| T8 | `PASS_WITH_CLARIFICATION` | Conditioning and the posterior projector norm are sound; caps/expectations must remain in the proved order. |
| T9 | `PASS_WITH_CLARIFICATION` | Duplicate maximizing labels are harmless; b is support-cardinality advice, not mutual information. |
| T10 | `PASS_WITH_CLARIFICATION` | The dimension result covers one accessible pre-search state, mixed advice and inaccessible purification, not refreshing or interaction. |
| T11 | `PASS_WITH_CLARIFICATION` | Effective bits/support are necessary posterior compression, neither sufficient nor implementation time. |

No mathematical error requiring a historical correction was found. There is no
`PROPOSED_THEORY_CORRECTIONS.md` because its conditional trigger did not occur.

## D. PRIOR ART

The audit logged 25 required/trace search families and compared 23 primary
sources. The closest cores are BBBV/hybrid search, Boyer et al. and Zalka on
tight/multiple-marked search, Høyer on arbitrary phases, Montanaro on prior
search, function-inversion advice/preprocessing tradeoffs, conditional guessing
probability, model-sensitive graph queries, constraint-aware QAOA, explicit
mixer/state-preparation cost shifting, and prior CVaR VQA work.

| Result family | Novelty status |
|---|---|
| `FIXED_QUERY_PHASE_SENSITIVE_FORM` | `POTENTIALLY_DISTINCT` |
| `ADAPTIVE_TOTAL_QUERY_SPECIALIZATION` | `LIKELY_REFORMULATION` |
| `POSTERIOR_PROJECTOR_THEOREM` | `POTENTIALLY_DISTINCT` |
| `FINITE_CLASSICAL_ADVICE_TRADEOFF` | `POTENTIALLY_DISTINCT` |
| `FINITE_QUANTUM_ADVICE_BOUND` | `POTENTIALLY_DISTINCT` |
| `EFFECTIVE_STRUCTURE_BITS` | `LIKELY_REFORMULATION` |
| `EXPLICIT_ATTRIBUTE_RCSP_BOUND` | `LIKELY_REFORMULATION` |
| `STRUCTURE_COST_RELOCATION_FRAMEWORK` | `LIKELY_REFORMULATION` |
| `THEORY_PLUS_RCSP_EMPIRICAL_INTEGRATION` | `NOVELTY_UNRESOLVED` |

Primary verdict: `THEORY_NOVELTY_UNRESOLVED`.
Secondary: `POTENTIALLY_DISTINCT_POSTERIOR_STRUCTURE_RESULT` and
`KNOWN_THEORY_NEW_APPLICATION_FRAME`.

No exact inspected source stated the additive phase coefficient or the same
posterior-projector/fixed-cardinality advice formulas. This non-detection is not
a priority result; independent forward/backward citation review remains
mandatory.

## E. EMPIRICAL EVIDENCE

- E0: v1 exposed 53 duplicate feasible-set levels among 175 tasks; v2 corrected
  to 140 tasks with zero duplicates over the frozen dilution range.
- E1: the scale-controlled contract retained correct ground states on 140/140
  tasks and reduced within-base scale drift.
- E2: the 56-task pilot found partial compensation and an exploratory p=3
  anomaly.
- E3: nested identity passed 168/168; continuation repaired the 29-run failure
  set in objective and 27/29 in feasibility gain; lower energy remained
  nonequivalent to higher feasibility.
- E4: discovery identified a 0.2193-decade O2 capacity gap and an O3 residual
  gap of 0.0069, selecting CVaR for prospective testing.
- E5: 84 held-out tasks/15 graphs confirmed H1 (0.354714949 decades, lower
  0.237378536, Holm p=0.000244141) and H2 (-0.00859515 against -0.10 margin,
  lower -0.03604875, same Holm p). O3 improved P_opt on 80/84 tasks.
- E6: Phase 3 completed through m=20, showed heterogeneous response including
  an O0/O3 reversal, and censored m=22. It is not a confirmed scaling law.
- E7: Theory-v1--v3 supplies access-model boundaries, not a direct rich-RCSP
  runtime interpretation.

Phase 1.2 and Phase 2 are not pooled. Post-holdout Phase-3 decomposition remains
descriptive. Phase 3B is `PENDING / OUTSIDE SYNTHESIS V1`.

## F. MASTER CLAIM SET

Recommended central empirical claims:

- `C-E0-UNIVERSE`, `C-E1-SCALE`: controlled construction and scale contract;
- `C-E3-OPT`: optimizer and objective-feasibility attribution;
- `C-E4-OBJDISC`: discovery-stage capacity comparison and O3 selection;
- `C-E5-H1`, `C-E5-H2`: preregistered held-out confirmation;
- `C-E5-POPT`, `C-E5-TAIL`: secondary route-quality and tail mechanism;
- `C-E6-SCALING`, `C-E6-BOTTLENECK`: censored heterogeneous scaling response.

Recommended scoped theory/boundary claims:

- `C-T1`, `C-T2`: membership-only average/hard-cap bounds;
- `C-T5`, `C-T6`: raw-density counterexample and padding;
- `C-T7`: explicit attribute-query subclass;
- `C-T8`--`C-T11`: posterior structure and necessary advice/support tradeoffs;
- `C-COST`: orthogonal cost-relocation ledger.

The matrix contains 26 rows. No scaffold claim exists without a matrix ID.

## G. REJECTED CLAIMS

- General quantum advantage: no end-to-end classical comparison or hardware.
- Universal explicit-RCSP hardness from raw phi_state: disproved by T5/T6.
- Explicit-RAM or compact-description interpretation of T7: outside its access
  model.
- CVaR breaks a membership-only theorem: false model transfer; CVaR uses rich
  energy information.
- O2 is a deployable objective: it is an exact-feasibility mechanistic ceiling.
- A confirmed global scaling law: contradicted by m=20 heterogeneity and m=22
  censoring.
- Effective bits equal runtime/gates: not implied.
- Feasible mixers/state preparation are free: their structure costs must be
  recorded.
- Quantum advice result covers refreshing/interaction: outside T10.
- Theorem, CVaR, or integrated-package priority: unresolved or preexisting.

## H. PUBLICATION STRATEGY

Favorable totals (5 is most favorable on every criterion): Option A integrated
22/50; Option B split 33/50; Option C empirical-primary 45/50.

Verdict: `EMPIRICAL_PRIMARY_PAPER_RECOMMENDED`.

Option C centers the mature preregistered result and complete mechanism chain
without depending on unresolved theory priority. Option B becomes viable if
external proof/prior-art review supports a defensible theory paper. Option A is
not recommended because its model heterogeneity, length, proof load, and
overclaim risk obscure the strongest evidence.

## I. MANUSCRIPT ARCHITECTURE

Recommended sequence:

1. Introduction
2. RCSP representations and access models
3. Controlled design and frozen evidence
4. Discovery-stage optimizer and objective attribution
5. Preregistered held-out CVaR results
6. Scaling response and resource ceiling
7. Membership-only boundary, posterior structure, and structure costs (compact;
   proofs appendix)
8. Related work
9. Limitations and open problems
10. Conclusion

The 13-file scaffold splits the compact theory boundary into model, global,
posterior, and explicit-RCSP modules for maintainability while retaining this
empirical-primary narrative.

## J. FIGURES/TABLES

Main figures: F1 access-model distinction; F2 chain/padding; F4 necessary
structure-query tradeoff; F5 evidence pipeline; F6 held-out H1/H2; F7
feasible-entry/conditional-optimality decomposition; F8 censored scaling
response; F9 cost relocation. F6/F7 may combine.

Main tables: T1 evidence stages; T2 controlled design; T3 optimizer attribution;
T4 preregistered H1/H2 statistics. Supplement: F3 theorem validation, T5 Phase-3
censoring, T6 full structure ledger, and all diagnostic plots.

## K. REVIEWER RISKS

Five most serious attacks:

1. the exact theory may be a reformulation of known search/advice results;
2. theory and empirical algorithms use different access models;
3. confirmation is narrow (Penalty-X p=3, synthetic DAGs, exact statevector,
   no hardware);
4. the scaling response reverses at m=20 and is censored at m=22;
5. the proofs, prior art, and empirical artifact lack independent external
   review/reproduction.

## L. READINESS GATES

| Gate | Status |
|---|---|
| G1 proof consistency | `PASS_WITH_LIMITATIONS` |
| G2 prior-art positioning | `PASS_WITH_LIMITATIONS` |
| G3 empirical integrity | `PASS` |
| G4 claim scope | `PASS` |
| G5 held-out separation | `PASS` |
| G6 scaling language | `PASS` |
| G7 cost relocation | `PASS` |
| G8 reproducibility path | `PASS` |
| G9 external-review readiness | `PASS_WITH_LIMITATIONS` |

Manuscript readiness: `READY_AFTER_EXTERNAL_PROOF_REVIEW`.

## M. HUMAN REVIEW REQUIREMENTS

Before submission, independent humans must:

1. review T1--T11, prioritizing T2 and T8--T10;
2. reproduce the advice/projector and one-shot dimension arguments;
3. conduct a primary-source priority review with forward/backward tracing;
4. verify that manuscript wording never transfers black-box theory to rich
   explicit RCSP;
5. reproduce Phase-2 numeric extraction, analysis-unit/multiplicity handling,
   and Phase-3 censoring from canonical rows.

The `review_package/` is material prepared for those reviewers; it is not a
completed external review.

## N. RECOMMENDED TITLE

Primary: **Feasible-Space Dilution and Objective Alignment in Shallow QAOA: A
Controlled RCSP Study**

Alternatives:

- *Feasible-Space Dilution in Quantum Optimization: Access-Model Boundaries and
  a Controlled RCSP Case Study*
- *Structure Is Not Free: Feasible-Space Dilution, Cost Relocation, and
  Controlled Quantum Routing Evidence*

## O. RECOMMENDED ABSTRACT

Small feasible subspaces create a practical concentration problem for
full-space quantum optimization, but raw feasible-state density can be
confounded by representation, Hamiltonian scale, classical optimization, and
objective choice. We isolate these factors in a controlled exact-statevector
study of shallow Penalty-X QAOA for resource-constrained shortest-path tasks. A
distinct-cardinality task construction removes repeated feasible-set levels,
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

## P. NEXT ACTION

`SEEK_EXTERNAL_PROOF_REVIEW`

Do not execute this recommendation automatically.

## Q. TESTS

- Full project suite: 165 passed in 188.78 seconds.
- Synthesis-only integrity: 13 tests.
- Post-generation integrity plus Theory-v3 immutability: 15 passed (shared
  filesystem status scan dominated the 1228.69-second runtime).
- Protected hashes: 1,403/1,403.
- LaTeX compiler: unavailable; no package installed. Static brace/environment,
  input, bibliography-key, claim-ID and placeholder checks pass.
- The historical Theory-v3 root assertion was updated for the isolated
  Synthesis-v1 root and strengthened with explicit Theory-v3 HEAD/clean checks;
  no scientific test was weakened.

## R. GIT

Branch: `synthesis/proof-review-manuscript-v1`
Commit message: `Freeze theory review and manuscript architecture`
Commit SHA: reported in the final handoff because a commit cannot contain its
own final object ID.
Push: no. Merge: no.

## Final verdicts

- Theory review: `SECOND_PASS_PASS_WITH_CLARIFICATIONS`
- Prior art primary: `THEORY_NOVELTY_UNRESOLVED`
- Prior art secondary: `POTENTIALLY_DISTINCT_POSTERIOR_STRUCTURE_RESULT`
- Publication architecture: `EMPIRICAL_PRIMARY_PAPER_RECOMMENDED`
- Manuscript readiness: `READY_AFTER_EXTERNAL_PROOF_REVIEW`
