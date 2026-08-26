#!/usr/bin/env python3
"""Rewrite xeelo-spec YAML mappings into OT extract key order."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.spec_loader import ENTRY_FILENAME, load_spec, write_spec  # noqa: E402


def _spec_roots(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file():
        if path.name == ENTRY_FILENAME:
            return [path.parent]
        if path.parent.name == "spec" and (path.parent.parent / ENTRY_FILENAME).is_file():
            return [path.parent.parent]
        raise SystemExit(f"Not a xeelo-spec entry or fragment: {path}")
    if not path.is_dir():
        raise SystemExit(f"Path not found: {path}")
    if (path / ENTRY_FILENAME).is_file():
        return [path]
    objects = path / "objects"
    search = objects if objects.is_dir() else path
    roots = sorted(
        p.parent
        for p in search.glob(f"*/{ENTRY_FILENAME}")
        if p.is_file()
    )
    if not roots:
        raise SystemExit(f"No {ENTRY_FILENAME} under {path}")
    return roots


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reorder spec YAML keys to match OT extract (stable git diffs)."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="xeelo-spec.yaml, its directory, a spec fragment, or a folder of object specs",
    )
    args = parser.parse_args()
    roots = _spec_roots(args.path)
    for root in roots:
        spec = load_spec(root)
        entry = write_spec(spec, root)
        print(f"Wrote {entry}")


if __name__ == "__main__":
    main()
