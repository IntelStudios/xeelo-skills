#!/usr/bin/env python3
"""Upload Object Transfer ZIP(s) to Admin and process them (async parse + broker job)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.admin_client import ConnectionConfig, push_object_transfer_zip  # noqa: E402


def _zips_from_loop(loop: Path) -> list[Path]:
    output = loop / "output"
    zips = sorted(output.glob("*-object-transfer.zip"))
    if not zips:
        raise SystemExit(f"No Object Transfer ZIPs under {output}")
    return zips


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload and process Object Transfer ZIP(s) via Xeelo Admin"
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (adminBaseUrl, siteId, credentials)",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        action="append",
        default=[],
        help="Object Transfer ZIP path (repeatable)",
    )
    parser.add_argument(
        "--loop",
        type=Path,
        default=None,
        help="Change loop directory; uses output/*-object-transfer.zip",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3600.0,
        help="Seconds to wait for upload parse WS and process completion (default 3600)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=5.0,
        help="Seconds between GridModel polls after Process (default 5)",
    )
    parser.add_argument(
        "--only-test",
        action="store_true",
        help="Process as test only (ObjectSetupXMLIsTestOnly=1)",
    )
    args = parser.parse_args()

    zips: list[Path] = list(args.zip)
    if args.loop:
        zips.extend(_zips_from_loop(args.loop))
    # unique, preserve order
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in zips:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    if not unique:
        raise SystemExit("Provide --zip and/or --loop")

    config = ConnectionConfig.load(args.connection)
    print(
        f"Pushing {len(unique)} Object Transfer ZIP(s) to "
        f"{config.admin_base_url} (siteId={config.site_id})"
    )
    for zip_path in unique:
        print(f"Uploading {zip_path} (waiting for parse Task Success before process)")
        row = push_object_transfer_zip(
            config,
            zip_path,
            timeout_seconds=args.timeout,
            poll_period=args.poll,
            only_test=args.only_test,
        )
        print(
            f"Processed xmlId={row.xml_id} {row.filename} "
            f"status={row.process_status} {row.message}".rstrip()
        )


if __name__ == "__main__":
    main()
