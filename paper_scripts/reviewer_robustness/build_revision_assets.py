#!/usr/bin/env python3
"""Build manuscript assets for the frozen reviewer-robustness results.

The script only writes the new reviewer-revision asset names listed below.
It also records a one-time snapshot of the Overleaf text sources before the
revision so pre-existing manuscript edits remain distinguishable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
OVERLEAF = ROOT / "overleaf"
RESULTS = ROOT / "results" / "reviewer_robustness"
REVISION = RESULTS / "paper_revision"

FIGURES = {
    RESULTS / "B1_depth_budget" / "figures" / "Figure_R1_depth_budget.pdf":
        OVERLEAF / "figures" / "fig12_reviewer_depth_budget.pdf",
    RESULTS / "A1_optimizer" / "figures" / "optimizer_objective_effect.pdf":
        OVERLEAF / "figures" / "fig13_reviewer_optimizer_robustness.pdf",
    RESULTS / "A2_alpha" / "figures" / "Figure_R2_alpha_sensitivity.pdf":
        OVERLEAF / "figures" / "fig14_reviewer_alpha_sensitivity.pdf",
    RESULTS / "A3_finite_shot" / "figures" / "Figure_R3_finite_shot_training.pdf":
        OVERLEAF / "figures" / "fig15_reviewer_finite_shot_training.pdf",
    RESULTS / "A3_finite_shot" / "figures" / "Figure_R4_alpha_shots.pdf":
        OVERLEAF / "figures" / "fig16_reviewer_alpha_shots.pdf",
}


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


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def one(items: Iterable[dict[str, str]], **criteria: object) -> dict[str, str]:
    matches = [
        item
        for item in items
        if all(str(item[key]) == str(value) for key, value in criteria.items())
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one row for {criteria}, found {len(matches)}")
    return matches[0]


def snapshot_before_revision() -> None:
    target = REVISION / "pre_revision_overleaf_snapshot.json"
    if target.exists():
        return
    source_files = sorted(
        path
        for path in OVERLEAF.rglob("*")
        if path.is_file() and path.suffix.lower() in {".tex", ".bib", ".md"}
    )
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in source_files
    ]
    aggregate = hashlib.sha256()
    for item in entries:
        aggregate.update(item["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(item["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    git_status = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    payload = {
        "schema": "reviewer-paper-pre-revision-snapshot-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_count": len(entries),
        "aggregate_sha256": aggregate.hexdigest(),
        "sources": entries,
        "git_status_short": git_status,
    }
    atomic_write(target, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def copy_figures() -> None:
    for source, destination in FIGURES.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and sha256(source) == sha256(destination):
            continue
        shutil.copy2(source, destination)


def build_optimizer_table() -> None:
    data = rows(RESULTS / "A1_optimizer" / "optimizer_summary.csv")
    pass_data = rows(RESULTS / "A1_optimizer" / "optimizer_pass_subset.csv")
    labels = {"COBYLA": "COBYLA", "Nelder-Mead": "Nelder--Mead", "SLSQP": "SLSQP"}
    body: list[str] = []
    for optimizer in ("COBYLA", "Nelder-Mead", "SLSQP"):
        o0 = one(data, optimizer=optimizer, objective="O0")
        o3 = one(data, optimizer=optimizer, objective="O3")
        relevant = [item for item in pass_data if item["optimizer"] == optimizer]
        lower_lower = sum(
            item["O0_lower_energy_but_lower_feasibility_than_O3"].lower() == "true"
            for item in relevant
        )
        n_pass = int(o0["certified_pass_pair_count"])
        lo = float(o0["pass_subset_O3_minus_O0_G_ci_lower"])
        hi = float(o0["pass_subset_O3_minus_O0_G_ci_upper"])
        body.append(
            f"{labels[optimizer]} & "
            f"{int(o0['nested_failure_count'])}/{int(o0['nested_comparison_count'])} & "
            f"{int(o3['nested_failure_count'])}/{int(o3['nested_comparison_count'])} & "
            f"{n_pass} & {lower_lower}/{n_pass} & "
            f"$[{lo:.4f},{hi:.4f}]$ \\\\"
        )
    text = r"""% Generated by paper_scripts/reviewer_robustness/build_revision_assets.py.
\begin{table}[t]
\centering
\caption{Optimizer robustness on 56 discovery tasks and three fixed seeds.
Nested failures compare the best $p=3$ point with the exactly embedded $p=2$
point under 120 actual objective calls. The last two columns retain only pairs
for which both O0 and O3 pass that diagnostic; the interval is a 95\% graph-
cluster bootstrap CI for O3-minus-O0 $\gfeas$. Configurations are diagnostic,
not an optimizer ranking.}
\label{tab:reviewer-optimizer}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lrrrrl@{}}
\toprule
Optimizer & \shortstack{O0 nested\\failure} & \shortstack{O3 nested\\failure}
& \shortstack{dual-PASS\\pairs} & \shortstack{O0 lower energy,\\lower $\pfeas$}
& \shortstack{PASS-only $\Delta\gfeas$\\graph CI} \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    atomic_write(OVERLEAF / "tables" / "table08_reviewer_optimizer.tex", text)


