#!/usr/bin/env python3
"""Create an application backup via GraphQL Mutate_admin_transfer_backup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.graphql_client import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    ConnectionPermissionError,
    GraphqlError,
    backup_admin_transfer,
    format_mutation_messages,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an application backup via GraphQL Mutate_admin_transfer_backup"
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (xeeloUrl, token)",
    )
    parser.add_argument(
        "--delete-older-than",
        type=int,
        default=None,
        help="Optional days; omit to keep all backups",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    args = parser.parse_args()

    try:
        config = ConnectionConfig.load(args.connection)
        print(f"Backing up application at {config.graphql_url}")
        payload = backup_admin_transfer(
            config,
            delete_older_than=args.delete_older_than,
            timeout_seconds=args.timeout,
        )
    except (ValueError, ConnectionPermissionError, GraphqlError) as exc:
        raise SystemExit(str(exc)) from exc
    extra = format_mutation_messages(payload.get("messages"))
    suffix = f" {extra}" if extra else ""
    print(f"Backup success={payload.get('success')}{suffix}")


if __name__ == "__main__":
    main()
