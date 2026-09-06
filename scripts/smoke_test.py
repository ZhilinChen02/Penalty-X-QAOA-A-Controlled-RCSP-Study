#!/usr/bin/env python3
"""Run the original 12-task smoke optimization in a new temporary workspace."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='new external directory (default: temporary)')
    args = parser.parse_args()
    if args.output_dir is None:
        work = Path(tempfile.mkdtemp(prefix='qroute-smoke-'))
    else:
        work = args.output_dir.resolve()
        if work == ROOT or ROOT in work.parents or work in ROOT.parents:
            parser.error('output must be outside the repository')
        work.mkdir(parents=True, exist_ok=False)
    for name in ('src', 'configs'):
        shutil.copytree(ROOT / name, work / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (work / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/run_smoke.py', work / 'scripts/run_smoke.py')
    env = dict(os.environ, PYTHONPATH=str(work / 'src'), MPLBACKEND='Agg', PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([sys.executable, str(work / 'scripts/run_smoke.py')], cwd=work, env=env, check=True)
    print(f'SMOKE OUTPUT: {work}')


if __name__ == '__main__':
    main()
