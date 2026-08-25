"""SystemLine catalog for ObjectLineOnGrid (inbox system columns)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "enums" / "SystemLine.json"

SYS_KEY_PREFIX = "sys:"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    return tuple(raw)


def code_for_id(system_line_id: int) -> str | None:
    for row in _rows():
        if int(row["id"]) == int(system_line_id):
            return str(row["code"])
    return None


def id_for_code(code: str) -> int | None:
    needle = str(code)
    for row in _rows():
        if str(row["code"]) == needle:
            return int(row["id"])
    return None


def explicit_key_token(code: str) -> str:
    """Token used in ``ids.explicit.objectLineOnGrid`` after size/type/module."""
    return f"{SYS_KEY_PREFIX}{code}"
