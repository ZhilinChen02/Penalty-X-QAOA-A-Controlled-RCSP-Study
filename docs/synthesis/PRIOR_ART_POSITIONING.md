# Primary-Source Prior-Art Positioning

Audit date: 2026-08-29. Primary status:
`THEORY_NOVELTY_UNRESOLVED`. Secondary status:
`POTENTIALLY_DISTINCT_POSTERIOR_STRUCTURE_RESULT`.

This search used journal publishers, official proceedings, arXiv originals,
author manuscripts, and identifiable monographs only. It is systematic but not
proof of priority. No use of `NEW`, `FIRST`, or unqualified `NOVEL` is permitted.
The 25-query search log and 23-source comparison are in
`results/synthesis_v1/prior_art_search_log.csv` and
`prior_art_comparison_matrix.csv`.

## Closest established cores

BBBV, Boyer--Brassard--Høyer--Tapp, Zalka, and amplitude amplification establish
the black-box hybrid, multiple-marked \(\Theta(\sqrt{N/M})\), exact/tight
success, and matching-algorithm cores. Høyer treats arbitrary query phases.
Ambainis and de Wolf give an average-case query framework. Consequently, the
asymptotic search core behind T1, T2, and T7 is clearly preexisting.

Montanaro and later prior-knowledge work study quantum search under a known
prior distribution. Nayebi--Aaronson--Belovs--Trevisan and subsequent work give
classical/quantum advice and preprocessing tradeoffs for function inversion.
Aaronson and Aaronson--Kuperberg establish broader quantum-advice limitations
and separations. Conditional min-entropy and state-discrimination work provide
an established information-theoretic language for guessing with side
information. These are close to the interpretation of posterior concentration,
but the inspected sources use non-equivalent models.

Graph-query complexity is explicitly access-model dependent in the work of
Dürr and coauthors and later shortest-path work. Foundational succinct-graph
complexity likewise establishes that representation matters. No inspected
source states the exact parallel-branch explicit-attribute RCSP reduction or
the serial edge-bit-density padding formula, but both are elementary enough to
be positioned as applications/reformulations unless a broader priority review
supports more.

Constraint-aware alternating operators, warm starts, and Grover mixers already
inject feasible-space structure. Bärtschi and Eidenbenz explicitly describe
shifting complexity from mixer design to state preparation. Barkoutsos and
coauthors already apply CVaR to variational quantum optimization. The synthesis
therefore claims neither CVaR novelty nor the general idea of cost relocation.

## PA1--PA12 comparison

| Question | Finding |
|---|---|
| PA1 \(\Omega(\sqrt{N/M})\) multiple-marked search | Clearly preexisting (Boyer et al.; Zalka; amplitude amplification literature). |
| PA2 exact or near-exact success after \(q\) queries | Preexisting in standard Grover search models. |
| PA3 average random-subset formulation | Average-case search/query theory preexists; the inspected sources did not state the same fixed-cardinality projector formulation. |
| PA4 exact \(1+\sum_t|e^{-i\gamma_t}-1|\) coefficient | Not located; arbitrary-phase search itself clearly preexists. |
| PA5 adaptive measurement/feed-forward treatment | Standard purification/deferred-measurement query machinery; likely reformulation. |
| PA6 total-query trained-VQA specialization | No exact specialization located; it is a standard end-to-end query-accounting application. |
| PA7 \((2q+1)^2 2^b\phi\) classical-advice bound | Exact fixed-cardinality formula not located; strong asymptotic advice/preprocessing cores preexist in other models. |
| PA8 posterior-projector \(\Lambda(S)\) | Exact formulation not located; prior-search and posterior guessing analogues preexist. |
| PA9 finite-dimensional quantum-advice analogue | Advice/query tradeoffs preexist; exact one-shot marked-subset dimension formula not located. |
| PA10 effective-support interpretation | Prior concentration/effective search ordering preexists; the algebraic \(K_{\rm eff}\) parameterization appears a reformulation. |
| PA11 explicit-attribute parallel-path RCSP | No exact source located; multiple-marked reduction is immediate and should be sold as a scoped application. |
| PA12 Hilbert-density representation padding | General representation/succinctness sensitivity preexists; exact RCSP serial-padding statement not located. |

“Not located” means only that this search did not find an exact match. It does
not establish priority.

## Per-result novelty statuses

| Result family | Status | Reason |
|---|---|---|
| `FIXED_QUERY_PHASE_SENSITIVE_FORM` | `POTENTIALLY_DISTINCT` | Exact additive phase coefficient not located; hybrid and arbitrary-phase cores preexist. |
| `ADAPTIVE_TOTAL_QUERY_SPECIALIZATION` | `LIKELY_REFORMULATION` | Deferred measurement and end-to-end query accounting are standard. |
| `POSTERIOR_PROJECTOR_THEOREM` | `POTENTIALLY_DISTINCT` | Exact \(\Lambda(S)\) fixed-cardinality formulation not located amid close prior-search/guessing work. |
| `FINITE_CLASSICAL_ADVICE_TRADEOFF` | `POTENTIALLY_DISTINCT` | Exact finite-alphabet formula not located; asymptotic advice cores preexist. |
| `FINITE_QUANTUM_ADVICE_BOUND` | `POTENTIALLY_DISTINCT` | Exact one-shot dimension statement not located; broader quantum-advice tradeoffs preexist. |
| `EFFECTIVE_STRUCTURE_BITS` | `LIKELY_REFORMULATION` | Algebraic posterior-concentration reparameterization. |
| `EXPLICIT_ATTRIBUTE_RCSP_BOUND` | `LIKELY_REFORMULATION` | Direct multiple-marked search reduction in a legitimate new application model. |
| `STRUCTURE_COST_RELOCATION_FRAMEWORK` | `LIKELY_REFORMULATION` | Cost shifting is explicit in prior structured-mixer work; the ledger is a synthesis framework. |
| `THEORY_PLUS_RCSP_EMPIRICAL_INTEGRATION` | `NOVELTY_UNRESOLVED` | No exact package found, but integration novelty needs field-wide review. |

## Safe positioning

The paper may say that it applies established quantum-search principles to
separate representation density, candidate-domain query complexity, posterior
structure, and implementation cost in a controlled RCSP study. It may present
the exact posterior-projector form as a potentially distinct formulation
pending review. It may not claim priority for the search bound, CVaR, feasible
mixers, advice-query tradeoffs, or the integrated package.

Independent human prior-art review should specifically trace citations forward
and backward from Boyer et al., Montanaro, Nayebi et al., Aaronson--Kuperberg,
and Bärtschi--Eidenbenz, and check recent work published after their citation
networks.
