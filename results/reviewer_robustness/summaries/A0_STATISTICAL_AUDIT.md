# R0 — statistical and frozen-protocol audit

## Finding

Existing confirmatory inference is already graph-level and does not require correction. This audit found clustering in the task layout, but **did not find pseudo-replication in the preregistered Phase-2 H1/H2 inference**.

## Task topology

- Discovery: **56 tasks / 10 base graphs**; each graph contributes 3–7 dilution tasks.
- Held-out: **84 tasks / 15 base graphs**; each graph contributes 3–7 dilution tasks.
- Phase 3: **180 tasks / 30 base graphs**; every graph contributes six dilution tasks. Split counts are {'development': 96, 'extrapolation_holdout': 60, 'interpolation_holdout': 24}.

Tasks from one graph are therefore correlated repeated conditions and cannot be treated as independent replicates for new inference.

## Existing Phase-2 confirmatory statistics

The frozen pipeline first averages all planned dilution-level contrasts within each graph, then gives each of 15 held-out graphs equal weight. It uses exact one-sided sign flips of paired graph contrasts, whole-graph bootstrap resampling, and Holm correction over the preregistered two-hypothesis H1/H2 family. The frozen H1 graph mean is 0.354715 decades (Holm-adjusted p=0.000244140625); H2 is -0.008595 decades (Holm-adjusted p=0.000244140625). These values are inventoried, not re-estimated or replaced.

## New reviewer-robustness statistics

New experiments retain task-level results descriptively. Paired O3−O0 effects are formed within task, averaged within base graph, and summarized across equal-weight graphs with graph-cluster bootstrap confidence intervals. Any sign-flip result is explicitly post-hoc and is not added to the frozen H1/H2 family.

## Frozen boundary

This pass will not recalculate or replace the discovery/held-out assignment, alpha=0.10 selection, H1/H2 family, headline p-values or intervals, 29/168 observation, m=20 reversal, m=22 censoring, or theory claims. Tracked canonical inputs and results are protected by the pre-run SHA-256 inventory at `results/reviewer_robustness/audit/canonical_hashes_before.json`.
