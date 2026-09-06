# Global full-space feasible-space dilution theorem

## Audited theorem

Let (N\ge 1), let (0\le M\le N), and let Ω be an (N)-element query
basis. Draw ℱ uniformly from the size-(M) subsets of Ω and define

\[
\Pi_{\mathcal F}=\sum_{x\in\mathcal F}|x\rangle\langle x|,
\qquad \phi=M/N.
\]

Let the ancilla Hilbert space have arbitrary dimension. Consider any normalized
pure input state, unitaries (V_0,\ldots,V_q), and phases
γ₁,…,γ_q such that all are fixed independently of the particular ℱ. The
only ℱ-dependent operation is

\[
Q_{\mathcal F}(\gamma_t)=I+
  (e^{-i\gamma_t}-1)(\Pi_{\mathcal F}\otimes I_A).
\]

For

\[
|\psi_{\mathcal F}\rangle=
V_qQ_{\mathcal F}(\gamma_q)V_{q-1}\cdots
V_1Q_{\mathcal F}(\gamma_1)V_0|\psi_{\rm in}\rangle
\]

and

\[
P_{\mathcal F}=\langle\psi_{\mathcal F}|
(\Pi_{\mathcal F}\otimes I_A)|\psi_{\mathcal F}\rangle,
\]

the audited bound is

\[
\boxed{
\mathbb E_{\mathcal F}P_{\mathcal F}
\le
\min\!\left\{1,
\left(1+\sum_{t=1}^q|e^{-i\gamma_t}-1|\right)^2\frac MN
\right\}.}
\]

No restriction is placed on the (V_t) beyond unitarity and independence from
the particular marked set. Ancillas may be entangled with the query register.
The theorem is an average over uniformly random size-(M) sets, not a pointwise
upper bound for each set.

## Proof

Replace all queries by the identity. Let φ_t be the reference state immediately
before query (t), with (t=1,\ldots,q). It is independent of ℱ. Because the
query register is finite, write

\[
|\varphi_t\rangle=\sum_{x=1}^N|x\rangle|\alpha_{t,x}\rangle,
\qquad \sum_x\|\alpha_{t,x}\|^2=1.
\]

Then

\[
a_t(\mathcal F)^2
=\|(\Pi_{\mathcal F}\otimes I_A)|\varphi_t\rangle\|^2
=\sum_{x\in\mathcal F}\|\alpha_{t,x}\|^2.
\]

Every (x) belongs to a uniform size-(M) subset with probability (M/N), so

\[
\mathbb E_{\mathcal F}a_t(\mathcal F)^2=M/N=\phi.
\]

This establishes the identity without restricting the ancilla dimension.
Moreover,

\[
(Q_{\mathcal F}(\gamma_t)-I)|\varphi_t\rangle
=(e^{-i\gamma_t}-1)(\Pi_{\mathcal F}\otimes I_A)|\varphi_t\rangle,
\]

whose norm is (c_ta_t(\mathcal F)), where
(c_t=|e^{-i\gamma_t}-1|).

For precise indexing, let (d_t) be the true/reference distance after the
first (t) queries and the following (V_t); equivalently it is the distance
immediately before query (t+1). Thus (d_0=0) after (V_0). Unitarity and the
triangle inequality give, for (t=0,\ldots,q-1),

\[
d_{t+1}(\mathcal F)
\le d_t(\mathcal F)+c_{t+1}a_{t+1}(\mathcal F).
\]

Iteration gives (d_q\le\sum_t c_ta_t). Minkowski's inequality in
(L_2(\mathcal F)) then gives

\[
\|d_q\|_{L_2}
\le\sum_t c_t\|a_t\|_{L_2}
=\sqrt\phi\sum_t c_t.
\]

Let ψ∅ be the final identity-query reference state and let
(R_{\mathcal F}=\|(\Pi_{\mathcal F}\otimes I_A)|\psi_\varnothing\rangle\|^2).
The same inclusion identity gives ᵓR=φ. Contractivity of an orthogonal
projection and the triangle inequality give pointwise

\[
\sqrt{P_{\mathcal F}}
\le\sqrt{R_{\mathcal F}}+d_q(\mathcal F).
\]

A second application of Minkowski yields

