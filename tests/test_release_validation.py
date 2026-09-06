"""Portable release checks supplement, rather than replace, scientific regressions."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(relative):
    spec = importlib.util.spec_from_file_location('release_helper', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_output_checks_use_unchanged_reference_hashes(tmp_path):
    helper = _load('reproduction/_reproduction_common.py')
    reference = ROOT / 'reproduction/rebuilt/headlines.json'
    output = tmp_path / reference.name
    output.write_bytes(reference.read_bytes())
    helper.verify(output)
    output.write_bytes(output.read_bytes() + b' ')
    with pytest.raises(RuntimeError, match='hash mismatch'):
        helper.verify(output)
    with pytest.raises(ValueError, match='outside'):
        helper.output_directory(ROOT / 'results')


def test_frozen_headline_and_theory_reconstruction():
    sys.path.insert(0, str(ROOT))
    from paper_scripts import rebuild_publication_results as rebuild
    helper = _load('scripts/validate_release.py')
    universe = rebuild.reconstruct_universe()
    optimizer, _ = rebuild.reconstruct_optimizer()
    discovery, _ = rebuild.reconstruct_discovery()
    heldout, *_ = rebuild.reconstruct_heldout()
    scaling, *_ = rebuild.reconstruct_scaling()
    claims = rebuild.build_claim_audit(universe, optimizer, discovery, heldout, scaling)
    assert claims.status.eq('PASS').all(), claims[claims.status.ne('PASS')].to_dict('records')
    assert (discovery['task_count'], heldout['task_count']) == (56, 84)
    assert heldout['H1']['pass'] and heldout['H2']['pass']
    assert helper.reconstruct_theory()['v3']['violations'] == 0


def test_public_snapshot_integrity_manifest():
    manifest = ROOT / 'release_manifest.json'
    if not manifest.exists():
        pytest.skip('public snapshot only; original evidence is covered by existing historical tests')
    rows = json.loads(manifest.read_text())['files']
    for row in rows:
        path = ROOT / row['path']
        assert path.is_file(), row['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['public_sha256'], row['path']


def test_public_redactions_preserve_historical_scientific_hashes():
    manifest_path = ROOT / 'release_manifest.json'
    if not manifest_path.exists():
        pytest.skip('public snapshot only; unredacted original has the historical inventory test')
    manifest = json.loads(manifest_path.read_text())
    public = {r['path']: r for r in manifest['files']}
    excluded = {r['path']: r['reason'] for r in manifest['excluded']}
    protected = ROOT / 'results/synthesis_v1/protected_hashes_before.sha256'
    lines = protected.read_text().splitlines()
    assert len(lines) == 1403
    for line in lines:
        expected, relative = line.split('  ', 1)
        if relative in public:
            row = public[relative]
            assert row['source_sha256'] == expected, relative
            if not row['sanitizations']:
                assert row['public_sha256'] == expected, relative
        else:
            assert relative in excluded, relative
            assert 'private historical worktree' in excluded[relative], relative
