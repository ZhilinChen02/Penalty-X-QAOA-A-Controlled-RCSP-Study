# Phase 3 empirical dilution scaling report

## A. PHASE 3 STATUS

RESOURCE_CENSORED

## B. TASK UNIVERSE

### Table 1 — Phase-3 task universe by size and split

| size_m | split | base_graphs | tasks | candidate_routes_min | candidate_routes_max |
| --- | --- | --- | --- | --- | --- |
| 12 | development | 4 | 24 | 6 | 6 |
| 12 | interpolation_holdout | 1 | 6 | 6 | 6 |
| 14 | development | 4 | 24 | 7 | 8 |
| 14 | interpolation_holdout | 1 | 6 | 7 | 7 |
| 16 | development | 4 | 24 | 9 | 11 |
| 16 | interpolation_holdout | 1 | 6 | 9 | 9 |
| 18 | development | 4 | 24 | 11 | 12 |
| 18 | interpolation_holdout | 1 | 6 | 11 | 11 |
| 20 | extrapolation_holdout | 5 | 30 | 11 | 16 |
| 22 | extrapolation_holdout | 5 | 30 | 14 | 17 |

Thirty base graphs and 180 tasks span m=12--22. The observed D range is 2.8342--6.6227; phi_state spans 2.3842e-07--0.0014648.

### Table 2 — phi_state and D ranges by size

| size_m | phi_min | phi_max | D_min | D_max |
| --- | --- | --- | --- | --- |
| 12 | 0.00024414 | 0.0014648 | 2.8342 | 3.6124 |
| 14 | 6.1035e-05 | 0.00048828 | 3.3113 | 4.2144 |
| 16 | 1.5259e-05 | 0.00016785 | 3.7751 | 4.8165 |
| 18 | 3.8147e-06 | 4.5776e-05 | 4.3394 | 5.4185 |
| 20 | 9.5367e-07 | 1.5259e-05 | 4.8165 | 6.0206 |
| 22 | 2.3842e-07 | 4.0531e-06 | 5.3922 | 6.6227 |

## C. RESOURCE CEILING

Largest completed m: 20. Censored sizes: [22].

### Table 3 — resource/runtime guards

| size_m | statevector_memory_mb | predicted_memory_per_worker_mb | single_p3_forward_time_s | predicted_full_optimization_s | resource_guard_pass | resource_censored | safe_worker_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12 | 0.0625 | 0.50781 | 0.0012252 | 0.36755 | True | False | 8 |
| 14 | 0.25 | 2.0312 | 0.006262 | 1.8786 | True | False | 8 |
| 16 | 1 | 8.125 | 0.032063 | 9.6189 | True | False | 8 |
| 18 | 4 | 32.5 | 0.13085 | 39.255 | True | False | 8 |
| 20 | 16 | 130 | 1.1429 | 342.87 | True | False | 8 |
| 22 | 64 | 520 | 7.4976 | 2249.3 | False | True | 8 |

## D. EXECUTION

Primary p2 rows: 540/540. Primary p3 rows: 540/540. Resource-censored planned cells: 180. Other failures: 0. Recorded stage wall time: 3.565 hours. Peak recorded worker memory: 362.6 MB.

## E. MODEL SELECTION

| objective | model_id | cv_rmse | cv_mae | cv_rmse_se | aicc |
| --- | --- | --- | --- | --- | --- |
| O0 | M1 | 0.33769 | 0.22418 | 0.04826 | -212.81 |
| O2 | M1 | 0.16922 | 0.12716 | 0.019399 | -344.9 |
| O3 | M1 | 0.19391 | 0.13185 | 0.028317 | -318.09 |

## F. SCALING EXPONENTS

