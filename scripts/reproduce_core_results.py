#!/usr/bin/env python3
"""Reconstruct frozen headlines, held-out inference and scaling; no optimization."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    sys.argv.insert(1, '--from-existing-results')
    runpy.run_path(str(Path(__file__).with_name('validate_release.py')), run_name='__main__')
