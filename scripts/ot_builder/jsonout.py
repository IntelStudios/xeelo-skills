"""Assemble Object transfer JSON (download shape; only changing rows)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ot_builder.delta import omit_unchanged_rows
from ot_builder.xml import _sorted_tables

DATA = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _bit_columns() -> dict[str, frozenset[str]]:
    bits: dict[str, frozenset[str]] = {}
    schema_dir = DATA / "schemas"
    if not schema_dir.is_dir():
        return bits
    for path in schema_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        table = str(data.get("table") or path.stem)
        names = {
            str(col["name"])
            for col in data.get("columns") or []
            if isinstance(col, dict)
            and str(col.get("type") or "").lower() == "bit"
            and col.get("name")
        }
        if names:
            bits[table] = frozenset(names)
    return bits


def _json_cell(table: str, column: str, value: Any) -> Any:
    if table in _bit_columns() and column in _bit_columns()[table]:
        if isinstance(value, bool):
            return value
        if value in (0, 1, "0", "1"):
            return value in (1, "1", True)
    return value


def _clean_row(table: str, row: dict) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        cleaned[str(key)] = _json_cell(table, str(key), value)
    return cleaned


def build_object_transfer_json(
    rows: dict[str, list[dict]],
    *,
    baseline: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """UTF-8 JSON object: table name → row arrays.

    When ``baseline`` is a DB-transfer download, rows whose Orig. ID already
    exists with the same generated cells are omitted. FK references to those
    IDs stay on changing rows. Returns ``(json_text, omitted_count)``.
    """
    omitted = 0
    if baseline:
        rows, omitted = omit_unchanged_rows(rows, baseline, clean_row=_clean_row)
    payload: dict[str, list[dict[str, Any]]] = {}
    for table in _sorted_tables(rows):
        table_rows = rows.get(table) or []
        if not table_rows:
            continue
        out_rows: list[dict[str, Any]] = []
        for row in table_rows:
            if not isinstance(row, dict):
                continue
            cleaned = _clean_row(table, row)
            if cleaned:
                out_rows.append(cleaned)
        if out_rows:
            payload[table] = out_rows
    if not payload:
        raise ValueError("Object Transfer JSON has no table rows")
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n", omitted


def write_json(text: str, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_object_transfer_json_text(text: str) -> dict[str, Any]:
    """Validate GraphQL/file Object Transfer JSON (table → row arrays)."""
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        raise ValueError("Object Transfer JSON is empty")
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid Object Transfer JSON: {exc}") from exc
    if not isinstance(obj, dict) or isinstance(obj, list):
        raise ValueError("Object Transfer JSON must be an object keyed by table name")
    if not obj:
        raise ValueError("Object Transfer JSON has no tables")
    for table, table_rows in obj.items():
        if not isinstance(table, str) or not table:
            raise ValueError(f"Invalid table name in Object Transfer JSON: {table!r}")
        if not isinstance(table_rows, list):
            raise ValueError(
                f"Object Transfer table {table!r} must be an array of rows, "
                f"got {type(table_rows).__name__}"
            )
        if not table_rows:
            raise ValueError(f"Object Transfer table {table!r} is empty (omit unchanged tables)")
        for i, row in enumerate(table_rows):
            if not isinstance(row, dict) or isinstance(row, list):
                raise ValueError(
                    f"Object Transfer {table}[{i}] must be an object, got {type(row).__name__}"
                )
    return obj
