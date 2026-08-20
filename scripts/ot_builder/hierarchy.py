"""Build ObjectMap schema pairs from ObjectSetup edges."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"


def load_transfer_map() -> list[dict]:
    return json.loads((DATA / "object-transfer-map.json").read_text(encoding="utf-8"))


def build_object_map(edges: list[dict] | None = None) -> list[dict]:
    """Full schema map from object-transfer-map.json, plus LanguageTable pairs from edges."""
    pairs = [
        {"TableName": entry["parent"], "ChildTableName": entry["child"]}
        for entry in load_transfer_map()
    ]
    seen = {(pair["TableName"], pair["ChildTableName"]) for pair in pairs}
    for edge in edges or []:
        if edge.get("ChildTableName") != "LanguageTable":
            continue
        key = (str(edge["TableName"]), "LanguageTable")
        if key in seen:
            continue
        seen.add(key)
        pairs.append({"TableName": key[0], "ChildTableName": "LanguageTable"})
    return pairs


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
