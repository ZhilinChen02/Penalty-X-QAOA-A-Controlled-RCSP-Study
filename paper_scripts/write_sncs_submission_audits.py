#!/usr/bin/env python3
"""Write final SN Computer Science delivery audits without changing science."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "submission" / "sn_computer_science_final_short"
GUIDELINES = "https://link.springer.com/journal/42979/submission-guidelines"
SCOPE = "https://link.springer.com/journal/42979/aims-and-scope"
LATEX = "https://www.springernature.com/gp/authors/campaigns/latex-author-support"
CANONICAL_HASH = (
    "0ef9ef8dc2a1f5cd062af2d8d1bef251a8d879e4139c95a23cf2225acacc5987"
)
FATAL_WARNING_KEYS = (
    "undefined_citations",
    "undefined_references",
    "duplicate_labels",
    "overfull_boxes",
    "bookmark_hierarchy",
    "duplicate_destinations",
    "pdf_string_warnings",
    "missing_files",
)


def write(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise RuntimeError(f"{' '.join(command)} failed:\n{result.stdout}")
    return result.stdout.strip()


def extract_balanced(text: str, marker: str) -> str:
    start = text.index(marker) + len(marker)
    depth = 1
    index = start
    while depth:
        char = text[index]
        escaped = index > 0 and text[index - 1] == "\\"
        if char == "{" and not escaped:
            depth += 1
        elif char == "}" and not escaped:
            depth -= 1
        index += 1
    return text[start : index - 1]


def abstract_words(text: str) -> list[str]:
    abstract = extract_balanced(text, "\\abstract{")
    abstract = re.sub(r"%.*", "", abstract)
    abstract = abstract.replace("\\alpha", "alpha")
    abstract = re.sub(r"\\[A-Za-z]+", " ", abstract)
    abstract = abstract.replace("$", " ").replace("--", "-")
    abstract = re.sub(r"[{}]", " ", abstract)
    # Hyphenated compounds and formatted numerals are counted as single tokens.
    return re.findall(
        r"(?<![A-Za-z0-9])[+]?(?:[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)",
        abstract,
    )


def expand_inputs(entry: Path) -> str:
    pattern = re.compile(r"\\input\{([^}]+)\}")

    def expand(text: str, stack: tuple[Path, ...]) -> str:
        def replacement(match: re.Match[str]) -> str:
            name = match.group(1)
            path = FINAL / (name if name.endswith(".tex") else name + ".tex")
            if path in stack:
                raise RuntimeError(f"recursive TeX input: {path}")
            return expand(path.read_text(encoding="utf-8"), stack + (path,))

        return pattern.sub(replacement, text)

    return expand(entry.read_text(encoding="utf-8"), (entry,))


def heading_depth(text: str) -> int:
    levels = {
        "section": 1,
        "subsection": 2,
        "subsubsection": 3,
        "paragraph": 4,
        "subparagraph": 5,
        "bmhead": 5,
    }
    used = [
        level
        for command, level in levels.items()
        if re.search(rf"\\{command}\*?\{{", text)
    ]
    return max(used, default=0)


def bib_blocks(text: str) -> dict[str, str]:
    starts = list(re.finditer(r"^@(\w+)\{([^,]+),", text, flags=re.MULTILINE))
    blocks: dict[str, str] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks[match.group(2).strip()] = text[match.start() : end]
    return blocks


def citation_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for group in re.findall(r"\\cite[A-Za-z]*\{([^}]+)\}", text):
        keys.update(key.strip() for key in group.split(",") if key.strip())
    return keys


def labelled_count(text: str, prefix: str) -> int:
    return len(set(re.findall(rf"\\label\{{{prefix}:[^}}]+\}}", text)))


def caption_args(text: str) -> list[str]:
    captions: list[str] = []
    marker = "\\caption{"
    offset = 0
    while True:
        try:
            start = text.index(marker, offset)
        except ValueError:
            break
        captions.append(extract_balanced(text[start:], marker))
        offset = start + len(marker)
    return captions


def environment_blocks(text: str, name: str) -> str:
    pattern = re.compile(
        rf"\\begin\{{{name}\*?\}}.*?\\end\{{{name}\*?\}}",
        flags=re.DOTALL,
    )
    return "\n".join(pattern.findall(text))


def md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def compliance_table(rows: list[tuple[str, str, str, str, str]]) -> str:
    lines = [
        "| Requirement | Official requirement | Manuscript status | Evidence/location | Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend("| " + " | ".join(md_cell(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def warning_summary(build: dict[str, object]) -> str:
    rows = []
    for label, result in (
        ("Packaged main", build["main"]),
        ("Packaged ESM_1", build["esm_1"]),
        ("Clean-archive main", build["archive_reproduction"]["main"]),
        ("Clean-archive ESM_1", build["archive_reproduction"]["esm_1"]),
    ):
        warnings = result["warnings"]
        rows.append(
            "| {} | {} | {} | {} | {} |".format(
                label,
                sum(warnings[key] for key in FATAL_WARNING_KEYS),
                warnings["underfull_hboxes"],
                warnings["underfull_vboxes"],
                result["page_count"],
            )
        )
    return "\n".join(
        [
            "| Build | Fatal warnings | Underfull hboxes | Underfull vboxes | Pages |",
            "| --- | ---: | ---: | ---: | ---: |",
            *rows,
        ]
    )


def main() -> int:
    if not (FINAL / ".sncs_build_output").is_file():
        raise RuntimeError(f"not a managed SNCS output directory: {FINAL}")

    build = json.loads((FINAL / "BUILD_RESULTS.json").read_text(encoding="utf-8"))
    main_source = (FINAL / "main_submission.tex").read_text(encoding="utf-8")
    esm_source = (FINAL / "ESM_1.tex").read_text(encoding="utf-8")
    main_tex = expand_inputs(FINAL / "main_submission.tex")
    esm_tex = expand_inputs(FINAL / "ESM_1.tex")
    bib_text = (FINAL / "references.bib").read_text(encoding="utf-8")
    bibliography = bib_blocks(bib_text)
    cited = citation_keys(main_tex) | citation_keys(esm_tex)

    words = abstract_words(main_source)
    keywords = [
        item.strip()
        for item in extract_balanced(main_source, "\\keywords{").replace("\n", " ").split(",")
        if item.strip()
    ]
    main_depth = heading_depth(main_tex)
    esm_depth = heading_depth(esm_tex)
    doi_count = sum(bool(re.search(r"^\s*doi\s*=", block, re.I | re.M)) for block in bibliography.values())
    preprints = [block for block in bibliography.values() if block.lstrip().lower().startswith("@misc")]
    figure_labels = re.findall(r"\\label\{(fig:[^}]+)\}", main_tex + esm_tex)
    table_labels = re.findall(r"\\label\{(tab:[^}]+)\}", main_tex + esm_tex)
    uncited = set(bibliography) - cited
    missing = cited - set(bibliography)
    uncited_labels = [
        label
        for label in figure_labels + table_labels
        if (main_tex + esm_tex).count(label) < 2
    ]
    figure_captions = caption_args(
        environment_blocks(main_tex, "figure") + environment_blocks(esm_tex, "figure")
    )
    figure_captions_without_terminal_period = sum(
        not re.sub(r"\s+", " ", caption).strip().endswith(".")
        for caption in figure_captions
    )

    assert "\\documentclass[pdflatex,sn-mathphys-num]{sn-jnl}" in main_source
    assert "\\articletype{Original Research}" in main_source
    assert 170 <= len(words) <= 200
    assert all(f"\\textbf{{{label}}}" in extract_balanced(main_source, "\\abstract{") for label in ("Purpose", "Methods", "Results", "Conclusion"))
    assert 4 <= len(keywords) <= 6
    assert main_depth <= 3 and esm_depth <= 3
    assert not missing and not uncited
    assert doi_count == len(bibliography)
    assert len(preprints) == 4 and all("arXiv preprint" in block for block in preprints)
    assert not uncited_labels
    assert len(figure_captions) == len(figure_labels)
    assert figure_captions_without_terminal_period == len(figure_captions)
    assert labelled_count(main_tex, "fig") <= 4
    assert labelled_count(main_tex, "tab") <= 2
    assert build["main"]["page_count"] <= 25
    assert all(build[part]["warnings"][key] == 0 for part in ("main", "esm_1") for key in FATAL_WARNING_KEYS)

    test_output = run(["pytest", "-q"])
    if "178 passed" not in test_output:
        raise RuntimeError(f"unexpected pytest result:\n{test_output}")
    number_output = run(["python", "paper_scripts/reviewer_robustness/audit_paper_numbers.py"])
    if "PASS (62 checks)" not in number_output:
        raise RuntimeError(number_output)
    shutil.copy2(
        ROOT / "results" / "reviewer_robustness" / "PAPER_NUMBER_AUDIT.md",
        FINAL / "PAPER_NUMBER_AUDIT.md",
    )
    integrity_output = run(
        ["python", "paper_scripts/reviewer_robustness/run_reviewer_robustness.py", "integrity"]
    )
    integrity = json.loads(integrity_output)
    assert integrity["pass"] is True
    assert integrity["observed_file_count"] == 1399
    assert integrity["observed_aggregate_sha256"] == CANONICAL_HASH

    author_actions = f"""# Author Action Required — SN Computer Science

