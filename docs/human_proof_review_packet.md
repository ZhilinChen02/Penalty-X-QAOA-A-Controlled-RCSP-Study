# Human Proof-Review Packet

## Status and purpose

This packet is prepared for independent review by a quantum-information
researcher. **No independent human proof review has yet occurred.** The
statements below delimit the manuscript's empirical interpretation; they are
not lower bounds on the rich-energy QAOA experiment and do not establish
quantum advantage.

The authoritative manuscript statements are in
`overleaf/sections/08_theory.tex`, with proofs in
`overleaf/appendices/appendix_theory.tex`. Supporting audit notes are under
`docs/theory/`. If wording here and the manuscript ever diverge, review the
manuscript statement and proof, then record the discrepancy rather than
silently reconciling it.

## Global model and notation

- The label domain is \(\Omega=\{1,\ldots,N\}\).
- The marked set \(F\) is uniform over all size-\(M\) subsets unless a
  conditional posterior is explicitly introduced.
- \(\phi=M/N\) and
  \(\Pi_F=\sum_{x\in F}|x\rangle\!\langle x|\).
- The membership phase query is \(O_F=I-2\Pi_F\). The phase-sensitive query
  is \(Q_F(\gamma)=I+(e^{-i\gamma}-1)\Pi_F\), with arbitrary ancillas
  suppressed in the notation.
- A query bound is average over the fixed-cardinality prior and the
  algorithm's internal randomness. It is not pointwise over every marked set.
- A *pathwise hard cap* means every coherent history makes at most \(q\)
  counted membership calls. Training, sampling, feedback, validation, and the
  final circuit are all included when they use that interface.
- The empirical QAOA cost phase supplies a multilevel RCSP energy. That is a
  richer access model than binary membership, so none of the membership-only
  bounds directly lower-bounds O0--O3.

## Dependency map

```text
phase-sensitive average bound
  +-- adaptive membership-only dilution bound
  |     +-- expected-query truncation
  |     +-- explicit-attribute-query RCSP lower bound
  +-- posterior structure bound
  |     +-- finite classical-advice lemma and tradeoff
  +-- one-shot quantum-advice dimension bound

raw-density counterexample -- independent representation result
edge-subdivision padding  -- independent representation result
posterior-projector lemma -- notation/basic fact used by posterior theorem
multiple-marked search    -- supplies attribute-query upper bound
```

The Grover/BBBV hybrid and multiple-marked-search core is standard. The exact
posterior-projector and one-shot advice formulations remain novelty-unresolved.

## 1. Phase-sensitive average bound

### Statement

For a normalized fixed-query pure-state algorithm

\[
|\psi_F\rangle=V_qQ_F(\gamma_q)\cdots V_1Q_F(\gamma_1)V_0
|\psi_{\rm in}\rangle,
\]

whose input, interquery unitaries, and phases are independent of the particular
\(F\), its final marked probability obeys

\[
\mathbb E_F P_F\leq
\min\!\left\{1,
\left(1+\sum_{t=1}^q|e^{-i\gamma_t}-1|\right)^2\phi
\right\}.
\]

### Assumptions and dependencies

- Uniform fixed-cardinality marked-set prior.
- Fixed query schedule; arbitrary \(F\)-independent ancilla and unitaries.
- No \(F\)-dependent input state or uncharged side information.
- Uses only the identity-oracle reference path, projection contractivity, and
  the \(L^2(F)\) triangle inequality.

### Proof outline

1. Replace all queries by identity and denote the normalized pre-query
   reference states by \(|\varphi_t\rangle\).
2. Because each reference state is independent of \(F\), its expected marked
   squared norm is exactly \(\phi\).
3. Hybridize one slot at a time. The distance increment is at most
   \(c_t\|\Pi_F\varphi_t\|\), where
   \(c_t=|e^{-i\gamma_t}-1|\).
4. Minkowski gives an \(L^2(F)\) final-state distance of at most
   \(\sqrt\phi\sum_t c_t\).
5. Projection contractivity and a second Minkowski step add the final
   identity-reference marked norm, yielding the displayed square-root bound;
   square it and cap by one.

### Possible failure points to inspect

- Both Minkowski steps must be taken in \(L^2(F)\), not by replacing a mean
  norm with a norm of the mean.
- The reference state used at each slot must be independent of \(F\).
- Ancilla identity factors and the final projection must be carried
  consistently.
