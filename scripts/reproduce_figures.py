#!/usr/bin/env python3
"""Replot four Figure-v3 main figures and the finite-shot supplement from frozen rows."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'dist/reproduced_figures',
                        help='new directory; default dist/reproduced_figures (must not exist)')
    parser.add_argument('--paper', action='store_true',
                        help='also compile a paper copy; requires PyMuPDF, TeX and the Springer template')
    parser.add_argument('--tex-bin', type=Path, help='directory containing pdflatex and bibtex')
    parser.add_argument('--template-dir', type=Path, help='directory with sn-jnl.cls and sn-mathphys-num.bst')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or output in ROOT.parents or any((ROOT/d)==output or (ROOT/d) in output.parents
            for d in ('src','data','results','configs','overleaf','reproduction','tests')):
        parser.error('choose a new output directory outside scientific sources and frozen results')
    if output.exists():
        parser.error('output already exists; choose a new --output-dir to preserve previous outputs')
    subprocess.run([sys.executable, str(ROOT/'paper_scripts/redesign_main_figures_v3.py'),
                    '--output-dir', str(output)], check=True, cwd=ROOT)
    if args.paper:
        command = [sys.executable, str(ROOT/'paper_scripts/build_figure_v3_review.py'),
                   '--output-dir', str(output)]
        for flag, value in [('--tex-bin', args.tex_bin), ('--template-dir', args.template_dir)]:
            if value is not None: command.extend([flag, str(value.resolve())])
        subprocess.run(command, check=True, cwd=ROOT)
    print(f'FROZEN-RESULT FIGURES: {output}')


if __name__ == '__main__':
    main()
