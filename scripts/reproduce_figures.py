#!/usr/bin/env python3
"""Replot the four paper figures from verified frozen tables (PDF and PNG)."""
from pathlib import Path
import argparse
import json
from verify_release import ROOT, verify
import _plot_figures as plot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'dist/reproduced_figures',
                        help='new output directory; default: dist/reproduced_figures')
    parser.add_argument('--supplementary', action='store_true',
                        help='also render the finite-shot supplementary figure')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or output in ROOT.parents or (ROOT in output.parents and ROOT/'dist' not in output.parents):
        parser.error('use a new directory under dist/ or outside the repository')
    if output.exists():
        parser.error('output already exists; choose a new --output-dir')
    verify()
    output.mkdir(parents=True)
    plot.style()
    ledger = {}
    for function in (plot.figure1, plot.figure2, plot.figure3, plot.figure4):
        function(output, ledger)
    if args.supplementary:
        plot.supplement(output, ledger)
    (output/'figure_inputs.json').write_text(json.dumps(ledger, indent=2)+'\n')
    print(f'Frozen-result figures: PASS ({output})')


if __name__ == '__main__':
    main()
