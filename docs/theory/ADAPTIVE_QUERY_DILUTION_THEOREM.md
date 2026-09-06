# Adaptive hard-cap feasible-space dilution theorem

## Status and provenance

[V1_THEOREM] The fixed pure-query theorem in
`GLOBAL_QAOA_DILUTION_THEOREM.md` remains unchanged.

[V2_NEW_PROOF] This document formalizes its extension to intermediate
measurements, classical feed-forward, hard-capped stopping, mixed states, and
history-controlled query phases. The primary adaptive verdict is
`VALID_AFTER_REFINEMENT` because the oracle and padding models must be stated
explicitly.

[PRIOR_ART_SOURCE] Zalka's 1999 search-optimality paper explicitly observes that
measurement-controlled classical hardware can be replaced by coherent quantum
control without increasing oracle invocations. The register-level reduction
below supplies the details needed for this particular random-marked-subset
bound; it is not claimed as a historically first deferred-measurement proof.

## Adaptive interaction model

[V2_NEW_PROOF] Let the query-label register $Q$ have basis
$\Omega=\{1,\ldots,N\}$. Let $\mathcal F$ be uniform over the size-$M$
subsets of $\Omega$, and write $\phi=M/N$. The algorithm may have arbitrary
finite-dimensional quantum work, transcript, controller, random-seed,
environment, halt, scratch, and output registers. It begins in an
$\mathcal F$-independent state. Between query opportunities it may apply any
$\mathcal F$-independent quantum instrument and classical computation. Its
only $\mathcal F$-dependent operation is an allowed oracle call. On every
physical branch it makes at most $q$ calls. Finally it outputs a label
$x\in\Omega$, and succeeds when $x\in\mathcal F$.

[V2_NEW_PROOF] The hard cap is pathwise: $Q\le q$ almost surely. It is not a
bound only on $\mathbb E Q$. The expectation in the theorem includes the
uniform choice of $\mathcal F$, all measurement outcomes, and all internal
randomness.

## Theorem A: fixed phase-flip oracle

[V2_NEW_PROOF] Suppose every query is

\[
O_{\mathcal F}=I-2(\Pi_{\mathcal F}\otimes I).
\]

Then every adaptive algorithm in the preceding model satisfies

\[
\boxed{
\mathbb E_{\mathcal F}P_{\mathcal F}
\le \min\{1,(2q+1)^2\phi\}.
}
\]

[V2_NEW_PROOF] This is an average-over-uniform-size-$M$-subsets statement.
It implies the existence of a hard subset and the usual uniform-guarantee
lower bound, but it is not a pointwise upper bound for every $\mathcal F$.

## Complete purification and deferral construction

### Registers

[V2_NEW_PROOF] Use registers $Q$ (active query label), $A$ (algorithm
workspace), $H$ (measurement transcript), $R$ (purified random seed), $E$
(discarded measurement environments), $Z$ (halt flag), $S$ (isolated scratch
query label/workspace), and $X$ (final output label). All are initialized
independently of $\mathcal F$.

### Measurements and discarded data

[V2_NEW_PROOF] An $\mathcal F$-independent instrument with Kraus operators
$K_{h,e}$ is replaced by its Stinespring isometry

\[
|\psi\rangle|0\rangle_H|0\rangle_E
\longmapsto
\sum_{h,e}K_{h,e}|\psi\rangle|h\rangle_H|e\rangle_E.
\]

The outcome is retained in $H$; data discarded by the original procedure is
retained in $E$. Orthogonal $H,E$ records prevent interference between
classical branches. Tracing them out exactly reproduces the original
post-measurement state and outcome probabilities.

### Randomized choices and feed-forward

[V2_NEW_PROOF] A classical random seed is prepared coherently in $R$, with
amplitudes equal to square roots of its probabilities. Every feed-forward map is
implemented as an $H,R,Z$-controlled unitary or Stinespring isometry. Since
the original controller code is independent of $\mathcal F$, these coherent
controls are also independent of $\mathcal F$.

### Early stopping and fixed slots

