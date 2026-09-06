# Phase 0.5 dilution stress protocol

Phase 0 v1 remains historical evidence. Its committed result files are verified
against SHA-256 hashes before and after Phase 0.5; no v1 task ID or canonical row is
rewritten.

The prospective v2 generator holds the layered topology policy, edge-count strata,
master seed, base count, and positive integer objective costs fixed. It expands the
edge-resource support from integers 1–9 to integers 1–1000. This prospective choice
was frozen before v2 characterization and does not inspect QAOA results.

For one graph, route resources are grouped into unique thresholds. Each threshold
has an exactly achievable cumulative feasible-route count. The policy reserves
exactly achievable preferred counts from `1, 2, 4, 8, 16, 32, M`, maps an
unachievable preference to a nearest unused achievable count, and fills remaining
capacity with thresholds maximally separated in log-cardinality. It emits at most
seven distinct budgets and never duplicates a feasible set merely to balance cells.

Graphs with fewer than seven achievable thresholds are marked
`INSUFFICIENT_DISTINCT_FEASIBLE_SETS`. Every primary stress task retains at least one
feasible route. `D1` is the tightest emitted level and larger D indices are looser.

Phase 0.5 performs exact characterization and resource projection only. It does not
run Penalty-X QAOA or any other Phase 1 algorithm.
