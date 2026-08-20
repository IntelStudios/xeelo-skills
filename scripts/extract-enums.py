#!/usr/bin/env python3
"""Extract enum/reference data from SmarterMDM-User postdeploy scripts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

USER_REPO = Path(os.environ.get("XEELO_USER_REPO", "/data/src/SmarterMDM-User"))
POSTDEPLOY = USER_REPO / "SmarterMDM/SmartMDMSQLProject/PostDeploy"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "enums"


def parse_insert_rows(sql: str, table_alias: str) -> list[dict]:
    rows: list[dict] = []
    pattern = re.compile(
        rf"insert\s+into\s+(?:@|dbo\.\[?temp_)?{table_alias}[^\n]*\n?(.*?)(?=insert\s+into|EXEC\s+dbo\.spSyncSysTables|$)",
        re.IGNORECASE | re.DOTALL,
    )
    block = pattern.search(sql)
    if not block:
        return rows

    value_pattern = re.compile(r"\((\d+),\s*N?'([^']*(?:''[^']*)*)'", re.IGNORECASE)
    for match in value_pattern.finditer(block.group(1)):
        row_id = int(match.group(1))
        name = match.group(2).replace("''", "'")
        rows.append({"id": row_id, "name": name})
    return rows


def parse_object_line_type(sql: str) -> list[dict]:
    rows = []
    section = re.search(
        r"INSERT INTO \[dbo\]\.\[temp_ObjectLineType\].*?VALUES\s*(.*?)\s*EXEC dbo\.spSyncSysTables 'ObjectLineType'",
        sql,
        re.DOTALL | re.IGNORECASE,
    )
    if not section:
        return rows
    for match in re.finditer(r"\((\d+),\s*N'([^']+)'", section.group(1)):
        rows.append({"id": int(match.group(1)), "name": match.group(2)})
    return rows


def parse_object_line_validation(sql: str) -> list[dict]:
    rows = []
    section = re.search(
        r"INSERT INTO \[dbo\]\.\[temp_ObjectLineValidation\].*?VALUES\s*(.*?)\s*EXEC dbo\.spSyncSysTables 'ObjectLineValidation'",
        sql,
        re.DOTALL | re.IGNORECASE,
    )
    if not section:
        return rows
    for match in re.finditer(r"\((\d+),\s*N'([^']+)'", section.group(1)):
        rows.append({"id": int(match.group(1)), "name": match.group(2)})
    return rows


def parse_workflow_action_styles(sql: str) -> list[dict]:
    rows = []
    for match in re.finditer(
        r"\((\d+),\s*'([^']+)',\s*'[^']*',\s*'[^']*',\s*'[^']*',\s*'[^']*',\s*\d+,\s*\d+",
        sql,
    ):
        rows.append({"id": int(match.group(1)), "name": match.group(2)})
    return rows


def parse_custom_color(sql: str) -> list[dict]:
    rows: list[dict] = []
    section = re.search(
        r"insert\s+into\s+dbo\.temp_CustomColor.*?values\s*(.*?)(?:merge\s+dbo\.CustomColor)",
        sql,
        re.DOTALL | re.IGNORECASE,
    )
    if not section:
        return rows
    for match in re.finditer(
        r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*([01])\s*\)",
        section.group(1),
    ):
        rows.append(
            {
                "code": match.group(1),
                "hex": match.group(2),
                "isDefault": match.group(3) == "1",
            }
        )
    return rows


def parse_object_line_source_style(sql: str) -> list[dict]:
    rows = []
    section = re.search(
        r"INSERT INTO \[dbo\]\.\[temp_ObjectLineSourceStyle\].*?VALUES\s*(.*?)\s*EXEC dbo\.spSyncSysTables 'ObjectLineSourceStyle'",
        sql,
        re.DOTALL | re.IGNORECASE,
    )
    if not section:
        return rows
    for match in re.finditer(r"\((\d+),\s*N'([^']+)'", section.group(1)):
        rows.append({"id": int(match.group(1)), "name": match.group(2)})
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    object_sql = (POSTDEPLOY / "070_SyncTables_Object.sql").read_text(encoding="utf-8", errors="replace")
    workflow_sql = (POSTDEPLOY / "030_SyncTables_Workflow.sql").read_text(encoding="utf-8", errors="replace")
    misc_sql = (POSTDEPLOY / "140_SyncTables_Misc.sql").read_text(encoding="utf-8", errors="replace")

    enums = {
        "ObjectLineType.json": parse_object_line_type(object_sql),
        "ObjectLineValidation.json": parse_object_line_validation(object_sql),
        "ObjectLineSourceStyle.json": parse_object_line_source_style(object_sql),
        "WorkflowStepActionStyle.json": parse_workflow_action_styles(workflow_sql),
        "CustomColor.json": parse_custom_color(misc_sql),
    }

    for filename, data in enums.items():
        (OUT_DIR / filename).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {filename} ({len(data)} rows)")


if __name__ == "__main__":
    main()
