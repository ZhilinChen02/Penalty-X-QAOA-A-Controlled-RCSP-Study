# Second-Pass Theory Review

Audit label: `SECOND_PASS_MACHINE_AUDIT`

This is a second machine reasoning pass over Theory-v1--v3. It is not an
independent human proof review. The review used two deliberately separated
passes: reconstruction from each formal statement and assumptions, followed by
an adversarial comparison with the historical proof documents. Historical
theory artifacts were treated as immutable.

## Result

Verdict: `SECOND_PASS_PASS_WITH_CLARIFICATIONS`.

No theorem was found invalid and no historical correction is proposed. T1 and
T5 pass without an added qualification; T2--T4 and T6--T11 pass with
publication-facing scope clarifications. These clarifications prevent model or
quantifier expansion; they do not alter the proved formulas.

| Result | Status | Publication-critical clarification |
|---|---|---|
| T1 fixed-query phase-sensitive bound | `PASS` | Average over a uniform fixed-cardinality feasible-set prior, not pointwise in every set. |
| T2 adaptive hard-cap bound | `PASS_WITH_CLARIFICATION` | A history-controlled oracle is one counted slot only under the stated direct-sum membership interface. |
| T3 trained total-query specialization | `PASS_WITH_CLARIFICATION` | Constrains end-to-end membership access, not final trained depth or classical training time. |
| T4 expected-query truncation | `PASS_WITH_CLARIFICATION` | Use the integer truncation inequality; never substitute \(q=\mathbb E Q\). |
| T5 raw-edge-bit counterexample | `PASS` | Refutes a raw-density-only explicit-complexity bound, not representation-specific QAOA behavior. |
| T6 representation padding | `PASS_WITH_CLARIFICATION` | Coefficient bit length grows \(O(\log r)\), while explicit topology/input length grows \(\Theta(r)\). |
| T7 explicit-attribute RCSP | `PASS_WITH_CLARIFICATION` | A length-\(K\) random-access input-query result; the target-success regime and \(M=K\) endpoint must be stated. |
| T8 posterior structure | `PASS_WITH_CLARIFICATION` | Condition before applying the hybrid; do not interchange expectation and operator norm or move caps without justification. |
| T9 finite classical advice | `PASS_WITH_CLARIFICATION` | \(b\) bounds advice-support cardinality, not Shannon or mutual information. |
| T10 finite quantum advice | `PASS_WITH_CLARIFICATION` | One pre-search advice state of total accessible dimension \(d\); no refreshed or interactive provider. |
| T11 effective quantities | `PASS_WITH_CLARIFICATION` | Necessary posterior compression only; neither sufficiency nor implementation cost. |

The row-complete derivations and comparisons are frozen in
`results/synthesis_v1/second_pass_proof_review.csv`.

## Pass A: reconstruction

### T1: fixed-query phase-sensitive dilution

For a uniform size-\(M\) subset \(\mathcal F\subset[N]\), let
\(\phi=M/N\). Compare the real circuit with an identity-oracle reference
circuit. The reference state at query slot \(t\) is independent of
\(\mathcal F\), so

\[
\mathbb E_{\mathcal F}
\langle\psi_t|\Pi_{\mathcal F}|\psi_t\rangle=\phi.
\]

A phase query changes a state by at most
\(c_t\|\Pi_{\mathcal F}\psi_t\|\), where
\(c_t=|e^{-i\gamma_t}-1|\). Applying the \(L^2\) triangle inequality to the
hybrid recursion and once more to the final marked projection gives

\[
\left(\mathbb E P_{\mathcal F}\right)^{1/2}
\leq \left(1+\sum_t c_t\right)\sqrt\phi.
\]

Squaring and applying the probability cap proves T1. The argument uses only an
average reference-overlap identity; it makes no pointwise small-overlap claim.

### T2: adaptive hard cap

Purify mixed states, internal randomness, measurement, and feed-forward into
unitary evolution with orthogonal history registers. Pad a branch that stops
early by sending all remaining query slots to an isolated scratch target; the
branch never recombines with an active branch. A controlled membership query
is a direct sum over histories, and its deviation from identity has norm at
most two on the marked subspace. The T1 hybrid therefore gives

\[
\mathbb E P_{\rm success}\leq
\min\{1,(2q+1)^2\phi\}.
\]

The hard cap is pathwise. Expected query count is not a hard cap.

### T3: trained total-query specialization

Regard training, sample generation, feedback, optimizer state, stored
transcripts, and the final circuit as a single adaptive interaction. Classical
storage does not erase the membership calls that generated it. T2 applies to
the total pathwise count

\[
q_{\rm total}=q_{\rm training}+q_{\rm sampling}
+q_{\rm feedback}+q_{\rm final}.
\]

Free explicit attributes or cost values would instead define a richer
information-access model.

### T4: expected-query truncation

Let \(Q\) be the nonnegative integer number of membership queries and
\(\bar q=\mathbb E Q\), with both expectations taken over the prior and all
internal randomness. For any deterministic integer \(T\geq0\), turn executions
with \(Q>T\) into failure. The retained protocol has hard cap \(T\), while

