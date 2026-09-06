# Targeted related-work and novelty audit

Audit date: 2026-08-31

This audit supports positioning for the existing controlled RCSP study. It is
not an independent prior-art opinion and does not certify novelty. Searches
covered constrained and penalty-based QAOA, feasibility-preserving mixers,
CVaR and feasibility-guided variational objectives, warm starts, optimizer
limitations, feasible sampling, search with advice, multiple-marked search,
and graph-query models. Metadata was checked against publisher or arXiv
records before each bibliography entry was added.

## Verified additions

- `zhou2020qaoa`: Leo Zhou, Sheng-Tao Wang, Soonwon Choi, Hannes Pichler,
  Mikhail D. Lukin (2020), *Quantum Approximate Optimization Algorithm:
  Performance, Mechanism, and Implementation on Near-Term Devices*, Physical
  Review X 10, 021067. [DOI](https://doi.org/10.1103/PhysRevX.10.021067),
  arXiv:1812.01041. Supports depth-progressive parameter initialization and
  the importance of the classical outer loop. Peer reviewed.
- `akshay2021reachability`: V. Akshay, H. Philathong, I. Zacharov, J.
  Biamonte (2021), *Reachability Deficits in Quantum Approximate Optimization
  of Graph Problems*, Quantum 5, 532.
  [DOI](https://doi.org/10.22331/q-2021-08-30-532), arXiv:2007.09148.
  Supports the distinction between ansatz reachability and optimizer failure.
  Peer reviewed.
- `fuchs2022mixers`: Franz Georg Fuchs, Kjetil Olsen Lye, Halvor Møll
  Nilsen, Alexander Johannes Stasik, Giorgio Sartor (2022), *Constraint
  Preserving Mixers for the Quantum Approximate Optimization Algorithm*,
  Algorithms 15(6), 202. [DOI](https://doi.org/10.3390/a15060202). Supports
  feasible-subspace mixer construction and its gate/Trotterization costs.
  Peer reviewed.
- `ruan2023constraints`: Yue Ruan, Zhiqiang Yuan, Xiling Xue, Zhihao Liu
  (2023), *Quantum approximate optimization for combinatorial problems with
  constraints*, Information Sciences 619, 98–125.
  [DOI](https://doi.org/10.1016/j.ins.2022.11.020), arXiv:2002.00943.
  Supports general equality, inequality, and oracle-validated constraint
  encodings. Peer reviewed.
- `herman2023zeno`: Dylan Herman et al. (2023), *Constrained optimization
  via quantum Zeno dynamics*, Communications Physics 6, 219.
  [DOI](https://doi.org/10.1038/s42005-023-01331-9), arXiv:2209.15024.
  Supports repeated constraint measurements as a distinct dynamics/resource
  model. Peer reviewed.
- `he2023alignment`: Zichang He et al. (2023), *Alignment between initial
  state and mixer improves QAOA performance for constrained optimization*,
  npj Quantum Information 9, 121.
  [DOI](https://doi.org/10.1038/s41534-023-00787-5), arXiv:2305.03857.
  Supports the effect of initial-state/mixer alignment at low depth. Peer
  reviewed.
- `anderson2024easier`: Noel T. Anderson, Jay-U Chung, Shelby Kimmel,
  Da-Yeon Koh, Xiaohan Ye (2024), *Improved Quantum Query Complexity on
  Easier Inputs*, Quantum 8, 1309.
  [DOI](https://doi.org/10.22331/q-2024-04-08-1309), arXiv:2303.00217.
  Supports established average-case search-with-structure/advice context.
  Peer reviewed.
- `bucher2025penaltyfree`: David Bucher, Jonas Stein, Sebastian Feld,
  Claudia Linnhoff-Popien (2025), *Penalty-free approach to accelerating
  constrained quantum optimization*, Physical Review A 112, 062605.
  [DOI](https://doi.org/10.1103/fb5m-cl9m), arXiv:2504.08663. Supports
  indicator-function QAOA as a stronger circuit/access intervention than
  changing only a scalar classical loss. Peer reviewed.
- `onah2025limitations`: Chinonso Onah, Kristel Michielsen (2025; v4
  revised 2026), *Fundamental Limitations of QAOA on Constrained Problems and
  a Route to Exponential Enhancement*. [arXiv:2511.17259](https://arxiv.org/abs/2511.17259).
  A close theoretical feasibility study for permutation constraints; it is
  not the RCSP optimizer/loss attribution result here. Preprint.
- `li2026feasibilityloss`: Hui-Min Li, Yuan-Liang Han, Zhi-Xi Wang,
  Shao-Ming Fei (2026), *Variational Quantum Algorithm for Constrained
  Combinatorial Optimization Problems*, Physical Review A 113, 032406.
  [DOI](https://doi.org/10.1103/ykxd-h19w), arXiv:2603.05833. Establishes
  prior feasibility-guided loss design with a validation-oracle pathway.
  Peer reviewed.
- `lei2026routing`: Yuan-Zheng Lei, Yaobang Gong, Xianfeng Terry Yang, Nii
  Attoh-Okine (2026), *Improving Feasibility in Quantum Approximate
  Optimization Algorithm for Vehicle Routing via Constraint-Aware
  Initialization and Hybrid XY-X Mixing*.
  [arXiv:2604.07218](https://arxiv.org/abs/2604.07218). Directly studies
  routing feasibility and finite-shot/noisy regimes while changing the
  initialization and mixer. Preprint.
- `lee2026cvarpenalty`: Xin Wei Lee, Hoong Chuin Lau (2026),
  *CVaR-Assisted Custom Penalty Function for Constrained Optimization*.
  [arXiv:2604.20088](https://arxiv.org/abs/2604.20088). Establishes
  CVaR-assisted constrained optimization and sampled custom penalties as
  prior work. Preprint.
- `gupta2026rostering`: Aruna Gupta, S. R. Hassan (2026),
  *Constraint-Preserving QAOA for Personnel Rostering: Coverage-Preserving
  and Guarded-XY Mixer Constructions*.
  [arXiv:2607.09145v2](https://arxiv.org/abs/2607.09145). A close comparison
  including Penalty-X, structural mixers, expectation, CVaR, feasibility, and
  exact statevectors; it changes the mixer and application rather than using
  a fixed-ansatz held-out attribution design. Preprint.

## Screened close work not added as a manuscript citation

- LaRose, Rieffel, and Venturelli, *Mixer-phaser Ansätze for quantum
  optimization with hard constraints* (2022, DOI
  10.1007/s42484-022-00069-x): relevant to compilation-aware mixers, but the
  manuscript already cites the framework and general mixer sources.
- Carmo et al., *Warm-Starting QAOA with XY Mixers* (arXiv:2504.19934):
  Egger et al. and He et al. provide peer-reviewed support for the manuscript's
  warm-start and alignment claims.
- Bucher et al., *Efficient QAOA Architecture for Solving Multi-Constrained
  Optimization Problems* (arXiv:2506.03115 / QCE 2025): the peer-reviewed
  IF-QAOA article is sufficient for the access-model distinction.
- Singhal, Maheshwari, and Joshi, *COMET* (arXiv:2607.02622), and Kim and
  Filipovska, *Feasibility-Preserving Quantum Search for Constrained
  Transportation Routing* (arXiv:2608.05394): very recent application
  preprints screened for direct Penalty-X/structured-mixer comparisons. They
  should be rechecked immediately before submission because their records may
  still change.

## Positioning conclusion

The literature does not support wording that CVaR, constraint-aware losses,
sparse-feasibility concerns, or feasibility-preserving QAOA are new. The
defensible contribution is the controlled attribution design: the same
Penalty-X Hamiltonian and ansatz separate a nested-depth optimizer
certificate, an exact statevector feasible-capacity control, and classical
loss choice, followed by a preregistered held-out graph analysis and a
resource-censored scaling result that retains the high-size reversal.

## Human review still required

1. Perform forward- and backward-citation review for the exact posterior-
   projector bound, finite classical-advice lemma, and one-shot quantum-advice
   proposition.
2. Decide whether posterior inclusion concentration `Lambda(S)` and its
   fixed-cardinality form are new or repackage conditional guessing
   probability/search-with-advice results.
3. Recheck every 2025–2026 preprint at submission for revisions, publication,
   changed theorem scope, and newly cited overlapping work.
4. Obtain an independent novelty judgment. This Codex audit verifies sources
   and supports positioning; it is not an independent priority opinion.
