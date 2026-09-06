# Release scope and remaining review

The release tree is independent of the author's Git worktree. No original file
was deleted, no Git history or index was rewritten, no remote was modified and
no upload occurred. Existing uncommitted manuscript/scientific changes belong
to the author and were preserved at their starting bytes.

`release_manifest.json` in a public snapshot lists public/source hashes, metadata
sanitization labels and exclusions. Original frozen reference hashes under
`reproduction/`, `tests/fixtures/` and historical result roots are not regenerated.
Metadata-only redactions can therefore make a whole historical tree hash differ;
this is disclosed, not repaired by changing a golden result. Canonical numerical
CSV rows, seeds, configs and theory statements remain unchanged.

Tests which depend on private historical worktrees/commits or complete unredacted
provenance are explicitly skipped in the public snapshot. This covers historical
Git ancestry, private-worktree status and predecessor byte inventories containing
redacted host/path metadata. The scientific invariant tests still run. The added
public-manifest test verifies every included public file, while headline hashes
and scientific reconstruction independently check all reported numbers.

The optional CUDA test checks one tiny complex128 cost layer against NumPy. It
uses no optimizer, changes no scientific module and establishes no experimental
GPU backend. CPU-only installation can skip it without losing scientific checks.

## Paper compilation

`overleaf/main.tex` and `overleaf/ESM_1.tex` use the Springer `sn-jnl` class and
`sn-mathphys-num.bst`. The original `overleaf/` directory lacked these files; the
public snapshot omits the vendor files pending redistribution review. Supply the
official template through `--template-dir` (see `paper/README.md`). With the full
LaTeX requirements installed, build in a disposable copy of `overleaf/`:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error ESM_1.tex
pdflatex -interaction=nonstopmode -halt-on-error ESM_1.tex
pdflatex -interaction=nonstopmode -halt-on-error ESM_1.tex
```

This preserves the author-action warnings and all scientific text. It does not
establish journal submission readiness. The definitive submission variant,
author/affiliation/contact metadata, proof review and declaration fields need
human confirmation. Consult the final audit for the actual compilation outcome.

## Storage policy

Keep source, configs, manifests, canonical compact CSV/JSON, reference hashes and
necessary figures under ordinary Git tracking. The audit found no file reaching
100 MB. Thousands of small run receipts are useful audit evidence; they are
retained. A Zenodo release archive is useful for the complete frozen bundle.
Git LFS is optional for future bulky binaries; it is not required for current
canonical rows. Do not upload local SQLite conversations, credential-labelled
files, HPC provenance dumps, editor state, logs, caches or generated archives.
The original project's detailed inventory/large-file report is local audit
material and must not be uploaded unreviewed.

## Manual decisions before upload

- Confirm the copyright holder for the requested MIT code license; separately
  confirm data and manuscript/figure rights and any copied snippets/font rights.
  Third-party template code is not included in the public package.
- Confirm the final author list/order and citation metadata. The draft contains
  an attested name, but this does not settle release authorship.
- Select the final paper/submission variant and resolve its visible author-action
  fields. No scientific prose should be changed during this metadata review.
- Select repository name, version/date, Zenodo creators, description, keywords,
  related paper identifiers and archival DOI only after they actually exist.
- An independent person still needs to reproduce/review the evidence and proof
  assumptions; the automated release audit is not that external review.

Suggested GitHub upload commands appear only in `OPEN_SOURCE_AUDIT.md`.
They were not executed. Do not publish the private worktree or its Git history.
