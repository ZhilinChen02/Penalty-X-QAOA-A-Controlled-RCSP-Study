#!/usr/bin/env python3
"""Build and validate the SN Computer Science v3 submission package.

This is a publication-formatting build. It flattens the audited v2 manuscript,
copies presentation assets, and applies journal-specific front/back matter. It
does not run QAOA, change optimizer parameters, or modify canonical evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "overleaf"
VENDOR = ROOT / "paper_assets/springer_nature_latex_2024_12"
OUTPUT = ROOT / "submission/sn_computer_science_v3"
DIST = ROOT / "dist"
AUDIT = ROOT / "paper_audit"
ZIP_PATH = DIST / "Q-RouteDilution_SNCS_v3.zip"
SUPPLEMENT_ZIP_PATH = DIST / "Q-RouteDilution_SNCS_v3_supplementary.zip"
PDF_PATH = DIST / "Q-RouteDilution_SNCS_v3.pdf"

BASELINE_COMMIT = "4d1111f3661f4b2df852eec2b382555a63e434d2"
BRANCH = "paper-finalization-v3-sncs"
JOURNAL = "SN Computer Science"
ARTICLE_TYPE = "Original Research"
TEMPLATE_VERSION = "Springer Nature sn-jnl 3.1 (December 2024)"

BODY_SOURCES = [
    "sections/01_introduction.tex",
    "sections/02_problem.tex",
    "sections/03_methods.tex",
    "sections/04_optimizer_attribution.tex",
    "sections/05_objective_alignment.tex",
    "sections/06_heldout_results.tex",
    "sections/07_scaling.tex",
    "sections/08_theory.tex",
    "sections/09_related_work.tex",
    "sections/10_discussion.tex",
    "sections/11_limitations.tex",
    "sections/12_conclusion.tex",
]

APPENDIX_SOURCES = [
    "appendices/appendix_theory.tex",
    "appendices/appendix_tasks.tex",
    "appendices/appendix_optimization.tex",
    "appendices/appendix_statistics.tex",
    "appendices/appendix_scaling.tex",
    "appendices/appendix_artifact.tex",
]

FIGURE_MAP = {
    "fig01_experimental_concept.pdf": "Fig1.pdf",
    "fig02_dilution_scale_control.pdf": "Fig2.pdf",
    "fig03_optimizer_attribution.pdf": "Fig3.pdf",
    "fig04_objective_misalignment.pdf": "Fig4.pdf",
    "fig05_objective_discovery.pdf": "Fig5.pdf",
    "fig06_heldout_confirmation.pdf": "Fig6.pdf",
    "fig07_feasibility_optimality.pdf": "Fig7.pdf",
    "fig08_scaling_response.pdf": "Fig8.pdf",
    "fig09_theory_scope.pdf": "Fig9.pdf",
    "fig10_structure_cost_relocation.pdf": "Fig10.pdf",
    "fig11_finite_shot_endpoint_robustness.pdf": "Fig11.pdf",
}

CANONICAL_SOURCES = [
    "data/manifests/phase0_v2_dilution_stress.json",
    "results/phase0_v2_dilution_stress/summary.json",
    "results/phase1_pilot_v1/pilot_summary.json",
    "results/phase1_1_optimization_diagnostic/summary.json",
    "results/phase1_2_objective_alignment/summary.json",
    "results/phase2_confirmatory_v1/PREREGISTRATION.md",
    "results/phase2_confirmatory_v1/confirmatory_statistics.json",
    "results/phase3_scaling_v1/SCALING_MODEL_FREEZE.json",
    "results/phase3_scaling_v1/summary.json",
    "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv",
]

ABSTRACT_PLAIN = """Purpose: When shallow full-space Penalty-X quantum approximate optimization algorithm (QAOA) performs poorly on a sparse-feasible constrained problem, the loss may reflect representation-induced dilution, optimizer inadequacy, objective misalignment, or ansatz limitations. We separate these explanations in a controlled resource-constrained shortest-path study.

Methods: Exact-statevector experiments used a uniform plus-state, transverse X mixer, scale-controlled diagonal penalty Hamiltonian, and at most three alternating layers. Exact ansatz nesting diagnosed optimizer failures. We compared mean energy, expected penalty, exact feasibility control, and conditional value at risk over the lowest-energy 10% tail (CVaR-0.10). CVaR was selected on 56 discovery tasks across 10 graphs, then evaluated under a preregistered protocol on 84 tasks across 15 disjoint graphs.