[V2_NEW_PROOF] Introduce exactly $q$ chronological query slots. Before each
slot, an $\mathcal F$-independent controlled swap selects $Q$ on active
branches and an isolated scratch register $S$ on halted branches. Apply the
ordinary oracle unconditionally to the selected query register, then undo the
swap. Future controls never couple halted scratch data back to $X$. Thus
padding may change an inaccessible environment on a halted branch but cannot
change its output distribution. This avoids assuming that a controlled version
of an unknown phase oracle is free.

[V2_NEW_PROOF] For a membership-bit oracle, one may alternatively place its
response bit in $|+\rangle$ on halted branches because $X|+\rangle=|+\rangle$.

### Output register

[V2_NEW_PROOF] A newly sampled label, the best earlier observed label, or any
label selected from the transcript is reversibly copied into $X$. A final
$\mathcal F$-independent swap places $X$ into the theorem's query register.
The success effect is therefore
$\Pi_{\mathcal F}\otimes I_{\mathrm{rest}}$. Tracing out the purification
registers gives exactly the adaptive algorithm's classical output distribution.

## Hybrid proof after purification

[V2_NEW_PROOF] After the construction, the entire procedure is a pure algorithm
with exactly $q$ phase-flip queries and $\mathcal F$-independent inter-query
unitaries. Let $|\varphi_t\rangle$ be the identity-oracle reference state
immediately before slot (t), including every transcript and environment
register. It is independent of $\mathcal F$, so

\[
\mathbb E_{\mathcal F}
\| (\Pi_{\mathcal F}\otimes I)|\varphi_t\rangle\|^2=\phi.
\]

The phase-flip perturbation has norm

\[
\|(O_{\mathcal F}-I)|\varphi_t\rangle\|
=2\|(\Pi_{\mathcal F}\otimes I)|\varphi_t\rangle\|.
\]

The v1 hybrid recursion and $L_2(\mathcal F)$ Minkowski inequality give

\[
(\mathbb E d_q^2)^{1/2}\le 2q\sqrt{\phi}.
\]

The final reference output has average marked mass $\phi$. Projection
contractivity and a second Minkowski application yield

\[
\sqrt{\mathbb E P_{\mathcal F}}
\le (2q+1)\sqrt{\phi}.
\]

Squaring and applying the probability cap proves Theorem A.

## Corollary B: membership-bit oracle

[V2_NEW_PROOF] For

\[
B_{\mathcal F}|x,b\rangle
=|x,b\oplus 1[x\in\mathcal F]\rangle,
\]

the direct perturbation identity is

\[
B_{\mathcal F}-I
=(\Pi_{\mathcal F}\otimes(X-I))
\]

on the query and answer registers. Since $\lVert X-I\rVert=2$, the same hybrid proof
gives

\[
\mathbb E P_{\mathcal F}\le\min\{1,(2q+1)^2\phi\}.
\]

[V2_NEW_PROOF] One bit query implements a phase flip by preparing the answer
in $|-\rangle$. The reverse direction is not a free one-query equivalence for
an uncontrolled phase oracle: a global phase can be unobservable. A controlled
phase-oracle interface can write the membership bit using phase kickback. The
coarse membership result does not depend on that reverse simulation.

## Theorem C: history-controlled phases

[V2_NEW_PROOF] Suppose query slot $t$ has transcript-controlled phase
$\gamma_t(h)$. Its purified operation is

\[
U_{\mathcal F,t}
=\sum_h|h\rangle\!\langle h|\otimes
\left[I+(e^{-i\gamma_t(h)}-1)\Pi_{\mathcal F}\right].
\]

Define

\[
c_t=\sup_h|e^{-i\gamma_t(h)}-1|\le2.
\]

Then

\[
\|(U_{\mathcal F,t}-I)|\varphi_t\rangle\|
\le c_t\|(\Pi_{\mathcal F}\otimes I)|\varphi_t\rangle\|,
\]

because the control-block multiplier has operator norm $c_t$. Consequently,

