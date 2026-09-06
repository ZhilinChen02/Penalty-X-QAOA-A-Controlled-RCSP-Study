# SN Computer Science v3 journal-requirements audit

Audit date: 2026-08-31 (Europe/Copenhagen)  
Target journal: *SN Computer Science*  
Planned article type: Original Research

## Authoritative sources

- [SN Computer Science submission guidelines](https://link.springer.com/journal/42979/submission-guidelines)
- [SN Computer Science journal page](https://link.springer.com/journal/42979)
- [Springer Nature LaTeX author support](https://www.springernature.com/la/authors/campaigns/latex-author-support)

The journal-level instructions take precedence over the generic template. The
requirements below were checked against the live pages on the audit date.

## Requirement mapping

| Current requirement | v3 implementation | Status |
|---|---|---|
| Editable manuscript source | Flat LaTeX source ZIP | Complete |
| Springer Nature LaTeX template | Official `sn-jnl` 3.1, December 2024 | Complete |
| Concise title and complete title-page metadata | Title complete; author e-mail and affiliation remain placeholders | **Author action required** |
| Structured abstract, 150--250 words | Purpose/Methods/Results/Conclusion; 231 words | Complete |
| Four to six keywords | Six keywords | Complete |
| No more than three displayed heading levels | Section/subsection/subsubsection only in v3 | Complete |
| Numeric citations in square brackets | `sn-mathphys-num` | Complete |
| Consecutively numbered reference list and DOI links when available | BibTeX source audited; 31 cited keys resolve | Complete pending portal render |
| Figures inside the body and supplied separately | Eleven body-linked vector PDFs, `Fig1.pdf`--`Fig11.pdf` | Complete |
| Statements and Declarations | All standard headings present | Complete structurally; funding and competing interests require author text |
| LLM use documented when beyond copy editing | AI-assisted publication-preparation disclosure in Methods | Complete, subject to author approval |
| LaTeX files compile using pdfLaTeX and are zipped | `pdflatex` option and flat ZIP; Tectonic fallback compilation passes | Final pdfLaTeX/portal check required |
| No source subdirectories in the compilation upload | All 15 source files are at ZIP root | Complete |

## Scope fit

The journal's broad computer-science scope includes quantum computing and
mathematical/combinatorial optimization. The manuscript is positioned as a
controlled empirical-methodology paper at that intersection. The cover letter
does not claim a new CVaR method, quantum advantage, or a universal QAOA
limitation.

## Package layout

- `dist/Q-RouteDilution_SNCS_v3.zip`: the flat compilation-source upload.
- `dist/Q-RouteDilution_SNCS_v3_supplementary.zip`: five flat provenance/data
  files for separate supplementary-material designation.
- `dist/Q-RouteDilution_SNCS_v3.pdf`: locally rendered review PDF produced by
  the isolated Tectonic fallback compiler.
- `submission/sn_computer_science_v3/cover_letter.md`: editable cover-letter
  draft with explicit author-confirmation fields.
- `submission/sn_computer_science_v3/submission_metadata.json`: copy/paste
  metadata and unresolved fields.
- `submission/sn_computer_science_v3/SUBMISSION_CHECKLIST.md`: final author and
  production gate.

## Deliberately unresolved

No affiliation, active e-mail address, ORCID, funding, competing-interest
statement, acknowledgements, repository URL, or DOI was inferred. The title
page and declarations retain visible placeholders until the author supplies
or confirms those facts. Independent proof review, prior-art judgment, and
external reproduction also remain open human-only tasks.
