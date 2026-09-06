# Statistical audit — task rows versus graph clusters

## Outcome

Existing confirmatory inference is already graph-level and does not require correction. The independent unit in frozen Phase 2 is `base_graph_id`; its exact sign-flip test, graph bootstrap, and Holm-corrected H1/H2 family remain canonical and unchanged.

## O3−O0 feasibility-gain comparison

| Source | Unit | n | Mean effect | 95% bootstrap CI |
|---|---|---:|---:|---:|
| Discovery | task | 56 | 0.292589 | [0.216328, 0.376070] |
| Discovery | graph | 10 | 0.245415 | [0.118343, 0.375723] |
| Held-out | task | 84 | 0.403734 | [0.316458, 0.500162] |
| Held-out | graph | 15 | 0.354715 | [0.216222, 0.508024] |

The held-out graph mean exactly matches the frozen H1 effect (0.354715) within 1e-12. The interval above is a new two-sided robustness interval and does not replace the frozen one-sided bound or p-value.

## Sampling-unit inventory

- Discovery has 56 tasks nested in 10 graphs; its Phase-1 result was exploratory/descriptive.
- Held-out has 84 tasks nested in 15 graphs; the preregistered Phase-2 inference averages within graph before inference.
- Phase 3 has 180 tasks nested in 30 graphs, six tasks per graph; its frozen inference operates on graph-level fitted exponents and grouped resampling.
- New B1, A1, A2, and A3 summaries use task rows descriptively and paired graph aggregation for robustness intervals.

No historical p-value, confidence bound, hypothesis family, or headline effect is modified by this audit.
