# Theory Validation v3 report

## A. THEORY V3 STATUS

```text
COMPLETE
```

The required theory, executable constructions, adversarial tests, numerical
validation, primary-source audit, cost ledger, and eight figures are present.
The only refinement to the requested package is scientifically necessary: an
unqualified bounded-error `Theta(sqrt(K/M))` statement is false when free
guessing already meets the target, including `M=K`.

## B. WORKTREE SAFETY

| Worktree | Branch / HEAD | State |
|---|---|---|
| `<LOCAL_WORKSPACE>/Q-RouteDilution` | `main` / `b9922aadbc3c098db74a8e4ee992572a698d1f53` | Protected dirty Phase-3B state; not edited |
| `<LOCAL_WORKSPACE>/Q-RouteDilution-theory-v2` | `theory/adaptive-query-rcsp-bridge-v1` / `68d0799be9d6e50f4a06e704d4c5a0265bcb5045` | Clean; not edited |
| `<LOCAL_WORKSPACE>/Q-RouteDilution-theory-v3` | `theory/structure-advice-rcsp-v1` / base `68d0799be9d6e50f4a06e704d4c5a0265bcb5045` | All v3 edits isolated here |

The full original status is anchored by the immutable v2 snapshot and by the
v3 content fingerprint in `worktree_safety_baseline.json`. The Theory-v1/v2
artifact tree hash is
`23a1bdf525dd322456d76d87f510fefa73bdb9f838ff9edc2b86bbc69574fc2c`.
Final recomputation matched the original worktree's status hash
`e62f29e5a10ba18891082079e4f2555eb1829356472cbd5e956bcc8db36aec53`
and tracked-diff hash
`8a7dadaa00ac9121c1b9e41a7d757403830a255257ca92fb4fb0c529d37f48e6`.
No merge or push was performed.

## C. RAW EDGE-BIT RESULT

For the explicit chain

\[
s=v_0\to v_1\to\cdots\to v_m=t,
\]

exactly one of `2^m` edge selections is a valid feasible route, hence
`phi_state=2^{-m}`. The route and optimum are returned by linear traversal in
`O(m)` time with an `m`-edge output. This contradicts every universal bound
`T*(I)>=c phi_state(I)^{-1/2}` for fixed `c>0`.

The edge-subdivision lemma replaces one edge by `r` private serial segments,
splits all rational additive coefficients by `r`, preserves routes, totals,
feasibility, ordering, and optimum, and gives

\[
\phi_{\rm state}(I^{(r)})=2^{-(r-1)}\phi_{\rm state}(I).
\]

Coefficient bit length grows by at most `O(log r)` while explicit topology and
route-output size grow by `Theta(r)`. It does not make the logical problem
exponentially harder.

## D. EXPLICIT RCSP QUERY RESULT

The graph has known paths `s->u_i->t`. The fixed first resource is one; the
second is one for `z_i=1` and two for `z_i=0`; budget is two. The explicit
length-`K` attribute array is accessed only by the counted query

\[
O_z|i,b\rangle=|i,b\oplus z_i\rangle.
\]

Thus branch `i` is feasible iff `z_i=1`, and finding a feasible route is
multiple-marked search. For average target success `tau`,

\[
q\ge\frac12\left(\sqrt{\frac{\tau K}{M}}-1\right).
\]

Uniform worst-case target success implies the same average lower bound.
Amplitude amplification gives `O(sqrt(K/M))` queries. Therefore, for fixed
`tau` with `M/K<tau`,

\[
Q_\tau^{\rm RCSP}(K,M)=\Theta_\tau(\sqrt{K/M}).
\]

For exact success this is `Theta(sqrt(K/M))` when `1<=M<K`, while `M=K`
costs zero queries. If the array is supplied free, the query lower bound is
inapplicable. The input has `Theta(K)` cells; no exponential lower bound in
`log K` is claimed. The relevant fraction is `phi_path=M/K`, not
`phi_state=M/2^{2K}`.

