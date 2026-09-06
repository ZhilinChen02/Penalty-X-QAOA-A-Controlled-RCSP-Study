# B2 — Exact classical RCSP context

Completed 140/140 canonical tasks; failed records: 0.

## Protocol and correctness

A resource-cost label-setting solver with elementary-path-safe dominance is instrumented for generated, expanded, dominance-pruned, resource-pruned, and maximum-live labels. High-resolution timings repeat each complete solve 20–100 times until at least 0.02 s of timed work is observed. The median is reported; microsecond differences are not interpreted.

Manifest: `results/reviewer_robustness/manifests/manifest_classical_baseline.json`.

Exact optimum agreement is **140/140**. Median solve time is 4.99785e-05 s, p95 9.54456e-05 s, maximum 0.00018814 s. Median generated labels: 13.0; maximum: 30.

## Interpretation and claim impact

The benchmark is deliberately classically tractable and is used for controlled mechanistic attribution rather than a quantum-advantage claim. Classical timing is context only and is not compared with simulator wall time as a hardware-performance claim.

Graph clustering is not used for the exact-agreement check: correctness is verified task by task on all 140 canonical instances. Timing summaries are descriptive and are not inferential performance comparisons.

This result supports placing the classical context in the main methods/limitations text, with detailed counters in the appendix.
