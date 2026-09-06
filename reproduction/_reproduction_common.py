"""Small deterministic helpers for the paper-level reproduction scripts."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(tempfile.gettempdir()) / "qroute-reproduction"
EXPECTED_HASHES = ROOT / "reproduction" / "expected_hashes.txt"


def stable_value(value: Any) -> Any:
    """Convert nested output to portable JSON values with stable precision."""
    if isinstance(value, dict):
        return {str(key): stable_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [stable_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite value in reproduction output")
        return round(value, 12)
    if hasattr(value, "item"):
        return stable_value(value.item())
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(stable_value(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def expected_hashes() -> dict[str, str]:
    records: dict[str, str] = {}
    for line in EXPECTED_HASHES.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        checksum, relative = stripped.split(maxsplit=1)
        records[relative.strip()] = checksum
    return records


def verify(path: Path) -> None:
    # References are keyed by artifact identity, independently of output location.
    # The committed reference hashes are never rewritten.
    relative = (Path("reproduction") / "rebuilt" / path.name).as_posix()
    expected = expected_hashes().get(relative)
    if expected is None:
        raise RuntimeError(f"no expected hash registered for {relative}")
    observed = digest(path)
    if observed != expected:
        raise RuntimeError(
            f"hash mismatch for {relative}: expected {expected}, observed {observed}"
        )
    print(f"HASH PASS  {relative}  {observed}")


def output_directory(path: Path) -> Path:
    """Require outputs outside the source tree to preserve frozen evidence."""
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents or resolved in ROOT.parents:
        raise ValueError("use an output directory outside the repository")
    resolved.mkdir(parents=True, exist_ok=True)
    if any(child.is_symlink() for child in resolved.iterdir()):
        raise ValueError("output directory must not contain symlinks")
    return resolved