- The result is average-case; no pointwise statement follows.

### Boundary cases and prior art

- \(M=0\): success is zero. \(M=N\): the probability cap is essential.
- \(q=0\): the bound reduces to \(\phi\).
- \(\gamma_t\equiv0\pmod{2\pi}\): the corresponding query contributes zero.
- The hybrid-search core is standard. Whether the exact phase-sensitive
  expression is already present in this form requires human prior-art review.

## 2. Adaptive membership-only dilution theorem (priority review)

### Statement

An adaptive protocol with a pathwise hard cap of \(q\) binary membership
queries satisfies

\[
\mathbb E_F P_{\rm success}\leq
\min\{1,(2q+1)^2\phi\}.
\]

The expectation includes the random fixed-cardinality set and internal
randomness.

### Assumptions and dependencies

- The only \(F\)-dependent operation is the counted membership oracle.
- Initial states, interquery operations, controls, and ancillas are otherwise
  independent of \(F\).
- Every execution history has at most \(q\) calls.
- The selected classical label is copied into a designated output/query
  register before testing success.
- Derived from the phase-sensitive theorem with phase \(\pi\).

### Proof outline

1. Purify mixed initial states and classical randomness.
2. Replace measurements and instruments by Stinespring isometries; retain
   outcomes in orthogonal transcript registers and implement feed-forward
   coherently.
3. Pad early-halting branches to \(q\) slots by querying an isolated scratch
   register that never recouples to the output.
4. Reversibly copy the final selected label to the measured output register.
5. Apply the phase-sensitive hybrid with
   \(\|O_F-I\|\) contribution \(2\|\Pi_F\varphi_t\|\), obtaining
   \((2q+1)\sqrt\phi\) at the amplitude level.

### Possible failure points to inspect

- Verify that the scratch-query padding is a valid ordinary query and cannot
  leak back into the output through later operations.
- Verify that purification covers transcript-dependent stopping without
  introducing hidden \(F\)-dependent unitaries.
- A history-controlled direct sum counts as one call only if that controlled
  membership interface is explicitly available.
- Confirm that an output computed from the full transcript is covered by the
  reversible-copy construction.
- Confirm that *all* training and evaluation calls are charged when applying
  the theorem to an adaptive variational procedure.

### Boundary cases and prior art

- \(q=0\) gives the random-guess average \(\phi\).
- The theorem becomes noninformative once \((2q+1)^2\phi\geq1\).
- The bit-query oracle has the same coarse factor because
  \(B_F-I=\Pi_F\otimes(X-I)\) and \(\|X-I\|=2\).
- The Grover/BBBV hybrid core and its order are standard; no theorem priority
  is claimed. Review should focus on the adaptive/purified statement and its
  interface accounting.

## 3. Expected-query truncation (priority review)

### Statement

If the nonnegative integer-valued membership-call count \(Q\) has mean
\(\bar q\), then for every deterministic integer \(T\geq0\),

\[
\mathbb E P\leq\min\!\left\{1,
\frac{\bar q}{T+1}+
\min\{1,(2T+1)^2\phi\}\right\}.
\]

### Assumptions and dependencies

- \(Q\) may depend on the transcript and on \(F\).
- The protocol otherwise satisfies the membership-only assumptions.
- Uses the hard-cap theorem plus Markov's inequality for an integer variable.

### Proof outline

Convert all executions with \(Q>T\) into declared failures. The retained
protocol has pathwise cap \(T\). The original success probability is at most
the retained success plus \(\Pr(Q>T)\), and
\(\Pr(Q>T)=\Pr(Q\geq T+1)\leq\bar q/(T+1)\).

### Possible failure points to inspect

- One may **not** substitute \(q=\mathbb E Q\) directly into the hard-cap
  theorem.
- The integer threshold is \(T+1\), not \(T\).
- Truncation must turn long runs into failures rather than outputting whatever
  label is present at the cutoff.
- If \(Q\) is independently drawn before the interaction, conditioning can
  yield a separate \(\mathbb E(2Q+1)^2\) bound. That argument does not apply
  to transcript-dependent stopping.

### Boundary cases and prior art

- \(T=0\) gives \(\bar q+\phi\), capped at one.
- Optimization over integer \(T\) is permitted after the inequality is
  established; choosing \(T\) from the realized transcript is not.
