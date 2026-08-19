#!/usr/bin/env python3
"""Extract ObjectSetup parent→child schema map from spAdminObjectSetupXMLDownload.sql."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

USER_REPO = Path(os.environ.get("XEELO_USER_REPO", "/data/src/SmarterMDM-User"))
DOWNLOAD_SQL = (
    USER_REPO
    / "SmarterMDM/SmartMDMSQLProject/SQL scripts/Stored Procedures/Admin - ObjectSetup/spAdminObjectSetupXMLDownload.sql"
)
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "object-transfer-map.json"

PATTERN = re.compile(
    r"insert\s+into\s+#temp_RelMap\s*\(\s*TableName\s*,\s*ChildTableName\s*\)\s*values\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
    re.IGNORECASE,
)


def main() -> None:
    sql = DOWNLOAD_SQL.read_text(encoding="utf-8", errors="replace")
    edges = []
    seen = set()
    for parent, child in PATTERN.findall(sql):
        key = (parent, child)
        if key not in seen:
            seen.add(key)
            edges.append({"parent": parent, "child": child})

    edges.sort(key=lambda e: (e["parent"], e["child"]))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(edges, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH.name} ({len(edges)} edges)")


if __name__ == "__main__":
    main()
