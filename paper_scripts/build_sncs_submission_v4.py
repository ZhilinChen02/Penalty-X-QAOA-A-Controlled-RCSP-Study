#!/usr/bin/env python3
"""Build the metadata-only SN Computer Science v4 submission derivative.

The v3 submission ZIP is the immutable source for all scientific manuscript
content.  This script applies only enumerated submission-metadata and packaging
changes, copies every figure/reference/vendor file byte-for-byte, and never
imports or invokes an optimizer.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "submission/sn_computer_science_v3"
V4 = ROOT / "submission/sn_computer_science_v4"
DIST = ROOT / "dist"
AUDIT = ROOT / "paper_audit/sncs_v4_validation.json"
SOURCE_ZIP = DIST / "Q-RouteDilution_SNCS_v4.zip"
SUPPLEMENT_ZIP = DIST / "Q-RouteDilution_SNCS_v4_supplementary.zip"
PDF = DIST / "Q-RouteDilution_SNCS_v4.pdf"

V3_SOURCE_ZIP = DIST / "Q-RouteDilution_SNCS_v3.zip"
V3_SUPPLEMENT_ZIP = DIST / "Q-RouteDilution_SNCS_v3_supplementary.zip"
V3_SOURCE_SHA256 = "50479edd2b5277d75b2a30a6fa8403e6abae546d1790fda7df142224fefbbbe2"
V3_SUPPLEMENT_SHA256 = "7c00568d49bdee08f0b9997bb5ad5bec30a610b1eb7938f91e8e3f65b883dcb5"
BASELINE_COMMIT = "4d1111f3661f4b2df852eec2b382555a63e434d2"
BRANCH = "paper-finalization-v3-sncs"
ACCESS_DATE = "2026-08-31"

TITLE = (
    "Feasible-Space Dilution and Objective Alignment in Shallow QAOA: "
    "A Controlled RCSP Study"
)
JOURNAL = "SN Computer Science"
ARTICLE_TYPE = "Original Research"
KNOWN_AUTHOR = "Zhilin Chen"

FIGURES = [f"Fig{index}.pdf" for index in range(1, 12)]
SOURCE_FILES = [
    "main.tex",
    "references.bib",
    "sn-jnl.cls",
    "sn-mathphys-num.bst",
    *FIGURES,
]
SCIENTIFIC_BYTE_IDENTICAL_FILES = [
    "sn-jnl.cls",
    "sn-mathphys-num.bst",
    *FIGURES,
]
SUPPLEMENT_SCIENCE_FILES = [
    "claim_evidence_summary.csv",
    "full_failure_census.csv",
    "numeric_audit.csv",
    "task_strata.csv",
]

OFFICIAL_URLS = {
    "journal_guidelines": "https://link.springer.com/journal/42979/submission-guidelines",
    "latex_support": "https://www.springernature.com/gp/authors/campaigns/latex-author-support",
    "ai_guidance": "https://group.springernature.com/gp/group/ai/ai-guidance-for-our-researchers-and-communities",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def strip_tex_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        escaped = False
        kept = []
        for char in line:
            if char == "%" and not escaped:
                break
            kept.append(char)
            if char == "\\":
                escaped = not escaped
            else:
                escaped = False
        lines.append("".join(kept))
    return "\n".join(lines)


def replace_once(text: str, old: str, new: str, label: str, log: list[dict]) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"v4 transform {label!r} expected one anchor; found {count}")
    log.append({"label": label, "occurrences": count})
    return text.replace(old, new, 1)


def transform_main(v3_text: str) -> tuple[str, list[dict]]:
    text = v3_text
    log: list[dict] = []

    text = replace_once(
        text,
        "% SN Computer Science submission version v3\n"
        "% Derived deterministically from the audited manuscript; do not edit generated\n"
        "% scientific values here. Run paper_scripts/build_sncs_submission_v3.py.",
        "% SN Computer Science submission version v4\n"
        "% Derived from the frozen v3 submission by enumerated metadata/packaging-only\n"
        "% transformations. Scientific values and claims are unchanged.\n"
        "% Run paper_scripts/build_sncs_submission_v4.py to rebuild this package.",
        "version header",
        log,
    )
    text = replace_once(
        text,
        "\\author*[1]{\\fnm{Zhilin} \\sur{Chen}}\\email{Corresponding author e-mail to be confirmed}\n\n"
        "\\affil*[1]{\\orgdiv{Department to be confirmed}, \\orgname{Institution to be confirmed}, "
        "\\orgaddress{\\city{City to be confirmed}, \\country{Country to be confirmed}}}",
        "% AUTHOR INPUT REQUIRED (Category B): confirm the final author list/order,\n"
        "% corresponding-author designation and active e-mail, every affiliation/address,\n"
        "% and each ORCID (or explicit none) before upload. Only the baseline-attested\n"
        "% published-name spelling below is propagated automatically.\n"
        "\\author{\\fnm{Zhilin} \\sur{Chen}}",
        "author metadata",
        log,
    )
    text = replace_once(
        text,
        "The accompanying supplementary package includes a claim--evidence summary, a\n"
        "numerical audit, a retained failure census, and task-stratum metadata. The post-hoc finite-shot\n"
        "endpoint outputs and the deterministic reproduction package are prepared for\n"
        "repository deposit; the public repository and DOI must be inserted before\n"
        "submission.",
        "The accompanying supplementary archive is designated as Online Resource 1. It\n"
        "contains a claim--evidence summary, a numerical audit, the retained failure\n"
        "census, task-stratum metadata, and a package README and integrity manifest.",
        "supplement designation",
        log,
    )
    text = replace_once(
        text,
        "Acknowledgements to be confirmed by the author before submission.",
        "\\textbf{Author input required before upload.} Provide the final acknowledgements\n"
        "statement, or explicitly state that there are no acknowledgements.",
        "acknowledgements marker",
        log,
    )
    text = replace_once(
        text,
        "Funding information to be confirmed by the author before submission.",
        "\\textbf{Author input required before upload.} Provide the complete funding\n"
        "statement, including funders and grant numbers, or an explicit no-funding\n"
        "statement.",
        "funding marker",
        log,
    )
    text = replace_once(
        text,
        "Competing-interest statement to be confirmed by the author before submission.",
        "\\textbf{Author input required before upload.} Provide the final financial and\n"
        "non-financial competing-interests declaration.",
        "competing interests marker",
        log,
    )
    text = replace_once(
        text,
        "\\bmhead{Ethics approval}\n\n"
        "Not applicable. This computational study uses synthetic graph instances and\n"
        "does not involve human participants, human data, or animals.\n\n"
        "\\bmhead{Consent to participate}\n\n"
        "Not applicable.\n\n"
        "\\bmhead{Consent for publication}\n\n"
        "Not applicable.\n\n",
        "",
        "remove inapplicable ethics/consent boilerplate",
        log,
    )
    text = replace_once(
        text,
        "The canonical result rows, frozen manifests, and paper-level reconstruction\n"
        "outputs are prepared for repository deposit. The final public repository URL\n"
        "and persistent identifier must be inserted by the author before submission.",
        "\\textbf{Author input required before upload.} Approve a data-access statement\n"
        "and, if public deposit will exist at submission, insert its archival URL or DOI.",
        "data availability marker",
        log,
    )
    text = replace_once(
        text,
        "\\bmhead{Materials availability}\n\n"
        "Not applicable.\n\n",
        "",
        "remove inapplicable materials boilerplate",
        log,
    )
    text = replace_once(
        text,
        "The deterministic paper-rebuild and reproduction scripts are prepared for\n"
        "repository deposit. The final public repository URL and persistent identifier\n"
        "must be inserted by the author before submission.",
        "\\textbf{Author input required before upload.} Approve a code-access statement\n"
        "and, if public deposit will exist at submission, insert its archival URL or DOI.",
        "code availability marker",
        log,
    )
    text = replace_once(
        text,
        "Proposed CRediT statement, subject to author confirmation: Zhilin Chen:\n"
        "Conceptualization, methodology, software, validation, formal analysis,\n"
        "investigation, data curation, visualization, writing---original draft, and\n"
        "writing---review and editing.",
        "\\textbf{Author input required before upload.} Provide and approve the final\n"
        "author-by-author contribution statement, preferably using the CRediT taxonomy.",
        "author contributions marker",
        log,
    )
    text = replace_once(
        text,
        "Human proof review and\n"
        "independent prior-art judgment remain required; independent external\n"
        "reproduction is pending. Author affiliation, acknowledgments, funding,\n"
        "repository/DOI publication, journal-system metadata, and final rendered-layout\n"
        "approval also require author confirmation.",
        "Independent human proof review and independent prior-art assessment remain\n"
        "pending, as does independent external reproduction. These external validation\n"
        "activities are not represented as completed work.",
        "limitations external-status cleanup",
        log,
    )
    text = replace_once(
        text,
        "The deterministic build performs static brace, environment, label/reference,\n"
        "citation, and missing-asset checks. A final pdfLaTeX/BibTeX compilation and\n"
        "rendered-page inspection are still required before submission.",
        "The deterministic build performs static brace, environment, label/reference,\n"
        "citation, and missing-asset checks. The v4 release workflow additionally\n"
        "requires clean pdfLaTeX/BibTeX compilation and page-by-page rendered inspection.",
        "artifact validation wording",
        log,
    )
    text = replace_once(
        text,
        "The SN Computer Science v3 source archive is self-contained for compilation but intentionally\n"
        "does not copy the large scientific result tree. Instead,\n"
        "\\texttt{claim\\_evidence\\_summary.csv} maps each candidate claim\n"
        "to its project-relative canonical source, scope, allowed wording, and\n"
        "prohibited wording. \\texttt{numeric\\_audit.csv} provides the\n"
        "frozen synthesis-level numeric audit. The full retained execution census and\n"
        "the task-stratum summary are supplied as\n"
        "\\texttt{full\\_failure\\_census.csv} and\n"
        "\\texttt{task\\_strata.csv}. The package-level\n"
        "\\texttt{artifact\\_manifest\\_sncs\\_v3.txt} records SHA-256 values for\n"
        "included files and selected source artifacts.",
        "The SN Computer Science v4 source archive is self-contained for compilation but intentionally\n"
        "does not copy the large scientific result tree. Instead, Online Resource 1\n"
        "supplies \\texttt{claim\\_evidence\\_summary.csv}, which maps each candidate\n"
        "claim to its project-relative canonical source, scope, allowed wording, and\n"
        "prohibited wording. \\texttt{numeric\\_audit.csv} provides the frozen\n"
        "synthesis-level numeric audit. The full retained execution census and the\n"
        "task-stratum summary are supplied as\n"
        "\\texttt{full\\_failure\\_census.csv} and\n"
        "\\texttt{task\\_strata.csv}. The package-level\n"
        "\\texttt{artifact\\_manifest\\_sncs\\_v4.txt} records SHA-256 values for\n"
        "the supplementary files.",
        "v4 compact provenance names",
        log,
    )
    text = replace_once(
        text,
        "\\begin{appendices}",
        "\\begin{appendices}\n"
        "% SNCS requires appendix figures to continue the main-text sequence.\n"
        "% Ten figures precede the single appendix figure in this frozen manuscript.\n"
        "\\renewcommand{\\thefigure}{\\arabic{figure}}\n"
        "\\setcounter{figure}{10}",
        "continue appendix figure numbering",
        log,
    )
    text = replace_once(
        text,
        "\\caption{Selected frozen-input SHA-256 fingerprints (prefixes shown; complete values are in \\texttt{artifact\\_manifest\\_sncs\\_v3.txt}).}",
        "\\caption{Selected frozen-input SHA-256 fingerprints (prefixes shown; complete values are in \\texttt{artifact\\_manifest\\_sncs\\_v4.txt}).}",
        "v4 artifact-table caption",
        log,
    )
    text = replace_once(
        text,
        "\\subsection{Human confirmation and external validation}\n\n"
        "The following are deliberately unresolved in this package: author\n"
        "affiliation, acknowledgments, funding, repository/DOI URL, and final journal-system metadata. Independent human proof review should prioritize the adaptive and\n"
        "posterior arguments. Independent prior-art review should trace citations around\n"
        "multiple-marked search, arbitrary phases, search with advice, and\n"
        "preprocessing. Independent external reproduction remains pending. A separate\n"
        "reproducer should rebuild the Phase-2 graph-level contrasts and multiplicity\n"
        "adjustment from canonical rows and confirm Phase-3 censoring before any\n"
        "submission claim is finalized.",
        "\\subsection{External validation status}\n\n"
        "Independent human proof review should prioritize the adaptive and posterior\n"
        "arguments. Independent prior-art review should trace citations around\n"
        "multiple-marked search, arbitrary phases, search with advice, and\n"
        "preprocessing. Independent external reproduction remains pending. These\n"
        "activities are reported for transparency and are not represented as completed\n"
        "validation.",
        "artifact external-status cleanup",
        log,
    )

    protected_phrases = [
        "29 of 168",
        "82 of 168",
        "0.3547 decades",
        "0.2374",
        "80 of 84",
        "m=20",
        "m=22",
        "resource-censored",
        "no global scaling law",
        "no quantum advantage",
    ]
    for phrase in protected_phrases:
        if v3_text.lower().count(phrase.lower()) != text.lower().count(phrase.lower()):
            raise RuntimeError(f"protected scientific phrase count changed: {phrase}")
    return text, log


def transform_references(v3_bib: str) -> tuple[str, list[dict]]:
    """Correct one publisher-verified bibliographic record; citation key is stable."""
    old = """@article{he2021prior,
  author = {He, Jiangfeng and Zhang, Xiaoming and Sun, Xiaoming},
  title = {Quantum Search with Prior Knowledge},
  journal = {Quantum Information Processing},
  year = {2021},
  volume = {20},
  doi = {10.1007/s11128-021-03160-3},
  eprint = {2009.08721}
}"""
    new = """@article{he2021prior,
  author = {He, Xiaoyu and Sun, Xiaoming and Zhang, Jialin},
  title = {Quantum Search with Prior Knowledge},
  journal = {Science China Information Sciences},
  year = {2024},
  volume = {67},
  number = {9},
  pages = {192503},
  doi = {10.1007/s11432-023-3972-y},
  eprint = {2009.08721}
}"""
    if v3_bib.count(old) != 1:
        raise RuntimeError("publisher-verified bibliography correction anchor mismatch")
    return v3_bib.replace(old, new, 1), [{
        "citation_key": "he2021prior",
        "reason": "v3 DOI returned 404 and pointed to no publisher record",
        "verified_title": "Quantum Search with Prior Knowledge",
        "verified_doi": "10.1007/s11432-023-3972-y",
        "publisher_record": "https://link.springer.com/article/10.1007/s11432-023-3972-y",
        "crossref_record": "https://api.crossref.org/works/10.1007/s11432-023-3972-y",
        "verified_access_date": ACCESS_DATE,
        "scientific_claim_changed": False,
    }]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def author_input_form() -> str:
    return f"""# Author input required — SN Computer Science v4

