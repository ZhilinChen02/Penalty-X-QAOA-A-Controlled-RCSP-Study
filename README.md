# Penalty-X QAOA: A Controlled RCSP Study

**Feasible-Space Dilution and Objective Alignment in Shallow Penalty-X QAOA: A Controlled RCSP Study**

**Zhilin Chen — University of Copenhagen**

Code, benchmark definitions and frozen results for a controlled exact-statevector
study of shallow, full-space Penalty-X QAOA on resource-constrained shortest paths.

## Overview

Edge-bit encoding makes feasible routes sparse within the full state space.
This study separates feasible-space dilution, Hamiltonian scale, optimizer
inadequacy and objective alignment. It compares mean energy (O0), expected
penalty (O1), exact feasibility as a mechanistic capacity control (O2), and
lower-tail CVaR (O3). CVaR is selected on discovery data and evaluated on a
frozen, preregistered held-out split. Scaling and post-hoc robustness studies
identify boundaries of the observed behavior.

The conclusions apply to this controlled RCSP benchmark and tested protocol.
They establish neither quantum advantage nor failure of all constrained QAOA,
and do not establish a universal scaling law or hardware advantage.

## Main findings

- **Benchmark:** 140 corrected tasks on 25 graphs; discovery 56/10 and held-out
  84/15. Scale control preserves all exact optima.
- **Optimizer diagnosis:** 29/168 certified nested failures. Continuation repairs
  their objective in 29/29 cases and improves feasibility in 27/29.
- **Objective alignment:** CVaR closes a median 97.8783% of the taskwise O2–O0
  gap on discovery tasks under the matched protocol.
- **Held-out inference:** H1 (O3–O0) is +0.3547 decades, with one-sided 95% lower
  bound +0.2374. H2 (O3–O2) is −0.0086, with lower bound −0.0360 above the frozen
  −0.10 noninferiority margin. Both Holm-adjusted p-values are 0.000244140625;
  graphs are the independent analysis units.
- **Scaling:** 180 planned tasks on 30 graphs. At m=20 the earlier O3/O0 exponent
  ordering reverses. All 180 planned m=22 run rows are resource-censored, with
  unavailable scientific outcomes.
- **Finite-shot training:** both post-hoc shot-trained graph-effect intervals
  cross zero; this analysis does not replace or revise the held-out H1/H2 family.

## Installation

Tested on Linux with Python 3.11.15. Install the pinned scientific stack and pytest:

```bash
git clone https://github.com/ZhilinChen02/Penalty-X-QAOA-A-Controlled-RCSP-Study.git
cd Penalty-X-QAOA-A-Controlled-RCSP-Study
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
```

Alternatively, `conda env create -f environment.yml` followed by
`conda activate qroute-release` installs the same minimal stack. Editable
installation is intentional: experiment modules locate configs and results
relative to this checkout. A standalone wheel without these files is insufficient.

## Quick start

```bash
python scripts/smoke_test.py
python scripts/verify_release.py
pytest -q
```

The existing smoke configuration runs 12 small tasks and writes 36 rows to a
new temporary workspace. It exercises graph generation, exact feasibility,
Hamiltonians and small QAOA optimization. No HPC system is needed.

## Reproduce results

```bash
python scripts/reproduce_core_results.py
```

This reconstructs core statistics from compact frozen tables, checks 21 headline
values, graph-level H1/H2 inference, benchmark splits, stored scaling exponents,
resource censoring and theory numerical residuals. It also checks file hashes
and figure inputs. It performs no optimization or scaling refit and writes no
canonical results. The retained tables include complete matched comparisons,
negative outcomes and failed/censored statuses.

Full experiments are opt-in and expensive; they must run in a separate experiment
workspace. The stage map, seeds, budgets and historical freeze prerequisites are
in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md). Different optimizer environments may
produce different trajectories; keep reruns separate from the paper's results.

## Reproduce figures

```bash
python scripts/reproduce_figures.py
# Include the finite-shot supplementary figure, in a different new directory:
python scripts/reproduce_figures.py --supplementary --output-dir dist/figures_with_supplement
```

The default output is a new `dist/reproduced_figures/`, containing PDF and PNG.
Existing directories are protected against replacement. Plotting uses frozen
inputs and stored confidence intervals. The final four main figures are in
[figures/main/](figures/main/), with one PDF and one PNG per figure.

## Repository structure

| Directory | Contents |
| --- | --- |
| `src/qroute_dilution/` | Benchmark, Hamiltonians, exact simulation, objectives, optimizers, statistics and theory |
| `configs/`, `data/manifests/` | Seeds, graph/task definitions, resource budgets and discovery/held-out splits |
| `results/` | Compact canonical tables in their original phase paths; `manifest.json` records hashes and provenance |
| `results/headline_results.csv` | Frozen headline values and paper display values |
| `scripts/` | Verification, smoke, plotting, task materialization and original experiment drivers |
| `figures/main/`, `figures/supplementary/` | Final main figures and finite-shot supplement |
| `tests/` | Public-data scientific invariants and integrity checks; optional CUDA infrastructure check |
| `docs/` | Reproduction, experiment map, result provenance and scoped theory statements |
| `analysis/`, `protocols/` | Frozen post-hoc protocol and preregistration |

Original phase paths are retained to preserve imports and manifest references.
[RESULT_PROVENANCE.md](docs/RESULT_PROVENANCE.md) maps each claim to its data and
analysis. Redundant manuscript packages, optimizer traces and internal reviews
are not part of the current source tree.

## Computational requirements

The scientific simulator uses NumPy on **CPU**. Smoke, verification, tests and
replotting need neither CUDA nor HPC. PyTorch is optional for a small CUDA
infrastructure test; it is not a scientific simulation backend.

A complex128 statevector alone uses `16 * 2**m` bytes: 16 MiB at m=20 and 64 MiB
at m=22. Energy arrays, masks, additional states and parallel workers add memory.
Runtime also grows with depth, evaluations, seeds and tasks. These are storage
identities, not measured whole-process resource limits. The reported m=22
censoring reflects the frozen protocol's computational budget.

## Citation

Use [CITATION.cff](CITATION.cff) for machine-readable author, title and repository
metadata. DOI and arXiv identifiers will be added when assigned.

```bibtex
@misc{chen2026penaltyx,
  author = {Chen, Zhilin},
  title = {Feasible-Space Dilution and Objective Alignment in Shallow Penalty-X QAOA: A Controlled RCSP Study},
  year = {2026},
  howpublished = {Companion research code},
  url = {https://github.com/ZhilinChen02/Penalty-X-QAOA-A-Controlled-RCSP-Study}
}
```

## License

Original project code is released under the [MIT License](LICENSE), copyright
2026 Zhilin Chen. Third-party font components retain their own license; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No third-party LaTeX templates,
external datasets or downloaded papers are bundled.