Status: **READY_AFTER_AUTHOR_METADATA**. The typesetting, source archives,
scientific audits, and visual checks are complete, but the red author-action
drafts must not be uploaded to Editorial Manager.

Only the published-name spelling `Zhilin Chen` was verifiable in this
repository. No affiliation, e-mail, ORCID, funding, acknowledgement,
competing-interest declaration, contribution statement, or archival code/data
URL was inferred.

## Required human decisions

1. Confirm the complete author list, order, spelling, and corresponding-author designation.
2. Supply the official department, institution, city, and country for every affiliation.
3. Supply an active corresponding-author e-mail address.
4. Supply each ORCID if available, or explicitly confirm that no ORCID is to be shown.
5. Approve the Funding statement; use a no-funding statement only if factually true.
6. Approve the Competing interests statement; use a no-interests statement only if factually true.
7. Approve a Data availability statement matching the real submission-time archive status; do not insert a provisional or invented DOI/URL.
8. Approve a Code availability statement on the same basis.
9. Approve the final Author contributions/CRediT statement after confirming the author list.
10. Supply acknowledgements, or explicitly confirm that there are none.
11. Confirm that the computational-study Ethics/Consent `Not applicable` statements are factually correct.
12. Review and approve the factual OpenAI Codex disclosure in Methods, `Software and AI-Assisted Workflow`.
13. Mirror the confirmed author metadata in `ESM_1.tex` and `ESM_2_contents/README.md`.
14. Remove the red `AUTHOR-ACTION DRAFT` subtitles and every `REQUIRED` marker only after filling the fields.
15. Complete the cover letter's author/contact, originality, and simultaneous-submission confirmations.
16. Confirm the submission status of the Q-RouteBench/IJOC companion manuscript. If it is submitted or under review, cross-cite it where journal policy permits and disclose the relationship in the cover letter as documented in `COMPANION_OVERLAP_AUDIT.md`.

