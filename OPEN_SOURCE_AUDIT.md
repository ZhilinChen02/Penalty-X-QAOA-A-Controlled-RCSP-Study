# Open-source release audit

Audit date: 2026-09-06. **Status: PARTIAL.** Engineering, frozen-result
reconstruction and clean-environment checks passed. Public upload still needs
a confirmed copyright holder, citation authors and rights review. This is a
release candidate, not an assertion of completed journal submission or external
independent reproduction.

## Deliverables

- Shared, independent repository: `dist/open_source/Q-RouteDilution-public/`.
- Public ZIP: `dist/open_source/Q-RouteDilution-public.zip`.
- Public payload: 11,304 files, approximately 95.6 MiB uncompressed. Files are
  real files on the shared NFS filesystem; no symlinks or Git directory exist.
- Exact payload sizes and hashes are recorded in `release_manifest.json`.
- ZIP verification: **PASS**, actual Info-ZIP `unzip -t`, exit code 0 and no
  compressed-data errors. See `ZIP_INTEGRITY_TEST.txt` beside the archive.

Paths here are relative to the author's project. In an extracted public archive,
this document is at the repository root. Private audit evidence stays outside
the public package; it contains local paths and is intentionally not published.

## Repository cleanup

The existing `src/qroute_dilution/` package and manifest-referenced directories
were retained. No algorithm refactor or wholesale move was needed.

1. Rewrote README with actual installation, smoke, test, frozen reconstruction,
   figure generation, hardware and opt-in experiment commands.
2. Added `scripts/smoke_test.py`, `reproduce_core_results.py`,
   `reproduce_figures.py` and `run_tests.sh`. They wrap existing implementations;
   new output directories protect frozen evidence against replacement.
3. Added `docs/EXPERIMENTS.md`, `docs/RESULT_PROVENANCE.md`, data/result READMEs
   and updated environment, reproduction, paper and release instructions.
4. Kept a minimal five-dependency pinned scientific/plotting environment and
   pytest development file; aligned package support with Python 3.11. Added the
   optional PyMuPDF review extra. No full conda-environment dump was published.
5. Expanded `.gitignore` for editor state, caches, virtual environments, generated
   archives, LaTeX auxiliaries, profiling output and scheduler material.
6. Prepared the requested standard MIT text with year 2026 and an explicit
   copyright-holder placeholder; retained `LICENSE_REVIEW.md`. Updated citation
   metadata without inventing authors, public URLs, arXiv identifiers or DOI.
7. Made the Figure v3 review builder work without a v2 review archive and accept
   an independently supplied Springer template. Included 15 small PDF/SVG/PNG
   derivatives for four main figures and the finite-shot supplement.
8. Extended the traceable snapshot builder to use shared `dist/open_source/`,
   omit private/vendor/generated files, and record every source/public hash.
   Only public copies of two packaging READMEs are adapted to explain omitted
   templates and the new compilation entry point.

The inventory covers tracked and untracked files, source and experiment drivers,
analysis/plot/theory code, tests, configs, data/results, LaTeX, supplementary
material, logs, caches, binaries, large files and duplicates. It uses all twelve
requested source/evidence/private/development/review categories. No notebooks
were present. Local inventories contain 12,223 entries at snapshot construction
(1,670 tracked files present and 10,553 other files present). Four pre-existing
tracked deletions and all pre-existing working-tree edits were preserved.

## Scientific integrity

**Canonical scientific results modified: NO.**

- All 11,189 protected original files across source, results, inputs/configs,
  manuscript, tests and reproduction references remain at their starting hashes.
- No scientific core, benchmark, seed, objective, feasibility/CVaR definition,
  floating-point calculation order or frozen inference was changed in this
  cleanup. No reference results or golden hashes were regenerated.
- No formal optimization campaign was rerun. Only the existing bounded smoke
  configuration ran tiny optimizations, in a new temporary directory.
- All completed formal evidence, failures, negative results and resource-censored
  rows are retained. Excluded smoke outputs are development checks, not failed
  formal experiments. No result was selected or removed to improve a claim.
- Public privacy redactions affect ten files: seven JSON hostname strings and
  personal paths in three Markdown reports. Parsed comparison found **zero**
  numeric, Boolean, array or missing-value changes, including stored NaNs. The
  original ten files remain unchanged. Public byte hashes honestly differ and
  are recorded alongside original hashes; historical golden files stay intact.
