# Phase 2 Confirmatory Report — Held-Out CVaR Dilution Confirmation

## A. Phase 2 status

**COMPLETE**. The held-out inferential dataset is separate from Phase 1.2 discovery evidence.

## B. Frozen identity

- Pre-run SHA: `99c928f1e76652b2bf562364b9a03c821df9e0b0`
- Manifest SHA-256: `0556bb659521e570cde5deac881cf1e0f771fcc46408750c2ef934f41054e0f6`
- Config SHA-256: `0e87433b5b33ad10b58affe40162e1cbdbcd4bcb5ec45d9bd38c6222a5549a2f`
- Preregistration SHA-256: `87b8c3d814d74098877b2e53b67c3d3a195e4b09dcf72fda7d9c26b775b992e1`
- Held-out tasks/base graphs: 84/15
- Discovery graph/task overlap: 0/0

## C. Execution

Planned and retained denominators are 252 p=2 preparation rows and 252 p=3 comparison rows; observed rows are 252 and 252. Scientific failure count is 0. Summed cell runtimes are 8359.7s (p=2) and 18838.3s (p=3); maximum recorded worker peak memory is 278.8 MB. No raw statevector was persisted.

## D. H1 — CVaR versus mean energy

Graph-level mean O3–O0 effect: **0.3547 decades**. One-sided grouped-bootstrap 95% lower bound: **0.2374**. Exact sign-flip raw p: **0.00012207**; Holm-adjusted p: **0.000244141**. Result: **PASS**.

## E. H2 — non-inferiority to capacity control

Graph-level mean O3–O2 effect: **-0.0086 decades**. Frozen margin: **-0.10 decades**. One-sided grouped-bootstrap 95% lower bound: **-0.0360**. Exact shifted sign-flip raw p: **0.000152588**; Holm-adjusted p: **0.000244141**. Result: **PASS**. O2 remains a statevector mechanistic capacity control, not a deployment-ready solver objective.

## F. Discovery versus held-out replication

| Quantity | Phase 1.2 discovery | Phase 2 held-out |
|---|---:|---:|
| O2–O0 capacity gap | 0.2193 | 0.2528 |
| O3–O0 benefit | 0.2124 | 0.3547 |
| O2–O3 residual gap | 0.0069 | 0.0035 |

Direction replicated: **YES**. Discovery rows were not pooled into Phase 2 inference.

## G. Dilution compensation

Median kappa is -0.0323 for O0, 0.2804 for O2, and 0.1374 for O3. The median O3–O0 kappa difference is 0.3622. These slope analyses are secondary and do not define a threshold or phase transition.

## H. Routing quality

O3 versus O0 `P_opt` wins/losses/ties: 80/4/0; paired median difference 0.00639968. O3 increased both `P_feas` and `P_opt` on 79 tasks, while feasibility rose and conditional optimal quality fell on 32 tasks. Median `P_opt_given_feasible` was 0.3605 (O0) versus 0.4077 (O3); median conditional route cost was 14.9322 versus 14.8318.

O3 ended at higher mean Hamiltonian energy than O0 on 81/84 tasks. This is not classified as an optimization failure because O3 optimizes the frozen CVaR loss rather than mean energy. Median feasibility changes from the common initial point were 0.00449598 for O0 and 0.0231348 for O3; median optimal-probability changes were 0.00198744 and 0.00960309.

## I. CVaR-tail mechanism

Strict energy separation passed 84/84 tasks and the tail condition passed 84/84 O3 rows. Fully feasible tails occurred in **20/84** tasks. Median O3–O0 `G_feas` benefit was 0.0561 when the tail was fully feasible and 0.3865 when it was partial. Median `P_opt_given_feasible` was 0.3951 for fully feasible tails and 0.4327 for partial tails. This is descriptive; alpha remained frozen at 0.10.

## J. Scientific verdict

**CVAR_HELDOUT_SUPPORTED**

This result does not imply quantum advantage, universal resolution of dilution, a critical dilution threshold, a phase transition, or general QAOA success/failure on RCSP.

## K. Next recommendation

**FREEZE_RESULTS_AND_START_MANUSCRIPT** — recorded only and not executed.

## Verification

- Tests: `70 passed in 2.45s`
- Immutable predecessors: verified
- Preregistered graph-level family: H1 and H2 only, Holm corrected
- Raw statevectors: not persisted
