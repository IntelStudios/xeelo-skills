#!/usr/bin/env python3
"""Generate Object Transfer JSON for all object specs in a change loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.delta import (  # noqa: E402
    find_project_root,
    latest_snapshot_json,
    load_baseline_json,
)
from ot_builder.jsonout import build_object_transfer_json, write_json  # noqa: E402
from ot_builder.rows import build_rows  # noqa: E402
from ot_builder.spec_loader import load_spec  # noqa: E402


def _generate_one(spec_path: Path, json_path: Path, baseline: dict | None) -> None:
    spec = load_spec(spec_path)
    result = build_rows(spec)
    text, omitted = build_object_transfer_json(result.rows, baseline=baseline)
    write_json(text, json_path)
    extra = f", {omitted} unchanged omitted" if omitted else ""
    print(
        f"Wrote {json_path} "
        f"({sum(len(v) for v in result.rows.values())} source rows{extra})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Object Transfers for a change loop")
    parser.add_argument(
        "loop",
        type=Path,
        help="Change loop directory (contains objects/ and output/)",
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

    objects_dir = args.loop / "objects"
    output_dir = args.loop / "output"
    if not objects_dir.is_dir():
        raise SystemExit(f"Missing objects directory: {objects_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = sorted(objects_dir.glob("*/xeelo-spec.yaml"))
    if not specs:
        raise SystemExit(f"No object specs under {objects_dir}")

    baseline = None
    if not args.no_baseline:
        snap = args.baseline
        if snap is None:
            project = find_project_root(args.loop)
            snap = latest_snapshot_json(project) if project else None
        if snap is None:
            print("No DB-transfer snapshot; emitting all generated rows")
        else:
            baseline = load_baseline_json(snap)
            print(f"Baseline: {snap}")

    for spec_path in specs:
        slug = spec_path.parent.name
        json_path = output_dir / f"{slug}-object-transfer.json"
        _generate_one(spec_path, json_path, baseline)

    print(f"Generated {len(specs)} Object Transfer package(s) in {output_dir}")


if __name__ == "__main__":
    main()
