#!/usr/bin/env python3
"""Generate Xeelo Object transfer JSON from xeelo-spec.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.delta import find_project_root, latest_snapshot_json, load_baseline_json
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
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="DB-transfer JSON to diff against (default: latest project snapshots/)",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Do not omit unchanged rows vs download",
    )
    args = parser.parse_args()

    baseline = None
    if not args.no_baseline:
        snap = args.baseline
        if snap is None:
            project = find_project_root(args.spec)
            snap = latest_snapshot_json(project) if project else None
        if snap is not None:
            baseline = load_baseline_json(snap)
            print(f"Baseline: {snap}")

    spec = load_spec(args.spec)
    result = build_rows(spec)
    text, omitted = build_object_transfer_json(result.rows, baseline=baseline)
    write_json(text, args.output)
    extra = f", {omitted} unchanged omitted" if omitted else ""
    print(
        f"Wrote {args.output} "
        f"({sum(len(v) for v in result.rows.values())} source rows{extra})"
    )


if __name__ == "__main__":
    main()
