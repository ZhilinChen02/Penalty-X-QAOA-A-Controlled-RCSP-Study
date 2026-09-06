# A1 — Optimizer robustness

**Execution status: COMPLETE.** Completed 2016/2016 runs; failed records: 0.

## Protocol

The frozen matrix uses discovery tasks, the three original seeds, p=2/3, O0/O3(alpha=0.10), COBYLA/Nelder–Mead/SLSQP, and a strict 120-objective-call budget. Every SLSQP finite-difference call is counted by the wrapper. SciPy-reported nfev is retained when SciPy returns normally; a null value after a hard wrapper stop is disclosed rather than imputed.

Manifest: `results/reviewer_robustness/manifests/manifest_optimizer_robustness.json`.

## Numerical findings

- COBYLA/O0: nested failures 28/168 (0.167); median signed regret -0.186917; median graph G_feas 0.9626.
- COBYLA/O3: nested failures 38/168 (0.226); median signed regret -0.0495381; median graph G_feas 1.9972.
- Nelder-Mead/O0: nested failures 54/168 (0.321); median signed regret -0.0783413; median graph G_feas 0.8855.
- Nelder-Mead/O3: nested failures 61/168 (0.363); median signed regret -0.0648611; median graph G_feas 2.0172.
- SLSQP/O0: nested failures 46/168 (0.274); median signed regret -0.0617496; median graph G_feas 1.0001.
- SLSQP/O3: nested failures 72/168 (0.429); median signed regret -0.0368037; median graph G_feas 2.0250.

## Certified-pass mechanism test

- COBYLA: 113 O0/O3 pairs pass both nested diagnostics; O0 has lower energy but lower feasibility than O3 in 103/113, and an O0 p3 energy improvement with feasibility loss versus embedded p2 occurs in 76/113.
- Nelder-Mead: 72 O0/O3 pairs pass both nested diagnostics; O0 has lower energy but lower feasibility than O3 in 65/72, and an O0 p3 energy improvement with feasibility loss versus embedded p2 occurs in 49/72.
- SLSQP: 70 O0/O3 pairs pass both nested diagnostics; O0 has lower energy but lower feasibility than O3 in 58/70, and an O0 p3 energy improvement with feasibility loss versus embedded p2 occurs in 41/70.

## Interpretation and limitation

The historical 29/168 value remains frozen and is not expected to be reproduced mechanically. This post-hoc matrix asks whether nested failure occurs outside COBYLA and whether energy–feasibility misalignment survives after certified failures are removed. Task rows are descriptive; effect intervals aggregate paired effects within graph.

No global optimizer, hardware noise, alternative mixer, or advantage comparison is included.

## Claim impact

The complete optimizer and PASS-only results above can support a qualified mechanism statement.
For a complete matrix, the paper may state that nested failure is not COBYLA-specific across the three tested local optimizers and that objective misalignment persists on dual-PASS runs. It should not call any optimizer universally unsuitable.

<!-- REVIEWER_ROBUSTNESS_SYNTHESIS -->

## Completed-result interpretation

- COBYLA: certified-PASS graph mean O3−O0 G_feas=0.7809, 95% graph bootstrap CI [0.5770, 0.9971].
- Nelder-Mead: certified-PASS graph mean O3−O0 G_feas=0.9271, 95% graph bootstrap CI [0.5796, 1.2473].
- SLSQP: certified-PASS graph mean O3−O0 G_feas=0.9938, 95% graph bootstrap CI [0.6096, 1.3458].

Where SciPy reported nfev, wrapper-versus-SciPy disagreements were 0/1512. SLSQP has 504 null SciPy nfev entries because the strict wrapper stopped at the call cap; its own counter still records every numerical finite-difference call.

Nested failures occur for all three tested local optimizers, so the phenomenon is not COBYLA-specific. More importantly, the positive PASS-only graph intervals and the frequent lower-energy/lower-feasibility O0 comparisons show that objective misalignment persists after the certified optimizer-failure cases are removed. This supports treating optimizer inadequacy and objective misalignment as distinct tested mechanisms, without claiming either optimizer is universally unsuitable.

**Claim impact:** supported across the tested local optimizers, with scope limited to the frozen tasks, seeds, depths, and 120-call budget.
