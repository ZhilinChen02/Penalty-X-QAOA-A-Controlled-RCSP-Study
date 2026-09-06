# Structure/advice prior-art audit

## Method

The audit used the required search phrases plus exact-formula searches and
inspected arXiv originals, publisher records, or author-hosted primary copies.
Downloaded papers were not stored. The complete query log and comparison
matrix are in:

- `results/theory_validation_v3/prior_art_search_log.csv`
- `results/theory_validation_v3/prior_art_structure_tradeoff.csv`

Failure to locate a theorem is not evidence that none exists. No novelty claim
is made from this bounded search.

## Closest search results

[Boyer, Brassard, Høyer, and Tapp](https://arxiv.org/abs/quant-ph/9605034)
analyze Grover search with multiple marked items and give search lower bounds.
[Zalka](https://arxiv.org/abs/quant-ph/9902049) gives order-optimal search for
known/unknown marked counts and notes an exact-success variant. These are the
direct foundations for the `sqrt(K/M)` branch-query result; that search order
is known prior art.

[Montanaro](https://arxiv.org/abs/0908.3066) studies “quantum search with
advice,” where the marked location is sampled from a known prior distribution,
and obtains constant-factor optimal expected-query behavior.
[He, Zhang, and Sun](https://arxiv.org/abs/2009.08721) optimize expected success
at fixed query count under prior knowledge. These models are close in theme but
do not, in the inspected statements, give an instance-dependent finite-alphabet
channel `S(F)` followed by the posterior size-`M` projector norm used here.

[Nayebi, Aaronson, Belovs, and Trevisan](https://arxiv.org/abs/1408.3193),
[Chung, Liao, and Qian](https://arxiv.org/abs/1911.09176), and
[Chung, Guo, Liu, and Qian](https://arxiv.org/abs/2006.05650) establish
classical- and quantum-advice time/space/query tradeoffs for function or
permutation inversion with preprocessing. Their advice depends on an oracle
and is used against a later inversion challenge. These strong results show
that preprocessing/advice tradeoffs are established territory, but their task,
parameters, and statements are not the marked-subset posterior theorem.

[König, Renner, and Schaffner](https://arxiv.org/abs/0807.1338) give the
operational guessing-probability meaning of conditional min-entropy, and
[Vitanov et al.](https://arxiv.org/abs/1205.5231) develop smooth min/max-entropy
chain rules. Thus a factor bounded by the size/dimension of side information is
consistent with established leakage principles; the elementary `2^b` advice
lemma should not be presented as conceptually unprecedented.

## Explicit graph/query context

[Beals et al.](https://arxiv.org/abs/quant-ph/9802049) formalize standard
input-bit quantum query lower bounds.
[Dürr, Heiligman, Høyer, and Mhalla](https://arxiv.org/abs/quant-ph/0401091)
show that graph-query complexity changes between adjacency-matrix and
adjacency-array models. Those results support the v3 insistence on a precise
attribute-query interface but do not imply a raw-`phi_state` RCSP bound.

[Galperin and Wigderson](https://doi.org/10.1016/S0019-9958(83)80004-7) and
[Papadimitriou and Yannakakis](https://doi.org/10.1016/S0019-9958(86)80009-2)
show that succinct graph representations can have radically different
complexity from explicit ones. This is broad prior art for representation
sensitivity, not the exact rational RCSP edge-subdivision identity.

For explicit RCSP practice,
[Ahmadi et al.](https://doi.org/10.1609/aaai.v35i14.17450) describe exact
resource-constrained pathfinding algorithms that exploit initialization and
search heuristics. This supports treating natural explicit RCSP as a
structure-rich problem rather than an unstructured membership oracle.

## Exact-form audit

Searches for the literal `(2q+1)^2` with advice, the `2^b` advice/query factor,
posterior quantum search, and effective support found no inspected primary
source stating exactly

\[
P_{\rm success}\le(2q+1)^2 2^b\phi
\]

for a uniform random size-`M` subset, an instance-dependent advice channel, and
a hard membership-query cap. The formula is nevertheless a short consequence
of known hybrid-search reasoning plus an elementary finite-alphabet leakage
bound. Independent expert/literature review is still required before any
novelty assertion.

## Verdict

Primary:

```text
NOVELTY_UNRESOLVED
```

Secondary descriptive label:

```text
POTENTIALLY_DISTINCT_POSTERIOR_PROJECTOR_FORM
```

The known `sqrt(K/M)` search result, prior-distribution search, min-entropy
guessing interpretation, and preprocessing tradeoffs must all be credited as
prior art.