def build_protocol_table() -> None:
    text = r"""% Generated by paper_scripts/reviewer_robustness/build_revision_assets.py.
\begin{table}[t]
\centering
\caption{Frozen post-hoc reviewer-robustness protocols. All task selections
used graph and structural variables only. Additional tail fractions and all
robustness intervals are exploratory and do not enter the preregistered H1/H2
family.}
\label{tab:reviewer-protocols}
\small
\begin{tabularx}{\textwidth}{@{}l>{\raggedright\arraybackslash}p{2.6cm}>{\raggedright\arraybackslash}X@{}}
\toprule
Study & Scope & Frozen factors \\
\midrule
Optimizer & 56 discovery tasks, 10 graphs & COBYLA, Nelder--Mead, SLSQP; O0/O3; $p=2,3$; three seeds; 120 actual objective calls \\
Tail fraction & 56 discovery tasks, 10 graphs & $\alpha\in\{.02,.05,.10,.25,.50,1\}$; COBYLA; $p=3$; three seeds; 120 calls \\
Depth--budget & 24 discovery tasks, 10 graphs & $p\in\{2,3,4\}$; 120/240/480-call prefixes; O0/O3; COBYLA; three seeds \\
Finite-shot training & 10 held-out tasks, 10 graphs & O0/O3; $p=3$; 1,000/10,000 shots per call; five seeds; 240-call cap \\
Classical context & All 140 canonical tasks, 25 graphs & Exact instrumented label-setting; repeated descriptive timing \\
\bottomrule
\end{tabularx}
\end{table}
"""
    atomic_write(OVERLEAF / "tables" / "tableS6_reviewer_protocols.tex", text)


def build_depth_table() -> None:
    nested = rows(RESULTS / "B1_depth_budget" / "figure_data_nested_failure.csv")
    contrasts = rows(RESULTS / "B1_depth_budget" / "depth_budget_contrasts.csv")
    body: list[str] = []
    for budget in (120, 240, 480):
        p23 = [item for item in nested if item["transition"] == "p2->p3" and int(item["budget"]) == budget]
        p34 = [item for item in nested if item["transition"] == "p3->p4" and int(item["budget"]) == budget]
        fail23 = sum(int(item["nested_failure_count"]) for item in p23)
        n23 = sum(int(item["nested_comparison_count"]) for item in p23)
        fail34 = sum(int(item["nested_failure_count"]) for item in p34)
        n34 = sum(int(item["nested_comparison_count"]) for item in p34)
        o0 = one(contrasts, comparison="p4_minus_p3", metric="G_feas", objective="O0", budget=budget)
        o3 = one(contrasts, comparison="p4_minus_p3", metric="G_feas", objective="O3", budget=budget)
        body.append(
            f"{budget} & {fail23}/{n23} ({100*fail23/n23:.1f}\\%) & "
            f"{fail34}/{n34} ({100*fail34/n34:.1f}\\%) & "
            f"{float(o0['graph_delta_mean']):.4f} & {float(o3['graph_delta_mean']):.4f} & "
            f"{int(o0['positive_graphs'])}/10; {int(o3['positive_graphs'])}/10 \\\\"
        )
    text = r"""% Generated by paper_scripts/reviewer_robustness/build_revision_assets.py.
\begin{table}[t]
\centering
\caption{Depth--budget ablation on the pre-frozen 24-task subset. Failure
counts pool O0 and O3 over three seeds. $p=4-p=3$ effects are equal-weight
graph means in $\gfeas$; the last column gives positive-graph counts for
O0; O3. Checkpoints are the best evaluated incumbents in verified trajectory
prefixes.}
\label{tab:reviewer-depth-budget}
\small
\begin{tabular}{@{}rrrrrr@{}}
\toprule
$N_{\rm fev}$ & $p2\to p3$ failure & $p3\to p4$ failure & \shortstack{$p4-p3$\\O0 $\gfeas$} & \shortstack{$p4-p3$\\O3 $\gfeas$} & \shortstack{positive graphs\\O0; O3} \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    atomic_write(OVERLEAF / "tables" / "tableS7_depth_budget.tex", text)


def build_alpha_table() -> None:
    data = rows(RESULTS / "A2_alpha" / "alpha_summary_graph.csv")
    discovery = [item for item in data if item["split"] == "discovery"]
    means: dict[float, float] = {}
    for alpha in (0.02, 0.05, 0.10, 0.25, 0.50, 1.00):
        vals = [float(item["G_feas"]) for item in discovery if float(item["alpha"]) == alpha]
        if len(vals) != 10:
            raise ValueError(f"alpha {alpha}: expected 10 discovery graphs, found {len(vals)}")
        means[alpha] = sum(vals) / len(vals)
    body = [
        f"{alpha:.2f} & {means[alpha]:.4f} & {means[alpha]-means[0.10]:+.4f} \\\\"
        for alpha in (0.02, 0.05, 0.10, 0.25, 0.50, 1.00)
    ]
    text = r"""% Generated by paper_scripts/reviewer_robustness/build_revision_assets.py.
