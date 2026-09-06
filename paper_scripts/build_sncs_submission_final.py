#!/usr/bin/env python3
"""Build and independently reproduce the SN Computer Science submission bundle.

This is a packaging and typesetting script only. It copies manuscript sources,
compiles them, and checks the resulting logs; it never reads or writes the
canonical experiment tree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLEAF = ROOT / "overleaf"
TEMPLATE = ROOT / "paper_assets" / "springer_nature_latex_2024_12"
FINAL = ROOT / "submission" / "sn_computer_science_final_short"
PREVIOUS_FINAL = ROOT / "submission" / "sn_computer_science_final"
MARKER = FINAL / ".sncs_build_output"

EXPECTED_TEMPLATE_HASHES = {
    "sn-jnl.cls": "36d0c3273a59d48dc6a9c7b080dfa1ec50dc10229d8751568d1f2e490ffa5ecc",
    "sn-mathphys-num.bst": "b3a7c7fbcc1e7f9619de634fcea2f5bb7a245818a5942bc576e40ea001633332",
}

MAIN_FIGURES = {
    "fig02_dilution_scale_control.pdf",
    "fig03_optimizer_attribution.pdf",
    "fig06_heldout_confirmation.pdf",
    "fig12_reviewer_depth_budget.pdf",
    "fig15_reviewer_finite_shot_training.pdf",
}
MAIN_TABLES = {
    "table03_optimizer_attribution.tex",
    "table04_heldout_results.tex",
}
ESM_FIGURES = {
    "fig01_experimental_concept.pdf",
    "fig04_objective_misalignment.pdf",
    "fig05_objective_discovery.pdf",
    "fig07_feasibility_optimality.pdf",
    "fig08_scaling_response.pdf",
    "fig09_theory_scope.pdf",
    "fig10_structure_cost_relocation.pdf",
    "fig11_finite_shot_endpoint_robustness.pdf",
    "fig13_reviewer_optimizer_robustness.pdf",
    "fig14_reviewer_alpha_sensitivity.pdf",
    "fig16_reviewer_alpha_shots.pdf",
}
ESM_TABLES = {
    "table01_protocol_summary.tex",
    "table02_objectives.tex",
    "table06_theory_scope.tex",
    "table07_related_work.tex",
    "table08_reviewer_optimizer.tex",
    "tableS1_failure_census.tex",
    "tableS2_task_strata.tex",
    "tableS3_statistics.tex",
    "tableS4_proof_assumptions.tex",
    "tableS5_artifact_hashes.tex",
    "tableS6_reviewer_protocols.tex",
    "tableS7_depth_budget.tex",
    "tableS8_alpha_sensitivity.tex",
    "tableS9_finite_shot_training.tex",
    "tableS10_classical_context.tex",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def verify_template() -> dict[str, str]:
    observed = {}
    for name, expected in EXPECTED_TEMPLATE_HASHES.items():
        path = TEMPLATE / name
        if not path.is_file():
            raise FileNotFoundError(path)
        observed[name] = sha256(path)
        if observed[name] != expected:
            raise RuntimeError(
                f"Springer template hash changed for {name}: "
                f"{observed[name]} != {expected}"
            )
    return observed


def reset_output() -> None:
    if FINAL.exists():
        if not MARKER.is_file():
            raise RuntimeError(f"Refusing to replace unmarked directory: {FINAL}")
        shutil.rmtree(FINAL)
    FINAL.mkdir(parents=True)
    write_text(MARKER, "Managed by paper_scripts/build_sncs_submission_final.py")


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target)


def copy_selected(source: Path, target: Path, names: set[str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        path = source / name
        if not path.is_file():
            raise FileNotFoundError(path)
        shutil.copy2(path, target / name)


def stage_full_package(template_hashes: dict[str, str]) -> None:
    shutil.copy2(OVERLEAF / "main.tex", FINAL / "main_submission.tex")
    shutil.copy2(OVERLEAF / "ESM_1.tex", FINAL / "ESM_1.tex")
    shutil.copy2(OVERLEAF / "references.bib", FINAL / "references.bib")
    for name in EXPECTED_TEMPLATE_HASHES:
        shutil.copy2(TEMPLATE / name, FINAL / name)
    shutil.copy2(TEMPLATE / "TEMPLATE_PROVENANCE.md", FINAL / "TEMPLATE_PROVENANCE.md")
    for directory in ("sections", "appendices", "tables", "figures", "supplementary"):
        copy_tree(OVERLEAF / directory, FINAL / directory)

    provenance = [
        "# Springer Nature LaTeX Template Provenance",
        "",
        "- Template release: Springer Nature LaTeX authoring template v3.1, December 2024.",
        "- Official template page checked: 2026-09-04.",
        "- Journal class option: pdflatex,sn-mathphys-num.",
        "- No local edit was made to the class or bibliography-style file.",
        "",
        "## Included file hashes",
        "",
    ]
    provenance.extend(
        f"- {name}: {digest}" for name, digest in sorted(template_hashes.items())
    )
    write_text(FINAL / "TEMPLATE_PROVENANCE_SNCS.md", "\n".join(provenance))

    number_audit = (
        ROOT / "results" / "reviewer_robustness" / "PAPER_NUMBER_AUDIT.md"
    )
    if not number_audit.is_file():
        raise FileNotFoundError(number_audit)
    shutil.copy2(number_audit, FINAL / "PAPER_NUMBER_AUDIT.md")
    gamma_audit = (
        ROOT
        / "results"
        / "reviewer_robustness"
        / "final_audits"
        / "GAMMA_PERIODICITY_AUDIT.md"
    )
    companion_audit = PREVIOUS_FINAL / "COMPANION_OVERLAP_AUDIT.md"
    for audit in (gamma_audit, companion_audit):
        if not audit.is_file():
            raise FileNotFoundError(audit)
        shutil.copy2(audit, FINAL / audit.name)


def esm2_readme() -> str:
    return """# Online Resource 2