| split | objective | n | mean | median | IQR | ci_lower | ci_upper | min | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | O0 | 16 | 1.0005 | 0.98809 | 0.96054 | 0.6013 | 1.4341 | -0.61519 | 3.3117 |
| development | O2 | 16 | 0.64673 | 0.65268 | 0.22076 | 0.46502 | 0.82843 | -0.14324 | 1.3513 |
| development | O3 | 16 | 0.63089 | 0.60837 | 0.26955 | 0.4365 | 0.81436 | -0.3991 | 1.482 |
| extrapolation_holdout | O0 | 5 | 0.61499 | 0.66643 | 0.40926 | 0.39626 | 0.83371 | 0.26 | 0.94435 |
| extrapolation_holdout | O2 | 5 | 0.78848 | 0.82194 | 0.15773 | 0.55898 | 0.97925 | 0.34619 | 1.061 |
| extrapolation_holdout | O3 | 5 | 1.2821 | 0.96538 | 0.41499 | 0.77088 | 2.049 | 0.65389 | 2.7952 |
| interpolation_holdout | O0 | 4 | 0.99979 | 0.87034 | 0.53777 | 0.40732 | 1.7217 | 0.23305 | 2.0254 |
| interpolation_holdout | O2 | 4 | 0.41267 | 0.36152 | 0.23601 | 0.13843 | 0.73805 | 0.05684 | 0.87079 |
| interpolation_holdout | O3 | 4 | 0.34891 | 0.37946 | 0.4184 | 0.11327 | 0.58455 | 0.029826 | 0.60688 |

## G. OBJECTIVE SCALING DIFFERENCE

| split | Delta_CVAR_MEAN_median | Delta_CVAR_MEAN_mean | Delta_CVAR_CAPACITY_median | Delta_CVAR_CAPACITY_mean |
| --- | --- | --- | --- | --- |
| development | -0.18231 | -0.36957 | 0.0015223 | -0.015837 |
| extrapolation_holdout | 0.3989 | 0.66715 | -0.03132 | 0.49366 |
| interpolation_holdout | -0.46855 | -0.65088 | -0.10676 | -0.063759 |

## H. HELD-OUT PREDICTION

Interpolation:

| split | objective | predictor | centered_response_RMSE | centered_response_MAE | eta_MAE | base_graphs |
| --- | --- | --- | --- | --- | --- | --- |
| interpolation_holdout | O0 | B_FLAT_ETA_0 | 0.41773 | 0.30648 | 0.99979 | 4 |
| interpolation_holdout | O0 | B_UNIFORM_ETA_1 | 0.3031 | 0.23424 | 0.51292 | 4 |
| interpolation_holdout | O0 | SELECTED_FROZEN | 0.30289 | 0.23362 | 0.49965 | 4 |
| interpolation_holdout | O2 | B_FLAT_ETA_0 | 0.19032 | 0.16508 | 0.41267 | 4 |
| interpolation_holdout | O2 | B_UNIFORM_ETA_1 | 0.23531 | 0.17686 | 0.58733 | 4 |
| interpolation_holdout | O2 | SELECTED_FROZEN | 0.16626 | 0.12835 | 0.34113 | 4 |
| interpolation_holdout | O3 | B_FLAT_ETA_0 | 0.17008 | 0.15072 | 0.34891 | 4 |
| interpolation_holdout | O3 | B_UNIFORM_ETA_1 | 0.23066 | 0.16859 | 0.65109 | 4 |
| interpolation_holdout | O3 | SELECTED_FROZEN | 0.15583 | 0.11136 | 0.30119 | 4 |

Extrapolation:

