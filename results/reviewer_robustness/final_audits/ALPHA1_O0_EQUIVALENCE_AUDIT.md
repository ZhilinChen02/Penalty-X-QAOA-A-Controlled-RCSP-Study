# Audit S1 — alpha=1 versus matched O0

## Verdict

**PASS for objective equivalence; optimization-trajectory equivalence is not licensed.** Across all 222 executed discovery and post-hoc held-out alpha=1 endpoints, the maximum within-run difference between exact CVaR at alpha=1 and mean energy is `2.420e-13` (discovery-only maximum `1.821e-13`). The paper may therefore state that alpha=1 numerically recovers the mean-energy objective to machine precision.

## Closest frozen O0 comparison

The closest frozen control is the 168-row Phase-1.1 `P3_CONTINUATION_B1` mean-energy table. Every pair uses the same task, depth, seed, exactly identical embedded-p2 initialization, nominal 120-call budget, COBYLA name, `rhobeg=0.5`, and `catol=1e-8`. Initial alpha=1 versus O0 objective values differ by at most `2.023e-13`.

The full execution protocol is nevertheless **not identical**. The historical O0 table was produced with the Phase-1.1 optimizer wrapper under SciPy 1.17.0; A2 used the strict reviewer wrapper under SciPy 1.18.0. The historical wrapper also evaluated the start separately from its optimizer-call ledger, whereas the reviewer wrapper counted every optimizer objective call directly. Full evaluation trajectories were not persisted in either artifact and cannot be compared retrospectively.

## Endpoint comparison

- Same actual nfev: 164/168 pairs.
- Terminal theta equal within 1e-12: 0/168 pairs.
- Median/max terminal-theta absolute difference: 0.190695/1.63224.
- Median/max absolute terminal-objective difference: 0.0091399/0.31204.
- Median/max absolute P_feas difference: 0.000782593/0.0417349.
- Median/max absolute G_feas difference: 0.0347145/0.424697.
- Median/max absolute P_opt difference: 0.000378762/0.0333827.

These endpoint differences are not an objective-identity failure. They occur between numerically perturbed objective implementations executed through different wrapper/software versions; derivative-free COBYLA trajectories can bifurcate under such perturbations. Because both factors differ and trajectories are unavailable, the audit does not claim a unique causal allocation between floating-point perturbation and implementation version.

## Licensed manuscript wording

> At alpha=1, the CVaR objective numerically recovers the mean-energy objective to machine precision.

The manuscript must not state that alpha=1 and historical O0 optimization trajectories or terminal states are necessarily identical.
