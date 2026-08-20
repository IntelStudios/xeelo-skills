#!/usr/bin/env python3
"""Apply Object Transfer(s) for real and precompile site settings via GraphQL."""

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
    precompile_settings,
    push_object_transfer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload and process Object Transfer XML, then precompile via Xeelo GraphQL"
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
    args = parser.parse_args()

    try:
        paths = collect_transfer_paths(loop=args.loop, xmls=args.xml, zips=args.zip)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    config = ConnectionConfig.load(args.connection)
    print(f"Publishing {len(paths)} Object Transfer package(s) to {config.graphql_url}")
    for path in paths:
        print(f"Uploading {path} (isTestOnly=false)")
        result = push_object_transfer(
            config,
            path,
            only_test=False,
            timeout_seconds=args.timeout,
        )
        print(
            f"Processed xmlId={result.object_setup_xml_id} {result.filename} "
            f"success={result.success}"
        )
    print(f"Precompiling settings at {config.graphql_url}")
    payload = precompile_settings(config, timeout_seconds=args.timeout)
    extra = format_mutation_messages(payload.get("messages"))
    suffix = f" {extra}" if extra else ""
    print(f"Precompile success={payload.get('success')}{suffix}")


if __name__ == "__main__":
    main()