\begin{table}[t]
\centering
\caption{Post-hoc CVaR tail-fraction sensitivity on 56 discovery tasks.
Values are equal-weight means over ten graph aggregates. The frozen
confirmatory choice remains $\alpha=0.10$; the final column is descriptive.}
\label{tab:reviewer-alpha}
\small
\begin{tabular}{@{}rrr@{}}
\toprule
$\alpha$ & Graph-mean $\gfeas$ & Difference from $\alpha=0.10$ \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    atomic_write(OVERLEAF / "tables" / "tableS8_alpha_sensitivity.tex", text)


def build_finite_shot_table() -> None:
    data = rows(RESULTS / "A3_finite_shot" / "finite_shot_training_effect_summary.csv")
    order = (("EXACT_CANONICAL", "Exact training"), ("SHOT_10000", "10,000-shot training"), ("SHOT_1000", "1,000-shot training"))
    body: list[str] = []
    for regime, label in order:
        item = one(data, regime=regime)
        mean = float(item["graph_effect_mean"])
        lo = float(item["graph_effect_ci_lower"])
        hi = float(item["graph_effect_ci_upper"])
        body.append(
            f"{label} & {int(item['graph_positive_count'])}/10 & {mean:.4f} & "
            f"$[{lo:.4f},{hi:.4f}]$ \\\\"
        )
    text = r"""% Generated by paper_scripts/reviewer_robustness/build_revision_assets.py.
\begin{table}[t]
\centering
\caption{O3-minus-O0 finite-shot training effects on ten pre-frozen tasks
from ten held-out graphs. Final parameters are evaluated exactly; intervals
are 95\% graph-cluster bootstrap CIs. The exact row uses the matched canonical
endpoints for the same tasks.}
\label{tab:reviewer-finite-training}
\small
\begin{tabular}{@{}lrrl@{}}
\toprule
Training regime & Positive graphs & Mean $\Delta\gfeas$ & Graph CI \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    atomic_write(OVERLEAF / "tables" / "tableS9_finite_shot_training.tex", text)


def build_classical_table() -> None:
    item = one(rows(RESULTS / "B2_classical" / "classical_summary.csv"), scope="ALL")
    median_us = float(item["median_solve_time_s"]) * 1e6
    p95_us = float(item["p95_solve_time_s"]) * 1e6
    max_us = float(item["max_solve_time_s"]) * 1e6
    text = rf"""% Generated by paper_scripts/reviewer_robustness/build_revision_assets.py.
\begin{{table}}[t]
\centering
\caption{{Exact classical RCSP context. Times are descriptive medians of
repeated high-resolution measurements and are not compared with statevector
runtime or hardware performance.}}
\label{{tab:reviewer-classical}}
\small
\begin{{tabular}}{{@{{}}rrrrrr@{{}}}}
\toprule
Optimum matches & Median time ($\mu$s) & p95 ($\mu$s) & Max ($\mu$s) & \shortstack{{Median generated\\labels}} & \shortstack{{Maximum generated\\labels}} \\
\midrule
{int(item['optimum_match_count'])}/{int(item['task_count'])} & {median_us:.1f} & {p95_us:.1f} & {max_us:.1f} & {float(item['median_labels_generated']):.0f} & {int(item['max_labels_generated'])} \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    atomic_write(OVERLEAF / "tables" / "tableS10_classical_context.tex", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-snapshot", action="store_true")
    args = parser.parse_args()
    if not args.no_snapshot:
        snapshot_before_revision()
    copy_figures()
    build_optimizer_table()
    build_protocol_table()
    build_depth_table()
    build_alpha_table()
    build_finite_shot_table()
    build_classical_table()
    outputs = [destination.relative_to(ROOT).as_posix() for destination in FIGURES.values()]
    outputs.extend(
        [
            "overleaf/tables/table08_reviewer_optimizer.tex",
            "overleaf/tables/tableS6_reviewer_protocols.tex",
            "overleaf/tables/tableS7_depth_budget.tex",
            "overleaf/tables/tableS8_alpha_sensitivity.tex",
            "overleaf/tables/tableS9_finite_shot_training.tex",
            "overleaf/tables/tableS10_classical_context.tex",
        ]
    )
    print(json.dumps({"status": "ok", "outputs": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
