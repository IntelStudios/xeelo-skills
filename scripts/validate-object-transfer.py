#!/usr/bin/env python3
"""Validate Xeelo Object transfer XML/ZIP format (upload SP compatibility)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.validate import ValidationError, validate_path  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Xeelo Object transfer XML/ZIP")
    parser.add_argument("paths", nargs="+", type=Path, help="XML or ZIP files to validate")
    args = parser.parse_args()

    errors: list[str] = []
    for path in args.paths:
        if not path.exists():
            errors.append(f"{path}: file not found")
            continue
        try:
            validate_path(path)
            print(f"OK {path}")
        except ValidationError as exc:
            errors.append(str(exc))

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