- The two public-only packaging README edits are separately labelled
  `documentation_changes` in the manifest, not scientific or privacy edits.

### Headline reconstruction

The frozen pipeline passes 21 claim checks and seven exact reconstruction hashes.
It reconstructs the corrected 140-task benchmark, 168 optimizer comparisons,
discovery O2–O0 gap and CVaR closure, 84 held-out tasks on 15 independent graphs,
H1/H2 effects, bootstrap lower bounds, Holm correction and secondary task counts.
The 180-task Phase-3 design, m=20 reversal and m=22 resource censoring also pass.
The m=22 census contains 180 planned run rows with no scientific outcomes; these
are not confused with the Phase-3 task count. Membership, adaptive and
structure/advice theory numerical checks pass with zero reported violations.
See `docs/RESULT_PROVENANCE.md` for actual file/script/figure mappings.

### Existing discrepancy retained and disclosed

In `src/qroute_dilution/reviewer_robustness/finite_shot.py`, the historical
`aggregate_finite_shot_training` caller passes a runs-only frame with two shot
regimes to `_plot_training`. The existing terminal-distribution PDF contains
three groups, matching `finite_shot_training_summary_task.csv` under
`results/reviewer_robustness/A3_finite_shot/`: 20 task–objective summaries per
regime, including exact training. Calling the current historical helper through
that aggregate path does not reconstruct the same boxes.

The existing PDF was checked against that frozen task-summary table (maximum
quantile discrepancy from PDF vector-coordinate extraction below 1.7e-7).
Figure v3 reads this table explicitly. Neither the historical helper nor any
result was changed to conceal the provenance issue. The new figure entry point
reproduces the documented frozen-table interpretation; the old aggregate caller
is not advertised as an interchangeable replot command. This does not fail the
headline numerical checks and does not alter the confirmatory conclusions.

## Tests

Validation used both the original environment and a fresh Python 3.11 virtual
environment with a separate byte-copy of the public checkout. The clean copy
had the pinned dependencies and editable package installed from scratch. The
original scientific environment was not modified.

| Check | Actual outcome |
| --- | --- |
| Original full `pytest -q` | 181 passed / 183 collected; 2 skipped; 0 failed |
| Clean CPU public `pytest -q` | 172 passed / 183 collected; 11 skipped; 0 failed |
| CUDA infrastructure test in original suite | 1 passed; tiny complex128 cost layer versus NumPy, no optimizer |
| Package imports | 59 discoverable submodules imported successfully |
| `python scripts/smoke_test.py` | 12 tasks, 36 rows, 0 failures; separate output directory |
| `python scripts/reproduce_core_results.py` | PASS; 21 claims, seven exact hashes, H1/H2/scaling/theory |
| `python scripts/reproduce_figures.py --paper ...` | PASS; four main figures and one supplementary figure from frozen data |
| Historical `validate_release.py --from-existing-results --assets` | PASS; rebuilt assets only in disposable workspace |
| Optional full paper compile with supplied official template | PASS; main 17 pages, supplement 33 pages; zero unresolved references/citations and zero overfull warnings |
| Citation YAML parsing | PASS; author/identifier completeness still pending |
| Final public manifest/scientific reference checks after documentation edits | 4 passed, 0 skipped, 0 failed |

The original suite skips two public-manifest-only checks. The clean public suite
skips ten tests requiring historical private Git/worktrees/unredacted inventories
and one optional CUDA test because PyTorch is not installed. Scientific invariant
expectations and golden data are unchanged. Public manifest and retained-source
hash tests run in the clean suite. The exact skips are explained in README and
`docs/RELEASE_GUIDE.md`; they are not hidden test failures.

The scientific simulator is NumPy on CPU. A passed optional CUDA infrastructure
test establishes neither GPU acceleration of the scientific pipeline nor GPU
performance claims. Full experiment runtime was not benchmarked by this audit.

## Sensitive information audit

The complete working tree, including untracked private SQLite/editor material,
was inspected without publishing matching values. Git history review covered
13 reachable commits, 1,661 blobs, commit metadata and the staged-only `KEY.txt`
blob. No actual credential token, private key or credential assignment was found.
`KEY.txt` is an existing staged private note with machine/identity information,
not a verified credential; it is excluded and left intact in the original.