Results: Nesting identified 29 certified optimizer failures in 168 comparisons; continuation repaired objective value in all 29 and improved feasibility gain in 27. In 82 comparisons, lower mean energy coincided with lower feasibility gain. On discovery, CVaR closed a median 97.9% of the capacity gap. Held-out CVaR improved graph-level feasibility compensation over mean energy by 0.3547 decades (one-sided lower bound 0.2374) and was non-inferior to capacity control at the frozen margin. Optimal-route probability increased on 80 of 84 tasks. Yet the CVaR-versus-mean-energy ordering reversed at size 20; size 22 was prospectively resource-censored.

Conclusion: In the tested setting, some depth failure is optimizer-induced and mean energy underuses feasible-concentration capacity. CVaR improves held-out feasible entry, but no global scaling law or quantum advantage follows."""

KEYWORDS = [
    "quantum approximate optimization algorithm",
    "resource-constrained shortest path",
    "constrained optimization",
    "feasible-space dilution",
    "conditional value at risk",
    "variational quantum algorithms",
]

AI_DISCLOSURE = r"""
\subsection{AI-assisted publication preparation}

An AI-assisted coding tool (OpenAI Codex, accessed August 2026) was used under
author supervision during publication finalization to implement deterministic
reconstruction, post-hoc endpoint-sampling, and formatting scripts; assist with
repository, claim, and citation audits; and edit prose. It did not generate or
modify the canonical primary experiment rows and did not rerun QAOA
optimization. The author remains responsible for verifying all generated code,
analyses, citations, and prose before submission.
""".strip()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def strip_tex_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def resolve_input(name: str, parent: Path) -> Path:
    relative = Path(name)
    if not relative.suffix:
        relative = relative.with_suffix(".tex")
    candidates = [SOURCE / relative, parent / relative]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file() and SOURCE.resolve() in resolved.parents:
            return resolved
    raise FileNotFoundError(f"cannot resolve manuscript input {name!r} from {parent}")


def expand_file(path: Path, stack: tuple[Path, ...] = ()) -> str:
    resolved = path.resolve()
    if resolved in stack:
        chain = " -> ".join(item.name for item in (*stack, resolved))
        raise RuntimeError(f"cyclic LaTeX input chain: {chain}")
    text = resolved.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        child = resolve_input(match.group(1), resolved.parent)
        return expand_file(child, (*stack, resolved))

    expanded = re.sub(r"\\input\{([^}]+)\}", replace, text)
    relative = resolved.relative_to(SOURCE.resolve()).as_posix()
    return f"% BEGIN FLATTENED SOURCE: {relative}\n{expanded.rstrip()}\n% END FLATTENED SOURCE: {relative}"


def journalize(text: str) -> str:
    for old, new in FIGURE_MAP.items():
        text = text.replace(old, new)
    text = text.replace(
        "The Overleaf directory is self-contained for compilation but intentionally",
        "The SN Computer Science v3 source archive is self-contained for compilation but intentionally",
    )
    text = text.replace(
        "Because no TeX\ncompiler is installed in the build environment, the package receives static\nbrace, environment, input, label/reference, citation, and missing-asset checks;\nthe clean package should additionally be compiled on Overleaf before\nsubmission.",
        "The deterministic build performs static brace, environment, label/reference,\ncitation, and missing-asset checks. A final pdfLaTeX/BibTeX compilation and\nrendered-page inspection are still required before submission.",
    )
    text = text.replace(
        "repository/DOI publication, and journal-specific formatting also require\nauthor confirmation.",
        "repository/DOI publication, journal-system metadata, and final rendered-layout\napproval also require author confirmation.",
    )
    text = text.replace(
        "repository/DOI URL, and final venue\nformatting.",
        "repository/DOI URL, and final journal-system metadata.",
    )
    text = text.replace(
        r"supplementary/artifact\_manifest.txt",
        r"artifact\_manifest\_sncs\_v3.txt",
    )
    text = text.replace(r"supplementary/claim\_evidence\_summary.csv", r"claim\_evidence\_summary.csv")
    text = text.replace(r"supplementary/numeric\_audit.csv", r"numeric\_audit.csv")
    text = text.replace(r"supplementary/full\_failure\_census.csv", r"full\_failure\_census.csv")
    text = text.replace(r"supplementary/task\_strata.csv", r"task\_strata.csv")
    return text


def abstract_tex() -> str:
    paragraphs = []
    for paragraph in ABSTRACT_PLAIN.split("\n\n"):
        label, body = paragraph.split(":", 1)
        body = body.strip()
        body = body.replace("CVaR-0.10", r"CVaR-0.10")
        paragraphs.append(rf"\textbf{{{label}:}} {body}")
    return "\n\n".join(paragraphs)


def build_main_tex() -> str:
    bodies = []
    for relative in BODY_SOURCES:
        expanded = expand_file(SOURCE / relative)
        if relative == "sections/09_related_work.tex":
            expanded = expanded.replace(r"\paragraph{", r"\subsection{")
        bodies.append(expanded)
        if relative == "sections/03_methods.tex":
            bodies.append(AI_DISCLOSURE)
    appendices = []
    for relative in APPENDIX_SOURCES:
        expanded = expand_file(SOURCE / relative)
        if relative == "appendices/appendix_statistics.tex":
            expanded = expanded.replace(r"\paragraph{", r"\subsubsection{")
        appendices.append(expanded)
    body_text = journalize("\n\n".join(bodies))
    appendix_text = journalize("\n\n".join(appendices))

    return rf"""% SN Computer Science submission version v3