Article title: Feasible-Space Dilution and Objective Alignment in Shallow
Penalty-X QAOA: A Controlled RCSP Study

Journal: SN Computer Science

Article type: Original Research

Author: Zhilin Chen

Affiliation: **AUTHOR ACTION REQUIRED**

Corresponding author: **AUTHOR ACTION REQUIRED**

E-mail: **AUTHOR ACTION REQUIRED**

This archive contains compact reproducibility metadata and machine-readable
result summaries. It is not a replacement for a public archival repository or
the complete canonical experiment tree.

Files:

- claim_evidence_summary.csv: claim-to-evidence mapping and wording bounds.
- numeric_audit.csv: frozen synthesis-level manuscript-number audit.
- full_failure_census.csv: retained execution and censoring census.
- task_strata.csv: controlled task-stratum summary.
- artifact_manifest.txt: hashes for included and selected source artifacts.
"""


def deterministic_zip(source: Path, output: Path) -> None:
    fixed_time = (2024, 12, 1, 0, 0, 0)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=fixed_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes())


def build_esm2() -> Path:
    content = FINAL / "ESM_2_contents"
    content.mkdir()
    write_text(content / "README.md", esm2_readme())
    for path in sorted((OVERLEAF / "supplementary").iterdir()):
        if path.is_file():
            shutil.copy2(path, content / path.name)
    output = FINAL / "ESM_2.zip"
    deterministic_zip(content, output)
    return output


def prepare_main_source(source: Path) -> None:
    shutil.copy2(FINAL / "main_submission.tex", source / "main_submission.tex")
    shutil.copy2(FINAL / "references.bib", source / "references.bib")
    for name in EXPECTED_TEMPLATE_HASHES:
        shutil.copy2(FINAL / name, source / name)
    copy_tree(FINAL / "sections", source / "sections")
    copy_selected(FINAL / "tables", source / "tables", MAIN_TABLES)
    copy_selected(FINAL / "figures", source / "figures", MAIN_FIGURES)


def prepare_esm_source(source: Path) -> None:
    shutil.copy2(FINAL / "ESM_1.tex", source / "ESM_1.tex")
    for name in EXPECTED_TEMPLATE_HASHES:
        shutil.copy2(FINAL / name, source / name)
    copy_tree(FINAL / "appendices", source / "appendices")
    copy_selected(FINAL / "tables", source / "tables", ESM_TABLES)
    copy_selected(FINAL / "figures", source / "figures", ESM_FIGURES)


def run_command(command: list[str], cwd: Path, log: Path) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=os.environ.copy(),
    )
    write_text(log, "$ " + " ".join(command) + "\n\n" + result.stdout)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}; see {log}"
        )


def compile_main(cwd: Path, log_root: Path) -> None:
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main_submission.tex"],
        ["bibtex", "main_submission"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main_submission.tex"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main_submission.tex"],
    ]
    for index, command in enumerate(commands, start=1):
        run_command(command, cwd, log_root / f"main_{index}_{command[0]}.txt")


def compile_esm(cwd: Path, log_root: Path) -> None:
    command = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "ESM_1.tex"]
    for index in range(1, 4):
        run_command(command, cwd, log_root / f"esm_{index}_pdflatex.txt")


def warning_counts(log: Path) -> dict[str, int]:
    text = log.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "undefined_citations": r"(?:Citation .* undefined|undefined citations)",
        "undefined_references": r"(?:Reference .* undefined|undefined references)",
        "duplicate_labels": r"(?:multiply defined|Label .* multiply defined)",
        "overfull_boxes": r"Overfull \\[hv]box",
        "underfull_hboxes": r"Underfull \\hbox",
        "underfull_vboxes": r"Underfull \\vbox",
        "bookmark_hierarchy": r"Difference \([0-9]+\) between bookmark levels",
        "duplicate_destinations": r"destination with the same identifier",
        "pdf_string_warnings": r"Token not allowed in a PDF string",
        "missing_files": r"(?:File .* not found|I can't find file|No file .*\.bbl)",
    }
    return {
        key: len(re.findall(pattern, text, flags=re.IGNORECASE))
        for key, pattern in patterns.items()
    }


def page_count(pdf: Path) -> int:
    ghostscript = shutil.which("gs")
    if not ghostscript:
        raise RuntimeError("Ghostscript is required for PDF page counting")
    command = [
        ghostscript,
        "-q",
        "-dNODISPLAY",
        "-c",
        f"({pdf.resolve()}) (r) file runpdfbegin pdfpagecount = quit",
    ]
    return int(subprocess.check_output(command, text=True).strip())


def ghostscript_preflight(pdf: Path, log: Path) -> None:
    command = [
        shutil.which("gs") or "gs",
        "-q",
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=nullpage",
        "-o",
        os.devnull,
        str(pdf),
    ]
    run_command(command, pdf.parent, log)


def archive_sources() -> tuple[Path, Path]:
    main_zip = FINAL / "Q-RouteDilution_SNCS_submission_source.zip"
    esm_zip = FINAL / "Q-RouteDilution_SNCS_ESM_1.zip"
    with tempfile.TemporaryDirectory(prefix="sncs-source-stage-") as raw:
        stage = Path(raw)
        main_source = stage / "main"
        esm_source = stage / "esm"
        main_source.mkdir()
        esm_source.mkdir()
        prepare_main_source(main_source)
        prepare_esm_source(esm_source)
        deterministic_zip(main_source, main_zip)
        deterministic_zip(esm_source, esm_zip)
    return main_zip, esm_zip


def reproduce_archive(archive: Path, kind: str, log_root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"sncs-{kind}-reproduce-") as raw:
        target = Path(raw)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(target)
        if kind == "main":
            compile_main(target, log_root / "archive_main")
            pdf = target / "main_submission.pdf"
            log = target / "main_submission.log"
        else:
            compile_esm(target, log_root / "archive_esm")
            pdf = target / "ESM_1.pdf"
            log = target / "ESM_1.log"
        return {
            "archive": archive.name,
            "page_count": page_count(pdf),
            "warnings": warning_counts(log),
            "pdf_sha256": sha256(pdf),
        }


def clean_package_intermediates() -> None:
    """Keep the delivery directory free of disposable TeX build products."""

    names = (
        "main_submission.aux",
        "main_submission.bbl",
        "main_submission.blg",
        "main_submission.log",
        "main_submission.out",
        "ESM_1.aux",
        "ESM_1.log",
        "ESM_1.out",
        "ESM_1.toc",
    )
    for name in names:
        path = FINAL / name
        if path.exists():
            path.unlink()


def main() -> int:
    for executable in ("pdflatex", "bibtex", "gs"):
        if not shutil.which(executable):
            raise RuntimeError(
                f"{executable} is unavailable; load the TeX module before running"
            )
    template_hashes = verify_template()
    reset_output()
    stage_full_package(template_hashes)
    build_esm2()

    log_root = FINAL / "build_logs"
    compile_main(FINAL, log_root / "package_main")
    compile_esm(FINAL, log_root / "package_esm")
    ghostscript_preflight(
        FINAL / "main_submission.pdf",
        log_root / "package_main" / "ghostscript_preflight.txt",
    )
    ghostscript_preflight(
        FINAL / "ESM_1.pdf",
        log_root / "package_esm" / "ghostscript_preflight.txt",
    )

    main_zip, esm_zip = archive_sources()
    archive_main = reproduce_archive(main_zip, "main", log_root)
    archive_esm = reproduce_archive(esm_zip, "esm", log_root)

    package_main_warnings = warning_counts(FINAL / "main_submission.log")
    package_esm_warnings = warning_counts(FINAL / "ESM_1.log")
    fatal_warning_keys = (
        "undefined_citations",
        "undefined_references",
        "duplicate_labels",
        "overfull_boxes",
        "bookmark_hierarchy",
        "duplicate_destinations",
        "pdf_string_warnings",
        "missing_files",
    )
    for name, warnings in (
        ("package main", package_main_warnings),
        ("package ESM", package_esm_warnings),
        ("archive main", archive_main["warnings"]),
        ("archive ESM", archive_esm["warnings"]),
    ):
        failures = {key: warnings[key] for key in fatal_warning_keys if warnings[key]}
        if failures:
            raise RuntimeError(f"{name} warning gate failed: {failures}")

    results = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "template_hashes": template_hashes,
        "main": {
            "page_count": page_count(FINAL / "main_submission.pdf"),
            "pdf_sha256": sha256(FINAL / "main_submission.pdf"),
            "warnings": package_main_warnings,
        },
        "esm_1": {
            "page_count": page_count(FINAL / "ESM_1.pdf"),
            "pdf_sha256": sha256(FINAL / "ESM_1.pdf"),
            "warnings": package_esm_warnings,
        },
        "source_archives": {
            main_zip.name: sha256(main_zip),
            esm_zip.name: sha256(esm_zip),
            "ESM_2.zip": sha256(FINAL / "ESM_2.zip"),
        },
        "archive_reproduction": {
            "main": archive_main,
            "esm_1": archive_esm,
        },
    }
    write_text(FINAL / "BUILD_RESULTS.json", json.dumps(results, indent=2, sort_keys=True))
    clean_package_intermediates()
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