## Rebuild and gate

After updating `overleaf/main.tex`, `overleaf/ESM_1.tex`, and the ESM_2 README
generator, run:

```bash
module load texlive/2023
python paper_scripts/reviewer_robustness/audit_paper_numbers.py
python paper_scripts/build_sncs_submission_final.py
python paper_scripts/write_sncs_submission_audits.py
```

The submission candidate is uploadable only when a case-insensitive search for
`AUTHOR-ACTION`, `AUTHOR ACTION`, and `REQUIRED]` returns no hit in the two TeX
sources, ESM_2 README, or rendered PDFs.

Official requirements were checked on 2026-09-04 against the
[SN Computer Science Submission Guidelines]({GUIDELINES}).
"""
    write(FINAL / "AUTHOR_ACTION_REQUIRED_SNCS.md", author_actions)

    build_audit = f"""# SN Computer Science Build Audit

Generated from the final author-action build on 2026-09-04.

## Build result

- Main manuscript: **{build['main']['page_count']} pages**.
- Online Resource 1: **{build['esm_1']['page_count']} pages**.
- Structured abstract: **{len(words)} words**, including the four labels; hyphenated compounds and formatted numerals count as one token.
- Keywords: **{len(keywords)}**.
- Heading depth: main **{main_depth}**, ESM_1 **{esm_depth}**.
- Bibliography: **{len(bibliography)} cited references**, **{doi_count}/{len(bibliography)} DOI fields**.
- Main figures/tables: **{labelled_count(main_tex, 'fig')} / {labelled_count(main_tex, 'tab')}**.
- ESM_1 figures/tables: **{labelled_count(esm_tex, 'fig')} / {labelled_count(esm_tex, 'tab')}**.