\[
\sqrt{\mathbb E P_{\mathcal F}}
\le\sqrt\phi+\sqrt\phi\sum_t c_t.
\]

Both sides are nonnegative, so squaring is valid. Combining with the trivial
probability bound (\mathbb E P\le1) proves the theorem.

## Corollaries

Since (c_t=2|\sin(\gamma_t/2)|\le2),

\[
\mathbb E P_{\mathcal F}\le\min\{1,(2q+1)^2\phi\}
\le(2q+1)^2\phi.
\]

Consequently at least one size-(M) set satisfies
(P_{\mathcal F}\le(2q+1)^2\phi). This is existential, not pointwise.

If either every size-(M) set succeeds with probability at least τ, or the
uniform average succeeds with probability at least τ, then

\[
q\ge \max\!\left\{0,\frac12
\left(\sqrt{\tau/\phi}-1\right)\right\}.
\]

For integer query counts one may take the ceiling. For fixed τ>0 and
φ→0 this is (q=\Omega(\phi^{-1/2})).

If φ_n≤2^{-αn}, α>0, and (q(n)\le Cn^k) for all sufficiently
large (n), then

\[
\mathbb E P_n\le(2Cn^k+1)^2 2^{-\alpha n}.
\]

For every fixed (0<\beta<\alpha), the right side is at most
(2^{-\beta n}) for sufficiently large (n). Thus it is
(2^{-\Omega(n)}); the threshold depends on α, (C), and (k).

## Fixed-schedule global QAOA

For (H_{\mathcal F}=I-\Pi_{\mathcal F}),

\[
e^{-i\gamma H_{\mathcal F}}
=e^{-i\gamma}[I+(e^{i\gamma}-1)\Pi_{\mathcal F}].
\]

The leading scalar is a global phase and the bracket is one phase query with
query angle (-\gamma). A fixed, instance-independent global-QAOA schedule
with one such binary cost layer per layer therefore has (q=p). Constant
worst-case success over the entire binary marked-set family requires
(p=\Omega(\phi^{-1/2})). If each layer makes at most (c) relevant queries,

\[
p\ge \frac1{2c}\left(\sqrt{\tau/\phi}-1\right)
\]

when the right side is positive.

This depth statement is not automatic for instance-trained QAOA. Training
queries, measurement shots, adaptive feedback, and final execution must be
counted together. A standard purification/deferred-measurement reduction is
plausible for a bounded worst-case number of queries, but is not formalized in
this audit.

## Grover achievability

For (0<M<N), let

\[
|G\rangle=M^{-1/2}\sum_{x\in\mathcal F}|x\rangle,
\quad
|B\rangle=(N-M)^{-1/2}\sum_{x\notin\mathcal F}|x\rangle,
\]

and let θ=arcsin√φ. The uniform state is
(|s\rangle=\sin\theta|G\rangle+\cos\theta|B\rangle). A π phase query
followed by reflection about |s⟩ rotates this plane by (2\theta), yielding

\[
P_{\rm Grover}(q)=\sin^2((2q+1)\theta).
\]

This is an achievability construction, not an asserted universal exact upper
bound. In the regime ((2q+1)\sqrt\phi\to0),

\[
P_{\rm Grover}(q)=(2q+1)^2\phi
+O((2q+1)^4\phi^2).
\]

For (q\ge1), the remainder is equivalently (O(q^4\phi^2)). Together with
the lower bound, this supports (q=\Theta(\phi^{-1/2})) for constant-success
unstructured search. Exact Grover optimality is not proved here.

## Structure-injection escape routes and nonclaims

The direct theorem does not cover ℱ-dependent initial states or mixers,
feasibility-preserving state preparation that already encodes ℱ, uncounted
enumeration of ℱ, or richer oracles exposing gradients, distances, graph
structure, or a succinct description. Structured families such as known
prefix sets, fixed-Hamming-weight sets, and known affine subspaces may admit
algorithms outside the black-box model.

The theorem does not directly establish a pointwise bound for natural RCSP
Hamiltonians. That would require an explicit reduction embedding a sufficiently
unstructured marked-set family into RCSP or a separate RCSP structural lower
bound.

## External prior-art verification required before publication

This offline audit contains no literature search or novelty claim. Relevant
prior theorems, standard adaptive-query reductions, and attribution must be
checked externally before publication.
