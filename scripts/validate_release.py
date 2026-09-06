#!/usr/bin/env python3
"""Verify frozen paper results; optionally rebuild assets in a disposable copy."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))


def reconstruct_theory() -> dict:
    """Check numerical bound residuals against frozen summaries, without optimization."""
    import numpy as np
    import pandas as pd

    checks = {}
    specifications = [
        ('v1', 'finite_case_summary.csv', 'numerical_validation_summary.json',
         'average_success', 'phase_sensitive_bound', 'maximum_phase_bound_residual'),
        ('v2', 'adaptive_finite_case_summary.csv', 'adaptive_validation_summary.json',
         'average_success', 'hard_cap_bound', 'maximum_coarse_residual'),
        ('v3', 'posterior_advice_validation.csv', 'posterior_advice_validation_summary.json',
         'actual_average_success', 'coarse_bound', 'maximum_success_residual'),
    ]
    for version, csv_name, json_name, success, bound, summary_key in specifications:
        directory = ROOT / 'results' / f'theory_validation_{version}'
        frame = pd.read_csv(directory / csv_name)
        summary = json.loads((directory / json_name).read_text())
        residual = frame[success].to_numpy() - frame[bound].to_numpy()
        maximum = float(np.max(residual))
        assert abs(maximum - summary[summary_key]) <= 1e-12, version
        assert int((residual > 1e-10).sum()) == summary['violations'] == 0, version
        if version == 'v1':
            assert len(frame) == summary['random_algorithms']
            assert int(frame.n_unique_feasible_sets.sum()) == summary['unique_feasible_sets_across_algorithm_rows']
        else:
            assert len(frame) == summary['protocols' if version == 'v2' else 'parameter_rows']
            assert int(frame.subset_evaluations.sum()) == summary['subset_evaluations']
        checks[version] = {'rows': len(frame), 'maximum_residual': maximum, 'violations': 0}
    directory = ROOT / 'results/theory_validation_v3'
    summary = json.loads((directory / 'explicit_rcsp_validation_summary.json').read_text())
    for name, key in [('raw_phi_counterexamples.csv', 'unique_chain_rows'),
                      ('representation_padding_validation.csv', 'padding_rows'),
                      ('parallel_branch_validation.csv', 'parallel_branch_rows')]:
        frame = pd.read_csv(directory / name)
        assert len(frame) == summary[key], name
    branches = pd.read_csv(directory / 'parallel_branch_validation.csv')
    assert branches.attribute_mapping_ok.astype(str).str.lower().eq('true').all()
    assert summary['construction_failures'] == 0
    checks['explicit_rcsp'] = summary
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-existing-results', '--validate-existing-results',
                        action='store_true', required=True,
                        help='read frozen evidence; never run experimental optimization')
    parser.add_argument('--output-dir', type=Path,
                        help='new directory outside the repository; default: unique temporary directory')
    parser.add_argument('--assets', action='store_true',
                        help='also run legacy publication builders in an isolated copy')
    args = parser.parse_args()
    if args.output_dir is None:
        output = Path(tempfile.mkdtemp(prefix='qroute-validation-'))
    else:
        output = args.output_dir.resolve()
        if output == ROOT or ROOT in output.parents or output in ROOT.parents:
            parser.error('output must be outside the repository')
        output.mkdir(parents=True, exist_ok=False)

    from paper_scripts import rebuild_publication_results as rebuild
    before = rebuild.canonical_hashes()
    for script in ('reproduce_headlines.py', 'reproduce_heldout.py', 'reproduce_scaling_verdict.py'):
        subprocess.run([sys.executable, str(ROOT / 'reproduction' / script),
                        '--output-dir', str(output / 'reconstructed'), '--verify'], check=True, cwd=ROOT)
    universe = rebuild.reconstruct_universe()
    optimizer, _ = rebuild.reconstruct_optimizer()
    discovery, _ = rebuild.reconstruct_discovery()
    heldout, *_ = rebuild.reconstruct_heldout()
    scaling, *_ = rebuild.reconstruct_scaling()
    claims = rebuild.build_claim_audit(universe, optimizer, discovery, heldout, scaling)
    claims.to_csv(output / 'claim_evidence_audit.csv', index=False)
    mismatch = claims[claims.status.ne('PASS')]
    if len(mismatch):
        raise RuntimeError(f'STOP: manuscript/evidence discrepancy: {mismatch.claim_id.tolist()}')
    theory = reconstruct_theory()
    if rebuild.canonical_hashes() != before:
        raise RuntimeError('STOP: canonical inputs changed')
    report = {'status': 'PASS', 'optimizer_invoked': False,
              'claim_checks': len(claims), 'claim_mismatches': 0,
              'canonical_inputs_unchanged': True, 'theory': theory}
    if args.assets:
        # Legacy builders write to project-relative paths. A full disposable copy
        # preserves their behavior and protects both frozen inputs and paper sources.
        workspace = output / 'asset-workspace'
        workspace.mkdir()
        for name in ('src', 'configs', 'data', 'results', 'docs', 'overleaf', 'paper_scripts',
                     'paper_audit', 'manuscript', 'paper', 'tests', 'review_package', 'reproduction'):
            if (ROOT / name).exists():
                shutil.copytree(ROOT / name, workspace / name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.log', '*.sqlite*'))
        shutil.copy2(ROOT / 'pyproject.toml', workspace / 'pyproject.toml')
        subprocess.run([sys.executable, str(workspace / 'paper_scripts/rebuild_publication_results.py')],
                       cwd=workspace, check=True)
        report['assets_rebuilt_in_disposable_copy'] = True
    (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'RELEASE VALIDATION PASS: {output}')


if __name__ == '__main__':
    main()
