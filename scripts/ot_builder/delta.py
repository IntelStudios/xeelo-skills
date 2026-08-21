"""Drop Object Transfer rows that already exist unchanged in a DB-transfer download."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _identity_columns() -> dict[str, str]:
    cols: dict[str, str] = {}
    schema_dir = DATA / "schemas"
    if not schema_dir.is_dir():
        return cols
    for path in schema_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        table = str(data.get("table") or path.stem)
        identities = [
            str(col["name"])
            for col in data.get("columns") or []
            if isinstance(col, dict) and col.get("identity") and col.get("name")
        ]
        if not identities:
            continue
        preferred = f"{table}ID"
        cols[table] = preferred if preferred in identities else identities[0]
    return cols


def _pk_column(table: str) -> str:
    return _identity_columns().get(table) or f"{table}ID"


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _pk_key(value: Any) -> Any:
    n = _as_int(value)
    return n if n is not None else value


def values_equal(left: Any, right: Any) -> bool:
    if left is right or left == right:
        return True
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    li, ri = _as_int(left), _as_int(right)
    if li is not None and ri is not None:
        return li == ri
    return False


def row_unchanged(generated: dict[str, Any], existing: dict[str, Any]) -> bool:
    """True when every generated cell matches the download row. Extra download columns are ignored."""
    if not generated:
        return True
    for key, value in generated.items():
        if key not in existing:
            return False
        if not values_equal(value, existing[key]):
            return False
    return True


def index_baseline(baseline: dict[str, Any]) -> dict[str, dict[Any, dict[str, Any]]]:
    indexed: dict[str, dict[Any, dict[str, Any]]] = {}
    for table, table_rows in baseline.items():
        if not isinstance(table_rows, list):
            continue
        pk_col = _pk_column(str(table))
        by_id: dict[Any, dict[str, Any]] = {}
        for row in table_rows:
            if not isinstance(row, dict) or pk_col not in row:
                continue
            by_id[_pk_key(row[pk_col])] = row
        indexed[str(table)] = by_id
    return indexed


def omit_unchanged_rows(
    rows: dict[str, list[dict]],
    baseline: dict[str, Any],
    *,
    clean_row,
) -> tuple[dict[str, list[dict]], int]:
    """Keep new rows and rows whose generated cells differ from the download."""
    indexed = index_baseline(baseline)
    omitted = 0
    kept: dict[str, list[dict]] = {}
    for table, table_rows in rows.items():
        pk_col = _pk_column(table)
        existing = indexed.get(table) or {}
        out: list[dict] = []
        for row in table_rows:
            if not isinstance(row, dict):
                continue
            cleaned = clean_row(table, row)
            if not cleaned:
                continue
            if pk_col not in cleaned:
                out.append(row)
                continue
            found = existing.get(_pk_key(cleaned[pk_col]))
            if found is not None and row_unchanged(cleaned, found):
                omitted += 1
                continue
            out.append(row)
        if out:
            kept[table] = out
    return kept, omitted


def find_project_root(start: Path) -> Path | None:
    for path in [start.resolve(), *start.resolve().parents]:
        if (path / ".xeelo-connection.json").is_file():
            return path
        if (path / "snapshots").is_dir() and (path / "changes").is_dir():
            return path
    return None


def latest_snapshot_json(project: Path) -> Path | None:
    snap = project / "snapshots"
    if not snap.is_dir():
        return None
    dirs = sorted(p for p in snap.iterdir() if p.is_dir())
    if not dirs:
        return None
    files = sorted(dirs[-1].glob("*.json"))
    return files[-1] if files else None


def load_baseline_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or isinstance(data, list):
        raise ValueError(f"Baseline {path} must be a JSON object keyed by table name")
    return data
