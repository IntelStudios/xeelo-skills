#!/usr/bin/env python3
"""Extract entity labels from Admin en.json tableName section."""

from __future__ import annotations

import json
import os
from pathlib import Path

ADMIN_REPO = Path(os.environ.get("XEELO_ADMIN_REPO", "/data/src/SmarterMDM-Admin"))
EN_JSON = ADMIN_REPO / "XeeloAdminNetGUI/ClientApp/src/assets/i18n/en.json"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def flatten_table_names(node: dict, prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in node.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_table_names(value, full_key))
        else:
            result[key if not prefix else key] = value
    return result


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(EN_JSON.read_text(encoding="utf-8"))
    table_names = data.get("tableName", {})
    flat = {}
    if "$sa" in table_names:
        flat.update(table_names["$sa"])
    for key, value in table_names.items():
        if key != "$sa" and isinstance(value, str):
            flat[key] = value

    (OUT_DIR / "entity-labels.json").write_text(
        json.dumps(flat, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote entity-labels.json ({len(flat)} labels)")


if __name__ == "__main__":
    main()
