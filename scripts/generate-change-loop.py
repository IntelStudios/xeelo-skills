#!/usr/bin/env python3
"""Generate Object Transfer ZIP(s) for all object specs in a change loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.hierarchy import build_object_map, dedupe_edges  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.spec_loader import load_spec  # noqa: E402
from ot_builder.validate import validate_object_transfer_xml  # noqa: E402
from ot_builder.xml import build_object_transfer_xml  # noqa: E402
from ot_builder.zipout import write_xml, write_zip  # noqa: E402


def _generate_one(spec_path: Path, xml_path: Path, zip_path: Path) -> None:
    spec = load_spec(spec_path)
    transfer_version = spec.get("transferVersion", "1.3.0")
    result = build_rows(spec)
    edges = dedupe_edges(result.edges)
    object_map = build_object_map(edges)
    xml_bytes = build_object_transfer_xml(result.rows, edges, object_map, transfer_version)
    write_xml(xml_bytes, xml_path)
    validate_object_transfer_xml(xml_bytes, str(xml_path))
    write_zip(xml_bytes, zip_path)
    validate_object_transfer_xml(xml_bytes, str(zip_path))
    print(
        f"Wrote {zip_path} "
        f"({len(edges)} edges, {sum(len(v) for v in result.rows.values())} rows)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Object Transfers for a change loop")
    parser.add_argument(
        "loop",
        type=Path,
        help="Change loop directory (contains objects/ and output/)",
    )
    args = parser.parse_args()

    objects_dir = args.loop / "objects"
    output_dir = args.loop / "output"
    if not objects_dir.is_dir():
        raise SystemExit(f"Missing objects directory: {objects_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = sorted(objects_dir.glob("*/xeelo-spec.yaml"))
    if not specs:
        raise SystemExit(f"No object specs under {objects_dir}")

    for spec_path in specs:
        slug = spec_path.parent.name
        xml_path = output_dir / f"{slug}-object-transfer.xml"
        zip_path = output_dir / f"{slug}-object-transfer.zip"
        _generate_one(spec_path, xml_path, zip_path)

    print(f"Generated {len(specs)} Object Transfer package(s) in {output_dir}")


if __name__ == "__main__":
    main()
