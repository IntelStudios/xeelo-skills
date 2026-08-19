#!/usr/bin/env python3
"""Extract TableHint rows from postdeploy SQL."""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

USER_REPO = Path(os.environ.get("XEELO_USER_REPO", "/data/src/SmarterMDM-User"))
MISC_SQL = USER_REPO / "SmarterMDM/SmartMDMSQLProject/PostDeploy/140_SyncTables_Misc.sql"
SETTINGS_SQL = USER_REPO / "SmarterMDM/SmartMDMSQLProject/PostDeploy/120_SyncTables_Settings.sql"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_table_hints(sql: str) -> list[dict]:
    hints = []
    pattern = re.compile(
        r"insert\s+into\s+@TableH?int\s+values\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(N?'(?:''|[^'])*')\s*\)",
        re.IGNORECASE,
    )
    for table, column, hint_raw in pattern.findall(sql):
        hint_html = hint_raw.strip()
        if hint_html.startswith("N'"):
            hint_html = hint_html[2:-1]
        elif hint_html.startswith("'"):
            hint_html = hint_html[1:-1]
        hint_html = hint_html.replace("''", "'")
        hints.append(
            {
                "table": table,
                "column": column,
                "hintHtml": hint_html,
                "hintText": strip_html(hint_html),
            }
        )
    return hints


def extract_settings_hints(sql: str) -> list[dict]:
    hints = []
    for match in re.finditer(
        r"\(\d+,\s*'[^']*',\s*\d+,\s*'([^']+)',\s*'[^']*',\s*'[^']*',\s*\d+,\s*'([^']*)'\)",
        sql,
    ):
        hints.append(
            {
                "key": match.group(1),
                "hintHtml": match.group(2),
                "hintText": strip_html(match.group(2)),
            }
        )
    return hints


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    misc = MISC_SQL.read_text(encoding="utf-8", errors="replace")
    settings = SETTINGS_SQL.read_text(encoding="utf-8", errors="replace")

    table_hints = extract_table_hints(misc)
    (OUT_DIR / "table-hints.json").write_text(
        json.dumps(table_hints, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote table-hints.json ({len(table_hints)} hints)")

    settings_hints = [h for h in extract_settings_hints(settings) if h["hintText"]]
    (OUT_DIR / "settings-hints.json").write_text(
        json.dumps(settings_hints, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote settings-hints.json ({len(settings_hints)} hints)")


if __name__ == "__main__":
    main()
