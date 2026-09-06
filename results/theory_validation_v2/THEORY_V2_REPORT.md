# Theory Validation v2 report

## A. THEORY V2 STATUS

`COMPLETE`

[INFERENCE] The three tracks were completed independently. Track B succeeded
after explicit model refinements. Track C did not find a polynomial
explicit-input RCSP bridge. Track A found extensive prior art for the coarse
search theory and left the exact phase-sensitive form unresolved.

## B. WORKTREE SAFETY

[V2_NEW_PROOF] Original initial status and final status are identical:

```text
 M src/qroute_dilution/phase3_tasks.py
?? configs/phase3b_highsize_v1.yaml
?? data/manifests/phase3b_highsize_v1/
?? protocols/phase3b_highsize_v1/
?? results/phase3b_highsize_v1/
?? scripts/run_phase3b_highsize_v1.py
?? src/qroute_dilution/phase3b_analysis.py
?? src/qroute_dilution/phase3b_execution.py
?? src/qroute_dilution/phase3b_tasks.py
?? src/qroute_dilution/torch_backend.py
?? tests/test_phase3b_highsize.py
```

[V2_NEW_PROOF] Original HEAD remained
`b9922aadbc3c098db74a8e4ee992572a698d1f53`; its tracked diff remained 5
insertions and 2 deletions in `phase3_tasks.py`. Unchanged: **YES**.

[V2_NEW_PROOF] New worktree:
`<LOCAL_WORKSPACE>/Q-RouteDilution-theory-v2`.
Branch: `theory/adaptive-query-rcsp-bridge-v1`.

## C. PRIOR ART

[PRIOR_ART_SOURCE] Network status: available. Searches performed: 21. Included
primary sources: 11. No downloaded paper was committed.

[INFERENCE] Verdict:

```text
COARSE_RESULT_PREEXISTS_PHASE_SENSITIVE_FORM_UNCLEAR
```

[PRIOR_ART_SOURCE] The closest results are BBBV's hybrid search lower bound;
Boyer--Brassard--Høyer--Tapp's multiple-mark analysis; Zalka and
Dohotaru--Høyer exact singleton optimality; Høyer arbitrary-phase amplitude
amplification; Gilyén--Arunachalam--Wiebe's arbitrary-phase hybrid method; and
Benchasattabuse et al.'s QAOA search-round bounds.

## D. ADAPTIVE THEOREM

[V2_NEW_PROOF] Let $\mathcal F$ be uniform among size-$M$ subsets of an
$N$-label basis and $\phi=M/N$. An algorithm may use arbitrary ancillas,
mixed states, intermediate measurements, discarded environments, classical
randomness, feed-forward, and early stopping. It begins independently of
$\mathcal F$, receives no other $\mathcal F$-dependent information, makes at
most $q$ membership-oracle calls on every branch, and outputs a label $x$.
Success means $x\in\mathcal F$.

[V2_NEW_PROOF] For either a fixed phase-flip oracle or the standard
membership-bit oracle,

\[
\boxed{
\mathbb E_{\mathcal F}P_{\mathcal F}
\le\min\{1,(2q+1)^2\phi\}.
}
\]

[V2_NEW_PROOF] If slot $t$ is a counted history-controlled direct sum of
phases and

\[
c_t=\sup_h|e^{-i\gamma_t(h)}-1|,
\]

then

\[
\boxed{
\mathbb E_{\mathcal F}P_{\mathcal F}
\le
\min\left\{1,\left(1+\sum_t c_t\right)^2\phi\right\}.
}
\]

The statements are average/random-subset bounds, not pointwise bounds.

| Theorem candidate | Verdict |
|---|---|
| Fixed-query v1 theorem | VALID_AS_STATED |
| Hard-cap adaptive theorem | VALID_AFTER_REFINEMENT |
| Fixed phase-flip adaptive model | VALID_STANDARD_REDUCTION_FORMALIZED |
| Membership-bit oracle | VALID_AFTER_REFINEMENT |
| Branch-dependent phase | VALID_AFTER_REFINEMENT |
| Variable stopping with hard cap | VALID_STANDARD_REDUCTION_FORMALIZED |
| Mixed-state/CPTP model | VALID_STANDARD_REDUCTION_FORMALIZED |
| Trained total-query theorem | VALID_STANDARD_REDUCTION_FORMALIZED |
| Expected-query-only theorem | VALID_AFTER_REFINEMENT |
| Naive hard-cap formula with \(q=\mathbb E Q\) | INVALID |
| Rich cost oracle | OPEN_GAP |

## E. ADAPTIVE PROOF

[V2_NEW_PROOF] Measurements are replaced by Stinespring isometries retaining
outcomes and discarded data in orthogonal transcript/environment registers.
Random choices are purified. Feed-forward becomes transcript-controlled,
$\mathcal F$-independent unitaries. Early-stopped branches are padded by
swapping an isolated scratch query into each remaining ordinary oracle slot.
The selected final label is reversibly moved into the success-measurement
register.

[V2_NEW_PROOF] The result is a fixed-slot pure algorithm. The v1 identity-oracle
hybrid proof applies. A phase flip or bit query has perturbation coefficient two;
a history-controlled phase slot has operator norm coefficient $c_t$. Final
projection and Minkowski give the stated bounds.

## F. ADAPTIVE NUMERICAL VALIDATION

[NUMERICAL_VALIDATION] Protocols: 528. Exhaustive protocol/subset evaluations:
12,960. Maximum coarse residual: $2.22\times10^{-16}$. Maximum
phase-sensitive residual: $2.22\times10^{-16}$. Direct/deferred distribution
difference: $5.55\times10^{-16}$. Hybrid-recursion residual: zero. Violations:
0.