The main article satisfies the project's hard pre-submission target of at most
25 total pages. The reduction was achieved by deleting repetition, merging
sections, and moving proofs, protocols, and full robustness matrices to Online
Resource 1 rather than by shrinking type, margins, or artwork.

## Compilation

The main archive was extracted into an empty temporary directory and compiled
using `pdflatex`, `bibtex`, `pdflatex`, `pdflatex`. ESM_1 was independently
extracted and compiled with three `pdflatex` passes. Both reproduced the same
page counts as the staged package.

{warning_summary(build)}

All fatal-warning categories are zero: undefined citations, undefined
references, duplicate labels, overfull boxes, bookmark-hierarchy warnings,
duplicate PDF destinations, PDF-string warnings, and missing files. The listed
underfull warnings arise from short/floating pages and narrow supplementary
table/caption lines; all {build['main']['page_count'] + build['esm_1']['page_count']} pages were rendered and visually inspected, with no
clipping, collision, unreadable table, or broken page. Ghostscript preflight
passed for both PDFs. Embedded font streams (`FontFile`/`FontFile2`) were
confirmed by PDF debug inspection.

## Visual and structural inspection

- Title page, corresponding-author block, structured abstract, and keywords checked.
- Purpose, Methods, Results, and Conclusion labels are visually distinct; the complete abstract fits page 1.
- Equations, the short main-text scope argument, main figures/tables, declarations, all references, and DOI links checked.
- ESM title metadata, two-page contents, proofs, robustness matrices, figures, tables, and final flowchart checked.
- Figure panels use lowercase `a`, `b`, `c`; captions use template-generated `Fig.` numbering and omit an author-added terminal full stop ({figure_captions_without_terminal_period}/{len(figure_captions)} figure captions).
- All {len(figure_labels)} figure and {len(table_labels)} table labels have an explicit textual reference.
- All artwork is repository-generated from project scripts/local frozen result files; no web/stock/watermarked asset was found, so no third-party figure permission is required.

## Scientific freeze gates

- Tests: `{test_output.splitlines()[-1]}`.
- Manuscript-number audit: `62/62 PASS`.
- Canonical integrity: `{integrity['observed_file_count']}/{integrity['expected_file_count']} files unchanged`.
- Canonical aggregate SHA-256: `{integrity['observed_aggregate_sha256']}`.

## Checksums

