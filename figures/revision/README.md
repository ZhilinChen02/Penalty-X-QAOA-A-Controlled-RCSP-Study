# Figures of the revised manuscript

These are Figs. 1–3 of the revised manuscript, *Conditional value-at-risk
training improves feasible-solution sampling in shallow penalty-based QAOA for
resource-constrained shortest paths*. They were drawn in draw.io; each figure
is stored as its editable source (`.drawio`), the PDF used in the manuscript
and a PNG rendered from that PDF for the repository README.

| Figure | Content | Made from |
| --- | --- | --- |
| [Fig. 1](Fig1.png) | Training loop of Penalty-X QAOA (RCSP → circuit → samples → loss → optimizer → angles) with the five candidate mechanisms M1–M5 tagged where they act; right: held-out geometric-mean P_feas relative to mean-energy training (O0 = 1, O3 = 10^0.355 ≈ 2.26, O2 = 10^0.363 ≈ 2.31) | Schematic, edited directly in draw.io |
| [Fig. 2](Fig2.png) | Discovery set. **a** Nesting test: energy gap of each three-layer run to its embedded two-layer start (168 runs; 29 certified failures). **b** Continuation of the 29 failed runs (27 gain feasibility). **c** G_feas of each loss minus that of the feasibility control (56 tasks; bars: medians) | `make_drawio_figures.py` from frozen tables |
| [Fig. 3](Fig3.png) | Held-out tests. **a** H1 and **b** H2: graph-level contrasts, their mean and one-sided 95 % interval. **c** CVaR gain on the 84 tasks, by whether the CVaR state reached P_feas ≥ α | `make_drawio_figures.py` from frozen tables |

Colours are shared across the figures: grey for mean-energy training (O0),
coral for CVaR (O3), teal for the feasibility control (O2) and purple for
certified optimizer failures.

## Regenerating

Figs. 2 and 3 are written from the frozen result tables only (no
optimization). From the repository root:

```bash
python figures/revision/make_drawio_figures.py --repo . --out figures/revision
```

The script checks the numbers quoted in the manuscript (for example 29/168
failures, 27/29 continued runs, the median gaps 0.219, 0.242 and 0.0069
decades to the control, and the 20/64 split of the held-out tasks) and writes
[`figure_ledger.json`](figure_ledger.json). Run on this repository, it
reproduces `Fig2.drawio` and `Fig3.drawio` byte for byte.

The PDFs and PNGs are exported with the draw.io desktop command line (version
32.6.10 was used) and Ghostscript:

```bash
DRAWIO=/path/to/drawio bash figures/revision/export_figures.sh
```

On Linux the script renders Helvetica with FreeSans (shipped with TeX Live),
so that the PDFs embed TrueType fonts; see
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md). Without the command
line, open a `.drawio` file in draw.io and use *File → Export as → PDF* with
*Crop* ticked.

The figures of the original submission remain in [`../main/`](../main/) and
[`../supplementary/`](../supplementary/); their hashes are recorded in
`results/manifest.json` and they are replotted by
`scripts/reproduce_figures.py`.