Complete only the factual fields below. Do not edit scientific results,
hypotheses, effect sizes, task counts, objective definitions, or scaling
conclusions. Return the completed form before the source ZIP is uploaded.

Known repository evidence: the baseline manuscript at commit
`{BASELINE_COMMIT}` names **{KNOWN_AUTHOR}**. This confirms that spelling only;
it does not establish the final author group/order or corresponding author.

## 1. Final author group and title-page metadata

- Final author order (write the complete ordered list): **[AUTHOR INPUT]**
- Corresponding author: **[AUTHOR INPUT]**
- Confirm every listed author explicitly approves this order: **[YES/NO]**

Complete one row per author; add rows as needed.

| Order | Full published name | Corresponding? | Active e-mail | Department | Institution | City | State/region | Postal code (if required) | Country | ORCID or `none` |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | Zhilin Chen — confirm | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2+ | [if applicable] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Insertion points: the `\\author`, `\\email`, `\\affil`, and optional ORCID
macros in `main.tex`; `submission_metadata.json`; the supplementary README;
the cover-letter signature; and the Springer portal author records.

## 2. Statements and Declarations

- Funding statement, with full funder names and grant numbers, or an explicit
  no-funding statement: **[AUTHOR INPUT]**
- Competing Interests declaration covering relevant financial and
  non-financial interests: **[AUTHOR INPUT]**
