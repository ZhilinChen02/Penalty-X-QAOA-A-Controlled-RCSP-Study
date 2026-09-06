# Manuscript sources in the public code release

This directory contains the manuscript, supplementary sources, bibliography,
figures and compact evidence tables. The historical Overleaf ZIP is not part of
this code release. The Springer class and bibliography style are also omitted;
supply the official template separately as described in `../paper/README.md`.

From the repository root, `python scripts/reproduce_figures.py --paper
--output-dir dist/paper_review --template-dir /path/to/springer-template`
replots frozen data and compiles a separate paper copy containing Figure v3.
Install the optional review dependency and make pdfLaTeX/BibTeX available first.
The source manuscript here is preserved; the generated copy integrates v3 and
its supplementary panel. See `../docs/RESULT_PROVENANCE.md` for the data chain.

Before submission, a human must confirm the affiliation, acknowledgments,
funding statement, data/code repository URL and DOI, and final venue-specific
formatting. Independent human proof and prior-art review also remain required.

The package contains no raw statevectors or canonical result directories. The
CSV files under `supplementary/` provide compact claim and numeric provenance;
their project-relative source identifiers refer to the frozen scientific
artifact at baseline commit `4d1111f3661f4b2df852eec2b382555a63e434d2`.
Figure 11 is explicitly post-hoc endpoint-sampling robustness and is not part
of the preregistered confirmatory family. Figures 12--16 and Tables R1/S6--S10
report the separate reviewer-robustness analyses; they do not replace the
frozen held-out test. Independent external reproduction remains pending.
