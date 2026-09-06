# Hamiltonian scale and penalty-confound audit

Phase 0.6 reads the frozen v1/v2 tasks and exact references. It does not execute QAOA.
No existing result row, task manifest, or evidence file was modified.

**Scale audit verdict: `SCALE_CONTROL_RECOMMENDED`.**

## Exact ground-state correctness

- Current medium contract exact-original-optimal: **140/140**.
- Scale-controlled prospective contract exact-original-optimal: **140/140**.
- Current valid ground states: 140/140.
- Current resource-feasible ground states: 140/140.
- Controlled flow/resource classification unchanged: 140/140.

Any count below 140 is a penalty-correctness failure, not a QAOA result.

## Scale-confound evidence

- Current v2 energy-span range: 3.42698e+07 to 1.82405e+09; median 4.65752e+08.
- Current weighted resource-penalty/cost ratio range: 426739 to 1.39623e+07.
- V2/v1 median energy-span factor: 11683.8.
- V2/v1 median resource-penalty/cost-ratio factor: 12203.7.
- Within-base max/min span ratio, current: min 1.21503, median 1.72526, max 4.0375.
- Within-base max/min span ratio, controlled: min 1.0271, median 1.07495, max 1.15163.

Correlations below are diagnostics, not causal claims.

### Global Spearman correlations with dilution score

| metric | n | spearman_rho | spearman_pvalue |
|---|---|---|---|
| resource_penalty_p95 | 140 | 0.878882 | 3.36434e-46 |
| resource_penalty_max | 140 | 0.89534 | 2.53381e-50 |
| total_energy_p95 | 140 | 0.878766 | 3.57898e-46 |
| total_energy_max | 140 | 0.89534 | 2.53381e-50 |
| resource_penalty_to_cost_ratio | 140 | 0.73972 | 1.65246e-25 |
| flow_penalty_to_cost_ratio | 140 | 0.657056 | 1.18662e-18 |

### Size-stratified Spearman correlations

| group | metric | n | spearman_rho | spearman_pvalue |
|---|---|---|---|---|
| S1 | resource_penalty_p95 | 15 | 0.869318 | 2.56936e-05 |
| S1 | resource_penalty_max | 15 | 0.869318 | 2.56936e-05 |
| S1 | total_energy_p95 | 15 | 0.869318 | 2.56936e-05 |
| S1 | total_energy_max | 15 | 0.869318 | 2.56936e-05 |
| S1 | resource_penalty_to_cost_ratio | 15 | 0.869318 | 2.56936e-05 |
| S1 | flow_penalty_to_cost_ratio | 15 | 0 | 1 |
| S2 | resource_penalty_p95 | 20 | 0.767811 | 7.73448e-05 |
| S2 | resource_penalty_max | 20 | 0.550652 | 0.0118683 |
| S2 | total_energy_p95 | 20 | 0.767811 | 7.73448e-05 |
| S2 | total_energy_max | 20 | 0.550652 | 0.0118683 |
| S2 | resource_penalty_to_cost_ratio | 20 | 0.69801 | 0.000621136 |
| S2 | flow_penalty_to_cost_ratio | 20 | 0 | 1 |
| S3 | resource_penalty_p95 | 35 | 0.581358 | 0.000249826 |
| S3 | resource_penalty_max | 35 | 0.517706 | 0.00144671 |
| S3 | total_energy_p95 | 35 | 0.581358 | 0.000249826 |
| S3 | total_energy_max | 35 | 0.517706 | 0.00144671 |
| S3 | resource_penalty_to_cost_ratio | 35 | 0.652083 | 2.19532e-05 |
| S3 | flow_penalty_to_cost_ratio | 35 | 0 | 1 |
| S4 | resource_penalty_p95 | 35 | 0.567696 | 0.00037538 |
| S4 | resource_penalty_max | 35 | 0.413975 | 0.0134283 |
| S4 | total_energy_p95 | 35 | 0.567696 | 0.00037538 |
| S4 | total_energy_max | 35 | 0.413975 | 0.0134283 |
| S4 | resource_penalty_to_cost_ratio | 35 | 0.515137 | 0.00154213 |
| S4 | flow_penalty_to_cost_ratio | 35 | -0.022198 | 0.89928 |
| S5 | resource_penalty_p95 | 35 | 0.634006 | 4.32923e-05 |
| S5 | resource_penalty_max | 35 | 0.507261 | 0.00186998 |
| S5 | total_energy_p95 | 35 | 0.634006 | 4.32923e-05 |
| S5 | total_energy_max | 35 | 0.507261 | 0.00186998 |
| S5 | resource_penalty_to_cost_ratio | 35 | 0.559118 | 0.000480429 |
| S5 | flow_penalty_to_cost_ratio | 35 | 0.0151361 | 0.931229 |

