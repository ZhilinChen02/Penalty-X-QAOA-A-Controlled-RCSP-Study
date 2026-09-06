"""Public-checkout scientific integrity; no private worktree or old Git needed."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from verify_release import verify, verify_manifest, verify_benchmark


def test_public_frozen_manifest_and_complete_matrices():
    manifest = verify_manifest()
    assert manifest['baseline_commit'] == 'dc4106f03905b8ea86a0596fa2f007a094cfa4b1'
    assert all(row.get('rows', 0) >= 0 for row in manifest['files'])


def test_reconstruct_headlines_statistics_scaling_and_theory():
    report = verify()
    assert report['claims'] == 21
    assert report['H1']['pass'] and report['H2']['pass']
    assert not report['optimizer_invoked'] and not report['scaling_refit_performed']
    assert report['theory']['v3']['violations'] == 0


def test_manifest_rejects_changed_scientific_value(tmp_path):
    (tmp_path/'results').mkdir()
    table=tmp_path/'results/row.csv'
    table.write_text('p_feas\n0.25\n')
    row={'path':'results/row.csv','sha256':hashlib.sha256(table.read_bytes()).hexdigest(),
         'rows':1,'columns':['p_feas']}
    (tmp_path/'results/manifest.json').write_text(json.dumps({'files':[row]}))
    verify_manifest(tmp_path)
    table.write_text('p_feas\n0.26\n')
    with pytest.raises(RuntimeError,match='checksum mismatch'):
        verify_manifest(tmp_path)


def test_frozen_split_partitions_and_scaling_manifest():
    assert verify_benchmark() == {'corrected_tasks':140,'discovery_tasks':56,
                                  'heldout_tasks':84,'scaling_tasks':180}
