from __future__ import annotations

import csv
import hashlib
import re

import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNTHESIS = ROOT / "results" / "synthesis_v1"


def _rows(name: str) -> list[dict[str, str]]:
    with (SYNTHESIS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_all_protected_predecessor_hashes_are_unchanged() -> None:
    if (ROOT / "release_manifest.json").exists():
        pytest.skip("historical 1403-file audit includes private worktree metadata; "
                    "public bytes are checked by test_public_snapshot_integrity_manifest")
    lines = (SYNTHESIS / "protected_hashes_before.sha256").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(lines) == 1403
    for line in lines:
        expected, relative = line.split("  ", 1)
        target = ROOT / relative
        assert target.is_file(), relative
        assert _sha256(target) == expected, relative


def test_inventory_exactly_matches_protected_manifest() -> None:
    inventory = _rows("SYNTHESIS_INPUT_INVENTORY.csv")
    assert len(inventory) == 1403
    assert len({row["asset_id"] for row in inventory}) == 1403
    assert all(row["immutable"] == "YES" for row in inventory)
    expected = {
        relative: digest
        for digest, relative in (
            line.split("  ", 1)
            for line in (SYNTHESIS / "protected_hashes_before.sha256")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    assert {row["path"]: row["sha256"] for row in inventory} == expected


def test_all_manuscript_claim_tokens_resolve() -> None:
    known = {row["claim_id"] for row in _rows("CLAIM_EVIDENCE_MATRIX.csv")}
    texts = []
    for path in sorted((ROOT / "manuscript").rglob("*.tex")):
        texts.append(path.read_text(encoding="utf-8"))
    used = set(re.findall(r"C-[A-Z0-9]+(?:-[A-Z0-9]+)+", "\n".join(texts)))
    assert used
    assert used <= known, sorted(used - known)


def test_every_section_has_claim_source_outline_visual_and_warning_metadata() -> None:
    for path in sorted((ROOT / "manuscript" / "sections").glob("*.tex")):
        text = path.read_text(encoding="utf-8")
        for marker in (
            "\\paragraph{Purpose.}",
            "\\paragraph{Claim IDs.}",
            "\\paragraph{Source asset IDs.}",
            "\\paragraph{Paragraph outline.}",
            "\\paragraph{Placeholders.}",
            "\\paragraph{Unsupported-wording warning.}",
        ):
            assert marker in text, (path.name, marker)


def test_headline_numbers_map_to_frozen_canonical_evidence() -> None:
    protected = {
        line.split("  ", 1)[1]
        for line in (SYNTHESIS / "protected_hashes_before.sha256")
        .read_text(encoding="utf-8")
        .splitlines()
    }
    rows = _rows("numeric_claim_audit.csv")
    assert len(rows) >= 25
    for row in rows:
        assert row["claim_id"]
        assert row["source_field_or_row"]
        assert row["source_file"] in protected
        assert (ROOT / row["source_file"]).is_file()
        assert row["verification"] == "INTEGRITY_RECOMPUTATION"


def test_unfinished_phase3b_is_not_used_as_evidence() -> None:
    evidence_columns = {
        "CLAIM_EVIDENCE_MATRIX.csv": ["source_files"],
        "empirical_evidence_matrix.csv": ["source_files"],
        "numeric_claim_audit.csv": ["source_file"],
        "figure_table_plan.csv": ["source_data"],
    }
    for name, columns in evidence_columns.items():
        for row in _rows(name):
            for column in columns:
                value = row[column].lower().replace("-", "").replace("_", "")
                assert "phase3b" not in value, (name, column, row[column])


def test_scaffold_has_no_unqualified_prohibited_wording() -> None:
    prohibited = [
        r"demonstrat(?:e|es|ed) (?:a )?quantum advantage",
        r"every explicit rcsp instance requires",
        r"confirmed global (?:empirical )?scaling law",
        r"cvar violates (?:the )?membership",
        r"feasibility-preserving mixer obtains structure for free",
        r"subdivision makes (?:the )?rcsp exponentially harder",
        r"b_eff is (?:automatically )?(?:runtime|gate complexity)",
    ]
    negation = re.compile(r"\b(no|not|never|without|unsupported|do not)\b", re.I)
    for path in sorted((ROOT / "manuscript").rglob("*.tex")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in prohibited:
                if re.search(pattern, line, re.I):
                    assert negation.search(line), (path, number, line)


def test_all_bibliography_keys_resolve() -> None:
    bib = (ROOT / "manuscript" / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{\s*([^,\s]+)", bib))
    assert len(keys) >= 10
    citations: set[str] = set()
    for path in sorted((ROOT / "manuscript").rglob("*.tex")):
        for group in re.findall(r"\\cite\{([^}]+)\}", path.read_text(encoding="utf-8")):
            citations.update(key.strip() for key in group.split(","))
    assert citations
    assert citations <= keys, sorted(citations - keys)


def test_tex_scaffold_has_balanced_braces_environments_and_inputs() -> None:
    tex_files = sorted((ROOT / "manuscript").rglob("*.tex")) + sorted(
        (ROOT / "review_package").glob("*.tex")
    )
    assert tex_files
    for path in tex_files:
        lines = [line.split("%", 1)[0] for line in path.read_text(encoding="utf-8").splitlines()]
        text = "\n".join(lines)
        depth = 0
        escaped = False
        for character in text:
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                assert depth >= 0, path
        assert depth == 0, path
        environment_stack: list[str] = []
        for match in re.finditer(r"\\(begin|end)\{([^}]+)\}", text):
            action, environment = match.groups()
            if action == "begin":
                environment_stack.append(environment)
            else:
                assert environment_stack and environment_stack.pop() == environment, path
        assert not environment_stack, path
    main = (ROOT / "manuscript" / "main.tex").read_text(encoding="utf-8")
    for relative in re.findall(r"\\input\{([^}]+)\}", main):
        assert (ROOT / "manuscript" / f"{relative}.tex").is_file(), relative


def test_figure_table_placeholders_have_plan_rows_and_sources() -> None:
    plan = _rows("figure_table_plan.csv")
    known = {row["visual_id"] for row in plan}
    assert {f"F{i}" for i in range(1, 10)} <= known
    placeholders: set[str] = set()
    for path in sorted((ROOT / "manuscript").rglob("*.tex")):
        placeholders.update(
            re.findall(r"\[([FT]\d+)\b", path.read_text(encoding="utf-8"))
        )
    assert placeholders <= known, sorted(placeholders - known)
    for row in plan:
        assert row["source_data"]
        assert row["claim_ids"]


def test_all_theorem_dependencies_resolve() -> None:
    rows = _rows("theorem_dependency_edges.csv")
    theorem_ids = {f"T{i}" for i in range(1, 12)}
    assert {row["dependent"] for row in rows} == theorem_ids
    assert all(row["independent_human_review_mandatory"] == "YES" for row in rows)
    reviewed = {row["result_id"] for row in _rows("second_pass_proof_review.csv")}
    assert reviewed == theorem_ids


def test_readiness_and_publication_decisions_are_complete() -> None:
    gates = _rows("readiness_gates.csv")
    assert [row["gate_id"] for row in gates] == [f"G{i}" for i in range(1, 10)]
    assert all(row["status"] in {"PASS", "PASS_WITH_LIMITATIONS", "FAIL", "NOT_APPLICABLE"} for row in gates)
    strategies = _rows("publication_strategy_matrix.csv")
    assert sum(row["recommendation"] == "PRIMARY" for row in strategies) == 1
    assert next(row for row in strategies if row["recommendation"] == "PRIMARY")["option"] == "C_EMPIRICAL_PRIMARY"


def test_all_required_synthesis_outputs_exist() -> None:
    names = {
        "SYNTHESIS_INPUT_INVENTORY.csv",
        "second_pass_proof_review.csv",
        "prior_art_search_log.csv",
        "prior_art_comparison_matrix.csv",
        "empirical_evidence_matrix.csv",
        "numeric_claim_audit.csv",
        "CLAIM_EVIDENCE_MATRIX.csv",
        "publication_strategy_matrix.csv",
        "venue_matrix.csv",
        "manuscript_section_matrix.csv",
        "theorem_dependency_edges.csv",
        "figure_table_plan.csv",
        "reviewer_attack_matrix.csv",
        "readiness_gates.csv",
        "failure_census.csv",
        "summary.json",
    }
    assert all((SYNTHESIS / name).is_file() for name in names)
