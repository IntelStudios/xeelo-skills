#!/usr/bin/env python3
"""Precompile Xeelo site settings via GraphQL Mutate_admin_precompile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.graphql_client import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    format_mutation_messages,
    precompile_settings,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompile Xeelo site settings via GraphQL")
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (xeeloUrl, token)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    args = parser.parse_args()

    config = ConnectionConfig.load(args.connection)
    print(f"Precompiling settings at {config.graphql_url}")
    payload = precompile_settings(config, timeout_seconds=args.timeout)
    extra = format_mutation_messages(payload.get("messages"))
    suffix = f" {extra}" if extra else ""
    print(f"Precompile success={payload.get('success')}{suffix}")


if __name__ == "__main__":
    main()
