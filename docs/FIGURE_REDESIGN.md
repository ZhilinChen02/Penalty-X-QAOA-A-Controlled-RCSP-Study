# Main-figure redesign

`paper_scripts/redesign_main_figures.py` redraws the four main-text figures from
frozen CSV/JSON and integrates them into an independent copy of `overleaf/`.
It does not run optimization or modify scientific source, canonical results,
the original paper, or the existing public release candidate.

Run in the documented plotting environment:

```bash
python paper_scripts/redesign_main_figures.py
# Or choose a NEW directory outside this repository:
python paper_scripts/redesign_main_figures.py --output-dir /tmp/qroute-figures-review
```

The command prints its output directory. It produces four PDF/SVG/PNG sets,
`paper/`, a README, and `FIGURE_REDESIGN_AUDIT.json` with input hashes and the
displayed values. SVG text remains editable; PDF fonts are embedded.

| Main figure | Output stem | Presentation changes |
| --- | --- | --- |
| 1 | `fig02_dilution_scale_control` | Restrained colors, all 140 task points, horizontal logarithmic energy-span comparison |
| 2 | `fig03_optimizer_attribution` | Ranked gaps, shared failure-set colors, counts outside plotting area |
| 3 | `fig06_heldout_confirmation` | Consistent graph ranking, separate statistical summaries, explicit one-sided lower bounds |
| 4 | `fig_main04_robustness_boundaries` | One canvas with panels a–e, consistent budget markers and colors, horizontal finite-shot effect intervals |

All main-text captions and numerical prose are preserved. In the copied paper,
the fourth figure's two image inclusion lines become one line. The original
depth/budget and finite-shot images remain available for supplementary material.

## Verification of this rendering

The shared review package is `dist/figures_v2/` in this project. It additionally
contains `index.html` for before/after comparison, `main_figures_v2.pdf` with
four vector pages, and `Q-RouteDilution-paper-figures-v2.zip` containing the
integrated LaTeX copy. These review conveniences are separate from the plotting
command's standard outputs. All review files are real files on the project NFS filesystem; they do not
depend on compute-node `/tmp`. Top-level `fig1_redesign` through
`fig4_redesign` files are also available in PDF, SVG and PNG formats. The
plotting script and frozen inputs reproduce the figures.

- Hash checks passed for all 11 plotting inputs and 59 original paper files.
- The copied TeX differs only in the fourth figure's image inclusion block.
- All four PDFs were inspected visually and contain vector plots.
- H1/H2 retain their stored one-sided bounds and Holm-adjusted p-values.
- Depth and finite-shot panels retain their stored two-sided confidence
  intervals. Both shot-trained effect intervals still cross zero.
- Independent `scripts/validate_release.py --from-existing-results` passed:
  seven reference hashes, headline claims, held-out results, scaling verdicts,
  and theory checks. This validation recomputes statistics from frozen results;
  it does not rerun optimization. Rendering itself reads stored statistics.
- The full manuscript has not been compiled: no TeX engine is available in the
  current environment.

## Existing finite-shot plot provenance issue

The existing finite-shot PDF contains three terminal-distribution boxes,
including `EXACT_CANONICAL`. The current `aggregate_finite_shot_training` caller
passes its runs table to `_plot_training`; that table contains only the two
shot regimes. Calling that entry point therefore does not reproduce the
existing three-box panel.

The existing PDF's three boxes instead match
`finite_shot_training_summary_task.csv`: 20 task–objective summaries per regime.
This was checked by inverting the original vector PDF's axis coordinates and
comparing all three boxes' quartiles, medians and whiskers against the frozen
table. Maximum discrepancy was less than 1.7e-7, attributable to PDF coordinate
precision. The evidence is in `LEGACY_BOX_PROVENANCE_CHECK.json` in the review
package.

The redesign explicitly uses this matching summary table and labels its
aggregation unit. It does not change the scientific module, source tables,
reported sample sizes, or original PDF. Repair of that existing aggregation
caller's behavior is outside this presentation-only change.
