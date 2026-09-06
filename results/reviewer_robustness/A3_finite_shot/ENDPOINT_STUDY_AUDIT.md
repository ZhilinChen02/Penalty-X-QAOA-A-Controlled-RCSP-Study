# Existing finite-shot endpoint study audit

## Integrity and coverage

The pre-existing post-hoc study at `results/posthoc_finite_shot_endpoint_v1/` passes its recorded input/output SHA-256 checks. It covers all **84 held-out tasks / 15 graphs**, both O0 and O3 frozen terminal states, [1000, 10000, 100000] shots, and 20 deterministic sampling replicates. It records P_feas, P_opt, mean energy, and empirical CVaR(alpha=0.10), with exact endpoint reconstruction errors checked against authoritative rows.

This evidence is reused and was **not rerun**. The new reviewer work only adds the missing alpha×shot paired estimator grid and end-to-end finite-shot optimization.

## Scientific boundary

The existing study holds theta fixed after exact-statevector training. It tests estimator error and endpoint ordering only. It cannot establish finite-shot training robustness, device or hardware robustness, noise robustness, compilation robustness, or hardware readiness.
