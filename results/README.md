# Frozen scientific evidence

The existing stage directories are retained because manifests and scientific
regressions refer to their paths. `phase0_v2_dilution_stress/` is the corrected
140-task benchmark. Phase 1 is discovery/diagnostic evidence; Phase 2 is the
84-task held-out study; Phase 3 records completed and resource-censored cells.
`theory_validation_v1/` through `v3/` hold numerical theory checks.
`reviewer_robustness/` and `posthoc_finite_shot_endpoint_v1/` are separate post-hoc
analyses. Earlier Phase-0/synthesis material remains historical evidence.

Failures, negative effects, all formal run receipts and all m=22 censoring rows
are retained. Development smoke outputs, machine package dumps, private worktree
records and obsolete compiled revision archives are excluded only by documented
release rules, never by scientific outcome. The public manifest records every
included file and all exclusions. Only hostname/path strings in public metadata
are redacted; numeric values and the original-tree results are unchanged.

Use `python scripts/reproduce_core_results.py` to reconstruct reported claims,
and `python scripts/reproduce_figures.py` to replot. Both preserve these files.
See `docs/RESULT_PROVENANCE.md` and `docs/REPRODUCIBILITY.md` at repository root.
