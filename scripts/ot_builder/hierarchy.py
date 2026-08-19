"""Build ObjectMap schema pairs from ObjectSetup edges."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"


def load_transfer_map() -> list[dict]:
    return json.loads((DATA / "object-transfer-map.json").read_text(encoding="utf-8"))


def build_object_map(_edges: list[dict] | None = None) -> list[dict]:
    """Full schema map from object-transfer-map.json (matches Xeelo download)."""
    return [
        {"TableName": entry["parent"], "ChildTableName": entry["child"]}
        for entry in load_transfer_map()
    ]


def dedupe_edges(edges: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for edge in edges:
        key = (
            edge["TableName"],
            edge["TableRowID"],
            edge["ChildTableName"],
            edge["ChildTableRowID"],
        )
        if key not in seen:
            seen.add(key)
            out.append(edge)
    return out
