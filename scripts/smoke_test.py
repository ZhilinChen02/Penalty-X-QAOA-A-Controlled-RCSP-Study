#!/usr/bin/env python3
"""Run the bounded CPU smoke pipeline in a new workspace; never overwrite evidence."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('release_smoke.py')), run_name='__main__')