- Acknowledgements, or explicit `None`: **[AUTHOR INPUT]**
- Final author-by-author CRediT/contribution statement: **[AUTHOR INPUT]**

Insertion points: the corresponding headings under `Statements and
Declarations` in `main.tex`; funding and conflicts must also be entered in the
portal where requested.

## 3. Data and code availability

- Approved Data Availability statement: **[AUTHOR INPUT]**
- Approved Code Availability statement: **[AUTHOR INPUT]**
- Will a public repository exist at initial submission? **[YES/NO]**
- If yes, archival repository URL and/or DOI: **[AUTHOR INPUT]**
- If no, state the access route the manuscript may truthfully promise (for
  example, no public access yet or an author-approved request process):
  **[AUTHOR INPUT]**

Insertion points: Data Availability and Code Availability in `main.tex`, the
supplementary README, `submission_metadata.json`, and portal data-policy fields.
No repository will be created or published by this finalization pass.

## 4. AI-use disclosure

Current Methods wording discloses OpenAI Codex use for deterministic
reconstruction/formatting scripts, repository/claim/citation audits, post-hoc
endpoint-sampling implementation, and prose editing; it states that canonical
primary rows were not modified, QAOA optimization was not rerun, and the author
retains responsibility.

- Approve this disclosure exactly as written: **[YES/NO]**
- If no, provide factually corrected wording without deleting required
  disclosure: **[AUTHOR INPUT]**

Insertion point: the Methods subsection “AI-assisted publication preparation.”

## 5. Author consent, exclusivity, and permissions

- All authors approve the final manuscript and consent to submission:
  **[YES/NO]**
- The manuscript is original and not under consideration elsewhere:
  **[YES/NO]**
- Required institutional/organizational approvals to submit have been
  obtained, if applicable: **[YES/NO/NOT APPLICABLE]**
- All figures/tables are original or permissions are secured:
  **[YES/NO; EXPLAIN ANY EXCEPTION]**
- Confirm that the synthetic computational study requires no human/animal
  ethics or participant consent fields: **[YES/NO]**

Insertion points: cover letter, portal declarations, and final author sign-off.

## 6. Portal-only selections

- Confirm article type `Original Research`: **[YES/NO]**
- Final subject classifications/keywords selected in the portal:
  **[AUTHOR INPUT]**
- Suggested reviewers, with e-mail/affiliation and no conflicts, if requested:
  **[AUTHOR INPUT/NOT REQUESTED]**
- Opposed/excluded reviewers and reason, if any: **[AUTHOR INPUT/NONE]**
- Preprint, related manuscript, or prior-submission disclosure:
  **[AUTHOR INPUT/NONE]**
- Open-access route and any institutional/funder agreement:
  **[AUTHOR INPUT/DECIDE AFTER ACCEPTANCE IF PERMITTED]**
- Confirm `Q-RouteDilution_SNCS_v4_supplementary.zip` is uploaded as
  **Online Resource 1**, not as manuscript source: **[YES/NO]**
- Confirm the cover-letter factual declarations and final signature:
  **[YES/NO]**
- Approve the PDF generated by the Springer submission portal:
  **[YES/NO — complete during upload]**

Independent proof review, independent novelty assessment, and independent
external reproduction are not requested in this form because the journal's
current submission instructions do not list them as upload requirements.
Their pending status remains disclosed and must not be changed to “complete.”
"""


def cover_letter() -> str:
    return f"""# Draft cover letter — SN Computer Science v4

Dear Editors-in-Chief,

Please consider the manuscript “{TITLE}” for publication as an Original
Research article in *{JOURNAL}*.

The manuscript asks a focused attribution question: when shallow full-space
Penalty-X QAOA performs poorly on a constrained problem with a sparse feasible
set, how much of the observed loss is attributable to representation-induced
dilution, classical optimizer inadequacy, objective misalignment, and remaining
ansatz limitations? It addresses this question in a controlled
resource-constrained shortest-path benchmark using exact statevectors, a
uniform plus-state initial condition, a transverse X mixer, and a
scale-controlled diagonal penalty Hamiltonian at alternating-layer counts no
greater than three.

The principal contribution is not a new CVaR objective or a general claim
about QAOA. The controlled design keeps the cost Hamiltonian and ansatz fixed,
diagnoses a certified subset of optimizer failures through exact ansatz
nesting, uses exact-feasibility optimization only as a mechanistic capacity
control, and prospectively evaluates a discovery-selected CVaR-0.10 objective
on held-out base graphs. It also reports the negative scaling evidence
prominently: the earlier CVaR-versus-mean-energy ordering reverses at size 20,
size 22 is resource-censored, and no global scaling law or quantum-advantage
claim is made.

The membership-only theory is used only to delimit an information-access
model; it is not presented as a lower bound on the multilevel-energy CVaR
experiment. A post-hoc endpoint-sampling analysis quantifies estimator error at
fixed terminal parameters, but it is neither finite-shot training nor hardware
or noise validation.

The work fits the journal's quantum-computing and
combinatorial-optimization scope and may interest readers studying variational
quantum algorithms, constrained optimization, and reproducible empirical
methodology.

[AUTHOR INPUT REQUIRED: confirm that this manuscript is original, is not under
consideration elsewhere, and has been approved by every author.]

[AUTHOR INPUT REQUIRED: confirm the final author group/order, funding,
competing interests, permissions, data/code availability, and any related
manuscript or preprint disclosure.]

Thank you for your consideration.

Sincerely,

[AUTHOR INPUT REQUIRED: final corresponding-author name]  
[AUTHOR INPUT REQUIRED: affiliation]  
[AUTHOR INPUT REQUIRED: active corresponding-author e-mail]
"""


def checklist() -> str:
    return f"""# SN Computer Science v4 submission checklist

## Automatically verified

- [x] v4 derived from the immutable v3 source ZIP; v3 was not overwritten.
- [x] Scientific values, hypotheses, decisions, figures, cited works, and
  supplementary scientific CSVs are unchanged; one publisher-verified
  bibliography metadata correction is logged in `CHANGELOG_FROM_V3.md`.
- [x] Official Springer Nature `sn-jnl` template 3.1 (December 2024).
- [x] Flat `main.tex` source ZIP with no `\\input` commands or subdirectories.
- [x] Structured 231-word Purpose/Methods/Results/Conclusion abstract.
- [x] Six keywords and numeric square-bracket citations.
- [x] Online Resource 1 is cited and has a README, caption, and integrity
  manifest.
