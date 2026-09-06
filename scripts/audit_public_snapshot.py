#!/usr/bin/env python3
"""Read-only release scan. Report locations/types, never credential values."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

# Token boundaries matter: scientific task IDs can contain the substring 'sk-'.
PATTERNS = {
    'credential_token': re.compile(rb'(?<![A-Za-z0-9_-])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|hf_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{16,})'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    'personal_or_hpc_path': re.compile(rb'/(?:home|Users|scratch|lustre|zhome)/[A-Za-z0-9_.-]+(?:/[^\s"\x27,;<>`\\]+)*'),
    'internal_hostname': re.compile(rb'\b[A-Za-z0-9.-]+\.unicph\.domain\b'),
    'private_url': re.compile(rb'https?://(?:[^/\s:@]+:[^/\s@]+@|(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(?::\d+)?)'),
}
EMAIL = re.compile(rb'(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]{1,100}@[A-Za-z0-9.-]{1,100}\.[A-Za-z]{2,20}')


def scan(root: Path):
    findings = []; emails = []; missing = []; python_errors = []; symlinks = []
    count = 0; total = 0
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if '.git' in rel.parts or path.is_dir(): continue
        if path.is_symlink():
            symlinks.append({'path': rel.as_posix(), 'broken': not path.exists()})
            continue
        count += 1; total += path.stat().st_size
        data = path.read_bytes()
        if (path.name == 'KEY.txt' or '.sqlite' in path.name or path.name.startswith('.env')
            or '__pycache__' in rel.parts or path.suffix in {'.pyc','.log','.out','.err','.slurm','.key','.pem'}):
            findings.append({'path': rel.as_posix(), 'line': None, 'kind': 'excluded_file_type'})
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(data):
                findings.append({'path': rel.as_posix(), 'line': data.count(b'\n',0,match.start())+1, 'kind': kind})
        if b'@' in data:
            for match in EMAIL.finditer(data):
                emails.append({'path': rel.as_posix(), 'line': data.count(b'\n',0,match.start())+1})
        if path.suffix == '.py':
            try: ast.parse(data, filename=rel.as_posix())
            except SyntaxError as error: python_errors.append({'path': rel.as_posix(), 'line': error.lineno})
    manifest_path = root / 'release_manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        expected_paths = {r['path'] for r in manifest['files']}
        for row in manifest['files']:
            path = root / row['path']
            if not path.is_file(): missing.append(row['path'])
            elif hashlib.sha256(path.read_bytes()).hexdigest() != row['public_sha256']:
                findings.append({'path': row['path'], 'line': None, 'kind': 'manifest_hash_mismatch'})
        for path in root.rglob('*'):
            if path.is_file() and '.git' not in path.relative_to(root).parts:
                relative = path.relative_to(root).as_posix()
                if relative not in expected_paths and relative not in manifest['self_excluded_from_hashes']:
                    findings.append({'path': relative, 'line': None, 'kind': 'unmanifested_file'})
    # LaTeX local inputs, includes and figures; do not treat standard packages as missing files.
    paper_missing = []
    for base in ('overleaf', 'manuscript'):
        directory = root / base
        for path in directory.rglob('*.tex'):
            text = '\n'.join(line.split('%')[0] for line in path.read_text().splitlines())
            for command, value in re.findall(r'\\(input|include|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}', text):
                if '\\' in value or '#' in value: continue
                candidate = directory / value
                candidates = [candidate, candidate.with_suffix('.tex')]
                if command == 'includegraphics':
                    candidates = [parent / f'{value}{ext}' for parent in (directory, directory/'figures')
                                  for ext in ('','.pdf','.png','.jpg','.eps')]
                if not any(p.is_file() for p in candidates):
                    paper_missing.append({'source': path.relative_to(root).as_posix(), 'target': value})
    return {'status': 'PASS' if not (findings or missing or python_errors or symlinks or paper_missing) else 'FAIL',
            'file_count': count, 'logical_bytes': total, 'findings': findings, 'email_locations_for_review': emails,
            'missing_manifest_files': missing, 'symlinks': symlinks,
            'python_syntax_errors': python_errors, 'missing_local_paper_inputs': paper_missing,
            'limitations': 'Pattern scan plus explicit exclusion/manifest policy; not proof of absence of arbitrary secrets. PDF bytes scanned; extracted-text and metadata inspection is a separate audit.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, help='JSON output outside snapshot; default stdout')
    args = parser.parse_args()
    root = args.root.resolve()
    result = scan(root)
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        output = args.output.resolve()
        if root == output or root in output.parents:
            parser.error('scan report must be outside the snapshot')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
        print(f"PUBLIC SCAN {result['status']}: {result['file_count']} files; report {output}")
    else: print(text)
    if result['status'] != 'PASS': sys.exit(1)


if __name__ == '__main__':
    main()
