#!/usr/bin/env python3
"""Verify compact frozen evidence without optimization or scaling refits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import numpy as np
import pandas as pd
from qroute_dilution import publication as frozen


def require(condition, message):
    if not condition:
        raise RuntimeError('Verification failed: ' + message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(root=ROOT):
    manifest = json.loads((root / 'results/manifest.json').read_text())
    paths = [r['path'] for r in manifest['files']]
    require(len(paths) == len(set(paths)), 'duplicate manifest entries')
    for row in manifest['files']:
        path = (root / row['path']).resolve()
        require(root.resolve() in path.parents, 'manifest path escapes repository')
        require(path.is_file(), 'missing ' + row['path'])
        require(digest(path) == row['sha256'], 'checksum mismatch: ' + row['path'])
        if 'rows' in row:
            with path.open(newline='') as handle:
                reader = csv.reader(handle)
                require(next(reader) == row['columns'], 'column schema: ' + row['path'])
                require(sum(1 for _ in reader) == row['rows'], 'row count: ' + row['path'])
    return manifest


def verify_original(original, manifest):
    """Optional byte/projection comparison to the unmodified research checkout."""
    def equivalent(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(
                k == 'host' or equivalent(a[k], b[k]) for k in a)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
        if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
            return True
        return type(a) is type(b) and a == b

    compared = 0
    for row in manifest['files']:
        origin = row.get('original_path')
        if not origin:
            continue
        source, target = original / origin, ROOT / row['path']
        require(source.is_file(), 'original missing: ' + origin)
        if row.get('projection'):
            with source.open(newline='') as handle:
                old = list(csv.DictReader(handle))
            with target.open(newline='') as handle:
                new = list(csv.DictReader(handle))
            projected = [{k: item[v] for k, v in row['projection'].items()} for item in old]
            require(new == projected, 'original table projection: ' + origin)
        elif digest(source) != digest(target):
            # Previously published privacy redactions are retained. Only the
            # hostname field may differ in JSON; no numerical field may differ.
            if target.suffix == '.json':
                require(equivalent(json.loads(source.read_text()), json.loads(target.read_text())),
                        'original JSON values: ' + origin)
            elif row.get('privacy_redacted_document'):
                require(digest(source) == row['original_sha256'], 'original document: ' + origin)
            else:
                raise RuntimeError('Original bytes differ: ' + origin)
        compared += 1
    return compared


def verify_benchmark():
    names = ['phase0_v2_dilution_stress.json', 'phase1_pilot_v1.json', 'phase2_confirmatory_v1.json']
    manifests = [json.loads((ROOT / 'data/manifests' / name).read_text()) for name in names]
    tasks = [{r['task_id'] for r in m['tasks']} for m in manifests]
    graphs = [{r['base_instance_id'] for r in m['tasks']} for m in manifests]
    require([len(s) for s in tasks] == [140, 56, 84], 'benchmark task counts')
    require([len(s) for s in graphs] == [25, 10, 15], 'benchmark graph counts')
    require(not tasks[1] & tasks[2] and tasks[1] | tasks[2] == tasks[0], 'task split')
    require(not graphs[1] & graphs[2] and graphs[1] | graphs[2] == graphs[0], 'graph split')
    universe = json.loads((ROOT / 'data/manifests/phase3_scaling_v1/task_universe.json').read_text())
    require(universe['task_count'] == 180 and universe['base_graph_count'] == 30, 'Phase 3 counts')
    require(len({r['task_id'] for r in universe['tasks']}) == 180, 'Phase 3 unique tasks')
    require({r['size_m'] for r in universe['tasks']} == {12, 14, 16, 18, 20, 22}, 'Phase 3 sizes')
    return {'corrected_tasks': 140, 'discovery_tasks': 56, 'heldout_tasks': 84,
            'scaling_tasks': 180}


def verify_scaling():
    directory = ROOT / 'results/phase3_scaling_v1'
    rows = pd.read_csv(directory / 'canonical_results.csv')
    exponents = pd.read_csv(directory / 'base_graph_exponents.csv')
    reference = json.loads((ROOT / 'results/canonical/headlines.json').read_text())['scaling']
    require(len(rows) == 1080 and rows.run_id.nunique() == 1080, 'complete scaling run matrix')
    require(rows.task_id.nunique() == 180, 'scaling task coverage')
    require(len(exponents) == 75, 'stored graph/objective exponent count')
    means = exponents[exponents.size_m.eq(20)].groupby('objective').eta.mean().to_dict()
    for objective in ('O0', 'O2', 'O3'):
        require(abs(means[objective] - reference['m20'][objective]['mean_eta']) <= 5e-12,
                'stored m=20 exponent: ' + objective)
    require(means['O3'] > means['O0'], 'm=20 ordering reversal')
    censored = rows[rows.size_m.eq(22)]
    require(len(censored) == 180 and censored.execution_status.eq('RESOURCE_CENSORED').all(),
            'm=22 resource-censored rows')
    require(frozen.bool_series(censored.resource_censored).all(), 'm=22 censoring flags')
    for column in ['objective_final', 'p_feas', 'p_opt', 'terminal_parameters']:
        require(censored[column].isna().all(), 'censored outcomes must remain unavailable: ' + column)
    preflight = pd.read_csv(directory / 'resource_preflight.csv')
    m22 = preflight[preflight.size_m.eq(22)]
    require(len(m22) == 1 and frozen.bool_series(m22.resource_censored).all()
            and not frozen.bool_series(m22.resource_guard_pass).any(), 'm=22 preflight boundary')
    return {'m20': means, 'm20_ordering_reversal': True, 'm22_resource_censored': True}


def verify_figures(manifest):
    import _plot_figures as plot
    covered = {r['path'] for r in manifest['files']}
    require(set(plot.INPUTS) <= covered, 'unverified figure inputs')
    for i in range(1, 5):
        for extension in ('pdf', 'png'):
            require(f'figures/main/fig{i}.{extension}' in covered, 'missing main figure')
    # Validate the stored depth gains/intervals used by Figure 4, with no refit.
    plot.depth_effects()


def verify():
    manifest = verify_manifest()
    benchmark = verify_benchmark()
    universe = frozen.reconstruct_universe()
    optimizer, _ = frozen.reconstruct_optimizer()
    discovery, _ = frozen.reconstruct_discovery()
    heldout, _, graphs, _ = frozen.reconstruct_heldout()
    require(frozen.compare_graph_rows(graphs) <= 5e-12, 'held-out graph contrasts')
    stored = json.loads((ROOT / 'results/phase2_confirmatory_v1/confirmatory_statistics.json').read_text())
    for hypothesis in ('H1', 'H2'):
        for key in ('effect_mean', 'one_sided_95_lower_bound', 'bootstrap_standard_error',
                    'raw_p_value', 'holm_adjusted_p_value', 'null_margin'):
            require(abs(heldout[hypothesis][key] - stored[hypothesis][key]) <= 5e-12,
                    f'{hypothesis} {key}')
        require(heldout[hypothesis]['pass'], hypothesis + ' frozen decision')
        require(heldout[hypothesis]['holm_adjusted_p_value'] == 0.000244140625,
                hypothesis + ' Holm p-value')
    scaling = verify_scaling()
    values = {
        'task_universe_count': universe['task_count'],
        'duplicate_primary_feasible_sets': universe['duplicate_primary_feasible_sets'],
        'nested_identity': optimizer['nested_identity_pass_count'],
        'certified_optimizer_failures': optimizer['certified_optimizer_failures'],
        'continuation_objective_repairs': optimizer['continuation_objective_repairs'],
        'continuation_feasibility_improvements': optimizer['continuation_feasibility_improvements'],
        'energy_feasibility_mismatch': optimizer['lower_energy_and_lower_feasibility_gain'],
        'discovery_cvar_gap_closure_percent': discovery['median_cvar_gap_closure_percent'],
        'heldout_H2_margin': heldout['H2']['null_margin'],
        'heldout_Popt_wins': heldout['secondary']['O3_vs_O0_P_opt_wins'],
        'heldout_both_wins': heldout['secondary']['O3_vs_O0_both_Pfeas_Popt_wins'],
        'm20_ordering_reversal': True, 'm22_resource_censor': True,
    }
    for h, keys in [('H1', ['effect_mean', 'one_sided_95_lower_bound', 'holm_adjusted_p_value']),
                    ('H2', ['effect_mean', 'one_sided_95_lower_bound'])]:
        values.update({f'heldout_{h}_{k}': heldout[h][k] for k in keys})
    values.update({f'm20_mean_eta_{o}': v for o, v in scaling['m20'].items()})
    with (ROOT / 'results/headline_results.csv').open(newline='') as handle:
        expected = list(csv.DictReader(handle))
    require(len(expected) == len(values) == 21, 'headline claim coverage')
    for row in expected:
        value = row['value']
        ref = {'True': 1.0, 'False': 0.0}.get(value)
        if ref is None:
            ref = float(value)
        require(abs(float(values[row['claim']]) - ref) <= 5e-12, 'headline: ' + row['claim'])
    require(round(discovery['median_cvar_gap_closure_percent'], 4) == 97.8783, 'displayed CVaR closure')
    require(round(heldout['H1']['effect_mean'], 4) == 0.3547, 'displayed H1')
    require(round(heldout['H2']['effect_mean'], 4) == -0.0086, 'displayed H2')
    finite = pd.read_csv(ROOT / 'results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv')
    noisy = finite[finite.shots_per_evaluation.gt(0)]
    require(len(noisy) == 2 and (noisy.graph_effect_ci_lower < 0).all()
            and (noisy.graph_effect_ci_upper > 0).all(), 'post-hoc finite-shot intervals')
    theory = frozen.reconstruct_theory()
    verify_figures(manifest)
    return {'status': 'PASS', 'claims': len(values), 'benchmark': benchmark,
            'H1': heldout['H1'], 'H2': heldout['H2'], 'scaling': scaling,
            'theory': theory, 'optimizer_invoked': False, 'scaling_refit_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-checkout', type=Path,
                        help='optional read-only comparison to the original research checkout')
    args = parser.parse_args()
    report = verify()
    if args.original_checkout:
        count = verify_original(args.original_checkout.resolve(), verify_manifest())
        print(f'Original frozen files/projections: {count} PASS')
    for message in ['Canonical result verification: PASS', 'Headline claims: PASS',
                    'Benchmark manifest: PASS', 'Figures: PASS', 'Scientific results modified: NO']:
        print(message)
    return report


if __name__ == '__main__':
    main()
