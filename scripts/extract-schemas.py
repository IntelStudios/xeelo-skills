#!/usr/bin/env python3
"""Extract CREATE TABLE schemas from SmarterMDM-User SQL scripts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

USER_REPO = Path(os.environ.get("XEELO_USER_REPO", "/data/src/SmarterMDM-User"))
TABLES_ROOT = USER_REPO / "SmarterMDM/SmartMDMSQLProject/SQL scripts/Tables"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "schemas"

PRIORITY_TABLES = [
    "Company",
    "ObjectType",
    "Object",
    "ObjectLineTab",
    "ObjectLineSection",
    "ObjectLine",
    "ObjectLineLookup",
    "ObjectLineLookupValue",
    "ObjectLineSource",
    "ObjectLineSourceValue",
    "ObjectLineSourceRefObject",
    "ObjectDefault",
    "ObjectDefaultAccess",
    "ObjectDefaultLine",
    "ObjectUpdateAction",
    "ObjectUpdateAccess",
    "Workflow",
    "WorkflowStep",
    "WorkflowStepAction",
    "Role",
    "RequestStatus",
    "WorkflowStepActionStyle",
    "ObjectLineValidation",
    "ObjectLineOnGrid",
    "ObjectAction",
    "ObjectActionParam",
    "ObjectActionCondition",
    "WorkflowStepObjectAction",
    "LanguageTable",
    "ObjectLineAutoNumber",
    "Notification",
    "NotificationAttachment",
    "NotificationCondition",
    "NotificationPrintout",
    "NotificationCalculation",
    "WorkflowStepNotification",
]


def find_table_file(table_name: str) -> Path | None:
    for path in TABLES_ROOT.rglob(f"{table_name}.sql"):
        return path
    return None


def parse_create_table(sql: str, table_name: str) -> dict:
    start = re.search(
        rf"CREATE\s+TABLE\s+(?:\[dbo\]\.)?\[{re.escape(table_name)}\]\s*\(",
        sql,
        re.IGNORECASE,
    )
    if not start:
        return {"table": table_name, "columns": [], "foreignKeys": []}

    i = start.end()
    depth = 1
    body_chars: list[str] = []
    while i < len(sql) and depth > 0:
        ch = sql[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        body_chars.append(ch)
        i += 1
    body = "".join(body_chars)

    columns: list[dict] = []
    foreign_keys: list[dict] = []

    for raw_line in body.split("\n"):
        line = raw_line.strip().rstrip(",")
        if not line or line.startswith("--"):
            continue
        if line.upper().startswith("CONSTRAINT"):
            fk = re.search(
                r"FOREIGN\s+KEY\s*\(\[?(\w+)\]?\)\s*REFERENCES\s*\[?dbo\]?\.\[?(\w+)\]?\s*\(\[?(\w+)\]?\)",
                line,
                re.IGNORECASE,
            )
            if fk:
                foreign_keys.append(
                    {
                        "column": fk.group(1),
                        "referencesTable": fk.group(2),
                        "referencesColumn": fk.group(3),
                    }
                )
            continue

        col_match = re.match(r"\[(\w+)\]\s+(.+)", line)
        if not col_match:
            continue

        name = col_match.group(1)
        rest = col_match.group(2)
        identity = "IDENTITY" in rest.upper()
        nullable = "NOT NULL" not in rest.upper()
        default_match = re.search(r"DEFAULT\s*\(([^)]+)\)", rest, re.IGNORECASE)
        type_match = re.match(
            r"(NVARCHAR\s*\([^)]+\)|VARCHAR\s*\([^)]+\)|NVARCHAR\s*\(MAX\)|VARCHAR\s*\(MAX\)|INT|BIT|DATETIME|BIGINT|DECIMAL\s*\([^)]+\)|UNIQUEIDENTIFIER|CHAR\s*\([^)]+\))",
            rest,
            re.IGNORECASE,
        )
        columns.append(
            {
                "name": name,
                "type": type_match.group(1) if type_match else rest.split()[0],
                "nullable": nullable,
                "identity": identity,
                "default": default_match.group(1).strip() if default_match else None,
            }
        )

    return {"table": table_name, "columns": columns, "foreignKeys": foreign_keys}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for table in PRIORITY_TABLES:
        path = find_table_file(table)
        if not path:
            print(f"WARN: missing table file for {table}")
            continue
        schema = parse_create_table(path.read_text(encoding="utf-8", errors="replace"), table)
        (OUT_DIR / f"{table}.json").write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {table}.json ({len(schema['columns'])} columns)")


if __name__ == "__main__":
    main()
