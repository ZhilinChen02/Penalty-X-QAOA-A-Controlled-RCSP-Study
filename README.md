# Q-RouteDilution

Reproducible code for a controlled exact-statevector study of feasible-space
dilution, optimizer failure and objective alignment in full-space,
penalty-based, non-feasibility-preserving QAOA for resource-constrained shortest
paths (RCSP).

Start with the frozen-result commands below. They reconstruct the reported
results without rerunning the experimental optimizations. The public candidate
still needs a confirmed copyright holder and final citation metadata; see
[LICENSE_REVIEW.md](LICENSE_REVIEW.md).

## Overview

The layered RCSP benchmark uses edge-bit states and a Penalty-X QAOA ansatz.
Feasible routes occupy a small fraction of the full state space. A global scale
contract removes a Hamiltonian energy-span confound while preserving exact
optima. Nested depth embeddings diagnose optimizer inadequacy; matched objective
comparisons distinguish mean-energy improvement from feasible-mass improvement.
CVaR is selected on discovery data and evaluated on a frozen held-out split.
The conclusions concern this tested protocol and its information-access models.
They establish neither quantum advantage nor a failure of all constrained QAOA.

Frozen findings include:

- Corrected benchmark: 140 tasks / 25 graphs; discovery 56 / 10; held-out 84 / 15.
- Nested diagnostic: 29/168 certified optimizer failures; continuation improves
  their objective in 29/29 and feasibility in 27/29.
- Discovery: O2 exposes capacity not induced by O0; CVaR-0.10 closes a median
  97.8783% of the taskwise O2–O0 gap under the stated matched design.
- Held-out H1: +0.3547 decades, one-sided lower bound +0.2374. H2: −0.0086,
  lower bound −0.0360 above the −0.10 noninferiority margin. Both Holm-adjusted
  p-values are 0.000244140625. Graphs are the independent analysis units.
- Phase 3: 180 planned tasks / 30 graphs. At m=20 the earlier O3/O0 exponent
  ordering reverses; 180 planned m=22 run rows are resource-censored, with no
  scientific outcomes. No global extrapolative scaling law is inferred.
- Post-hoc finite-shot training is less decisive than fixed-endpoint sampling:
  both shot-trained graph-effect intervals cross zero. It does not revise H1/H2.

## Installation