% Derived deterministically from the audited manuscript; do not edit generated
% scientific values here. Run paper_scripts/build_sncs_submission_v3.py.
\documentclass[pdflatex,sn-mathphys-num]{{sn-jnl}}

\usepackage{{graphicx}}
\usepackage{{amsmath,amssymb,mathtools}}
\usepackage{{booktabs,tabularx,array,multirow,longtable}}
\usepackage{{xcolor}}
\usepackage{{microtype}}
\usepackage{{siunitx}}
\usepackage{{enumitem}}
\usepackage[nameinlink,noabbrev]{{cleveref}}

\graphicspath{{{{./}}}}
\sisetup{{detect-all,group-separator={{,}},group-minimum-digits=4}}
\setlist{{nosep,leftmargin=*}}
\setlength{{\emergencystretch}}{{2em}}

\theoremstyle{{thmstyleone}}
\newtheorem{{theorem}}{{Theorem}}
\newtheorem{{proposition}}[theorem]{{Proposition}}
\newtheorem{{lemma}}[theorem]{{Lemma}}
\newtheorem{{corollary}}[theorem]{{Corollary}}
\theoremstyle{{thmstylethree}}
\newtheorem{{definition}}[theorem]{{Definition}}
\theoremstyle{{thmstyletwo}}
\newtheorem{{remark}}[theorem]{{Remark}}

\newcommand{{\pfeas}}{{P_{{\mathrm{{feas}}}}}}
\newcommand{{\popt}}{{P_{{\mathrm{{opt}}}}}}
\newcommand{{\pcond}}{{P_{{\mathrm{{opt}}\mid\mathrm{{feas}}}}}}
\newcommand{{\gfeas}}{{G_{{\mathrm{{feas}}}}}}
\newcommand{{\phistate}}{{\phi_{{\mathrm{{state}}}}}}
\newcommand{{\phipath}}{{\phi_{{\mathrm{{path}}}}}}
\newcommand{{\F}}{{\mathcal{{F}}}}
\newcommand{{\E}}{{\mathbb{{E}}}}
\newcommand{{\R}}{{\mathbb{{R}}}}
\newcommand{{\supp}}{{\operatorname{{supp}}}}
\newcommand{{\cvar}}{{\operatorname{{CVaR}}}}
\newcommand{{\ind}}{{\mathbf{{1}}}}

\begin{{document}}

\title[Feasible-space dilution in shallow Penalty-X QAOA]{{Feasible-Space Dilution and Objective Alignment in Shallow QAOA: A Controlled RCSP Study}}

\author*[1]{{\fnm{{Zhilin}} \sur{{Chen}}}}\email{{Corresponding author e-mail to be confirmed}}

\affil*[1]{{\orgdiv{{Department to be confirmed}}, \orgname{{Institution to be confirmed}}, \orgaddress{{\city{{City to be confirmed}}, \country{{Country to be confirmed}}}}}}

\abstract{{{abstract_tex()}}}

\keywords{{{", ".join(KEYWORDS)}}}

\maketitle

{body_text}

\backmatter

\bmhead{{Supplementary information}}

The accompanying supplementary package includes a claim--evidence summary, a
numerical audit, a retained failure census, and task-stratum metadata. The post-hoc finite-shot
endpoint outputs and the deterministic reproduction package are prepared for
repository deposit; the public repository and DOI must be inserted before
submission.

\bmhead{{Acknowledgements}}

Acknowledgements to be confirmed by the author before submission.

\section*{{Statements and Declarations}}

\bmhead{{Funding}}

Funding information to be confirmed by the author before submission.

\bmhead{{Competing interests}}

Competing-interest statement to be confirmed by the author before submission.