| split | objective | predictor | centered_response_RMSE | centered_response_MAE | eta_MAE | base_graphs |
| --- | --- | --- | --- | --- | --- | --- |
| extrapolation_holdout | O0 | B_FLAT_ETA_0 | 0.31337 | 0.22609 | 0.61499 | 5 |
| extrapolation_holdout | O0 | B_UNIFORM_ETA_1 | 0.25295 | 0.22055 | 0.38501 | 5 |
| extrapolation_holdout | O0 | SELECTED_FROZEN | 0.24808 | 0.21584 | 0.35847 | 5 |
| extrapolation_holdout | O2 | B_FLAT_ETA_0 | 0.33291 | 0.24961 | 0.78848 | 5 |
| extrapolation_holdout | O2 | B_UNIFORM_ETA_1 | 0.18106 | 0.14473 | 0.23591 | 5 |
| extrapolation_holdout | O2 | SELECTED_FROZEN | 0.17659 | 0.12983 | 0.26793 | 5 |
| extrapolation_holdout | O3 | B_FLAT_ETA_0 | 0.66528 | 0.46334 | 1.2821 | 5 |
| extrapolation_holdout | O3 | B_UNIFORM_ETA_1 | 0.46602 | 0.28996 | 0.51818 | 5 |
| extrapolation_holdout | O3 | SELECTED_FROZEN | 0.51633 | 0.30768 | 0.63204 | 5 |

The selected frozen model is compared directly with eta=1 uniform and eta=0 flat baselines. No holdout refit enters these values.

## I. CURVATURE / SIZE DEPENDENCE

One exponent suffices: YES. Selected forms: {"O0": "M1", "O2": "M1", "O3": "M1"}.

## J. OPTIMIZATION ADEQUACY

| size_m | objective_id | Delta_G_budget | Delta_objective_budget | same_common_initialization | substantial_budget_sensitivity | optimizer_adequacy_flag |
| --- | --- | --- | --- | --- | --- | --- |
| 12 | O0 | 0.14126 | 0.0090558 | True | True | False |
| 12 | O2 | 0.16116 | 0.035584 | True | True | False |
| 12 | O3 | 0.44244 | 0.62593 | True | True | False |
| 14 | O0 | 0.026426 | 0.023605 | True | False | False |
| 14 | O2 | 0.1505 | 0.040977 | True | True | False |
| 14 | O3 | 0.16653 | 0.11223 | True | True | False |
| 16 | O0 | 0.080009 | 0.0097992 | True | False | False |
| 16 | O2 | 0.01205 | 0.0012474 | True | False | False |
| 16 | O3 | 0.0041712 | 0.0044464 | True | False | False |
| 18 | O0 | 0.0057849 | 0.012283 | True | False | False |
| 18 | O2 | 0.0052186 | 0.0007195 | True | False | False |
| 18 | O3 | 0.033316 | 0.016993 | True | False | False |

Optimizer-limited claim ceiling triggered: False.

## K. OPTIMALITY