\[
\boxed{
\mathbb E P_{\mathcal F}
\le
\min\left\{1,\left(1+\sum_{t=1}^{q}c_t\right)^2\phi\right\}.
}
\]

[V2_NEW_PROOF] The coarse bound follows from $c_t\le2$. This theorem assumes
that the controlled direct-sum query is the counted oracle interface. It does
not assert that arbitrary controlled access to an otherwise unknown unitary is
free.

## Mixed-state and CPTP formulation

[V2_NEW_PROOF] Between queries, arbitrary $\mathcal F$-independent CPTP maps
are permitted. Dilate every map into an isometry with a fresh environment,
retain all environments, and apply the Euclidean pure-state proof above. No
trace-distance/Euclidean-distance conversion is used. The final success
probability is unchanged after tracing the environments. Status:
`VALID_STANDARD_REDUCTION_FORMALIZED`.

## Expected query count is different

[COUNTEREXAMPLE] The substitution

\[
\mathbb E P\stackrel{?}{\le}(2\mathbb E Q+1)^2\phi
\]

is invalid. With $\phi=10^{-6}$, choose a long branch with probability $0.01$,
run $785$ Grover iterations on it, and otherwise make zero queries and guess
uniformly. The mean query count is $7.85$, the actual success is approximately
$0.010001$, while the proposed mean-substitution expression is approximately
$2.7889\times10^{-4}$.

[V2_NEW_PROOF] A rigorous truncation statement does hold. If
$\mathbb E_{\mathcal F,\mathrm{internal}}Q\le\bar q$, then for every integer
$T\ge0$, truncate before query (T+1). The original success obeys

\[
\boxed{
\mathbb E P
\le
\min\left\{1,
\frac{\bar q}{T+1}
+\min\{1,(2T+1)^2\phi\}
\right\}.
}
\]

The first term is integer-valued Markov:
$\Pr(Q>T)=\Pr(Q\ge T+1)\le\bar q/(T+1)$. The second is the hard-cap theorem for
the truncated algorithm. Minimizing over deterministic $T$ is valid. For
fixed target success this bound still implies
$\bar q=\Omega(\phi^{-1/2})$, but it does not provide the false quadratic
formula in $\bar q$.

[V2_NEW_PROOF] If the query count \(Q\) is sampled independently before the
algorithm begins, and hence independently of both \(\mathcal F\) and the
oracle-derived transcript, conditioning on \(Q=k\) gives the valid mixture
bound

\[
\mathbb E P
\le
\mathbb E\!\left[\min\{1,(2Q+1)^2\phi\}\right]
\le
\min\{1,\phi\,\mathbb E(2Q+1)^2\}.
\]

This expected-square statement is not proved for transcript-dependent stopping;
the truncation bound above is the general result established here.

## Verdict matrix

| Candidate | Status |
|---|---|
| `HARD_CAP_FIXED_PHASE_ADAPTIVE` | `VALID_STANDARD_REDUCTION_FORMALIZED` |
| `HARD_CAP_MEMBERSHIP_BIT_ORACLE` | `VALID_AFTER_REFINEMENT` |
| `HARD_CAP_BRANCH_DEPENDENT_PHASE` | `VALID_AFTER_REFINEMENT` |
| `EXPECTED_QUERY_COUNT_ONLY` | `VALID_AFTER_REFINEMENT` |
| `VARIABLE_STOPPING_WITH_HARD_CAP` | `VALID_STANDARD_REDUCTION_FORMALIZED` |
| `MIXED_STATE_CPTP_MODEL` | `VALID_STANDARD_REDUCTION_FORMALIZED` |

## Nonclaims

[OPEN_GAP] No equal-form rich value-oracle theorem is proved.

[OPEN_GAP] No direct standard explicit-input RCSP lower bound follows.

[INFERENCE] The theorem constrains total counted membership queries, not the
depth of a final circuit obtained after training.

[COUNTEREXAMPLE] Free explicit access to $\mathcal F$, an $\mathcal F$-dependent
initial state, or an $\mathcal F$-dependent mixer permits zero-query success and
is outside this model.
