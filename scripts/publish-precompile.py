#!/usr/bin/env python3
"""Start Xeelo Admin PreCompileSettings and wait for Compile WebSocket success."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.admin_client import ConnectionConfig, publish_site  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompile Xeelo site settings via Admin")
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (adminBaseUrl, siteId, credentials)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3600.0,
        help="Seconds to wait for Compile notification (default 3600)",
    )
    args = parser.parse_args()

    config = ConnectionConfig.load(args.connection)
    print(f"Publishing (PreCompileSettings) {config.admin_base_url} (siteId={config.site_id})")
    msg = publish_site(config, timeout_seconds=args.timeout)
    text = msg.get("Message") or "Compilation successful"
    print(f"Compile {msg.get('Status')}: {text}")


if __name__ == "__main__":
    main()