## E. POSTERIOR STRUCTURE THEOREM

For `F` uniform over size-`M` subsets and classical pre-search structure `S`,

\[
\overline\Pi_s=\mathbb E[\Pi_F\mid S=s],
\quad
\lambda_s=\|\overline\Pi_s\|_\infty
=\max_x\Pr[x\in F\mid S=s],
\quad
\phi\le\lambda_s\le1.
\]

With history-controlled phase coefficients
`c_t(s)=sup_h |exp(-i gamma_t(s,h))-1|` and
`C(s)=1+sum_t c_t(s)`, the complete conditional theorem is

\[
\mathbb E[P\mid S=s]\le\min\{1,C(s)^2\lambda_s\}.
\]

Therefore

\[
\mathbb E P\le
\mathbb E_S[\min\{1,C(S)^2\lambda_S\}]
\le\min\{1,\mathbb E_S[C(S)^2\lambda_S]\}.
\]

With `Lambda=E lambda_S` and `c_t<=2`,

\[
\boxed{\mathbb E P\le\min\{1,(2q+1)^2\Lambda(S)\}.}
\]

The identity-oracle reference is advice-dependent but conditionally independent
of remaining `F` uncertainty; this is the key proof invariant.

## F. FINITE ADVICE TRADEOFF

For `|supp S|<=2^b`, choosing a maximizing label for each supported advice
value gives

\[
\Lambda\le\min\{1,2^b\phi\}.
\]

Duplicate maximizing labels only repeat upper-bound terms. Hence

\[
\boxed{\mathbb E P\le\min\{1,(2q+1)^2 2^b\phi\}.}
\]

For `tau>0` and `phi>0`, the necessary integer condition is

\[
b\ge\max\left\{0,
\left\lceil\log_2\frac{\tau}{(2q+1)^2\phi}\right\rceil\right\}.
\]

`tau=0` and nonpositive logarithms require zero bits; `M=0` is outside the
member-output/logarithmic model. Global phase coefficients factor; advice-
dependent coefficients remain inside the conditional expectation.

## G. EFFECTIVE STRUCTURE

\[
b_{\rm eff}=\log_2(\Lambda/\phi),
\qquad
K_{\rm eff}=M/\Lambda,
\]

with

\[
0\le b_{\rm eff}\le\log_2(1/\phi),
\quad b_{\rm eff}\le b,
\quad M\le K_{\rm eff}\le N,
\quad N/K_{\rm eff}=2^{b_{\rm eff}}.
\]

Target `tau` necessarily requires

\[
b_{\rm eff}+2\log_2(2q+1)\ge\log_2(\tau/\phi),
\qquad
K_{\rm eff}\le(2q+1)^2M/\tau.
\]

For `phi_n=2^{-alpha n}` and polynomial `q(n)`, constant success needs
`b_eff>=alpha n-O(log n)` under this random-subset prior. These are necessary,
not sufficient, conditions.

## H. QUERY-GENERATED STRUCTURE

Membership-query preprocessing and later search are one adaptive interaction:

\[
q_{\rm total}=q_{\rm pre}+q_{\rm post}.
\]

Writing the transcript into classical advice does not erase its generation
queries. A structured operation simulated by `r` membership queries and used
`L` times is charged `rL`; absent a simulation it is a stronger oracle.

## I. COST RELOCATION

- **Penalty-X full-space QAOA:** burden remains in rich penalty construction,
  energy queries, training/sampling, and invalid-route validation.
- **CVaR Penalty-X:** burden moves to rich energy-distribution sampling and tail
  estimation; it is `RICH_COST_INFORMATION`, not a membership violation.
- **Warm-start QAOA:** burden moves to classical solve/relaxation or learned
  advice and warm-state preparation.
- **Feasible-subspace preparation:** burden moves to enumeration/loaders,
  state gates, ancillas, postselection, and retries.