- This is an elementary truncation repair, not presented as a novel
  expected-query lower-bound technique.

## 4. Raw-density counterexample

### Statement

For every \(m\geq1\), an explicit \(m\)-edge RCSP instance has raw edge-bit
feasible density \(2^{-m}\), yet its unique exact route can be read and
output in \(O(m)\) time.

### Assumptions, proof, and checks

Use a directed chain of \(m\) edges, resource and objective coefficient one,
and budget \(m\). Exactly one of the \(2^m\) edge selections is the route;
adjacency-list traversal outputs it in linear time. Check that the time model
includes reading/outputting \(m\) edge identifiers and that the conclusion is
only that raw edge-bit density alone cannot imply a universal explicit-input
lower bound. It does not deny representation-specific dilution.

### Prior-art/novelty status

The construction is elementary and is not asserted to be a priority result.

## 5. Edge-subdivision representation-padding lemma

### Statement

Replacing one edge by a private serial chain of \(r\geq1\) edges, each with
\(1/r\) of every rational additive coefficient, preserves routes,
feasibility, objective ordering, and tied optima while multiplying raw
edge-bit density by \(2^{-(r-1)}\).

### Proof outline and checks

Private degree-one internal vertices force traversal of the entire new chain,
giving a route bijection. Additive totals are unchanged. The number of
feasible route encodings is unchanged while the bitstring denominator gains
\(r-1\) variables. Check rational encoding length: coefficient bit length
grows only logarithmically in \(r\), but the explicit topology and route
output grow as \(\Theta(r)\). This prevents a false compact-input exponential
hardness reading.

## 6. Explicit-attribute-query RCSP theorem

### Statement

For \(K\) known two-edge branches, exactly \(M\) marked by a counted
random-access attribute oracle, and fixed target success
\(\tau\in(0,1]\) with \(M/K<\tau\),

\[
Q^{\rm RCSP}_{\tau}(K,M)=\Theta_{\tau}(\sqrt{K/M}).
\]

For exact success this holds for \(1\leq M<K\); \(M=K\) needs no query.

### Assumptions and dependencies

- The topology is known and contains \(K\) parallel two-edge branches.
- A length-\(K\) attribute array has exactly \(M\) ones and is available via
  counted quantum random-access queries.
- Equal objective costs reveal no marked index.
- The lower bound uses the membership theorem; amplitude amplification gives
  the upper bound.

### Proof outline and checks

Assign resource one to each first edge and resource one/two to the second edge
according to the attribute bit, with budget two. Branch feasibility is exactly
the queried bit. The problem is therefore multiple-marked search. Check the
zero-query regime carefully: when \(M/K\geq\tau\), uniform guessing already
meets the target, so the unqualified all-\(M\) formula is false. Also verify
that this counts array queries, not RAM time, circuit gates, or a compact graph
description; the explicit input has \(\Theta(K)\) cells.

### Prior-art/novelty status

The multiple-marked-search complexity is standard. The RCSP embedding is an
explicit access-model illustration, not a claim of a new search lower bound.

## 7. Posterior-projector lemma

### Statement

For supported classical advice value \(S=s\), define

\[
\overline\Pi_s=\mathbb E[\Pi_F\mid S=s],\qquad
\lambda_s=\|\overline\Pi_s\|_\infty.
\]

Then

\[
\operatorname{Tr}\overline\Pi_s=M,
\quad \lambda_s=\max_x\Pr(x\in F\mid S=s),
\quad \phi\leq\lambda_s\leq1.
\]

### Proof and checks

The operator is diagonal in the label basis with posterior inclusion
probabilities as entries. Their sum is the conditional expectation of the
fixed cardinality \(M\). Inspect the fixed-cardinality assumption: if the
cardinality were random, the trace and lower bound would need alteration.

## 8. Posterior structure theorem (priority review)

### Statement

Let classical side information \(S\) be produced before search and define
\(\Lambda(S)=\mathbb E_S\lambda_S\). Under the same pathwise hard-cap
membership model,

\[
\mathbb E P_{\rm success}\leq
\min\{1,(2q+1)^2\Lambda(S)\}.
\]

The sharper conditional phase-sensitive form is

\[
\mathbb E[P\mid S=s]\leq
\min\left\{1,\left(1+\sum_t c_t(s)\right)^2\lambda_s\right\}.
\]

### Assumptions and dependencies