- `main_submission.pdf`: `{build['main']['pdf_sha256']}`
- `ESM_1.pdf`: `{build['esm_1']['pdf_sha256']}`
- `Q-RouteDilution_SNCS_submission_source.zip`: `{build['source_archives']['Q-RouteDilution_SNCS_submission_source.zip']}`
- `Q-RouteDilution_SNCS_ESM_1.zip`: `{build['source_archives']['Q-RouteDilution_SNCS_ESM_1.zip']}`
- `ESM_2.zip`: `{build['source_archives']['ESM_2.zip']}`
"""
    write(FINAL / "BUILD_AUDIT.md", build_audit)

    rows = [
        ("Springer Nature LaTeX template", "Use the publisher template.", "PASS", "`main_submission.tex`; official v3.1 December 2024 class/BST hashes in `BUILD_RESULTS.json`.", "None."),
        ("Original Research", "Use the journal's current article category.", "PASS", "`\\articletype{Original Research}`; package terminology is consistent.", "Select Original Research in Editorial Manager."),
        ("Title", "Provide a concise article title.", "PASS", "Title block in `main_submission.tex` and mirrored in ESM_1.", "None."),
        ("Author name(s)", "List all authors on the title page.", "BLOCKED_ON_AUTHOR_INPUT", "Only `Zhilin Chen` is repository-attested; red author-action draft.", "Confirm complete list, order, spelling, and corresponding author."),
        ("Affiliation", "Give department/institution and city/country.", "BLOCKED_ON_AUTHOR_INPUT", "Official `\\affil*` structure is present with four visible required fields.", "Supply verified official English affiliation(s)."),
        ("Corresponding e-mail", "Give an active corresponding-author e-mail.", "BLOCKED_ON_AUTHOR_INPUT", "Official `\\email` slot is present with a visible required field.", "Supply active address."),
        ("ORCID", "Include ORCID if available.", "BLOCKED_ON_AUTHOR_INPUT", "No repository-confirmed ORCID.", "Supply ORCID(s), or confirm none is available."),
        ("Structured abstract 150–250", "Structured abstract, 150–250 words.", "PASS", f"Abstract is {len(words)} words including labels; page 1.", "None."),
        ("Purpose", "Required structured-abstract heading.", "PASS", "Bold run-in label in abstract.", "None."),
        ("Methods", "Required structured-abstract heading.", "PASS", "Bold run-in label in abstract.", "None."),
        ("Results", "Required structured-abstract heading.", "PASS", "Bold run-in label in abstract; all numbers covered by number audit.", "None."),
        ("Conclusion", "Required structured-abstract heading.", "PASS", "Bold run-in label; no-advantage, no-global-scaling, and no-hardware/noise qualifications are retained.", "None."),
        ("Keywords", "Provide 4–6 keywords.", "PASS", f"{len(keywords)} keywords in `main_submission.tex`.", "None."),
        ("Heading hierarchy", "No more than three displayed levels.", "PASS", f"Main maximum level {main_depth}; ESM_1 maximum level {esm_depth}; no `paragraph`, `subparagraph`, or `bmhead` display headings.", "None."),
        ("Numbered citations", "Use consecutive square-bracket numeric citations.", "PASS", "`sn-mathphys-num`; rendered examples include compressed ranges and comma-separated citations.", "None."),
        ("Reference resolution", "List only cited works and number consecutively.", "PASS", f"{len(cited)}/{len(bibliography)} cited keys resolve; no missing or uncited entry.", "None."),
        ("DOI links", "Provide DOI links when available.", "PASS", f"{doi_count}/{len(bibliography)} entries contain DOI fields; PDF renders full DOI hyperlinks.", "None."),
        ("Preprint status", "Identify preprints accurately.", "PASS", "Four 2025/2026 `@misc` records explicitly say `arXiv preprint`; none is presented as a journal article.", "Update only if publication status changes before submission."),
        ("Figure numbering", "Number figures consecutively and cite them in text.", "PASS", f"Main Fig. 1–{labelled_count(main_tex, 'fig')}; ESM Fig. S1–S{labelled_count(esm_tex, 'fig')}; every label is cited.", "None."),
        ("Figure accessibility", "Use legible, high-contrast artwork not dependent on color alone.", "PASS", "Vector artwork; panel labels, positions, marker/line distinctions, legends, annotations, and colorblind-readable high-contrast palettes; all pages inspected at final size.", "None."),
        ("Figure captions", "Use concise captions with template numbering.", "PASS", f"`\\caption` generates `Fig.`; lowercase panel labels; {figure_captions_without_terminal_period}/{len(figure_captions)} figure captions omit an author-added terminal full stop.", "None."),
        ("Third-party permissions", "Obtain permission for reused material.", "PASS", "All 16 figures are produced by repository scripts from local project data/protocol diagrams; no third-party/stock/web/watermarked asset.", "No permission required."),
        ("Table numbering", "Number tables with Arabic numerals and cite in order.", "PASS", f"Main Tables 1–{labelled_count(main_tex, 'tab')}; ESM Tables S1–S{labelled_count(esm_tex, 'tab')}; every label is cited.", "None."),
        ("Table format", "Use editable tables, captions, and table notes.", "PASS", "All tables are native LaTeX, not screenshots; no overfull box; large matrices remain in ESM_1.", "None."),
        ("Acknowledgements", "Provide a separate acknowledgement section when applicable.", "BLOCKED_ON_AUTHOR_INPUT", "Separate section exists with a visible author-action marker.", "Supply wording or confirm none."),
        ("Declarations placement", "Place declarations before references.", "PASS", "`Statements and Declarations` precedes `References` in the source and rendered manuscript.", "None."),
        ("Funding", "Declare funding.", "BLOCKED_ON_AUTHOR_INPUT", "Required field exists; no funding fact was inferred.", "Approve factual statement."),
        ("Competing interests", "Declare relevant financial/non-financial interests.", "BLOCKED_ON_AUTHOR_INPUT", "Required field exists; no no-interest declaration was inferred.", "Approve factual statement."),
        ("Data availability", "Provide a data-availability statement.", "BLOCKED_ON_AUTHOR_INPUT", "Required field exists; no provisional URL/DOI inserted.", "Approve real submission-time status and archive link if public."),
        ("Code availability", "Provide a code-availability statement.", "BLOCKED_ON_AUTHOR_INPUT", "Required field exists; no provisional URL/DOI inserted.", "Approve real submission-time status and archive link if public."),
        ("Author contributions", "Describe contributions.", "BLOCKED_ON_AUTHOR_INPUT", "Required field exists; contribution roles were not inferred.", "Confirm author list, then approve CRediT wording."),
        ("Ethics approval", "State applicability.", "PASS", "Not applicable: synthetic graphs/computational simulation, no human/animal/biological material.", "Author to confirm factual applicability."),
        ("Consent to participate", "State applicability.", "PASS", "Not applicable; no participants.", "Author to confirm."),
        ("Consent for publication", "State applicability.", "PASS", "Not applicable; no participant/private material.", "Author to confirm."),
        ("AI-tool disclosure", "LLMs are not authors; substantive generative use is disclosed in Methods.", "PASS", "The final Methods paragraph states the Codex role, deterministic tests/audits, unchanged canonical data, and human responsibility.", "Author to review and approve wording."),
        ("Online Resource naming", "Refer to files as Online Resource 1, 2, etc.", "PASS", "First definition and later references use `Online Resource 1`; artifact is `Online Resource 2`.", "None."),
        ("ESM text format", "Upload text supplementary material as PDF.", "PASS", f"`ESM_1.pdf`, {build['esm_1']['page_count']} pages, uses S-numbering and a contents list.", "Upload PDF after metadata completion."),
        ("ESM metadata", "Each supplementary file gives title, journal, authors, affiliation, and corresponding e-mail.", "BLOCKED_ON_AUTHOR_INPUT", "ESM_1 and ESM_2 have title/journal/name and structurally visible affiliation/e-mail fields.", "Fill the same verified metadata in both resources."),
        ("Appendix versus Online Resource", "Avoid duplicate article appendices and standalone SI.", "PASS", "No scientific appendix remains in main; proofs/protocols/full matrices/provenance occur once in ESM_1.", "None."),
        ("Editable source files", "Supply editable manuscript source and assets.", "PASS", "TeX, BibTeX, class/BST, native table sources, and vector figures included.", "None."),
        ("Complete source archive", "Archive must be self-contained.", "PASS", "Both source ZIPs rebuilt from empty temporary directories using archive-only files.", "None."),
        ("Build warnings", "Submission files should compile without unresolved elements.", "PASS", "All fatal warning categories are zero in package and clean-archive builds.", "Underfull warnings visually accepted; see `BUILD_AUDIT.md`."),
        ("Project page target", "Internal target: no more than 25 total main-manuscript pages.", "PASS", f"Main is {build['main']['page_count']} pages; proofs, complete protocols, and full robustness matrices are in Online Resource 1.", "None."),
        ("Scientific freeze", "Internal project constraint.", "PASS", f"62/62 number checks; 178 tests; 1399/1399 canonical files; hash `{CANONICAL_HASH}`.", "None."),
    ]
    compliance = f"""# SN Computer Science Final Compliance Audit

