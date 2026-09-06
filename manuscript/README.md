# Manuscript scaffold

This directory is an architecture freeze, not a polished manuscript. The
selected strategy is empirical-primary with theory as a scoped boundary and
cost-accounting framework. Claim IDs must resolve in
`results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv`; source asset IDs resolve in
`SYNTHESIS_INPUT_INVENTORY.csv`.

Build, if a LaTeX distribution is available:

```bash
cd manuscript
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Before prose drafting, complete independent human proof and prior-art review.
Do not add a claim, headline number, or visual without adding its matrix row and
canonical source first.
