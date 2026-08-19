#!/usr/bin/env python3
"""Extract DB transfer table list from spAdminDbSetupXMLProcessBatch.sql."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

USER_REPO = Path(os.environ.get("XEELO_USER_REPO", "/data/src/SmarterMDM-User"))
BATCH_SQL = (
    USER_REPO
    / "SmarterMDM/SmartMDMSQLProject/SQL scripts/Stored Procedures/Admin - DbSetup/spAdminDbSetupXMLProcessBatch.sql"
)
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    sql = BATCH_SQL.read_text(encoding="utf-8", errors="replace")
    rows = []
    for table_type, table_name in re.findall(
        r"\('([UDX])',\s*'([^']+)'\)", sql
    ):
        rows.append({"table": table_name, "type": table_type})
    rows.sort(key=lambda r: r["table"])

    (OUT_DIR / "transfer-tables.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote transfer-tables.json ({len(rows)} tables)")


if __name__ == "__main__":
    main()
