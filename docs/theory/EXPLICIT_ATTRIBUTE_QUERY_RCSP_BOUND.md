# Explicit-attribute-query RCSP bound

## Access model

The directed topology, branch labels, fixed objective coefficients, first-edge
resources, source, target, and budget are known. The explicit input also
contains a length-`K` status/attribute array

\[
z=(z_1,\ldots,z_K)\in\{0,1\}^K,
\qquad \sum_i z_i=M.
\]

The array is not free classical side information. It is accessed through the
standard quantum random-access input query

\[
O_z|i,b\rangle=|i,b\oplus z_i\rangle,
\]

and each invocation costs one input query. Arbitrary array-independent
computation is free in query complexity. If the complete array is instead
delivered at zero access cost, an algorithm may read/scan it classically and
this input-query lower bound is not the applicable model.

The result is therefore classified as

```text
explicit topology
+ explicit attribute array
+ quantum random-access input-query model
```

## Parallel-branch construction

Create vertices `s,t,u_1,...,u_K` and two-edge paths

\[
P_i:s\to u_i\to t.
\]

The first edge of every branch has resource one. The second has resource one
when `z_i=1` and two when `z_i=0`. Set budget `B=2`, and use equal fixed
objective costs. Therefore

\[
r(P_i)=
\begin{cases}
2,&z_i=1,\\
3,&z_i=0,
\end{cases}
\qquad
P_i\text{ feasible}\Longleftrightarrow z_i=1.
\]

There are exactly `M` feasible routes. A branch-feasibility check uses one
status-array query, and conversely the feasibility bit is exactly `z_i`.
Finding a feasible branch is thus the size-`M` marked search problem on `K`
labels with no leakage from the fixed topology or fixed attributes.

## Lower bound, success convention, and endpoint refinement

For a uniformly random size-`M` status vector, the audited adaptive search
theorem gives every hard-cap `q` algorithm

\[
\mathbb E_z P_{\rm success}(z)
\le \min\left\{1,(2q+1)^2\frac{M}{K}\right\}.
\]

Hence average success at least `tau` requires

\[
q\ge\frac12\left(\sqrt{\frac{\tau K}{M}}-1\right).
\]

The same lower bound applies to an algorithm promised success at least `tau`
for every size-`M` vector, since a uniform worst-case guarantee implies the
average guarantee.

The often-written unqualified statement

\[
Q(K,M)=\Theta(\sqrt{K/M})\quad(1\le M\le K)
\]

needs a success qualification. A zero-query uniformly random branch already
succeeds with probability `M/K` for every size-`M` vector. Thus, for a fixed
target `tau in (0,1]`,

\[
Q_\tau(K,M)=0\quad\text{when }M/K\ge\tau.
\]

In the nontrivial regime `M/K<tau`, integrality plus the displayed lower bound
gives

\[
Q_\tau(K,M)=\Omega_\tau(\sqrt{K/M}).
\]

Indeed, with `x=sqrt(K/M)`, if `sqrt(tau)x>=2` the continuous bound is at
least `sqrt(tau)x/4`; otherwise it is positive, so integer `q>=1`, which is
also at least `sqrt(tau)x/2`. This proves the same order for both average-case
target success and uniform worst-case target success.

For exact success (`tau=1`) the particularly clean form is

\[
\boxed{Q_{1}(K,M)=\Theta(\sqrt{K/M})\quad\text{for }1\le M<K,}
\]

with the necessary endpoint `Q_1(K,K)=0`.

## Matching upper bound

Prepare the uniform superposition over branch index and use the one-query
feasibility check as the Grover marking oracle. Amplitude amplification with
known `M` finds a feasible branch using `O(sqrt(K/M))` attribute queries; the
exact variant uses adjustable phases and at most a constant additive overhead.
Thus, whenever the target is nontrivial (`M/K<tau`),

\[
\boxed{Q_\tau^{\rm RCSP}(K,M)=\Theta_\tau(\sqrt{K/M}).}
\]

The construction is numerically checked, but the lower bound is the analytic
search reduction.

## Which feasible fraction is relevant?

The candidate input domain has

\[
\phi_{\rm path}=M/K.
\]

The same graph has `2K` edge variables, so its raw edge-bit statistic is

\[
\phi_{\rm state}=M/2^{2K}.
\]

Therefore `phi_path != phi_state`. The valid query lower bound tracks the
counted input-query domain of branch labels, not the invalid edge-bit Hilbert
space.

## Explicitness boundary and verdict

The input contains `Theta(K)` attribute cells and `Theta(K)` explicit graph
entries. This is a legitimate explicit-input query lower bound in input length
`K`; it is not a succinct `O(log K)`-bit reduction and gives no exponential
lower bound in compact-description size.

With the success/endpoint refinement above, the track verdict is

```text
EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND_VALID
```
