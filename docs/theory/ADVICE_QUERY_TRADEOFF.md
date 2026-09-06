# Finite classical advice and membership-query tradeoff

## Advice alphabet lemma

Assume the posterior model in `POSTERIOR_STRUCTURE_DILUTION_THEOREM.md` and
`|supp S|<=2^b`. For each supported advice value choose

\[
x_s\in\arg\max_x\Pr[x\in F\mid S=s].
\]

Then

\[
\begin{aligned}
\Lambda
&=\sum_s\Pr(S=s)\Pr(x_s\in F\mid S=s)\\
&=\sum_s\Pr(S=s,x_s\in F)\\
&\le\sum_s\Pr(x_s\in F)\\
&=|\operatorname{supp}S|\,\phi\\
&\le2^b\phi.
\end{aligned}
\]

The penultimate equality counts one unconditional event per advice value. If
two advice values select the same `x_s`, that event is deliberately counted
twice; duplicate maximizers can only make this union-free upper bound looser,
not invalidate it. Since `Lambda<=1`,

\[
\boxed{\Lambda(S)\le\min\{1,2^b\phi\}.}
\]

The argument covers randomized as well as deterministic classical advice
channels.

## Advice-query theorem

Combining the alphabet lemma with the posterior hard-cap theorem gives

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\{1,(2q+1)^2 2^b\phi\}.
}
\]

For target average success `tau>0`, a necessary real-valued condition is

\[
b\ge\log_2\frac{\tau}{(2q+1)^2\phi}
\]

when the right side is positive. Since physical classical advice length is a
nonnegative integer,

\[
\boxed{
b\ge\max\left\{0,
\left\lceil\log_2\frac{\tau}{(2q+1)^2\phi}\right\rceil
\right\}.
}
\]

Edge cases are audited before taking the ceiling: `tau=0` needs no advice;
`phi=0` admits no successful member output and is outside the logarithmic
formula; `phi=1` needs no structure; and when the logarithm is nonpositive the
necessary lower bound is zero. This is a necessary condition, not a claim that
every bit allocation meeting it is useful.

## Phase-sensitive form

If the slot coefficients `c_t` are global constants, independent of the advice
value, then

\[
\boxed{
\mathbb E P_{\rm success}
\le\min\left\{1,
\left(1+\sum_t c_t\right)^2 2^b\phi
\right\}.
}
\]

If coefficients depend on `S`, the correct statement is instead

\[
\mathbb E_S\left[
\min\{1,C(S)^2\lambda_S\}
\right]
\le
\min\{1,\mathbb E_S[C(S)^2\lambda_S]\}.
\]

One may use global per-slot suprema to recover a factored bound, but may not
replace `C(S)^2 lambda_S` by a product of unrelated averages.

## Tightness and meaning

For singleton marked sets, `b=log2 N` bits can name the marked label and
saturate the zero-query scale. At the other extreme, constant advice gives
`Lambda=phi` and recovers ordinary dilution. The theorem quantifies information
access only. It does not convert advice bits into preprocessing time, circuit
depth, memory traffic, or state-preparation cost.

Verdict:

```text
FINITE_ADVICE_TRADEOFF_VALID
```