- **Path-exchange mixer:** burden moves to candidate paths, neighbor/mixer graph
  construction, connectivity, and compilation.
- **XY/constraint-preserving mixer:** burden moves to algebraic compilation,
  connectivity routing, Trotterization, and residual-constraint checks.
- **Grover feasible-state mixer:** burden moves to feasible-state loading,
  reflection synthesis, or the charged membership simulation.
- **Explicit feasible-basis QAOA:** burden moves to enumeration, objective
  evaluation, storage/indexing, mixer graph, and loading; supplied objective
  values already permit classical `argmin`.
- **Classical corridor restriction:** burden moves to corridor construction,
  miss risk, effective-support quality, validation, and dynamic patch/rebuild.
- **Oracle-RCSP branch search:** burden is counted attribute access and
  amplitude amplification; physical QRAM/deployment costs remain unknown.

No arbitrary scalar combines these orthogonal resources. Unmeasured costs are
recorded `UNKNOWN`.

## J. PRIOR ART

Multiple-marked Grover bounds, prior-distribution search, min-entropy guessing
and leakage principles, function-inversion preprocessing tradeoffs, graph query
models, and succinct/explicit representation gaps all preexist. Eighteen
searches inspected fourteen primary-source rows. No exact match for the full
posterior-projector plus `(2q+1)^2 2^b phi` theorem was located, but the search
is not exhaustive.

```text
NOVELTY_UNRESOLVED
POTENTIALLY_DISTINCT_POSTERIOR_PROJECTOR_FORM
```

## K. NUMERICAL VALIDATION

- posterior parameter cells `(N,M,q)`: `44`;
- validation rows: `1,056`;
- advice channel families: constant, partition, noisy bucket, one-marked-label,
  random deterministic maps, random stochastic maps;
- declared alphabet sizes: `1,2,4,8`;
- advice-conditioned subset evaluations: `80,860`;
- unique-chain rows: `40`;
- rational padding rows: `7`;
- parallel-branch rows: `30`;
- maximum success residual: `3.3306690738754696e-16`;
- maximum advice-concentration residual: `2.220446049250313e-16`;
- violations: `0`.

All nonzero residuals are floating-point roundoff. Numerical tests are not the
lower-bound proof.

## L. FINAL VERDICTS

```text
RAW_PHI_STATE_LOWER_BOUND_IMPOSSIBLE
EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND_VALID
POSTERIOR_STRUCTURE_BOUND_VALID
FINITE_ADVICE_TRADEOFF_VALID
QUANTUM_ADVICE_BOUND_VALID
STRUCTURE_COST_CONTRACT_COMPLETE
```

## M. ALLOWED PAPER POSITIONING

Primary:

```text
THEORY_NOVELTY_UNRESOLVED
```

Secondary:

```text
EXPLICIT_RCSP_QUERY_SUBCLASS_PLUS_EMPIRICAL_CASE_STUDY
POTENTIALLY_DISTINCT_POSTERIOR_PROJECTOR_FORM
```

## N. OPEN GAPS

- rich cost-oracle lower bounds;
- interactive/reusable quantum advice beyond the proved single-state model;
- natural explicit-RCSP structural lower bounds;
- computational cost of producing useful `S`;
- implementation and amortization of state/mixer structure;
- external independent proof and prior-art review.

## O. TESTS

The final full suite passed: `152 passed in 128.35s`. Existing tests were not
weakened. Safety fingerprints are recorded in `summary.json` and
`worktree_safety_baseline.json`. Theory-v1/v2 artifacts remain hash-identical
to the audited predecessor tree.

## P. GIT

All changes are confined to branch `theory/structure-advice-rcsp-v1` in the v3
worktree and are committed with message:

```text
Prove structure-query tradeoffs and explicit RCSP access bounds
```

The commit SHA is reported in the handoff because a commit cannot contain its
own final SHA. No push and no merge were performed.