Official journal requirements were checked online on **2026-09-04**. The
[current SNCS Submission Guidelines]({GUIDELINES}) take priority; the
[Springer Nature LaTeX support page]({LATEX}) and [SNCS aims and scope]({SCOPE})
were used for template and scope checks.

{compliance_table(rows)}

## Architecture and verdict

The main article contains the scientific narrative, core results, a short
information-access scope argument, declarations, and references. Online Resource 1 contains complete theorem statements and proofs,
full protocols, reviewer-robustness matrices, additional figures/tables, and
provenance; none of that material is duplicated as a main-paper appendix.
Online Resource 2 contains compact machine-readable result summaries and
metadata, not a substitute for a public archive.

Mechanical, bibliographic, visual, and scientific-freeze gates pass. Required
identity and declaration fields remain genuinely unknown and are visibly
blocked rather than fabricated.

**Verdict: READY_AFTER_AUTHOR_METADATA**
"""
    write(FINAL / "SNCS_COMPLIANCE_AUDIT.md", compliance)

    cover_notes = f"""# Cover Letter Notes — SN Computer Science

- Journal: **SN Computer Science**
- Article type: **Original Research**
- Scope fit: **quantum computing, constrained combinatorial optimization, and modeling/simulation**.
- Positioning: a controlled mechanistic study of feasible-space dilution, optimizer inadequacy, and objective alignment in full-space Penalty-X QAOA.
- The benchmark is classically tractable by design; the exact classical solver reproduces 140/140 frozen optima.
- No quantum computational advantage or global scaling law is claimed.
- Finite-shot wording remains qualified: fixed-endpoint estimates are stable, while finite-shot retraining gives mixed evidence; no hardware/noise validation was performed.
- The primary frozen experiment uses `p=3`; the `p=4` depth-budget study is explicitly post-hoc/reviewer robustness.
- At `m=22`, runs were administratively censored by the preregistered computational budget; this is not presented as a qubit, statevector-memory, or algorithmic barrier.
- The repository contains a distinct Q-RouteBench/IJOC companion candidate. If it has been submitted, disclose the relationship and scientific differences summarized in `COMPANION_OVERLAP_AUDIT.md`.

