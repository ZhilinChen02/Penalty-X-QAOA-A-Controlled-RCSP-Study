# Final paper report

## A. PAPER STATUS

`COMPLETE`

The complete empirical-primary manuscript, appendices, ten vector figures,
eleven tables, compact provenance supplements, audits, and clean Overleaf ZIP
have been produced. A manuscript PDF is conditional on TeX availability; no
TeX engine is installed in this environment.

## B. TITLE

**Feasible-Space Dilution and Objective Alignment in Shallow QAOA: A
Controlled RCSP Study**

Author: Zhilin Chen. Affiliation remains a neutral confirmation placeholder.

## C. TOTAL WORD COUNT

- Main text (including abstract): approximately **8,997** words.
- Appendices: approximately **3,865** words.
- Total prose estimate: approximately **12,862** words.
- Abstract: **216** words.
- Introduction: approximately **1,319** words.

Counts use a static LaTeX-aware prose tokenizer and exclude displayed
mathematics, bibliography, figure/table bodies, and markup.

## D. OVERLEAF ZIP

- Absolute path:
  `<LOCAL_WORKSPACE>/Q-RouteDilution-paper-v1/dist/Q-RouteDilution_Overleaf_v1.zip`
- Size: **631,781 bytes** (well below 50 MB).
- File count: **47**.
- SHA-256:
  `0bd0151eada820938715be818d14cedce73faaa5496876c8b2f159ab2f5953fa`.

The archive root directly contains `main.tex`, `references.bib`, `README.md`,
`sections/`, `appendices/`, `figures/`, `tables/`, and `supplementary/`.

## E. PDF

`LATEX_COMPILER_NOT_AVAILABLE`

No `latexmk`, `pdflatex`, `xelatex`, `lualatex`, or `bibtex` executable is
installed. No PDF was fabricated. Static checks and a clean ZIP extraction
were completed successfully.

## F. SECTIONS

Completed main matter:

1. Abstract
2. Introduction
3. Problem Setting and Definitions
4. Controlled Experimental Design
5. Optimizer and Objective Attribution
6. Objective-Alignment Study
7. Preregistered Held-Out Confirmation
8. Scaling Response and Resource Ceiling
9. Representation, Search, and Structure
10. Related Work
11. Discussion
12. Limitations
13. Conclusion

Completed appendices:

- A. Mathematical Proofs
- B. Task Construction
- C. Hamiltonian and Optimization Details
- D. Optimizer Attribution
- E. Objective-Alignment Details
- F. Held-Out Preregistration and Statistics
- G. Scaling Analysis
- H. Reproducibility and Artifact Details

## G. FIGURES

1. Controlled experimental attribution pipeline.
2. Dilution coverage and Hamiltonian scale control.
3. Nested-ansatz and continuation optimizer attribution.
4. Mean-energy/feasibility misalignment and energy decomposition.
5. Discovery comparison of O0--O3.
6. Preregistered held-out graph-level H1/H2 contrasts.
7. Feasible-entry/conditional-optimality decomposition.
8. Development, interpolation, $m=20$, and resource-censored $m=22$ response.
9. Raw-density, access-model, and posterior-structure scope.
10. Structure-cost relocation ledger.

All outputs are vector PDFs generated from frozen canonical inputs or, for the
three scope schematics, from frozen protocol/theory descriptions. Their exact
inputs, filters, aggregations, script, and output names are in
`paper_audit/figure_manifest.csv`.

## H. TABLES

Main tables:

1. Experimental task and protocol summary.
2. Objectives O0--O3.
3. Optimizer attribution summary.
4. Held-out confirmatory results.
5. Scaling-response summary.
6. Theory access-model and nonclaim summary.

Supplementary tables cover the failure census, task strata, statistical
contract, proof assumptions, and artifact hashes. Source, aggregation, and
rounding policies are recorded in `paper_audit/table_manifest.csv`.

## I. MAIN EMPIRICAL RESULT

In the preregistered held-out evaluation of 84 tasks from 15 nonoverlapping
base graphs, the graph-level O3-minus-O0 effect in $G_{\mathrm{feas}}$ was
**+0.3547149490180106 decades**, with one-sided 95% lower bound
**+0.23737853648218638** and Holm-adjusted exact sign-flip
$p=\mathbf{0.000244140625}$. The superiority criterion was satisfied.

