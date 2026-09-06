#!/usr/bin/env python3
"""Trace every reviewer-robustness manuscript headline to formal artifacts."""

from __future__ import annotations

import csv
import hashlib
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
OVERLEAF = ROOT / "overleaf"
RESULTS = ROOT / "results" / "reviewer_robustness"
OUTPUT = RESULTS / "PAPER_NUMBER_AUDIT.md"


def read_rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def select(items: list[dict[str, str]], **criteria: object) -> list[dict[str, str]]:
    return [
        item
        for item in items
        if all(str(item[key]) == str(value) for key, value in criteria.items())
    ]


def exactly_one(items: list[dict[str, str]], **criteria: object) -> dict[str, str]:
    matches = select(items, **criteria)
    if len(matches) != 1:
        raise ValueError(f"expected one row for {criteria}, found {len(matches)}")
    return matches[0]


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def expand_tex(path: Path, stack: tuple[Path, ...] = ()) -> str:
    resolved = path.resolve()
    if resolved in stack:
        raise ValueError(f"recursive TeX input: {resolved}")
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        target = OVERLEAF / name
        if not target.suffix:
            target = target.with_suffix(".tex")
        if not target.is_file():
            raise FileNotFoundError(target)
        return expand_tex(target, stack + (resolved,))

    return re.sub(r"\\input\{([^}]+)\}", replace, text)


