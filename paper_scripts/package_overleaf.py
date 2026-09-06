#!/usr/bin/env python3
"""Create and validate the clean, self-contained Overleaf archive."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLEAF = ROOT / "overleaf"
DIST = ROOT / "dist"
AUDIT = ROOT / "paper_audit"
ZIP_PATH = DIST / "Q-RouteDilution_Overleaf_v2.zip"
PDF_PATH = DIST / "Q-RouteDilution_Manuscript_v2.pdf"
BASELINE_COMMIT = "4d1111f3661f4b2df852eec2b382555a63e434d2"

ALLOWED_ROOT = {
    "main.tex",
    "references.bib",
    "README.md",
    "sections",
    "appendices",
    "figures",
    "tables",
    "supplementary",
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
    "results/theory_validation_v1/summary.json",
    "results/theory_validation_v2/summary.json",
    "results/theory_validation_v3/summary.json",
    "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv",
]

DERIVED_PUBLICATION_SOURCES = [
    "results/finalization_audit_v1/reconstructed_headlines.json",
    "results/finalization_audit_v1/heldout_statistics_rebuilt.json",
    "results/finalization_audit_v1/scaling_verdict_rebuilt.json",
    "results/finalization_audit_v1/claim_evidence_audit.csv",
    "results/posthoc_finite_shot_endpoint_v1/manifest.json",
    "results/posthoc_finite_shot_endpoint_v1/sampling_config.json",
    "results/posthoc_finite_shot_endpoint_v1/exact_reference.csv",
    "results/posthoc_finite_shot_endpoint_v1/aggregate.csv",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def package_files() -> list[Path]:
    return sorted(path for path in OVERLEAF.rglob("*") if path.is_file())


def write_manifest() -> None:
    manifest = OVERLEAF / "supplementary/artifact_manifest.txt"
    lines = [
        "Q-RouteDilution manuscript artifact manifest",
        f"baseline_source_commit {BASELINE_COMMIT}",
        "working_branch paper-finalization-v2",
        "stage PUBLICATION_FINALIZATION_V2",
        "phase3b_evidence EXCLUDED",
        "posthoc_finite_shot_role POSTHOC_ROBUSTNESS_ONLY",
        "hash_algorithm SHA256",
        "",
        "[included_overleaf_files]",
        "# The manifest omits its own digest because a cryptographic self-hash is not finite.",
    ]
    for path in package_files():
        if path == manifest:
            continue
        lines.append(f"{digest(path)}  {path.relative_to(OVERLEAF).as_posix()}")
    lines.extend(["", "[selected_canonical_source_files]"])
    for relative in CANONICAL_SOURCES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"canonical source missing: {relative}")
        lines.append(f"{digest(path)}  {relative}")
    lines.extend(["", "[publication_rebuild_and_posthoc_files]"])
    for relative in DERIVED_PUBLICATION_SOURCES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"publication source missing: {relative}")
        lines.append(f"{digest(path)}  {relative}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_tree(root: Path) -> dict:
    top = {path.name for path in root.iterdir()}
    unexpected = sorted(top - ALLOWED_ROOT)
    missing_root = sorted(ALLOWED_ROOT - top)
    symlinks = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_symlink()]
    forbidden = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if any(part in {".git", "__pycache__", ".ipynb_checkpoints", ".venv", "venv"}
               for part in path.parts)
    ]

    text_files = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg"}]
    absolute = []
    for path in text_files:
        text = path.read_text(encoding="utf-8")
        if "/home/" in text or "file://" in text:
            absolute.append(path.relative_to(root).as_posix())

    tex_paths = sorted(root.rglob("*.tex"))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in tex_paths)
    combined = "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in combined.splitlines())
    missing_inputs = []
    for name in re.findall(r"\\input\{([^}]+)\}", combined):
        target = root / name
        if not target.suffix:
            target = target.with_suffix(".tex")
        if not target.is_file():
            missing_inputs.append(name)
    missing_figures = []
    for name in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", combined):
        if not (root / name).is_file() and not (root / "figures" / name).is_file():
            missing_figures.append(name)

    labels = re.findall(r"\\label\{([^}]+)\}", combined)
    refs: set[str] = set()
    for group in re.findall(r"\\(?:ref|eqref|cref|Cref)\{([^}]+)\}", combined):
        refs.update(item.strip() for item in group.split(","))
    missing_refs = sorted(refs - set(labels))

    bib = (root / "references.bib").read_text(encoding="utf-8")
    bib_keys = set(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", bib))
    cited: set[str] = set()
    for group in re.findall(r"\\cite\w*\s*\{([^}]+)\}", combined):
        cited.update(key.strip() for key in group.split(","))
    unresolved_citations = sorted(cited - bib_keys)

    begin = {}
    end = {}
    for name in re.findall(r"\\begin\{([^}]+)\}", combined):
        begin[name] = begin.get(name, 0) + 1
    for name in re.findall(r"\\end\{([^}]+)\}", combined):
        end[name] = end.get(name, 0) + 1
    environment_mismatch = {
        name: begin.get(name, 0) - end.get(name, 0)
        for name in sorted(set(begin) | set(end))
        if begin.get(name, 0) != end.get(name, 0)
    }

    result = {
        "main_tex_at_root": (root / "main.tex").is_file(),
        "unexpected_root_entries": unexpected,
        "missing_root_entries": missing_root,
        "symlinks": symlinks,
        "forbidden_content": forbidden,
        "absolute_paths": absolute,
        "missing_inputs": sorted(set(missing_inputs)),
        "missing_figures": sorted(set(missing_figures)),
        "missing_references": missing_refs,
        "unresolved_citations": unresolved_citations,
        "environment_mismatch": environment_mismatch,
        "file_count": len([path for path in root.rglob("*") if path.is_file()]),
    }
    result["pass"] = result["main_tex_at_root"] and not any(
        result[key]
        for key in (
            "unexpected_root_entries", "missing_root_entries", "symlinks",
            "forbidden_content", "absolute_paths", "missing_inputs",
            "missing_figures", "missing_references", "unresolved_citations",
            "environment_mismatch",
        )
    )
    return result


def make_zip(files: list[Path]) -> None:
    DIST.mkdir(exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(OVERLEAF).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 29, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def compile_if_available(clean_root: Path) -> dict:
    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if not latexmk and not pdflatex:
        if PDF_PATH.exists():
            PDF_PATH.unlink()
        return {"status": "LATEX_COMPILER_NOT_AVAILABLE", "compiler": "", "log_tail": ""}

    if latexmk:
        command = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
        compiler = "latexmk -pdf"
    elif bibtex:
        commands = [
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            [bibtex, "main"],
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        ]
        output = ""
        for command_item in commands:
            run = subprocess.run(command_item, cwd=clean_root, text=True, capture_output=True)
            output += run.stdout + run.stderr
            if run.returncode:
                return {"status": "FAIL", "compiler": "pdflatex+bibtex", "log_tail": output[-8000:]}
        shutil.copy2(clean_root / "main.pdf", PDF_PATH)
        return {"status": "PASS", "compiler": "pdflatex+bibtex", "log_tail": output[-3000:]}
    else:
        return {"status": "FAIL", "compiler": "pdflatex without bibtex", "log_tail": "BibTeX unavailable"}

    run = subprocess.run(command, cwd=clean_root, text=True, capture_output=True)
    output = run.stdout + run.stderr
    if run.returncode or not (clean_root / "main.pdf").is_file():
        return {"status": "FAIL", "compiler": compiler, "log_tail": output[-8000:]}
    shutil.copy2(clean_root / "main.pdf", PDF_PATH)
    return {"status": "PASS", "compiler": compiler, "log_tail": output[-3000:]}


def main() -> None:
    write_manifest()
    source_validation = validate_tree(OVERLEAF)
    if not source_validation["pass"]:
        raise SystemExit(f"Overleaf source tree validation failed: {source_validation}")

    files = package_files()
    make_zip(files)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        corrupt = archive.testzip()
        listing = archive.namelist()
        if corrupt:
            raise SystemExit(f"corrupt ZIP entry: {corrupt}")

    with tempfile.TemporaryDirectory(prefix="qroute_overleaf_verify_") as temp:
        clean_root = Path(temp)
        with zipfile.ZipFile(ZIP_PATH) as archive:
            archive.extractall(clean_root)
        clean_validation = validate_tree(clean_root)
        compile_result = compile_if_available(clean_root)
        if not clean_validation["pass"]:
            raise SystemExit(f"clean extraction validation failed: {clean_validation}")
        if compile_result["status"] == "FAIL":
            raise SystemExit(f"clean compilation failed: {compile_result['log_tail']}")

    report = {
        "baseline_source_commit": BASELINE_COMMIT,
        "working_branch": "paper-finalization-v2",
        "zip_path": str(ZIP_PATH),
        "zip_size_bytes": ZIP_PATH.stat().st_size,
        "zip_sha256": digest(ZIP_PATH),
        "zip_file_count": len(listing),
        "zip_root_entries": sorted({name.split("/", 1)[0] for name in listing}),
        "zip_test": "PASS",
        "source_tree_validation": source_validation,
        "clean_extraction_validation": clean_validation,
        "clean_compile": compile_result,
        "target_under_50_mb": ZIP_PATH.stat().st_size < 50 * 1024 * 1024,
    }
    (AUDIT / "package_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
