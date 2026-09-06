#!/usr/bin/env python3
"""Compile the revised manuscript in an isolated clean directory and audit logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OVERLEAF = ROOT / "overleaf"
OUTPUT_DIR = ROOT / "results" / "reviewer_robustness" / "paper_revision"
PDF_OUTPUT = OUTPUT_DIR / "Q-RouteDilution_reviewer_robustness.pdf"
LOG_OUTPUT = OUTPUT_DIR / "main.log"
CONSOLE_OUTPUT = OUTPUT_DIR / "tectonic_console.log"
JSON_OUTPUT = OUTPUT_DIR / "manuscript_build_audit.json"
MD_OUTPUT = OUTPUT_DIR / "MANUSCRIPT_BUILD_AUDIT.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def matching_lines(text: str, patterns: tuple[str, ...]) -> list[str]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    matches = [line.strip() for line in text.splitlines() if any(item.search(line) for item in compiled)]
    return list(dict.fromkeys(matches))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True, help="Path to a Tectonic executable")
    args = parser.parse_args()
    engine = Path(args.engine).expanduser().resolve()
    if not engine.is_file():
        raise FileNotFoundError(engine)

    version_run = subprocess.run([str(engine), "--version"], text=True, capture_output=True, check=True)
    version = (version_run.stdout + version_run.stderr).strip()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="qroute-paper-clean-build-") as raw_temp:
        build_root = Path(raw_temp) / "overleaf"
        shutil.copytree(OVERLEAF, build_root)
        command = [
            str(engine), "-X", "compile", "main.tex", "--keep-logs",
            "--keep-intermediates", "-p",
        ]
        run = subprocess.run(command, cwd=build_root, text=True, capture_output=True)
        console = run.stdout + run.stderr
        atomic_write(CONSOLE_OUTPUT, console)
        built_pdf = build_root / "main.pdf"
        built_log = build_root / "main.log"
        if built_log.is_file():
            shutil.copy2(built_log, LOG_OUTPUT)
            log_text = built_log.read_text(encoding="utf-8", errors="replace")
        else:
            log_text = ""
        # Tectonic's console retains diagnostics from early passes. Only the
        # final TeX log determines whether references and citations converged.
        final_diagnostics = log_text if log_text else console

        categories = {
            "undefined_references": matching_lines(final_diagnostics, (r"undefined references?", r"reference .* undefined")),
            "undefined_citations": matching_lines(final_diagnostics, (r"citation .* undefined", r"undefined citations?")),
            "duplicate_labels": matching_lines(final_diagnostics, (r"multiply defined", r"duplicate.*label")),
            "overfull_boxes": matching_lines(final_diagnostics, (r"overfull \\hbox", r"overfull \\vbox")),
            "underfull_boxes": matching_lines(final_diagnostics, (r"underfull \\hbox", r"underfull \\vbox")),
            "bookmark_warnings": matching_lines(final_diagnostics, (r"pdf string", r"bookmark.*warning")),
            "missing_characters": matching_lines(final_diagnostics, (r"missing character",)),
        }
        hard_warning_count = sum(
            len(categories[name])
            for name in ("undefined_references", "undefined_citations", "duplicate_labels", "missing_characters")
        )
        success = run.returncode == 0 and built_pdf.is_file() and hard_warning_count == 0
        if built_pdf.is_file():
            shutil.copy2(built_pdf, PDF_OUTPUT)

    page_count: int | None = None
    pdfinfo = shutil.which("pdfinfo")
    if PDF_OUTPUT.is_file() and pdfinfo:
        info_run = subprocess.run([pdfinfo, str(PDF_OUTPUT)], text=True, capture_output=True)
        match = re.search(r"^Pages:\s+(\d+)", info_run.stdout, re.MULTILINE)
        if match:
            page_count = int(match.group(1))
    if page_count is None:
        match = re.search(r"Output written on .*?\((\d+) pages?", log_text)
        if match:
            page_count = int(match.group(1))

    source_files = sorted(
        path for path in OVERLEAF.rglob("*")
        if path.is_file() and path.suffix.lower() in {".tex", ".bib"}
    )
    source_digest = hashlib.sha256()
    for path in source_files:
        source_digest.update(path.relative_to(OVERLEAF).as_posix().encode("utf-8"))
        source_digest.update(b"\0")
        source_digest.update(sha256(path).encode("ascii"))
        source_digest.update(b"\n")

    payload = {
        "schema": "reviewer-manuscript-build-audit-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if success else "FAIL",
        "engine": version,
        "engine_path": str(engine),
        "engine_sha256": sha256(engine),
        "clean_build": True,
        "returncode": run.returncode,
        "pdf_path": PDF_OUTPUT.relative_to(ROOT).as_posix() if PDF_OUTPUT.is_file() else "",
        "pdf_sha256": sha256(PDF_OUTPUT) if PDF_OUTPUT.is_file() else "",
        "pdf_size_bytes": PDF_OUTPUT.stat().st_size if PDF_OUTPUT.is_file() else 0,
        "page_count": page_count,
        "source_file_count": len(source_files),
        "source_aggregate_sha256": source_digest.hexdigest(),
        "warning_categories": categories,
    }
    atomic_write(JSON_OUTPUT, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    lines = [
        "# Manuscript Build Audit",
        "",
        f"- Status: **{payload['status']}**",
        f"- Engine: `{version}`",
        "- Build isolation: clean temporary copy of `overleaf/`",
        f"- PDF: `{payload['pdf_path'] or 'not generated'}`",
        f"- PDF SHA-256: `{payload['pdf_sha256'] or 'n/a'}`",
        f"- Pages: {page_count if page_count is not None else 'not available'}",
        f"- Source aggregate SHA-256: `{payload['source_aggregate_sha256']}`",
        "",
        "## Warning audit",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for name, values in categories.items():
        lines.append(f"| {name.replace('_', ' ')} | {len(values)} |")
    detail_lines = [(name, values) for name, values in categories.items() if values]
    if detail_lines:
        lines.extend(["", "## Warning details", ""])
        for name, values in detail_lines:
            lines.append(f"### {name.replace('_', ' ').title()}")
            lines.append("")
            for value in values:
                lines.append(f"- `{value.replace('`', "'")}`")
            lines.append("")
    atomic_write(MD_OUTPUT, "\n".join(lines) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
