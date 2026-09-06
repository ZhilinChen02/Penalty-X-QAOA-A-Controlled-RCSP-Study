# Reviewer-robustness resume instructions

All required reviewer-robustness phases are complete. Formal scientific choices are defined only by the frozen manifests in `results/reviewer_robustness/manifests/`; do not edit them. Complete run JSON records are independently validated and skipped by every execution command.

## Final state (2026-09-04)

- R0, B1, A1, A2, A3 fixed-endpoint audit, A3 finite-shot training, alpha x shots estimation, B2, and statistical synthesis are complete.
- The registry contains 9,412/9,412 `COMPLETE` formal records, zero failed and zero timed-out formal runs.
- The pre-existing fixed-endpoint finite-shot study was audited and reused without rerunning it.
- The final suite reports 177 passed, zero failed, zero skipped.
- B3 is intentionally `NOT_TESTED`; it is not a remaining required run.
- The one failed alpha x shots wiring event occurred during smoke testing, created no formal record, and is preserved at `results/reviewer_robustness/smoke/A3_finite_shot/smoke_failure_20260904T063245.json`. Amendment 003 documents the tested correction.

## Read-only verification and regeneration

Run from the repository root:

```bash
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py integrity
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py registry
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py synthesis
pytest -q
```

The first two commands verify canonical protection and rebuild the registry from per-run JSON files. `synthesis` only rebuilds derived contrasts, summaries, and revision notes; it does not optimize or sample.

## Optional re-aggregation from existing run records

These commands are also read-only with respect to run records and canonical science:

```bash
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py b1-aggregate
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py a1-aggregate
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py a2-aggregate
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py a3-training-aggregate
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py a3-estimator-aggregate
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py b2-aggregate
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py statistical-audit
python paper_scripts/reviewer_robustness/run_reviewer_robustness.py synthesis
```

## Safety and future execution

Never reset, restore, clean, or replace the pre-existing dirty working tree. Do not delete partial reviewer output. If reviewer execution code changes before any future formal extension, run relevant tests and append a machine-readable `code-amendment` first. B3 requires a separately frozen manifest and should be started only in response to a specific external-validity need; it is not authorized as an implicit continuation of this completed pass.