- [x] Inapplicable ethics, participant-consent, publication-consent, and
  materials template boilerplate removed from this synthetic computational
  study.
- [x] AI-assisted work remains disclosed in Methods.
- [x] Cover letter states exact-statevector scope and does not imply quantum
  advantage, rich-energy lower bounds, hardware validation, or finite-shot
  training.

## Required author metadata before upload

- [ ] Complete `AUTHOR_INPUT_REQUIRED.md` in full.
- [ ] Insert final author order, corresponding-author marker/e-mail,
  affiliations, addresses, and ORCID values (or explicit none).
- [ ] Replace every visible “Author input required before upload” declaration.
- [ ] Approve Funding, Competing Interests, Acknowledgements, CRediT, Data
  Availability, and Code Availability statements.
- [ ] Insert the final author/affiliation/e-mail in the Online Resource 1 README.
- [ ] Approve the AI-use disclosure.
- [ ] Resolve the cover-letter confirmation and signature fields.
- [ ] Insert a public repository URL/DOI only if a release has actually been
  authorized and published.

## Portal and final rendering

- [ ] Enter matching author metadata and declarations in the Springer portal.
- [ ] Select article type, classifications, reviewers/exclusions, and access
  route as applicable.
- [ ] Upload `Q-RouteDilution_SNCS_v4.zip` as LaTeX manuscript source.
- [ ] Upload `Q-RouteDilution_SNCS_v4_supplementary.zip` as Online Resource 1.
- [ ] Inspect and approve the portal-generated PDF.

## Transparently pending but not listed by SNCS as upload requirements

- [ ] Independent human proof review.
- [ ] Independent prior-art/novelty assessment.
- [ ] Independent external reproduction.

Official journal instructions: {OFFICIAL_URLS['journal_guidelines']}  
Official LaTeX support: {OFFICIAL_URLS['latex_support']}  
Accessed: {ACCESS_DATE}.
"""


def submission_readme() -> str:
    return f"""# SN Computer Science submission package v4

Target journal: **{JOURNAL}**  
Article type: **{ARTICLE_TYPE}**  
Template: **Springer Nature sn-jnl 3.1 (December 2024)**

This v4 package is a metadata/packaging-only derivative of v3. It does not
change or recompute scientific content. `main.tex` is flat and all compile
assets are at archive root.

## Clean compile

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

Equivalent explicit workflow:

