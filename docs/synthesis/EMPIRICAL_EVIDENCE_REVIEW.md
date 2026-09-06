# Empirical Evidence Review

This review integrates canonical Phase 0--3 evidence without recomputing QAOA
optimization, merging inferential datasets, or using unfinished Phase 3B work.
Every number below maps to a frozen source in
`results/synthesis_v1/numeric_claim_audit.csv`.

## Evidence chain

### Task construction and scale control

The Phase-0 v1 universe contained 175 tasks on 25 base graphs, but 53 budget
rows repeated feasible sets. The v2 distinct-cardinality correction produced
140 tasks with no duplicated feasible set, spanning
\(\phi=1.9073486328125\times10^{-6}\) to \(0.0234375\). This is a controlled
synthetic stress universe, not evidence about the prevalence of dilution in
natural RCSP instances.

The Hamiltonian audit identified raw scale covariation with dilution. The
scale-controlled contract preserved the correct ground state on all 140 tasks
and reduced within-base scale variation (median maximum/minimum span ratio
1.07495). This supports the experimental contract; it does not remove every
possible confound.

### Pilot and optimization attribution

The 56-task, 10-graph Penalty-X pilot completed 504 optimized rows. Median
\(P_{\rm feas}\) at depths 1, 2 and 3 was 0.005089, 0.005984 and 0.003190,
respectively. The original p=3 compensation slope was anomalous and remained an
exploratory observation.

Phase 1.1 verified nested-ansatz identity for all 168 paired rows. The original
p=3 solution was worse than embedded p=2 in 29 of 168 runs; continuation
improved the optimized objective for all 29 and feasibility gain for 27. This
attributes a material part of the anomaly to optimization. It does not show
that classical optimization explains all dilution. Lower penalty energy and
higher feasibility were also not equivalent: among 108 comparisons where the
random p=3 run had lower objective than continuation, 82 had lower feasibility
gain.

### Objective discovery

Phase 1.2 compared mean energy O0, a penalty surrogate O1, exact-feasibility
capacity objective O2, and CVaR O3 with \(\alpha=0.10\) on the same discovery
tasks. The median O2--O0 capacity gap was 0.2193 decades. O1 left a 0.2417 gap;
O3 left 0.0069. O2 is a mechanistic, nondeployable ceiling because it directly
uses exact feasibility. These exploratory results selected O3 for held-out
testing; they are not pooled with Phase 2.

### Preregistered held-out confirmation

Phase 2 used 84 tasks from 15 base graphs with zero graph/task overlap with the
discovery set. The preregistered graph-level H1 contrast O3--O0 in compensation
was 0.354714949 decades (bootstrap SE 0.074725821; one-sided 95% lower bound
0.237378536; Holm-adjusted \(p=0.000244140625\)). H1 passed.

The H2 O3--O2 contrast was -0.00859515 decades against a -0.10 noninferiority
margin; its one-sided lower bound was -0.03604875 and its Holm-adjusted
\(p=0.000244140625\). H2 passed. O2 remains a capacity ceiling, so H2 is not a
deployability comparison.

Secondary held-out evidence showed O3--O0 \(P_{\rm opt}\) wins/ties/losses of
80/0/4 and a median difference of 0.00639968. Both \(P_{\rm feas}\) and
\(P_{\rm opt}\) increased on 79 of 84 tasks. Energy separation and the frozen
CVaR-tail condition held on all 84 tasks; 20 tails were fully feasible. This
supports the empirical interpretation that rich RCSP energy information adds
signal beyond binary feasibility membership. It is not a query lower bound and
does not show that CVaR violates one.

### Scaling response

Phase 3 constructed 180 tasks on 30 base graphs across `m=12...22`, but the
frozen resource guard permitted optimization only through `m=20`. The stage
completed 540 p=2 and 540 p=3 result rows; the m=22 cells were resource-censored
rather than treated as failures.

The development and interpolation response favored O2/O3 over O0 on average,
but the m=20 extrapolation reversed the mean-versus-CVaR ordering: mean
extrapolation \(\eta\) was 0.61499 for O0 and 1.28214 for O3 (higher is worse
compensation). The stage therefore supports heterogeneous, size-dependent
response and a resource ceiling, not a confirmed global scaling law. A
post-holdout decomposition found positive conditional-optimality slopes while
feasible-entry probability fell on all 75 completed graph-objective
trajectories. That is a descriptive mechanism hypothesis only.

## Claim ceilings

- The confirmatory center is the Phase-2 Penalty-X p=3 exact-statevector result.
- Phase 1 supplies discovery and mechanism, not confirmatory replication.
- Phase 3 supplies scaling response and censoring, not an asymptotic law.
- No hardware, natural-instance external validity, or end-to-end quantum
  advantage has been established.
- The empirical algorithms use rich Hamiltonian energy, so membership-only
  theory is a boundary/accounting model rather than a direct runtime theorem.
