# Figure v3: manuscript-scale redesign

In the public checkout, small pre-rendered figures are in `figures/main_v3/`.
Run `python scripts/reproduce_figures.py` to regenerate them from frozen rows.
The original author review described below is not bundled as a duplicate archive;
`--paper --template-dir /path/to/template` generates a new compiled review copy.

The shared deliverable is `dist/figures_v3/`. Open `index.html` for the v2/v3
comparison and compiled page previews. The main figures are on manuscript
pages 5, 7, 8 and 9; finite-shot training is now supplementary Fig. S6, page 22.
The full depth summaries are retained in the supplement on page 19.

The figure width is exactly the original Springer class's 31 pica (372 TeX
points, about 13.1 cm), rather than drawing wider and reducing the labels at
inclusion time. The plots use black STIX serif text and coordinated math.
Base ticks, legends and annotations are at least 8 points; mathematical
subscripts follow the font's normal smaller sizing. Figure 4 has two panels.

Main changes:

- Figure 1 adds an actual frozen seven-edge RCSP example. The dilution data
  occupy the largest panel; all 140 observations in the scale audit remain.
- Figure 2 retains all 168 comparisons, emphasizes the 29 certified failures,
  and shows continuation against a clear equality line. Objective-mismatch
  evidence remains in the existing text and supplementary analyses.
- Figure 3 separates the 15 ranked graph effects from the mean and one-sided
  lower bound. Arrows indicate intervals with no finite upper endpoint.
- Figure 4 pairs budget-dependent nested failure with depth-gain estimates.
  The six displayed depth-gain confidence intervals are read from the frozen
  report at its existing four-decimal precision. Graph means are checked
  against the frozen graph table. Finite-shot results move intact to the
  supplement; the main-text numbers and interpretation stay unchanged.

Both PDFs compile with pdfLaTeX and BibTeX from TeX Live 2023: 17 main pages,
33 supplementary pages, no unresolved references/citations or overfull boxes.
The paper copy retains all existing author-action placeholders. Only figure
blocks and the necessary navigation text change in that copy.

## Rebuild

Use the repository's plotting environment plus **PyMuPDF 1.28.2** for PDF
assembly and page previews. PyMuPDF is a review-tool dependency, not a
scientific simulation dependency. `pdflatex` and `bibtex` must be available.
The original environments and source results are not modified by these tools.

```bash
python paper_scripts/redesign_main_figures_v3.py
python paper_scripts/build_figure_v3_review.py
# If TeX is not on PATH, add: --tex-bin /path/to/texlive/bin
```

Rendering reads stored statistics without optimization or resampling. The
separate headline audit recomputes existing-result statistics and verifies
21 claims, seven reference hashes and theory checks. Its outputs are copied
into `dist/figures_v3/headline_validation/`.

The prior v2 entry point is `paper_scripts/redesign_main_figures.py`. Its
historical primary-figure sources are `paper_scripts/build_paper_assets.py`
and the depth/finite-shot plotting helpers in
`src/qroute_dilution/reviewer_robustness/`. They are all preserved. The existing
finite-shot helper/caller provenance issue is documented in
`docs/FIGURE_REDESIGN.md`; v3 uses the same verified task-summary distribution.

All v3 deliverables are real files on the shared project filesystem. The
review ZIP includes the compiled paper, supplement, merged figures, SVG/PNG
outputs, comparisons, audit records and a separate LaTeX ZIP.
