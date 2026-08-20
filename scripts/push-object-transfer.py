#!/usr/bin/env python3
"""Upload Object Transfer XML and process it via GraphQL (dry-run or real)."""

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
    push_object_transfer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload and process Object Transfer XML via Xeelo GraphQL"
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .xeelo-connection.json (xeeloUrl, token)",
    )
    parser.add_argument(
        "--xml",
        type=Path,
        action="append",
        default=[],
        help="Object Transfer XML path (repeatable)",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        action="append",
        default=[],
        help="Object Transfer ZIP path (repeatable; XML is read from the archive)",
    )
    parser.add_argument(
        "--loop",
        type=Path,
        default=None,
        help="Change loop directory; uses output/*-object-transfer.xml (or .zip)",
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
        help="Process as test only (isTestOnly=true)",
    )
    args = parser.parse_args()

    try:
        paths = collect_transfer_paths(loop=args.loop, xmls=args.xml, zips=args.zip)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    config = ConnectionConfig.load(args.connection)
    mode = "test" if args.only_test else "real"
    print(
        f"Pushing {len(paths)} Object Transfer package(s) to "
        f"{config.graphql_url} ({mode})"
    )
    for path in paths:
        print(f"Uploading {path} (isTestOnly={str(args.only_test).lower()})")
        result = push_object_transfer(
            config,
            path,
            only_test=args.only_test,
            timeout_seconds=args.timeout,
        )
        print(
            f"Processed xmlId={result.object_setup_xml_id} {result.filename} "
            f"success={result.success} onlyTest={result.only_test}"
        )


if __name__ == "__main__":
    main()