| response | base_graph_id | split | size_m | objective | n_levels | eta | intercept | RMSE | slope_vs_D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P_opt | g-0510569b7dbe24ff | development | 18 | O0 | 6 | -0.033549 | -2.5855 | 0.17788 | nan |
| P_opt | g-0510569b7dbe24ff | development | 18 | O2 | 6 | -0.08881 | -2.3688 | 0.053696 | nan |
| P_opt | g-0510569b7dbe24ff | development | 18 | O3 | 6 | 0.1083 | -1.4034 | 0.10833 | nan |
| P_opt | g-0deca2d7d26bc264 | extrapolation_holdout | 20 | O0 | 6 | 0.26299 | -2.1794 | 0.32455 | nan |
| P_opt | g-0deca2d7d26bc264 | extrapolation_holdout | 20 | O2 | 6 | 0.11041 | -2.4457 | 0.22778 | nan |
| P_opt | g-0deca2d7d26bc264 | extrapolation_holdout | 20 | O3 | 6 | 1.9236 | 6.7271 | 0.66415 | nan |
| P_opt | g-22d56a3beb2cd856 | development | 14 | O0 | 6 | 0.3344 | -0.91247 | 0.1554 | nan |
| P_opt | g-22d56a3beb2cd856 | development | 14 | O2 | 6 | 0.053189 | -1.7015 | 0.10416 | nan |
| P_opt | g-22d56a3beb2cd856 | development | 14 | O3 | 6 | 0.064762 | -1.6612 | 0.10279 | nan |
| P_opt | g-275f626d73d8e8bd | development | 12 | O0 | 6 | -0.16143 | -2.5778 | 0.44333 | nan |
| P_opt | g-275f626d73d8e8bd | development | 12 | O2 | 6 | -0.24269 | -2.4424 | 0.13724 | nan |
| P_opt | g-275f626d73d8e8bd | development | 12 | O3 | 6 | -0.39527 | -2.9051 | 0.10823 | nan |
| P_opt | g-2fd196f1ec0acd82 | development | 12 | O0 | 6 | 0.42971 | 0.12179 | 0.074362 | nan |
| P_opt | g-2fd196f1ec0acd82 | development | 12 | O2 | 6 | 0.37685 | 0.087231 | 0.079184 | nan |
| P_opt | g-2fd196f1ec0acd82 | development | 12 | O3 | 6 | 0.39624 | 0.15777 | 0.087386 | nan |
| P_opt | g-3115314f81a28bbb | interpolation_holdout | 14 | O0 | 6 | -1.1911 | -6.5354 | 0.4295 | nan |
| P_opt | g-3115314f81a28bbb | interpolation_holdout | 14 | O2 | 6 | -1.4577 | -7.3318 | 0.34656 | nan |
| P_opt | g-3115314f81a28bbb | interpolation_holdout | 14 | O3 | 6 | -1.4231 | -7.1779 | 0.31987 | nan |
| P_opt | g-340c0c88fcc14180 | interpolation_holdout | 16 | O0 | 6 | 0.18695 | -1.6134 | 0.29586 | nan |
| P_opt | g-340c0c88fcc14180 | interpolation_holdout | 16 | O2 | 6 | -0.14604 | -2.6741 | 0.11657 | nan |
| P_opt | g-340c0c88fcc14180 | interpolation_holdout | 16 | O3 | 6 | -0.32323 | -3.4146 | 0.069394 | nan |
| P_opt | g-3973175f1911b646 | development | 18 | O0 | 6 | -0.28255 | -3.8956 | 0.1783 | nan |
| P_opt | g-3973175f1911b646 | development | 18 | O2 | 6 | -0.63764 | -5.2252 | 0.084577 | nan |
| P_opt | g-3973175f1911b646 | development | 18 | O3 | 6 | -0.3225 | -3.7198 | 0.084901 | nan |
| P_opt | g-3cf4bd3967c31b19 | development | 14 | O0 | 6 | 0.74504 | 1.0623 | 0.15831 | nan |
| P_opt | g-3cf4bd3967c31b19 | development | 14 | O2 | 6 | -0.059054 | -1.6693 | 0.07778 | nan |
| P_opt | g-3cf4bd3967c31b19 | development | 14 | O3 | 6 | -0.012381 | -1.4813 | 0.11456 | nan |
| P_opt | g-3e6704b429f1ca32 | extrapolation_holdout | 20 | O0 | 6 | 0.22636 | -1.0958 | 0.16001 | nan |
| P_opt | g-3e6704b429f1ca32 | extrapolation_holdout | 20 | O2 | 6 | 0.38193 | 0.21897 | 0.10031 | nan |
| P_opt | g-3e6704b429f1ca32 | extrapolation_holdout | 20 | O3 | 6 | 0.34522 | -0.057916 | 0.16499 | nan |

P_opt scaling and P_opt_given_feasible slopes are secondary descriptive decompositions; they do not replace the primary P_feas analysis.

Across every completed split/objective group, every base graph had a positive
`P_opt_given_feasible` slope versus D (75/75 graph-objective trajectories). Median
endpoint increases ranged from 0.696 to 0.832 in absolute conditional probability,
while median log10(P_feas) endpoint changes were negative. Within this constructed
suite, the observed dilution failure therefore arose primarily from entering the
feasible set; concentration on an optimum conditional on feasibility generally
improved as the feasible set narrowed. This is a finite-range descriptive
decomposition, not a separate scaling-law claim.