\bmhead{{Ethics approval}}

Not applicable. This computational study uses synthetic graph instances and
does not involve human participants, human data, or animals.

\bmhead{{Consent to participate}}

Not applicable.

\bmhead{{Consent for publication}}

Not applicable.

\bmhead{{Data availability}}

The canonical result rows, frozen manifests, and paper-level reconstruction
outputs are prepared for repository deposit. The final public repository URL
and persistent identifier must be inserted by the author before submission.

\bmhead{{Materials availability}}

Not applicable.

\bmhead{{Code availability}}

The deterministic paper-rebuild and reproduction scripts are prepared for
repository deposit. The final public repository URL and persistent identifier
must be inserted by the author before submission.

\bmhead{{Author contributions}}

Proposed CRediT statement, subject to author confirmation: Zhilin Chen:
Conceptualization, methodology, software, validation, formal analysis,
investigation, data curation, visualization, writing---original draft, and
writing---review and editing.

\begin{{appendices}}

% Keep appendix hyperlink anchors unique after the Springer class resets
% figure, table, and equation counters.
\renewcommand{{\theHfigure}}{{appendix.\Alph{{section}}.\arabic{{figure}}}}
\renewcommand{{\theHtable}}{{appendix.\Alph{{section}}.\arabic{{table}}}}
\renewcommand{{\theHequation}}{{appendix.\Alph{{section}}.\arabic{{equation}}}}

{appendix_text}

\end{{appendices}}

\bibliography{{references}}

\end{{document}}
"""


def write_supporting_files() -> None:
    readme = f"""# SN Computer Science submission package v3

Target journal: **{JOURNAL}**  
Article type: **{ARTICLE_TYPE}**  
Template: **{TEMPLATE_VERSION}**

`main.tex` is a flat, single-document Springer Nature source file. It contains
no `\\input` commands. Figures are separate vector PDFs named `Fig1.pdf`
through `Fig11.pdf`. The bibliography uses the numeric
`sn-mathphys-num` style supplied by `sn-jnl.cls`.

## Compile

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

`dist/Q-RouteDilution_SNCS_v3.zip` is the flat LaTeX source upload: all
compilation files are at archive root, as required by Springer Nature's LaTeX
submission guidance. Upload `cover_letter.md` separately after resolving its
confirmation fields. The separately generated
`dist/Q-RouteDilution_SNCS_v3_supplementary.zip` contains the CSV provenance
files and should be designated as supplementary material rather than manuscript
source.

## Before upload

Resolve every item marked `TO BE CONFIRMED` in `SUBMISSION_CHECKLIST.md`. The
visible placeholders in the title page and Statements and Declarations are
deliberate: no affiliation, e-mail, funding, competing-interest, or repository
fact has been invented.

