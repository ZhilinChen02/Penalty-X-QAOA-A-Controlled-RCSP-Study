#!/usr/bin/env python3
"""Build a separate, traceable public candidate without Git history or local metadata."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = {'src', 'scripts', 'configs', 'tests', 'data', 'protocols', 'results',
                'figures', 'paper', 'overleaf', 'manuscript', 'review_package',
                'paper_scripts', 'paper_assets', 'paper_audit', 'docs', 'reproduction', 'analysis'}
PUBLIC_FILES = {'README.md', '.gitignore', 'pyproject.toml', 'CITATION.cff', 'LICENSE',
                'LICENSE_REVIEW.md', 'environment.yml', 'requirements.txt', 'requirements-dev.txt', 'OPEN_SOURCE_AUDIT.md'}
LOCAL_PARTS = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
               '.idea', '.vscode', '.venv', '.release-audit-private', 'build_logs', 'checkpoints', 'build', 'conda-meta'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def exclusion(relative: Path):
    p = relative.as_posix()
    if any(part in LOCAL_PARTS or (part.startswith('.venv') or part.endswith('.egg-info')) for part in relative.parts):
        return 'cache/editor/private worktree metadata'
    if relative.name == 'KEY.txt' or '.sqlite' in relative.name or relative.name.startswith('.env'):
        return 'secret-labelled or local conversation/credential material; review privately'
    if relative.name in {'.DS_Store', 'Thumbs.db'}:
        return 'operating-system metadata'
    if relative.suffix.lower() in {'.cls', '.bst'}:
        return 'third-party template redistribution unresolved; acquire upstream separately'
    if relative.suffix.lower() in {'.pyc', '.log', '.out', '.err', '.slurm', '.aux', '.blg', '.bbl', '.fls', '.toc', '.nav', '.snm', '.vrb', '.lof', '.lot', '.tmp', '.bak', '.prof', '.lprof', '.synctex'} or relative.name.endswith(('.synctex.gz','.fdb_latexmk')):
        return 'generated log, scheduler material or compiler/cache output'
    if relative.suffix.lower() in {'.npy', '.npz', '.statevector', '.ckpt', '.pt', '.pth'}:
        return 'large checkpoint/state artifact; not needed for frozen-row reproduction'
    if 'worktree_safety' in p or 'original_worktree_' in p or 'PRE_EXISTING_WORKTREE' in p:
        return 'private historical worktree provenance; original retained'
    if p.startswith('results/reviewer_robustness/provenance/'):
        return 'local environment/git/package dumps; minimal public environment supplied separately'
    if p.startswith('results/reviewer_robustness/smoke/'):
        return 'reviewer development smoke outputs; formal evidence retained'
    if p.startswith('results/reviewer_robustness/paper_revision/') and relative.suffix in {'.pdf', '.zip'}:
        return 'obsolete generated revision package; current paper source retained'
    if relative.parts[0] == 'paper_audit' and relative.suffix == '.json':
        return 'local packaging/worktree validation output; new public audit supersedes it'
    if relative.parts[0] == 'submission':
        return 'duplicate editorial submission variants; final public variant needs author review'
    if relative.parts[0] == 'dist' or relative.suffix == '.zip':
        return 'generated archives; rebuild from public source after manual review'
    if relative.parts[0] not in PUBLIC_ROOTS and p not in PUBLIC_FILES:
        return 'development-only or uncertain top-level material; retained in original'
    return None


def classify(relative: Path, reason):
    p = relative.as_posix(); top = relative.parts[0]
    if relative.name == 'KEY.txt' or '.sqlite' in p or relative.name.startswith('.env'):
        return 'secrets/private files'
    if 'worktree' in p.lower() or '/provenance/' in p or relative.suffix == '.slurm':
        return 'local/HPC-specific files'
    if top == 'submission': return 'uncertain — needs human review'
    if '__pycache__' in p or relative.suffix in {'.pyc', '.log', '.zip', '.aux'} or top in {'.idea', 'dist', '.pytest_cache'}:
        return 'generated artifacts'
    if reason: return 'obsolete/development-only material'
    if top == 'src': return 'public source code'
    if top in {'scripts','paper_scripts','configs','protocols','reproduction','data'}: return 'reproducibility scripts'
    if top == 'tests': return 'tests'
    if top == 'results': return 'canonical scientific results' if not p.startswith('results/synthesis_v1/') else 'supplementary material'
    if top == 'overleaf': return 'supplementary material' if ('appendices' in p or 'supplementary' in p or relative.name == 'ESM_1.tex') else 'paper source'
    if top == 'manuscript': return 'paper source'
    if top in {'paper', 'review_package', 'figures', 'analysis'}: return 'supplementary material'
    if top == 'paper_assets': return 'uncertain — needs human review'
    return 'documentation'


def sanitize(relative, raw):
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw, []
    changes = []
    # Only privacy-bearing strings. Never rewrite numeric values, arrays or hashes.
    substitutions = [
        ('personal workspace path', r'/home/[A-Za-z0-9_.-]+/PycharmProjects/', '<LOCAL_WORKSPACE>/'),
        ('personal path', r'/(?:home|Users|scratch|lustre|zhome)/[A-Za-z0-9_.-]+(?:/[^\s"\x27,;<>`\\]+)*', '<LOCAL_PATH>'),
        ('internal hostname', r'\b[A-Za-z0-9.-]+\.unicph\.domain\b', '<REDACTED_HOST>'),
    ]
    for label, pattern, replacement in substitutions:
        text, count = re.subn(pattern, replacement, text)
        if count: changes.append({'kind': label, 'count': count})
    return text.encode('utf-8'), changes


def release_documentation(relative, raw):
    """Adapt packaging instructions only in the public copy, retaining originals."""
    if relative.as_posix() == 'overleaf/README.md':
        text = raw.decode('utf-8')
        marker = 'Before submission, a human must confirm'
        if marker in text:
            introduction = '''# Manuscript sources in the public code release

This directory contains the manuscript, supplementary sources, bibliography,
figures and compact evidence tables. The historical Overleaf ZIP is not part of
this code release. The Springer class and bibliography style are also omitted;
supply the official template separately as described in `../paper/README.md`.

From the repository root, `python scripts/reproduce_figures.py --paper
--output-dir dist/paper_review --template-dir /path/to/springer-template`
replots frozen data and compiles a separate paper copy containing Figure v3.
Install the optional review dependency and make pdfLaTeX/BibTeX available first.
The source manuscript here is preserved; the generated copy integrates v3 and
its supplementary panel. See `../docs/RESULT_PROVENANCE.md` for the data chain.

'''
            return (introduction + marker + text.split(marker, 1)[1]).encode(), ['public manuscript build instructions']
    if relative.name == 'TEMPLATE_PROVENANCE.md':
        note = ('> Public-release note: the vendor files described below are not bundled.\n'
                '> This retained provenance record identifies the separately supplied\n'
                '> template used for the successful compilation check.\n\n')
        if not raw.startswith(b'> Public-release note:'):
            return note.encode() + raw, ['clarify omitted vendor files']
    return raw, []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True, help='new external directory or child of dist/open_source; must not exist')
    parser.add_argument('--inventory-dir', type=Path, help='optional private original-tree inventory directory')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    public_dist = ROOT / 'dist/open_source'
    if output == ROOT or output in ROOT.parents or (ROOT in output.parents and public_dist not in output.parents):
        parser.error('snapshot must be external or a child of dist/open_source')
    output.mkdir(parents=True, exist_ok=False)
    git = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=False)
    tracked = set(git.stdout.decode().split('\0')) if git.returncode == 0 else set()
    records = []; excluded = []; inventory = []
    paths=[]
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        base=Path(directory)
        dirs[:]=[d for d in dirs if d!='.git' and not ((base/d)==output or output in (base/d).parents)]
        paths.extend(base/name for name in files)
    for path in sorted(paths):
        if path.is_dir(): continue
        relative = path.relative_to(ROOT)
        reason = exclusion(relative)
        if path.is_symlink(): reason = 'symlink requires manual review; no link following'
        size = path.lstat().st_size
        inventory.append({'path': relative.as_posix(), 'size_bytes': size,
            'tracked': relative.as_posix() in tracked, 'category': classify(relative, reason),
            'public': not bool(reason), 'reason': reason or 'retained for source/evidence/reproduction'})
        if reason:
            excluded.append({'path': relative.as_posix(), 'reason': reason})
            continue
        raw = path.read_bytes()
        public, changes = sanitize(relative, raw)
        public, documentation_changes = release_documentation(relative, public)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(public)
        shutil.copymode(path, target)
        records.append({'path': relative.as_posix(), 'source_sha256': digest(raw),
                        'public_sha256': digest(public), 'size_bytes': len(public),
                        'sanitizations': changes, 'documentation_changes': documentation_changes})
    # Small approved derivative figures are useful in a checkout; omit the
    # duplicate review archives and compiler outputs surrounding them in dist/.
    for stem in ('fig1_v3','fig2_v3','fig3_v3','fig4_v3','figS_finite_shot_v3'):
        for extension in ('pdf','svg','png'):
            source = ROOT/'dist/figures_v3'/f'{stem}.{extension}'
            if not source.is_file(): continue
            relative = Path('figures/main_v3')/source.name
            target = output/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            value = digest(target.read_bytes())
            records.append({'path': relative.as_posix(), 'source_path': source.relative_to(ROOT).as_posix(),
                'source_sha256': value, 'public_sha256': value, 'size_bytes': target.stat().st_size,
                'sanitizations': []})
    manifest = {'schema_version': 1, 'policy': 'NO_GIT_NO_OPTIMIZATION_NO_CANONICAL_NUMERIC_EDITS',
                'files': records, 'excluded': excluded,
                'self_excluded_from_hashes': ['release_manifest.json']}
    (output / 'release_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if args.inventory_dir:
        args.inventory_dir.mkdir(parents=True, exist_ok=True)
        with (args.inventory_dir / 'file_inventory.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(inventory[0])); writer.writeheader(); writer.writerows(inventory)
        with (args.inventory_dir / 'large_files.csv').open('w', newline='') as handle:
            names = ['size_bytes', 'path', 'tracked', 'needed_for_reproduction', 'recommended_public', 'storage']
            writer = csv.DictWriter(handle, fieldnames=names); writer.writeheader()
            for row in sorted(inventory, key=lambda x:x['size_bytes'], reverse=True):
                if row['size_bytes'] < 1024*1024: continue
                writer.writerow({'size_bytes': row['size_bytes'], 'path': row['path'], 'tracked': row['tracked'],
                    'needed_for_reproduction': 'yes/provenance' if row['public'] else 'no/manual review',
                    'recommended_public': row['public'], 'storage': 'ordinary Git + Zenodo archive' if row['public'] else 'exclude; original retained'})
    print(json.dumps({'snapshot': str(output), 'files': len(records)+1,
        'logical_bytes': sum(x['size_bytes'] for x in records) + (output/'release_manifest.json').stat().st_size,
        'sanitized_files': sum(bool(x['sanitizations']) for x in records), 'excluded_files': len(excluded)}, indent=2))


if __name__ == '__main__':
    main()
