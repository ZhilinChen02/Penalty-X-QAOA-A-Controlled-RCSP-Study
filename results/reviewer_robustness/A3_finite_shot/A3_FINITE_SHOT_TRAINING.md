# A3 — End-to-end finite-shot training

**Execution status: COMPLETE.** Completed 200/200 planned runs; failed records: 0.

## Protocol

The manifest freezes 10 held-out tasks selected only by graph, m, feasible fraction, and dilution. O0 and O3(alpha=0.10) use COBYLA with 240 actual objective calls, 1e3 or 1e4 shots per call, and 5 independent training/sampling seeds.

Every evaluation receives a fresh PCG64 sample whose seed is a stable SHA-256 derivation of task, objective, shots, training seed, and evaluation index. Final theta is evaluated with the exact statevector, separating noisy training from true final quality.

Manifest: `results/reviewer_robustness/manifests/manifest_finite_shot.json`; execution copy: `results/reviewer_robustness/A3_finite_shot/training_manifest.json`.

## Numerical findings

- SHOT_10000: graph mean O3−O0 G_feas=0.1706, 95% graph-cluster bootstrap CI [-0.0106, 0.3862].
- SHOT_1000: graph mean O3−O0 G_feas=0.1246, 95% graph-cluster bootstrap CI [-0.0050, 0.3351].
- EXACT_CANONICAL: graph mean O3−O0 G_feas=0.3599, 95% graph-cluster bootstrap CI [0.1641, 0.5697].
- Total objective calls: 10072; total sampled bitstrings: 55612000.
- 1000 shots/eval: median actual nfev=50; median exact-terminal G_feas SD across task/objective groups=0.04423.
- 10000 shots/eval: median actual nfev=51; median exact-terminal G_feas SD across task/objective groups=0.04447.

## Interpretation and limitations

Ordering and variance are reported without a positivity requirement. This simulator experiment tests sampling noise in the classical objective only; it does not model device, gate, readout, or hardware noise and does not establish hardware readiness.

## Claim impact

The complete graph-level effects above determine whether finite-shot training preserves the exact ordering.
Any paper statement must remain about finite-sampling objective estimation/training in an exact simulator; it must not be described as device-noise robustness or hardware readiness.

<!-- REVIEWER_ROBUSTNESS_SYNTHESIS -->

## Completed-result interpretation

- EXACT_CANONICAL: 9/10 graph effects are positive; mean=0.3599, 95% CI [0.1641, 0.5697].
- SHOT_10000: 8/10 graph effects are positive; mean=0.1706, 95% CI [-0.0106, 0.3862].
- SHOT_1000: 6/10 graph effects are positive; mean=0.1246, 95% CI [-0.0050, 0.3351].

Both shot-trained point estimates retain the exact O3−O0 sign, and 10k shots has better graphwise sign consistency than 1k. However, both shot-trained graph-cluster intervals cross zero and both effects are attenuated relative to exact training. The appropriate result is therefore a threshold-like, mixed finding: ordering is mostly preserved at 10k, less stable at 1k, and neither regime supports a hardware-readiness claim.

**Claim impact:** mixed for end-to-end finite-shot training; supported with qualification for fixed-endpoint estimation.
