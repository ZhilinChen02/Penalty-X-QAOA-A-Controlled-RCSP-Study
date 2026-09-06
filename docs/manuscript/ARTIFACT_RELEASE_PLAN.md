# Artifact and Reproducibility Plan

No release, push, DOI minting, or archive action is performed in Synthesis v1.

## Frozen canonical roots

The protected result roots from smoke through Phase 3 and Theory-v1--v3, plus
`docs/theory`, `configs`, `data/manifests`, and `protocols`, are immutable. Their
1,403 SHA-256 entries are recorded in
`results/synthesis_v1/protected_hashes_before.sha256` and must verify before any
release candidate is built.

## Release contents

Release:

- frozen manifests, configs, preregistrations and protocols;
- canonical task/result CSVs, summaries, claim matrices, failure censuses and
  theorem validation rows;
- reference implementation and all tests;
- Synthesis-v1 claim/evidence, numeric-source and hash inventories;
- environment metadata and a machine-readable command transcript;
- source data and scripts for every manuscript figure/table.

Large raw statevectors were not canonical evidence and need not be released.
Downloaded papers, caches, temporary optimization files, local virtual
environments, and duplicate historical render products may be excluded if the
hash inventory records the exclusion. Intermediate files used by a canonical
summary should be retained unless regenerability is demonstrated.

## Validation target

Provide one command, proposed as `make validate-release`, that performs:

1. environment/version report;
2. protected hash verification;
3. `pytest -q`, including theorem and empirical integrity tests;
4. claim-ID, bibliography, visual-source and dependency checks;
5. read-only regeneration of Synthesis CSVs in a temporary directory and
   bytewise comparison;
6. LaTeX syntax/compilation check where TeX is available.

The environment should be locked with an exported, human-readable package lock
and platform metadata. The lock is distinct from canonical scientific data.

## Reference code versus scientific data

Code is the reference mechanism used to regenerate or validate results.
Canonical CSV/JSON rows and their hashes are the frozen scientific record.
Re-running an optimizer creates a new evidence stage; it must never silently
replace a canonical row. Read-only arithmetic checks are labeled
`INTEGRITY_RECOMPUTATION`.

## Archive and DOI plan

After external review and manuscript claim freeze:

1. create a clean release worktree from the reviewed commit;
2. verify all hashes and tests;
3. remove only documented noncanonical caches/large intermediates;
4. tag a versioned release;
5. archive source, canonical data and environment metadata through an
   institutional/Zenodo-class repository;
6. record the archive checksum and DOI in the manuscript artifact appendix;
7. preserve the git commit and manifest as independent identities.

## External reproduction checklist

- fresh clone from the archived commit;
- environment creation from the lock;
- protected-hash pass;
- complete test pass;
- manuscript figure/table regeneration from canonical rows;
- independent extraction of every numeric-claim row;
- independent theorem-test execution (not a substitute for proof review);
- explicit report of platform, runtime, memory and deviations.

## Worktree cleanup

Only after publication/release decisions: list every worktree, confirm all
branches/dirty files are preserved, and remove only explicitly authorized clean
temporary worktrees. Never delete or merge the empirical, Theory-v2, Theory-v3,
or Synthesis histories as a cleanup shortcut.