### Within-base-graph Spearman summary

Each metric was evaluated separately inside every base graph. Undefined correlations
occur when the numerical component is constant across that graph's stress levels.

| metric | base_graphs | defined_correlations | rho_min | rho_median | rho_max |
|---|---|---|---|---|---|
| resource_penalty_p95 | 25 | 25 | 1 | 1 | 1 |
| resource_penalty_max | 25 | 25 | 1 | 1 | 1 |
| total_energy_p95 | 25 | 25 | 1 | 1 | 1 |
| total_energy_max | 25 | 25 | 1 | 1 | 1 |
| resource_penalty_to_cost_ratio | 25 | 25 | 1 | 1 | 1 |
| flow_penalty_to_cost_ratio | 25 | 0 | nan | nan | nan |

## V1 vs v2 current-contract scale

| Metric | v1 | v2 |
|---|---:|---:|
| edge_resource_min | 1 | 2 |
| edge_resource_median | 4 | 431 |
| edge_resource_max | 9 | 1000 |
| budget_min | 3 | 140 |
| budget_median | 14 | 1391 |
| budget_max | 30 | 3134 |
| resource_penalty_p95_median | 900 | 10771528 |
| energy_span_min | 3598 | 34269838 |
| energy_span_median | 39863 | 4.6575239e+08 |
| energy_span_max | 178493 | 1.8240518e+09 |
| resource_penalty_to_cost_ratio_median | 329.7561 | 4024235.9 |
| flow_penalty_to_cost_ratio_median | 18.75 | 19.615385 |

The 1–1000 redesign leaves feasible-set semantics intact but materially enlarges the
raw squared-resource component and phase scale. Tighter budgets within a fixed graph
also increase raw excess, so numerical scale moves with dilution under the current form.

## Cost-phase scale

Pilot initial gammas are sampled from uniform [0, 2*pi]; observed frozen initial values span 1.43611 to 4.67661 with median 3.22955. none (COBYLA; phases are periodic).
Current median-gamma raw phase spans range from 1.10676e+08 to 5.89087e+09 radians.
Controlled median-gamma phase spans range from 1584.12 to 2403.34 radians.
These are numerical phase spans only; no barren-plateau or ruggedness theorem is claimed.

## Prospective scale-controlled contract

```text
P_resource = 1[excess>0] + min((excess / sum_edge_resources)^2, 1)
P_flow     = 1[flow_raw>0] + min(flow_raw / max_x(flow_raw), 1)
E_control  = routing_cost + 172 P_flow + 172 P_resource
```

The scales are shared by all stress levels of the same base graph. Both controlled
components are zero exactly for their original valid class and lie in `(1,2]` for any
violation. The global coefficient 172 is one above the declared generator-wide routing
cost bound `19 edges × cost 9 = 171`; it was not chosen from QAOA outcomes.

## Within-base-graph scale isolation

