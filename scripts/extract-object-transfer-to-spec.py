#!/usr/bin/env python3
"""Extract xeelo-spec.yaml from Xeelo Object transfer XML/ZIP."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.extract import extract_spec  # noqa: E402
from ot_builder.spec_loader import load_spec, write_spec  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract xeelo-spec.yaml from Object transfer")
    parser.add_argument("transfer", type=Path, help="Object transfer XML or ZIP")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output directory for split spec (writes xeelo-spec.yaml + spec/*.yaml)",
    )
    parser.add_argument("--object-id", type=int, default=None)
    parser.add_argument("--object-code", default=None)
    parser.add_argument("--object-name", default=None)
    parser.add_argument("--merge", type=Path, default=None, help="Merge into existing spec (file or directory)")
    args = parser.parse_args()

    merge = load_spec(args.merge) if args.merge else None
    spec = extract_spec(
        args.transfer,
        object_id=args.object_id,
        object_code=args.object_code,
        object_name=args.object_name,
        merge=merge,
    )
    entry_path = write_spec(spec, args.output)
    obj_id = spec["ids"]["explicit"]["objectId"]
    tab_count = len(spec["layout"]["tabs"])
    table_count = len(spec["ids"]["byTable"])
    print(f"Wrote {entry_path} (objectId={obj_id}, tabs={tab_count}, byTable={table_count} tables)")


if __name__ == "__main__":
    main()