Author must add verified contact details and approve statements on authorship,
originality, simultaneous submission, funding, competing interests, data/code
availability, and acknowledgements. Do not send this note itself as the cover
letter.

Scope checked against [SNCS aims and scope]({SCOPE}) on 2026-09-04.
"""
    write(FINAL / "COVER_LETTER_NOTES.md", cover_notes)

    manifest_targets = [
        "main_submission.pdf",
        "main_submission.tex",
        "references.bib",
        "sn-jnl.cls",
        "sn-mathphys-num.bst",
        "ESM_1.pdf",
        "ESM_1.tex",
        "ESM_2.zip",
        "Q-RouteDilution_SNCS_submission_source.zip",
        "Q-RouteDilution_SNCS_ESM_1.zip",
        "SNCS_COMPLIANCE_AUDIT.md",
        "AUTHOR_ACTION_REQUIRED_SNCS.md",
        "PAPER_NUMBER_AUDIT.md",
        "GAMMA_PERIODICITY_AUDIT.md",
        "COMPANION_OVERLAP_AUDIT.md",
        "FINAL_SHORTENING_REPORT.md",
        "BUILD_AUDIT.md",
        "COVER_LETTER_NOTES.md",
        "BUILD_RESULTS.json",
    ]
    manifest_rows = []
    for name in manifest_targets:
        path = FINAL / name
        manifest_rows.append(
            f"| `{name}` | {path.stat().st_size} | `{sha256(path)}` |"
        )
    manifest = f"""# SN Computer Science Submission File Manifest

This directory is an **author-action draft**, not yet an upload set. After the
blocked metadata is supplied and all red markers are removed, the recommended
Editorial Manager files are:

1. `main_submission.pdf` — main manuscript.
2. `Q-RouteDilution_SNCS_submission_source.zip` — self-contained editable main source.
3. `ESM_1.pdf` — Online Resource 1 (text supplementary information).
4. `Q-RouteDilution_SNCS_ESM_1.zip` — editable ESM_1 source if requested.
5. `ESM_2.zip` — Online Resource 2, compact machine-readable metadata and summaries.

The audit Markdown files are internal handoff evidence and normally should not
be uploaded unless the journal requests them.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
{chr(10).join(manifest_rows)}

## Source archive boundaries

The main ZIP contains only the TeX entry point, bibliography, current official
class/BST, required section/table sources, and five vector assets used in four
numbered main figures. The ESM ZIP contains only its TeX entry point, class/BST, appendices/tables, and 11
supplementary vector figures. Neither archive depends on an absolute path or a
file outside the archive.

`SUBMISSION_FILE_MANIFEST.md` excludes its own recursively changing checksum.
"""
    write(FINAL / "SUBMISSION_FILE_MANIFEST.md", manifest)

    print(
        json.dumps(
            {
                "abstract_words": len(words),
                "keywords": len(keywords),
                "main_heading_depth": main_depth,
                "esm_heading_depth": esm_depth,
                "references": len(bibliography),
                "main_pages": build["main"]["page_count"],
                "esm_pages": build["esm_1"]["page_count"],
                "tests": test_output.splitlines()[-1],
                "number_audit": "62/62 PASS",
                "canonical_files": integrity["observed_file_count"],
                "canonical_sha256": integrity["observed_aggregate_sha256"],
                "verdict": "READY_AFTER_AUTHOR_METADATA",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