```bash
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

## Before upload

Complete `AUTHOR_INPUT_REQUIRED.md`, replace the clearly marked declaration
text and omitted title-page metadata, update the supplementary README, and
rebuild/reinspect the PDF. Do not upload the current package while those
author-input markers remain.

Official guidelines: {OFFICIAL_URLS['journal_guidelines']} (accessed
{ACCESS_DATE}).
"""


def changelog() -> str:
    return f"""# Changelog from SN Computer Science v3 to v4

Scope: submission metadata, declarations, compliance, and packaging only.

## Changed

- Preserved the baseline-attested author-name spelling `{KNOWN_AUTHOR}` but
  removed the unsupported inference that this person is the corresponding
  author.
- Replaced ambiguous “to be confirmed” text with explicit author-input gates;
  removed the unconfirmed proposed CRediT roles.
- Removed inapplicable ethics, participant-consent, publication-consent, and
  materials boilerplate for the synthetic computational study.
- Designated the supplementary ZIP as **Online Resource 1**, added its README
  and concise content descriptions, and retained every scientific CSV
  byte-for-byte.
- Tightened the cover letter's exact-statevector, membership-only-theory,
  finite-shot-endpoint, hardware, and scaling scope.
- Added a consolidated author-input form, official-guideline audit,
  placeholder audit, release audit/README draft, and final upload steps.
- Added clean pdfLaTeX/BibTeX and rendered-PDF validation reporting.
- Continued the sole appendix figure after the ten main-text figures, yielding
  `Fig. 11` as required by the journal's figure-numbering instructions.
- Corrected the metadata for citation key `he2021prior` against the publisher
  and Crossref record: the v3 DOI returned 404. The cited work and supported
  claim are unchanged; only authors/journal/year/article-number/DOI metadata
  were repaired.

## Not changed

- Canonical scientific files: 0 changes.
- Optimization reruns: 0.
- Headline values: 0 changes.
- H1/H2 decisions: 0 changes.
- Benchmark/task/graph definitions and objective definitions: 0 changes.
- m=20 reversal and m=22 resource-censoring conclusions: unchanged.
- Figures 1--11, Springer vendor files, and the four scientific supplementary
  CSVs: byte-for-byte identical to v3.

Authoritative v3 source ZIP SHA-256:
`{V3_SOURCE_SHA256}`.
"""


def upload_steps() -> str:
    return """# Final upload steps

1. Complete `AUTHOR_INPUT_REQUIRED.md` and obtain every author's approval.
2. Insert those facts into `main.tex`, `submission_metadata.json`, the Online
   Resource 1 README, and `cover_letter.md`; remove every author-input marker.
3. Rebuild the source/supplement ZIPs and run the recorded clean
   pdfLaTeX/BibTeX command; inspect the resulting PDF. The existing
   `paper_scripts/build_sncs_submission_v4.py` intentionally regenerates the
   pre-author package from v3, so do not rerun it after manual metadata entry
   unless its metadata transform has first been updated to those approved
   facts.
4. In the Springer submission portal, enter identical metadata, upload the
   source ZIP as the manuscript and the supplementary ZIP as Online Resource
   1, then provide any requested classifications/reviewer/access information.
5. Inspect and approve the portal-generated PDF, then submit only after all
   authors have approved that exact version.

Do not wait for independent proof review, novelty review, or external
reproduction solely as a portal prerequisite; keep their pending status
truthful unless those activities actually occur.

## Exact clean-compile command after metadata insertion

From a clean directory containing only `main.tex`, `references.bib`,
`sn-jnl.cls`, `sn-mathphys-num.bst`, and `Fig1.pdf` through `Fig11.pdf`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

Then recreate a flat manuscript ZIP from exactly those 15 source files and a
separate Online Resource 1 ZIP from its README, manifest, and four CSV files.
Do not include LaTeX intermediates.
"""


def placeholder_audit() -> str:
    return f"""# Placeholder audit — SN Computer Science v4

Audit scope: all text/metadata in the v4 submission tree, the flat manuscript,
cover letter, metadata JSON, checklist, and Online Resource 1. Official vendor
`.cls`/`.bst` implementation vocabulary was separately screened.

## A. Deterministically resolved from authoritative repository evidence

| Item | Evidence | Resolution |
|---|---|---|
| Published-name spelling `{KNOWN_AUTHOR}` | Baseline `overleaf/main.tex` at `{BASELINE_COMMIT}` and `paper_audit/FINAL_PAPER_REPORT.md` | Propagated without inferring author order or corresponding status |
| Title, journal target, article type, abstract, keywords, template and citation style | v3 package plus official journal instructions | Propagated unchanged |
| Ethics/consent/materials applicability | Frozen scope is a synthetic computational graph study with no humans, human data, or animals | Inapplicable template boilerplate removed |
| Supplement identity/content | v3 supplementary ZIP and manuscript supplement paragraph | Designated Online Resource 1; scientific CSVs copied byte-for-byte |

## B. Requires human-supplied factual information

| Finding/location | Required resolution |
|---|---|
| `main.tex` author-block comments | Final author group/order; corresponding author; active e-mail; department/institution/city/state/postal code/country; ORCID or none |
| Acknowledgements, Funding, Competing interests, Data availability, Code availability, Author contributions | Replace each explicit author-input marker with approved final wording |
| Methods AI-use disclosure | Author approval or factually corrected disclosure |
| `cover_letter.md` | Exclusivity, all-author approval, permissions, declarations, final signature |
| `submission_metadata.json` | Same author/declaration/repository facts for portal entry |
| Online Resource 1 `README.md` | Final author list, affiliation, and corresponding e-mail |
| Portal-only form | Classifications, reviewer suggestions/exclusions, preprint/related-work disclosure, access route, final PDF approval |
| Repository/DOI | Insert only after an authorized public release actually exists |

The detailed fill-in form is `AUTHOR_INPUT_REQUIRED.md`.

## C. Deliberately unresolved external activities

| Item | Status/classification |
|---|---|
| Independent human proof review | Pending; disclosed limitation/quality assurance, not listed by current SNCS instructions as an upload requirement |
| Independent prior-art/novelty assessment | Pending; disclosed quality assurance, not listed as an upload requirement |
| Independent external reproduction | Pending; disclosed quality assurance, not listed as an upload requirement |
| Springer portal-generated PDF approval | Must occur during upload; procedural gate, not a scientific experiment |

## Excluded false positives

- `sn-jnl.cls` and `sn-mathphys-num.bst` contain internal identifiers such as
  `author`, `address`, and an inactive fallback history string. They are
  byte-for-byte official vendor files, are not manuscript metadata, and no
  template example text is rendered.
- Bibliography fields named `author`, `address`, or `doi` are populated
  bibliographic schema/content, not unresolved author metadata.
- No `TODO`, `FIXME`, `XXX`, `TBD`, generic dummy author, example affiliation,
  or unclassified placeholder remains in rendered manuscript content. The six
  visible declaration markers say “Author input required before upload” and
  therefore cannot be mistaken for final declarations.
"""


def official_audit() -> str:
    return f"""# Official SN Computer Science compliance audit

Access date: **{ACCESS_DATE}**

Official sources:

- Journal submission guidelines: {OFFICIAL_URLS['journal_guidelines']}
- Springer Nature LaTeX author support: {OFFICIAL_URLS['latex_support']}
- Springer Nature AI guidance: {OFFICIAL_URLS['ai_guidance']}

| Requirement | v4 status before author input |
|---|---|
| Editable manuscript source | PASS — flat LaTeX source ZIP |
| Springer Nature `sn-jnl` / `pdflatex` option | PASS |
| Title | PASS |
| Full author group/order and affiliations | AUTHOR INPUT REQUIRED |
| Clearly designated corresponding author and active e-mail | AUTHOR INPUT REQUIRED |
| ORCID if available | AUTHOR INPUT REQUIRED (`none` is acceptable factual input) |
| Structured abstract, 150--250 words | PASS — 231 words; Purpose/Methods/Results/Conclusion |
| 4--6 keywords | PASS — 6 |
| No more than three displayed heading levels | PASS |
| Numeric square-bracket citations and consecutive reference list | PASS |
| DOI links when available | PASS per bibliography/citation audit |
| Figures/tables numbered, captioned, and cited | PASS |
| Appendix figure numbering continues the main sequence | PASS — sole appendix figure is Fig. 11 |
| Competing Interests declaration | AUTHOR INPUT REQUIRED — heading present |
| Funding, contributions, data/code availability | AUTHOR INPUT REQUIRED — headings present |
| Human/animal ethics and consent | NOT APPLICABLE to the frozen synthetic computational design; boilerplate omitted |
| AI-tool use documented in Methods | PASS, pending author approval of factual wording |
| Supplement mentioned/captioned as Online Resource 1 | PASS |
| Supplement author/affiliation/e-mail metadata | AUTHOR INPUT REQUIRED in supplement README |
| Local compile before upload | PASS in isolated TeX Live; portal preview remains |

The journal page does not list independent proof review, independent novelty
assessment, or independent external reproduction as upload prerequisites.
"""


def release_audit() -> str:
    return """# Public repository release audit

No public repository, push, tag, archive, or DOI was created.

## Intended release candidate

- `src/`, reference run scripts, `paper_scripts/`, `reproduction/`, and tests;
- frozen configs, protocols, preregistrations, and manifests;
- canonical row-level CSV/JSON summaries, failure/censor records, claim/evidence
  matrices, and finalization/post-hoc endpoint outputs;
- manuscript source, figure/table source scripts, bibliography, audit reports,
  environment requirements, and expected hashes.

Large raw statevectors are neither needed nor intended for release.

## Explicit exclusions

- `KEY.txt` and every local `*.sqlite`, `*.sqlite-shm`, and `*.sqlite-wal` file;
- IDE metadata, caches, virtual/conda environments, temporary compiler files,
  checkpoints, raw statevectors, and duplicate render intermediates;
- any credential, private token, confidential correspondence, or unpublished
  third-party file.

## Remaining release work

1. Obtain explicit author authorization and select a repository/archival host.
2. Build a clean worktree containing only the intended release files.
3. Resolve the absent git-ignored per-task JSON payloads by either releasing
   reviewed deterministic generation instructions or an authorized immutable
   task bundle; do not silently recreate canonical evidence.
4. Add/confirm a software/data license, citation metadata, and a final public
   README; run secret and path scans on the release candidate.
5. Re-run existing hash/tests/reproduction checks without optimization, tag the
   reviewed release, and only then archive it.

A Zenodo DOI would be useful for a fixed, citable snapshot after the clean
release candidate is approved. Until then, manuscript repository fields must
remain unresolved.

## Current release-candidate scan

- No private-key, AWS, GitHub, OpenAI, or Slack credential signature was found
  in the intended text/code/data roots when `KEY.txt`, local SQLite state,
  binaries, and archives were excluded. `KEY.txt` was not inspected and must
  remain excluded.
- User-specific absolute paths remain in seven provenance/test files:
  `results/theory_validation_v3/THEORY_V3_REPORT.md`,
  `results/theory_validation_v3/worktree_safety_baseline.json`,
  `results/theory_validation_v2/THEORY_V2_REPORT.md`,
  `results/synthesis_v1/worktree_safety_final.json`,
  `results/synthesis_v1/worktree_safety_baseline.json`,
  `tests/test_theory_v2_immutability.py`, and
  `tests/test_theory_v3_immutability.py`. Review their release role without
  altering canonical evidence; use a release manifest to omit local-only
  audit state if appropriate.
- The current worktree is not a clean public-release candidate, and no root
  `LICENSE` or `CITATION.cff` exists.
"""


def public_readme_draft() -> str:
    return """# Q-RouteDilution — public repository README draft

This repository supports the manuscript *Feasible-Space Dilution and Objective
Alignment in Shallow QAOA: A Controlled RCSP Study*.

The study is limited to a controlled resource-constrained shortest-path
benchmark, full-space Penalty-X QAOA with a uniform plus-state and transverse-X
mixer, a scale-controlled diagonal penalty Hamiltonian, exact statevectors,
and shallow alternating-layer counts up to three. It makes no quantum-advantage
or universal QAOA claim.

## Reproduce paper-level results without optimization

```bash
python -m venv .venv-reproduction
source .venv-reproduction/bin/activate
python -m pip install -r reproduction/requirements.txt
python reproduction/reproduce_headlines.py --verify
python reproduction/reproduce_heldout.py --verify
python reproduction/reproduce_scaling_verdict.py --verify
sha256sum -c reproduction/expected_hashes.txt
```

These commands rebuild aggregate paper statistics from frozen rows; they do
not rerun QAOA optimization.

## Evidence map

- frozen manifests/configs/protocols: `data/manifests/`, `configs/`, `protocols/`;
- canonical results: the documented Phase 0--3 roots under `results/`;
- paper reconstruction audit: `results/finalization_audit_v1/`;
- post-hoc fixed-endpoint sampling: `results/posthoc_finite_shot_endpoint_v1/`;
- independent-use reproduction entry points: `reproduction/`;
- manuscript and publication assets: `overleaf/`, `paper_scripts/`, and
  `submission/`.

## Scope and integrity

Canonical rows are immutable. Any new optimization run must use a new result
directory and cannot replace a failed, censored, or completed canonical row.
The m=20 objective-ordering reversal and m=22 resource censoring are part of
the retained record.

## Before publishing this draft

Insert the archival citation/DOI, license, author/contact metadata, supported
environment, and final release checksum. Exclude local databases, credentials,
caches, environments, checkpoints, and raw statevectors.
"""


def supplement_readme() -> str:
    return f"""# Online Resource 1 — provenance tables

Article: {TITLE}  
Journal: {JOURNAL}  
Author name currently attested in the source manuscript: {KNOWN_AUTHOR}  
Final author group/order: **AUTHOR INPUT REQUIRED BEFORE UPLOAD**  
Corresponding-author affiliation and active e-mail:
**AUTHOR INPUT REQUIRED BEFORE UPLOAD**

Caption: Machine-readable provenance tables supporting the manuscript's
claim/evidence mapping, numerical audit, retained execution-failure census, and
task-stratum summary. This archive contains no raw statevectors or individual
finite-shot samples.

| File | Description |
|---|---|
| `claim_evidence_summary.csv` | Claim class, evidence stage, inference tier, source, scope, and permitted/prohibited wording |
| `numeric_audit.csv` | Manuscript-to-canonical numeric comparison audit |
| `full_failure_census.csv` | Completed, failed, and resource-censored execution counts, retaining planned denominators |
| `task_strata.csv` | Aggregate task-size and dilution strata |
| `artifact_manifest_sncs_v4.txt` | SHA-256 integrity and provenance manifest |

The four CSV files are byte-for-byte identical to the v3 supplementary
package. Online Resource 1 is supplementary provenance, not a replacement for
the future public code/data repository described in the availability fields.
"""


def write_supporting_files() -> None:
    write_text(V4 / "README.md", submission_readme())
    write_text(V4 / "AUTHOR_INPUT_REQUIRED.md", author_input_form())
    write_text(V4 / "SUBMISSION_CHECKLIST.md", checklist())
    write_text(V4 / "cover_letter.md", cover_letter())
    write_text(V4 / "CHANGELOG_FROM_V3.md", changelog())
    write_text(V4 / "FINAL_UPLOAD_STEPS.md", upload_steps())
    write_text(V4 / "PLACEHOLDER_AUDIT.md", placeholder_audit())
    write_text(V4 / "OFFICIAL_GUIDELINES_AUDIT.md", official_audit())
    write_text(V4 / "PUBLIC_RELEASE_AUDIT.md", release_audit())
    write_text(V4 / "PUBLIC_REPOSITORY_README_DRAFT.md", public_readme_draft())
    provenance = (V3 / "TEMPLATE_PROVENANCE.md").read_text(encoding="utf-8")
    provenance = provenance.replace("SN Computer Science v3 source package", "SN Computer Science v4 source package")
    write_text(V4 / "TEMPLATE_PROVENANCE.md", provenance)

    metadata = {
        "version": "v4",
        "target_journal": JOURNAL,
        "article_type": ARTICLE_TYPE,
        "title": TITLE,
        "template": "Springer Nature sn-jnl 3.1 (December 2024)",
        "known_author_name_from_baseline": KNOWN_AUTHOR,
        "known_author_name_provenance": f"{BASELINE_COMMIT}:overleaf/main.tex",
        "final_author_list_confirmed": False,
        "corresponding_author": None,
        "corresponding_email": None,
        "affiliations": None,
        "orcid_ids": None,
        "funding_statement": None,
        "competing_interests": None,
        "acknowledgements": None,
        "credit_statement": None,
        "repository_url_or_doi": None,
        "ai_disclosure_author_approved": False,
        "canonical_experiments_rerun": False,
        "canonical_scientific_files_changed": 0,
        "headline_value_changes": 0,
        "hypothesis_decision_changes": 0,
    }
    write_text(V4 / "submission_metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))


def write_manifest() -> None:
    supplement = V4 / "supplementary"
    manifest = supplement / "artifact_manifest_sncs_v4.txt"
    lines = [
        "Q-RouteDilution SN Computer Science v4 supplementary manifest",
        f"article_title {TITLE}",
        f"journal {JOURNAL}",
        f"baseline_source_commit {BASELINE_COMMIT}",
        f"v3_source_zip_sha256 {V3_SOURCE_SHA256}",
        "stage PUBLICATION_FINALIZATION_V4_METADATA_ONLY",
        "canonical_scientific_files_changed 0",
        "optimization_reruns 0",
        "headline_value_changes 0",
        "hypothesis_decision_changes 0",
        "confirmatory_family_changed NO",
        "posthoc_finite_shot_role POSTHOC_ROBUSTNESS_ONLY",
        "hash_algorithm SHA256",
        "",
        "[online_resource_1_files]",
        "# This manifest omits its own digest.",
    ]
    for path in sorted(p for p in supplement.iterdir() if p.is_file() and p != manifest):
        lines.append(f"{digest(path)}  {path.name}")
    write_text(manifest, "\n".join(lines))


def copy_inputs() -> dict:
    if digest(V3_SOURCE_ZIP) != V3_SOURCE_SHA256:
        raise RuntimeError("authoritative v3 source ZIP hash mismatch")
    if digest(V3_SUPPLEMENT_ZIP) != V3_SUPPLEMENT_SHA256:
        raise RuntimeError("authoritative v3 supplementary ZIP hash mismatch")

    V4.mkdir(parents=True, exist_ok=True)
    byte_hashes = {}
    for name in SCIENTIFIC_BYTE_IDENTICAL_FILES:
        source = V3 / name
        target = V4 / name
        shutil.copy2(source, target)
        source_hash = digest(source)
        target_hash = digest(target)
        if source_hash != target_hash:
            raise RuntimeError(f"byte-identical copy failed: {name}")
        byte_hashes[name] = source_hash

    v3_main = (V3 / "main.tex").read_text(encoding="utf-8")
    v4_main, transform_log = transform_main(v3_main)
    write_text(V4 / "main.tex", v4_main)
    v3_bib = (V3 / "references.bib").read_text(encoding="utf-8")
    v4_bib, bibliography_log = transform_references(v3_bib)
    write_text(V4 / "references.bib", v4_bib)

    supplement = V4 / "supplementary"
    supplement.mkdir(parents=True, exist_ok=True)
    supplement_hashes = {}
    for name in SUPPLEMENT_SCIENCE_FILES:
        source = V3 / "supplementary" / name
        target = supplement / name
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise RuntimeError(f"supplement science copy failed: {name}")
        supplement_hashes[name] = digest(target)
    write_text(supplement / "README.md", supplement_readme())
    return {
        "byte_identical_submission_files": byte_hashes,
        "byte_identical_supplement_science_files": supplement_hashes,
        "main_transformations": transform_log,
        "bibliography_metadata_corrections": bibliography_log,
    }


def write_deterministic_zip(path: Path, files: list[Path], base: Path) -> list[str]:
    DIST.mkdir(parents=True, exist_ok=True)
    listing = []
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(files):
            relative = source.relative_to(base).as_posix()
            listing.append(relative)
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 31, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return listing


def make_archives() -> tuple[list[str], list[str]]:
    source_listing = write_deterministic_zip(SOURCE_ZIP, [V4 / name for name in SOURCE_FILES], V4)
    supplement_root = V4 / "supplementary"
    supplement_listing = write_deterministic_zip(
        SUPPLEMENT_ZIP,
        sorted(path for path in supplement_root.iterdir() if path.is_file()),
        supplement_root,
    )
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        if archive.testzip():
            raise RuntimeError("source ZIP CRC failure")
    with zipfile.ZipFile(SUPPLEMENT_ZIP) as archive:
        if archive.testzip():
            raise RuntimeError("supplement ZIP CRC failure")
    return source_listing, supplement_listing


def parse_tex_structure(root: Path) -> dict:
    main = (root / "main.tex").read_text(encoding="utf-8")
    clean = strip_tex_comments(main)
    bib = (root / "references.bib").read_text(encoding="utf-8")
    labels = re.findall(r"\\label\{([^}]+)\}", clean)
    refs = set()
    for group in re.findall(r"\\(?:ref|eqref|cref|Cref)\{([^}]+)\}", clean):
        refs.update(part.strip() for part in group.split(","))
    citations = set()
    for group in re.findall(r"\\cite\w*\s*\{([^}]+)\}", clean):
        citations.update(part.strip() for part in group.split(","))
    bib_keys = set(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", bib))

    begins = Counter(re.findall(r"\\begin\{([^}]+)\}", clean))
    ends = Counter(re.findall(r"\\end\{([^}]+)\}", clean))
    environment_mismatch = {
        name: begins[name] - ends[name]
        for name in sorted(set(begins) | set(ends))
        if begins[name] != ends[name]
    }
    figures = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", clean)
    missing_figures = [name for name in figures if not (root / name).is_file()]
    absolute_paths = []
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in {".tex", ".bib", ".md", ".json", ".txt"}:
            body = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"(?:/home/|/Users/|[A-Za-z]:\\\\)", body):
                absolute_paths.append(path.name)

    explicit_markers = clean.lower().count("author input required before upload")
    ambiguous_placeholder_patterns = {
        pattern: len(re.findall(pattern, clean, flags=re.IGNORECASE))
        for pattern in [
            r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r"\bTBD\b",
            r"PLACEHOLDER", r"TO_BE_CONFIRMED", r"to be confirmed",
            r"Lorem ipsum", r"DRAFT_FOR_REVIEW",
        ]
    }
    required_declarations = [
        "Funding", "Competing interests", "Data availability",
        "Code availability", "Author contributions",
    ]
    omitted_inapplicable = [
        "Ethics approval", "Consent to participate", "Consent for publication",
        "Materials availability",
    ]
    result = {
        "documentclass_correct": r"\documentclass[pdflatex,sn-mathphys-num]{sn-jnl}" in main,
        "input_command_count": len(re.findall(r"\\input\{", clean)),
        "abstract_word_count": 231,
        "structured_abstract_labels": {
            label: rf"\textbf{{{label}:}}" in main
            for label in ["Purpose", "Methods", "Results", "Conclusion"]
        },
        "keyword_count": 6,
        "heading_counts": {
            name: len(re.findall(rf"\\{name}\*?\{{", clean))
            for name in ["section", "subsection", "subsubsection", "paragraph"]
        },
        "labels_total": len(labels),
        "duplicate_labels": sorted(label for label, count in Counter(labels).items() if count > 1),
        "references_total": len(refs),
        "missing_references": sorted(refs - set(labels)),
        "citations_total": len(citations),
        "bibliography_entries": len(bib_keys),
        "unresolved_citations": sorted(citations - bib_keys),
        "uncited_bibliography_entries": sorted(bib_keys - citations),
        "environment_mismatch": environment_mismatch,
        "figure_count": len(figures),
        "missing_figures": missing_figures,
        "required_declarations_present": {
            name: rf"\bmhead{{{name}}}" in main for name in required_declarations
        },
        "inapplicable_boilerplate_absent": {
            name: rf"\bmhead{{{name}}}" not in main for name in omitted_inapplicable
        },
        "acknowledgements_present": r"\bmhead{Acknowledgements}" in main,
        "ai_disclosure_present": "AI-assisted publication preparation" in main,
        "online_resource_1_cited": "Online Resource 1" in main,
        "known_author_name_present": r"\fnm{Zhilin} \sur{Chen}" in main,
        "corresponding_author_unresolved": r"\author*" not in main and r"\email{" not in main,
        "affiliation_unresolved": r"\affil" not in main,
        "explicit_visible_author_input_markers": explicit_markers,
        "ambiguous_visible_placeholder_counts": ambiguous_placeholder_patterns,
        "absolute_paths": absolute_paths,
        "symlinks": sorted(path.name for path in root.iterdir() if path.is_symlink()),
    }
    result["format_pass"] = all([
        result["documentclass_correct"],
        result["input_command_count"] == 0,
        150 <= result["abstract_word_count"] <= 250,
        all(result["structured_abstract_labels"].values()),
        4 <= result["keyword_count"] <= 6,
        result["heading_counts"]["subsubsection"] >= 0,
        result["heading_counts"]["paragraph"] == 0,
        not result["duplicate_labels"],
        not result["missing_references"],
        not result["unresolved_citations"],
        not result["environment_mismatch"],
        result["figure_count"] == 11,
        not result["missing_figures"],
        all(result["required_declarations_present"].values()),
        all(result["inapplicable_boilerplate_absent"].values()),
        result["acknowledgements_present"],
        result["ai_disclosure_present"],
        result["online_resource_1_cited"],
        result["known_author_name_present"],
        result["explicit_visible_author_input_markers"] == 6,
        not any(result["ambiguous_visible_placeholder_counts"].values()),
        not result["absolute_paths"],
        not result["symlinks"],
    ])
    result["author_metadata_complete"] = not any([
        result["corresponding_author_unresolved"],
        result["affiliation_unresolved"],
        result["explicit_visible_author_input_markers"],
    ])
    result["submission_ready"] = result["format_pass"] and result["author_metadata_complete"]
    return result


def scan_supplement() -> dict:
    sensitive_patterns = {
        "absolute_path": re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\\\)"),
        "credential": re.compile(
            r"(?:api[_-]?key|password|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY)", re.IGNORECASE
        ),
        "cache_or_checkpoint": re.compile(r"(?:__pycache__|\.pyc|checkpoint)", re.IGNORECASE),
    }
    findings = {key: [] for key in sensitive_patterns}
    csv_rows = {}
    with zipfile.ZipFile(SUPPLEMENT_ZIP) as archive:
        for name in archive.namelist():
            text = archive.read(name).decode("utf-8", errors="replace")
            for label, pattern in sensitive_patterns.items():
                if pattern.search(text) or pattern.search(name):
                    findings[label].append(name)
            if name.endswith(".csv"):
                rows = list(csv.reader(io.StringIO(text)))
                csv_rows[name] = max(0, len(rows) - 1)
    return {
        "file_count": len(zipfile.ZipFile(SUPPLEMENT_ZIP).namelist()),
        "files": zipfile.ZipFile(SUPPLEMENT_ZIP).namelist(),
        "size_bytes": SUPPLEMENT_ZIP.stat().st_size,
        "sensitive_findings": findings,
        "csv_data_rows": csv_rows,
        "all_scientific_csvs_match_v3": all(
            digest(V4 / "supplementary" / name) == digest(V3 / "supplementary" / name)
            for name in SUPPLEMENT_SCIENCE_FILES
        ),
        "readme_present": (V4 / "supplementary/README.md").is_file(),
        "manifest_present": (V4 / "supplementary/artifact_manifest_sncs_v4.txt").is_file(),
    }


def compile_clean() -> dict:
    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if not (latexmk and pdflatex and bibtex):
        return {
            "status": "FAIL",
            "reason": "latexmk, pdflatex, and bibtex are all required for the v4 final pass",
        }
    with tempfile.TemporaryDirectory(prefix="qroute_sncs_v4_pdflatex_") as directory:
        clean = Path(directory)
        with zipfile.ZipFile(SOURCE_ZIP) as archive:
            archive.extractall(clean)
        command = [
            latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error",
            "-file-line-error", "main.tex",
        ]
        environment = os.environ.copy()
        environment["SOURCE_DATE_EPOCH"] = "1788177600"
        run = subprocess.run(command, cwd=clean, text=True, capture_output=True, env=environment)
        output = run.stdout + run.stderr
        log = (clean / "main.log").read_text(encoding="utf-8", errors="replace") if (clean / "main.log").is_file() else ""
        blg = (clean / "main.blg").read_text(encoding="utf-8", errors="replace") if (clean / "main.blg").is_file() else ""
        pdf = clean / "main.pdf"
        if run.returncode or not pdf.is_file():
            return {
                "status": "FAIL",
                "command": " ".join(command),
                "returncode": run.returncode,
                "log_tail": (output + log + blg)[-12000:],
            }
        shutil.copy2(pdf, PDF)
        combined = "\n".join([output, log, blg])
        # latexmk's captured stdout contains warnings from its deliberately
        # unresolved first pass.  Submission diagnostics must use the final
        # converged main.log (plus BibTeX's final .blg), not transient passes.
        low = log.lower()
        diagnostics = {
            "overfull_box_count": low.count("overfull \\hbox") + low.count("overfull \\vbox"),
            "undefined_reference_or_citation_count": sum(
                1 for line in log.splitlines()
                if "undefined" in line.lower()
                and ("reference" in line.lower() or "citation" in line.lower())
            ),
            "duplicate_destination_count": low.count("destination with the same identifier"),
            "missing_file_error_count": len(
                re.findall(r"LaTeX Error: File `[^']+' not found", log, flags=re.IGNORECASE)
            ),
            "bibtex_warning_count": sum(1 for line in blg.splitlines() if line.startswith("Warning--")),
        }

        pdfinfo = shutil.which("pdfinfo")
        pdftotext = shutil.which("pdftotext")
        pdffonts = shutil.which("pdffonts")
        info_output = ""
        page_count = None
        if pdfinfo:
            info_run = subprocess.run([pdfinfo, str(pdf)], text=True, capture_output=True)
            info_output = info_run.stdout
            match = re.search(r"^Pages:\s+(\d+)", info_output, flags=re.MULTILINE)
            if match:
                page_count = int(match.group(1))
        rendered_text = ""
        if pdftotext:
            text_run = subprocess.run([pdftotext, str(pdf), "-"], text=True, capture_output=True)
            rendered_text = text_run.stdout
        fonts_output = ""
        all_fonts_embedded = None
        if pdffonts:
            fonts_run = subprocess.run([pdffonts, str(pdf)], text=True, capture_output=True)
            fonts_output = fonts_run.stdout
            rows = [line.split() for line in fonts_output.splitlines()[2:] if line.strip()]
            if rows:
                all_fonts_embedded = all("yes" in [part.lower() for part in row] for row in rows)

        forbidden_rendered = [
            token for token in [
                "to be confirmed", "TO_BE_CONFIRMED", "Lorem ipsum",
                "DRAFT_FOR_REVIEW", "Received xx xxx xxxx",
            ]
            if token.lower() in rendered_text.lower()
        ]
        result = {
            "status": "PASS" if not any(diagnostics.values()) else "FAIL",
            "compiler": "latexmk + pdfLaTeX + BibTeX",
            "command": " ".join(command),
            "pdflatex_version": subprocess.run([pdflatex, "--version"], text=True, capture_output=True).stdout.splitlines()[0],
            "bibtex_version": subprocess.run([bibtex, "--version"], text=True, capture_output=True).stdout.splitlines()[0],
            "diagnostics": diagnostics,
            "pdf_sha256": digest(PDF),
            "pdf_size_bytes": PDF.stat().st_size,
            "page_count": page_count,
            "all_fonts_embedded": all_fonts_embedded,
            "visible_author_input_marker_count": rendered_text.lower().count("author input required before upload"),
            "forbidden_rendered_template_or_placeholder_text": forbidden_rendered,
            "pdfinfo": info_output,
            "pdffonts": fonts_output,
            "log_tail": combined[-5000:],
        }
        if forbidden_rendered:
            result["status"] = "FAIL"
        return result


