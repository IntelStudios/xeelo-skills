#!/usr/bin/env python3
"""Download Xeelo DB transfer XML via GraphQL Select_admin_transfer_download."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.graphql_client import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    download_db_transfer_xml,
    xml_to_utf16_le_bytes,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download DB transfer XML from Xeelo GraphQL")
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (xeeloUrl, token)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Project directory (default: parent of connection file)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    args = parser.parse_args()

    config = ConnectionConfig.load(args.connection)
    project = args.project or args.connection.parent
    if project.name.startswith("."):
        project = project.parent

    print(f"Downloading DB transfer from {config.graphql_url}")
    xml = download_db_transfer_xml(config, timeout_seconds=args.timeout)
    data = xml_to_utf16_le_bytes(xml)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project.name}_{stamp}.xml"
    out_dir = project / "snapshots" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(data)
    print(f"Wrote {out_path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
