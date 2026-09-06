# Audit S2 — depth-budget nested diagnostic

## Verdict

**PASS.** All mapping, accounting, embedding, comparison-direction, and threshold checks passed. A deterministic stratified sample of 24 cases (one from every transition x budget x objective x PASS/FAIL cell) was exactly recomputed from the stored parameters using audit seed `2026090502`; all 24 classifications agree with the formal table.

## Semantics checked

- Formal design: 24 tasks, two objectives, three depths, three seeds, and one deterministic maximum-480 COBYLA trajectory per cell (432 trajectories total).
- Checkpoints: 1,296 best-evaluated incumbents from the verified 120/240/480 trajectory prefixes. The pre-formal checkpoint gate reproduced the independent capped history prefixes exactly. A checkpoint is therefore a genuine trajectory-prefix incumbent, not an invented continuation state.
- Nested comparisons: 864 rows. Signed regret is `deeper checkpoint objective - exactly embedded shallower checkpoint objective`; failure means regret greater than `1.0e-10`. This direction gives the deeper run credit for its best evaluated prefix incumbent.
- The legacy column name `deeper_terminal_objective` denotes that checkpoint incumbent in B1. Manuscript wording should use “best evaluated checkpoint” rather than imply an unavailable last-evaluated iterate.
- Task IDs, graph IDs, objectives, seeds, depths, and budgets match the frozen B1 manifest. Actual objective calls never exceed 480; checkpoint indices lie inside their requested/effective prefixes.
- Zero-angle embedding identity passes for 864/864 formal comparisons. The largest absolute identity error in the 24 exact audit cases is `0.000e+00`; largest recomputed regret discrepancy is `1.416e-15`.

## Reconfirmed pooled rates

- p2->p3, 120 nfev: 30/144 = 20.8%.
- p2->p3, 240 nfev: 31/144 = 21.5%.
- p2->p3, 480 nfev: 38/144 = 26.4%.
- p3->p4, 120 nfev: 45/144 = 31.2%.
- p3->p4, 240 nfev: 45/144 = 31.2%.
- p3->p4, 480 nfev: 47/144 = 32.6%.

Pooling uses 24 tasks x two objectives x three seeds = 144 comparisons per transition/budget cell. O0 and O3 remain separately identifiable in the underlying table; no task or seed is duplicated or dropped.

## Frozen interpretation

> Increasing the tested classical evaluation budget did not monotonically reduce certified nested-ansatz failures.

This statement is limited to the frozen 24 discovery tasks, COBYLA, O0/O3, p=2/3/4, the three original seeds, the best-prefix checkpoint diagnostic, and budgets 120/240/480. It does not imply that more optimization never helps, nor that deeper QAOA is intrinsically worse.