## G. TRAINED QAOA

[V2_NEW_PROOF] The adaptive theorem applies when every same-instance datum is
obtained through the counted membership oracle and the entire interaction has a
deterministic total cap

\[
q_{\mathrm{total}}=\sum_{r,j}S_{rj}p_{rj}+q_{\mathrm{final}}.
\]

It covers a new sample, a best prior sample, or a transcript-selected output.
It constrains $q_{\mathrm{total}}$, not final trained depth.

[COUNTEREXAMPLE] Free access to an explicit QUBO, RCSP graph, penalty table,
feasible list, or same-instance coefficient data violates the oracle-only
assumption.

## H. EXPECTED QUERY COUNT

[COUNTEREXAMPLE] The exact hard-cap expression with $q=\mathbb E Q$ is false;
a 1% branch running 785-query Grover search at $\phi=10^{-6}$ violates it.

[V2_NEW_PROOF] A theorem was obtained after refinement. If
$\mathbb E Q\le\bar q$, then for every integer $T\ge0$,

\[
\mathbb E P\le
\min\left\{1,\frac{\bar q}{T+1}+\min\{1,(2T+1)^2\phi\}\right\}.
\]

This still yields $\bar q=\Omega(\phi^{-1/2})$ for fixed target success, but
not the false quadratic formula in $\bar q$.

[V2_NEW_PROOF] If \(Q\) is sampled independently before the interaction,
conditioning on \(Q\) additionally gives
\(\mathbb E P\le\min\{1,\phi\,\mathbb E(2Q+1)^2\}\). This expected-square
statement is not claimed for transcript-dependent stopping.

## I. RCSP BRIDGE

[V2_NEW_PROOF] Explicit parallel paths map membership exactly but require
$\Theta(N)$ input and visibly encode the marked set.

[V2_NEW_PROOF] A binary layered graph has $O(n)$ edges and $2^n$ paths, but
the audited exact arbitrary-subset additive encoding uses $N-M$ resources.

[OPEN_GAP] Succinct circuit predicates describe only structured subsets and
were not compiled into a standard additive RCSP bridge preserving black-box
access.

[COUNTEREXAMPLE] A compact singleton RCSP encoding reveals every marked bit in
its explicit coefficients.

[V2_NEW_PROOF] Oracle-RCSP is a direct corollary but is nonstandard.

[OPEN_GAP] Rich multilevel cost/penalty oracles can reveal more than membership;
status: `RICH_COST_ORACLE_EXTENSION_OPEN`.

## J. DESCRIPTION BARRIER

[V2_NEW_PROOF] Representing every size-$M$ subset requires

\[
L\ge\log_2{N\choose M}.
\]

For fixed $0<\phi<1$, this is
$NH_2(\phi)-O(\log N)=\Theta(2^n)$ bits when $N=2^n$. For $M=1$, it is
only $n$ bits; the caveat is that an explicit singleton identifier removes
search hardness. For $M=\operatorname{poly}(n)$, listing marked labels can be
polynomial length but equally exposes them.

## K. FINAL RCSP VERDICT

```text
ORACLE_RCSP_ONLY
```

## L. NOVELTY/POSITIONING

[INFERENCE] Paper positioning:

```text
KNOWN_SEARCH_THEORY_WITH_NEW_DILUTION_APPLICATION
```

[PRIOR_ART_SOURCE] Coarse query scaling, exact singleton search, multiple-mark
amplification, adaptive/coherent search normalization, arbitrary-phase methods,
and QAOA search bounds are known.

[OPEN_GAP] The exact phase-sensitive sum was not matched, but novelty
is unresolved. Potential contributions are a careful reformulation, total-query
specialization, access-model taxonomy, and empirical integration.

## M. ALLOWED CLAIM

[V2_NEW_PROOF] For uniformly random size-$M$ marked subsets accessed only
through membership queries, the audited feasible-dilution bound extends to
intermediate measurements, classical feed-forward, mixed states, and early
stopping when the complete interaction has a deterministic hard cap $q$,
giving average success at most $\min\{1,(2q+1)^2M/N\}$. For same-instance
variational training under the same oracle-only condition, $q$ counts every
training shot, evaluation, feedback round, and final query. The result applies
directly to oracle-RCSP, but no direct lower bound for standard explicit-input
RCSP is established.

## N. PROHIBITED CLAIM

[COUNTEREXAMPLE] The strongest tempting invalid statement is: “All trained
QAOA algorithms for explicit RCSP require final circuit depth
$\Omega(\phi^{-1/2})$.” It confuses final depth with total query cost, ignores
free explicit side information and rich cost values, and assumes an RCSP bridge
that was not found.

## O. OPEN GAPS

[OPEN_GAP] Rich value/cost oracle lower bound.

[OPEN_GAP] Polynomial explicit-input RCSP bridge or structured-subclass theorem.

[OPEN_GAP] A sharper expected-query success theorem beyond truncation.

[OPEN_GAP] Independent external proof review.

[OPEN_GAP] Exact prior-art status of the phase-sensitive formula.

## P. TESTS

[NUMERICAL_VALIDATION] Full suite: 123 passed, 0 failed. V1 predecessor files
are unchanged from commit `b9922aa`. Original worktree snapshot is byte-for-byte
unchanged.

## Q. GIT

[INFERENCE] Work is committed only on
`theory/adaptive-query-rcsp-bridge-v1` with message
`Formalize adaptive query bounds and audit the RCSP bridge`. It is not pushed or
merged. The commit SHA is reported in the final handoff because a commit cannot
contain its own final SHA.