- \(S\) is classical and available before the search interaction.
- Conditional on \(S=s\), all residual \(F\)-dependence enters through
  counted membership calls.
- Advice generation is not silently free if it itself queries \(F\); its
  resource cost lies outside this conditional search statement and must be
  reported separately.
- Uses the phase-sensitive hybrid and posterior-projector lemma.

### Proof outline

1. Condition on supported \(s\). Identity-oracle reference states may depend
   on \(s\), but not on residual \(F\) given \(s\).
2. Their conditional expected marked mass is
   \(\langle\psi_s|\overline\Pi_s|\psi_s\rangle\leq\lambda_s\).
3. Repeat both hybrid/Minkowski steps conditionally to obtain the capped
   phase-sensitive inequality.
4. Average the already capped conditional result. For the coarse form use
   \(c_t(s)\leq2\), then linearity and the outer probability cap.

### Possible failure points to inspect

- Conditioning must be restricted to supported advice values.
- The identity-reference evolution must remain independent of residual
  \(F\) after conditioning.
- Do not replace
  \(\mathbb E[\min\{1,a\lambda_S\}]\) by equality with
  \(\min\{1,a\mathbb E\lambda_S\}\); only the displayed inequality is used.
- Confirm that arbitrary posterior correlations among labels do not affect
  the operator-norm argument.
- Confirm that the theorem is only necessary posterior concentration, not a
  construction of an algorithm or a cost model for producing \(S\).

### Boundary cases and prior art

- Uninformative \(S\): \(\Lambda=\phi\), recovering the base theorem.
- Fully identifying advice: \(\Lambda=1\), making the bound uninformative.
- The formulation is adjacent to quantum search with advice, min-entropy
  leakage, and preprocessing/query tradeoffs. The exact posterior-projector
  form requires independent prior-art judgment; the manuscript labels this
  novelty-unresolved.

## 9. Finite classical-advice lemma (priority review)

### Statement

If the supported classical advice alphabet has size at most \(2^b\), then

\[
\Lambda(S)\leq\min\{1,2^b\phi\}.
\]

Consequently

\[
\mathbb E P_{\rm success}
\leq\min\{1,(2q+1)^2 2^b\phi\}.
\]

### Proof outline

For every supported \(s\), choose a maximizing label \(x_s\). Then

\[
\Lambda=\sum_s\Pr(S=s,x_s\in F)
\leq\sum_s\Pr(x_s\in F)
=|\operatorname{supp}S|\phi.
\]

The last equality holds term by term under the uniform fixed-cardinality
prior, even if several advice values choose the same label.

### Possible failure points to inspect

- Duplicated maximizing labels cause repeated marginal terms; this may loosen
  but does not invalidate the upper bound.
- The alphabet-size hypothesis concerns supported values. Shannon entropy
  alone does not imply this support bound.
- The resulting bit/query inequality is necessary only. It does not turn
  advice bits into preprocessing time, memory, gates, or state-preparation
  cost.
- A candidate set of size \(K\) implies \(\lambda=M/K\) only under a uniform
  conditional fixed-size posterior over that set.

### Boundary cases and prior art

- \(b=0\) recovers \(\Lambda=\phi\).
- The cap by one matters when \(2^b\phi>1\).
- The counting argument is elementary and consistent with min-entropy leakage
  ideas; no broad conceptual novelty is claimed. Whether this exact lemma has
  an earlier identical statement remains for human literature review.

## 10. One-shot quantum-advice proposition (priority review)

### Statement

Suppose one \(F\)-dependent density operator \(\rho_F\) on a total accessible
advice Hilbert space of dimension \(d\) is supplied before an otherwise
membership-only fixed-query interaction. Then

\[
\mathbb E P_{\rm success}\leq
\min\left\{1,
\left(1+\sum_t c_t\right)^2d\phi\right\},
\]

with coarse hard-cap form \((2q+1)^2d\phi\), capped at one.

### Assumptions and dependencies

- Exactly one pre-search advice state is supplied.
- \(d\) is the joint dimension of all simultaneously accessible advice
  registers.
- After receipt, the only further \(F\)-dependent operations are counted
  membership queries.
- The interquery schedule is fixed in the stated proposition.
- Mixed advice and entanglement with an inaccessible purifier are allowed.
- Uses the phase-sensitive hybrid after replacing the reference-overlap bound.