## L. SCALING VERDICT

RESOURCE_CENSORED_SCALING

## M. OBJECTIVE VERDICT

MIXED_OBJECTIVE_SCALING

## N. ALLOWED PAPER CLAIM

Within the completed Penalty-X QAOA / controlled-RCSP range, feasible-state density showed an objective-specific empirical scaling response, but the prospectively censored upper size prevents claiming the full preregistered empirical scaling law; the objective-exponent comparison is reported only for the completed development and held-out graphs.

## O. NEXT RECOMMENDATION

REDESIGN_SCALING_SUITE

## P. GIT

The immutable completion commit is recorded after final hash verification. No push is performed.

## Scaling validity checklist

- at_least_5_levels_per_analyzed_graph: PASS
- at_least_4_development_graphs_per_size: PASS
- no_split_leakage: PASS
- new_universe_before_qaoa: PASS
- model_frozen_before_holdout: PASS
- interpolation_completed: PASS
- unseen_larger_size_completed: PASS
- curvature_compared: PASS
- frozen_cv_rule_used: PASS
- holdout_reported_without_refit: PASS
- optimizer_adequacy_reported: PASS
- zeros_failures_not_hidden: PASS
- objective_uncertainty_reported: PASS
- graph_heterogeneity_reported: PASS
- no_universal_asymptotic_wording: PASS

## Historical read-only comparison

| evidence_set | objective | base_graphs | median_eta | mean_eta | used_in_phase3_fit |
| --- | --- | --- | --- | --- | --- |
| Phase1_2_historical | O0 | 10 | 0.92229 | 0.96419 | False |
| Phase1_2_historical | O2 | 10 | 0.81148 | 0.72365 | False |
| Phase1_2_historical | O3 | 10 | 0.82742 | 0.77692 | False |
| Phase2_historical | O0 | 15 | 1.0323 | 1.3053 | False |
| Phase2_historical | O2 | 15 | 0.71961 | 0.76927 | False |
| Phase2_historical | O3 | 15 | 0.86261 | 0.76874 | False |
| Phase3_development | O0 | 16 | 0.98809 | 1.0005 | True |
| Phase3_development | O2 | 16 | 0.65268 | 0.64673 | True |
| Phase3_development | O3 | 16 | 0.60837 | 0.63089 | True |
| Phase3_extrapolation_holdout | O0 | 5 | 0.66643 | 0.61499 | False |
| Phase3_extrapolation_holdout | O2 | 5 | 0.82194 | 0.78848 | False |
| Phase3_extrapolation_holdout | O3 | 5 | 0.96538 | 1.2821 | False |
| Phase3_interpolation_holdout | O0 | 4 | 0.87034 | 0.99979 | False |
| Phase3_interpolation_holdout | O2 | 4 | 0.36152 | 0.41267 | False |
| Phase3_interpolation_holdout | O3 | 4 | 0.37946 | 0.34891 | False |

Phase 1/2 rows were excluded from Phase-3 task design, model selection, and coefficient fitting.
Their qualitative CVaR compensation pattern is consistent with Phase-3 development and
interpolation estimates, but it does not persist at the completed m=20 extrapolation
ceiling, where the paired CVaR-minus-mean eta contrast reverses sign. The predecessor
comparison therefore supports the `MIXED_OBJECTIVE_SCALING` verdict rather than a rescue
of the frozen scaling claim.

## Exact identity

Maximum eta/kappa identity error: 2.554e-15. The equality kappa=1-eta is algebraic and is not itself an empirical law.

## Figures

Fourteen figures in `figures/` retain individual graph trajectories or graph-level points. Figure 14 is explicitly classical simulation/runtime scaling, not quantum complexity.
