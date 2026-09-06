# POSTHOC_FINITE_SHOT_ENDPOINT_ROBUSTNESS

This directory contains a post-hoc sampling analysis of the already-frozen
O0 and O3 terminal distributions for all 84 held-out tasks. It is not a new
confirmatory experiment, does not retrain QAOA, and does not change the
preregistered H1/H2 family or its interpretation.

## Design

- Endpoints: frozen p=3 terminal parameters for O0 and O3.
- Sampling: 1,000, 10,000, and 100,000 shots; 20 deterministic replicates.
- Seed identity: SHA-256 of label, task ID, objective, shot count, and replicate.
- Estimators: P_feas, P_opt, normalized mean Hamiltonian energy, and empirical
  lowest-energy CVaR-0.10.
- All requested shot counts make alpha*N an integer (100, 1,000, 10,000).
  The implementation nevertheless supports a fractional final observation for
  noninteger cutoffs by weighting it fractionally before dividing by alpha*N.
- Individual samples and raw statevectors are not persisted.
- Ordering recovery is conditioned on a non-tied exact O3-vs-O0
  comparison; exact ties are counted separately in `aggregate.csv`.

## Integrity

The 140-task universe was regenerated only in memory from the frozen generator
seed/configuration and matched every manifest identity and characterization row.
The maximum absolute regenerated endpoint difference from stored exact metrics was `7.327e-15`.

## Compact ordering summary

| Shots | P_feas O3-vs-O0 ordering recovered |
|---:|---:|
| 1,000 | 0.948 |
| 10,000 | 0.993 |
| 100,000 | 1.000 |

Full bias, MAE, standard deviation, RMSE, percentile, relative-error, and
ordering summaries are in `aggregate.csv`. Replicate-level estimates (not
individual samples) are in `metrics.csv`.

## Interpretation boundary

These results quantify estimator uncertainty at exact simulator endpoints.
They do not establish finite-shot training robustness, device robustness,
noise robustness, compilation robustness, or hardware performance.
