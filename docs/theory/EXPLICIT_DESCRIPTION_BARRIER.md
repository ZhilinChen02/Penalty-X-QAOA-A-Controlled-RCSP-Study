# Explicit-description barrier

## Counting statement

[V2_NEW_PROOF] An explicit representation containing $L$ bits has at most
$2^L$ distinct bit patterns and therefore describes at most $2^L$ feasible
subsets. Representing every size-$M$ subset of an $N$-element domain requires

\[
2^L\ge {N\choose M},
\qquad
\boxed{L\ge\log_2{N\choose M}}.
\]

[INFERENCE] This is a worst-family description-counting lower bound. It does
not say that every particular subset needs that many bits, and it does not by
itself establish computational or query hardness.

## Constant marked fraction

[V2_NEW_PROOF] If $M=\phi N$ with fixed $0<\phi<1$, Stirling estimates give

\[
\log_2{N\choose\phi N}
=NH_2(\phi)-O(\log N),
\]

where

\[
H_2(\phi)=-\phi\log_2\phi-(1-\phi)\log_2(1-\phi).
\]

For $N=2^n$, this is $\Theta(2^n)$ bits for a fixed nontrivial $\phi$.
Thus a polynomial-in-$n$ explicit representation cannot realize every such
marked subset.

## Singleton caveat

[V2_NEW_PROOF] For $M=1$,

\[
\log_2{N\choose1}=\log_2N=n.
\]

[COUNTEREXAMPLE] The counting argument therefore does not exclude a compact
singleton description. But if the $n$-bit singleton identifier—or equivalent
per-bit RCSP coefficients—is explicitly readable, the algorithm can output it
with zero membership-oracle queries. Compact description and hidden search are
different properties.

## Sparse marked sets

[V2_NEW_PROOF] For $1\le M=o(N)$,

\[
\log_2{N\choose M}
=\Theta\!\left(M\log_2\frac{N}{M}+M\right)
\]

under the usual sparse regimes. If $M=\operatorname{poly}(n)$ and $N=2^n$,
explicitly listing the $M$ marked $n$-bit labels requires $O(Mn)$ bits and
is polynomial in $n$.

[COUNTEREXAMPLE] Such a list destroys black-box search hardness because one may
read and output an entry. Hiding that list behind an oracle restores an oracle
model, but the resulting problem is no longer standard explicit-input RCSP.

## What the argument does not prove

[OPEN_GAP] It does not rule out structured polynomial-size families of feasible
sets, including affine subspaces, prefix sets, automaton languages, or subsets
defined by small circuits.

[OPEN_GAP] It does not prove that additive RCSP constraints cannot encode any
hard structured subclass. It only rules out a polynomial-length explicit
description capable of representing every arbitrary constant-density subset.

[OPEN_GAP] It does not stop an explicit representation from being difficult to
solve computationally. It says only that query hardness cannot be imported from
the whole random-subset family without accounting for description size and
information leakage.
