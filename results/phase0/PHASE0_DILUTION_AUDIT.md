# Phase 0 dilution stress audit

This report audits the immutable Phase 0 v1 evidence at commit
`5aa822f586f66ab3bb2b00e165780b111b13ad45`. Existing v1 result files and rows
were read only. Prospective v2 construction does not use QAOA outcomes.

**Audit verdict: `V2_RECOMMENDED`.**

## V1 summary

- Duplicated budgets: 53 / 175 (30.29%).
- Duplicated feasible sets: 53 / 175 (30.29%).
- Effective distinct levels per graph: min 2, median 5.0, max 7.
- Feasible-state fraction: min 1.90734863281e-06, median 0.0006103515625, max 0.0234375.
- Dilution score range: 1.6301 to 5.7196.

## Why 53 duplicate cases occurred

- 35 rows: repeated `lower`-quantile order-statistic indices. All are in S1/S2, whose graphs have only 3/4 candidate routes; seven requested quantiles therefore cannot yield seven sets.
- 18 rows: different order-statistic indices had equal route-resource sums under edge resources drawn from integers 1–9.
- 0 rows: budget rounding. V1 selected observed integer route resources directly, so there was no separate rounding operation.
- Across 169 route entries there were 139 per-graph unique consumptions, leaving 30 tied excess entries.
- 10 graphs structurally cannot supply seven path-cardinality levels; 16 graphs had fewer than seven unique resource thresholds after integer ties.

The generator structure is therefore the hard resolution limit for S1/S2. The narrow
integer resource support contributes the remaining ties. Fixed ordinary quantiles can
also miss an available distinct threshold when a selected order statistic is tied.

## V1 vs prospective v2 coverage

| Metric | Phase 0 v1 | Stress v2 |
|---|---:|---:|
| Task rows | 175 | 140 |
| Summed distinct feasible sets | 122 | 140 |
| Globally distinct phi_state values | 33 | 29 |
| Minimum phi_state | 1.90734863281e-06 | 1.90734863281e-06 |
| Median phi_state | 0.0006103515625 | 0.0001220703125 |
| Maximum phi_state | 0.0234375 | 0.0234375 |
| Dilution score range | 1.6301–5.7196 | 1.6301–5.7196 |

V2 adds 18 distinct within-graph feasible sets (14.75%) while storing zero duplicated primary sets. 10 graphs are explicitly marked `INSUFFICIENT_DISTINCT_FEASIBLE_SETS`; no row is copied to force a balanced 175-task matrix. V2 improves distinct resolution, not the theoretical global endpoints, which were already reached by v1.

Wide integer support 1–1000 produced 169 unique route-resource thresholds across 169 per-graph route entries and zero resource-tie graphs. V2 has fewer globally unique numeric phi values because its shared cardinality schedule repeats the same count/2^m values across base graphs; its gain is within-graph distinct stress resolution.

## Theoretical and actual minima by size

| Size | Edges | Theoretical minimum 1/2^m | V1 actual minimum | V2 actual minimum |
|---|---:|---:|---:|---:|
| S1 | 7 | 0.0078125 | 0.0078125 | 0.0078125 |
| S2 | 10 | 0.0009765625 | 0.0009765625 | 0.0009765625 |
| S3 | 13 | 0.0001220703125 | 0.0001220703125 | 0.0001220703125 |
| S4 | 16 | 1.52587890625e-05 | 1.52587890625e-05 | 1.52587890625e-05 |
| S5 | 19 | 1.90734863281e-06 | 1.90734863281e-06 | 1.90734863281e-06 |

## Pilot Phase 1 projection (not executed)

- Selected pilot tasks: 56.
- Penalty-X runs: 504.
- Single-process central wall time: 0.887 h (range 0.443–4.433 h).
- Conservative peak process RSS: 320.0 MiB.
- Estimated disk without statevectors: 3.97 MiB.

## Per-base-graph v1 audit