Official journal instructions:
<https://link.springer.com/journal/42979/submission-guidelines>
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")

    checklist = """# SN Computer Science v3 submission checklist

## Format checks completed

- [x] Springer Nature `sn-jnl` template, version 3.1 (December 2024).
- [x] One flat `main.tex`; no `\\input` commands.
- [x] Numeric square-bracket citation style (`sn-mathphys-num`).
- [x] Structured abstract with Purpose, Methods, Results, and Conclusion.
- [x] Abstract length within the journal's 150--250-word range.
- [x] Six keywords.
- [x] No more than three displayed heading levels.
- [x] Figures placed in the body and supplied as separate vector PDFs.
- [x] Statements and Declarations headings included.
- [x] Scientific values inherited from the independently rebuilt manuscript.
- [x] m=20 reversal and m=22 resource censoring remain visible.
- [x] Post-hoc finite-shot analysis remains explicitly non-confirmatory.

## Author-supplied items required before upload

- [ ] Confirm full author list, order, and corresponding author.
- [ ] Replace the corresponding-author e-mail placeholder.
- [ ] Replace department, institution, city, and country placeholders.
- [ ] Add ORCID identifier(s), if available.
- [ ] Confirm or replace the proposed CRediT author-contribution statement.
- [ ] Supply acknowledgements, or replace the placeholder with “Not applicable.”
- [ ] Supply the funding statement, including grant numbers, or state “No funding was received.”
- [ ] Supply the competing-interest statement.
- [ ] Publish the data/code repository and insert its persistent URL/DOI.
- [ ] Review and approve the AI-assisted publication-preparation disclosure.
- [ ] Confirm exclusive submission, author approval, and permission status in the cover letter.
- [ ] Select the final subject classification in the Editorial Manager form.
- [ ] Confirm whether Figure 11 and supporting CSV files are uploaded as supplementary material.

## Human-only scientific checks that remain open

- [ ] Independent human proof review.
- [ ] Independent prior-art/novelty judgment.
- [ ] Independent external reproduction.

## Final production checks

- [ ] Compile with pdfLaTeX and BibTeX in a clean TeX environment.
- [ ] Resolve any undefined reference/citation or bibliography warning.
- [ ] Inspect overfull boxes, table width, font embedding, and figure legibility.
- [ ] Confirm all figure lettering remains readable at journal column width.
- [ ] Run the submission PDF through the journal portal's generated-PDF preview.
"""
    (OUTPUT / "SUBMISSION_CHECKLIST.md").write_text(checklist, encoding="utf-8")

    cover = """# Draft cover letter — SN Computer Science

Dear Editors-in-Chief,

Please consider the manuscript “Feasible-Space Dilution and Objective
Alignment in Shallow QAOA: A Controlled RCSP Study” for publication as an
Original Research article in *SN Computer Science*.

The manuscript asks a focused attribution question: when shallow full-space
Penalty-X QAOA performs poorly on a constrained problem with a sparse feasible
set, how much of the loss is attributable to representation-induced dilution,
classical optimizer inadequacy, objective misalignment, and remaining ansatz
limitations? It answers this question in a controlled resource-constrained
shortest-path benchmark using exact statevectors, a uniform plus-state initial
condition, a transverse X mixer, and a scale-controlled diagonal penalty
Hamiltonian at alternating-layer counts no greater than three.

The principal contribution is not a new CVaR objective or a general claim
about QAOA. It is a controlled attribution design that holds the cost
Hamiltonian and ansatz fixed, certifies a subset of optimizer failures through
exact ansatz nesting, uses direct feasibility optimization only as a
mechanistic capacity control, and prospectively confirms a discovery-selected
CVaR-0.10 objective on held-out base graphs. The manuscript also reports the
negative scaling evidence prominently: the earlier CVaR-versus-mean-energy
ordering reverses at size 20, size 22 is resource-censored, and no global
scaling law or quantum-advantage claim is made.

The work fits the journal's quantum-computing and combinatorial-optimization
scope and may be of interest to readers studying variational quantum
algorithms, constrained optimization, and reproducible empirical methodology.

[AUTHOR CONFIRMATION REQUIRED: This manuscript is original, is not under
consideration elsewhere, and has been approved by every author.]

[AUTHOR CONFIRMATION REQUIRED: competing interests, funding, permissions, and
public data/code repository statement.]

Thank you for your consideration.

Sincerely,

Zhilin Chen  
[Affiliation to be confirmed]  
[Corresponding-author e-mail to be confirmed]
"""
    (OUTPUT / "cover_letter.md").write_text(cover, encoding="utf-8")

    provenance = (VENDOR / "TEMPLATE_PROVENANCE.md").read_text(encoding="utf-8")
    (OUTPUT / "TEMPLATE_PROVENANCE.md").write_text(provenance, encoding="utf-8")


def copy_assets() -> None:
    shutil.copy2(SOURCE / "references.bib", OUTPUT / "references.bib")
    shutil.copy2(VENDOR / "sn-jnl.cls", OUTPUT / "sn-jnl.cls")
    shutil.copy2(VENDOR / "sn-mathphys-num.bst", OUTPUT / "sn-mathphys-num.bst")
    for old, new in FIGURE_MAP.items():
        source = SOURCE / "figures" / old
        if not source.is_file():
            raise FileNotFoundError(f"missing manuscript figure: {source}")
        shutil.copy2(source, OUTPUT / new)

    supplementary = OUTPUT / "supplementary"
    supplementary.mkdir(exist_ok=True)
    for source in sorted((SOURCE / "supplementary").glob("*.csv")):
        shutil.copy2(source, supplementary / source.name)


