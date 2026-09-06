# Environment and resource scope

The release audit inspected both the active Python and the requested
reference environment. The latter is the release validation target:

| Component | Reference environment | Initial active Python |
|---|---|---|
| Python | 3.11.15 | 3.12.4 |
| NumPy | 2.4.6 | 2.4.6 |
| SciPy | 1.17.1 | 1.18.0 |
| pandas | 3.0.5 | 3.0.3 |
| Matplotlib | 3.11.0 | 3.11.0 |
| PyYAML | 6.0.3 | 6.0.3 |
| pytest | 9.1.1 | 9.1.1 |
| PyTorch | 2.11.0+cu128 | 2.6.0+cu124 |
| CUDA build | 12.8 | 12.4 |

The initial active Python differs from the requested named environment.
`requirements.txt` records the named environment's five scientific/plotting
packages; `requirements-dev.txt` adds pytest. `reproduction/requirements.txt`
retains the earlier reference-output stack as provenance. No full conda export,
local editable-install paths or hundreds of unrelated packages are distributed.

The project metadata permits Python >=3.11; this is a compatibility declaration,
not evidence that every such version was tested. Linux is the tested platform;
legacy experiment modules use the Unix `resource` module. Windows users should
use a Linux environment/WSL; native Windows was not validated.

All scientific modules use NumPy CPU simulation, SciPy optimization and pandas
analysis. PyTorch is optional for the separate small CUDA infrastructure check.
The audited host exposes one NVIDIA A100-PCIE-40GB. No full experiment GPU backend
or speed comparison exists in this source tree.

A complex128 statevector alone uses:

| Edge bits m | Statevector only |
|---|---|
| 12 | 64 KiB |
| 20 | 16 MiB |
| 22 | 64 MiB |
| 26 | 1 GiB |

Multiply storage by additional simultaneous state copies; float64 energies,
Boolean masks, state-characterization arrays and parallel workers add memory.
This table is arithmetic, not a measured whole-process memory budget. Runtime
also grows with layers, objective evaluations, restarts and task count. Existing
resource-preflight CSV/JSON and frozen configs record the actual censoring policy.
Do not reinterpret m=22 administrative censoring as zero feasible probability,
a hardware impossibility, or a universally applicable RAM boundary.

The release audit's clean venv installation downloads pinned packages and uses
`pip install --no-deps -e .` for the project. Editable installation is intentional:
legacy modules derive the repository root from `src/` and need external configs
and results. A standalone wheel without these resources is not a supported
reproduction artifact. TeX compilation additionally requires a LaTeX distribution,
BibTeX, the packages in the paper preamble, and the documented Springer template.
