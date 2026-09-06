# Paper revision plan (no manuscript files modified)

## Main text candidates

1. Add a compact reviewer-robustness paragraph stating that nested failures also occur under Nelder–Mead and SLSQP, while PASS-only O3−O0 graph intervals remain positive for all three tested optimizers. Preserve the frozen 29/168 observation as the historical diagnostic.
2. State that the full discovery alpha scan places 0.10 on a broad 0.05–0.25 plateau and that alpha=1 agrees numerically with mean energy. Label the scan post-hoc and do not replace the preregistered alpha.
3. Add the finite-shot threshold result: fixed-endpoint ordering is strong by 10k shots, but end-to-end 1k/10k training effects are attenuated and their graph-level intervals cross zero.
4. Add the p=4 nuance: p4 terminal metrics improve over p3, while p3→p4 nested failures are more frequent and do not fall with budget. Avoid intrinsic-depth or barren-plateau language.
5. Add one explicit classical-context sentence: exact label-setting matches 140/140 optima in sub-millisecond time; the benchmark is mechanistic, not an advantage benchmark.

## Appendix/artifact

- Table R1: optimizer rates, signed regret, G_feas, and PASS-only graph intervals.
- Figure R1 and `depth_budget_contrasts.csv`: full depth × budget matrix and nested transitions.
- Figure R2 and `alpha_neighborhood_effects.csv`: alpha scan, with held-out rows marked POST_HOC_SENSITIVITY.
- Figures R3/R4: shot-trained effects and alpha×shots estimator map.
- Table R2: exact classical timings and label counters.
- Include frozen selection algorithms, run registry, code-amendment chain, and scheduling-only rebalancing records.

## Wording to narrow

- Replace any unqualified “depth-three failure is optimizer-induced” wording with “a certified subset is optimizer-inadequate; objective misalignment remains after those failures are removed.”
- Do not say that more budget monotonically repairs deeper optimization.
- Do not call finite-shot results hardware/noise robustness.
- Do not compare simulator wall time with the exact solver as a hardware-performance claim.

## B3

Do not add B3 for this revision unless a reviewer explicitly requests external validity beyond the layered-DAG construction. If triggered later, freeze a separate family manifest before generation and keep it appendix-only.
