# Experiment map

The paper uses the following actual sequence. The listed source drivers retain
historical stage paths, initialization and objective definitions. Full runs are
not part of the default quick start.

| Stage | Definition and driver | Frozen evidence |
| --- | --- | --- |
| Initial benchmark / corrected dilution stress | `scripts/run_phase0.py`, `run_phase05.py`; `configs/phase0_v2_dilution_stress.yaml` | `data/manifests/phase0_v2_dilution_stress.json` and corrected characterization |
| Scale control | `scripts/run_phase06.py`; penalty contract config | `results/phase0_v2_dilution_stress/penalty_contract_comparison.csv` |
| Depth pilot | `scripts/run_phase1_pilot_v1.py` | 560 rows in `results/phase1_pilot_v1/master_seed_level_results.csv` |
| Nested diagnostic / continuation | `scripts/run_phase1_1_diagnostic.py` | Phase-1.1 paired comparisons and seed-level outcomes |
| O0/O1/O2/O3 discovery | `scripts/run_phase1_2_objective_alignment.py` | Phase-1.2 objective and capacity-gap tables |
| Frozen held-out H1/H2 | `scripts/run_phase2_confirmatory_v1.py` | Phase-2 preregistration, initialization and matched results |
| Scaling, interpolation / extrapolation | `scripts/run_phase3_scaling_v1.py` | Phase-3 manifests, model freeze, canonical results and censoring |
| Post-hoc optimizer, alpha, depth/budget, finite-shot, classical context | `src/qroute_dilution/reviewer_robustness/`; `analysis/reviewer_robustness/protocol_v1.json` | Complete compact run/summary tables and five task-selection manifests |
| Membership, adaptive and structure/advice numerical validation | `scripts/validate_global_dilution_bound.py`, `validate_adaptive_dilution_bound.py`, `validate_structure_advice_bound.py`, `validate_explicit_rcsp_query_constructions.py` | `results/theory_validation_v1/`, `v2/`, `v3/` |

Use each driver's `--help` for its real stage arguments. The stage drivers are
retained as the original experimental implementation; some freeze stages require
predecessor commits, complete historical inventories or initialization endpoints
that are not part of this compact checkout. They are not advertised as a fresh
one-command full campaign. The archived initial public commit retains the larger
evidence bundle; author-private historical Git guards are not bypassed or
rewritten. A new full campaign needs a separate, explicitly versioned execution
plan and its own outputs, without relabelling it as the original frozen run.

For a runnable small optimization using the same graph, Hamiltonian and QAOA
pipeline, use:

```bash
python scripts/smoke_test.py
```

It creates a fresh workspace automatically. For larger exploratory runs, the
original generic `scripts/run_phase1.py --config CONFIG.yaml` invokes
`run_phase1_workflow`; run it only in an isolated experiment copy with new output
paths. Configs provide the original seeds and budgets. Changes to optimizer
versions, tolerances, initialization, task order or seed handling can change
trajectories and must not replace canonical outcomes.

O0 is mean energy; O1 is expected flow plus resource penalty; O2 is exact
`1-P_feas`; O3 is the weighted lower energy tail with fractional cutoff mass.
The frozen discovery/held-out CVaR alpha is 0.10. These objectives and all
original scientific modules remain unchanged. Post-hoc studies are distinct
from the confirmatory H1/H2 family and must not be pooled with it.
