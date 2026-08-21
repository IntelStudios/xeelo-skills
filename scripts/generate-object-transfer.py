#!/usr/bin/env python3
"""Generate Xeelo Object transfer JSON from xeelo-spec.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.jsonout import build_object_transfer_json, write_json
from ot_builder.rows import build_rows
from ot_builder.spec_loader import load_spec


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Xeelo Object transfer from xeelo-spec.yaml")
    parser.add_argument("spec", type=Path, help="Path to xeelo-spec.yaml")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/object-transfer.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    spec = load_spec(args.spec)
    result = build_rows(spec)
    text = build_object_transfer_json(result.rows)
    write_json(text, args.output)
    print(
        f"Wrote {args.output} "
        f"({sum(len(v) for v in result.rows.values())} source rows)"
    )


if __name__ == "__main__":
    main()