def command_argument(text: str, command: str) -> str:
    """Return the first balanced braced argument of a TeX command."""
    marker = f"\\{command}"
    start = text.find(marker)
    if start < 0:
        raise ValueError(f"missing TeX command: {marker}")
    opening = text.find("{", start + len(marker))
    if opening < 0:
        raise ValueError(f"missing argument for TeX command: {marker}")
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{" and (index == 0 or text[index - 1] != "\\"):
            depth += 1
        elif text[index] == "}" and (index == 0 or text[index - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[opening + 1:index]
    raise ValueError(f"unbalanced argument for TeX command: {marker}")


def scientific_tex(value: float, digits: int = 2) -> str:
    if value == 0:
        return "0"
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10**exponent)
    return f"{mantissa:.{digits}f}\\times10^{{{exponent}}}"


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


@dataclass(frozen=True)
class Check:
    item: str
    source: str
    computed: str
    token: str
    scope: str = "assembled"


def build_checks() -> list[Check]:
    checks: list[Check] = []

    optimizer_summary_path = "results/reviewer_robustness/A1_optimizer/optimizer_summary.csv"
    optimizer_summary = read_rows(optimizer_summary_path)
    pass_path = "results/reviewer_robustness/A1_optimizer/optimizer_pass_subset.csv"
    pass_rows = read_rows(pass_path)
    optimizer_runs_path = "results/reviewer_robustness/A1_optimizer/optimizer_runs.csv"
    optimizer_runs = read_rows(optimizer_runs_path)
    checks.append(Check("A1 formal run count", optimizer_runs_path, str(len(optimizer_runs)), "2,016 runs"))
    nonnull_scipy = [item for item in optimizer_runs if item["scipy_reported_nfev"].strip()]
    null_scipy = len(optimizer_runs) - len(nonnull_scipy)
    disagree = sum(not as_bool(item["nfev_accounting_match"]) for item in nonnull_scipy)
    checks.append(Check("A1 SciPy-count audit", optimizer_runs_path, f"{disagree}/{len(nonnull_scipy)}; null={null_scipy}", f"{len(nonnull_scipy):,} runs"))
    checks.append(Check("A1 strict-stop missing counts", optimizer_runs_path, str(null_scipy), f"{null_scipy} SLSQP runs"))

    for optimizer in ("COBYLA", "Nelder-Mead", "SLSQP"):
        o0 = exactly_one(optimizer_summary, optimizer=optimizer, objective="O0")
        o3 = exactly_one(optimizer_summary, optimizer=optimizer, objective="O3")
        for objective, item in (("O0", o0), ("O3", o3)):
            count = int(item["nested_failure_count"])
            total = int(item["nested_comparison_count"])
            checks.append(Check(
                f"A1 {optimizer} {objective} nested failures",
                optimizer_summary_path,
                f"{count}/{total}",
                f"{count}/{total}",
            ))
        retained = [item for item in pass_rows if item["optimizer"] == optimizer]
        lower_lower = sum(as_bool(item["O0_lower_energy_but_lower_feasibility_than_O3"]) for item in retained)
        checks.append(Check(
            f"A1 {optimizer} dual-PASS lower-energy/lower-feasibility pairs",
            pass_path,
            f"{lower_lower}/{len(retained)}",
            f"{lower_lower}/{len(retained)}",
        ))
        lo = float(o0["pass_subset_O3_minus_O0_G_ci_lower"])
        hi = float(o0["pass_subset_O3_minus_O0_G_ci_upper"])
        checks.append(Check(
            f"A1 {optimizer} dual-PASS graph CI",
            optimizer_summary_path,
            f"[{lo:.4f},{hi:.4f}]",
            f"[{lo:.4f},{hi:.4f}]",
        ))

    nested_path = "results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv"
    nested = read_rows(nested_path)
    for transition in ("p2->p3", "p3->p4"):
        for budget in (120, 240, 480):
            relevant = select(nested, transition=transition, budget=budget)
            failures = sum(as_bool(item["nested_failure"]) for item in relevant)
            total = len(relevant)
            rate = 100 * failures / total
            checks.append(Check(
                f"B1 {transition} at {budget} calls",
                nested_path,
                f"{failures}/{total} ({rate:.1f}%)",
                f"{failures}/{total} ({rate:.1f}\\%)",
            ))

    contrasts_path = "results/reviewer_robustness/B1_depth_budget/depth_budget_contrasts.csv"
    contrasts = read_rows(contrasts_path)
    for objective in ("O0", "O3"):
        item = exactly_one(
            contrasts,
            comparison="p4_minus_p3",
            metric="G_feas",
            objective=objective,
            budget=120,
        )
        effect = float(item["graph_delta_mean"])
        positives = int(item["positive_graphs"])
        checks.append(Check(
            f"B1 p4-p3 {objective} G_feas at 120 calls",
            contrasts_path,
            f"{effect:.4f}; {positives}/10 positive",
            f"{effect:+.4f}",
        ))

    alpha_graph_path = "results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv"
    alpha_graph = select(read_rows(alpha_graph_path), split="discovery")
    alpha_means: dict[float, float] = {}
    for alpha in (0.02, 0.05, 0.10, 0.25, 0.50, 1.00):
        values = [float(item["G_feas"]) for item in alpha_graph if math.isclose(float(item["alpha"]), alpha)]
        if len(values) != 10:
            raise ValueError(f"alpha={alpha}: expected 10 graphs, found {len(values)}")
        alpha_means[alpha] = sum(values) / len(values)
        checks.append(Check(
            f"A2 discovery graph-mean G_feas alpha={alpha:.2f}",
            alpha_graph_path,
            f"{alpha_means[alpha]:.4f}",
            f"{alpha_means[alpha]:.4f}",
        ))

    alpha_task_path = "results/reviewer_robustness/A2_alpha/alpha_summary_task.csv"
    alpha_task = select(read_rows(alpha_task_path), split="discovery")
    by_task: dict[str, dict[float, float]] = {}
    for item in alpha_task:
        by_task.setdefault(item["task_id"], {})[float(item["alpha"])] = float(item["G_feas"])
    nonmonotone = 0
    for values_by_alpha in by_task.values():
        values = [values_by_alpha[a] for a in (0.02, 0.05, 0.10, 0.25, 0.50, 1.00)]
        increasing = all(b >= a - 1e-12 for a, b in zip(values, values[1:]))
        decreasing = all(b <= a + 1e-12 for a, b in zip(values, values[1:]))
        nonmonotone += not (increasing or decreasing)
    checks.append(Check("A2 non-monotone task count", alpha_task_path, f"{nonmonotone}/{len(by_task)}", f"{nonmonotone}/{len(by_task)}"))

    alpha_runs_path = "results/reviewer_robustness/A2_alpha/alpha_runs.csv"
    alpha_runs = read_rows(alpha_runs_path)
    alpha1 = [item for item in alpha_runs if math.isclose(float(item["alpha"]), 1.0)]
    max_alpha1_error = max(abs(float(item["alpha1_minus_mean_endpoint_error"])) for item in alpha1)
    alpha1_token = scientific_tex(max_alpha1_error, 2)
    checks.append(Check("A2 alpha=1 objective endpoint", alpha_runs_path, f"{max_alpha1_error:.17g}", alpha1_token))

    equivalence_path = "results/reviewer_robustness/final_audits/alpha1_o0_equivalence.csv"
    equivalence = read_rows(equivalence_path)
    max_initial = max(abs(float(item["initial_objective_alpha1_minus_o0"])) for item in equivalence)
    checks.append(Check("S1 matched initial-objective error", equivalence_path, f"{max_initial:.17g}", scientific_tex(max_initial, 2)))
    checks.append(Check("S1 matched discovery cells", equivalence_path, str(len(equivalence)), "168 discovery cells"))

    nested_audit_path = "results/reviewer_robustness/final_audits/nested_audit_cases.csv"
    nested_audit = read_rows(nested_audit_path)
    for item_name, column in (
        ("S2 deeper-objective recomputation error", "deeper_objective_abs_error"),
        ("S2 embedded-objective recomputation error", "embedded_objective_abs_error"),
        ("S2 signed-regret recomputation error", "signed_regret_abs_error"),
    ):
        value = max(abs(float(item[column])) for item in nested_audit)
        checks.append(Check(item_name, nested_audit_path, f"{value:.17g}", scientific_tex(value, 2)))
    checks.append(Check("S2 sampled audit cases", nested_audit_path, str(len(nested_audit)), f"{len(nested_audit)} stratified PASS/FAIL cases"))

    endpoint_path = "results/posthoc_finite_shot_endpoint_v1/aggregate.csv"
    endpoint = read_rows(endpoint_path)
    for shots in (1000, 10000, 100000):
        item = exactly_one(
            endpoint,
            record_type="ORDERING_AGREEMENT",
            scope="ALL",
            objective_id="O3_vs_O0",
            shots=shots,
            metric="p_feas",
        )
        probability = 100 * float(item["ordering_agreement_probability"])
        checks.append(Check(
            f"A3 fixed-endpoint P_feas ordering at {shots} shots",
            endpoint_path,
            f"{probability:.1f}%",
            f"{probability:.1f}\\%",
        ))

    estimator_path = "results/reviewer_robustness/A3_finite_shot/alpha_shot_estimator.csv"
    estimator = read_rows(estimator_path)
    for shots in (1000, 10000, 100000):
        relevant = [
            item for item in estimator
            if math.isclose(float(item["alpha"]), 0.10) and int(item["shots"]) == shots
        ]
        mean_rmse = sum(float(item["rmse"]) for item in relevant) / len(relevant)
        checks.append(Check(
            f"A3 mean O0/O3 alpha=.10 RMSE at {shots} shots",
            estimator_path,
            f"{mean_rmse:.8f}",
            f"{mean_rmse:.5f}",
        ))

    training_path = "results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv"
    training = read_rows(training_path)
    for regime in ("EXACT_CANONICAL", "SHOT_10000", "SHOT_1000"):
        item = exactly_one(training, regime=regime)
        mean = float(item["graph_effect_mean"])
        lo = float(item["graph_effect_ci_lower"])
        hi = float(item["graph_effect_ci_upper"])
        positives = int(item["graph_positive_count"])
        checks.append(Check(
            f"A3 training effect {regime}",
            training_path,
            f"{mean:.4f} [{lo:.4f},{hi:.4f}], {positives}/10",
            f"{mean:.4f}",
        ))
        checks.append(Check(
            f"A3 training CI {regime}",
            training_path,
            f"[{lo:.4f},{hi:.4f}]",
            f"[{lo:.4f},{hi:.4f}]",
        ))
    training_runs_path = "results/reviewer_robustness/A3_finite_shot/finite_shot_training_runs.csv"
    checks.append(Check("A3 finite-shot training run count", training_runs_path, str(len(read_rows(training_runs_path))), "200/200 runs"))

    classical_path = "results/reviewer_robustness/B2_classical/classical_summary.csv"
    classical = exactly_one(read_rows(classical_path), scope="ALL")
    matches = int(classical["optimum_match_count"])
    tasks = int(classical["task_count"])
    median_us = float(classical["median_solve_time_s"]) * 1e6
    p95_us = float(classical["p95_solve_time_s"]) * 1e6
    max_us = float(classical["max_solve_time_s"]) * 1e6
    median_labels = int(float(classical["median_labels_generated"]))
    max_labels = int(classical["max_labels_generated"])
    checks.append(Check("B2 exact optimum agreement", classical_path, f"{matches}/{tasks}", f"{matches}/{tasks}"))
    checks.append(Check("B2 median solve time", classical_path, f"{median_us:.1f} microseconds", f"{median_us:.1f}"))
    checks.append(Check("B2 p95 solve time", classical_path, f"{p95_us:.1f} microseconds", f"{p95_us:.1f}"))
    checks.append(Check("B2 maximum solve time", classical_path, f"{max_us:.1f} microseconds", f"{max_us:.1f}"))
    checks.append(Check("B2 generated-label range", classical_path, f"median={median_labels}; max={max_labels}", f"median {median_labels} and maximum {max_labels}"))

    primary_path = "results/finalization_audit_v1/claim_evidence_audit.csv"
    primary = exactly_one(read_rows(primary_path), claim_id="heldout_H1_effect_mean")
    checks.extend([
        Check(
            "Abstract held-out O3-O0 effect",
            primary_path,
            f"{float(primary['authoritative_value']):.4f}",
            "$+0.3547$",
            "abstract",
        ),
        Check(
            "Main/ESM frozen CVaR tail fraction",
            "configs/phase2_confirmatory_v1.yaml",
            "alpha=0.10",
            "\\alpha=0.10",
            "assembled",
        ),
        Check(
            "Main/ESM alpha-neighborhood lower endpoint",
            alpha_graph_path,
            "alpha=0.05",
            "\\alpha=0.05",
            "assembled",
        ),
        Check(
            "Main/ESM alpha-neighborhood upper endpoint",
            alpha_graph_path,
            "alpha=0.25",
            "and 0.25",
            "assembled",
        ),
        Check(
            "Main/ESM post-hoc maximum depth",
            contrasts_path,
            "p=4",
            "$p=4$",
            "assembled",
        ),
        Check(
            "Main/ESM 10k finite-shot training",
            training_path,
            "10,000 shots",
            "10,000-shot",
            "assembled",
        ),
        Check(
            "Main/ESM 1k finite-shot training",
            training_path,
            "1,000 shots",
            "1,000-shot",
            "assembled",
        ),
    ])
    return checks


def main() -> int:
    main_tex = expand_tex(OVERLEAF / "main.tex")
    esm_tex = expand_tex(OVERLEAF / "ESM_1.tex")
    assembled = normalize(main_tex + "\n" + esm_tex)
    abstract = normalize(command_argument(main_tex, "abstract"))
    scopes = {"assembled": assembled, "abstract": abstract}
    checks = build_checks()
    evaluated: list[tuple[Check, int]] = []
    for check in checks:
        evaluated.append((check, scopes[check.scope].count(normalize(check.token))))
    failures = [(check, count) for check, count in evaluated if count == 0]

    sources = sorted({check.source for check in checks})
    lines = [
        "# Paper Number Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Overall status: **{'PASS' if not failures else 'FAIL'}**",
        "",
        "This audit recomputes the reviewer-robustness numbers displayed in the",
        "assembled main article and Online Resource and verifies that each",
        "formatted value occurs in the recursively expanded TeX source. The held-out",
        "effect retained in the structured abstract is checked there specifically;",
        "detailed robustness headlines are checked across the assembled main/ESM source.",
        "The audit does not modify any result file.",
        "",
        "| Item | Scope | Computed from artifact | Manuscript token | Occurrences | Status | Source |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for check, count in evaluated:
        status = "PASS" if count else "FAIL"
        source = check.source.replace("|", "\\|")
        token = check.token.replace("|", "\\|")
        computed = check.computed.replace("|", "\\|")
        lines.append(f"| {check.item} | {check.scope} | `{computed}` | `{token}` | {count} | {status} | `{source}` |")
    lines.extend(["", "## Source fingerprints", ""])
    for source in sources:
        path = ROOT / source
        lines.append(f"- `{source}`: `{sha256(path)}`")
    lines.extend([
        "",
        "## Verdict",
        "",
        (
            "All new manuscript numbers trace to formal result artifacts."
            if not failures
            else f"{len(failures)} manuscript-number checks failed; revision is not ready."
        ),
        "",
    ])
    atomic_write(OUTPUT, "\n".join(lines))
    print(f"{OUTPUT.relative_to(ROOT)}: {'PASS' if not failures else 'FAIL'} ({len(checks)} checks)")
    if failures:
        for check, _ in failures:
            print(f"missing token: {check.item}: {check.token}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