| Base graph | m | 2^m | Routes | Unique R | Effective | Index dup | Tie dup | Duplicate pairs | T1 phi | T1 route | T2 phi | T2 route | T3 phi | T3 route | T4 phi | T4 route | T5 phi | T5 route | T6 phi | T6 route | T7 phi | T7 route |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1-b000-g-030e22a4b8e64e77 | 7 | 128 | 3 | 2 | 2 | 4 | 1 | T2=T3=T4=T5=T6=T7 | 0.0234375 | 1 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 |
| S1-b001-g-c6bcaa76a703859c | 7 | 128 | 3 | 3 | 3 | 4 | 0 | T2=T3=T4; T5=T6=T7 | 0.0234375 | 1 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 |
| S1-b002-g-d4602cd1b1dba4b7 | 7 | 128 | 3 | 3 | 3 | 4 | 0 | T2=T3=T4; T5=T6=T7 | 0.0234375 | 1 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 |
| S1-b003-g-f318c6a9c544d080 | 7 | 128 | 3 | 3 | 3 | 4 | 0 | T2=T3=T4; T5=T6=T7 | 0.0234375 | 1 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 |
| S1-b004-g-9df77dbccff877f5 | 7 | 128 | 3 | 3 | 3 | 4 | 0 | T2=T3=T4; T5=T6=T7 | 0.0234375 | 1 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.015625 | 0.666667 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 | 0.0078125 | 0.333333 |
| S2-b000-g-c0608305feeffbb0 | 10 | 1024 | 4 | 3 | 3 | 3 | 1 | T2=T3=T4=T5; T6=T7 | 0.00390625 | 1 | 0.0029296875 | 0.75 | 0.0029296875 | 0.75 | 0.0029296875 | 0.75 | 0.0029296875 | 0.75 | 0.0009765625 | 0.25 | 0.0009765625 | 0.25 |
| S2-b001-g-43af4a2bb7f827f7 | 10 | 1024 | 4 | 4 | 4 | 3 | 0 | T2=T3; T4=T5; T6=T7 | 0.00390625 | 1 | 0.0029296875 | 0.75 | 0.0029296875 | 0.75 | 0.001953125 | 0.5 | 0.001953125 | 0.5 | 0.0009765625 | 0.25 | 0.0009765625 | 0.25 |
| S2-b002-g-dcee0d154a6a56e8 | 10 | 1024 | 4 | 4 | 4 | 3 | 0 | T2=T3; T4=T5; T6=T7 | 0.00390625 | 1 | 0.0029296875 | 0.75 | 0.0029296875 | 0.75 | 0.001953125 | 0.5 | 0.001953125 | 0.5 | 0.0009765625 | 0.25 | 0.0009765625 | 0.25 |
| S2-b003-g-1aeebbf57e1fc02e | 10 | 1024 | 4 | 4 | 4 | 3 | 0 | T2=T3; T4=T5; T6=T7 | 0.00390625 | 1 | 0.0029296875 | 0.75 | 0.0029296875 | 0.75 | 0.001953125 | 0.5 | 0.001953125 | 0.5 | 0.0009765625 | 0.25 | 0.0009765625 | 0.25 |
| S2-b004-g-09b1133f6e4fd993 | 10 | 1024 | 4 | 3 | 3 | 3 | 1 | T1=T2=T3; T4=T5; T6=T7 | 0.00390625 | 1 | 0.00390625 | 1 | 0.00390625 | 1 | 0.001953125 | 0.5 | 0.001953125 | 0.5 | 0.0009765625 | 0.25 | 0.0009765625 | 0.25 |
| S3-b000-g-3201b1f700a594cf | 13 | 8192 | 7 | 6 | 6 | 0 | 1 | T5=T6 | 0.00085449219 | 1 | 0.00073242188 | 0.857143 | 0.00061035156 | 0.714286 | 0.00048828125 | 0.571429 | 0.00036621094 | 0.428571 | 0.00036621094 | 0.428571 | 0.00012207031 | 0.142857 |
| S3-b001-g-6312121f837a016a | 13 | 8192 | 7 | 7 | 7 | 0 | 0 | none | 0.00085449219 | 1 | 0.00073242188 | 0.857143 | 0.00061035156 | 0.714286 | 0.00048828125 | 0.571429 | 0.00036621094 | 0.428571 | 0.00024414062 | 0.285714 | 0.00012207031 | 0.142857 |
| S3-b002-g-ccccfea2344eea34 | 13 | 8192 | 7 | 6 | 6 | 0 | 1 | T4=T5 | 0.00085449219 | 1 | 0.00073242188 | 0.857143 | 0.00061035156 | 0.714286 | 0.00048828125 | 0.571429 | 0.00048828125 | 0.571429 | 0.00024414062 | 0.285714 | 0.00012207031 | 0.142857 |
| S3-b003-g-14c0fab60fb67c6a | 13 | 8192 | 7 | 6 | 6 | 0 | 1 | T3=T4 | 0.00085449219 | 1 | 0.00073242188 | 0.857143 | 0.00061035156 | 0.714286 | 0.00061035156 | 0.714286 | 0.00036621094 | 0.428571 | 0.00024414062 | 0.285714 | 0.00012207031 | 0.142857 |
| S3-b004-g-d0c2be481b1e7235 | 13 | 8192 | 7 | 4 | 4 | 0 | 3 | T1=T2; T3=T4=T5 | 0.00085449219 | 1 | 0.00085449219 | 1 | 0.00061035156 | 0.714286 | 0.00061035156 | 0.714286 | 0.00061035156 | 0.714286 | 0.00024414062 | 0.285714 | 0.00012207031 | 0.142857 |
| S4-b000-g-5862e3c4d7860c94 | 16 | 65536 | 9 | 5 | 5 | 0 | 2 | T1=T2; T5=T6 | 0.0001373291 | 1 | 0.0001373291 | 1 | 9.1552734e-05 | 0.666667 | 7.6293945e-05 | 0.555556 | 6.1035156e-05 | 0.444444 | 6.1035156e-05 | 0.444444 | 1.5258789e-05 | 0.111111 |
| S4-b001-g-0b2888c172349795 | 16 | 65536 | 8 | 7 | 6 | 0 | 1 | T3=T4 | 0.00012207031 | 1 | 9.1552734e-05 | 0.75 | 7.6293945e-05 | 0.625 | 7.6293945e-05 | 0.625 | 4.5776367e-05 | 0.375 | 3.0517578e-05 | 0.25 | 1.5258789e-05 | 0.125 |
| S4-b002-g-e13c6faa15e11202 | 16 | 65536 | 8 | 6 | 5 | 0 | 2 | T3=T4; T5=T6 | 0.00012207031 | 1 | 9.1552734e-05 | 0.75 | 7.6293945e-05 | 0.625 | 7.6293945e-05 | 0.625 | 4.5776367e-05 | 0.375 | 4.5776367e-05 | 0.375 | 1.5258789e-05 | 0.125 |
| S4-b003-g-b7bfa4b08047a3d1 | 16 | 65536 | 10 | 8 | 7 | 0 | 0 | none | 0.00015258789 | 1 | 0.00012207031 | 0.8 | 0.00010681152 | 0.7 | 9.1552734e-05 | 0.6 | 6.1035156e-05 | 0.4 | 4.5776367e-05 | 0.3 | 1.5258789e-05 | 0.1 |
| S4-b004-g-50bfea5134a5b688 | 16 | 65536 | 8 | 7 | 6 | 0 | 1 | T5=T6 | 0.00012207031 | 1 | 9.1552734e-05 | 0.75 | 7.6293945e-05 | 0.625 | 6.1035156e-05 | 0.5 | 4.5776367e-05 | 0.375 | 4.5776367e-05 | 0.375 | 1.5258789e-05 | 0.125 |
| S5-b000-g-e15079b273b4594e | 19 | 524288 | 10 | 9 | 7 | 0 | 0 | none | 1.9073486e-05 | 1 | 1.5258789e-05 | 0.8 | 1.335144e-05 | 0.7 | 9.5367432e-06 | 0.5 | 7.6293945e-06 | 0.4 | 5.7220459e-06 | 0.3 | 1.9073486e-06 | 0.1 |
| S5-b001-g-0621bd668b23ad3e | 19 | 524288 | 12 | 9 | 6 | 0 | 1 | T5=T6 | 2.2888184e-05 | 1 | 2.0980835e-05 | 0.916667 | 1.5258789e-05 | 0.666667 | 1.335144e-05 | 0.583333 | 9.5367432e-06 | 0.416667 | 9.5367432e-06 | 0.416667 | 1.9073486e-06 | 0.0833333 |
| S5-b002-g-e3ffd0a86ed87aaa | 19 | 524288 | 12 | 10 | 7 | 0 | 0 | none | 2.2888184e-05 | 1 | 1.9073486e-05 | 0.833333 | 1.5258789e-05 | 0.666667 | 1.335144e-05 | 0.583333 | 1.1444092e-05 | 0.5 | 7.6293945e-06 | 0.333333 | 1.9073486e-06 | 0.0833333 |
| S5-b003-g-88f05556b4300cce | 19 | 524288 | 10 | 8 | 6 | 0 | 1 | T2=T3 | 1.9073486e-05 | 1 | 1.5258789e-05 | 0.8 | 1.5258789e-05 | 0.8 | 9.5367432e-06 | 0.5 | 7.6293945e-06 | 0.4 | 3.8146973e-06 | 0.2 | 1.9073486e-06 | 0.1 |
| S5-b004-g-97c4d57eb951f3b8 | 19 | 524288 | 12 | 9 | 6 | 0 | 1 | T3=T4 | 2.2888184e-05 | 1 | 1.9073486e-05 | 0.833333 | 1.5258789e-05 | 0.666667 | 1.5258789e-05 | 0.666667 | 9.5367432e-06 | 0.416667 | 5.7220459e-06 | 0.25 | 3.8146973e-06 | 0.166667 |