### Proof outline

For an \(F\)-independent trace-preserving reference channel \(A\), use
\(\rho_F\preceq I_d\) to obtain

\[
\mathbb E_F\operatorname{Tr}[(\Pi_F\otimes I)A(\rho_F)]
\leq \phi\operatorname{Tr}A(I_d)=d\phi.
\]

Choose canonical purifications of the advice states; the inaccessible
purifying register does not enlarge the counted accessible dimension or the
marked projected norm. Substitute \(d\phi\) for \(\phi\) in the
phase-sensitive hybrid.

### Possible failure points to inspect

- Confirm the operator inequality \(\rho_F\preceq I_d\) is used on the
  accessible advice space and that positivity of \(A\) preserves it.
- Verify \(\operatorname{Tr}A(I_d)=d\) for a trace-preserving channel even
  when its output space is larger.
- Scrutinize the canonical-purification step: it must preserve the relevant
  projected norm without treating the inaccessible reference as free
  accessible advice.
- Check that the hybrid's reference channel can be taken \(F\)-independent at
  every slot despite the \(F\)-dependent initial advice state.
- Fresh copies, refreshed advice, interactive providers, and reusable
  preprocessing are not covered. Neither is an unbounded-dimensional
  classical label smuggled into the advice interface.

### Boundary cases and prior art

- \(d=1\) recovers the no-advice bound.
- When \(d\phi\geq1\), the result may be vacuous.
- Multiple advice registers use their product/joint dimension, not the sum.
- Search with quantum advice and function-inversion-with-advice literature is
  adjacent. The exact one-shot dimension formulation remains
  novelty-unresolved and needs specialist review.

## Review questions requiring an explicit human answer

1. Is each adaptive purification/padding step implementable with exactly the
   claimed number of membership slots under the stated oracle interface?
2. Does the output-register construction cover arbitrary transcript-derived
   classical outputs without an extra counted query?
3. Is the conditional posterior hybrid valid for correlated
   fixed-cardinality posteriors, including all cap/expectation operations?
4. Is the expected-query truncation statement the strongest justified claim
   made anywhere in the manuscript, with no hidden use of
   \(q=\mathbb E Q\)?
5. Does the quantum-advice proof correctly keep the dimension factor at
   \(d\), including mixed states and inaccessible purification?
6. Are the endpoint qualifications in the explicit-attribute theorem
   sufficient, particularly \(M/K<\tau\) and \(M=K\)?
7. Do any statements inadvertently imply a lower bound for rich multilevel
   energy access, explicit-input RCSP time, or the empirical CVaR optimizer?
8. Which exact formulations, if any, are already present in prior work?

## Requested review record

The reviewer should record one status per item: `VALID`, `VALID_WITH_EDIT`,
`UNCLEAR`, or `INVALID`.

| Item | Status | Required edit or concern | Reviewer/date |
|---|---|---|---|
| Phase-sensitive average bound | PENDING |  |  |
| Adaptive membership theorem | PENDING |  |  |
| Expected-query truncation | PENDING |  |  |
| Raw-density counterexample | PENDING |  |  |
| Representation-padding lemma | PENDING |  |  |
| Explicit-attribute RCSP theorem | PENDING |  |  |
| Posterior-projector lemma | PENDING |  |  |
| Posterior structure theorem | PENDING |  |  |
| Finite classical-advice lemma | PENDING |  |  |
| One-shot quantum-advice proposition | PENDING |  |  |
| Prior-art/novelty assessment | PENDING |  |  |

## Materials to send with this packet

- `overleaf/sections/08_theory.tex`
- `overleaf/appendices/appendix_theory.tex`
- `overleaf/tables/table06_theory_scope.tex`
- `overleaf/tables/tableS4_proof_assumptions.tex`
- `docs/theory/PROOF_AUDIT.md`
- `docs/theory/PRIOR_ART_AUDIT.md`
- `docs/theory/THEORY_V3_CLAIM_BOUNDARY.md`
- `docs/theory/TRAINED_QAOA_TOTAL_QUERY_THEOREM.md`
- `docs/theory/POSTERIOR_STRUCTURE_DILUTION_THEOREM.md`
- `docs/theory/ADVICE_QUERY_TRADEOFF.md`

The manuscript must continue to state that independent human proof review and
independent prior-art judgment are pending until a named reviewer completes
and returns this record.
