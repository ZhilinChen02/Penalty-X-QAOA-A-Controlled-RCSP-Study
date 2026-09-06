#!/usr/bin/env python3
"""Recreate missing instance JSON in a new external directory, verifying frozen identities."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='new external directory; default: temporary')
    args = parser.parse_args()
    if args.output_dir is None:
        output = Path(tempfile.mkdtemp(prefix='qroute-instances-'))
    else:
        output = args.output_dir.resolve()
        if output == ROOT or ROOT in output.parents or output in ROOT.parents:
            parser.error('output must be outside the repository')
        output.mkdir(parents=True, exist_ok=False)

    import pandas as pd
    from qroute_dilution.graph_generator import generate_layered_graph
    from qroute_dilution.io import load_config, write_task
    from qroute_dilution.models import Task
    from qroute_dilution.rcsp import enumerate_simple_routes, solve_exact_rcsp
    from qroute_dilution.reviewer_robustness.common import task_from_manifest_row

    roots = [('phase0_v2_dilution_stress', 'phase0_v2_dilution_stress.json'),
             ('phase3_scaling_v1', 'phase3_scaling_v1/task_universe.json')]
    count = {}
    for stage, manifest_name in roots:
        manifest = json.loads((ROOT / 'data/manifests' / manifest_name).read_text())
        characterization = pd.read_csv(ROOT / 'results' / stage / 'task_characterization.csv').set_index('task_id')
        family = {r['base_instance_id']: r for r in manifest['families']}
        config = load_config(ROOT / 'configs/phase3_scaling_v1.yaml')
        graph_cache = {}
        for row in manifest['tasks']:
            if stage == 'phase0_v2_dilution_stress':
                task = task_from_manifest_row(row)
            else:
                f = family[row['base_instance_id']]
                if f['base_instance_id'] not in graph_cache:
                    graph = generate_layered_graph(
                        target_n_edges=f['target_n_edges'], layer_widths=f['layer_widths'],
                        seed=f['generation_seed'], cost_range=tuple(config['cost_range']),
                        resource_range=tuple(config['resource_range']))
                    assert graph.graph_id == f['base_graph_id']
                    graph_cache[f['base_instance_id']] = (graph, enumerate_simple_routes(graph))
                graph, routes = graph_cache[f['base_instance_id']]
                feasible, optimal, cost = solve_exact_rcsp(routes, row['budget'])
                raw = (f"phase3|{row['base_instance_id']}|L{row['dilution_level']}|"
                       f"{row['intended_feasible_routes']}|{row['budget']:.17g}")
                assert 'task-p3-' + hashlib.sha256(raw.encode()).hexdigest()[:16] == row['task_id']
                assert len(feasible) == row['actual_feasible_routes']
                task = Task(row['task_id'], row['base_instance_id'], f"m{row['size_m']}",
                            f"L{row['dilution_level']}", row['target_n_edges'], row['actual_n_edges'],
                            f['generation_seed'], row['budget'], math.nan, False, False,
                            graph, routes, feasible, optimal, cost,
                            task_build_time_s=0.0, exact_reference_time_s=0.0)
            ref = characterization.loc[task.task_id]
            assert task.graph.graph_id == ref.get('graph_id', ref.get('base_graph_id'))
            assert len(task.feasible_routes) == int(ref['n_feasible_states'])
            assert len(task.optimal_routes) == int(ref['n_optimal_states'])
            assert abs(task.optimal_cost - float(ref['optimal_cost'])) < 1e-12
            target = (output / row['task_path']).resolve()
            if output not in target.parents:
                raise ValueError('task manifest path escapes output directory')
            write_task(target, task)
        count[stage] = len(manifest['tasks'])
    (output / 'instance_validation.json').write_text(json.dumps({'counts': count,
        'optimizer_invoked': False, 'timings': 'new payload timing fields are not canonical scientific results'}, indent=2) + '\n')
    print(f'INSTANCE VALIDATION PASS: {count}; {output}')


if __name__ == '__main__':
    main()
