# Paper sources and generated copies

The current manuscript source is `overleaf/main.tex`; its supplement is
`overleaf/ESM_1.tex`. This `paper/` directory also retains earlier synthesis
material referenced by provenance tests. It has not replaced the current paper.

Figure v3 is produced by `scripts/reproduce_figures.py`. Add `--paper` to create
and compile an independent LaTeX copy with new image references and matching
captions; the original paper and its numbers stay unchanged. Finite-shot plots
move into the generated supplement while their main-text numerical claims remain.

Requirements for compilation: PyMuPDF (`pip install -e '.[review]'`), a working
pdfLaTeX/BibTeX distribution, and the official Springer Nature template with
`sn-jnl.cls` and `sn-mathphys-num.bst`. The public code archive does not redistribute
these vendor files pending review. Obtain the template from the upstream page
recorded in `paper_assets/springer_nature_latex_2024_12/TEMPLATE_PROVENANCE.md` and
pass `--template-dir /path/to/template`. Pass `--tex-bin /path/to/texlive/bin` if
needed. Standalone figure regeneration requires neither template nor TeX.

Original bibliographies, manuscript sources and supplementary sources are kept;
compiler auxiliaries, logs and repeated submission bundles are excluded. The
existing author-action placeholders are deliberate and still require completion.
