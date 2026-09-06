# Posterior structure dilution theorem

## Model

Let `Omega={1,...,N}` and let `F` be uniform over all size-`M` subsets, with
`phi=M/N`. Before membership-query search, an arbitrary deterministic or
randomized classical channel depending on `F` outputs side information `S`.
Conditioned on `S=s`, the algorithm may choose an `s`-dependent initial state,
ancillas, unitaries, instruments, measurements, feed-forward, stopping rule,
and output decoder. Every branch makes at most `q` membership queries. After
`S` is delivered, no other `F`-dependent information is available except
through those counted queries.

Write

\[
\Pi_F=\sum_{x\in F}|x\rangle\!\langle x|,
\qquad
\overline\Pi_s=\mathbb E[\Pi_F\mid S=s],
\qquad
\lambda_s=\|\overline\Pi_s\|_\infty.
\]

Only positive-probability advice values are considered. Since every posterior
set still has exactly `M` elements,

\[
\operatorname{Tr}\overline\Pi_s=M.
\]

The operator is diagonal and its `x`-th diagonal entry is
`Pr[x in F|S=s]`. Therefore

\[
\boxed{\lambda_s=\max_x\Pr[x\in F\mid S=s].}
\]

The maximum of `N` nonnegative diagonal entries with sum `M` is at least their
average, and no probability exceeds one, so

\[
\phi\le\lambda_s\le1.
\]

Define the average posterior concentration

\[
\Lambda(S)=\mathbb E_S[\lambda_S].
\]

## Phase-sensitive conditional theorem

At query slot `t`, allow the purified history- and advice-controlled phase
`gamma_t(s,h)` and set

\[
c_t(s)=\sup_h|e^{-i\gamma_t(s,h)}-1|,
\qquad
C(s)=1+\sum_{t=1}^q c_t(s).
\]

**Theorem.** Under the model above,

\[
\boxed{
\mathbb E[P_{\rm success}\mid S=s]
\le \min\{1,C(s)^2\lambda_s\}.
}
\]

Consequently,

\[
\boxed{
\mathbb E P_{\rm success}
\le
\mathbb E_S\!\left[\min\{1,C(S)^2\lambda_S\}\right].
}
\]

The always-valid coarsening

\[
\mathbb E P_{\rm success}
\le\min\{1,\mathbb E_S[C(S)^2\lambda_S]\}
\]

uses separately that every probability is at most one and that
`min(1,a)<=a`. It does not assert equality and does not move a nonlinear cap
through expectation in the wrong direction.

If the coefficients are global—`c_t(s)=c_t` for every supported advice
value—then `C` factors legitimately and the requested phase-sensitive form is

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\left\{1,
\left(1+\sum_t c_t\right)^2\Lambda(S)
\right\}.
}
\]

## Proof

Fix `S=s`. Purify all internal randomness, measurements, discarded data, and
feed-forward exactly as in the audited Theory-v2 adaptive theorem. Pad early
stopping to `q` slots using an isolated scratch query register. All
identity-oracle reference states may depend on `s`, but the reference circuit
has no access to the remaining random choice of `F` under the posterior.

For every normalized reference state `|psi_s>` (including arbitrary work and
ancilla registers),

\[
\begin{aligned}
\mathbb E[\langle\psi_s|(\Pi_F\otimes I)|\psi_s\rangle\mid S=s]
&=\langle\psi_s|(\overline\Pi_s\otimes I)|\psi_s\rangle\\
&\le\lambda_s.
\end{aligned}
\]

Let `|varphi_{t,s}>` be the identity-oracle reference immediately before slot
`t`. The controlled direct-sum query perturbation obeys

\[
\|(U_{F,t}-I)|\varphi_{t,s}\rangle\|
\le c_t(s)\|(\Pi_F\otimes I)|\varphi_{t,s}\rangle\|.
\]

Conditional `L_2(F|s)` Minkowski and the preceding overlap bound yield

\[
\left(\mathbb E[d_q(F,s)^2\mid s]\right)^{1/2}
\le\left(\sum_t c_t(s)\right)\sqrt{\lambda_s}.
\]

The final identity-reference marked amplitude has conditional `L_2` norm at
most `sqrt(lambda_s)`. Projection contractivity and a second Minkowski
application give

\[
\sqrt{\mathbb E[P_{\rm success}\mid s]}
\le C(s)\sqrt{\lambda_s}.
\]

Squaring and applying the probability cap proves the conditional theorem.
Average the already-conditioned statement with the law of total expectation
to obtain the second display.

## Coarse hard-cap corollary

Since every phase coefficient is at most two,

\[
\mathbb E[P\mid s]\le\min\{1,(2q+1)^2\lambda_s\}.
\]

The function `x -> min(1,(2q+1)^2 x)` is concave; equivalently, bound the
expectation both by one and by `(2q+1)^2 E lambda_S`. Thus

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\{1,(2q+1)^2\Lambda(S)\}.
}
\]

When `S` is constant, posterior symmetry gives `lambda_s=Lambda=phi`, exactly
recovering Theory-v2.

## Query-generated advice

If a preprocessing stage uses `q_pre` membership queries to produce `S`, the
premise that `S` arrives before the counted interaction is false. Purify the
complete two-stage controller and charge

\[
q_{\rm total}=q_{\rm pre}+q_{\rm post}.
\]

The Theory-v2 trained/adaptive total-query theorem applies to the whole
interaction. Storing a transcript as classical advice between stages does not
erase the queries that created it. Preprocessing that reads richer explicit
instance data instead changes the information-access model.

## Structured-operation simulation

If an `F`-dependent operation `W_F` is simulated with at most `r` membership
queries per call and invoked `L` times, charge `rL` calls in the total-query
theorem. Without such a simulation, feasible-state preparation,
feasibility-preserving mixing, or a feasible-neighbor operation is a strictly
stronger structure oracle—not a free mixer.

## Finite-dimensional quantum advice extension

The same proof admits one `F`-dependent quantum advice state `rho_F` on a
`d`-dimensional register, provided all subsequent `F` dependence still enters
through counted membership queries. For any `F`-independent trace-preserving
channel `A`, positivity gives `rho_F <= I_d`, hence

\[
\begin{aligned}
\mathbb E_F\operatorname{Tr}[(\Pi_F\otimes I)A(\rho_F)]
&\le
\mathbb E_F\operatorname{Tr}[(\Pi_F\otimes I)A(I_d)]\\
&=\phi\operatorname{Tr}A(I_d)=d\phi.
\end{aligned}
\]

Use a canonical purification of each `rho_F`; the squared projected norm is
the same reduced-state trace, so the pure-state hybrid proof applies without
replacing `d` by `d^2`. Therefore

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\left\{1,\left(1+\sum_t c_t\right)^2d\phi\right\}
}
\]

and in particular `min{1,(2q+1)^2 d phi}`. Multiple supplied advice registers
are charged by their **joint** dimension. Advice supplied afresh during the
interaction, an `F`-dependent advice-generation oracle, entanglement with an
accessible provider, or richer instance operations are outside this theorem.

Verdict:

```text
POSTERIOR_STRUCTURE_BOUND_VALID
QUANTUM_ADVICE_BOUND_VALID
```
