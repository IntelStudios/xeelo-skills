#!/usr/bin/env python3
"""Generate Xeelo Object transfer XML/ZIP from xeelo-spec.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.hierarchy import build_object_map, dedupe_edges
from ot_builder.rows import build_rows
from ot_builder.spec_loader import load_spec
from ot_builder.validate import validate_object_transfer_xml
from ot_builder.xml import build_object_transfer_xml
from ot_builder.zipout import write_xml, write_zip


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Xeelo Object transfer from xeelo-spec.yaml")
    parser.add_argument("spec", type=Path, help="Path to xeelo-spec.yaml")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/object-transfer.xml"),
        help="Output XML path",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        default=None,
        help="Optional ZIP path for Admin Object Transfer upload",
    )
    args = parser.parse_args()

    spec = load_spec(args.spec)
    transfer_version = spec.get("transferVersion", "1.3.0")

    result = build_rows(spec)
    edges = dedupe_edges(result.edges)
    object_map = build_object_map(edges)
    xml_bytes = build_object_transfer_xml(result.rows, edges, object_map, transfer_version)

    write_xml(xml_bytes, args.output)
    validate_object_transfer_xml(xml_bytes, str(args.output))
    print(f"Wrote {args.output} ({len(edges)} hierarchy edges, {sum(len(v) for v in result.rows.values())} rows)")

    if args.zip:
        write_zip(xml_bytes, args.zip)
        validate_object_transfer_xml(xml_bytes, str(args.zip))
        print(f"Wrote ZIP: {args.zip}")


if __name__ == "__main__":
    main()
