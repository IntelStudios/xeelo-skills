#!/usr/bin/env python3
"""Extract projects/<project>/env from a DB transfer JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.db_extract import extract_env  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract env catalog + object specs from DB transfer")
    parser.add_argument("transfer", type=Path, help="DB transfer JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output env directory (e.g. projects/ovnet/env)",
    )
    args = parser.parse_args()

    summary = extract_env(args.transfer, args.output)
    print(
        f"Wrote {args.output} "
        f"(catalog={summary['catalogObjects']} objects, "
        f"extracted={len(summary['extractedObjects'])})"
    )
    for item in summary["extractedObjects"]:
        print(f"  - {item['slug']} (id={item['id']})")


if __name__ == "__main__":
    main()