History contains 82 local-path/identity/internal-host matches and one distinct
author/committer email in metadata. No historical blob exceeds 20 MiB. The
candidate contains no Git history; publishing a fresh snapshot avoids exposing
those historical machine details. No history rewrite was attempted.

Public scanning covers raw file bytes, Python syntax, manifest completeness,
local LaTeX inputs, absolute personal/HPC paths, internal hosts, private URLs,
token/private-key patterns and email locations. Additional extracted-text and
metadata scanning covers all 37 included PDFs. All public scans passed with
zero findings, zero missing manifest files, zero missing local paper inputs,
zero syntax errors and zero symlinks. External Springer class/style dependencies
are documented and intentionally supplied separately. Pattern scans are bounded
checks, not a proof that arbitrary encoded secrets cannot exist.

## Excluded material and large files

The manifest gives each of 935 excluded file entries a reason. They include
editor/cache state, local SQLite conversations and queues, private notes,
historical worktree/HPC provenance, logs, scheduler/compiler output, development
smoke receipts, duplicate generated archives and submission variants. Third-party
Springer class/style files are excluded pending redistribution review. Their
provenance record remains with an explicit public-package note.

**No original file was deleted.** Unique research evidence is not discarded.
There are no original or public individual files above 20, 50 or 100 MiB at the
audited inventory stage. The newly generated public ZIP is a distribution
artifact under ignored `dist/`, not a file to add to source Git. The public tree
contains 25 duplicate-content groups, deliberately retained where historical
references and manuscript builds use different paths. Ordinary Git is sufficient
for current compact evidence. A Zenodo release archive is useful for the full
bundle; current evidence requires neither Git LFS nor an undisclosed statevector
archive. See `data/README.md` and `results/README.md`.

## Reproducibility boundaries

Frozen claim reconstruction, figures, historical tables, smoke tests and CPU
invariants work in the clean checkout. The conda file mirrors the tested pip
stack, but a separate conda solve was not run. Full paper compilation requires
the optional review package, pdfLaTeX/BibTeX and the supplied upstream template.

Full optimization, scaling and finite-shot campaigns remain opt-in and were
not rerun. The historical drivers preserve their fixed stage paths, freeze
prerequisites, seeds and resume behavior. Run them in an isolated experiment
copy following `docs/EXPERIMENTS.md`, never over the canonical release results.
The full prospective freeze/optimization sequence has not been newly validated
as an end-to-end fresh campaign. Exact-statevector memory/time grows with edge
count, depth, evaluation count and parallel workers; HPC is not required for
smoke, tests or replotting. Stored m=22 censoring is a protocol budget boundary,
not a universal simulator memory ceiling.

## Git status and remaining manual actions

The original Git index is byte-identical to its starting state. No files were
staged or committed, no remote was changed and no push occurred. There is no
configured remote. The public repository/ZIP has no `.git` content.
An isolated temporary Git metadata directory was used to inspect the proposed
file set without staging: all 11,304 public files are eligible, with no ignored
payload accidentally omitted. README local links and named entry points exist.

Before uploading:

1. Confirm the copyright holder in `LICENSE`; the requested MIT license text is
   prepared with 2026, but draft paper authors do not establish ownership.
2. Confirm final authors/order and complete `CITATION.cff`. Add the actual public
   repository URL, DOI or arXiv identifier only when known; none was invented.
3. Confirm the rights scope for original code, synthetic benchmark data,
   manuscript and figure assets. Third-party templates are not bundled. Review
   `LICENSE_REVIEW.md`; do not silently extend the code license to others' work.
4. Create the intended GitHub repository and, if desired, a Zenodo archive with
   confirmed creators and related identifiers. Choose the definitive manuscript
   metadata/submission variant separately from this scientific code cleanup.

After metadata edits, refresh the public manifest and rerun its integrity check
before repackaging. Suggested manual commands below are documentation only;
**none was executed**:

```bash
cd dist/open_source/Q-RouteDilution-public
git init -b main
git add .
git status
git commit -m "Prepare public research release"
git remote add origin YOUR_EMPTY_REPOSITORY_URL
git push -u origin main
```

Start from this clean snapshot instead of copying the author's private Git
history. Never use a force push or destructive history rewrite for this release.