The graph-level O3-minus-O2 effect was **-0.008595149938274194 decades**, with
one-sided lower bound **-0.03604874990402986**, above the frozen
**-0.10-decade** non-inferiority margin; the Holm-adjusted exact sign-flip
$p=\mathbf{0.000244140625}$. The non-inferiority criterion was satisfied. O2
remains a statevector-only mechanistic capacity control, and the margin is not
a deployment-utility threshold.

## J. MAIN THEORY RESULT

For a uniformly random size-$M$ feasible subset of an $N$-label domain, with
$\phi=M/N$, a membership-only adaptive protocol with arbitrary ancillas,
purified measurement/feed-forward, and a pathwise hard cap of $q$ counted
membership queries satisfies
$\mathbb{E}P_{\mathrm{success}}\leq\min\{1,(2q+1)^2\phi\}$. The result is an
average over the random fixed-cardinality subset prior, not pointwise for every
feasible set; training-generated membership access counts in the total, and
the theorem does not directly lower-bound the rich explicit RCSP energy access
used by the experiments.

## K. SCALING LANGUAGE

`NO GLOBAL SCALING LAW CLAIMED`

The completed $m=20$ response reverses the earlier O0/O3 ordering, and $m=22$
is prospectively resource-censored. The manuscript uses the frozen verdicts
`RESOURCE_CENSORED_SCALING` and `MIXED_OBJECTIVE_SCALING`.

## L. NUMERIC AUDIT

- Supported exact uses: **111**.
- Supported rounded uses: **67**.
- Mismatches: **0**.
- Unsupported numerical statements: **0**.

## M. CLAIM AUDIT

- Unique included frozen claim IDs: **25**.
- Included claim-use rows: **57** (11 unqualified supported; 38 supported with
  scope limits; 4 descriptive only; 4 resource-censored).
- Explicit prohibited/rejected claim rows: **6**.
- Unsupported claim-use rows: **0**.

## N. CITATIONS

- Cited primary-source keys verified: **21**.
- Broken or unresolved citation keys: **0**.
- Duplicate bibliography keys: **0**.
- Exact theorem-priority positioning still requires independent human
  forward/backward citation review.

## O. INTERNAL REVIEW

The required single hostile review is saved as
`paper_audit/INTERNAL_REVIEW.md` and is prominently labeled **NOT EXTERNAL PEER
REVIEW**. The five leading residual concerns are:

1. no independent human proof or theorem-priority review;
2. synthetic exact-statevector Penalty-X scope and a depth-three held-out arm;
3. only 15 independent held-out graph units and no deployment calibration of
   the H2 margin;
4. unmeasured hardware sampling/CVaR tail-estimation costs and no end-to-end
   classical-solver comparison;
5. $m=20$ reversal and $m=22$ resource censoring preclude scaling
   generalization.

One consolidated manuscript revision addressed the review; no iterative
result-changing edits were performed.

## P. HUMAN TODO

- independent proof review;
- independent prior-art/priority review;
- affiliation confirmation;
- acknowledgments and funding confirmation;
- repository and archive/DOI link;
- venue-specific class, length, and formatting migration;
- external empirical reproduction;
- final Overleaf/pdfLaTeX compilation and visual page proof.

## Q. OVERLEAF TEST

- ZIP corruption test: **PASS**.
- ZIP extraction: **PASS**.
- `main.tex` at extraction root: **YES**.
- Clean compile: **NOT AVAILABLE**.
- Static brace/environment/input/asset check: **PASS**.
- Unresolved citations: **0**.
- Unresolved references: **0**.
- Missing figures: **0**.
- Missing table inputs: **0**.
- Absolute paths: **0**.
- Symlinks: **0**.
- Forbidden cache/Git/build content: **0**.

## R. GIT

- Branch: `manuscript/overleaf-full-v1`.
- Source commit: `260e258af7d397f53c62521d9f52b31223076ec9`.
- Intended commit message: `Create complete Overleaf manuscript package`.
- Commit SHA: reported in the final handoff after the immutable commit is
  created (a commit cannot contain its own SHA).
- Push: **not performed**.
- Merge: **not performed**.

All 1,403 protected predecessor files match the synthesis hash manifest. The
original empirical worktree retains its exact pre-existing Phase-3B dirty
fingerprint; Theory-v2, Theory-v3, and synthesis worktrees remain clean at
their audited commits. The final project suite result is **165 passed in
79.19 seconds**.
