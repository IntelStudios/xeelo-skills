#!/usr/bin/env python3
"""Upload Object Transfer JSON via GraphQL (dry-run or real)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.graphql_client import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    collect_transfer_paths,
    format_mutation_messages,
    push_object_transfer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload Object Transfer JSON via Xeelo GraphQL"
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (xeeloUrl, token)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        action="append",
        default=[],
        help="Object Transfer JSON path (repeatable)",
    )
    parser.add_argument(
        "--loop",
        type=Path,
        default=None,
        help="Change loop directory; uses output/*-object-transfer.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    parser.add_argument(
        "--only-test",
        action="store_true",
        help="Dry-run (isTest=true)",
    )
    args = parser.parse_args()

    try:
        paths = collect_transfer_paths(loop=args.loop, jsons=args.json)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    config = ConnectionConfig.load(args.connection)
    mode = "test" if args.only_test else "real"
    print(
        f"Pushing {len(paths)} Object Transfer package(s) to "
        f"{config.graphql_url} ({mode})"
    )
    for path in paths:
        print(f"Uploading {path} (isTest={str(args.only_test).lower()})")
        result = push_object_transfer(
            config,
            path,
            only_test=args.only_test,
            timeout_seconds=args.timeout,
        )
        extra = format_mutation_messages(result.messages)
        suffix = f" {extra}" if extra else ""
        print(
            f"Uploaded {result.filename} success={result.success} "
            f"isTest={str(result.only_test).lower()}{suffix}"
        )


if __name__ == "__main__":
    main()