| base_instance_id | size_stratum | n_levels | current_energy_span_max_over_min | controlled_energy_span_max_over_min | spearman_dilution_current_span | spearman_dilution_controlled_span |
|---|---|---|---|---|---|---|
| v2-S1-b000-g-548c8c6335dd2a2e | S1 | 3 | 1.46493 | 1.0271 | 1 | 1 |
| v2-S1-b001-g-553bb3c5ba0f2136 | S1 | 3 | 3.19076 | 1.10784 | 1 | 1 |
| v2-S1-b002-g-a529fbde22ed09f4 | S1 | 3 | 4.0375 | 1.13775 | 1 | 1 |
| v2-S1-b003-g-c45ecbe0242c6377 | S1 | 3 | 3.21891 | 1.05672 | 1 | 1 |
| v2-S1-b004-g-e23fad4558949e26 | S1 | 3 | 3.11148 | 1.03936 | 1 | 1 |
| v2-S2-b000-g-60667963f6db3f1b | S2 | 4 | 1.96018 | 1.04365 | 1 | 0.4 |
| v2-S2-b001-g-6aa6775bed3bc2cc | S2 | 4 | 2.68751 | 1.07942 | 1 | 1 |
| v2-S2-b002-g-0780828b282bb310 | S2 | 4 | 1.67907 | 1.04102 | 1 | 1 |
| v2-S2-b003-g-686fdbb6f8f550f1 | S2 | 4 | 3.60912 | 1.15163 | 1 | 1 |
| v2-S2-b004-g-8c950d2bd101a5de | S2 | 4 | 2.24003 | 1.08736 | 1 | 1 |
| v2-S3-b000-g-8a16a856f5377a40 | S3 | 7 | 1.66329 | 1.06619 | 1 | 1 |
| v2-S3-b001-g-a712031e7959d564 | S3 | 7 | 1.69555 | 1.07273 | 1 | 1 |
| v2-S3-b002-g-fc8e50acd167f0aa | S3 | 7 | 1.71904 | 1.09076 | 1 | 1 |
| v2-S3-b003-g-f0c91af33253395a | S3 | 7 | 2.17453 | 1.12751 | 1 | 1 |
| v2-S3-b004-g-64377640089a831f | S3 | 7 | 1.21503 | 1.03129 | 1 | 1 |
| v2-S4-b000-g-3ff7063ef9ea5cfb | S4 | 7 | 1.6811 | 1.06435 | 1 | 0.892857 |
| v2-S4-b001-g-bd62d2d752385cc7 | S4 | 7 | 1.59197 | 1.06805 | 1 | 1 |
| v2-S4-b002-g-28cd30a80498cca2 | S4 | 7 | 1.57092 | 1.04751 | 1 | 0.964286 |
| v2-S4-b003-g-f6afb3a3727100d3 | S4 | 7 | 1.86854 | 1.09558 | 1 | 1 |
| v2-S4-b004-g-2fa0de1665fa7816 | S4 | 7 | 1.65078 | 1.06305 | 1 | 0.678571 |
| v2-S5-b000-g-a87f1b9ac089cc45 | S5 | 7 | 1.79781 | 1.09555 | 1 | 1 |
| v2-S5-b001-g-e0c69f84d376b633 | S5 | 7 | 1.57402 | 1.07495 | 1 | 0.964286 |
| v2-S5-b002-g-4a80ed839b63ddd7 | S5 | 7 | 1.61491 | 1.0774 | 1 | 0.964286 |
| v2-S5-b003-g-b9a8415aa1799cc5 | S5 | 7 | 1.72526 | 1.09452 | 1 | 0.964286 |
| v2-S5-b004-g-ad76642cd3b9f76c | S5 | 7 | 1.86175 | 1.08894 | 1 | 1 |

## Recommendation and execution status

Freeze `penalty_contract_v2_scale_controlled` for the future Phase 1 pilot.
The current medium contract remains historical and is not overwritten.

**Phase 1 executed: false.**

## Figures

- `results/phase0_v2_dilution_stress/hamiltonian_scale_figures/figure1_dilution_vs_current_energy_span.png`
- `results/phase0_v2_dilution_stress/hamiltonian_scale_figures/figure2_dilution_vs_resource_cost_ratio.png`
- `results/phase0_v2_dilution_stress/hamiltonian_scale_figures/figure3_v1_vs_v2_scale_distributions.png`
- `results/phase0_v2_dilution_stress/hamiltonian_scale_figures/figure4_current_vs_controlled_span.png`
- `results/phase0_v2_dilution_stress/hamiltonian_scale_figures/figure5_within_base_scale_variation.png`