\[
\Pr(Q>T)=\Pr(Q\geq T+1)\leq\frac{\bar q}{T+1}.
\]

Thus

\[
\mathbb E P\leq
\min\left\{1,
\frac{\bar q}{T+1}+
\min\{1,(2T+1)^2\phi\}\right\}.
\]

This is the valid replacement for the false convexity-violating substitution
\(q=\mathbb E Q\).

### T5--T7: explicit RCSP boundaries

An explicit \(m\)-edge directed chain has exactly one route, hence
\(\phi_{\rm state}=2^{-m}\), but reading and outputting the route costs
\(\Theta(m)\). This contradicts any universal positive-constant lower bound
proportional to \(\phi_{\rm state}^{-1/2}\).

Replacing one edge by a private serial path of \(r\) edges gives a route
bijection under path contraction/expansion. Splitting each rational additive
attribute evenly preserves route totals, feasibility, ordering, and optima.
The feasible-route numerator is fixed and the edge count grows by \(r-1\), so

\[
\phi_{\rm state}(I^{(r)})=2^{-(r-1)}\phi_{\rm state}(I).
\]

For the separate parallel-branch result, the topology and fixed attributes are
known and a length-\(K\) status array is explicit but charged through quantum
random access. Branch feasibility equals status-bit markedness. Multiple-marked
search supplies the lower bound, and amplitude amplification supplies the
upper bound. For fixed target \(\tau\) in the nontrivial regime, this gives
\(\Theta_\tau(\sqrt{K/M})\). It is not a RAM-time result and is not exponential
in a compact \(\log K\)-bit description. When \(M=K\), zero queries suffice;
when \(M/K\geq\tau\), random zero-query output already reaches target \(\tau\).

### T8--T9: posterior structure and finite advice

Condition on a supported advice value \(S=s\). The posterior projector

\[
\overline\Pi_s=\mathbb E[\Pi_{\mathcal F}\mid S=s]
\]

is diagonal in the label basis, and therefore

\[
\lambda_s=\|\overline\Pi_s\|_\infty
=\max_x\Pr(x\in\mathcal F\mid S=s).
\]

An identity-oracle reference may depend on \(s\), but is independent of the
residual uncertainty in \(\mathcal F\). Its conditional expected marked weight
is at most \(\lambda_s\), so the conditional hybrid proves

\[
\mathbb E[P\mid S=s]\leq \min\{1,C(s)^2\lambda_s\}.
\]

Average this expression before taking the coarser hard-cap consequence. With
\(\Lambda=\mathbb E_S\lambda_S\),

\[
\mathbb E P\leq \min\{1,(2q+1)^2\Lambda\}.
\]

If the advice support has at most \(2^b\) values, select one maximizing label
\(x_s\) for each supported output. Then

\[
\Lambda
=\sum_s\Pr(S=s,x_s\in\mathcal F)
\leq\sum_s\Pr(x_s\in\mathcal F)
\leq2^b\phi.
\]

Duplicate maximizing labels do not invalidate the inequality; they only count
the same marginal more than once and loosen it.

### T10: one-shot finite-dimensional quantum advice

The counted resource is the dimension of the total accessible pre-search
advice register, not the dimension of an inaccessible purifying reference. For
one \(\mathcal F\)-dependent density operator \(\rho_{\mathcal F}\) on a
\(d\)-dimensional accessible register, \(\rho_{\mathcal F}\preceq I_d\). An
\(\mathcal F\)-independent completely positive reference map therefore has
average marked weight bounded by \(d\phi\), and a canonical purification lets
the hybrid proceed without a \(d^2\) loss. This covers mixed advice and
entanglement with an inaccessible purifier. It does not cover fresh copies,
refreshing, or an interactive \(\mathcal F\)-dependent advice provider.

### T11: effective quantities

For \(0<\phi=M/N\), define

\[
b_{\rm eff}=\log_2(\Lambda/\phi),\qquad
K_{\rm eff}=M/\Lambda.
\]

Then \(0\leq b_{\rm eff}\leq\log_2(1/\phi)\),
\(M\leq K_{\rm eff}\leq N\), and
\(N/K_{\rm eff}=2^{b_{\rm eff}}\). Target average success \(\tau>0\) requires

\[
b_{\rm eff}+2\log_2(2q+1)\geq\log_2(\tau/\phi).
\]

The implication is necessary only.

## Pass B: adversarial comparison

The comparison found no hidden switch between average and pointwise claims in
the formal statements. Probability caps are correctly retained. The posterior
proof conditions before taking a norm, and the finite-advice proof uses support
cardinality rather than information entropy. The explicit RCSP proof is a
cell-query reduction, not a compact-input or explicit-RAM lower bound. The
training theorem counts total access, not final depth. The padding proof changes
representation density without asserting increased logical difficulty. The
effective quantities express necessity, not sufficiency.

The main residual risk is communicative scope drift during manuscript writing.
Every central theorem still requires independent human proof review before
submission, particularly T2, T8, T9, and T10. Because no mathematical error was
identified, `PROPOSED_THEORY_CORRECTIONS.md` is intentionally absent.
