# Primary-source prior-art audit

## Protocol

[PRIOR_ART_SOURCE] Network access was available. Twenty-one documented searches
screened primary publisher, DOI, proceedings, author, and arXiv pages. Eleven
sources were included after inspecting their abstracts and relevant theorem or
derivation sections. Search terms and source-level fields are preserved in
`prior_art_search_log.csv` and `prior_art_matrix.csv`.

[INFERENCE] This is an adversarial positioning audit, not an exhaustive novelty
opinion. Failure to locate an exact formula is not evidence that it is new.

## Closest search results

### General search lower bounds

[PRIOR_ART_SOURCE] Bennett, Bernstein, Brassard, and Vazirani (1997) supplied
the foundational oracle hybrid lower-bound method and the
$\Omega(\sqrt N)$ search barrier.

[PRIOR_ART_SOURCE] Boyer, Brassard, Høyer, and Tapp (1998), Section 3 and
Section 7, gave the exact Grover success formula with $t$ marked elements,
algorithms for known and unknown $t$, and a general lower bound yielding
$\Theta(\sqrt{N/t})$ search scaling.

[PRIOR_ART_SOURCE] Zalka (1999), equations (6)--(8) and Appendix 5.1, proved
exact Grover optimality for a unique marked item by an average-over-oracles
hybrid argument. The paper explicitly discusses replacing intermediate
measurement/classical control with coherent quantum hardware without adding
oracle invocations.

[PRIOR_ART_SOURCE] Dohotaru and Høyer (2009), Theorems 8 and 9, supplied a
self-contained exact angle-based lower bound for the unique-marked Grover
problem.

### Multiple marks, average case, and arbitrary phases

[PRIOR_ART_SOURCE] Brassard, Høyer, Mosca, and Tapp (2002), Theorems 2--4,
formalized amplitude amplification for general initial good probability $a$,
including measurement/randomized expected-time search variants and the
$\Theta(1/\sqrt a)$ construction.

[PRIOR_ART_SOURCE] Ambainis and de Wolf (2001) developed a general average-case
quantum query-complexity framework. Its input distribution is not the same
fixed-cardinality marked-subset success theorem, but average-case query analysis
is established prior art.

[PRIOR_ART_SOURCE] Høyer (2000), Theorem 1 and Section V, derived exact phase
matching for arbitrary-phase amplitude amplification. It is an achievability
and phase-control result, not the inspected v1 sum-of-query-perturbations upper
bound.

[PRIOR_ART_SOURCE] Gilyén, Arunachalam, and Wiebe (2019), Theorem 2, proved a
hybrid lower-bound method for controlled arbitrary phase oracles. Its bound is
expressed through a family-wide sum of squared/min-capped phase differences,
not the v1 factor
$(1+\sum_t|e^{-i\gamma_t}-1|)^2\phi$.

### QAOA and variational applications

[PRIOR_ART_SOURCE] Benchasattabuse et al. (arXiv:2308.15442v4), Corollary 2 and
Theorem 5, derive QAOA-round lower bounds for unstructured search and recover
$\Omega(\sqrt{N/m})$ scaling under stated initial-state, mixer, and phase
separator conditions. A general claim that the present work is the first QAOA
application of Grover-style search lower bounds is therefore unavailable.

[PRIOR_ART_SOURCE] Gilyén, Arunachalam, and Wiebe also analyze query accounting
for training quantum optimization procedures, including QAOA, under probability
and phase-oracle access. Their objective and result differ from the present
marked-subset success theorem, but variational-training oracle accounting is
not a new topic.

### Variable-time search and explicit RCSP

[PRIOR_ART_SOURCE] Ambainis, Kokainis, and Vihrovs (2023) study variable checking
times and matching lower bounds in a distinct variable-time search model. That
work does not justify substituting a transcript-dependent mean stopping count
into a convex hard-cap success bound.

[PRIOR_ART_SOURCE] Beasley and Christofides (1989) define RCSP through an
explicit graph, additive resource requirements, and budgets. This is an
explicit-input optimization model, not a hidden marked-set oracle.

## Result-by-result comparison

| Target | Audit conclusion | Tag |
|---|---|---|
| P-A: $q=\Omega(\sqrt{N/M})$ | Clearly preexists for unstructured multiple-mark search. | `PRIOR_ART_SOURCE` |
| P-B: exact/near-exact success upper bound | Exact singleton bounds and near/exact Grover tradeoffs preexist; multiple-mark constructions are known. | `PRIOR_ART_SOURCE` |
| P-C: average over random marked subsets | Singleton average-over-oracles and general average-case frameworks preexist; the exact fixed-$M$ formulation was not matched in inspected sources. | `INFERENCE` |
| P-D: precise phase-sensitive sum | No exact match located; arbitrary-phase hybrid methods exist. Status remains unresolved. | `OPEN_GAP` |
| P-E: $(2q+1)^2\phi$ under arbitrary inter-query unitaries | Coarse $O(q^2\phi)$ and stronger exact singleton bounds preexist; exact multiple-$M$ wording was not established as distinct. | `INFERENCE` |
| P-F: adaptive measurements/feed-forward | Standard coherent replacement is explicitly recognized in prior search work; v2 supplies a full specialization. | `PRIOR_ART_SOURCE` |
| P-G: QAOA/variational application | QAOA search lower bounds and variational oracle accounting preexist. | `PRIOR_ART_SOURCE` |
| P-H: feasible-density/dilution interpretation | Related constrained-QAOA feasibility discussions exist; the project's exact terminology/integration may be a reformulation, not established novelty. | `INFERENCE` |

## Verdict

[INFERENCE] Primary prior-art verdict:

```text
COARSE_RESULT_PREEXISTS_PHASE_SENSITIVE_FORM_UNCLEAR
```

[INFERENCE] The safest potentially contributory elements are the explicit
phase-sensitive reformulation, the complete hard-cap trained-total-query
specialization, the information-access/structure-injection taxonomy, and the
integration with the project's empirical dilution study. None is labeled novel.

## Publication requirement

[OPEN_GAP] Independent expert search and source checking remain required before
any novelty, priority, or first-proof statement. The current audit does not
authorize such wording.
