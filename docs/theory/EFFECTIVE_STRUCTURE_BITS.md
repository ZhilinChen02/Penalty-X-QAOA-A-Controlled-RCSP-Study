# Effective structure bits and effective support

Assume `0<phi=M/N<=1` and define

\[
b_{\rm eff}=\log_2\frac{\Lambda(S)}{\phi}.
\]

Because `phi<=Lambda<=1`,

\[
\boxed{0\le b_{\rm eff}\le\log_2(1/\phi).}
\]

For advice with at most `b` classical bits, `Lambda<=2^b phi`, hence
`b_eff<=b`. Effective structure bits measure the posterior concentration gain
relevant to this theorem. They are not automatically physical stored bits,
runtime, gate count, or full implementation information.

## Necessary structure-query budget

Substitution into the hard-cap theorem gives

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\{1,(2q+1)^2 2^{b_{\rm eff}}\phi\}.
}
\]

For target success `tau>0`, the necessary tradeoff is

\[
\boxed{
b_{\rm eff}+2\log_2(2q+1)
\ge\log_2\frac{\tau}{\phi}.
}
\]

This is sometimes useful as a budget interpretation, but it is not a
conservation law and is not sufficient for success.

## Exponential-dilution corollary

Let `phi_n=2^{-alpha n}` for a constant `alpha>0`, let target success
`tau in (0,1]` be constant, and suppose `q(n)<=C n^k` for constants `C,k` and
all sufficiently large `n`. Then

\[
\begin{aligned}
b_{\rm eff}
&\ge \alpha n+\log_2\tau-2\log_2(2q(n)+1)\\
&\ge \alpha n-2k\log_2n-O(1)\\
&=\boxed{\alpha n-O(\log n)}.
\end{aligned}
\]

This corollary is for the uniform random size-`M` subset prior and the stated
membership/advice model. It does not automatically transfer to natural
explicit RCSP instances.

## Effective support compression

Define

\[
K_{\rm eff}=\frac{M}{\Lambda(S)}.
\]

The bounds on `Lambda` imply

\[
\boxed{M\le K_{\rm eff}\le N},
\qquad
\boxed{
\frac{N}{K_{\rm eff}}=
\frac{\Lambda}{\phi}=2^{b_{\rm eff}}.
}
\]

The search theorem becomes

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\left\{1,(2q+1)^2\frac{M}{K_{\rm eff}}\right\}.
}
\]

Consequently, target `tau` requires

\[
\boxed{
K_{\rm eff}\le\frac{(2q+1)^2M}{\tau}.
}
\]

Interpretation: injected structure must compress effective candidate support
to within a quadratic-query factor of feasible-set size. This remains a
necessary condition.

## Known-candidate-set corollary

Suppose advice reveals a set `C_s` of size `K` and, **conditional on that
advice**, `F` is uniform over all size-`M` subsets of `C_s`. Every member of
`C_s` then has posterior inclusion probability `M/K`, every outside label has
probability zero, and

\[
\lambda_s=M/K,
\qquad K_{\rm eff}=K.
\]

Merely knowing that `C_s` contains all feasible labels is insufficient. Under
a nonuniform posterior, its labels can have unequal membership probabilities,
so `lambda_s` need not equal `M/K`; `K_eff=M/lambda_s` is the correct summary.