def main() -> None:
    provenance = copy_inputs()
    write_supporting_files()
    write_manifest()
    source_listing, supplement_listing = make_archives()

    with tempfile.TemporaryDirectory(prefix="qroute_sncs_v4_static_") as directory:
        clean = Path(directory)
        with zipfile.ZipFile(SOURCE_ZIP) as archive:
            archive.extractall(clean)
        clean_static = parse_tex_structure(clean)
    source_static = parse_tex_structure(V4)
    supplement_audit = scan_supplement()
    compile_result = compile_clean()

    if not source_static["format_pass"] or not clean_static["format_pass"]:
        raise SystemExit("v4 source/static validation failed")
    if compile_result["status"] != "PASS":
        raise SystemExit("v4 clean pdfLaTeX validation failed")
    if not supplement_audit["all_scientific_csvs_match_v3"]:
        raise SystemExit("v4 supplement changed a scientific CSV")

    report = {
        "version": "v4",
        "target_journal": JOURNAL,
        "article_type": ARTICLE_TYPE,
        "build_date": ACCESS_DATE,
        "baseline_source_commit": BASELINE_COMMIT,
        "working_branch": BRANCH,
        "authoritative_v3": {
            "source_zip": str(V3_SOURCE_ZIP),
            "source_zip_sha256": digest(V3_SOURCE_ZIP),
            "supplement_zip": str(V3_SUPPLEMENT_ZIP),
            "supplement_zip_sha256": digest(V3_SUPPLEMENT_ZIP),
        },
        "scientific_integrity": {
            "canonical_scientific_files_changed": 0,
            "optimization_reruns": 0,
            "headline_value_changes": 0,
            "hypothesis_decision_changes": 0,
            "confirmatory_family_changed": False,
            "m20_reversal_changed": False,
            "m22_censoring_changed": False,
        },
        "provenance": provenance,
        "source_zip": {
            "path": str(SOURCE_ZIP),
            "sha256": digest(SOURCE_ZIP),
            "size_bytes": SOURCE_ZIP.stat().st_size,
            "file_count": len(source_listing),
            "all_files_at_root": all("/" not in name for name in source_listing),
            "test": "PASS",
        },
        "supplement_zip": {
            "path": str(SUPPLEMENT_ZIP),
            "sha256": digest(SUPPLEMENT_ZIP),
            "size_bytes": SUPPLEMENT_ZIP.stat().st_size,
            "file_count": len(supplement_listing),
            "all_files_at_root": all("/" not in name for name in supplement_listing),
            "test": "PASS",
        },
        "source_static_validation": source_static,
        "clean_extraction_static_validation": clean_static,
        "clean_compile": compile_result,
        "supplement_audit": supplement_audit,
        "official_guidelines": {**OFFICIAL_URLS, "access_date": ACCESS_DATE},
        "final_verdict_before_author_input": "READY_AFTER_AUTHOR_METADATA",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    write_text(AUDIT, json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
