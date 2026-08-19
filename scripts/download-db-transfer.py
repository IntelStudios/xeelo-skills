#!/usr/bin/env python3
"""Download Xeelo DB transfer ZIP via Admin API (async prep + WebSocket + AdminTempFile)."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.admin_client import ConnectionConfig, download_db_transfer_zip  # noqa: E402


def _slug_stamp(name: str) -> str:
    # ovnet_20260811_145656.zip → 20260811_145656
    m = re.search(r"(\d{8}_\d{6})", name)
    if m:
        return m.group(1)
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download DB transfer from Xeelo Admin")
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (adminBaseUrl, siteId, credentials)",
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
        default=3600.0,
        help="Seconds to wait for TempFile notification (default 3600)",
    )
    args = parser.parse_args()

    config = ConnectionConfig.load(args.connection)
    project = args.project or args.connection.parent
    if project.name.startswith("."):
        project = project.parent

    print(f"Refreshing token / downloading DB transfer from {config.admin_base_url} (siteId={config.site_id})")
    data, filename = download_db_transfer_zip(config, timeout_seconds=args.timeout)
    stamp = _slug_stamp(filename)
    out_dir = project / "snapshots" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / Path(filename).name
    out_path.write_bytes(data)
    print(f"Wrote {out_path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