Tested baseline: Linux, Python **3.11.15**. Install the five pinned scientific and
plotting dependencies plus pytest, then install the project in editable mode:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
```

Conda alternative:

```bash
conda env create -f environment.yml
conda activate qroute-release
```

The pip route is checked in a clean environment. The conda file expresses the
same minimal stack; it is not a full export of an author's environment.
Editable installation is intentional: legacy workflows locate configs and
frozen results beside the source. A standalone wheel alone is insufficient.

## Quick start

```bash
python scripts/smoke_test.py
pytest -q
python scripts/reproduce_core_results.py
python scripts/reproduce_figures.py
```

The smoke test exercises graph generation, exact feasibility, Hamiltonians and
small QAOA optimization on the existing 12-task smoke configuration. It writes
only to a new temporary workspace and does not run a full experiment. The other
two reproduction commands read frozen evidence. Figure outputs are PDF/SVG/PNG
under a new `dist/reproduced_figures/` directory; choose `--output-dir` for later
runs, since existing outputs are protected against accidental replacement.

## Repository structure

| Path | Contents |
| --- | --- |
| `src/qroute_dilution/` | RCSP, exact statevectors, objectives, optimization, statistics and theory |
| `scripts/` | Safe smoke/reconstruction/replot entry points and original phase drivers |
| `configs/`, `protocols/`, `data/manifests/` | Benchmark definitions, seeds, budgets, splits and preregistration |
| `results/` | Frozen canonical rows, failures, censoring, summaries and necessary historical evidence |
| `reproduction/` | Deterministic reconstruction and unchanged reference hashes |
| `paper_scripts/` | Figure v3, historical asset builders and manuscript support |
| `figures/main_v3/` | Small pre-rendered main figures and finite-shot supplement in the public package |
| `overleaf/` | Manuscript and supplementary LaTeX sources; v3 is integrated into a generated copy |
| `paper/`, `manuscript/`, `review_package/` | Historical synthesis sources needed for provenance and regressions |
| `tests/`, `docs/` | Scientific invariants, experiment map and result provenance |

Directories referenced by frozen manifests were retained. Renaming the Python
package or moving canonical results would break existing evidence references.
See [RESULT_PROVENANCE.md](docs/RESULT_PROVENANCE.md) for result → data → analysis
→ figure mappings and [data/README.md](data/README.md) for input policy.

## Reproducing paper results

### Replot frozen results

```bash
python scripts/reproduce_figures.py --output-dir dist/my_figures
python scripts/reproduce_core_results.py
# Historical tables and asset set, rebuilt only in a disposable copy:
python scripts/validate_release.py --from-existing-results --assets
```

Figure v3 uses stored numerical results, including stored confidence intervals;
it does not refit statistics or run optimization. The core reconstruction checks
21 claims, exact reference hashes, held-out graph inference, scaling/censoring and
theory numerical validation. It writes its reconstructed files outside the frozen
tree. PDF bytes can vary across font/renderer versions even when the data agree.

For a compiled v3 paper copy, install the optional review dependency and supply
the official Springer template yourself; vendor files are omitted pending their
redistribution review:

```bash
python -m pip install -e '.[review]'
python scripts/reproduce_figures.py --paper --output-dir dist/paper_review --template-dir /path/to/springer-template
```

`pdflatex` and `bibtex` must be on PATH, or pass `--tex-bin /path/to/texlive/bin`.
A v2 comparison is optional; v3 paper generation works without author-local
`dist/figures_v2/`. See [paper/README.md](paper/README.md).

### Re-run experiments

Full optimization is opt-in. The original phase drivers retain fixed stage
outputs, resume behavior, freeze prerequisites and historical seed handling.
Use an isolated experiment copy and the ordered commands in
[EXPERIMENTS.md](docs/EXPERIMENTS.md) and
[REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md); do not launch them in the frozen
release checkout. Different optimizer/dependency environments may produce
numerically different trajectories. New results must remain distinct from the
paper's canonical evidence. A fresh full optimization campaign was not run for
this cleanup.

## Tests

```bash
pytest -q
# Equivalent convenience entry point:
sh scripts/run_tests.sh
```

Scientific checks cover RCSP ground truth, exact membership, Hamiltonians, scale
control, nested embedding, O0/O1/O2/O3, CVaR, deterministic seeds, manifests and
headline reconstruction. In a public snapshot, 10 historical provenance tests
explicitly skip because they require private worktrees, old Git commits or
unredacted inventories. Public manifest/hash tests replace their byte-inventory
role without changing any scientific expectations or golden data. The optional
GPU check skips when PyTorch/CUDA is unavailable; skips are reported normally.

## Hardware and computational requirements

Scientific simulation uses **NumPy on CPU**. No GPU or HPC system is required for
smoke tests, ordinary tests or replotting. PyTorch is only an optional tiny CUDA
infrastructure check, not a scientific acceleration backend.

A complex128 statevector alone needs `16 * 2**m` bytes: 16 MiB at m=20 and
64 MiB at m=22. Energy arrays, state copies, masks and concurrent workers add
memory; these are not whole-process RAM estimates. Runtime grows with depth,
evaluations, seeds and tasks. Full optimizer, scaling and finite-shot campaigns
can be expensive. Reported m=22 censoring reflects the frozen computational
budget, not a universal qubit or RAM ceiling. See [ENVIRONMENT.md](docs/ENVIRONMENT.md).

## Citation

[CITATION.cff](CITATION.cff) carries the manuscript title and explicit metadata
TODOs. The final author list, public URL, DOI and arXiv identifier have not been
invented. Fill them only when confirmed or assigned.

## License

The requested MIT text is prepared in [LICENSE](LICENSE), with year 2026.
**The copyright holder remains to be filled in.** The paper's draft author block
is not sufficient to decide ownership. Review [LICENSE_REVIEW.md](LICENSE_REVIEW.md)
for third-party templates, paper/data rights and remaining release actions.