def write_metadata() -> None:
    metadata = {
        "version": "v3",
        "target_journal": JOURNAL,
        "article_type": ARTICLE_TYPE,
        "title": "Feasible-Space Dilution and Objective Alignment in Shallow QAOA: A Controlled RCSP Study",
        "short_title": "Feasible-space dilution in shallow Penalty-X QAOA",
        "abstract_word_count": len(re.findall(r"[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*", ABSTRACT_PLAIN)),
        "keywords": KEYWORDS,
        "template": TEMPLATE_VERSION,
        "citation_style": "sn-mathphys-num",
        "suggested_scope": [
            "Quantum Computing",
            "Mathematical Programming and Combinatorial Optimization",
            "Modeling and Simulation",
        ],
        "corresponding_author": "Zhilin Chen",
        "corresponding_email": "TO_BE_CONFIRMED",
        "affiliation": "TO_BE_CONFIRMED",
        "repository_url_or_doi": "TO_BE_CONFIRMED",
        "scientific_scope": "controlled full-space Penalty-X QAOA RCSP attribution study",
        "confirmatory_family_changed": False,
        "canonical_experiments_rerun": False,
    }
    (OUTPUT / "submission_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_manifest() -> None:
    manifest = OUTPUT / "supplementary/artifact_manifest_sncs_v3.txt"
    lines = [
        "Q-RouteDilution SN Computer Science v3 artifact manifest",
        f"baseline_source_commit {BASELINE_COMMIT}",
        f"working_branch {BRANCH}",
        "stage PUBLICATION_FINALIZATION_V3_SNCS",
        "canonical_experiments_rerun NO",
        "confirmatory_family_changed NO",
        "posthoc_finite_shot_role POSTHOC_ROBUSTNESS_ONLY",
        "hash_algorithm SHA256",
        "",
        "[included_submission_files]",
        "# This manifest omits its own digest.",
    ]
    for path in sorted(item for item in OUTPUT.rglob("*") if item.is_file() and item != manifest):
        lines.append(f"{digest(path)}  {path.relative_to(OUTPUT).as_posix()}")
    lines.extend(["", "[selected_canonical_source_files]"])
    for relative in CANONICAL_SOURCES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"canonical source missing: {relative}")
        lines.append(f"{digest(path)}  {relative}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_source_tree(root: Path) -> dict:
    main = (root / "main.tex").read_text(encoding="utf-8")
    clean = strip_tex_comments(main)
    bib = (root / "references.bib").read_text(encoding="utf-8")

    labels = re.findall(r"\\label\{([^}]+)\}", clean)
    refs: set[str] = set()
    for group in re.findall(r"\\(?:ref|eqref|cref|Cref)\{([^}]+)\}", clean):
        refs.update(item.strip() for item in group.split(","))
    cited: set[str] = set()
    for group in re.findall(r"\\cite\w*\s*\{([^}]+)\}", clean):
        cited.update(item.strip() for item in group.split(","))
    bib_keys = set(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", bib))

    begins: dict[str, int] = {}
    ends: dict[str, int] = {}
    for name in re.findall(r"\\begin\{([^}]+)\}", clean):
        begins[name] = begins.get(name, 0) + 1
    for name in re.findall(r"\\end\{([^}]+)\}", clean):
        ends[name] = ends.get(name, 0) + 1
    environment_mismatch = {
        name: begins.get(name, 0) - ends.get(name, 0)
        for name in sorted(set(begins) | set(ends))
        if begins.get(name, 0) != ends.get(name, 0)
    }

    missing_figures = []
    for name in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", clean):
        if not (root / name).is_file():
            missing_figures.append(name)

    heading_counts = {
        "section": len(re.findall(r"\\section\*?\{", clean)),
        "subsection": len(re.findall(r"\\subsection\*?\{", clean)),
        "subsubsection": len(re.findall(r"\\subsubsection\*?\{", clean)),
        "paragraph": len(re.findall(r"\\paragraph\*?\{", clean)),
    }
    required_abstract_labels = ["Purpose", "Methods", "Results", "Conclusion"]
    declaration_heads = [
        "Funding", "Competing interests", "Ethics approval",
        "Consent to participate", "Consent for publication", "Data availability",
        "Materials availability", "Code availability", "Author contributions",
    ]
    placeholders = sorted(set(re.findall(
        r"[^\n]*(?:to be confirmed|TO_BE_CONFIRMED|must be inserted|subject to author confirmation)[^\n]*",
        main,
        flags=re.IGNORECASE,
    )))
    absolute_paths = []
    text_suffixes = {".tex", ".bib", ".md", ".json", ".csv", ".txt"}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_suffixes:
            text = path.read_text(encoding="utf-8", errors="replace")
            if "/home/" in text or "file://" in text:
                absolute_paths.append(path.relative_to(root).as_posix())

    result = {
        "target_journal": JOURNAL,
        "article_type": ARTICLE_TYPE,
        "template_version": TEMPLATE_VERSION,
        "main_tex_single_file": len(list(root.glob("*.tex"))) == 1,
        "documentclass_correct": r"\documentclass[pdflatex,sn-mathphys-num]{sn-jnl}" in main,
        "input_command_count": len(re.findall(r"\\input\{", clean)),
        "abstract_word_count": len(re.findall(r"[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*", ABSTRACT_PLAIN)),
        "abstract_word_limit": [150, 250],
        "abstract_labels_present": {
            label: rf"\textbf{{{label}:}}" in main for label in required_abstract_labels
        },
        "keyword_count": len(KEYWORDS),
        "keywords": KEYWORDS,
        "heading_counts": heading_counts,
        "displayed_heading_levels": 3 if heading_counts["subsubsection"] else 2,
        "labels_total": len(labels),
        "duplicate_labels": sorted({label for label in labels if labels.count(label) > 1}),
        "references_total": len(refs),
        "missing_references": sorted(refs - set(labels)),
        "citations_total": len(cited),
        "unresolved_citations": sorted(cited - bib_keys),
        "environment_mismatch": environment_mismatch,
        "missing_figures": sorted(set(missing_figures)),
        "figure_count": len(re.findall(r"\\includegraphics", clean)),
        "declaration_heads_present": {
            heading: rf"\bmhead{{{heading}}}" in main for heading in declaration_heads
        },
        "ai_assistance_disclosed_in_methods": "AI-assisted publication preparation" in main,
        "absolute_paths": sorted(absolute_paths),
        "symlinks": sorted(
            path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_symlink()
        ),
        "author_placeholders": placeholders,
        "vendor_hashes": {
            "sn-jnl.cls": digest(root / "sn-jnl.cls"),
            "sn-mathphys-num.bst": digest(root / "sn-mathphys-num.bst"),
        },
    }
    result["format_pass"] = all(
        [
            result["main_tex_single_file"],
            result["documentclass_correct"],
            result["input_command_count"] == 0,
            150 <= result["abstract_word_count"] <= 250,
            all(result["abstract_labels_present"].values()),
            4 <= result["keyword_count"] <= 6,
            result["displayed_heading_levels"] <= 3,
            result["heading_counts"]["paragraph"] == 0,
            not result["duplicate_labels"],
            not result["missing_references"],
            not result["unresolved_citations"],
            not result["environment_mismatch"],
            not result["missing_figures"],
            all(result["declaration_heads_present"].values()),
            result["ai_assistance_disclosed_in_methods"],
            not result["absolute_paths"],
            not result["symlinks"],
            result["vendor_hashes"]["sn-jnl.cls"]
            == "36d0c3273a59d48dc6a9c7b080dfa1ec50dc10229d8751568d1f2e490ffa5ecc",
            result["vendor_hashes"]["sn-mathphys-num.bst"]
            == "b3a7c7fbcc1e7f9619de634fcea2f5bb7a245818a5942bc576e40ea001633332",
        ]
    )
    result["submission_ready"] = result["format_pass"] and not placeholders
    return result


def write_deterministic_zip(zip_path: Path, files: list[Path], base: Path) -> list[str]:
    DIST.mkdir(exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    listing = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            relative = path.relative_to(base).as_posix()
            listing.append(relative)
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 31, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return listing


def make_archives() -> tuple[list[str], list[str]]:
    source_names = {
        "main.tex", "references.bib", "sn-jnl.cls", "sn-mathphys-num.bst",
        *(f"Fig{index}.pdf" for index in range(1, 12)),
    }
    source_files = [OUTPUT / name for name in sorted(source_names)]
    missing = [str(path) for path in source_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"source archive inputs missing: {missing}")
    source_listing = write_deterministic_zip(ZIP_PATH, source_files, OUTPUT)

    supplement_root = OUTPUT / "supplementary"
    supplement_files = sorted(path for path in supplement_root.iterdir() if path.is_file())
    supplement_listing = write_deterministic_zip(
        SUPPLEMENT_ZIP_PATH, supplement_files, supplement_root
    )
    return source_listing, supplement_listing


def compile_if_available(clean_root: Path) -> dict:
    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    tectonic = shutil.which("tectonic")
    if not latexmk and not pdflatex and not tectonic:
        if PDF_PATH.exists():
            PDF_PATH.unlink()
        return {
            "status": "LATEX_COMPILER_NOT_AVAILABLE",
            "compiler": "",
            "required_command": "pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex",
        }

    if latexmk:
        command = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
        run = subprocess.run(command, cwd=clean_root, text=True, capture_output=True)
        output = run.stdout + run.stderr
        compiler = "latexmk -pdf"
    elif pdflatex and bibtex:
        commands = [
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            [bibtex, "main"],
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        ]
        output = ""
        return_code = 0
        for command in commands:
            run = subprocess.run(command, cwd=clean_root, text=True, capture_output=True)
            output += run.stdout + run.stderr
            if run.returncode:
                return_code = run.returncode
                break
        compiler = "pdflatex+bibtex"
        run = subprocess.CompletedProcess(commands[-1], return_code, output, "")
    elif pdflatex:
        return {"status": "FAIL", "compiler": "pdflatex without BibTeX", "log_tail": "BibTeX unavailable"}
    else:
        command = [tectonic, "--keep-logs", "--keep-intermediates", "main.tex"]
        run = subprocess.run(command, cwd=clean_root, text=True, capture_output=True)
        output = run.stdout + run.stderr
        compiler = "tectonic fallback"

    pdf = clean_root / "main.pdf"
    if run.returncode or not pdf.is_file():
        return {"status": "FAIL", "compiler": compiler, "log_tail": output[-8000:]}
    shutil.copy2(pdf, PDF_PATH)
    warnings = [line for line in output.splitlines() if any(
        token in line for token in ("Warning", "Overfull", "Underfull", "undefined")
    )]
    lowered_output = output.lower()
    diagnostics = {
        "overfull_box_count": lowered_output.count("overfull \\hbox")
        + lowered_output.count("overfull \\vbox"),
        "underfull_box_count": lowered_output.count("underfull \\hbox")
        + lowered_output.count("underfull \\vbox"),
        "undefined_reference_or_citation_count": sum(
            1
            for line in output.splitlines()
            if "undefined" in line.lower()
            and ("reference" in line.lower() or "citation" in line.lower())
        ),
        "duplicate_destination_count": lowered_output.count(
            "destination with the same identifier"
        ),
    }
    return {
        "status": "PASS",
        "compiler": compiler,
        "pdf_path": str(PDF_PATH),
        "pdf_sha256": digest(PDF_PATH),
        "pdf_size_bytes": PDF_PATH.stat().st_size,
        "pdflatex_final_check_still_required": compiler == "tectonic fallback",
        "diagnostics": diagnostics,
        "warnings": warnings[-100:],
        "log_tail": output[-3000:],
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "main.tex").write_text(build_main_tex(), encoding="utf-8")
    copy_assets()
    write_supporting_files()
    write_metadata()
    write_manifest()

    validation = validate_source_tree(OUTPUT)
    if not validation["format_pass"]:
        raise SystemExit(f"SN Computer Science source validation failed: {validation}")

    listing, supplement_listing = make_archives()
    with zipfile.ZipFile(ZIP_PATH) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise SystemExit(f"corrupt ZIP entry: {corrupt}")
    with zipfile.ZipFile(SUPPLEMENT_ZIP_PATH) as archive:
        supplement_corrupt = archive.testzip()
        if supplement_corrupt:
            raise SystemExit(f"corrupt supplementary ZIP entry: {supplement_corrupt}")

    with tempfile.TemporaryDirectory(prefix="qroute_sncs_v3_") as temp:
        clean_root = Path(temp)
        with zipfile.ZipFile(ZIP_PATH) as archive:
            archive.extractall(clean_root)
        clean_validation = validate_source_tree(clean_root)
        compile_result = compile_if_available(clean_root)
        if not clean_validation["format_pass"]:
            raise SystemExit(f"clean SNCS archive validation failed: {clean_validation}")
        if compile_result["status"] == "FAIL":
            raise SystemExit(f"clean compilation failed: {compile_result.get('log_tail', '')}")

    report = {
        "baseline_source_commit": BASELINE_COMMIT,
        "working_branch": BRANCH,
        "target_journal": JOURNAL,
        "article_type": ARTICLE_TYPE,
        "source_directory": str(OUTPUT),
        "zip_path": str(ZIP_PATH),
        "zip_sha256": digest(ZIP_PATH),
        "zip_size_bytes": ZIP_PATH.stat().st_size,
        "zip_file_count": len(listing),
        "zip_all_files_at_root": all("/" not in name for name in listing),
        "zip_test": "PASS",
        "supplement_zip_path": str(SUPPLEMENT_ZIP_PATH),
        "supplement_zip_sha256": digest(SUPPLEMENT_ZIP_PATH),
        "supplement_zip_size_bytes": SUPPLEMENT_ZIP_PATH.stat().st_size,
        "supplement_zip_file_count": len(supplement_listing),
        "supplement_zip_all_files_at_root": all("/" not in name for name in supplement_listing),
        "supplement_zip_test": "PASS",
        "source_validation": validation,
        "clean_extraction_validation": clean_validation,
        "clean_compile": compile_result,
        "canonical_experiments_rerun": False,
        "confirmatory_family_changed": False,
    }
    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "sncs_v3_validation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
